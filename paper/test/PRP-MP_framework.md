# PRPG-Masked Prefetch (PRP-MP): 基于确定性伪随机掩码的去 TEE 密文预取框架

> **核心创新**：用**单全局种子 PRPG** 替代 Shamir 秘密共享，实现掩码的**零通信本地恢复**。客户端无需 P2P 交互即可计算任意轮次、任意客户端集合的累积掩码，彻底消除 PAMP 框架中的掩码恢复通信瓶颈。

---

## 1 核心思想与动机

### 1.1 当前 PAMP 框架的瓶颈

PAMP (Peer-Assisted Masked Prefetch) 通过**成对盲化掩码 + Shamir 秘密共享**实现去 TEE 的隐私保护：

```
客户端 i 生成掩码 s_i^(r) → Shamir 分成 n 份 → 加密份额上传服务器
                                                    ↓
客户端 k 同步时 ← P2P 请求 t-1 个其他客户端的份额 ← 服务器转发
                                                    ↓
客户端 k 恢复 Σs_i^(r) → 同态去掩 → 阈值解密
```

**核心痛点**：
1. **P2P 通信**：需要至少 $t$ 个其他客户端在线并响应
2. **延迟高**：等待 $t$ 个客户端响应增加同步时间
3. **份额存储**：服务器需存储每轮每个客户端的加密份额矩阵
4. **掉线敏感**：客户端掉线导致份额无法收集

### 1.2 ESAFL 的启示：PRPG

ESAFL [25-ESAFL] 的核心贡献之一是 **PRPG (Pseudorandom Polynomial Generation)**：

> 所有客户端共享秘密种子 $B$，本地独立生成相同的伪随机多项式 $a^{(t)} = \text{PRPG}(t, B)$，**无需任何交互**。

**关键洞察**：如果掩码也是**确定性的伪随机函数**，所有客户端用相同的种子生成本质上"相同"的掩码，就不需要 P2P 传输份额了。

### 1.3 PRP-MP 的核心设计

**一句话概括**：KGC 只分发一个**全局种子** $B$，客户端用 $B$ 本地生成所有轮次、所有客户端、所有 batch 的掩码。掩码恢复从"P2P 请求 Shamir 份额"变为"本地 PRNG 计算"。

```
KGC 生成全局种子 B（128 bit）
    ↓
分发 B 给所有客户端（初始化时一次性）
    ↓
客户端 i 需要恢复累积掩码时：
    S_cum = Σ_r Σ_{j∈S_r} PRNG(B, j, r, b)   ← 纯本地计算，零通信
```

---

## 2 符号定义

### 2.1 系统参数

| 符号 | 含义 | 取值 |
|------|------|------|
| $N$ | 客户端总数 | 30 |
| $\rho$ | 采样率 | 0.5 |
| $B$ | 全局 PRNG 种子 | 128-bit 随机串 |
| $T$ | 总训练轮次 | 20 |
| $b$ | batch 索引 | $0, 1, \ldots, B_{\text{total}}-1$ |
| $\text{slot\_count}$ | CKKS slot 数 | 4096 |

### 2.2 密钥

| 符号 | 含义 | 生成/分发 |
|------|------|----------|
| $(pk, sk)$ | CKKS 公钥/私钥 | KGC 生成，sk  Shamir 分片给客户端 |
| $B$ | **全局掩码种子** | KGC 生成，**所有客户端共享** |
| $sk_i$ | 客户端 $i$ 的 Shamir 私钥分片 | KGC 分发 |

> **重要**：$B$ 是**所有客户端共享的秘密**，服务器**不知道** $B$。

### 2.3 掩码（确定性伪随机）

**客户端 $j$ 在第 $r$ 轮、batch $b$ 的掩码**：

$$s_j^{(r,b)} = \text{PRNG}(B, \; j, \; r, \; b) \; \in \; \mathbb{R}^{\text{slot\_count}}$$

**PRNG 输入**：
- 种子 $B$（全局共享）
- 客户端 ID $j$
- 轮次 $r$
- batch 索引 $b$

**输出范围**：$[-M, M]$（如 $M=1.0$）

> **关键性质**：给定相同的 $(B, j, r, b)$，**任何客户端**都能生成**完全相同**的 $s_j^{(r,b)}$。

---

## 3 协议设计

### 3.1 Phase 0：初始化（KGC）

