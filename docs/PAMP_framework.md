# Peer-Assisted Masked Prefetch (PAMP)
## 对等辅助掩码预取：一种基于CKKS的隐私保护联邦学习通信优化方案

---

## 摘要

联邦学习（FL）通过分布式训练保护数据隐私，但频繁的模型同步导致巨大的通信开销。密文预取（Ciphertext Prefetching）通过让未选中客户端提前获取聚合增量来降低通信量，但现有方案面临两个根本问题：（1）单密钥同态加密中服务器持有私钥，安全模型不成立；（2）阈值解密引入大量辅助节点，联邦学习部署困难。本文提出PAMP（Peer-Assisted Masked Prefetch），一种只用CKKS同态加密的新颖方案，通过**Per-Client Concealment Masking（PCCM）**实现个体梯度在聚合前的双重隐藏，通过**Deferred Mask Cancellation with Peer Threshold（DMC-PT）**实现预取delta的延迟去掩与对等阈值解密。PAMP在不引入额外辅助节点的前提下，实现了服务器不可解密、客户端互相不可解密的强隐私保证，同时保持与FedAvg等价的训练精度。

**关键词**：联邦学习；CKKS同态加密；密文预取；安全聚合；阈值解密

---

## 1 引言

### 1.1 背景

联邦学习（Federated Learning, FL）[1]允许多个客户端在本地训练模型，仅上传梯度更新而非原始数据，从而保护数据隐私。然而，FL的通信开销巨大：在典型的跨设备场景中，每轮需要选中的客户端下载全局模型、训练、上传梯度，未被选中的客户端则处于空闲状态。

**密文预取（Ciphertext Prefetching）**[2]提出让未被选中的客户端提前获取全局模型的密文增量（delta），在本地同态累加。当客户端最终被选中时，只需解密累加的delta并应用到base model上，从而避免下载多轮历史更新。但现有预取方案基于单密钥CKKS[3]，服务器生成并持有私钥，这在安全模型上存在根本缺陷。

### 1.2 现有方案的局限性

**单密钥方案的不安全性**。TenSEAL[3]等CKKS实现中，服务器生成完整上下文（含私钥）并通过`get_full_context_bytes()`分发给客户端。这意味着服务器随时可以解密任何客户端的梯度，违反了FL的基本安全假设。

**阈值方案的不实用性**。Mouchet et al.[4]和Chen et al.[5]提出多密钥/阈值CKKS，但需要额外的辅助节点（Auxiliary Nodes）持有私钥份额参与解密。在真实的跨设备FL中（如数百万手机），部署和维护辅助节点是不现实的。

### 1.3 本文贡献

本文提出PAMP，一种只用CKKS的隐私保护密文预取方案，核心贡献如下：

- **Per-Client Concealment Masking（PCCM）**：每个客户端在加密前注入个体掩码和成对掩码，使聚合后的密文只暴露自掩码之和，个体梯度被完全隐藏。预取delta始终处于掩码保护状态。
- **Deferred Mask Cancellation with Peer Threshold（DMC-PT）**：预取阶段不解密，延迟到训练前通过Shamir秘密共享恢复累积掩码，同态去掩后得到纯梯度密文，再通过P2P阈值解密恢复明文。无需额外辅助节点。
- **完整的安全性分析**：在半诚实服务器、半诚实客户端、恶意客户端共谋（<t个和≥t个）、服务器-客户端共谋、恶意服务器六种威胁模型下给出形式化安全证明。

---

## 2 预备知识

### 2.1 CKKS同态加密

CKKS[6]是一种适用于近似算术的 leveled 全同态加密方案，工作在多项式环 $R = \mathbb{Z}[X]/(X^N + 1)$ 上。

**密钥生成**：
```
SecretKey: s ← χ_key (小整数分布)
PublicKey: a ← U(R_qL), e ← χ_err, b = -a·s + e
EvaluationKey: evk (用于重线性化和旋转)
```

**加密**：
```
输入: 消息 m ∈ R (编码后的明文多项式)
采样: v ← χ_enc, e0, e1 ← χ_err
输出: ct = (c0, c1) = (b·v + e0 + m, a·v + e1)
```

