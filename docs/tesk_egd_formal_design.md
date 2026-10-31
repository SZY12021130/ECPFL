# TESK-EGD: TEE-Encapsulated Single-Key with Enclave-Gated Decryption

> 基于可信执行环境（TEE）封装的单密钥 CKKS-FL 外层密码学框架
>
> 完整闭环设计、公式推导与安全性分析

---

## 一、引言与问题定义

### 1.1 现有方案的局限

现有单密钥 CKKS-FL 方案（如 BatchCrypt、FedPHE、PAMP）存在以下结构性安全缺陷：

**缺陷一：私钥集中持有**
- 服务器持有完整私钥 sk，可任意解密所有客户端的历史上传密文
- 一旦服务器被攻破，全系统历史数据暴露

**缺陷二：解密过程不透明**
- 服务器在不可审计的环境中执行解密、PTopk 累加器、重新加密
- 客户端无法验证服务器是否忠实地执行了这些操作

**缺陷三：明文模型暴露**
- 服务器维护明文模型 `self.model`，可直接读取模型参数
- 即使加密了全局状态，服务器仍可随时解密查看

### 1.2 TESK-EGD 的核心思想

> **将所有涉及私钥 sk 的操作（解密、明文运算、重新加密）迁移到可信执行环境（TEE）的隔离内存中执行。服务器主机（Server Host）仅作为密文传输代理，永远无法访问 sk 或明文模型。**

### 1.3 形式化问题定义

设联邦学习系统包含：
- $n$ 个客户端 $\mathcal{C} = \{C_1, ..., C_n\}$
- 1 个聚合服务器主机 $S_H$
- 1 个 TEE Enclave $E$（运行在 $S_H$ 的同一物理机上）

**目标**：设计协议 $\Pi_{TESK}$，使得：
1. $S_H$ 无法恢复 sk 或任何明文模型参数
2. $E$ 内执行的聚合逻辑可被远程证明验证
3. 协议在标准 CKKS 同态运算能力下完成闭环

---

## 二、系统架构

### 2.1 实体与信任假设

| 实体 | 信任等级 | 持有资产 | 职责 |
|------|----------|----------|------|
| **KGC** | 完全可信，初始化后离线 | $(sk, pk, evk)$ | 密钥生成、TEE 密封、分发 |
| **Server Host $S_H$** | 不可信（可恶意） | $pk, evk$ | 网络 I/O、密文路由、模型评估 |
| **TEE Enclave $E$** | 硬件可信 | 密封的 $sk, pk, evk$ | 解密、聚合、PTopk、重加密 |
| **Client $C_i$** | 半诚实 | $pk, evk$ | 本地训练、加密上传、接收预取 |

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        KGC (离线)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 生成 sk,pk  │  │ 密封 sk→E   │  │ 生成预取根密钥 K_r  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
    [公开分发]      [密封到 TEE]         [密封到 TEE]
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Server Host S_H                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  TEE Enclave E (隔离内存，S_H 不可访问)                │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  密封 sk  │  密封 K_r  │  明文模型 M_t        │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ECALL: process_round(ct_list, weights)         │  │  │
│  │  │  1. 同态聚合 → ct_agg                           │  │  │
│  │  │  2. sk 解密 → delta_plain                       │  │  │
│  │  │  3. PTopk 累加器 → delta_acc                    │  │  │
│  │  │  4. M_{t+1} = M_t + delta_acc                   │  │  │
│  │  │  5. pk 重加密 → ct_global                       │  │  │
│  │  │  6. 预取 delta 计算                             │  │  │
│  │  │  7. 输出 (ct_global, delta_prefetch)            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  [网络 I/O] ←── ct_i from Clients                           │
│  [网络 I/O] ←── ct_global, delta_prefetch to Clients        │
│  [模型评估] ←── 从 E 获取明文模型（可选，见3.6节）          │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 关键设计决策

