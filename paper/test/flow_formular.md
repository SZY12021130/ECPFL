# TEE-Free CipherFetch: 基于 ESHE 的去可信执行环境密文预取隐私保护框架

> **核心创新**：将 ESAFL [25-ESAFL] 的高效安全同态加密 ESHE 与 CipherFetch 的密文预取机制深度融合，构建**无需 TEE** 的端到端隐私保护联邦学习框架。预取 delta 全程以 ESHE 密文形式流转，客户端本地即可完成跨轮解密与模型同步。
>
> ⚠️ **v2 → v3 更新**：
> - **v2**：针对 ESAFL 全参与假设，提出 ESHE-PS 修正（所有 N 个客户端上传密文），给出基于 $C^{(r)} - C^{(r-1)}$ 密文减法的闭环推导。
> - **v3**：引入**全局掩码投票（GMV）**机制协调 batch 位置对齐；区分 **SIMULATION 模式**（TenSEAL 单密钥，当前代码实现）与 **NATIVE 模式**（真正多密钥 ESHE，未来扩展）；重写闭环公式推导以反映 SIMULATION 模式下直接复用聚合密文作为 delta 的设计。

---

## 符号表（Notation）

### 系统实体

| 符号 | 含义 | 说明 |
|------|------|------|
| $\mathcal{K}$ | 密钥生成中心 (KGC) | 可信，初始化后永久离线 |
| $\mathcal{S}$ | 聚合服务器 (AS) | **不可信**（半诚实或恶意） |
| $\mathcal{C}_i$ | 第 $i$ 个客户端 | $i \in [N] = \{1, 2, \ldots, N\}$ |
| $N$ | 客户端总数 | 跨 silo 场景通常 $N = 10 \sim 50$ |
| $S_r$ | 第 $r$ 轮选中的客户端集合 | $S_r \subseteq [N]$，采样率 $\rho = |S_r| / N$ |
| $\rho$ | 客户端采样率 | 如 $\rho = 0.5$ 表示每轮选一半客户端 |

### 密码学参数

| 符号 | 含义 | 说明 |
|------|------|------|
| $n$ | RLWE 维度 | 多项式环 $R = \mathbb{Z}[X]/(X^n + 1)$ 的维度，通常为 2 的幂次 |
| $q$ | 密文模数 | 2 的幂次，如 $q = 2^{60}$ |
| $p$ | 明文模数 | $p < q$，如 $p = 2^{40}$ |
| $R_q$ | 密文多项式环 | $\mathbb{Z}_q[X]/(X^n + 1)$ |
| $R_p$ | 明文多项式环 | $\mathbb{Z}_p[X]/(X^n + 1)$ |
| $\chi_s$ | 密钥采样分布 | 如三元分布 $\{-1, 0, 1\}$ |
| $\chi_e$ | 误差分布 | 高斯分布 $\mathcal{N}(0, \sigma^2)$ |
| $B$ | PRG 秘密种子 | $B \in [0, 1]^k$，用于生成分轮伪随机多项式 |
| $\lambda$ | 安全参数 | 决定密钥长度和噪声幅度 |
| $pk$ | 公钥 | 用于加密 |
| $sk$ | 私钥 | 用于解密（SIMULATION 模式下所有客户端共享） |
| $evk$ | 评估密钥 | 用于同态运算 |

### ESHE 密钥（NATIVE 模式）

| 符号 | 含义 | 公式/说明 |
|------|------|----------|
| $s_i$ | 客户端 $i$ 的独立加密密钥 | $s_i \leftarrow \chi_s$ |
| $s$ | 共享解密密钥 | $s = \left[\sum_{i=1}^N s_i\right]_q$ |
| $a_0$ | 初始公共多项式 | $a_0 \leftarrow U(R_q)$，均匀随机采样 |
| $a^{(t)}$ | 第 $t$ 轮伪随机多项式 | $a^{(t)} = \text{PRPG}(t, B)$，所有客户端本地独立生成 |

### 模型与梯度

| 符号 | 含义 | 公式/说明 |
|------|------|----------|
| $w^{(r)}$ | 第 $r$ 轮全局模型 | $w^{(r)} = w^{(r-1)} + \eta \cdot G_{\text{agg}}^{(r)}$ |
| $g_i^{(r)}$ | 客户端 $i$ 第 $r$ 轮本地梯度 | $g_i^{(r)} \leftarrow \text{LocalTrain}(D_i, w^{(r-1)}, E)$ |
| $\tilde{g}_i^{(r)}$ | 稀疏化后的梯度 | $\tilde{g}_i^{(r)} = \text{TopK}(g_i^{(r)} + r_i^{(r)})$ |
| $G_{\text{agg}}^{(r)}$ | 第 $r$ 轮聚合梯度 | $G_{\text{agg}}^{(r)} = \sum_{i \in S_r} w_i \cdot \tilde{g}_i^{(r)}$ |
| $r_i^{(r)}$ | 客户端 $i$ 第 $r$ 轮残差 | 误差反馈机制（PTopk）累积的未上传梯度 |
| $\eta$ | 学习率 | 全局模型更新步长 |
| $E$ | 本地训练 epoch 数 | 每轮客户端本地训练的轮数 |
| $D_i$ | 客户端 $i$ 的本地数据集 | $|D_i|$ 表示样本数量 |
| $w_i$ | FedAvg 权重 | $w_i = |D_i| / \sum_{j \in S_r} |D_j|$ |
| $d$ | 模型参数量 | 神经网络总参数个数 |

### 密文相关

| 符号 | 含义 | 说明 |
|------|------|------|
| $c_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮的上传密文 | ESHE 加密格式 |
| $C^{(t)}$ | 第 $t$ 轮聚合密文 | $C^{(t)} = \sum_{i=1}^N c_i^{(t)}$（NATIVE 模式） |
| $\Delta^{(r)}$ | 第 $r$ 轮聚合密文（SIMULATION） | $\Delta^{(r)} = \sum_{i \in S_r} w_i \cdot c_i^{(r)}$ |
| $\delta^{(r)}$ | 第 $r$ 轮 delta 密文 | 预取的基本单元 |
| $e^{(t)}$ | 第 $t$ 轮聚合误差 | $e^{(t)} = \sum_i e_i$ |
| $M^{(t)}$ | 第 $t$ 轮聚合明文 | $M^{(t)} = \sum_i m_i$ |
| $\text{Enc}$ | 加密算法 | ESHE 加密：$\text{Enc}(a, s_i, m) = [a \cdot s_i + p \cdot e + m]_q$ |
| $\text{Dec}$ | 标准解密算法 | $\text{Dec}(a, s, c) = [[c - a \cdot s]_q]_p$ |
| $\text{ExtDec}$ | 扩展解密算法 | 用于跨轮线性组合密文的解密 |
| $\text{PRPG}$ | 伪随机多项式生成器 | $a^{(t)} = \text{PRPG}(t, B)$ |
| $\text{PRNG}$ | 伪随机数生成器 | 用于盲化掩码生成 |

### 全局掩码投票（GMV）

| 符号 | 含义 | 说明 |
|------|------|------|
| $B$ | 总 batch 数 | 模型参数按 slot 打包后的 batch 数量 |
| $b$ | batch 索引 | $b \in [B] = \{0, 1, \ldots, B-1\}$ |
| $m_i^{(r)}$ | 客户端 $i$ 的本地 TopK 掩码 | $m_i^{(r)}[b] \in \{0, 1\}$ |
| $m_{\text{global}}^{(r)}$ | 第 $r$ 轮全局掩码 | 服务器聚合后的统一掩码 |
| $\gamma$ | 全局掩码稀疏度系数 | Union 模式下 $\gamma \approx 1.5 \sim 2$ |

### 预取相关

| 符号 | 含义 | 说明 |
|------|------|------|
| $\text{ct}_{\text{prefetch},k}$ | 客户端 $k$ 的预取密文累加器 | 同态累加所有接收到的 delta |
| $\mathcal{R}_k$ | 客户端 $k$ 错过的轮次集合 | $\mathcal{R}_k = \{r_{\text{sync},k}+1, \ldots, r_{\text{curr}}-1\}$ |
| $r_{\text{sync},k}$ | 客户端 $k$ 上次同步轮次 | 上次被选中训练的轮次 |
| $r_{\text{curr}}$ | 当前轮次 | 客户端 $k$ 本次被选中训练的轮次 |
| $r_{\text{first},k}$ | 客户端 $k$ 首次预取轮次 | 开始接收预取的轮次 |
| $r_{\text{last},k}$ | 客户端 $k$ 最后预取轮次 | 最近一次接收预取的轮次 |
| $w_{\text{base},k}$ | 客户端 $k$ 的 base 模型 | 上次同步时的全局模型快照 |
| $w_{\text{sync},k}$ | 同步后的模型 | 预取解密并应用后的最新模型 |
| $G_{\text{cum},k}$ | 客户端 $k$ 的累积梯度 | $G_{\text{cum},k} = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}$ |