**解密**：
```
μ = c0 + c1·s = m + e_noise
```

**同态运算**：
- 加法: ct1 + ct2 = (c1_0 + c2_0, c1_1 + c2_1)
- 标量乘: k · ct = (k·c0, k·c1)

### 2.2 Shamir秘密共享

$(t, n)$-Shamir秘密共享[7]将秘密 $s$ 分成 $n$ 份，任意 $t$ 份可以重构 $s$，任意 $t-1$ 份不泄露任何信息。

```
Sharing: 选择随机多项式 f(x) = s + a1·x + ... + a_{t-1}·x^{t-1}
         份额: s_i = f(i) mod p, i = 1,...,n
Reconstruction: s = Σ_{j∈T} λ_j · s_j, λ_j = Π_{k∈T,k≠j} k/(k-j)
```

**线性性质**：若 $[s_1]_j, [s_2]_j$ 分别是 $s_1, s_2$ 的Shamir份额，则 $[s_1]_j + [s_2]_j$ 是 $s_1 + s_2$ 的Shamir份额。

### 2.3 安全聚合

Bonawitz et al.[8]提出双掩码安全聚合：
- 每个客户端生成自掩码 $s_i$ 和成对掩码 $r_{ij}$（$r_{ij} = -r_{ji}$）
- 上传: $y_i = x_i + s_i + \sum_j r_{ij}$
- 聚合: $\sum_i y_i = \sum_i x_i + \sum_i s_i$（成对掩码抵消）

---

## 3 问题定义

### 3.1 系统模型

**实体**：
- **KGC（Key Generation Center）**：初始化时生成CKKS密钥、成对掩码，Shamir分片后离线
- **AS（Aggregation Server）**：每轮选择客户端，聚合密文更新，计算并广播delta，存储加密掩码份额
- **$\{C_i\}_{i=1}^n$**：客户端，本地训练，加密上传，接收预取，参与P2P阈值解密

**通信模型**：
- 服务器-客户端：星型拓扑，服务器广播delta，存储加密份额
- 客户端-客户端：P2P消息传递（仅阈值解密时需要）

### 3.2 威胁模型

**半诚实（Honest-but-Curious）**：实体遵循协议，但试图从观察到的信息中推断额外知识。

**恶意（Malicious）**：实体可以偏离协议，发送伪造消息。

**共谋（Collusion）**：多个实体共享信息，试图联合攻破安全性。

### 3.3 安全目标

1. **服务器不可解密**：AS无法从任何密文中恢复明文梯度
2. **客户端互相隔离**：单个客户端无法解密其他客户端的梯度
3. **共谋韧性**：< t 个客户端共谋无法恢复私钥或明文
4. **通信效率**：未选中客户端的通信量低于完整模型同步

---

## 4 PAMP方案设计

### 4.1 方案概览

PAMP在标准联邦学习流程中引入两层机制：

| 层级 | 机制 | 作用 |
|------|------|------|
| 隐私保护层 | PCCM + DMC-PT | 掩码隐藏个体梯度，延迟去掩+对等阈值解密 |
| 聚合层 | CKKS同态加法 | 掩码在聚合中自动抵消 |

### 4.2 Phase 0：初始化

```
KGC执行:
  1. CKKS.KeyGen(N, qL, χ) → (sk, pk, evk)
  2. Shamir.Split(sk, n, t) → {sk_i}_{i=1}^n
  3. 生成成对掩码:
       for each pair (i,j), i < j:
         r_ij ← U(-B, B)
         r_ji = -r_ij
  4. 分发:
       - pk, evk → AS
       - sk_i, {r_ij}_{j≠i} → C_i (通过安全通道)
  5. KGC.ShredAll()  // 销毁所有密钥材料
  6. KGC永久离线
```

**安全参数**：
- $N = 8192$（多项式次数）
- $q_L$：模数链 $[60, 40, 40, 60]$ bits
- $t = \lceil 2n/3 \rceil$（阈值）
- $B = 2^{20}$（掩码范围）