**(1) CKKS 密钥生成**：
$$(pk, sk, evk) \leftarrow \text{CKKS.KeyGen}(N_{\text{poly}}, q_L, \chi)$$

**(2) Shamir 分片私钥**（用于阈值解密）：
$$\{sk_1, sk_2, \ldots, sk_N\} \leftarrow \text{Shamir.Split}(sk, N, t)$$

**(3) 全局掩码种子**：
$$B \leftarrow \{0, 1\}^{128}$$

**(4) 分发**：
$$\begin{aligned}
(pk, evk) &\rightarrow \text{公开（所有实体）} \\
(sk_i) &\rightarrow \mathcal{C}_i \quad \text{（安全通道）} \\
B &\rightarrow \mathcal{C}_i \quad \text{（安全通道）}
\end{aligned}$$

**(5) KGC 销毁所有密钥材料，永久离线**。

### 3.2 Phase 1：训练与加密（采样客户端 $i \in S_r$）

**(1) 本地训练**：
$$g_i^{(r)} \leftarrow \text{LocalTrain}(D_i, w^{(r-1)}, E)$$

**(2) 残差补偿与稀疏化**（已有模块）：
$$\tilde{g}_{i,b}^{(r)} = \text{TopK}_b\left(g_{i,b}^{(r)} + r_{i,b}^{(r)}\right)$$

只对选中的 batch 执行步骤 (3)-(4)。

**(3) 本地生成掩码**（PRNG，零通信）：
$$s_{i,b}^{(r)} = \text{PRNG}(B, \; i, \; r, \; b)$$

> **注意**：客户端 $i$ 不需要从 KGC 或其他客户端获取掩码。只需知道全局种子 $B$ 和自己的 ID $i$。

**(4) 加掩并加密**：
$$\text{ct}_{i,b}^{(r)} = \text{CKKS.Enc}\left(pk, \; \tilde{g}_{i,b}^{(r)} + s_{i,b}^{(r)}\right)$$

**(5) 上传服务器**：
$$\mathcal{C}_i \rightarrow \mathcal{S}: \quad \{\text{ct}_{i,b}^{(r)}\}_{b \in \mathcal{B}_i^{(r)}}$$

其中 $\mathcal{B}_i^{(r)}$ 是客户端 $i$ 选中的 batch 集合。

### 3.3 Phase 2：服务器聚合与预取

**(1) 同态聚合**（按 batch）：

对于每个全局 batch $b$，令 $S_r^{(b)} = \{i \in S_r : b \in \mathcal{B}_i^{(r)}\}$（上传了 batch $b$ 的客户端集合）：

$$C_b^{(r)} = \sum_{i \in S_r^{(b)}} \text{ct}_{i,b}^{(r)} = \text{Enc}\left(pk, \; \sum_{i \in S_r^{(b)}} \tilde{g}_{i,b}^{(r)} + \sum_{i \in S_r^{(b)}} s_{i,b}^{(r)}\right)$$

**(2) 计算 Delta 密文**：
$$\delta_b^{(r)} = C_b^{(r)} - C_b^{(r-1)}$$

**(3) 广播预取**（给未选中客户端）：
$$\mathcal{S} \rightarrow \mathcal{C}_k, \quad \forall k \notin S_r: \quad \{\delta_b^{(r)}\}_b$$

### 3.4 Phase 3：客户端本地掩码恢复（核心创新）

**场景**：客户端 $k$ 在第 $r_{\text{curr}}$ 轮被选中，需要解密预取的 delta。

**(1) 确定需要恢复的轮次范围**：
$$\mathcal{R}_k = \{r_{\text{sync},k}+1, \; r_{\text{sync},k}+2, \; \ldots, \; r_{\text{curr}}-1\}$$

**(2) **本地计算累积掩码**（零通信，核心创新）**：

客户端 $k$ 知道 $B$、所有客户端 ID、以及每轮的参与集合 $\{S_r\}$（预采样计划公开）。对于每个 batch $b$：

$$S_{\text{cum},k}^{(b)} = \sum_{r \in \mathcal{R}_k} \sum_{j \in S_r^{(b)}} s_{j,b}^{(r)} = \sum_{r \in \mathcal{R}_k} \sum_{j \in S_r^{(b)}} \text{PRNG}(B, j, r, b)$$

> **这是纯本地计算**。客户端 $k$ 只需遍历所有轮次和所有参与客户端，调用 PRNG 生成掩码并累加。**无需向任何其他客户端发送请求**。

