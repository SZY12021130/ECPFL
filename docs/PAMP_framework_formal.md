# Peer-Assisted Masked Prefetch (PAMP)
## 对等辅助掩码预取：基于CKKS的隐私保护联邦学习通信优化

---

## 1 符号定义（全局统一）

### 1.1 系统参数

| 符号 | 含义 | 取值/范围 |
|------|------|----------|
| n | 客户端总数 | 10~1000 |
| t | Shamir阈值 | ⌈2n/3⌉ |
| T | 总训练轮次 | 100~10000 |
| r ∈ {0,1,...,T} | 绝对轮次（全局计数） | r=0为初始状态 |
| N | CKKS多项式次数 | 8192 |
| B | 掩码范围 | 2^20 |
| η | 学习率 | 1.0（简化假设） |

### 1.2 模型与梯度

| 符号 | 含义 | 公式 |
|------|------|------|
| w^(r) | **第r轮训练完成后的全局模型** | w^(r) = w^(r-1) + η·G_agg^(r) |
| w^(0) | 初始全局模型 | 随机初始化 |
| g_i^(r) | 客户端i在第r轮的本地梯度 | LocalTrain(D_i, w^(r-1)) |
| G_agg^(r) | 第r轮聚合梯度 | Σ_{i∈S_r} g_i^(r) |

**关键公式**：

$$
w^{(r)} = w^{(r-1)} + \eta \cdot G_{\text{agg}}^{(r)}
$$

当 η = 1 时：

$$
w^{(r)} - w^{(r-1)} = G_{\text{agg}}^{(r)}
$$

### 1.3 密钥与加密

| 符号 | 含义 |
|------|------|
| pk, sk | CKKS聚合公钥/私钥 |
| sk_i | 客户端i持有的私钥份额（Shamir分片） |
| evk | CKKS评估密钥 |

### 1.4 掩码

| 符号 | 含义 | 生成方式 |
|------|------|---------|
| s_i^(r) | 客户端i在第r轮的自掩码 | s_i^(r) ← U(-B, B) |
| S_agg^(r) | 第r轮聚合自掩码 | Σ_{i∈S_r} s_i^(r) |
| [s_i^(r)]_j | s_i^(r)的Shamir第j份份额 | Shamir.Split(s_i^(r), n, t) |

### 1.5 密文

| 符号 | 含义 | 公式 |
|------|------|------|
| ct_i^(r) | 客户端i上传的密文 | Enc(pk, g_i^(r) + s_i^(r)) |
| ct_agg^(r) | 第r轮聚合密文 | Σ_{i∈S_r} ct_i^(r) |
| δ^(r) | 第r轮delta密文 | ct_agg^(r) - ct_agg^(r-1) |

### 1.6 客户端状态

| 符号 | 含义 | 初始值 |
|------|------|--------|
| w_base,k | 客户端k的基准模型 | w^(0) |
| r_sync,k | 客户端k上次同步的轮次 | 0 |
| ct_prefetch,k | 客户端k预取的密文累加器 | ∅ |
| r_first,k | 客户端k开始预取的轮次 | None |
| r_last,k | 客户端k结束预取的轮次 | None |
| stored_mask_k | 客户端k存储的聚合掩码份额 | [S_agg^(0)]_k = 0 |

---

## 2 服务器存储信息

### 2.1 AS存储内容

| 类型 | 内容 | 加密状态 |
|------|------|---------|
| **公钥** | pk, evk | 公开 |
| **历史聚合密文** | {ct_agg^(r)}_{r=1}^T | CKKS密文 |
| **历史delta密文** | {δ^(r)}_{r=1}^T | CKKS密文 |
| **加密掩码份额** | {enc_{i→j}^(r)} | **用客户端j的公钥加密** |
| **客户端元数据** | {r_sync,k, w_base,k} | 明文 |

### 2.2 AS不存储（也无法获取）

- ❌ 私钥 sk 或任何 sk_i
- ❌ 明文梯度 g_i^(r)
- ❌ 明文掩码 s_i^(r)
- ❌ 聚合掩码 S_agg^(r) 的明文

---

## 3 客户端两种状态

### 3.1 类型A：有同步记录（之前被选中训练过）

**特征**：r_sync,k > 0，w_base,k = w^(r_sync,k)