### 4.3 Phase 1：每轮训练流程

#### 4.3.1 客户端本地训练与掩码加密

**轮次定义**：用绝对轮次 $r \in \{1, 2, \ldots, T\}$ 标记全局训练轮次。

```
客户端 C_i 在轮次 r:

Step 1: 本地训练（仅当被选中时）
  if i ∈ S_r:
    g_i^(r) ← LocalTrain(D_i, w_sync, E)
  else:
    g_i^(r) = 0  // 未选中，无梯度

Step 2: 自掩码生成与分片（仅当被选中时）
  if i ∈ S_r:
    s_i^(r) ← U(-B, B)
    {[s_i^(r)]_1, ..., [s_i^(r)]_n} ← Shamir.Split(s_i^(r), n, t)
    // 加密份额: enc_{i→j} = Enc(pk_j, [s_i^(r)]_j)
    // 上传 {enc_{i→1}, ..., enc_{i→n}} 到服务器

Step 3: 总掩码计算
  m_i^(r) = s_i^(r) + Σ_{j≠i} r_ij
  // 注意: 若 i ∉ S_r, s_i^(r) = 0, 但 r_ij 仍来自KGC预分发

Step 4: CKKS加密（仅当被选中时）
  if i ∈ S_r:
    ct_i^(r) = CKKS.Encrypt(pk, g_i^(r) + m_i^(r))

Step 5: 上传（仅当被选中时）
  if i ∈ S_r:
    C_i → AS: ct_i^(r)
```

**PCCM正确性**：

**定理1（掩码聚合抵消）**：若所有客户端诚实地执行PCCM，则服务器聚合后的密文满足：

$$\text{ct}_{\text{agg}}^{(r)} = \sum_{i \in S_r} \text{ct}_i^{(r)} = \text{Enc}\left(pk, \sum_{i \in S_r} g_i^{(r)} + \sum_{i \in S_r} s_i^{(r)}\right)$$

**证明**：

$$\begin{aligned}
\text{ct}_{\text{agg}}^{(r)} &= \sum_{i \in S_r} \text{Enc}(pk, g_i^{(r)} + m_i^{(r)}) \\
&= \sum_{i \in S_r} \text{Enc}(pk, g_i^{(r)} + s_i^{(r)} + \sum_{j \neq i} r_{ij}) \\
&= \text{Enc}\left(pk, \sum_{i \in S_r} g_i^{(r)} + \sum_{i \in S_r} s_i^{(r)} + \sum_{i \in S_r} \sum_{j \neq i} r_{ij}\right)
\end{aligned}$$

由于 $r_{ij} = -r_{ji}$，双重求和 $\sum_{i \in S_r} \sum_{j \neq i} r_{ij} = 0$（每对 $(i,j)$ 贡献 $r_{ij} + r_{ji} = 0$）。证毕。

#### 4.3.2 服务器聚合与预取广播

```
AS在轮次 r:

Step 6: 同态聚合
  ct_agg^(r) = Σ_{i∈S_r} ct_i^(r)

Step 7: 计算Delta
  δ^(r) = ct_agg^(r) - ct_agg^(r-1)
        = Enc(pk, ΔG^(r) + ΔS^(r))
  其中 ΔG^(r) = G_agg^(r) - G_agg^(r-1)
       ΔS^(r) = S_agg^(r) - S_agg^(r-1)
       G_agg^(r) = Σ_{i∈S_r} g_i^(r)
       S_agg^(r) = Σ_{i∈S_r} s_i^(r)

Step 8: 预取广播
  PrefSet ← BandwidthAwareSelect(unselected_clients)
  for C_j ∈ PrefSet:
    AS → C_j: δ^(r)
```

**关键观察**：delta仍是密文，且被 $\Delta S^{(r)}$ 掩码保护。AS无法从中获取任何明文信息。

#### 4.3.3 客户端预取累加