### 跨轮累积量（NATIVE 模式）

| 符号 | 含义 | 公式 |
|------|------|------|
| $\Delta a_k$ | 跨轮 $a$ 的累积差 | $\Delta a_k = a^{(r_{\text{curr}}-1)} - a^{(r_{\text{sync},k})}$ |
| $\Delta e_k$ | 跨轮误差的累积差 | $\Delta e_k = e^{(r_{\text{curr}}-1)} - e^{(r_{\text{sync},k})}$ |

### 安全与防御

| 符号 | 含义 | 说明 |
|------|------|------|
| $b_i^{(r)}$ | 客户端 $i$ 第 $r$ 轮的盲化掩码 | 成对零和掩码，$\sum_i b_i^{(r)} = 0$ |
| $\text{com}_i^{(r)}$ | 梯度承诺 | $\text{com} = H(\tilde{g}_i^{(r)} \| r \| \text{nonce})$ |
| $H$ | 密码学哈希函数 | 如 SHA-256 |
| $\sigma_i^{(r)}$ | 客户端 $i$ 的签名 | 对密文的数字签名 |
| $\pi_i^{(r)}$ | 范围证明 | 证明梯度范数在合法范围内 |
| $t$ | 阈值签名门限 | 阈值 $(t, N)$ 签名方案中的门限 |

### 复杂度参数

| 符号 | 含义 | 说明 |
|------|------|------|
| $M$ | 训练总轮数 | 联邦学习总通信轮数 |
| $n$ | RLWE 维度 | 同时影响密文大小和计算量 |
| $\gamma$ | 全局掩码稀疏度系数 | 实际通信量 = 理论量 $\times \gamma$ |

---

## 1 符号与预备知识

### 1.1 系统实体

| 实体 | 符号 | 信任假设 | 职责 |
|------|------|----------|------|
| **密钥生成中心 (KGC)** | $\mathcal{K}$ | 可信，初始化后永久离线 | 生成 ESHE 参数、分发密钥 |
| **聚合服务器 (AS)** | $\mathcal{S}$ | **不可信**（半诚实或恶意） | 收集密文、同态聚合、调度预取、维护密文历史 |
| **客户端** | $\mathcal{C}_i, i \in [N]$ | 半诚实或恶意 | 本地训练、ESHE 加密上传、接收预取、本地解密同步 |

### 1.2 ESHE 密码学参数

ESAFL [25-ESAFL] 提出的 ESHE 是基于 RLWE 的加法同态加密：

| 参数 | 符号 | 说明 |
|------|------|------|
| RLWE 维度 | $n$ | 多项式环 $R = \mathbb{Z}[X]/(X^n + 1)$ 的维度 |
| 密文模数 | $q$ | 2 的幂次 |
| 明文模数 | $p$ | $p < q$ |
| 秘密密钥分布 | $\chi_s$ | 密钥采样分布（如三元分布） |
| 误差分布 | $\chi_e$ | 高斯分布 $\mathcal{N}(0, \sigma^2)$ |
| PRG 种子参数 | $B \in [0, 1]^k$ | 伪随机多项式生成器的秘密种子 |

**核心多项式环**：
$$R_q = \mathbb{Z}_q[X]/(X^n + 1), \quad R_p = \mathbb{Z}_p[X]/(X^n + 1)$$

### 1.3 模型与梯度符号

| 符号 | 含义 | 公式 |
|------|------|------|
| $w^{(r)}$ | 第 $r$ 轮训练后的全局模型 | $w^{(r)} = w^{(r-1)} + \eta \cdot G_{\text{agg}}^{(r)}$ |
| $g_i^{(r)}$ | 客户端 $i$ 第 $r$ 轮本地梯度 | $\text{LocalTrain}(D_i, w^{(r-1)})$ |
| $G_{\text{agg}}^{(r)}$ | 第 $r$ 轮聚合梯度 | $\sum_{i \in S_r} g_i^{(r)}$ |
| $\tilde{g}_i^{(r)}$ | 客户端 $i$ 稀疏化后的梯度 | $\text{TopK}(g_i^{(r)} + r_i^{(r)})$ |
| $r_i^{(r)}$ | 客户端 $i$ 第 $r$ 轮残差 | 误差反馈机制 |

### 1.4 ESHE 密钥

| 符号 | 含义 | 生成方式 |
|------|------|----------|
| $\{s_i\}_{i \in [N]}$ | 客户端 $i$ 的**独立加密密钥** | $s_i \leftarrow \chi_s$ |
| $s$ | **共享解密密钥** | $s = \left[\sum_{i=1}^N s_i\right]_q$ |
| $a_0$ | 初始公共多项式 | $a_0 \leftarrow U(R_q)$ |
| $B$ | PRG 秘密参数 | $B \leftarrow U([0, 1]^k)$ |
| $a^{(t)}$ | 第 $t$ 轮伪随机多项式 | $a^{(t)} = \text{PRPG}(t, B)$ |

**PRPG 算法**（ESAFL）：
$$a^{(t)} = \text{Vec2Poly}\left(\text{PRG}\left((x_1 \oplus b_1) \| \cdots \|(x_k \oplus b_k)\right)\right)$$
其中 $(x_1 \| \cdots \| x_k)_2 = t$，$(b_1 \| \cdots \| b_k)_2 = B$。

> **关键性质**：所有客户端共享相同的 $B$，因此可以**本地独立生成**任意轮次的 $a^{(t)}$，无需交互。

---

## 2 当前方案回顾与问题分析

### 2.1 现有 CipherFetch/PAMP 框架

```
KGC ──sk, pk, evk──▶ Server(TEE)
           └────────▶ Client (pk, evk only)
```

**流程**：
1. 客户端用 pk 加密梯度 → 上传服务器
2. **TEE 内**解密 → PTopk 稀疏化 → 重新加密
3. 预取 delta 密文下发给未选中客户端
4. 客户端累加 delta，同步时 TEE 辅助解密

### 2.2 核心问题

| 问题 | 根因 | 影响 |
|------|------|------|
| **依赖 TEE** | sk 密封在 TEE 内 | 硬件部署复杂、侧信道风险、内存受限 |
| **单点失效** | KGC 泄露 sk → 全系统暴露 | 历史密文全部可解密 |
| **服务器-客户端共谋** | 服务器有 TEE 控制权 + 客户端可请求解密 | 可恢复明文聚合结果 |
| **预取 delta 非标准密文** | delta = ct_agg^(t) - ct_agg^(t-1) 是 CKKS 密文差分 | 需 TEE 内部处理 |
| **PTopk 必须在明文执行** | TopK 选择非同态操作 | 强制引入解密步骤 |

### 2.3 ESAFL 的局限：全参与假设

ESAFL 原文明确指出：

> "an aggregation ciphertext of **partial clients'** local ciphertexts **cannot be correctly decrypted**"

**根本原因**：解密密钥 $s = \sum_{i=1}^N s_i$ 是**全部 N 个客户端**加密密钥的和。若仅子集 $S_t \subset [N]$ 参与聚合：

$$C^{(t)} = \sum_{i \in S_t} c_i^{(t)} = \left[a^{(t)} \cdot \sum_{i \in S_t} s_i + p \cdot e^{(t)} + M^{(t)}\right]_q$$

用完整的 $s = \sum_{i=1}^N s_i$ 解密：

$$C^{(t)} - a^{(t)} \cdot s = \left[a^{(t)} \cdot \left(\sum_{i \in S_t} s_i - \sum_{i=1}^N s_i\right) + p \cdot e^{(t)} + M^{(t)}\right]_q = \left[-a^{(t)} \cdot \sum_{i \notin S_t} s_i + p \cdot e^{(t)} + M^{(t)}\right]_q$$

**巨大的"剩余密钥"项** $-a^{(t)} \cdot \sum_{i \notin S_t} s_i$ 导致解密完全失败。

**ESAFL 的假设场景**：cross-silo，N=9，**所有客户端每轮都参与**。这与 CipherFetch 的客户端采样（N=30，采样率 0.5）**直接冲突**。

### 2.4 ESHE-PS：适配客户端采样的关键修正

**核心思想**：每轮**所有 N 个客户端**上传密文，但**未采样客户端加密零向量**。

