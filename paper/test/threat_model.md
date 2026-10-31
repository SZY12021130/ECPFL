# Threat Model and Security Analysis

> 本节仿照 FedPHE (IEEE TDSC) 的威胁模型分析范式，对 CipherFetch 方案进行系统性的安全性分析。

---

## 先说结论：当前方案加密前**没有**添加 DP 噪声

在回答威胁模型之前，先明确回应用户的问题：**当前代码方案在本地梯度加密之前，没有添加差分隐私（DP）噪声。**

具体而言：
- `client.py::local_train()` 计算的是纯梯度差值 `param.data - old_params[name]`，无任何噪声注入。
- `ptopk.py` 中的 `apply_residual` / `update_residual` 是**误差反馈（Error Feedback）**机制，用于补偿 TopK 压缩导致的信息损失，其数学形式为 $r_{t+1} = (\Delta_t + r_t) - \text{TopK}(\Delta_t + r_t)$。这不是隐私保护噪声，而是**收敛性辅助机制**。
- 加密前的最后一步是稀疏化选择（TopK 或 RandK），然后直接送入 `CKKSEncryptor.encrypt_chunks()`。

**这意味着**：当前方案的隐私保护完全依赖于 CKKS 加密的语义安全性（RLWE 假设）。若未来需要在加密前添加 DP 噪声，可在 `local_train()` 返回 `model_update` 后、送入 `encrypt_model_update()` 之前，插入高斯/拉普拉斯噪声注入模块。该修改与现有架构正交，不影响 TEE 聚合和 Prefetch 流程。

---

## 1 系统实体与信任假设

仿照 FedPHE 的实体划分，CipherFetch 涉及四类核心实体：

| 实体 | 符号 | 功能 | 信任假设 |
|------|------|------|----------|
| **密钥生成中心 (KGC)** | $\mathcal{K}$ | 生成 CKKS 密钥对 $(pk, sk)$，初始化阈值参数 | 初始化后永久离线，半诚实 |
| **聚合服务器 (Host)** | $\mathcal{S}_H$ | 收集密文更新，执行同态聚合，调度 Prefetch，维护密文历史 | **不可信**，可诚实但好奇或恶意 |
| **可信执行环境 (TEE)** | $\mathcal{S}_E$ | 持有私钥 $sk$，执行明文聚合、全局残差补偿、二次压缩、重新加密 | 硬件可信，代码可远程认证 |
| **客户端** | $\mathcal{C}_i, i \in [n]$ | 本地训练，加密上传，接收 Prefetch delta，执行同态累加 | 半诚实（遵循协议但试图推断信息） |

**核心信任边界**：
- TEE 与 Server Host 之间的边界是硬件强隔离的：Host 无法读取 TEE 内存，TEE 通过 ECALL 接口接收密文输入并返回密文输出。
- 客户端持有公钥 $pk$ 和统一密钥上下文（含 $sk$，用于本地解密 Prefetch 状态），但**不共享 $sk$ 给其他客户端**。
- KGC 在初始化后离线，不参与任何轮次执行。

---

## 2 攻击者模型

仿照 FedPHE 的分类方法，我们考虑四种攻击者模型：半诚实服务器、半诚实客户端、恶意服务器、客户端合谋。

### 2.1 半诚实服务器 (Honest-but-Curious Server)

**能力**：Server Host 遵循协议执行所有规定操作（收集更新、调用 TEE、调度 Prefetch），但试图从观察到的密文和元数据中推断单个客户端的隐私信息。

**攻击目标**：
- 从密文 upload$_i$ 中恢复 Client $i$ 的明文梯度 $\mathbf{g}_i$。
- 从 Prefetch delta 的流量模式推断客户端的参与历史。
- 通过多轮密文对比，追踪特定客户端的模型演化轨迹。

**安全目标（对应 FedPHE 的 IND-CPA 定义）**：