**示例**：
```
客户端k：
  第3轮被选中训练 → r_sync,k = 3, w_base,k = w^(3)
  第4轮：未选中，开始预取
    接收 δ^(4) = Enc(pk, [w^(4)-w^(3)] + [S_agg^(4)-S_agg^(3)])
    ct_prefetch = δ^(4)
    r_first,k = 4, r_last,k = 4
  
  第5轮：未选中，继续预取
    接收 δ^(5)
    ct_prefetch = δ^(4) + δ^(5)
    r_last,k = 5
  
  第6轮：被选中
    需要解密
    ct_prefetch = δ^(4) + δ^(5) = Enc(pk, [w^(5)-w^(3)] + [S_agg^(5)-S_agg^(3)])
    
    去掩需要：S_cum = S_agg^(5) - S_agg^(3)
    
    阈值解密后：G_cum = w^(5) - w^(3)
    
    应用更新：w_sync = w_base,k + G_cum = w^(3) + (w^(5) - w^(3)) = w^(5)
```

### 3.2 类型B：无同步记录（从未被选中过）

**特征**：r_sync,k = 0，w_base,k = w^(0)

**示例**：
```
客户端m（新加入）：
  r_sync,m = 0, w_base,m = w^(0)
  
  第1轮：未选中，开始预取
    接收 δ^(1) = Enc(pk, [w^(1)-w^(0)] + [S_agg^(1)-S_agg^(0)])
    注意：S_agg^(0) = 0（初始状态无掩码）
    ct_prefetch = δ^(1)
    r_first,m = 1, r_last,m = 1
  
  第2轮：未选中，继续预取
    接收 δ^(2)
    ct_prefetch = δ^(1) + δ^(2)
    r_last,m = 2
  
  第3轮：被选中
    需要解密
    ct_prefetch = δ^(1) + δ^(2) = Enc(pk, [w^(2)-w^(0)] + [S_agg^(2)-S_agg^(0)])
    
    去掩需要：S_cum = S_agg^(2) - S_agg^(0) = S_agg^(2)
    
    阈值解密后：G_cum = w^(2) - w^(0)
    
    应用更新：w_sync = w_base,m + G_cum = w^(0) + (w^(2) - w^(0)) = w^(2)
```

---

## 4 Phase 0：初始化

### 4.1 KGC执行

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
(sk_i) &→ C_i \quad \text{(安全通道)}
\end{aligned}
$$

(4) KGC销毁所有密钥材料，永久离线。

---

## 5 Phase 1：每轮训练与预取

### 5.1 被选中的客户端

**客户端 i ∈ S_r：**

(1) 本地训练（使用最新全局模型）：

$$
g_i^{(r)} ← LocalTrain(D_i, w^{(r-1)}, E)
$$

**注意**：使用 w^(r-1)，不是 w_base,i。

(2) 生成自掩码并Shamir分片：

$$
\begin{aligned}
s_i^{(r)} &← U(-B, B) \\
\{[s_i^{(r)}]_1, \ldots, [s_i^{(r)}]_n\} &← Shamir.Split(s_i^{(r)}, n, t)
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

### 5.2 服务器聚合与广播

**AS在第r轮：**

(1) 同态聚合：

$$
ct_{agg}^{(r)} = \sum_{i ∈ S_r} ct_i^{(r)} = Enc\left(pk, G_{agg}^{(r)} + S_{agg}^{(r)}\right)
$$

其中：

$$
\begin{aligned}
G_{agg}^{(r)} &= \sum_{i ∈ S_r} g_i^{(r)} \\
S_{agg}^{(r)} &= \sum_{i ∈ S_r} s_i^{(r)}
\end{aligned}
$$

(2) 计算Delta：

$$
δ^{(r)} = ct_{agg}^{(r)} - ct_{agg}^{(r-1)}
$$

展开：

$$
\begin{aligned}
δ^{(r)} &= Enc\left(pk, G_{agg}^{(r)} + S_{agg}^{(r)}\right) - Enc\left(pk, G_{agg}^{(r-1)} + S_{agg}^{(r-1)}\right) \\
&= Enc\left(pk, [G_{agg}^{(r)} - G_{agg}^{(r-1)}] + [S_{agg}^{(r)} - S_{agg}^{(r-1)}]\right)
\end{aligned}
$$

令：

$$
\begin{aligned}
ΔG^{(r)} &= G_{agg}^{(r)} - G_{agg}^{(r-1)} \\
ΔS^{(r)} &= S_{agg}^{(r)} - S_{agg}^{(r-1)}
\end{aligned}
$$