$$
c_i^{(r)} = \begin{cases}
\left[a^{(r)} \cdot s_i + p \cdot e_i + \tilde{g}_i^{(r)}\right]_q & i \in S_r \text{（采样，传真实梯度）} \\
\left[a^{(r)} \cdot s_i + p \cdot e_i + \mathbf{0}\right]_q & i \notin S_r \text{（未采样，传零向量）}
\end{cases}
$$

聚合后：

$$C^{(r)} = \sum_{i=1}^N c_i^{(r)} = \left[a^{(r)} \cdot s + p \cdot e^{(r)} + G_{\text{agg}}^{(r)}\right]_q$$

其中 $G_{\text{agg}}^{(r)} = \sum_{i \in S_r} \tilde{g}_i^{(r)}$（未采样客户端贡献为 0）。

**关键优势**：
- 聚合密文恢复标准 ESHE 形式，可用 $s$ 正常解密
- 扩展解密（跨轮线性组合）仍然有效
- 预取 delta 机制正常工作

**通信开销**：
- 原始 CipherFetch + 采样率 $\rho=0.5$：$\rho N = 15$ 个密文/轮
- ESHE-PS：$N = 30$ 个密文/轮
- **上行开销增加 $1/\rho = 2\times$**

**对于 cross-silo 场景（N=10~50）**：2x 开销完全可接受。未采样客户端只需加密零向量，计算量极小（无需本地训练）。

### 2.5 ESHE-PS 带来的机会

ESAFL [25-ESAFL] 的 ESHE 算法具有**天然支持跨轮密文线性组合**的性质（Theorem 2）：

> 给定跨轮聚合密文 $\tilde{C}^{(t)} = [C^{(t)} - c_i^{(t)} + c_i^{(\tau)}]_q$，其解密结果在计算上不可区分于均匀随机分布。

在 ESHE-PS 中，$C^{(t)}$ 和 $C^{(\tau)}$ 都包含完整的 $a^{(t)} \cdot s$ 和 $a^{(\tau)} \cdot s$ 项，跨轮线性组合性质**保持成立**。

**这意味着**：ESHE-PS 密文可以像向量一样做线性组合（系数为 $\pm 1$），且组合后的密文仍可用扩展解密恢复。

### 2.6 全局掩码投票（Global Mask Vote）

**问题**：在标准稀疏化中，每个客户端独立选择 TopK batch，导致不同客户端的 `mask` 不同。服务器聚合时无法直接对齐 batch 位置，解密后会出现位置错位。

**解决方案**：引入全局掩码投票，让服务器协调所有客户端在**相同的 batch 位置**上传密文。

**流程**：

1. **本地 TopK 掩码**：每个选中客户端 $i \in S_r$ 计算自己的 TopK 位置，编码为二进制掩码 $m_i \in \{0,1\}^{B}$（$B$ 为总 batch 数）
2. **掩码上传**：客户端上传轻量掩码 $m_i$（~$B$ bytes，可忽略）
3. **服务器聚合**：根据投票模式生成全局掩码 $m_{\text{global}}$：
   - **Union**：$m_{\text{global}}[b] = \bigvee_{i \in S_r} m_i[b]$（并集）
   - **Threshold**：$m_{\text{global}}[b] = \mathbf{1}\left[\sum_{i} m_i[b] \geq \theta \cdot |S_r|\right]$（阈值）
   - **TopK-count**：取被选中次数最多的 $K$ 个 batch
4. **广播**：服务器将 $m_{\text{global}}$ 广播给所有选中客户端
5. **对齐加密**：客户端按 $m_{\text{global}}$ 加密——全局掩码为 1 的位置上传真实梯度（若该位置在本地 TopK 中）或零向量（若不在本地 TopK 中）

**效果**：所有客户端在相同 batch 位置有密文，服务器聚合后的密文可直接解密，无需处理位置错位。

**开销**：全局掩码通常比单个客户端的 TopK 更密集（Union 模式下约 $1 - (1-\rho)^k$ 的 batch 被选中），通信量增加 $1.5\sim 2\times$。

### 2.7 SIMULATION 模式与 NATIVE 模式

当前 TenSEAL 库不原生支持 ESAFL 的多密钥注入（$a^{(r)} \cdot s_i$），因此实现分为两模式：

| 模式 | 密钥管理 | 扩展解密 | 未采样客户端 | 适用场景 |
|------|----------|----------|-------------|----------|
| **SIMULATION** | 单密钥 CKKS，所有客户端共享 $(pk, sk)$ | 退化为标准 CKKS 解密（$\Delta a = 0$） | **无需上传**零密文 | 当前代码实现 |
| **NATIVE** | 多密钥 ESHE，每个客户端持独立 $s_i$ | 真正的扩展解密（$\Delta a = \sum \alpha_j a^{(r_j)}$） | **必须上传**零密文（ESHE-PS） | 未来 C++ 库实现 |

**SIMULATION 模式的安全性**：
- 所有客户端共享同一个 $sk$ → 任何客户端可解密其他客户端的单个密文
- 缓解方案：启用成对盲化掩码（blinding_mask），使单个密文解密后为 $\tilde{g}_i + b_i$，无法分离真实梯度
- 聚合后掩码自抵消：$\sum_i b_i = 0$

**本文档后续公式推导以 NATIVE 模式为理论基准，同时在关键处标注 SIMULATION 模式的简化形式。**

---

## 3 ESHE 密码学原语（精简定义）

### 3.1 算法元组

$$\text{ESHE} = (\text{Setup}, \text{KeyGen}, \text{PRPG}, \text{Enc}, \text{Dec}, \text{Eval})$$

### 3.2 密钥生成

$$\text{KeyGen}(pp) \rightarrow (\{s_i\}_{i \in [N]}, s, a_0, B)$$

- $s_i \leftarrow \chi_s$：客户端 $i$ 的独立加密密钥
- $s = \left[\sum_{i=1}^N s_i\right]_q$：共享解密密钥
- $a_0 \leftarrow U(R_q)$：初始公共多项式
- $B \leftarrow U([0, 1]^k)$：PRG 秘密种子

### 3.3 伪随机多项式生成

$$a^{(t)} = \text{PRPG}(t, B)$$

所有客户端本地生成，无需通信。

### 3.4 加密

$$c_i^{(t)} = \text{Enc}(a^{(t)}, s_i, m_i) = \left[a^{(t)} \cdot s_i + \tilde{p} \cdot e_i + m_i\right]_q$$

其中 $\tilde{p}$ 是全系数为 $p$ 的常数多项式，$e_i \leftarrow \chi_e$。

### 3.5 聚合（同态求和）

$$C^{(t)} = \text{Eval}\left(\{c_i^{(t)}\}_{i \in S_t}\right) = \sum_{i \in S_t} c_i^{(t)}$$

展开：
$$C^{(t)} = \left[a^{(t)} \cdot s + \tilde{p} \cdot e^{(t)} + M^{(t)}\right]_q$$

其中 $e^{(t)} = \sum_{i \in S_t} e_i$，$M^{(t)} = \sum_{i \in S_t} m_i$。

### 3.6 标准解密

$$M = \text{Dec}(a^{(t)}, s, C^{(t)}) = \left[\left[C^{(t)} - a^{(t)} \cdot s\right]_q\right]_p$$

验证：
$$\begin{aligned}
\left[C^{(t)} - a^{(t)} \cdot s\right]_q &= \left[a^{(t)} \cdot s + \tilde{p} \cdot e^{(t)} + M^{(t)} - a^{(t)} \cdot s\right]_q \\
&= \left[\tilde{p} \cdot e^{(t)} + M^{(t)}\right]_q
\end{aligned}$$

取模 $p$：$\left[\tilde{p} \cdot e^{(t)} + M^{(t)}\right]_p = M^{(t)}$（当 $\|e^{(t)}\|_\infty < p/2$ 时）

### 3.7 跨轮线性组合密文的扩展解密（核心创新）

**定理（ESAFL Theorem 2 扩展）**：设 $C^{(t_1)}, C^{(t_2)}, \ldots, C^{(t_k)}$ 为 $k$ 个不同轮次的聚合密文，定义线性组合：

$$C_{\text{mix}} = \left[\sum_{j=1}^k \alpha_j \cdot C^{(t_j)}\right]_q, \quad \alpha_j \in \{-1, 0, 1\}$$

则 $C_{\text{mix}}$ 可通过**扩展解密**恢复：

$$M_{\text{mix}} = \text{ExtDec}(\{a^{(t_j)}\}, \{\alpha_j\}, s, C_{\text{mix}}) = \left[\left[C_{\text{mix}} - \left(\sum_{j=1}^k \alpha_j \cdot a^{(t_j)}\right) \cdot s\right]_q\right]_p$$