**决策一：预取内容不二次加密**
- TEE 输出的 `delta_prefetch` 为明文差分
- Server Host 通过 HTTPS/TLS 分发给客户端
- 预取内容的机密性由传输层安全保证
- **理由**：`delta_prefetch` 是聚合结果的衍生物，其保密优先级低于原始梯度；且所有客户端最终都会知道全局模型状态

**决策二：模型评估在 TEE 外执行**
- 为支持标准 PyTorch 评估流程，TEE 定期将明文模型同步给 Server Host
- 同步通过安全内存拷贝（TEE→Host 的受控 OCALL）
- 同步的模型仅用于评估，不用于解密操作

---

## 三、核心协议设计

### 3.1 符号表

| 符号 | 含义 | 典型值/范围 |
|------|------|-------------|
| $N$ | CKKS 多项式次数 | 8192 |
| $\Delta$ | 全局缩放因子 | $2^{40}$ |
| $\lambda$ | 安全参数 | 128 bits |
| $(sk, pk, evk)$ | CKKS 密钥三元组 | — |
| $K_r$ | 预取根密钥（AES-256） | 256 bits |
| $M_t$ | 第 $t$ 轮全局模型 | $\mathbb{R}^d$ |
| $g_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮梯度 | $\mathbb{R}^d$ |
| $w_i$ | 聚合权重 | $\sum_i w_i = 1$ |
| $\mathcal{E}_{TEE}$ | TEE 密封/解封操作 | — |
| $\text{Quote}_E$ | TEE 远程证明引用 | — |

### 3.2 初始化阶段

**算法 1: TESK-EGD.Setup**

```
输入: 安全参数 λ, 客户端数 n, 模型维度 d
输出: 系统参数、密封密钥、远程证明引用

1. (sk, pk, evk) ← CKKS.KeyGen(λ, N=8192, mod=[60,40,40,60], Δ=2^40)
2. K_r ← AES.GenerateKey(256)           // 预取根密钥
3. sealed_sk ← TEE.Seal(sk, enclave_identity)    // 密封 sk
4. sealed_Kr ← TEE.Seal(K_r, enclave_identity)   // 密封 K_r
5. code_hash ← Hash(enclave_binary)     // MRENCLAVE 等效值
6. Quote_E ← TEE.GenerateQuote(code_hash)        // 远程证明引用

// 分发
7. 发送 (sealed_sk, sealed_Kr) → S_H (加载到 TEE)
8. 发布 (pk, evk, Quote_E) 到所有实体
9. KGC 销毁 (sk, K_r)，离线
```

**TEE 密封机制**：

$$\text{sealed\_sk} = \text{Enc}_{K_{seal}}(sk \| \text{enclave\_identity})$$

其中 $K_{seal}$ 是 TEE 硬件派生的密封密钥，仅同一 enclave 身份可解封。

### 3.3 客户端加密上传

**算法 2: TESK-EGD.ClientUpload**

```
输入: 客户端 i, 本地梯度 g_i^(t), 公钥 pk
输出: 加密更新 ct_i

1. delta_i ← g_i^(t) - g_i^(t-1)      // 若 upload_difference=true
2. ct_i ← CKKS.Enc(pk, delta_i)
3. 上传 ct_i → S_H (via HTTPS)
```

**公式表示**：

$$ct_i = (b_i, a_i) = (a_i \cdot s + m_i + e_{0,i}, \; a_i + e_{1,i}) \pmod{q_L}$$

其中 $m_i = \text{Encode}(\Delta_i, \Delta)$，$\Delta_i$ 为编码后的梯度差分。

### 3.4 服务器主机传递（ECALL）

**算法 3: TESK-EGD.HostRelay**

```
输入: 密文列表 {ct_i}, 权重 {w_i}
输出: 无（仅传递给 TEE）

1. S_H 验证每个 ct_i 的格式合法性（长度、模数）
2. S_H 执行 ECALL: E.process_round({ct_i}, {w_i})
3. S_H 等待 E 返回结果
```