```
未选中客户端 C_j:

Step 9: 累加预取delta
  if ct_prefetch is None:
    ct_prefetch = δ^(r)
    r_first = r  // 记录第一次预取轮次
  else:
    ct_prefetch += δ^(r)    // 同态加法
  r_last = r  // 记录最后一次预取轮次
```

**预取密文的状态**：

设客户端从第 $r_{\text{first}}$ 轮开始预取，到第 $r_{\text{last}}$ 轮结束，共预取 $R$ 轮：

$$\text{ct}_{\text{prefetch}} = \sum_{r=r_{\text{first}}}^{r_{\text{last}}} \delta^{(r)} = \text{Enc}\left(pk, \sum_{r=r_{\text{first}}}^{r_{\text{last}}} \Delta G^{(r)} + \sum_{r=r_{\text{first}}}^{r_{\text{last}}} \Delta S^{(r)}\right)$$

**望远镜求和**：

$$\sum_{r=r_{\text{first}}}^{r_{\text{last}}} \Delta G^{(r)} = \sum_{r=r_{\text{first}}}^{r_{\text{last}}} [G_{\text{agg}}^{(r)} - G_{\text{agg}}^{(r-1)}] = G_{\text{agg}}^{(r_{\text{last}})} - G_{\text{agg}}^{(r_{\text{first}}-1)}$$

$$\sum_{r=r_{\text{first}}}^{r_{\text{last}}} \Delta S^{(r)} = \sum_{r=r_{\text{first}}}^{r_{\text{last}}} [S_{\text{agg}}^{(r)} - S_{\text{agg}}^{(r-1)}] = S_{\text{agg}}^{(r_{\text{last}})} - S_{\text{agg}}^{(r_{\text{first}}-1)}$$

令：
- $G_{\text{cum}} = G_{\text{agg}}^{(r_{\text{last}})} - G_{\text{agg}}^{(r_{\text{first}}-1)}$（累积真实梯度变化）
- $S_{\text{cum}} = S_{\text{agg}}^{(r_{\text{last}})} - S_{\text{agg}}^{(r_{\text{first}}-1)}$（累积自掩码变化）

则：

$$\boxed{\text{ct}_{\text{prefetch}} = \text{Enc}\left(pk, G_{\text{cum}} + S_{\text{cum}}\right)}$$

#### 4.3.4 解密触发：掩码恢复与阈值解密

当客户端 $C_k$ 在第 $r_{\text{curr}}$ 轮被选中训练且 $\text{ct}_{\text{prefetch}} \neq \emptyset$ 时：

**Step 10：从服务器下载聚合掩码份额**

```
C_k:
  从服务器下载 {E_k^(r)}_{r=r_first}^{r_last}
  其中 E_k^(r) = Enc(pk_k, [S_agg^(r)]_k) 是服务器聚合的加密份额
  
  用 sk_k 解密得到 {[S_agg^(r)]_k}_{r=r_first}^{r_last}
```

**Step 11：本地计算累积掩码份额**

$$[S_{\text{cum}}]_k = [S_{\text{agg}}^{(r_{\text{last}})}]_k - [S_{\text{agg}}^{(r_{\text{first}}-1)}]_k$$

其中 $[S_{\text{agg}}^{(r_{\text{first}}-1)}]_k$ 是客户端 $k$ 在 $r_{\text{first}}-1$ 轮同步时存储的（见Step 18）。

**Step 12：P2P广播请求其他份额**

```
C_k → {C_j}: "Request [S_cum] share"
```

**Step 13：其他客户端响应**

```
每个在线客户端 C_j:
  从服务器下载 {E_j^(r)}_{r=r_first}^{r_last}（若尚未下载）
  用 sk_j 解密得到 {[S_agg^(r)]_j}
  计算 [S_cum]_j = [S_agg^(r_last)]_j - [S_agg^(r_first-1)]_j
  返回 [S_cum]_j 给 C_k
```

**Step 14：Shamir重构累积掩码**

客户端 $k$ 收集至少 $t$ 个份额 $\{[S_{\text{cum}}]_j\}_{j \in T}$，执行Shamir重构：

$$S_{\text{cum}} = \text{Shamir.Reconstruct}\left(\{[S_{\text{cum}}]_j\}_{j \in T}\right)$$