**(3) 加密累积掩码**：
$$\text{ct}_{\text{mask},k}^{(b)} = \text{Enc}\left(pk, \; S_{\text{cum},k}^{(b)}\right)$$

**(4) 同态去掩**：
$$\text{ct}_{\text{plain},k}^{(b)} = \text{ct}_{\text{prefetch},k}^{(b)} - \text{ct}_{\text{mask},k}^{(b)} = \text{Enc}\left(pk, \; G_{\text{cum},k}^{(b)}\right)$$

**(5) 阈值解密**：
$$G_{\text{cum},k}^{(b)} = \text{ThresholdDecrypt}\left(\text{ct}_{\text{plain},k}^{(b)}, \; \{sk_j\}_{j \in \mathcal{T}_k}\right)$$

其中 $\mathcal{T}_k$ 是至少 $t$ 个参与解密的客户端集合（可通过服务器转发份额）。

**(6) 模型同步**：
$$w_{\text{sync},k} = w_{\text{base},k} + \eta \cdot G_{\text{cum},k}$$

---

## 4 完整闭环公式推导

$$\begin{aligned}
&\textbf{初始化:} && B \leftarrow \{0,1\}^{128}, \quad (pk, sk) \leftarrow \text{CKKS.KeyGen}() \\
&\textbf{训练:} && g_{i,b}^{(r)} \leftarrow \text{LocalTrain}_b(D_i, w^{(r-1)}) \\
&\textbf{稀疏化:} && \tilde{g}_{i,b}^{(r)} = \text{TopK}_b(g_{i,b}^{(r)} + r_{i,b}^{(r)}) \\
&\textbf{PRNG掩码:} && s_{i,b}^{(r)} = \text{PRNG}(B, i, r, b) \\
&\textbf{加密:} && \text{ct}_{i,b}^{(r)} = \text{Enc}(pk, \tilde{g}_{i,b}^{(r)} + s_{i,b}^{(r)}) \\
&\textbf{聚合:} && C_b^{(r)} = \sum_{i \in S_r^{(b)}} \text{ct}_{i,b}^{(r)} = \text{Enc}\left(pk, G_b^{(r)} + S_b^{(r)}\right) \\
&\textbf{Delta:} && \delta_b^{(r)} = C_b^{(r)} - C_b^{(r-1)} \\
&\textbf{预取累加:} && \text{ct}_{\text{prefetch},k}^{(b)} = \sum_{r \in \mathcal{R}_k} \delta_b^{(r)} \\
&\textbf{展开:} && \text{ct}_{\text{prefetch},k}^{(b)} = \text{Enc}\left(pk, G_{\text{cum},k}^{(b)} + S_{\text{cum},k}^{(b)}\right) \\
&\textbf{本地掩码恢复:} && S_{\text{cum},k}^{(b)} = \sum_{r \in \mathcal{R}_k} \sum_{j \in S_r^{(b)}} \text{PRNG}(B, j, r, b) \\
&\textbf{去掩:} && \text{ct}_{\text{plain},k}^{(b)} = \text{ct}_{\text{prefetch},k}^{(b)} - \text{Enc}(pk, S_{\text{cum},k}^{(b)}) \\
&\textbf{阈值解密:} && G_{\text{cum},k}^{(b)} = \text{ThresholdDecrypt}(\text{ct}_{\text{plain},k}^{(b)}, \{sk_j\}) \\
&\textbf{同步:} && w_{\text{sync},k} = w_{\text{base},k} + \eta \cdot G_{\text{cum},k}
\end{aligned}$$

---

## 5 威胁模型与安全性分析

### 5.1 攻击者模型

| 威胁 | 攻击者 | 能力 |
|------|--------|------|
| 半诚实服务器 | $\mathcal{S}$ | 遵循协议，试图从密文推断隐私 |
| 半诚实客户端 | $\mathcal{C}_j$ | 遵循协议，试图推断其他客户端梯度 |
| 客户端合谋 | $< t$ 个客户端 | 共享密钥分片和种子 $B$ |
| 恶意客户端 | $\mathcal{C}_m$ | 上传错误梯度/掩码 |
| 恶意服务器 | $\mathcal{S}^*$ | 篡改聚合、伪造预取 |

### 5.2 半诚实服务器安全

**定理 1（服务器语义安全）**：服务器无法从任何密文恢复明文。