**证明**：
$$\begin{aligned}
C_{\text{mix}} &= \left[\sum_j \alpha_j \left(a^{(t_j)} \cdot s + \tilde{p} \cdot e^{(t_j)} + M^{(t_j)}\right)\right]_q \\
&= \left[\left(\sum_j \alpha_j \cdot a^{(t_j)}\right) \cdot s + \tilde{p} \cdot \left(\sum_j \alpha_j \cdot e^{(t_j)}\right) + \left(\sum_j \alpha_j \cdot M^{(t_j)}\right)\right]_q
\end{aligned}$$

因此：
$$\begin{aligned}
&\left[C_{\text{mix}} - \left(\sum_j \alpha_j \cdot a^{(t_j)}\right) \cdot s\right]_q \\
=& \left[\tilde{p} \cdot \left(\sum_j \alpha_j \cdot e^{(t_j)}\right) + \left(\sum_j \alpha_j \cdot M^{(t_j)}\right)\right]_q
\end{aligned}$$

取模 $p$ 得 $M_{\text{mix}} = \sum_j \alpha_j \cdot M^{(t_j)}$。$\square$

> **关键洞察**：客户端知道 $B$，可本地生成任意 $a^{(t)}$，因此可以解密**任意跨轮线性组合密文**，无需 TEE 参与。

---

## 4 TFCF 框架设计

### 4.1 系统架构

```
┌─────────────┐     初始化     ┌─────────────────────┐
│    KGC      │──────────────▶│  公共参数 pp=(n,p,q) │
│  (离线)     │               │  a0, B, {si}, s     │
└─────────────┘               └─────────────────────┘
         │                           │
         │  si, s, a0, B              │ a0, B
         ▼                           ▼
┌─────────────────┐            ┌──────────────┐
│   客户端 Ci     │◀───────────│   服务器 S   │
│ (si, s, a0, B)  │   密文     │  (无 sk/si)  │
└─────────────────┘   预取     └──────────────┘
```

**核心区别**：
- 服务器**不持有任何密钥份额**（无 sk，无 si）
- 所有解密操作在**客户端本地**完成
- 预取 delta 是 ESHE 密文，可跨轮累加

### 4.2 Phase 0：初始化

**KGC 执行**：

$$(pp, \{s_i\}_{i \in [N]}, s, a_0, B) \leftarrow \text{ESHE.KeyGen}(1^\lambda)$$

分发：
$$\begin{aligned}
(s_i, s, a_0, B) &\rightarrow \mathcal{C}_i \quad \text{(安全通道)} \\
(a_0, B) &\rightarrow \mathcal{S} \quad \text{(公开通道)}
\end{aligned}$$

KGC 销毁所有密钥材料，永久离线。

### 4.3 Phase 1：训练、投票与加密（ESHE-PS + GMV）

**（采样客户端 $i \in S_r$）**：

**(1) 本地训练**：
$$g_i^{(r)} \leftarrow \text{LocalTrain}(D_i, w^{(r-1)}, E)$$

**(2) 残差补偿与稀疏化**：
$$\tilde{g}_i^{(r)} = \text{TopK}\left(g_i^{(r)} + r_i^{(r)}\right)$$

---

**全局掩码投票子阶段（GMV）**：

**(3a) 本地掩码计算**：每个选中客户端计算本地 TopK 位置的二进制掩码
$$m_i^{(r)}[b] = \begin{cases} 1 & \text{if batch } b \text{ in } \text{TopK}(\tilde{g}_i^{(r)}) \\ 0 & \text{otherwise} \end{cases}, \quad b \in [B]$$

**(3b) 掩码上传**：选中客户端上传轻量掩码 $m_i^{(r)}$（~$B$ bytes）
$$\mathcal{C}_i \rightarrow \mathcal{S}: \quad m_i^{(r)}, \quad \forall i \in S_r$$

**(3c) 服务器聚合全局掩码**（以 Union 模式为例）：
$$m_{\text{global}}^{(r)}[b] = \bigvee_{i \in S_r} m_i^{(r)}[b] = \mathbf{1}\left[\sum_{i \in S_r} m_i^{(r)}[b] \geq 1\right]$$

**(3d) 广播全局掩码**：
$$\mathcal{S} \rightarrow \mathcal{C}_i: \quad m_{\text{global}}^{(r)}, \quad \forall i \in S_r$$

---

**(4) 对齐加密（按全局掩码）**：

**（采样客户端 $i \in S_r$）**：生成轮次伪随机多项式 $a^{(r)} = \text{PRPG}(r, B)$，按全局掩码加密：

$$c_i^{(r)}[b] = \begin{cases}
\left[a^{(r)} \cdot s_i + \tilde{p} \cdot e_i + \tilde{g}_i^{(r)}[b]\right]_q & \text{if } m_{\text{global}}^{(r)}[b] = 1 \text{ and } m_i^{(r)}[b] = 1 \\
\left[a^{(r)} \cdot s_i + \tilde{p} \cdot e_i + \mathbf{0}\right]_q & \text{if } m_{\text{global}}^{(r)}[b] = 1 \text{ and } m_i^{(r)}[b] = 0 \\
\text{skip} & \text{if } m_{\text{global}}^{(r)}[b] = 0
\end{cases}$$

> **SIMULATION 模式简化**：未采样客户端 $j \notin S_r$ **无需上传**零密文。单密钥共享 $sk$ 已满足解密约束，服务器可直接聚合选中客户端密文。
>
> **NATIVE 模式**：未采样客户端必须上传零密文：
> $$c_j^{(r)} = \left[a^{(r)} \cdot s_j + \tilde{p} \cdot e_j + \mathbf{0}\right]_q, \quad \forall j \notin S_r$$

**(5) 客户端上传服务器**：
$$\mathcal{C}_i \rightarrow \mathcal{S}: \quad c_i^{(r)}, \quad \forall i \in S_r \text{ (SIMULATION)} \text{ 或 } \forall i \in [N] \text{ (NATIVE)}$$

### 4.4 Phase 2：服务器聚合与预取

**服务器 $\mathcal{S}$ 在第 $r$ 轮**：

**(1) 同态聚合**：

**NATIVE 模式**（全部 $N$ 个密文）：
$$C^{(r)} = \sum_{i=1}^N c_i^{(r)} = \left[a^{(r)} \cdot s + \tilde{p} \cdot e^{(r)} + G_{\text{agg}}^{(r)}\right]_q$$

**SIMULATION 模式**（仅选中客户端密文）：
$$\Delta^{(r)} = \sum_{i \in S_r} w_i \cdot c_i^{(r)} = \left[a^{(r)} \cdot s + \tilde{p} \cdot e^{(r)} + G_{\text{agg}}^{(r)}\right]_q$$
其中 $w_i = |D_i| / \sum_{j \in S_r} |D_j|$ 为 FedAvg 权重。由于单密钥共享，$\sum_{i \in S_r} w_i \cdot s_i = s$（当 $w_i$ 归一化时）。

**(2) 计算 Delta 密文**：

**NATIVE 模式**（理论基准）：
$$\delta^{(r)} = \left[C^{(r)} - C^{(r-1)}\right]_q$$
通过密文同态减法得到纯梯度更新，扩展解密需累积 $\Delta a = a^{(r)} - a^{(r-1)}$。

**SIMULATION 模式**（当前实现）：
$$\delta^{(r)} = \Delta^{(r)} = \sum_{i \in S_r} w_i \cdot c_i^{(r)}$$
在 `upload_difference=true` 模式下，聚合密文 $\Delta^{(r)}$ **本身就是**本轮梯度更新 $G_{\text{agg}}^{(r)}$ 的加密形式，可直接作为预取 delta，**无需计算 $C^{(r)} - C^{(r-1)}$**。

> **为何省略同态减法？** TenSEAL 的 `CKKSVector` 对象共享同一个 context 的内部状态（如重线性化密钥）。`+`/`-` 操作会修改 context 状态，导致保存的 $C^{(r-1)}$ 在 $C^{(r)}$ 被创建后也发生变化，使得 $C^{(r)} - C^{(r-1)}$ 退化为全零（transparent ciphertext）。直接复用聚合密文 $\Delta^{(r)}$ 作为 delta 避免了这一问题，且数学上等价（在 upload_difference 模式下）。
>
> **关键**：SIMULATION 模式下 delta 密文可直接用标准 CKKS 解密，无需扩展解密（因为单密钥无 per-round $a^{(r)}$ 项需要校正）。

**(3) 广播预取**（仅给本轮未选中客户端）：
$$\mathcal{S} \rightarrow \mathcal{C}_j, \quad \forall j \notin S_r: \quad \delta^{(r)}$$

### 4.5 Phase 3：客户端预取累加

**所有客户端 $k \in [N]$**：