**Step 15：同态去掩**

客户端 $k$ 用公钥加密 $S_{\text{cum}}$（本地操作）：

$$\text{ct}_{\text{mask}} = \text{Enc}\left(pk, S_{\text{cum}}\right)$$

执行同态减法：

$$\boxed{\text{ct}_{\text{plain}} = \text{ct}_{\text{prefetch}} - \text{ct}_{\text{mask}} = \text{Enc}\left(pk, G_{\text{cum}}\right)}$$

**正确性验证**：

$$\begin{aligned}
\text{ct}_{\text{plain}} &= \text{Enc}(pk, G_{\text{cum}} + S_{\text{cum}}) - \text{Enc}(pk, S_{\text{cum}}) \\
&= \text{Enc}(pk, (G_{\text{cum}} + S_{\text{cum}}) - S_{\text{cum}}) \\
&= \text{Enc}(pk, G_{\text{cum}})
\end{aligned}$$

**Step 16：P2P阈值解密**

$\text{ct}_{\text{plain}} = (c_0, c_1)$ 是纯梯度密文。客户端 $k$ 执行 $(t,n)$-阈值解密：

**Step 16.1：部分解密份额计算**

每个参与的客户端 $j \in T$（$|T| = t$）计算：

$$D_j = sk_j \cdot c_1 + e_{\text{smudge},j}$$

其中 $e_{\text{smudge},j} \leftarrow D_{R, \sigma}$ 是smudging噪声，$\sigma \geq 2^s \cdot \|e_{\text{prefetch}}\|_{\text{can}}$。

**Step 16.2：拉格朗日插值组合**

客户端 $k$ 收集 $\{D_j\}_{j \in T}$，计算拉格朗日系数：

$$\lambda_j = \prod_{m \in T, m \neq j} \frac{-m}{j-m} \pmod{q_\ell}$$

组合明文：

$$\mu = c_0 + \sum_{j \in T} \lambda_j \cdot D_j = c_0 + c_1 \cdot sk + e_{\text{total}}$$

其中 $e_{\text{total}} = \sum_{j \in T} \lambda_j \cdot e_{\text{smudge},j}$。

**Step 16.3：CKKS解码**

$$G_{\text{cum}} = \text{CKKS.Decode}(\mu)$$

**Step 17：应用更新**

$$\boxed{w_{\text{sync}} = w_{\text{base}} + \eta \cdot G_{\text{cum}}}$$

其中 $w_{\text{base}} = w^{(r_{\text{first}}-1)}$ 是客户端上次同步时的模型。

**Step 18：更新本地存储**

```
C_k:
  // 存储当前轮次的聚合掩码份额，供下次预取使用
  stored_mask_share = [S_agg^(r_curr)]_k
  // 从服务器下载并解密得到
  
  // 清空预取状态
  ct_prefetch = ∅
  r_first = None
  r_last = None
  w_base = w_sync
```

---

## 5 完整闭环公式链

```
加密:   ct_i^(r) = Enc(pk, g_i^(r) + s_i^(r) + Σ_j r_ij)
           ↓
聚合:   ct_agg^(r) = Σ_{i∈S_r} ct_i^(r) = Enc(pk, G_agg^(r) + S_agg^(r))
           ↓
Delta:  δ^(r) = ct_agg^(r) - ct_agg^(r-1) = Enc(pk, ΔG^(r) + ΔS^(r))
           ↓
累加:   ct_prefetch = Σ_{r=r_first}^{r_last} δ^(r)
       = Enc(pk, [G_agg^(r_last) - G_agg^(r_first-1)] + [S_agg^(r_last) - S_agg^(r_first-1)])
       = Enc(pk, G_cum + S_cum)
           ↓
去掩:   ct_plain = ct_prefetch - Enc(pk, S_cum) = Enc(pk, G_cum)
           ↓           ↑
           └───────────┘
    [S_cum = S_agg^(r_last) - S_agg^(r_first-1)]
    [通过Shamir P2P恢复: 收集t个 [S_cum]_j 份额]
           ↓
阈值解密: G_cum = ThresholdDecrypt(ct_plain, {sk_j}_{j∈T})
           ↓
训练:   w_sync = w_base + η · G_cum = w^(r_last)
```