> **定义 1（对服务器的语义安全）**：对于任意概率多项式时间敌手 $\mathcal{A}$，给定两个等长明文梯度 $\mathbf{g}_0, \mathbf{g}_1$ 和挑战密文 $\text{ct}^* \leftarrow \text{Enc}(pk, \mathbf{g}_b)$（$b \in \{0,1\}$），敌手输出猜测 $b'$ 的优势满足：
> $$
> \left| \Pr[b' = b] - \frac{1}{2} \right| \leq \text{negl}(\lambda)
> $$

**证明概要**：
1. 客户端上传 upload$_i$ 是标准 CKKS 密文，其 IND-CPA 安全性基于决策性 RLWE 假设 [1]。
2. Server Host 仅持有 $pk$，不持有 $sk$（$sk$ 仅在 TEE 密封存储中）。
3. 在 RLWE 假设下，$(\mathbf{a}, \mathbf{a}\mathbf{s} + \mathbf{e} + \mathbf{m})$ 与均匀随机对计算不可区分。
4. 因此 Server Host 对 upload$_i$ 的视图与对随机密文的视图不可区分。

**结论**：Server Host 对单个客户端更新具有 IND-CPA 安全性。

### 2.2 半诚实客户端 (Honest-but-Curious Client)

**能力**：Client $j$ 遵循协议执行本地训练、加密上传和 Prefetch 累加，但试图从收到的信息中推断其他客户端的梯度。

**攻击目标**：
- 从全局模型更新中反推 Client $i$（$i \neq j$）的本地梯度。
- 利用多轮聚合结果建立方程组，求解特定客户端的更新。

**安全分析**：

在标准 CipherFetch 方案（无盲化掩码）中，Client $j$ 面临的信息分为两类：

1. **全局密文模型**：Client $j$ 收到的是完整全局模型密文（或稀疏 delta）。解密后得到的是聚合结果 $\sum_i \alpha_i \mathbf{g}_i$，而非单个 $\mathbf{g}_i$。由于 FedAvg 聚合是多个客户端梯度的加权平均，单个客户端的梯度被 "淹没" 在聚合中。

2. **Prefetch Delta**：Client $j$ 收到的 Prefetch delta 是服务器广播的公共信息，所有客户端收到相同的 delta，不包含任何客户端特定信息。

**局限**：若客户端数量极少（如 $n=2$），Client $j$ 可以从聚合结果中减去自身贡献，精确恢复另一个客户端的梯度。这是所有基于同态聚合的 FL 方案的共同局限，FedPHE 通过**盲化掩码**解决（见第 4 节扩展讨论）。

### 2.3 恶意服务器 (Malicious Server)

**能力**：Server Host 可任意偏离协议，包括：
- 篡改聚合权重 $\{\alpha_i\}$，给特定客户端更高/更低权重。
- 伪造 Prefetch delta，向客户端发送错误的全局更新。
- 选择性丢弃某些客户端的更新。
- 延迟或拒绝向特定客户端发送 Prefetch delta。
- 篡改 TEE 输入（但无法篡改 TEE 内部执行，除非攻破硬件）。

**攻击目标**：
- 破坏模型收敛（可用性攻击）。
- 通过控制 Prefetch delta 操纵特定客户端的本地模型（定向 poison）。
- 通过选择性聚合推断客户端隐私（membership inference 的变体）。

**防御机制与残余风险**：

| 攻击 | 影响 | 防御机制 | 残余风险 |
|------|------|----------|----------|
| 篡改聚合权重 | 模型偏差 | TEE 内密封存储权重，Host 无法修改 | TEE 硬件漏洞 |
| 伪造 Prefetch delta | 客户端模型偏离 | 数字签名验证 delta 来源 | 签名私钥泄露 |
| 选择性丢弃更新 | 收敛变慢/偏差 | 客户端监控本地精度变化 | 无法密码学检测 |
| 延迟 Prefetch | 训练效率降低 | 虚拟时钟计入延迟 | 无安全影响 |

**关键观察**：CipherFetch 对恶意服务器具有**自恢复能力**。即使 Server 发送错误的 Prefetch delta，客户端在下一轮被选中时上传的是本地梯度差值（相对于本地模型状态），下一轮聚合会重新校正全局模型。但持续的大幅度篡改会导致收敛失败。

### 2.4 客户端合谋 (Client Collusion)

**能力**：$k$ 个客户端共享各自收到的信息（包括全局模型、Prefetch delta、参与历史），联合推断非合谋客户端的隐私。

**攻击分析**：

在标准方案中（无盲化掩码），$k = n-1$ 个合谋客户端可以精确恢复非合谋客户端的梯度：

1. 合谋客户端知道聚合结果 $\mathbf{G} = \sum_{i=1}^n \alpha_i \mathbf{g}_i$。
2. 合谋客户端知道自身贡献 $\sum_{j \in \text{collusion}} \alpha_j \mathbf{g}_j$。
3. 相减得到：$\alpha_{\text{target}} \mathbf{g}_{\text{target}} = \mathbf{G} - \sum_{j \in \text{collusion}} \alpha_j \mathbf{g}_j$。
4. 由于权重 $\alpha_{\text{target}}$ 是公开的，可直接恢复 $\mathbf{g}_{\text{target}}$。

**缓解措施**：
- 在 cross-device 场景（大量客户端），$n-1$ 合谋的概率极低。
- 在 cross-silo 场景，机构间存在法律约束和声誉机制。
- 可在加密前添加差分隐私噪声（见第 5 节），使合谋恢复的只是带噪声的近似梯度。

---

## 3 安全目标

综合上述攻击者模型，CipherFetch 的安全目标可归纳为以下三个维度：

### 3.1 隐私保护 (Privacy)

**目标**：任何未持有私钥 $sk$ 的实体（包括 Server Host 和其他客户端）无法从密文中恢复单个客户端的明文梯度。

**依赖假设**：
- 决策性 RLWE 假设成立。
- TEE 硬件隔离有效，私钥 $sk$ 不外泄。
- 客户端不泄露自己的明文梯度。

### 3.2 正确性 (Correctness)

**目标**：在不存在恶意攻击的情况下，CipherFetch 的聚合结果与标准 FedAvg 的聚合结果等价（允许 CKKS 近似误差）。

**形式化表述**：
设标准 FedAvg 的聚合结果为 $\mathbf{W}_{t+1}^{\text{FedAvg}}$，CipherFetch 的解密结果为 $\mathbf{W}_{t+1}^{\text{CF}}$。则：

$$
\|\mathbf{W}_{t+1}^{\text{CF}} - \mathbf{W}_{t+1}^{\text{FedAvg}}\|_\infty \leq \varepsilon_{\text{CKKS}} + \varepsilon_{\text{sparse}}
$$

其中 $\varepsilon_{\text{CKKS}}$ 是 CKKS 编码/解码的近似误差（由缩放因子 $\Delta$ 和重缩放操作决定），$\varepsilon_{\text{sparse}}$ 是 TopK 稀疏化引入的信息损失（由 PTopK 残差补偿渐进消除）。

### 3.3 可用性 (Availability)

**目标**：系统能够容忍一定比例的客户 dropout 和服务器延迟，不影响最终收敛。

**具体保证**：
- **客户端 Dropout**：若客户端在训练前 dropout，其未完成的本地更新不影响全局模型（因其未上传）。若客户端在 Prefetch 阶段 dropout，其已接收的 Prefetch delta 会在本地缓存中等待，下次上线时自动应用。
- **TEE 故障**：若 TEE 临时不可用，系统可回退到标准同态聚合路径（无 TEE 压缩），牺牲部分通信效率但保持训练连续性。
- **Prefetch 失败**：若客户端带宽不足无法完成 Prefetch，其在被选中时通过 Fetch' 阶段补齐缺失的 delta，不会导致训练失败。

---

## 4 扩展讨论：盲化掩码与 $n-1$ 合谋防护

FedPHE 的核心贡献之一是引入了**盲化掩码（Blinding Mask）**机制，解决 $n-1$ 客户端合谋即可恢复目标梯度的问题。在 CipherFetch 的完整设计蓝图（README 文档）中，也预留了该扩展：

### 4.1 盲化掩码机制

KGC 为每个客户端生成一个随机掩码 $\mathbf{b}_i$，满足**零和约束**：

$$
\sum_{i=1}^n w_i \mathbf{b}_i = \mathbf{0}
$$

客户端在加密前将掩码加到梯度上：$\tilde{\mathbf{g}}_i = \mathbf{g}_i + \mathbf{b}_i$。TEE 内聚合后，掩码相互抵消：

$$
\sum_i w_i \tilde{\mathbf{g}}_i = \sum_i w_i \mathbf{g}_i + \underbrace{\sum_i w_i \mathbf{b}_i}_{= \mathbf{0}} = \sum_i w_i \mathbf{g}_i
$$

### 4.2 安全性分析

**定理 2（盲化掩码的合谋抵抗）**：在零和掩码保护下，$k < n-1$ 个合谋客户端无法恢复非合谋客户端的梯度。

**证明**：
1. $k$ 个合谋客户端知道 $\{\mathbf{b}_j\}_{j \in \text{collusion}}$，但不知道非合谋客户端的掩码。
2. 零和约束提供 1 个方程，但有 $n - k$ 个未知掩码。
3. 当 $k < n-1$ 时，未知数多于方程数，系统欠定，存在无穷多解。
4. 因此合谋客户端无法唯一确定目标掩码，进而无法从聚合结果中分离目标梯度。

**极限情况**：$k = n-1$ 时，只剩 1 个未知掩码，可由零和约束唯一确定。这是信息论下界，任何基于线性掩码的方案都无法抵抗 $n-1$ 合谋。

### 4.3 与当前代码的关系

当前代码实现（`ckks_fed_robustness`）中，TEE 路径暂未实现盲化掩码。原因：
- 掩码需要 KGC 参与和额外的密钥分发基础设施。
- 在实验验证阶段，优先保证核心流程（TEE 聚合 + Prefetch）的正确性。
- 掩码逻辑可通过 `TEEProcessor` 的扩展接口无缝接入，不影响现有架构。

---

## 5 扩展讨论：DP 噪声注入

当前方案未在加密前添加 DP 噪声，但架构支持正交增强。

### 5.1 注入位置

在 `client.py::local_train()` 返回 `model_update` 后、调用 `encrypt_model_update()` 之前，插入噪声模块：

```python
# 当前代码（无噪声）
model_update = {name: param.data - old_params[name] for name in params}

# 增强后（添加高斯噪声）
model_update = {name: param.data - old_params[name] for name in params}
model_update = add_gaussian_noise(model_update, epsilon, delta, sensitivity)
```

### 5.2 与 CKKS 的兼容性

CKKS 的近似算术对 DP 噪声有特殊影响：
- **正向作用**：CKKS 的编码舍入误差（$\approx 1/\Delta$）与 DP 噪声在统计上不可区分，可视为 "免费" 的额外隐私保护。
- **限制因素**：CKKS 的噪声预算限制了可注入的 DP 噪声幅度。若 DP 噪声过大，可能导致密文解密后超出有效精度范围。

### 5.3 推荐配置

| 场景 | DP 机制 | 噪声规模 | 精度损失 |
|------|---------|----------|----------|
| 高隐私 | 本地高斯 DP | $\sigma = 2.0$ | 3-5% |
| 均衡 | 中央 DP + 裁剪 | $\sigma = 0.5$ | 1-2% |
| 高精度 | 无 DP | — | 0% |

---

## 6 威胁矩阵总结

| 威胁 | 攻击者 | 影响 | 防御机制 | 安全等级 |
|------|--------|------|----------|----------|
| 服务器窥探单客户端梯度 | 半诚实 Server | 隐私泄露 | RLWE + $sk$ 隔离在 TEE | **计算安全** |
| 客户端窥探其他客户端梯度 | 半诚实 Client | 隐私泄露 | 聚合 "淹没" 效应 | $n$ 较小时脆弱 |
| $n-1$ 客户端合谋 | 合谋 Clients | 完全泄露 | 盲化掩码（扩展） | **信息论上界** |
| 恶意服务器篡改权重 | 恶意 Server | 模型偏差 | TEE 内密封验证 | TEE 被攻破时失效 |
| 恶意服务器伪造 delta | 恶意 Server | 客户端偏离 | 数字签名（扩展） | 签名密钥安全时有效 |
| 选择性丢弃更新 | 恶意 Server | 收敛变慢 | 客户端精度监控 | 无法密码学检测 |
| TEE 侧信道攻击 | 物理攻击者 | $sk$ / 梯度泄露 | 恒定时间 + 噪声注入 | 高级侧信道仍可能 |
| 预取 delta 中间人篡改 | 网络攻击者 | 客户端模型损坏 | HTTPS + 可选签名 | 证书被劫持时失效 |

---

## 参考文献

[1] J. H. Cheon, A. Kim, M. Kim, and Y. Song, "Homomorphic encryption for arithmetic of approximate numbers," in *Proc. ASIACRYPT*, 2017, pp. 409–437.

[2] Y. Li et al., "FedPHE: A Secure and Efficient Federated Learning via Packed Homomorphic Encryption," *IEEE Trans. Dependable Secure Comput.*, 2025.

[3] K. Bonawitz et al., "Practical secure aggregation for privacy-preserving machine learning," in *Proc. CCS*, 2017, pp. 1175–1191.

[4] B. McMahan et al., "Communication-efficient learning of deep networks from decentralized data," in *Proc. AISTATS*, 2017.