则：

$$
δ^{(r)} = Enc(pk, ΔG^{(r)} + ΔS^{(r)})
$$

**物理意义**：
- ΔG^(r) = G_agg^(r) - G_agg^(r-1) = [w^(r) - w^(r-1)] - [w^(r-1) - w^(r-2)] = w^(r) - 2w^(r-1) + w^(r-2)（当η=1时）

**简化表达**（望远镜累加后）：

$$
\sum_{r=a}^{b} δ^{(r)} = Enc\left(pk, [G_{agg}^{(b)} - G_{agg}^{(a-1)}] + [S_{agg}^{(b)} - S_{agg}^{(a-1)}]\right)
$$

当η=1时：

$$
G_{agg}^{(b)} - G_{agg}^{(a-1)} = w^{(b)} - w^{(a-1)}
$$

(3) 广播预取：

$$
AS → C_j, \quad ∀j ∉ S_r: \quad δ^{(r)}
$$

---

### 5.3 未选中客户端预取累加

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

## 6 Phase 2：解密触发

**场景**：客户端 k 在第 r_curr 轮被选中，且 ct_prefetch,k ≠ ∅。

### 6.1 状态检查

客户端 k 的当前状态：

$$
\begin{aligned}
w_{base,k} &= w^{(r_{sync,k})} \quad \text{（上次同步的全局模型）} \\
ct_{prefetch,k} &= \sum_{r=r_{first,k}}^{r_{last,k}} δ^{(r)} \quad \text{（预取的delta累加）}
\end{aligned}
$$

**检查是否需要fetch：**

$$
if \ r_{last,k} < r_{curr} - 1: \quad \text{需要fetch缺失的delta}
$$

---

### 6.2 Fetch缺失的Delta

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

### 6.3 预取密文展开

此时：

$$
ct_{prefetch,k} = \sum_{r=r_{first,k}}^{r_{curr}-1} δ^{(r)}
$$

展开（望远镜求和）：

$$
ct_{prefetch,k} = Enc\left(pk, [G_{agg}^{(r_{curr}-1)} - G_{agg}^{(r_{sync,k})}] + [S_{agg}^{(r_{curr}-1)} - S_{agg}^{(r_{sync,k})}]\right)
$$

令：

$$
\begin{aligned}
G_{cum,k} &= G_{agg}^{(r_{curr}-1)} - G_{agg}^{(r_{sync,k})} = w^{(r_{curr}-1)} - w^{(r_{sync,k})} \\
S_{cum,k} &= S_{agg}^{(r_{curr}-1)} - S_{agg}^{(r_{sync,k})}
\end{aligned}
$$

则：

$$
\boxed{ct_{prefetch,k} = Enc\left(pk, G_{cum,k} + S_{cum,k}\right)}
$$

**物理意义**：
- G_cum,k = w^(r_curr-1) - w^(r_sync,k)：从上次同步到当前之间的**全局模型变化量**
- S_cum,k：同一时期内的**累积掩码**

---

### 6.4 掩码恢复

#### 6.4.1 下载聚合份额

客户端 k 从AS下载加密份额：

$$
\{E_k^{(r)}\}_{r=r_{first,k}}^{r_{curr}-1}, \quad E_k^{(r)} = Enc(pk_k, [S_{agg}^{(r)}]_k)
$$

解密得到：

$$
\{[S_{agg}^{(r)}]_k\}_{r=r_{first,k}}^{r_{curr}-1}
$$

#### 6.4.2 本地计算累积掩码份额

$$
[S_{cum,k}]_k = [S_{agg}^{(r_{curr}-1)}]_k - [S_{agg}^{(r_{sync,k})}]_k
$$

其中 $[S_{agg}^{(r_{sync,k})}]_k$ 是客户端 k 在 $r_{sync,k}$ 轮同步时存储的（见6.8节）。

#### 6.4.3 P2P请求其他份额

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

#### 6.4.4 Shamir重构累积掩码

客户端 k 收集 t 个份额 $\{[S_{cum,k}]_j\}_{j ∈ T_k}$：

$$
S_{cum,k} = Shamir.Reconstruct\left(\{[S_{cum,k}]_j\}_{j ∈ T_k}\right)
$$

---

### 6.5 同态去掩

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

### 6.6 P2P阈值解密