---

## 6 安全性分析

### 6.1 半诚实服务器

**攻击能力**：AS记录所有密文、delta、聚合结果，试图恢复明文梯度或推断个体客户端数据。

**定理2（服务器语义安全）**：在决策性RLWE假设下，AS无法从任何密文中恢复明文。

**证明**：AS观察到的所有信息为密文形式。AS没有sk的任何份额。由CKKS的语义安全性（基于决策性RLWE），AS无法区分密文与随机值。即使AS知道delta的结构，也无法从中获取明文信息。证毕。

### 6.2 半诚实客户端（单个）

**定理3（单客户端隔离）**：单个客户端无法恢复任何其他客户端的个体梯度。

**证明**：
- **私钥层面**：$sk_i$ 是 $(t, n)$-Shamir分片，$t-1$ 个份额不泄露任何信息。
- **掩码层面**：客户端 $C_i$ 知道自身的 $s_i$ 和 $\{r_{ij}\}_j$，但不知道其他客户端的 $s_j$。由Shamir $(t, n)$-隐私，$C_i$ 获得的 $t-1$ 个 $[s_j]_i$ 份额不泄露 $s_j$。
- **密文层面**：即使 $C_i$ 通过共谋获得 $sk$，解密后看到的是聚合梯度 $\sum_j g_j + \sum_j s_j$，个体 $g_j$ 被 $s_j$ 隐藏。由于 $s_j \leftarrow U(-B, B)$ 且 $B \gg |g_j|$，$g_j + s_j$ 的分布与 $s_j$ 统计不可区分。证毕。

### 6.3 恶意客户端共谋（< t个）

**定理4（<t共谋安全）**：< t 个客户端共谋无法恢复sk，也无法重构任何自掩码 $s_i$。

**证明**：直接由Shamir秘密共享的 $(t-1)$-privacy性质。$k < t$ 个份额不泄露任何关于秘密的信息（信息论安全）。证毕。

### 6.4 恶意客户端共谋（≥ t个）

≥ t 个客户端可以恢复完整私钥 $sk$ 和所有自掩码 $\{s_i\}$。

**缓解**：设置 $t = \lceil 2n/3 \rceil$，需要多数客户端共谋。在真实FL中，客户端通常属于不同组织/设备，大规模共谋成本高。

### 6.5 服务器与客户端共谋

**定理5（服务器-单客户端共谋安全）**：AS与单个客户端共谋无法恢复明文。

**证明**：AS + $C_i$ 持有1个 $sk$ 份额。由于 $t \geq 2$，1个份额不足以恢复 $sk$。同时，$C_i$ 只持有自身的掩码信息，不知道其他客户端的 $s_j$。AS无法从密文中推断 $s_j$。因此，AS + $C_i$ 无法解密任何密文。证毕。

### 6.6 恶意服务器（选择性分发Delta）

AS可以给不同客户端发送不同的delta。由于delta是密文且被掩码保护：
- AS可以发送伪造delta，但客户端解密后得到的是随机值（因为掩码未抵消）
- 这会导致模型发散，但不会泄露明文
- **缓解**：客户端维护轮次号单调性检查，拒绝轮次号 $\leq$ last_accepted的delta

---

## 7 通信与计算分析

### 7.1 通信量对比

| 方案 | 每轮选中客户端上传 | 每轮未选中客户端下载 | 解密额外开销 |
|------|-------------------|---------------------|-------------|
| FedAvg | $O(d)$ | $O(d)$ (完整模型) | 0 |
| CipherFetch[2] | $O(d/S \cdot |ct|)$ | $O(|ct|)$ (delta) | 0 |
| 单密钥CKKS+Prefetch | $O(d/S \cdot |ct|)$ | $O(|ct|)$ | 0 |
| **PAMP** | $O(d/S \cdot |ct| + n \cdot |share|)$ | $O(|ct|)$ | $O(t \cdot |D_j|)$ (阈值解密) |

