# PAMP 简化方案
## 只用自掩码的隐私保护密文预取

---

## 核心设计

去掉成对掩码，只保留自掩码。安全性仍成立，因为：
- 服务器没有sk，无法解密
- 单个客户端只有sk_i，无法解密（需要t个份额）
- 自掩码s_i每轮独立随机，信息论安全

---

## 符号定义

| 符号 | 含义 |
|------|------|
| n | 客户端总数 |
| t | 阈值，t = ⌈2n/3⌉ |
| r ∈ {1,2,...,T} | 绝对轮次 |
| S_r ⊆ {1,...,n} | 第r轮被选中的客户端集合 |
| pk, sk | CKKS聚合公钥/私钥 |
| sk_i | 客户端i持有的私钥份额 |
| g_i^(r) | 客户端i在第r轮的本地梯度 |
| s_i^(r) | 客户端i在第r轮的自掩码，s_i^(r) ← U(-B,B) |
| [s_i^(r)]_j | s_i^(r)的Shamir第j份份额 |
| w^(r) | 第r轮的全局模型 |
| w_base,k | 客户端k的基准模型 |
| r_sync,k | 客户端k上次同步的轮次 |

---

## Phase 0：初始化

**KGC执行：**

(1) CKKS密钥生成：

$$
(pk, sk, evk) ← CKKS.KeyGen(N, q_L, χ)
$$

(2) Shamir分片私钥：

$$
\{sk_1, sk_2, \ldots, sk_n\} ← Shamir.Split(sk, n, t)
$$

(3) 分发：

$$
\begin{aligned}
(pk, evk) &→ AS \\
sk_i &→ C_i \quad \text{(安全通道)}
\end{aligned}
$$

(4) KGC销毁所有密钥材料，永久离线。

**安全参数**：
- N = 8192（多项式次数）
- q_L：模数链 [60, 40, 40, 60] bits
- t = ⌈2n/3⌉（阈值）
- B = 2^20（掩码范围）

---

## Phase 1：每轮训练与预取

### 1.1 被选中的客户端

**客户端 i ∈ S_r：**

(1) 本地训练：

$$
g_i^{(r)} ← LocalTrain(D_i, w_{sync,i}, E)
$$

(2) 生成自掩码并Shamir分片：

$$
\begin{aligned}
s_i^{(r)} &← U(-B, B) \\
\{[s_i^{(r)}]_1, [s_i^{(r)}]_2, \ldots, [s_i^{(r)}]_n\} &← Shamir.Split(s_i^{(r)}, n, t)
\end{aligned}
$$

(3) 加密份额上传服务器：

$$
enc_{i→j}^{(r)} = Enc(pk_j, [s_i^{(r)}]_j), \quad ∀j ∈ \{1,\ldots,n\}
$$

(4) CKKS加密梯度：

$$
ct_i^{(r)} = CKKS.Enc(pk, g_i^{(r)} + s_i^{(r)})
$$

(5) 上传服务器：

$$
C_i → AS: \quad ct_i^{(r)}
$$

---

### 1.2 服务器聚合与广播

**AS在第r轮：**

(1) 同态聚合：

$$
ct_{agg}^{(r)} = \sum_{i ∈ S_r} ct_i^{(r)} = Enc\left(pk, \sum_{i ∈ S_r} g_i^{(r)} + \sum_{i ∈ S_r} s_i^{(r)}\right)
$$

令：

$$
\begin{aligned}
G_{agg}^{(r)} &= \sum_{i ∈ S_r} g_i^{(r)} \\
S_{agg}^{(r)} &= \sum_{i ∈ S_r} s_i^{(r)}
\end{aligned}
$$

(2) 计算Delta：

$$
δ^{(r)} = ct_{agg}^{(r)} - ct_{agg}^{(r-1)} = Enc(pk, ΔG^{(r)} + ΔS^{(r)})
$$

其中：

$$
\begin{aligned}
ΔG^{(r)} &= G_{agg}^{(r)} - G_{agg}^{(r-1)} \\
ΔS^{(r)} &= S_{agg}^{(r)} - S_{agg}^{(r-1)}
\end{aligned}
$$

(3) 广播预取：

$$
AS → C_j, \quad ∀j ∉ S_r: \quad δ^{(r)}
$$

---

### 1.3 未选中客户端预取累加

**客户端 k ∉ S_r：**

(1) 接收并累加delta：

$$
ct_{prefetch,k} ← ct_{prefetch,k} + δ^{(r)}
$$

(2) 更新预取轮次记录：

$$
\begin{aligned}
r_{last,k} &← r \\
if \ r_{first,k} = None: &\quad r_{first,k} ← r
\end{aligned}
$$

---

## Phase 2：解密触发

**场景**：客户端 k 在第 r_curr 轮被选中，且 ct_prefetch,k ≠ ∅。

### 2.1 状态检查