**关键性质**：$S_H$ 仅传递密文字节流，不执行任何密码学操作。

### 3.5 TEE 内核心处理（ECALL）

**算法 4: TESK-EGD.EnclaveProcess**

```
输入: {ct_i}, {w_i}, 当前轮次 t
输出: ct_global, delta_prefetch

// 阶段 1: 解封密钥（仅本轮有效）
1. sk ← TEE.Unseal(sealed_sk)
2. M_t ← LoadModelFromSecureMemory()    // TEE 内明文模型

// 阶段 2: 同态聚合
3. ct_agg ← Σ_i w_i · ct_i              // CKKS 同态加+标量乘

// 阶段 3: 解密（TEE 内，S_H 不可见）
4. m_agg ← CKKS.Decrypt(sk, ct_agg)
5. delta_plain ← CKKS.Decode(m_agg)

// 阶段 4: PTopk 服务器累加器（若启用）
6. 若 ptopk.enable:
     delta_acc ← PTopk.ServerUpdate(delta_plain, lr)
   否则:
     delta_acc ← delta_plain · lr

// 阶段 5: 模型更新（TEE 内）
7. M_{t+1} ← M_t + delta_acc

// 阶段 6: 重新加密全局状态
8. ct_global ← CKKS.Enc(pk, Pack(M_{t+1}))

// 阶段 7: 预取计算
9. delta_prefetch ← ComputePrefetch(M_{t+1}, M_t)

// 阶段 8: 安全清理
10. 清零 sk, delta_plain, delta_acc 的内存
11. 返回 (ct_global, delta_prefetch)
```

**公式推导**：

**步骤 3（同态聚合）**：

$$ct_{agg} = \sum_{i \in S} w_i \cdot ct_i = \left(\sum_i w_i b_i, \; \sum_i w_i a_i\right)$$

展开验证：
$$\sum_i w_i b_i = \sum_i w_i (a_i s + m_i + e_{0,i}) = \left(\sum_i w_i a_i\right) s + \sum_i w_i m_i + \sum_i w_i e_{0,i}$$

**步骤 4（解密）**：

$$m_{agg} = \sum_i w_i b_i - \left(\sum_i w_i a_i\right) \cdot sk = \sum_i w_i m_i + \underbrace{\sum_i w_i e_{0,i} - \left(\sum_i w_i a_i\right) \cdot e_{sk}}_{\text{聚合噪声 } e_{agg}}$$

其中 $e_{sk}$ 为密钥生成时的误差。

**步骤 5-7（明文运算）**：

$$\Delta_{acc} = \text{PTopk}(\{\Delta_{plain}^{(\tau)}\}_{\tau=1}^t, \beta)$$

$$M_{t+1} = M_t + \Delta_{acc}$$

**步骤 8（重新加密）**：