其中 $d$ 是模型参数量，$S = N/2 = 4096$ 是CKKS slots数，$|ct|$ 是单个密文大小，$|share|$ 是加密掩码份额大小，$|D_j|$ 是部分解密份额大小。

**净节省**：预取 $R$ 轮后，客户端节省 $(R-1) \cdot |ct|$ 的下载量，阈值解密多花费 $t \cdot |ct|/2$。当 $R > t/2 + 1$ 时净收益为正。

### 7.2 计算开销

| 操作 | 开销来源 | 量级 |
|------|---------|------|
| 掩码生成 | 随机数采样 | $O(1)$ 每客户端 |
| Shamir分片 | 多项式求值 | $O(n \cdot t)$ 每被选中客户端 |
| 同态聚合 | CKKS加法 | $O(|S_r|)$ 每密文 |
| 预取累加 | CKKS加法 | $O(1)$ |
| 掩码恢复 | Shamir重构 | $O(t^2)$ |
| 阈值解密 | 多项式乘法 + 解码 | $O(t \cdot N \log N)$ |

---

## 8 实验设计

### 8.1 实验设置

- **数据集**：MNIST、CIFAR-10、FEMNIST
- **模型**：LeNet、ResNet-18
- **客户端数**：n = 10, 50, 100
- **采样率**：每轮 10%-30%
- **预取轮次**：R = 1, 3, 5, 10
- **阈值**：t = ⌈2n/3⌉

### 8.2 对比基线

1. **FedAvg**（明文，无预取）
2. **CipherFetch**（单密钥CKKS预取）
3. **PAMP（本文）**

### 8.3 评估指标

1. **准确率**：Top-1准确率，与FedAvg对比
2. **通信量**：总上传/下载字节数
3. **延迟**：单轮训练时间（含加密/聚合/预取/解密）
4. **解密成功率**：P2P阈值解密时在线客户端比例

### 8.4 预期结果

- **准确率**：PAMP与FedAvg差异 < 0.5%（掩码完全消除）
- **通信量**：相比FedAvg降低 60-80%（R=5时）
- **延迟**：单轮增加 10-20%（主要来自Shamir分片和阈值解密）
- **解密成功率**：> 95%（t=⌈2n/3⌉时，在线客户端通常 > 2n/3）

---

## 9 结论

本文提出PAMP，一种基于CKKS的隐私保护密文预取联邦学习方案。通过Per-Client Concealment Masking实现个体梯度的双重隐藏，通过Deferred Mask Cancellation with Peer Threshold实现无辅助节点的延迟解密。PAMP在半诚实和恶意威胁模型下均具有形式化安全保证，同时保持与标准FedAvg等价的训练精度，为隐私保护的联邦学习通信优化提供了一种可部署的密码学方案。

---

## 参考文献

[1] McMahan B, Moore E, Ramage D, et al. Communication-efficient learning of deep networks from decentralized data. AISTATS 2017.

[2] Luo S, Chen X. CipherFetch: Secure Ciphertext Prefetching for Federated Learning. (Existing project)

[3] A. Al Badawi et al., "Towards the AlexNet moment for homomorphic encryption: HCNN, the first homomorphic CNN on encrypted data with GPUs," IEEE TDSC 2020.

[4] Mouchet C, Troncoso-Pastoriza J, Froelicher D, et al. Multiparty homomorphic encryption from ring-learning-with-errors. PETS 2021.

[5] Chen H, Dai W, Kim M, et al. Efficient multi-key homomorphic encryption with packed ciphertexts with application to oblivious neural network inference. CCS 2019.

[6] Cheon J H, Kim A, Kim M, et al. Homomorphic encryption for arithmetic of approximate numbers. ASIACRYPT 2017.

[7] Shamir A. How to share a secret. Communications of the ACM, 1979.

[8] Bonawitz K, Ivanov V, Kreuter B, et al. Practical secure aggregation for privacy-preserving machine learning. CCS 2017.