**(1) 接收并累加 delta**（若 $k$ 本轮未选中）：
$$\text{ct}_{\text{prefetch},k} \leftarrow \text{ct}_{\text{prefetch},k} + \delta^{(r)}$$

**(2) 更新预取记录**（若 $k$ 本轮未选中）：
$$\begin{aligned}
r_{\text{last},k} &\leftarrow r \\
\text{if } r_{\text{first},k} = \text{None}: &\quad r_{\text{first},k} \leftarrow r
\end{aligned}$$

---

## 5 完整闭环公式推导（v3）

### 5.1 预取密文展开（基于聚合梯度 delta）

设客户端 $k$ 上次同步轮次为 $r_{\text{sync},k}$，当前被选中轮次为 $r_{\text{curr}}$。

**定义 delta 密文**：

**NATIVE 模式**：
$$\delta^{(r)} = \left[C^{(r)} - C^{(r-1)}\right]_q$$

**SIMULATION 模式**（当前实现）：
$$\delta^{(r)} = \Delta^{(r)} = \sum_{i \in S_r} w_i \cdot c_i^{(r)}$$
其中 $\Delta^{(r)}$ 是本轮聚合梯度 $G_{\text{agg}}^{(r)}$ 的密文形式。

---

**预取累加器**：
$$\text{ct}_{\text{prefetch},k} = \sum_{r \in \mathcal{R}_k} \delta^{(r)}$$

其中 $\mathcal{R}_k = \{r_{\text{sync},k}+1, \ldots, r_{\text{curr}}-1\}$ 是客户端 $k$ 在同步期间错过的轮次集合。

---

**SIMULATION 模式展开**：

$$\begin{aligned}
\text{ct}_{\text{prefetch},k} &= \sum_{r \in \mathcal{R}_k} \Delta^{(r)} \\
&= \sum_{r \in \mathcal{R}_k} \text{Enc}\left(G_{\text{agg}}^{(r)}\right) \\
&= \text{Enc}\left(\sum_{r \in \mathcal{R}_k} G_{\text{agg}}^{(r)}\right)
\end{aligned}$$

由于 `upload_difference=true` 时全局模型更新为：
$$w^{(r)} = w^{(r-1)} + \eta \cdot G_{\text{agg}}^{(r)}$$

累积梯度：
$$\sum_{r \in \mathcal{R}_k} G_{\text{agg}}^{(r)} = \frac{1}{\eta}\left(w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}\right)$$

当 $\eta = 1$ 时：
$$\sum_{r \in \mathcal{R}_k} G_{\text{agg}}^{(r)} = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}$$

因此：
$$\boxed{\text{ct}_{\text{prefetch},k} = \text{Enc}\left(w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}\right)}$$

---

**NATIVE 模式展开**（理论基准）：

$$\begin{aligned}
\text{ct}_{\text{prefetch},k} &= \sum_{r=r_{\text{sync},k}+1}^{r_{\text{curr}}-1} \left[C^{(r)} - C^{(r-1)}\right]_q \\
&= \left[C^{(r_{\text{curr}}-1)} - C^{(r_{\text{sync},k})}\right]_q
\end{aligned}$$

代入 $C^{(r)}$ 的展开式：
$$\begin{aligned}
\text{ct}_{\text{prefetch},k} &= \Bigg[\left(a^{(r_{\text{curr}}-1)} \cdot s + \tilde{p} \cdot e^{(r_{\text{curr}}-1)} + G_{\text{agg}}^{(r_{\text{curr}}-1)}\right) \\
&\quad - \left(a^{(r_{\text{sync},k})} \cdot s + \tilde{p} \cdot e^{(r_{\text{sync},k})} + G_{\text{agg}}^{(r_{\text{sync},k})}\right)\Bigg]_q \\
&= \Bigg[\underbrace{\left(a^{(r_{\text{curr}}-1)} - a^{(r_{\text{sync},k})}\right)}_{\Delta a_k} \cdot s + \tilde{p} \cdot \underbrace{\left(e^{(r_{\text{curr}}-1)} - e^{(r_{\text{sync},k})}\right)}_{\Delta e_k} \\
&\quad + \underbrace{\left(G_{\text{agg}}^{(r_{\text{curr}}-1)} - G_{\text{agg}}^{(r_{\text{sync},k})}\right)}_{G_{\text{cum},k}}\Bigg]_q
\end{aligned}$$

其中 $G_{\text{cum},k} = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}$。

### 5.2 定义累积量

**SIMULATION 模式**：
$$\begin{aligned}
G_{\text{cum},k} &= \sum_{r \in \mathcal{R}_k} G_{\text{agg}}^{(r)} = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})} \\
\text{ct}_{\text{prefetch},k} &= \text{Enc}\left(G_{\text{cum},k}\right)
\end{aligned}$$

**NATIVE 模式**：
$$\begin{aligned}
\Delta a_k &= a^{(r_{\text{curr}}-1)} - a^{(r_{\text{sync},k})} \\
\Delta e_k &= e^{(r_{\text{curr}}-1)} - e^{(r_{\text{sync},k})} \\
G_{\text{cum},k} &= w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}
\end{aligned}$$

$$\boxed{\text{ct}_{\text{prefetch},k} = \left[\Delta a_k \cdot s + \tilde{p} \cdot \Delta e_k + G_{\text{cum},k}\right]_q}$$

### 5.3 客户端解密

**SIMULATION 模式**（标准 CKKS 解密）：

由于所有客户端共享同一个 $sk$，且 delta 密文就是标准 CKKS 密文（无 per-round $a^{(r)}$ 项需要校正），解密退化为标准操作：

$$\begin{aligned}
G_{\text{cum},k} &= \text{Dec}(sk, \text{ct}_{\text{prefetch},k}) \\
&= \text{Dec}\left(sk, \sum_{r \in \mathcal{R}_k} \text{Enc}\left(G_{\text{agg}}^{(r)}\right)\right) \\
&= \sum_{r \in \mathcal{R}_k} G_{\text{agg}}^{(r)} \\
&= w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}
\end{aligned}$$

> **关键简化**：SIMULATION 模式下无需扩展解密（ExtDec），因为单密钥无跨轮 $a^{(r)}$ 累积项。客户端直接用 TenSEAL 的 `decrypt()` 即可。

**NATIVE 模式**（扩展解密）：

客户端 $k$ 知道 $B$，本地生成 $a^{(r_{\text{curr}}-1)}$ 和 $a^{(r_{\text{sync},k})}$，计算 $\Delta a_k$。

$$\begin{aligned}
G_{\text{cum},k} &= \text{ExtDec}(\Delta a_k, s, \text{ct}_{\text{prefetch},k}) \\
&= \left[\left[\text{ct}_{\text{prefetch},k} - \Delta a_k \cdot s\right]_q\right]_p \\
&= \left[\left[\tilde{p} \cdot \Delta e_k + G_{\text{cum},k}\right]_q\right]_p \\
&\approx G_{\text{cum},k}
\end{aligned}$$

### 5.4 模型同步

**通用形式**（两种模式相同）：

$$w_{\text{sync},k} = w_{\text{base},k} + \eta \cdot G_{\text{cum},k}$$

代入 $w_{\text{base},k} = w^{(r_{\text{sync},k})}$ 和 $G_{\text{cum},k} = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}$：

$$w_{\text{sync},k} = w^{(r_{\text{sync},k})} + \eta \cdot \left(w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})}\right)$$

当 $\eta = 1$ 时：
$$\boxed{w_{\text{sync},k} = w^{(r_{\text{curr}}-1)}}$$

**客户端模型同步到最新全局模型**。

### 5.5 完整闭环公式链