$$
\begin{aligned}
w_{base,k} &= w^{(r_{sync,k})} \\
ct_{prefetch,k} &= \sum_{r=r_{first,k}}^{r_{last,k}} δ^{(r)}
\end{aligned}
$$

**检查是否需要fetch：**

$$
if \ r_{last,k} < r_{curr} - 1:
$$

还有未预取的delta，需要fetch。

---

### 2.2 Fetch缺失的Delta

**客户端 k 向AS请求：**

$$
MissingRounds_k = \{r_{last,k}+1, r_{last,k}+2, \ldots, r_{curr}-1\}
$$

(1) 请求：

$$
C_k → AS: \quad "Request \ deltas \ for \ rounds \ MissingRounds_k"
$$

(2) AS响应（预先同态累加）：

$$
δ_{fetch,k} = \sum_{r ∈ MissingRounds_k} δ^{(r)}
$$

(3) 客户端累加：

$$
ct_{prefetch,k} ← ct_{prefetch,k} + δ_{fetch,k}
$$

更新：

$$
r_{last,k} ← r_{curr} - 1
$$

---

### 2.3 预取密文展开

此时：

$$
ct_{prefetch,k} = \sum_{r=r_{first,k}}^{r_{curr}-1} δ^{(r)} = Enc\left(pk, G_{cum,k} + S_{cum,k}\right)
$$

其中：

$$
\begin{aligned}
G_{cum,k} &= G_{agg}^{(r_{curr}-1)} - G_{agg}^{(r_{sync,k})} = w^{(r_{curr}-1)} - w^{(r_{sync,k})} \\
S_{cum,k} &= S_{agg}^{(r_{curr}-1)} - S_{agg}^{(r_{sync,k})}
\end{aligned}
$$

---

### 2.4 掩码恢复

#### 2.4.1 下载聚合份额

客户端 k 从AS下载加密份额：

$$
\{E_k^{(r)}\}_{r=r_{first,k}}^{r_{curr}-1}, \quad where \ E_k^{(r)} = Enc(pk_k, [S_{agg}^{(r)}]_k)
$$

解密得到：

$$
\{[S_{agg}^{(r)}]_k\}_{r=r_{first,k}}^{r_{curr}-1}
$$

#### 2.4.2 本地计算累积掩码份额

$$
[S_{cum,k}]_k = [S_{agg}^{(r_{curr}-1)}]_k - [S_{agg}^{(r_{sync,k})}]_k
$$

其中 $[S_{agg}^{(r_{sync,k})}]_k$ 是客户端 k 在 $r_{sync,k}$ 轮同步时存储的。

#### 2.4.3 P2P请求其他份额

客户端 k 广播：

$$
C_k → \{C_j\}_{j ≠ k}: \quad "Request \ [S_{cum,k}]_j"
$$

在线客户端 j 响应：

(1) 下载并解密（若尚未下载）：

$$
\{[S_{agg}^{(r)}]_j\}_{r=r_{first,k}}^{r_{curr}-1}
$$

(2) 计算累积份额：

$$
[S_{cum,k}]_j = [S_{agg}^{(r_{curr}-1)}]_j - [S_{agg}^{(r_{sync,k})}]_j
$$

(3) 返回 $[S_{cum,k}]_j$ 给客户端 k。

#### 2.4.4 Shamir重构累积掩码

客户端 k 收集 t 个份额 $\{[S_{cum,k}]_j\}_{j ∈ T_k}$：

$$
S_{cum,k} = Shamir.Reconstruct\left(\{[S_{cum,k}]_j\}_{j ∈ T_k}\right)
$$

---

### 2.5 同态去掩

客户端 k 加密恢复的掩码：

$$
ct_{mask,k} = Enc(pk, S_{cum,k})
$$

执行同态减法：

$$
\boxed{ct_{plain,k} = ct_{prefetch,k} - ct_{mask,k} = Enc\left(pk, G_{cum,k}\right)}
$$

**验证：**

$$
\begin{aligned}
ct_{plain,k} &= Enc(pk, G_{cum,k} + S_{cum,k}) - Enc(pk, S_{cum,k}) \\
&= Enc(pk, G_{cum,k})
\end{aligned}
$$

---

### 2.6 P2P阈值解密

$ct_{plain,k} = (c_0, c_1)$ 是纯梯度密文。

#### 2.6.1 部分解密份额

客户端 k 自己计算：

$$
D_k = sk_k · c_1 + e_{smudge,k}
$$

其中 $e_{smudge,k} ← D_{R,σ}$，$σ ≥ 2^s · \|e_{prefetch}\|_{can}$。

向其他客户端请求 t-1 个份额。在线客户端 j 计算：

$$
D_j = sk_j · c_1 + e_{smudge,j}
$$

返回 $D_j$ 给客户端 k。

#### 2.6.2 拉格朗日组合