$ct_{plain,k} = (c_0, c_1)$ 是纯梯度密文。

#### 6.6.1 部分解密份额

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

#### 6.6.2 拉格朗日组合

客户端 k 收集 t 个份额 $\{D_j\}_{j ∈ T_k}$：

$$
λ_j = \prod_{m ∈ T_k, m ≠ j} \frac{-m}{j-m} \pmod{q_ℓ}
$$

组合明文：

$$
μ_k = c_0 + \sum_{j ∈ T_k} λ_j · D_j = c_0 + c_1 · sk + e_{total,k}
$$

其中 $e_{total,k} = \sum_{j ∈ T_k} λ_j · e_{smudge,j}$。

#### 6.6.3 CKKS解码

$$
G_{cum,k} = CKKS.Decode(μ_k)
$$

---

### 6.7 模型同步与应用

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
\boxed{w_{sync,k} = w^{(r_{curr}-1)}}
$$

**客户端模型同步到最新全局模型。**

---

### 6.8 状态更新

客户端 k 更新本地状态：

$$
\begin{aligned}
w_{base,k} &← w_{sync,k} = w^{(r_{curr}-1)} \\
r_{sync,k} &← r_{curr} - 1 \\
stored\_mask\_share_k &← [S_{agg}^{(r_{curr}-1)}]_k \quad \text{（供下次预取使用）} \\
ct_{prefetch,k} &← ∅ \\
r_{first,k} &← None \\
r_{last,k} &← None
\end{aligned}
$$

---

## 7 完整闭环公式链

$$
\begin{aligned}
&\textbf{训练:} && g_i^{(r)} ← LocalTrain(D_i, w^{(r-1)}, E) \\
&\textbf{加密:} && ct_i^{(r)} = Enc(pk, g_i^{(r)} + s_i^{(r)}) \\
&\textbf{聚合:} && ct_{agg}^{(r)} = \sum_{i ∈ S_r} ct_i^{(r)} = Enc(pk, G_{agg}^{(r)} + S_{agg}^{(r)}) \\
&\textbf{Delta:} && δ^{(r)} = ct_{agg}^{(r)} - ct_{agg}^{(r-1)} = Enc(pk, ΔG^{(r)} + ΔS^{(r)}) \\
&\textbf{预取:} && ct_{prefetch,k} = \sum_{r=r_{first,k}}^{r_{last,k}} δ^{(r)} \\
&\textbf{Fetch:} && if \ r_{last,k} < r_{curr}-1: \quad ct_{prefetch,k} ← ct_{prefetch,k} + \sum_{r=r_{last,k}+1}^{r_{curr}-1} δ^{(r)} \\
&\textbf{展开:} && ct_{prefetch,k} = Enc(pk, G_{cum,k} + S_{cum,k}) \\
&\textbf{其中:} && G_{cum,k} = w^{(r_{curr}-1)} - w^{(r_{sync,k})} \\
& && S_{cum,k} = S_{agg}^{(r_{curr}-1)} - S_{agg}^{(r_{sync,k})} \\
&\textbf{去掩:} && ct_{plain,k} = ct_{prefetch,k} - Enc(pk, S_{cum,k}) = Enc(pk, G_{cum,k}) \\
&\textbf{阈值解密:} && G_{cum,k} = ThresholdDecrypt(ct_{plain,k}, \{sk_j\}_{j ∈ T_k}) \\
&\textbf{同步:} && w_{sync,k} = w_{base,k} + G_{cum,k} = w^{(r_{curr}-1)} \\
&\textbf{训练:} && g_k^{(r_{curr})} ← LocalTrain(D_k, w_{sync,k}, E)
\end{aligned}
$$

---

## 8 安全性定理

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

## 9 通信分析

| 操作 | 通信量 | 说明 |
|------|--------|------|
| 选中客户端上传ct_i | O(d/S · \|ct\|) | 加密梯度 |
| 选中客户端上传份额 | O(n · \|share\|) | 加密掩码份额 |
| 未选中客户端下载delta | O(\|ct\|) | 预取 |
| Fetch缺失delta | O(\|ct\|) | 补全 |
| 阈值解密请求 | O(t · \|D_j\|) | t个部分解密份额 |

**净节省**：预取R轮，节省(R-1)·\|ct\|下载量，多花费t·\|ct\|/2解密开销。当R > t/2 + 1时净收益为正。