$$\begin{aligned}
&\textbf{训练:} && g_i^{(r)} \leftarrow \text{LocalTrain}(D_i, w^{(r-1)}, E) \\
&\textbf{残差+稀疏化:} && \tilde{g}_i^{(r)} = \text{TopK}(g_i^{(r)} + r_i^{(r)}) \\
&\textbf{本地掩码:} && m_i^{(r)}[b] = \mathbf{1}[b \in \text{TopK}(\tilde{g}_i^{(r)})] \\
&\textbf{全局掩码投票:} && m_{\text{global}}^{(r)} = \text{Vote}(\{m_i^{(r)}\}_{i \in S_r}) \\
&\textbf{PRG:} && a^{(r)} = \text{PRPG}(r, B) \\
&\textbf{ESHE加密(采样):} && c_i^{(r)} = \text{Enc}\left(a^{(r)}, s_i, \tilde{g}_i^{(r)} \odot m_{\text{global}}^{(r)}\right) \quad (i \in S_r) \\
&\textbf{ESHE加密(未采样, NATIVE):} && c_j^{(r)} = \text{Enc}(a^{(r)}, s_j, \mathbf{0}) \quad (j \notin S_r) \\
&\textbf{聚合(NATIVE):} && C^{(r)} = \sum_{i=1}^N c_i^{(r)} = \left[a^{(r)} \cdot s + \tilde{p} \cdot e^{(r)} + G_{\text{agg}}^{(r)}\right]_q \\
&\textbf{聚合(SIMULATION):} && \Delta^{(r)} = \sum_{i \in S_r} w_i \cdot c_i^{(r)} = \text{Enc}\left(G_{\text{agg}}^{(r)}\right) \\
&\textbf{Delta(NATIVE):} && \delta^{(r)} = \left[C^{(r)} - C^{(r-1)}\right]_q \\
&\textbf{Delta(SIMULATION):} && \delta^{(r)} = \Delta^{(r)} = \text{Enc}\left(G_{\text{agg}}^{(r)}\right) \\
&\textbf{预取:} && \text{ct}_{\text{prefetch},k} = \sum_{r \in \mathcal{R}_k} \delta^{(r)} \\
&\textbf{Fetch:} && \text{if missing: } \text{ct}_{\text{prefetch},k} \leftarrow \text{ct}_{\text{prefetch},k} + \sum_{r \notin \mathcal{R}_k} \delta^{(r)} \\
&\textbf{解密(SIMULATION):} && G_{\text{cum},k} = \text{Dec}(sk, \text{ct}_{\text{prefetch},k}) = w^{(r_{\text{curr}}-1)} - w^{(r_{\text{sync},k})} \\
&\textbf{解密(NATIVE):} && G_{\text{cum},k} = \text{ExtDec}(\Delta a_k, s, \text{ct}_{\text{prefetch},k}) \\
&\textbf{同步:} && w_{\text{sync},k} = w_{\text{base},k} + \eta \cdot G_{\text{cum},k} = w^{(r_{\text{curr}}-1)} \\
&\textbf{训练:} && g_k^{(r_{\text{curr}})} \leftarrow \text{LocalTrain}(D_k, w_{\text{sync},k}, E)
\end{aligned}$$

---

## 6 威胁模型与安全性分析

### 6.1 系统威胁模型

| 威胁 | 攻击者 | 能力 |
|------|--------|------|
| **半诚实服务器** | $\mathcal{S}$ | 遵循协议但试图从密文推断隐私 |
| **半诚实客户端** | $\mathcal{C}_j$ | 遵循协议但试图推断其他客户端梯度 |
| **客户端合谋** | $\{\mathcal{C}_i\}_{i \in \mathcal{I}}, |\mathcal{I}| < N-1$ | 共享信息联合推断 |
| **服务器-客户端合谋** | $\mathcal{S} + \mathcal{C}_j$ | 服务器提供密文，客户端提供密钥 |
| **恶意客户端** | $\mathcal{C}_m$ | 上传错误梯度/密文、伪造数据 |
| **恶意服务器** | $\mathcal{S}^*$ | 篡改聚合权重、伪造预取、选择性丢弃 |

### 6.2 半诚实服务器安全