客户端 k 收集 t 个份额 $\{D_j\}_{j ∈ T_k}$：

$$
λ_j = \prod_{m ∈ T_k, m ≠ j} \frac{-m}{j-m} \pmod{q_ℓ}
$$

组合明文：

$$
μ_k = c_0 + \sum_{j ∈ T_k} λ_j · D_j = c_0 + c_1 · sk + e_{total,k}
$$

其中 $e_{total,k} = \sum_{j ∈ T_k} λ_j · e_{smudge,j}$。

#### 2.6.3 CKKS解码

$$
G_{cum,k} = CKKS.Decode(μ_k)
$$

---

### 2.7 模型同步与应用

客户端 k 应用累积梯度到base model：

$$
\boxed{w_{sync,k} = w_{base,k} + η · G_{cum,k}}
$$

代入：

$$
w_{sync,k} = w^{(r_{sync,k})} + η · [w^{(r_{curr}-1)} - w^{(r_{sync,k})}]
$$

当 η = 1 时：

$$
w_{sync,k} = w^{(r_{curr}-1)}
$$

**客户端模型同步到最新全局模型。**

---

### 2.8 状态更新

$$
\begin{aligned}
w_{base,k} &← w_{sync,k} \\
r_{sync,k} &← r_{curr} - 1 \\
stored\_mask\_share &← [S_{agg}^{(r_{curr}-1)}]_k \\
ct_{prefetch,k} &← ∅ \\
r_{first,k} &← None \\
r_{last,k} &← None
\end{aligned}
$$

---

## 完整闭环公式链

$$
\begin{aligned}
&加密: && ct_i^{(r)} = Enc(pk, g_i^{(r)} + s_i^{(r)}) \\
&聚合: && ct_{agg}^{(r)} = \sum_{i ∈ S_r} ct_i^{(r)} = Enc(pk, G_{agg}^{(r)} + S_{agg}^{(r)}) \\
&Delta: && δ^{(r)} = ct_{agg}^{(r)} - ct_{agg}^{(r-1)} = Enc(pk, ΔG^{(r)} + ΔS^{(r)}) \\
&预取: && ct_{prefetch,k} = \sum_{r=r_{first,k}}^{r_{last,k}} δ^{(r)} \\
&Fetch: && if \ r_{last,k} < r_{curr}-1: \quad ct_{prefetch,k} ← ct_{prefetch,k} + \sum_{r=r_{last,k}+1}^{r_{curr}-1} δ^{(r)} \\
&展开: && ct_{prefetch,k} = Enc(pk, G_{cum,k} + S_{cum,k}) \\
&其中: && G_{cum,k} = w^{(r_{curr}-1)} - w^{(r_{sync,k})} \\
& && S_{cum,k} = S_{agg}^{(r_{curr}-1)} - S_{agg}^{(r_{sync,k})} \\
&去掩: && ct_{plain,k} = ct_{prefetch,k} - Enc(pk, S_{cum,k}) = Enc(pk, G_{cum,k}) \\
&阈值解密: && G_{cum,k} = ThresholdDecrypt(ct_{plain,k}, \{sk_j\}_{j ∈ T_k}) \\
&同步: && w_{sync,k} = w_{base,k} + G_{cum,k} = w^{(r_{curr}-1)} \\
&训练: && g_k^{(r_{curr})} ← LocalTrain(D_k, w_{sync,k}, E)
\end{aligned}
$$

---

## 安全性定理

**定理1（服务器语义安全）**：AS无法从任何密文恢复明文。

**证明**：AS无sk份额，CKKS语义安全性基于RLWE假设。∎

**定理2（单客户端隔离）**：单个客户端无法恢复其他客户端的个体梯度。

**证明**：
- sk_i是(t,n)-Shamir分片，t-1个份额信息量为零
- s_j被Shamir保护，客户端i无法获取
- 即使获取sk，解密后看到的是聚合梯度Σg_j + Σs_j，个体g_j被s_j隐藏∎

**定理3（<t共谋安全）**：<t个客户端共谋无法恢复sk或任何s_i。

**证明**：Shamir的(t-1)-privacy性质，信息论安全。∎

**定理4（服务器-单客户端共谋安全）**：AS与单个客户端共谋无法恢复明文。

**证明**：AS+C_i持有1个sk份额，不足以恢复sk（t≥2）。∎

---

## 通信分析

| 操作 | 通信量 |
|------|--------|
| 选中客户端上传ct_i | O(d/S · \|ct\|) |
| 选中客户端上传份额 | O(n · \|share\|) |
| 未选中客户端下载delta | O(\|ct\|) |
| Fetch缺失delta | O(\|ct\|) |
| 阈值解密请求 | O(t · \|D_j\|) |

**净节省**：预取R轮，节省(R-1)·\|ct\|下载量，多花费t·\|ct\|/2解密开销。当R > t/2 + 1时净收益为正。