**证明**：
- 服务器持有 $pk$（公开）和密文
- 服务器**不持有** $sk$（Shamir 分片给客户端）
- 服务器**不持有** $B$（只分发给客户端）
- CKKS 的 IND-CPA 安全性基于 RLWE 假设
- 因此服务器视图与随机密文不可区分 $\square$

**关键**：服务器即使知道预采样计划 $\{S_r\}$，没有 $B$ 就无法生成掩码，无法去掩。

### 5.3 半诚实客户端安全

**定理 2（单客户端隔离）**：单个客户端无法恢复其他客户端的个体梯度。

**证明**：
- 客户端 $j$ 持有 $B$ 和 $sk_j$
- 客户端 $j$ 可以解密聚合密文（阈值解密参与），得到 $G_b^{(r)} = \sum_{i \in S_r^{(b)}} \tilde{g}_{i,b}^{(r)}$
- 客户端 $j$ 也可以生成本轮所有掩码 $s_{i,b}^{(r)}$，同态去掩后得到明文梯度聚合
- 但看到的结果是**聚合梯度**，不是单个梯度
- 当 $|S_r^{(b)}| \geq 2$ 时，个体梯度被淹没 $\square$

**与当前 PAMP 等价**：当前 PAMP 中客户端 $j$ 通过 Shamir 恢复也能得到聚合掩码和，进而得到聚合梯度。PRP-MP 没有引入额外的信息泄露。

### 5.4 客户端合谋安全

**定理 3（$< t$ 合谋安全）**：$< t$ 个客户端合谋无法恢复 $sk$ 或任何明文。

**证明**：Shamir $(t, N)$ 的 $(t-1)$-privacy（信息论安全）。$< t$ 个分片无法恢复 $sk$，因此无法解密任何密文。$\square$

### 5.5 服务器-客户端合谋

**分析**：服务器 + 客户端 $j$ 合谋。
- 合谋者拥有：所有密文 + $B$ + $sk_j$
- 可以解密聚合密文得到聚合梯度
- 客户端 $j$ 知道自身贡献，可以减去：$G_{\text{agg}} - \tilde{g}_j = \sum_{i \neq j} \tilde{g}_i$
- 仍无法分离单个 $\tilde{g}_i$

**残余风险**：当 $|S_r^{(b)}| = 2$ 且合谋者是其中之一时，可精确恢复另一个客户端的梯度。**缓解**：每轮至少选 3 个客户端，或引入差分隐私噪声。

### 5.6 恶意客户端防御

**攻击**：恶意客户端 $m$ 上传错误掩码（不使用 PRNG(B, m, r, b)，而是随机值）。

**防御——掩码承诺验证**：

1. KGC 在初始化时预计算并发布**掩码承诺根**（Merkle Root）：
   $$\text{MR} = \text{MerkleRoot}\left(\{H(s_j^{(r,b)})\}_{j,r,b}\right)$$

2. 客户端 $j$ 上传 $(\text{ct}_{j,b}^{(r)}, \pi_{j,b}^{(r)})$，其中 $\pi$ 是 $H(s_j^{(r,b)})$ 的 Merkle 证明

3. 服务器验证 Merkle 证明，确保客户端使用了正确的掩码

> **优化**：KGC 只需预计算并发布 Merkle Root（约 32 字节），无需存储所有叶节点。客户端本地生成 $s_j^{(r,b)}$ 后即可计算哈希和证明路径（如果 Merkle 树结构公开）。

**更轻量的防御——范围证明**：

客户端上传 $(\text{ct}_i, \pi_i^{\text{range}})$，其中 $\pi_i^{\text{range}}$ 是梯度和掩码的 L2 范数范围证明。

### 5.7 恶意服务器防御

**攻击**：服务器篡改聚合权重、伪造预取 delta。

**防御——客户端签名验证**：

1. 每个客户端 $i$ 持有签名密钥对 $(vk_i, sk_i^{\text{sign}})$
2. 客户端 $i$ 对本轮聚合密文签名：$\sigma_i^{(r)} = \text{Sign}(sk_i^{\text{sign}}, H(C^{(r)}))$
3. 收集至少 $t$ 个签名后，聚合结果被认为是"已验证的"
4. 客户端只接受带有效阈值签名的预取 delta

**防御——一致性检查**：

客户端 $k$ 验证预取 delta 的累积效果：
$$w_{\text{sync},k} \stackrel{?}{=} w_{\text{base},k} + \eta \cdot \text{Decode}(\text{ThresholdDecrypt}(\text{ct}_{\text{plain},k}))$$