**定理 1（对服务器的语义安全）**：对于任意 PPT 敌手 $\mathcal{A}$，给定等长明文梯度 $\mathbf{g}_0, \mathbf{g}_1$ 和挑战密文 $c^* \leftarrow \text{Enc}(a, s_i, \mathbf{g}_b)$，敌手输出猜测 $b'$ 的优势满足：
$$\left|\Pr[b' = b] - \frac{1}{2}\right| \leq \text{negl}(\lambda)$$

**证明**：直接由 ESAFL Theorem 1 [25-ESAFL]，ESHE 在 RLWE 假设下是 IND-CPA 安全的。服务器仅持有 $a_0, B$（公开参数），不持有任何 $s_i$ 或 $s$，无法区分密文与随机。$\square$

**推论**：服务器无法从预取 delta 密文 $\delta^{(r)}$ 中恢复任何信息。

### 6.3 半诚实客户端安全

**定理 2（单客户端隔离）**：单个半诚实客户端 $\mathcal{C}_j$ 无法恢复其他客户端的个体梯度。

**证明**：
- $\mathcal{C}_j$ 持有 $s_j$ 和 $s$，可以解密聚合密文 $C^{(r)}$
- 解密后得到 $G_{\text{agg}}^{(r)} = \sum_{i \in S_r} \tilde{g}_i^{(r)}$，是聚合结果
- 单个客户端梯度被"淹没"在聚合中
- 当 $|S_r| \geq 2$ 时，$\mathcal{C}_j$ 无法从 $G_{\text{agg}}^{(r)}$ 中分离出 $\tilde{g}_i^{(r)}$（$i \neq j$）

**局限**：若 $|S_r| = 1$（仅一个客户端被选中），$\mathcal{C}_j$ 若被选中则可恢复自己的梯度，这无意义；若 $\mathcal{C}_j$ 未被选中但窃听到仅一个客户端的聚合密文，则知道该客户端的梯度。**解决方案**：每轮至少选择 2 个客户端，或引入盲化掩码（见 6.7 节）。$\square$

### 6.4 客户端合谋安全

**定理 3（$< N-1$ 客户端合谋安全）**：任意 $< N-1$ 个客户端合谋无法恢复其他客户端的加密密钥或明文。

**证明**：直接由 ESAFL Theorem 5 [25-ESAFL]。

给定 $N-2$ 个合谋客户端的明文 $\{m_k\}_{k \in [N-2]}$ 和解密密钥 $s$，定义分布：
$$D = \{(s_i, e_i, m_i) : i \in \{N-1, N\}\}$$

由于 $s_{N-1} + s_N = s - \sum_{k=1}^{N-2} s_k$ 固定，$s_{N-1}$ 和 $s_N$ 服从高斯分布（Theorem 4 [25-ESAFL]）。在 RLWE 假设下，$m_{N-1}$ 和 $m_N$ 的计算分布与均匀随机分布不可区分。$\square$

### 6.5 服务器-客户端合谋安全

**定理 4（服务器-单客户端合谋）**：服务器 $\mathcal{S}$ 与单个客户端 $\mathcal{C}_j$ 合谋，无法恢复其他客户端的个体梯度。

**分析**：
- 合谋后拥有：所有密文 $\{c_i^{(r)}\}$ + $s_j$ + $s$
- 可解密聚合密文 $C^{(r)}$，得到 $G_{\text{agg}}^{(r)}$
- 但 $\mathcal{C}_j$ 知道自身梯度 $\tilde{g}_j^{(r)}$，可从聚合中减去：
  $$G_{\text{agg}}^{(r)} - \tilde{g}_j^{(r)} = \sum_{i \in S_r, i \neq j} \tilde{g}_i^{(r)}$$
- 仍无法分离出单个 $\tilde{g}_i^{(r)}$

**残余风险**：若 $|S_r| = 2$ 且 $\mathcal{C}_j$ 是其中之一，则可精确恢复另一个客户端的梯度。

**缓解方案**：引入盲化掩码（见 6.7 节），即使合谋也无法去掩。$\square$

### 6.6 恶意客户端防御：同态 Hash + 承诺

**攻击**：恶意客户端 $\mathcal{C}_m$ 可能：
- 上传伪造梯度（如模型投毒）
- 上传错误密文（如加密随机噪声而非梯度）

**防御方案 A：梯度承诺（Commitment）**

客户端在加密前计算梯度承诺：
$$\text{com}_i^{(r)} = \text{H}(\tilde{g}_i^{(r)} \| r_i^{(r)} \| r)$$

其中 H 是密码学哈希函数，$r_i^{(r)}$ 是随机 nonce。

上传：$(c_i^{(r)}, \text{com}_i^{(r)})$

服务器在聚合后验证：
$$\text{com}_i^{(r)} \stackrel{?}{=} \text{H}(\text{Decode}(\text{Decrypt}(c_i^{(r)})) \| r_i^{(r)} \| r)$$

**问题**：服务器无 sk，无法解密验证。

**改进方案 B：同态 Hash 验证**

利用 CKKS/ESHE 的同态性质，服务器可在密文上验证哈希：

1. 客户端计算 $\text{com}_i^{(r)} = \text{H}(\tilde{g}_i^{(r)})$
2. 客户端将 $\text{com}_i^{(r)}$ 作为明文附加到加密包中
3. 服务器聚合后，随机抽查部分客户端
4. 被抽查客户端向服务器**证明**其密文对应的明文哈希等于承诺

**更实用的方案 C：零知识范围证明 + 签密**

受 DSVFL [26-Ftopk] 启发：

1. 客户端本地训练后，计算梯度的 L2 范数范围证明：$\|\tilde{g}_i\|_2 \in [L, U]$
2. 客户端用私钥 $sk_i^{\text{sign}}$ 对密文签名：$\sigma_i^{(r)} = \text{Sign}(sk_i^{\text{sign}}, c_i^{(r)} \| r)$
3. 上传 $(c_i^{(r)}, \sigma_i^{(r)}, \pi_i^{(r)})$，其中 $\pi_i^{(r)}$ 是范围证明
4. 服务器验证签名和范围证明，拒绝异常上传

**效果**：恶意客户端无法上传任意大/小的梯度而不被检测。

### 6.7 盲化掩码（增强客户端间保密性）

受 FedPHE [25-FedPHE] 启发，引入成对盲化掩码：

KGC 为每对客户端 $(i, j)$ 生成共享种子 $seed_{i,j} = seed_{j,i}$。

客户端 $i$ 第 $r$ 轮的掩码：
$$b_i^{(r)} = \frac{1}{w_i} \sum_{j \neq i} \text{sgn}(i-j) \cdot \text{PRNG}(seed_{i,j}, r)$$

加密上传：
$$c_i^{(r)} = \text{Enc}(a^{(r)}, s_i, \tilde{g}_i^{(r)} + b_i^{(r)})$$

聚合后：
$$C^{(r)} = \text{Enc}\left(a^{(r)}, s, G_{\text{agg}}^{(r)} + \sum_{i \in S_r} b_i^{(r)}\right)$$

**关键性质**：当所有客户端参与时，$\sum_i b_i^{(r)} = 0$（掩码自抵消）。

**当部分客户端参与时**（如客户端采样），服务器需额外传输聚合掩码补偿值，或客户端通过 Shamir 秘密共享恢复部分掩码和。

**安全性提升**：
- 即使 $\mathcal{S} + \mathcal{C}_j$ 合谋，也无法从 $G_{\text{agg}}^{(r)} + \sum b_i^{(r)}$ 中恢复单个梯度
- 需要**所有**客户端合谋才能抵消掩码

### 6.8 恶意服务器防御：聚合验证

**攻击**：恶意服务器 $\mathcal{S}^*$ 可能：
- **权重篡改**：修改聚合权重，给特定客户端更高/更低权重
- **预取伪造**：向客户端发送错误的 $\delta^{(r)}$
- **选择性丢弃**：排除某些客户端的更新
- **延迟攻击**：不向特定客户端发送预取

**防御方案 A：可验证聚合（Verifiable Aggregation）**

受 DSVFL [26-Ftopk] 的 SCSA 协议启发：

1. 客户端 $i$ 加密上传 $c_i^{(r)}$ 后，保留梯度哈希 $\text{H}(\tilde{g}_i^{(r)})$
2. 服务器广播聚合结果 $C^{(r)}$ 和参与集合 $S_r$
3. 客户端在解密后验证：
   $$\text{H}\left(\text{Decode}(\text{Dec}(s, C^{(r)}))\right) \stackrel{?}{=} \text{H}\left(\sum_{i \in S_r} \tilde{g}_i^{(r)}\right)$$

**问题**：客户端不知道其他客户端的梯度，无法验证聚合正确性。

**改进方案 B：阈值签名 + 共识**

1. 每个客户端 $i$ 对本轮聚合结果签名：$\sigma_i = \text{Sign}(sk_i^{\text{sign}}, \text{H}(C^{(r)}))$
2. 收集至少 $t$ 个签名后，聚合结果被认为是"已验证的"
3. 客户端只接受带有效阈值签名的预取 delta

**改进方案 C：客户端侧聚合验证（Ftopk 动态验证）**

受 DSVFL [26-Ftopk] 启发：

1. 服务器发布聚合密文 $C^{(r)}$ 和权重 $\{w_i\}$
2. 每个客户端 $i$ 计算验证份额：$v_i = w_i \cdot \tilde{g}_i^{(r)}$
3. 客户端通过安全通道交换验证份额（Shamir 秘密共享保护）
4. 组合验证：$\sum v_i \stackrel{?}{=} \text{Dec}(s, C^{(r)})$

**实际部署建议**：
- 在跨 silo 场景（机构间），各机构有声誉约束，恶意服务器行为可被审计
- 引入**区块链日志**：服务器每轮将聚合结果哈希上链，不可篡改
- 定期审计：随机轮次要求服务器提供聚合轨迹证明

---

## 7 TEE 去除分析

### 7.1 当前方案为何需要 TEE

| 步骤 | 操作 | 为何需要 TEE |
|------|------|-------------|
| PTopk 稀疏化 | 在明文上执行 TopK 选择 | 需要解密聚合密文 |
| 预取 delta 解密 | 将 delta 密文转为明文 | 需要 sk |
| 全局模型更新 | 明文模型 + 明文 delta | 需要 sk 解密 |
| 重新加密 | 用 pk 加密更新后的模型 | 无需 TEE，但紧接解密步骤 |

### 7.2 TFCF 如何去除 TEE

**核心替代**：将**服务器端解密**转移到**客户端本地解密**。

| 步骤 | 当前方案（含 TEE） | TFCF（无 TEE） |
|------|-------------------|----------------|
| 密钥持有 | sk 密封在 TEE | $s = \sum s_i$，每个客户端持 $s_i$ 和 $s$ |
| 聚合密文解密 | TEE 内用 sk 解密 | 客户端本地用 $s$ 解密 |
| PTopk 稀疏化 | TEE 内明文执行 | **客户端本地**解密后执行 |
| 预取 delta 解密 | TEE 内用 sk 解密 | 客户端本地扩展解密（第 3.7 节） |
| 全局模型更新 | TEE 内明文更新 | 客户端本地明文更新 |

### 7.3 PTopk 的替代方案

PTopk 需要在明文上执行 TopK 选择，这是去除 TEE 的主要障碍。

**方案 A：客户端侧 PTopk（推荐）**

1. 服务器聚合后，**不解密**，直接将聚合密文 $C^{(r)}$ 广播给所有客户端
2. 每个客户端本地解密 $C^{(r)}$，得到 $G_{\text{agg}}^{(r)}$
3. 客户端本地执行 TopK 稀疏化，得到稀疏聚合梯度
4. 客户端用稀疏梯度更新本地模型

**通信开销**：每轮需要广播聚合密文给所有客户端（而非仅选中客户端），但预取机制减少了这部分开销。

**方案 B：服务器辅助的密文稀疏化**

利用 CKKS 的 SIMD 性质，服务器在密文上执行"近似 TopK"：
1. 服务器维护一个稀疏掩码模式（基于历史 TopK 位置）
2. 将掩码模式编码为明文多项式
3. 同态乘法：$C^{(r)}_{\text{sparse}} = C^{(r)} \odot \text{mask}$

**局限**：精确 TopK 需要比较操作，非同态。近似方案可能损失精度。

**方案 C：盲化掩码 + 服务器解密（折中）**

若必须保留服务器端明文操作：
1. 客户端上传加盲梯度：$c_i^{(r)} = \text{Enc}(\tilde{g}_i^{(r)} + b_i^{(r)})$
2. 引入**阈值解密**：将 $s$ 分成 $(t, N)$ 份，需要 $t$ 个客户端参与才能解密
3. 服务器收集 $t$ 个部分解密份额，组合后得到明文 $G_{\text{agg}}^{(r)} + \sum b_i^{(r)}$
4. 服务器通过 Shamir 恢复 $\sum b_i^{(r)}$（需要所有客户端的掩码份额）
5. 去掩后执行 PTopk

**结论**：此方案重新引入了交互，失去了 ESHE 一步解密的效率优势。

### 7.4 去除 TEE 的代价

| 维度 | 含 TEE | 无 TEE (TFCF) |
|------|--------|---------------|
| **硬件依赖** | Intel SGX/AMD SEV | 无 |
| **信任假设** | 硬件可信 | 密码学保证（RLWE） |
| **单点失效** | TEE 漏洞可导致 sk 泄露 | 无单一实体持有完整密钥 |
| **通信开销** | 低（TEE 本地解密） | 中（客户端本地解密） |
| **PTopk 执行位置** | 服务器 TEE | 客户端本地 |
| **服务器-客户端共谋** | 可攻破 TEE | 仅能恢复聚合结果 |
| **部署复杂度** | 高（TEE + 远程证明） | 低（纯软件） |

### 7.5 为什么在某些场景下仍需要 TEE

**场景 1：服务器必须执行复杂非线性操作**

若聚合后需要执行非线性函数（如 ReLU、Softmax 在全局模型上），同态加密无法直接支持。此时需要解密，若不允许任何客户端看到全局梯度，则 TEE 是必要的隔离环境。

**场景 2：监管要求**

某些行业（金融、医疗）要求服务器在"可信环境"中处理数据，即使密码学上安全，监管可能要求硬件级隔离。

**场景 3：客户端不可信**

若客户端可能恶意泄露解密后的聚合梯度，而服务器需要保护模型知识产权，则 TEE 可确保服务器端操作的机密性。

**本文立场**：

> **TFCF 在跨 silo FL 场景下可完全替代 TEE**。跨 silo 场景中，各机构（客户端）本身需要看到聚合结果以更新模型，且机构间有声誉约束。ESHE 的密码学安全性（IND-CPA + 抗 $< N-1$ 合谋）已足够强。
>
> **TEE 仅在以下情况不可替代**：服务器需执行非线性操作、监管强制硬件隔离、或模型知识产权需保护。

---

## 8 复杂度分析

### 8.1 计算复杂度

设 $N$ 为客户端数，$M$ 为训练轮数，$d$ 为模型参数量，$n$ 为 RLWE 维度。

| 阶段 | TFCF | 当前 CKKS+TEE | ESAFL [25-ESAFL] |
|------|------|---------------|------------------|
| 客户端加密 | $O(N \cdot M \cdot n)$ | $O(N \cdot M \cdot n)$ | $O(N \cdot M \cdot n)$ |
| 服务器聚合 | $O(N \cdot M \cdot n)$ | $O(N \cdot M \cdot n)$ | $O(N \cdot M \cdot n)$ |
| 解密 | $O(M \cdot n)$（每客户端） | $O(M \cdot n)$（TEE 内） | $O(M \cdot n)$（每客户端） |
| **总计算** | $O(3N \cdot M \cdot n + N \cdot M)$ | $O(3N \cdot M \cdot n + N \cdot M)$ | $O(3N \cdot M \cdot n + N \cdot M)$ |

**与 MKHE 对比**（FedPHE [25-FedPHE] 等）：
- MKHE [15]：$O(3(N+1)N \cdot M \cdot n + N \cdot M)$
- MKHE [16]：$O(7N \cdot M \cdot n + N \cdot M)$
- **TFCF / ESHE**：$O(3N \cdot M \cdot n + N \cdot M)$（线性于 $N$）

### 8.2 通信复杂度

| 方向 | TFCF (ESHE-PS) | 当前 CKKS+TEE |
|------|----------------|---------------|
| 客户端→服务器 | $O(N \cdot M \cdot n)$（**所有 N 个**客户端上传） | $O(\rho N \cdot M \cdot n)$（仅采样客户端上传，$\rho=0.5$） |
| 服务器→客户端（预取） | $O((1-\rho) N \cdot M \cdot n)$ | $O((1-\rho) N \cdot M \cdot n)$ |
| 解密交互 | **0**（本地解密） | 0（TEE 本地） |
| **总通信** | $O(N \cdot M \cdot n)$ | $O(\rho N \cdot M \cdot n)$ |

> **注意**：ESHE-PS 要求所有 $N$ 个客户端上传密文（采样传梯度、未采样传零），上行通信比采样方案多 $1/\rho$ 倍（如 $\rho=0.5$ 时多 2x）。对于 cross-silo 场景（$N=10\sim 50$），这是可接受的代价。

### 8.3 与相关工作对比

| 方案 | 密钥类型 | 抗合谋 | 预取支持 | TEE 依赖 | 通信复杂度 |
|------|----------|--------|----------|----------|------------|
| **当前 CipherFetch** | 单密钥 CKKS | ❌ | ✅ | ✅ | $O(\rho N M n)$ |
| **FedPHE [25-FedPHE]** | 单密钥 CKKS | ❌ | ❌ | ❌ | $O(NMn)$ |
| **ESAFL [25-ESAFL]** | ESHE（全参与） | $< N-1$ | ❌ | ❌ | $O(NMn)$ |
| **SSCKKS-tn [本文]** | $(t,N)$ 阈值 | $< t$ | ✅ | ❌ | $O(NMn + tNMn)$ |
| **TFCF-ESHE-PS (NATIVE)** | ESHE + 全上传 + 扩展解密 | $< N-1$ | ✅ | ❌ | $O(NMn)$ |
| **TFCF-ESHE-PS (SIMULATION)** | 单密钥 CKKS + 全局掩码投票 | ⚠️ 需盲化掩码 | ✅ | ❌ | $O(\rho N M n \cdot \gamma)$ |

> **SIMULATION 模式说明**：当前代码实现基于 TenSEAL 单密钥。抗合谋性弱于 NATIVE 模式（共享 $sk$ 导致任何客户端可解密单个密文），需依赖成对盲化掩码（blinding_mask）增强隐私。通信复杂度中 $\gamma$ 为全局掩码稀疏度系数（Union 模式下 $\gamma \approx 1.5\sim 2$）。

---

## 9 安全性定理汇总

**定理 1（IND-CPA）**：ESHE 在 RLWE 假设下是 IND-CPA 安全的。（ESAFL Theorem 1）

**定理 2（多轮隐私）**：ESHE 支持跨轮密文线性组合的安全聚合。（ESAFL Theorem 2 扩展）

**定理 3（抗合谋）**：TFCF 抵抗任意 $< N-1$ 个客户端的合谋攻击。（ESAFL Theorem 5）

**定理 4（服务器无知性）**：服务器无法从任何密文（包括预取 delta）中恢复明文信息。（由定理 1 直接得到）

**定理 5（扩展解密正确性）**：客户端可通过 ExtDec 正确恢复跨轮线性组合密文中的累积梯度。（第 3.7 节证明）

---

## 10 总结

本文提出 **TEE-Free CipherFetch (TFCF)** 及其采样适配版本 **ESHE-PS**，一种基于 ESAFL-ESHE 的去可信执行环境密文预取隐私保护框架。

**关键修正**：ESAFL 原始 ESHE 要求所有 $N$ 个客户端参与聚合（$s = \sum_{i=1}^N s_i$），与客户端采样机制冲突。本文提出 **ESHE-PS**：所有客户端每轮上传密文（采样传梯度、未采样传零），保持聚合密文可解密性，同时兼容预取。对于 cross-silo 场景（$N=10\sim 50$），2x 上行开销是可接受的代价。

**核心贡献**：
1. **识别并修正** ESAFL ESHE 的**全参与假设**与客户端采样的根本冲突，提出 ESHE-PS 适配方案
2. **提出全局掩码投票（GMV）**：协调所有客户端在相同 batch 位置上传密文，解决独立稀疏化导致的聚合错位问题
3. **首次**将 ESHE 的跨轮密文线性组合性质应用于联邦学习预取场景，实现预取 delta 全程密文保护
4. **区分 SIMULATION/NATIVE 双模式**：SIMULATION 模式基于 TenSEAL 单密钥实现，可立即部署；NATIVE 模式保留真正多密钥 ESHE 的理论完备性
5. **无需 TEE**，所有解密操作在客户端本地完成，消除硬件依赖和侧信道风险
6. **完整的闭环公式推导（v3）**，覆盖两种模式的训练、投票、加密、聚合、预取、解密、模型同步全流程
7. **综合威胁模型分析**，覆盖半诚实/恶意服务器、半诚实/恶意客户端、各类合谋攻击，并提出同态 Hash + 盲化掩码 + 聚合验证的防御体系

**未来工作**：
- 实现 ESHE 的 C++ 高效库（类似 ESAFL），替代当前 Python/TenSEAL 原型，支持 NATIVE 模式
- 探索**紧凑零密文**优化：未采样客户端的密钥项 $a^{(r)} \cdot s_j$ 可通过 PRPG 本地复用，仅需重采样误差多项式
- 探索全同态加密（FHE）扩展，支持非线性聚合函数
- 设计适用于 TFCF 的高效同态稀疏化算法，避免客户端侧 PTopk 的全模型下载

---

## 参考文献

- [25-ESAFL] Wu et al., "ESAFL: Efficient Secure Additively Homomorphic Encryption for Cross-Silo Federated Learning," IEEE TDSC, 2025.
- [25-FedPHE] Li et al., "FedPHE: A Secure and Efficient Federated Learning via Packed Homomorphic Encryption," IEEE TDSC, 2025.
- [25-FedFetch] Yan et al., "FedFetch: Faster Federated Learning with Adaptive Downstream Prefetching," IEEE INFOCOM, 2025.
- [24-ResFed] Song et al., "ResFed: Communication Efficient Federated Learning with Deep Compressed Residuals," IEEE IoT Journal, 2023.
- [26-Ftopk] Li et al., "Enhancing Federated Learning in Edge Computing With Secure Aggregation and Dynamic Verification," IEEE TMC, 2026.