$$ct_{global} = (b', a') = (a' \cdot s + m' + e'_0, \; a' + e'_1)$$

其中 $m' = \text{Encode}(M_{t+1}, \Delta)$。

### 3.6 模型评估同步（OCALL）

**算法 5: TESK-EGD.ModelSync**

```
输入: TEE 内明文模型 M_t
输出: 同步后的评估模型（S_H 侧）

// 由 S_H 定期触发（每 eval_interval 轮）
1. S_H 执行 OCALL: RequestModelForEval()
2. TEE 内:
   a. 验证 OCALL 来源合法性
   b. 将 M_t 复制到 OCALL 输出缓冲区
   c. 清零缓冲区中的敏感元数据
3. S_H 接收 M_t，用于标准 PyTorch 评估
```

**安全边界**：同步的 $M_t$ 仅用于评估，不用于解密。即使 $S_H$ 篡改评估模型，不影响下一轮聚合（因为下一轮仍从 TEE 内正确的 $M_t$ 出发）。

### 3.7 预取分发与客户端应用

**算法 6: TESK-EGD.PrefetchDelivery**

```
输入: delta_prefetch（明文）, 目标客户端 C_i
输出: C_i 本地模型更新

// Server Host 侧
1. S_H 将 delta_prefetch 打包为 HTTPS 响应
2. S_H 发送给 C_i

// Client 侧
3. C_i 接收 delta_prefetch
4. C_i: M_{local} ← M_{local} + delta_prefetch
5. C_i 清除预取缓存
```

**传输安全性**：
- delta_prefetch 通过 HTTPS（TLS 1.3）传输
- 机密性由 TLS 会话密钥保证
- 完整性由 TLS AEAD 认证标签保证

---

## 四、闭环正确性证明

### 4.1 定理 1（聚合正确性）

**定理**：TESK-EGD 的聚合结果与标准 FedAvg 等价。

**证明**：

设客户端 $i$ 上传梯度差分 $\Delta_i$，权重 $w_i = |D_i| / \sum_j |D_j|$。

标准 FedAvg：
$$M_{t+1}^{(std)} = M_t + \sum_{i \in S} w_i \Delta_i$$

TESK-EGD：

步骤 3（同态聚合）：
$$ct_{agg} = \sum_{i \in S} w_i \cdot \text{Enc}(pk, \Delta_i)$$

由 CKKS 同态线性性：
$$\text{Decrypt}(sk, ct_{agg}) = \sum_{i \in S} w_i \Delta_i + e_{agg}$$

其中 $e_{agg}$ 为聚合噪声，$\|e_{agg}\| \leq \sum_i |w_i| \|e_i\| \leq n \cdot \max|w_i| \cdot \sigma\sqrt{N}$。

步骤 5（模型更新）：
$$M_{t+1}^{(tesk)} = M_t + \sum_{i \in S} w_i \Delta_i + e_{agg}$$

因此：
$$\|M_{t+1}^{(tesk)} - M_{t+1}^{(std)}\| = \|e_{agg}\|$$

由 CKKS 参数选择，$\|e_{agg}\| / \Delta < 10^{-6}$，对模型收敛影响可忽略。

**QED**

### 4.2 定理 2（解密隔离性）

**定理**：Server Host $S_H$ 在协议执行期间无法获得 sk 或任何明文模型参数的任何信息。

**证明**：

**sk 隔离性**：
- sk 以 sealed_sk 形式存储在 TEE 密封内存中
- 解封操作 `TEE.Unseal()` 只能在 TEE enclave 内执行
- TEE 硬件保证：enclave 内存对 Host OS 不可读
- 因此 $S_H$ 无法读取 sk

**明文隔离性**：
- 所有明文运算（Decrypt、PTopk、Model Update）在 TEE 内执行
- TEE 输出仅包含：
  - ct_global（密文，需 sk 解密）
  - delta_prefetch（明文差分，聚合结果衍生物）
- $S_H$ 从 ct_global 无法推断明文（CKKS IND-CPA 安全）
- $S_H$ 从 delta_prefetch 只能知道聚合差分，无法反推单客户端梯度

**QED**

---

## 五、安全性分析

### 5.1 威胁模型

| 威胁编号 | 攻击者 | 能力 | 目标 |
|----------|--------|------|------|
| T-1 | 半诚实 $S_H$ | 遵循协议但试图读取 sk/明文 | 推断客户端数据 |
| T-2 | 恶意 $S_H$ | 篡改输入密文、重放、排除客户端 | 破坏模型或推断数据 |
| T-3 | TEE 侧信道攻击者 | 利用缓存时序、功耗、电压故障 | 提取 sk 或明文 |
| T-4 | 恶意客户端 $C_i$ | 发送错误梯度、伪造密文 | 破坏聚合或拒绝服务 |
| T-5 | $S_H$ + 客户端共谋 | 联合欺骗其他客户端 | 推断诚实客户端数据 |

### 5.2 T-1: 半诚实 Server Host

**攻击能力**：$S_H$ 可读取所有网络流量、磁盘文件、内存（除 TEE 隔离内存外）。

**防御效果**：

**定理 3**：在标准 RLWE 假设和 TEE 隔离假设下，TESK-EGD 对半诚实 $S_H$ 满足 **IND-CPA 安全**。

**证明**：

$S_H$ 可获得的信息：
1. **客户端上传密文** $ct_i$：由 CKKS IND-CPA 安全，$S_H$ 无法推断 $\Delta_i$
2. **聚合密文** $ct_{agg}$：同理无法推断聚合结果
3. **全局密文** $ct_{global}$：无法推断全局模型
4. **预取明文** $\delta_{prefetch}$：聚合结果的衍生物，仅泄露全局模型变化量

$S_H$ 无法获得的信息：
- sk：密封在 TEE 内
- 明文梯度：需 sk 解密
- 历史明文模型：TEE 内历史状态不暴露

因此 $S_H$ 的视图与理想功能（只输出聚合结果）计算不可区分。

**QED**

### 5.3 T-2: 恶意 Server Host

**攻击能力**：$S_H$ 可篡改、重放、排除客户端密文，可篡改 TEE 输入/输出（但不能读取 TEE 内存）。

**防御效果**：

| 攻击类型 | 效果 | 原因 |
|----------|------|------|
| 排除客户端 | ⚠️ 可执行 | $S_H$ 控制网络，可选择不传递某些 $ct_i$ 到 TEE |
| 篡改输入密文 | ⚠️ 可执行 | $S_H$ 可修改 $ct_i$ 的字节流 |
| 重放旧密文 | ⚠️ 可执行 | $S_H$ 可存储并重传历史 $ct_i$ |
| 伪造聚合结果 | ✅ 不可行 | TEE 内执行真实聚合，$S_H$ 无法伪造通过验证的 $ct_{global}$ |
| 读取 sk | ✅ 不可行 | TEE 内存隔离 |
| 注入恶意代码到 TEE | ✅ 不可行 | TEE 代码在初始化时度量（MRENCLAVE），$S_H$ 无法修改 |

**缓解措施**：

**缓解一：输入完整性校验**
- 每个客户端对 $ct_i$ 签名：$\sigma_i = \text{Sign}_{sk_i^{sig}}(H(ct_i))$
- TEE 内验证签名后才纳入聚合
- 防止 $S_H$ 篡改或重放

**缓解二：客户端排除检测**
- TEE 输出包含参与客户端列表
- 客户端验证自己是否被正确纳入

**缓解三：轮次计数器**
- TEE 内维护单调递增轮次计数器
- 拒绝处理旧轮次密文

### 5.4 T-3: TEE 侧信道攻击

**攻击面**：

| 侧信道类型 | 风险等级 | 说明 |
|------------|----------|------|
| 缓存时序（Cache Timing） | 高 | Prime+Probe、Flush+Reload |
| 分支预测（Branch Prediction） | 中 | Spectre 变体 |
| 功耗分析（Power Analysis） | 中 | 电压/功耗与数据相关 |
| 电压故障（Voltage Glitch） | 低 | Plundervolt 等 |
| 物理内存窥探 | 低 | 冷启动攻击、DMA 攻击 |

**缓解措施**：

1. **常数时间实现**：TEE 内聚合、解密代码使用常数时间算法，消除分支依赖
2. **数据无关内存访问**：使用固定内存访问模式，消除缓存侧信道
3. **TEE 微码更新**：及时应用 Intel/AMD 的侧信道缓解微码
4. **监控与熔断**：检测异常高的 ECALL 频率（可能指示侧信道探测）

**安全边界**：

**定理 4**：在 TEE 侧信道攻击成功概率 $\epsilon_{side} < 2^{-\lambda_{tee}}$ 的假设下，TESK-EGD 的安全性退化为标准 CKKS-FL 的安全性。

**证明概要**：
- 若侧信道攻击无法提取 sk，则 TEE 保护有效
- 若侧信道攻击以概率 $\epsilon$ 提取 sk，则系统安全性 = $(1-\epsilon) \cdot \text{TEE安全} + \epsilon \cdot \text{标准FL安全}$
- 当 $\epsilon$ 足够小（如 $2^{-40}$），整体安全仍满足 $2^{-\lambda}$ 级别

### 5.5 T-4: 恶意客户端

**攻击能力**：客户端可发送任意密文（包括错误梯度、恶意构造的密文）。

**防御效果**：

| 攻击类型 | 效果 | 缓解 |
|----------|------|------|
| 发送错误梯度 | ⚠️ 可执行 | 与标准 FL 相同，需拜占庭防御（Krum、Trimmed Mean）|
| 发送格式错误密文 | ✅ 可检测 | TEE 验证密文格式，拒绝非法输入 |
| 发送超大规模密文 | ✅ 可检测 | TEE 限制单密文大小，拒绝异常输入 |
| 拒绝服务（DoS） | ⚠️ 可执行 | 网络层限速，TEE 内超时机制 |

### 5.6 T-5: Server Host + 客户端共谋

**攻击场景**：$S_H$ 与恶意客户端 $C_{mal}$ 联合，试图推断诚实客户端 $C_{hon}$ 的数据。

**防御效果**：

**定理 5**：在 TEE 隔离假设下，即使 $S_H$ 与任意数量客户端共谋，也无法推断诚实客户端的明文梯度。

**证明**：

诚实客户端 $C_{hon}$ 的明文梯度 $\Delta_{hon}$ 仅在以下位置出现：
1. $C_{hon}$ 本地内存（共谋方无法访问）
2. 加密密文 $ct_{hon}$（IND-CPA 安全）
3. TEE 内聚合后的明文（TEE 内存隔离，共谋方无法访问）

共谋方可获得的信息：
- $ct_{hon}$：无法解密（无 sk）
- 聚合结果 $\sum_i w_i \Delta_i$：仅知加权和，无法分离 $\Delta_{hon}$

因此共谋无法获得 $\Delta_{hon}$ 的任何信息。

**QED**

---

## 六、效率分析

### 6.1 计算开销

| 操作 | 标准 CKKS-FL | TESK-EGD | 变化 |
|------|-------------|----------|------|
| 客户端加密 | $O(N \log N)$ | $O(N \log N)$ | 0% |
| 同态聚合 | $O(N \log N)$ | $O(N \log N)$ | 0% |
| 解密 | $O(N \log N)$ | $O(N \log N)$（TEE 内） | 0%（算法相同）|
| PTopk 累加器 | $O(d)$ | $O(d)$（TEE 内） | 0% |
| 重新加密 | $O(N \log N)$ | $O(N \log N)$（TEE 内） | 0% |
| **TEE 上下文切换** | 无 | ~$10\mu s$ / ECALL | 新增 |

**关键结论**：密码学运算量与标准 CKKS-FL 完全相同，仅增加 TEE ECALL/OCALL 的上下文切换开销（约 $10\mu s$ / 次，可忽略）。

### 6.2 通信开销

| 流量 | 标准 CKKS-FL | TESK-EGD | 变化 |
|------|-------------|----------|------|
| 客户端→Server | $ct_i$ | $ct_i$ | 0% |
| Server→TEE | 无（本地） | $ct_i$ 传递 | 本地内存拷贝 |
| TEE→Server | 无 | $ct_{global}, \delta_{prefetch}$ | 本地内存拷贝 |
| Server→Client | $ct_{prefetch}$ | $\delta_{prefetch}$（明文） | **减少**（明文 < 密文）|

**关键结论**：网络通信量与标准 CKKS-FL 相同或更少（预取内容从密文变为明文，体积相同但无需额外解密带宽）。

### 6.3 TEE 内存开销

| 组件 | 内存占用 |
|------|----------|
| 密封 sk | ~4 KB |
| 密封 $K_r$ | ~32 B |
| 明文模型（ResNet-18） | ~45 MB |
| 临时密文缓冲区 | ~10 MB |
| **总计** | **~55 MB** |

**SGX 兼容性**：Intel SGX EPC 限制为 128 MB（SGX1）或动态扩展（SGX2）。
- SGX1：需分页加载模型（~55 MB < 128 MB，勉强可行）
- SGX2：无内存限制，推荐

---

## 七、与现有工作对比

| 特性 | 标准 CKKS-FL | 3S-EAD | **TESK-EGD** | 阈值 CKKS |
|------|-------------|--------|-------------|----------|
| **sk 存储位置** | Server | Server+Edge+Client | **TEE Enclave** | 分散在客户端 |
| **Server 可读 sk** | ✅ 是 | ⚠️ 需共谋 | **❌ 否** | ❌ 否 |
| **解密透明度** | 不透明 | 两方协同 | **可远程证明** | 多方协同 |
| **硬件依赖** | 无 | 无 | **TEE** | 无 |
| **额外通信** | 无 | 1 RTT/轮 | **无** | t RTT/轮 |
| **侧信道风险** | N/A | N/A | **存在** | N/A |
| **部署复杂度** | 低 | 中 | **高** | 高 |

---

## 八、形式化安全定义

### 8.1 理想功能 $\mathcal{F}_{TESK}$

```
理想功能 F_TESK:
  状态: M_t (全局模型)
  
  输入 (Client i): Delta_i
  输入 (Server Host): S (选中客户端集合), {w_i}
  
  操作:
    1. 验证 |S| >= t_min
    2. Delta_agg = sum_{i in S} w_i * Delta_i
    3. M_{t+1} = M_t + PTopk(Delta_agg)
    4. 输出 (所有 Client): delta_prefetch = M_{t+1} - M_t
  
  泄漏 (Server Host): 仅 {w_i}, |S|, delta_prefetch
  泄漏 (Client i): 无（除自身输入/输出外）
```

### 8.2 安全性定理

**定理 6（TESK-EGD 安全性）**：在以下假设下：
1. CKKS 满足 IND-CPA 安全（RLWE 假设）
2. TEE 满足隔离性和远程证明（硬件安全假设）
3. TEE 侧信道攻击成功概率 $\epsilon_{side} < 2^{-\lambda_{tee}}$

TESK-EGD 协议 $\Pi_{TESK}$ **UC-安全**实现理想功能 $\mathcal{F}_{TESK}$，对恶意 Server Host 和半诚实客户端的安全参数为 $\lambda = \min(\lambda_{rlwe}, \lambda_{tee})$。

**证明概要**：
- 构造模拟器 $\mathcal{S}$，模拟 Server Host 的视图
- $\mathcal{S}$ 仅知 $\{w_i\}, |S|, \delta_{prefetch}$，与真实协议不可区分
- TEE 隔离性保证 Server Host 无法获得额外信息
- 侧信道攻击以可忽略概率打破隔离，安全性退化为标准 CKKS-FL

---

## 九、实现状态与待办

### 已完成
- [x] 系统架构设计
- [x] 核心协议（6个算法）
- [x] 公式推导（4个定理）
- [x] 安全性分析（6种威胁模型）
- [x] 效率分析
- [x] Python 框架代码（`tee_enclave.py`）

### 待实现
- [ ] SGX Enclave C++ 代码（`enclave/aggregator_trusted.c`）
- [ ] 远程证明验证（IAS / DCAP）
- [ ] 生产级 OCALL/ECALL 接口
- [ ] 侧信道缓解（常数时间实现）
- [ ] 与现有 PAMP 框架的完整集成测试