如果服务器伪造了 delta，同步后的模型与预期不符，客户端可以检测并上报。

---

## 6 与当前 PAMP / 其他方案对比

### 6.1 PRP-MP vs 当前 PAMP

| 维度 | 当前 PAMP | PRP-MP（本文） |
|------|-----------|---------------|
| **掩码分发** | Shamir 份额矩阵 + P2P 请求 | **全局种子 B（128 bit），零通信** |
| **同步延迟** | 等待 $t$ 个客户端响应 | **即时本地计算** |
| **掉线容忍** | $< t$ 个客户端掉线可恢复 | **任意客户端可独立恢复** |
| **服务器存储** | 加密 Shamir 份额矩阵 | **无掩码相关存储** |
| **客户端存储** | 自己的份额 + 他人的加密份额 | **仅种子 B** |
| **阈值解密** | 需要 | 需要（ unchanged ） |
| **安全性** | Shamir $(t-1)$-privacy | PRG 计算安全性 |

### 6.2 PRP-MP vs TEE 方案

| 维度 | TEE (TESK-EGD) | PRP-MP |
|------|---------------|--------|
| 硬件依赖 | Intel SGX / AMD SEV | **无** |
| 信任假设 | 硬件可信 | 密码学假设（RLWE + PRG） |
| 侧信道风险 | 有（缓存时序等） | **无** |
| 部署复杂度 | 高（远程证明、enclave） | **低（纯软件）** |
| 解密位置 | TEE 内 | 客户端阈值解密 |
| 掩码恢复 | TEE 内明文计算 | 客户端本地 PRNG |

### 6.3 PRP-MP vs ESAFL-ESHE

| 维度 | ESAFL-ESHE | PRP-MP |
|------|-----------|--------|
| 客户端采样 | ❌ 不兼容（需全参与） | ✅ 完全兼容 |
| Batch 级别稀疏化 | ❌ 需零密文补齐（20×） | ✅ 原生兼容 |
| 掩码级别 | 无掩码设计 | Batch 级别 PRNG |
| 预取支持 | 无 | ✅ 完整支持 |
| 去 TEE | ✅ | ✅ |
| 抗合谋 | $< N-1$ | $< t$（Shamir） |

---

## 7 复杂度分析

### 7.1 通信复杂度

| 操作 | 当前 PAMP | PRP-MP |
|------|----------|--------|
| 选中客户端上传密文 | $O(|S_r| \cdot B \cdot |\text{ct}|)$ | 相同 |
| 预取 delta 下发 | $O((N-|S_r|) \cdot B \cdot |\text{ct}|)$ | 相同 |
| **掩码恢复** | $O(t \cdot |\text{share}|)$ **P2P** | **$O(1)$ 本地计算** |
| **Shamir 份额存储** | $O(N \cdot T \cdot |\text{share}|)$ 服务器 | **$O(1)$** |

**每轮节省的通信**：消除了 $t$ 个客户端的 P2P 往返（约 $t \times$ 几 KB 到几 MB）。

### 7.2 计算复杂度

| 操作 | 当前 PAMP | PRP-MP |
|------|----------|--------|
| 掩码生成（客户端） | PRNG（本地） | PRNG（本地），相同 |
| **掩码恢复（同步时）** | Shamir.Reconstruct + P2P | **PRNG 累加** |
| 恢复 $k$ 轮 $m$ 个 batch | $O(k \cdot m \cdot \text{Shamir 开销})$ | $O(k \cdot m \cdot \text{PRNG 开销})$ |

PRNG 累加的计算量与 Shamir 重构相当或更优（PRNG 是高效伪随机生成器，Shamir 需要有限域上的拉格朗日插值）。

### 7.3 存储复杂度

| 实体 | 当前 PAMP | PRP-MP |
|------|----------|--------|
| 客户端 | $sk_i$ + 份额缓存 | $sk_i$ + **$B$（128 bit）** |
| 服务器 | 加密份额矩阵 $(N \times T \times B)$ | **无掩码存储** |

---

## 8 实现要点

### 8.1 PRNG 选择

推荐使用 **AES-CTR-DRBG** 或 **ChaCha20-DRBG**：

```python
def mask_prng(B: bytes, client_id: int, round_num: int, batch_idx: int, 
              length: int, range_val: float = 1.0) -> np.ndarray:
    """
    确定性掩码生成器。
    
    输入: B (16 bytes), client_id, round_num, batch_idx
    输出: length 维随机数组，范围 [-range_val, range_val]
    """
    # 组合输入为唯一种子
    counter = (client_id << 48) | (round_num << 16) | batch_idx
    # AES-CTR 或 ChaCha20 生成随机流
    rng = np.random.default_rng(seed=hash((B, counter)))
    return rng.uniform(-range_val, range_val, length)
```

**安全要求**：PRNG 必须是密码学安全的（CSPRNG），输出与真随机不可区分。

### 8.2 预采样计划公开性

PRP-MP 要求客户端知道每轮的参与集合 $S_r$ 来计算累积掩码。预采样计划可以：

1. **完全公开**：服务器广播预采样计划（不泄露隐私，只泄露参与 schedule）
2. **部分公开**：只向需要同步的客户端透露相关轮次的计划

### 8.3 与现有代码的集成

PRP-MP 可以**增量替换**当前 PAMP 的掩码恢复模块：

```python
# 当前 PAMP（需要 P2P）
def recover_cumulative_mask_pamp(client_id, rounds, server):
    shares = []
    for r in rounds:
        for j in get_online_peers(t):
            shares.append(request_share_from_peer(j, r))
    return shamir_reconstruct(shares)

# PRP-MP（纯本地）
def recover_cumulative_mask_prpmp(client_id, rounds, sampling_plan, B):
    cum_mask = np.zeros(batch_size)
    for r in rounds:
        for j in sampling_plan.get_participants(r):
            for b in range(num_batches):
                cum_mask += mask_prng(B, j, r, b, batch_size)
    return cum_mask
```

**改动量**：约 50 行代码替换 P2P 请求逻辑，其余流程完全不变。

---

## 9 安全性定理汇总

**定理 1（服务器无知性）**：服务器无 $sk$、无 $B$，无法从密文恢复任何明文信息。（基于 RLWE）

**定理 2（客户端视图等价）**：客户端 $j$ 在 PRP-MP 中的视图（聚合梯度 + 所有掩码）与在当前 PAMP 中的视图（聚合梯度 + Shamir 恢复的掩码和）信息等价。

**定理 3（$< t$ 合谋安全）**：$< t$ 个客户端合谋无法恢复 $sk$。（Shamir 信息论安全）

**定理 4（PRG 安全性）**：在 CSPRNG 假设下，不知道 $B$ 的敌手无法区分掩码与真随机。

**定理 5（去掩正确性）**：客户端 $k$ 本地计算的 $S_{\text{cum},k}$ 与真实累积掩码和相等。（PRNG 确定性 + 预采样计划一致性）

---

## 10 总结

本文提出 **PRPG-Masked Prefetch (PRP-MP)**，一种基于确定性伪随机掩码的去 TEE 密文预取框架。

**核心贡献**：
1. **消除 P2P 通信**：用单全局种子 PRPG 替代 Shamir 秘密共享，掩码恢复从"请求 $t$ 个客户端份额"变为"本地 PRNG 计算"
2. **兼容客户端采样 + batch 稀疏化**：完全保留现有 CipherFetch 的预取和 PTopk 流程，无需零密文补齐
3. **极低存储开销**：客户端仅需存储 128-bit 种子 $B$，服务器无需存储任何掩码相关数据
4. **即时同步**：客户端无需等待其他客户端在线，随时可本地完成掩码恢复

**局限与未来工作**：
- 阈值解密仍需要 $t$ 个客户端参与（可用服务器转发份额优化）
- 恶意客户端掩码伪造需额外验证机制（Merkle 承诺或范围证明）
- 全局种子 $B$ 的泄露会导致所有历史/未来掩码泄露（需定期轮换 $B$）

---

## 参考文献

- [25-ESAFL] Wu et al., "ESAFL: Efficient Secure Additively Homomorphic Encryption for Cross-Silo Federated Learning," IEEE TDSC, 2025.
- [25-FedPHE] Li et al., "FedPHE: A Secure and Efficient Federated Learning via Packed Homomorphic Encryption," IEEE TDSC, 2025.
- [25-FedFetch] Yan et al., "FedFetch: Faster Federated Learning with Adaptive Downstream Prefetching," IEEE INFOCOM, 2025.
- [26-Ftopk] Li et al., "Enhancing Federated Learning in Edge Computing With Secure Aggregation and Dynamic Verification," IEEE TMC, 2026.
