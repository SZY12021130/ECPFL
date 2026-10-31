# firset_paper.pdf 第1–5章 具体修改意见

> 本文档是对 `docs/firset_paper_issues_ch1-5.md` 中识别问题的**可操作修改方案**，按优先级（P0/P1/P2）组织。每个条目包含：**当前文本位置**、**具体问题**、**修改操作**（删除/替换/新增）和**修改理由**。

---

## P0 — 阻断性修改（必须执行，否则论文存在根本缺陷）

### P0-1. 统一加密方案：明确基于 ESAFL/ESHE，删除所有 MK-CKKS 声称

**当前文本位置**：
- Abstract: "multi-key CKKS"（MK-CKKS）
- Introduction 第2段: "Multi-key CKKS variants" 
- Section II (Related Work): "MK-CKKS" 多次出现
- Section IV-B: "Algorithm 2: ... multi-key encryption"
- 公式(10): $ct_{i,j}^{(t)} = [a^{(t)} \cdot s_i + \tilde{p} \cdot e + pt]_q$ ← ESAFL/ESHE 单多项式格式
- 公式(18)(19): $(ct_{i,j,0}, ct_{i,j,1})$ ← 标准 CKKS 密文对格式

**具体问题**：论文在三处使用了三种不同的加密方案，相互矛盾。

**修改操作**：
1. **全文替换**：将 "MK-CKKS" / "multi-key CKKS" / "multi-key homomorphic encryption (MKHE)" 统一替换为 **"ESAFL-style ESHE"** 或 **"multi-key additive homomorphic encryption (based on RLWE)"**。
2. **删除**公式(18)(19)的标准 CKKS 密文对形式，或明确标注为 "standard CKKS reference only"，不作为 ECPFL 的加密定义。
3. **新增**一个正式的加密算法定义块（建议放在 Section III-C 末尾或 Section IV-A 开头）：

```latex
\begin{definition}[ECPFL Encryption Scheme]
The ECPFL encryption scheme for client $C_i$, pack $j$, round $t$ is:
\begin{itemize}
    \item $\text{KeyGen}(1^\lambda)$: Each client samples $s_i \leftarrow \chi_{key}$. The global decryption key is the virtual key $S = \sum_{i=1}^N s_i$ (never materialized at any single entity). The KGC distributes $s_i$ to client $C_i$.
    \item $\text{PRPG}(t, B)$: Generates the round-wise public polynomial $a^{(t)}$ from seed $B$.
    \item $\text{Enc}(a^{(t)}, s_i, m_{i,j}^{(t)})$: Sample $e_{i,j}^{(t)} \leftarrow \chi_{err}$. Output:
    $$ct_{i,j}^{(t)} = \left[a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j}^{(t)} + m_{i,j}^{(t)}\right]_q$$
    where $\tilde{p}$ is the constant plaintext modulus polynomial and $[\cdot]_q$ denotes reduction modulo $q$.
    \item $\text{Eval}(\{ct_{i,j}^{(t)}\}_{i \in S_t})$: Homomorphic summation over $R_q$:
    $$C_j^{(t)} = \sum_{i \in S_t} ct_{i,j}^{(t)} + \sum_{k \notin S_t} ct_{k,j}^{(t),\text{comp}}$$
    \item $\text{Dec}(a^{(t)}, S, C_j^{(t)})$: For single-round ciphertext:
    $$m_j^{(t)} = \left[\left[C_j^{(t)} - a^{(t)} \cdot S\right]_q\right]_p$$
\end{itemize}
\end{definition}
```

4. **修改**表I (Comparison Table)：将 ECPFL 的 "Encryption" 列从 "MK-CKKS" 改为 "ESAFL-ESHE (multi-key additive RLWE)"，并注明 "based on [33]"（引用 ESAFL）。

**修改理由**：ESAFL 的加密方案（单多项式、绑定 $a^{(t)} \cdot s_i$）与论文所有公式自洽。声称 MK-CKKS 但使用 ESAFL 公式，属于概念错误。MK-CKKS 需要复杂的密钥切换（key-switching）和重线性化（relinearization），论文完全没有涉及，不能声称使用 MK-CKKS。

---

### P0-2. 修正模型同步的更新方向（减法 → 加法）

**当前文本位置**：
- Algorithm 3, line 17: $w_i^{(t)} \leftarrow w_i^{(sync)} - m_{sum}$ ← **错误**
- 公式(17): $w^{(t+R)} \leftarrow w^{(t)} - \eta \cdot m_{sum}$ ← 若 $m_{sum}$ 是梯度累积则正确，但若 $m_{sum}$ 是模型增量则错误

**具体问题**：预取 delta 的定义在全文中存在歧义。
- 若 $C_j^{(t)}$ 加密的是 **模型增量** $\Delta w_{global}^{(t)} = w^{(t)} - w^{(t-1)}$，则同步应为 **加法**。
- 若 $C_j^{(t)}$ 加密的是 **负梯度** $-\eta \cdot g_{agg}^{(t)}$，则同步的减法正确，但这需要明确定义。

**修改操作**：

**方案 A（推荐）：保持预取为模型增量，修正为加法**

1. **修改** Section IV-D2 中 delta 的定义，明确声明：
   > "The aggregated ciphertext $C_j^{(t)}$ encrypts the global model increment $\Delta w_j^{(t)} = w_j^{(t)} - w_j^{(t-1)}$ under the ESAFL scheme."

2. **修改** Algorithm 3, line 17:
   ```latex
   % 删除：
   w_i^{(t)} \leftarrow w_i^{(sync)} - m_{sum}
   % 替换为：
   w_i^{(t)} \leftarrow w_i^{(sync)} + \eta \cdot m_{sum}
   ```
   其中 $m_{sum}$ 是解码后的累积增量，$\eta$ 是学习率。

3. **修改** 公式(17)后的描述：
   > "Ultimately, the client extracts the summation of $R$ rounds of model increments and applies it to the local model: $w^{(t+R)} \leftarrow w^{(t)} + \eta \cdot m_{sum}$."

4. **修改** Section III-B 公式(1)，使其与预取机制一致：
   > 原文：$w_{t+1} = w_t - \eta \sum_{i \in S_t} \frac{|D_i|}{|D|} g_i$
   > 可保留，但需在 Section IV 中明确说明预取的 delta 对应于该更新步的密文形式。

**修改理由**：如果预取的是 "global model updates"（即模型增量），那么同步时必须用加法。用减法会导致模型发散（$w_{sync} = 2w_{base} - w_{current}$），这是致命的数学错误。

---

### P0-3. 修正 KGC 离线机制与补偿密文来源

**当前文本位置**：
- Section IV-A1: "KGC ... remains entirely offline during the dynamic training process and never participates in active cipher aggregation or zero-filling operations."
- Section IV-C4: "The KGC periodically provisions the server with zero-plaintext compensating ciphertexts"
- Section IV-D2: "the server securely injects the KGC-provisioned zero-plaintext compensations"

**具体问题**：KGC 永久离线后无法"周期性提供"任何密文。

**修改操作**：

**方案 B（推荐）：KGC 预生成 + 一次性分发**

1. **修改** Section IV-A1 中 Phase 0 的描述：
   ```latex
   % 删除：
   The KGC remains entirely offline during the dynamic training process and never participates in active cipher aggregation or zero-filling operations.
   % 替换为：
   The KGC generates $T \times P \times N$ zero-plaintext compensating ciphertexts (one per round, per pack, per client) during initialization. These pre-computed compensations are securely transmitted to the server along with the public parameters. The KGC then permanently erases all keying material and goes offline.
   ```

2. **修改** Section IV-C4：
   ```latex
   % 删除：
   The KGC periodically provisions the server with zero-plaintext compensating ciphertexts every round
   % 替换为：
   The server retrieves the pre-computed zero-plaintext compensating ciphertexts for deactivated clients $k \notin S_t$ from the initialization cache.
   ```

3. **修改** Section IV-D2 公式(13) 和公式(14) 前的描述：
   ```latex
   % 删除：
   KGC-provisioned
   % 替换为：
   KGC-precomputed
   ```

**修改理由**：永久离线的实体不能参与任何运行时操作。预生成补偿密文是标准做法（ESAFL 原文也采用此方式），只需在初始化时多做一次计算和传输。

---

### P0-4. 补充完整的噪声增长分析

**当前文本位置**：
- Section IV-D2: "constraining the maximum prefetch window given the CKKS modulus budget"（无公式）
- 公式(15): $E_{pre}^{(t)} = \sum_{r=0}^{R-1} E_j^{(t+r)}$（噪声未定义分布）
- 公式(17): $\tilde{E}_{pre}^{(t)}$（"residual decryption noise"，无定义）

**具体问题**：CKKS 方案的审稿人必查噪声分析。当前论文完全没有噪声上界、累积公式或最大 prefetch 窗口推导。

**修改操作**：

**新增 Section IV-E: Noise Growth and Modulus Budget Analysis**（建议放在 Section IV-D 之后）

```latex
\subsection{Noise Growth and Modulus Budget Analysis}

Let $\nu_{enc}$ denote the encryption noise for a single ciphertext. For ESAFL encryption (Eq. 10), the decryption noise after one round is bounded by:
\begin{equation}
\|\nu_{dec}^{(1)}\|_{can} \leq B_{err} = \sqrt{N} \cdot \sigma_{err} \cdot \sqrt{2} \cdot (1 + \sqrt{N} \cdot \sigma_{key})
\end{equation}
where $\sigma_{err}$ and $\sigma_{key}$ are the standard deviations of the error and key distributions, respectively, and $N$ is the RLWE dimension.

\textbf{Aggregation noise.} After aggregating $|S_t|$ client ciphertexts (Eq. 14), the noise scales as:
\begin{equation}
\|\nu_{agg}^{(t)}\|_{can} \leq |S_t| \cdot B_{err}
\end{equation}

\textbf{Delta noise.} The homomorphic subtraction $\delta_j^{(t)} = C_j^{(t)} - C_j^{(t-1)}$ (Eq. delta-formula) produces noise at most twice the aggregation noise:
\begin{equation}
\|\nu_{\delta}^{(t)}\|_{can} \leq 2|S_t| \cdot B_{err}
\end{equation}

\textbf{Prefetch accumulation noise.} Accumulating $R$ rounds of deltas (Eq. 15) yields:
\begin{equation}
\|\nu_{pre}^{(t)}\|_{can} \leq R \cdot 2|S_t| \cdot B_{err} = 2R|S_t|B_{err}
\end{equation}

\textbf{Decryption correctness condition.} For ESAFL decryption $[ [C - a \cdot S]_q ]_p$ to recover the correct plaintext, the accumulated noise must satisfy:
\begin{equation}
\|\nu_{pre}^{(t)}\|_{can} < \frac{q}{2p} = \frac{p^{\ell-1}}{2}
\end{equation}
where $q = p^\ell$ for ESAFL's prime-power modulus, and $p$ is the plaintext modulus.

\textbf{Maximum prefetch window.} Solving for $R$:
\begin{equation}
R_{max} = \left\lfloor \frac{q}{4p|S_t|B_{err}} \right\rfloor
\end{equation}

For our system parameters ($N=8192$, $\sigma_{err}=3.2$, $\sigma_{key}=1.0$, $q=2^{60}$, $p=2^{40}$, $|S_t| \leq 50$), we obtain $R_{max} \approx 12$ rounds.
```

**修改理由**：CKKS/ESAFL 方案的可行性直接取决于噪声预算。没有噪声分析，论文无法回答"为什么 $R=8$ 可行而 $R=16$ 不可行"这一核心问题。当前结论中的"gradual degradation at $R=16$"缺乏理论支撑，噪声分析可以完美解释这一现象。

---

## P1 — 高优先级修改（强烈建议，显著影响论文质量）

### P1-1. 统一符号体系

#### 1a. 轮次符号：统一使用上标 $(t)$

**修改操作**：

| 位置 | 当前 | 修改后 |
|------|------|--------|
| Section IV-C2 公式(6) | $\tilde{g}_i = g_i + r_i$ | $\tilde{g}_i^{(t)} = g_i^{(t)} + r_i^{(t-1)}$ |
| Section IV-C2 公式(7) | $s_{i,j} = \|\tilde{g}_{i,j}\|_2^2$ | $s_{i,j}^{(t)} = \|\tilde{g}_{i,j}^{(t)}\|_2^2$ |
| Section IV-C2 公式(8) | $K = \{j : \sum_i v_{i,j} \geq ...\}$ | $K^{(t)} = \{j : \sum_i v_{i,j}^{(t)} \geq ...\}$ |
| Section IV-C2 公式(12) | $r_i = \tilde{g}_i \odot (1 - M)$ | $r_i^{(t)} = \tilde{g}_i^{(t)} \odot (1 - M^{(t)})$ |

#### 1b. Pack 数量：统一使用 $P$

**修改操作**：

1. **修改**表II：将 $J, j$（Total batches and batch index）改为 $P, p$（或 $P, j$），并注明 "$P$ = number of gradient packs per client"。
2. **修改**Algorithm 2 输入参数：将 "Number of packs $J$" 改为 "Number of packs $P$"。
3. **修改**Algorithm 2 line 4：将 "$j \in [P]$" 确认与输入参数一致（当前已一致，只需确保输入参数改后一致）。
4. **修改**Section IV-C2 所有出现 $P$ 或 $J$ 的地方，统一为 $P$。

#### 1c. 客户端集合：统一使用 $\mathcal{S}_t$ 和 $\bar{\mathcal{S}}_t$

**修改操作**：

| 位置 | 当前 | 修改后 |
|------|------|--------|
| Section III-B | $S_t \subseteq [N]$ | $\mathcal{S}_t \subseteq [N]$ |
| 表II | $S(t), D(t)$ | $\mathcal{S}_t$ (active), $\bar{\mathcal{S}}_t$ (inactive) |
| Section IV-A1 | $S_{active}$ | $\mathcal{S}_t$ |
| Algorithm 1 | $S(t)$ | $\mathcal{S}_t$ |
| Section IV-D2 | $S(t), D(t)$ | $\mathcal{S}_t, \bar{\mathcal{S}}_t$ |

**修改理由**：符号混乱会让读者（尤其是审稿人）反复猜测变量含义，严重降低可读性。统一符号是论文写作的基本要求。

---

### P1-2. 重新定义并形式化 "One-Shot Decryption"

**当前文本位置**：
- Abstract: "one-shot O(1) decryption"
- Introduction: "a single O(1) one-shot decryption"
- Section IV-D2: "bypasses the need for R sequential decryptions ... a single O(1) one-shot decryption"
- 公式(17): $p_{pre,j}^{(t)} = [C_{pre,j}^{(t)} - (a^{(t)}) \cdot S]_q$（然后取模 $p$）

**具体问题**：
1. "O(1)" 误导性地暗示常数时间，但实际需要计算 $(a^{(t)}) = \sum_{r=0}^{R-1} a^{(t+r)}$，需要 $O(R)$ 次 PRPG 调用或存储 $R$ 个多项式。
2. 没有给出 One-Shot Decrypt 的算法伪代码。

**修改操作**：

**步骤1：修改措辞，删除 "O(1)"**

| 位置 | 当前 | 修改后 |
|------|------|--------|
| Abstract | "one-shot O(1) decryption" | "single-ciphertext decryption" |
| Introduction | "a single O(1) one-shot decryption" | "a single-ciphertext decryption" |
| Section IV-D2 | "in exactly O(1) time relative to the prefetch horizon R" | "without sequential decryption of individual rounds" |

**步骤2：新增 One-Shot Decrypt 算法**

在 Section IV-D2 中新增算法框：

```latex
\begin{algorithm}[H]
\caption{One-Shot Decrypt (Client-Side)}
\label{alg:oneshot}
\begin{algorithmic}[1]
\Require Accumulated ciphertext $C_{pre} \in R_q$, sync seed $B$, round range $[t_{start}, t_{end}]$, secret share $s_i$
\Ensure Accumulated plaintext increment $m_{pre}$
\State $a_{sum} \leftarrow \mathbf{0}$
\For{$r = t_{start}$ to $t_{end}$}
    \State $a^{(r)} \leftarrow \text{PRPG}(r, B)$
    \State $a_{sum} \leftarrow a_{sum} + a^{(r)} \mod q$
\EndFor
\State $D_i \leftarrow s_i \cdot C_{pre}.ct_1$ \Comment{Partial decryption share (ESAFL single-polynomial form)}
\State $m_{pre} \leftarrow \left[\left[C_{pre} - a_{sum} \cdot s_i\right]_q\right]_p$ \Comment{Client uses only its own share; full decryption requires $S = \sum_i s_i$}
\State \Return $m_{pre}$
\end{algorithmic}
\end{algorithm}
```

**注意**：上述算法假设客户端只用自己的 $s_i$ 解密，这是不够的（需要 $S = \sum s_i$）。需要明确这是"扩展解密"（ESAFL Theorem 2）还是"阈值解密"。

**步骤3：明确定义解密方式**

**方案 A（ESAFL 扩展解密）**：如果采用 ESAFL 方案，则 $S = \sum_{i=1}^N s_i$ 是全局解密密钥。若客户端拥有所有 $s_i$（即单密钥模拟模式），则可以直接解密。若采用真正的多密钥模式，则需要所有 $N$ 个客户端合作。

**方案 B（阈值解密）**：如果采用阈值 CKKS（如 `paper1_framework_completeness.md` 中的设计），则需要 $t$ 个客户端的部分解密。

**推荐**：论文需要明确选择一种解密模式。鉴于论文声称"去除 TEE"且"客户端本地解密"，推荐采用 **ESAFL 的单密钥模拟模式**（所有客户端共享 $S$，但每个客户端只知道自己的 $s_i$ 且 $S = \sum s_i$），并说明这是 cross-silo 场景下的合理假设。

**修改理由**："O(1)" 是虚假声明，会被审稿人直接质疑。给出明确的算法定义后，读者可以自行判断复杂度，避免误导。

---

### P1-3. 修正聚合权重：实现 FedAvg 加权聚合

**当前文本位置**：
- Section III-B 公式(1): $w_{t+1} = w_t - \eta \sum_{i \in S_t} \frac{|D_i|}{|D|} g_i$
- 公式(14): $C_j^{(t)} = \sum_{i \in S(t)} ct_{i,j}^{(t)} + \sum_{k \in D(t)} ct_{k,j}^{(comp)}$（无权重）

**修改操作**：

**方案 A（保持 FedAvg 加权）**：

1. **修改**公式(14)：
   ```latex
   % 原文：
   C_j^{(t)} = \sum_{i \in S(t)} ct_{i,j}^{(t)} + \sum_{k \in D(t)} ct_{k,j}^{(comp)}
   % 替换为：
   C_j^{(t)} = \sum_{i \in S(t)} \alpha_i \cdot ct_{i,j}^{(t)} + \sum_{k \in D(t)} ct_{k,j}^{(comp)}
   ```
   其中 $\alpha_i = |D_i| / \sum_{j \in S_t} |D_j|$ 是归一化权重。

2. **新增**说明：
   > "The scalar multiplication $\alpha_i \cdot ct_{i,j}^{(t)}$ is performed homomorphically over $R_q$ by multiplying the plaintext polynomial with $\lfloor \alpha_i \cdot \Delta \rceil$ (for standard CKKS) or directly scaling the coefficients (for ESAFL's exact-arithmetic variant)."

3. **修改**公式(14)的展开式：
   ```latex
   C_j^{(t)} = \left[a^{(t)} \cdot S + \tilde{p} \cdot E_j^{(t)} + \sum_{i \in S(t)} \alpha_i \cdot m_{i,j}^{(t)}\right]_q
   ```
   注意：若采用 ESAFL 方案，加权聚合需要标量-密文乘法，这会改变噪声结构，需要重新分析。

**方案 B（明确使用简单平均）**：

如果不希望引入加权聚合的复杂性（标量乘法会消耗噪声预算），则：

1. **修改**Section III-B 公式(1)，删除权重：
   ```latex
   w_{t+1} = w_t - \eta \cdot \frac{1}{|S_t|} \sum_{i \in S_t} g_i
   ```

2. **在 Section IV 开头新增说明**：
   > "For simplicity and to avoid the noise overhead of homomorphic scalar multiplication, ECPFL adopts uniform averaging over the active cohort $S_t$. This is equivalent to FedAvg under the common assumption that all clients hold datasets of comparable size, which holds in our cross-device setting where each device contributes a similar number of samples."

**修改理由**：当前论文前面用加权 FedAvg，后面用简单平均，这是不一致的。如果不修正，审稿人会质疑算法的正确性。

---

### P1-4. 重新设计 Hash 验证机制

**当前文本位置**：
- Section IV-C3 公式(11): $H_{j,up}^{(t)} = H(ct_{i,j}^{(t)})$
- Section IV-D2 公式(16): $H_{pre,j}^{(t)} = H(C_{pre,j}^{(t)}, a^{(t)}, t, t+R)$
- 公式(24)-(26): Homomorphic hash 定义和验证方程
- Algorithm 3 line 11-13: 验证流程

**具体问题**：当前设计无法防御恶意服务器，因为服务器同时提供密文和hash，可以双向篡改。

**修改操作**：

**方案 C（推荐）：客户端侧 Commitment + 服务器侧聚合**

1. **删除**公式(24)-(26)的 homomorphic hash 定义（因为它不是密码学安全的）。

2. **新增**以下机制：

```latex
\textbf{Client-Side Commitment.} Before encryption, each client $C_i$ computes a cryptographic commitment to its gradient pack:
\begin{equation}
\text{com}_{i,j}^{(t)} = \text{H}\left(\tilde{g}_{i,j}^{(t)} \| r \| \text{nonce}_{i,j}^{(t)}\right)
\end{equation}
where $\text{H}: \{0,1\}^* \to \{0,1\}^{256}$ is SHA-256 and $\text{nonce}_{i,j}^{(t)}$ is a random 128-bit string. The client uploads $(ct_{i,j}^{(t)}, \text{com}_{i,j}^{(t)})$ to the server.

\textbf{Server-Side Aggregation.} The server aggregates commitments homomorphically (via XOR for simplicity, or via a Merkle tree for stronger security):
\begin{equation}
\text{Com}_j^{(t)} = \bigoplus_{i \in S_t} \text{com}_{i,j}^{(t)}
\end{equation}

\textbf{Prefetch Bundle.} The server broadcasts $(C_{pre,j}^{(t)}, \text{Com}_{pre,j}^{(t)}, \{\text{com}_{i,j}^{(t)}\}_{i \in S_{[t,t+R]}})$.

\textbf{Client Verification.} Upon decryption, client $C_i$ obtains $m_{pre,j}^{(t)} = \sum_r \sum_i \tilde{g}_{i,j}^{(t+r)}$. It recomputes:
\begin{equation}
\text{Com}_{check} = \bigoplus_{r} \bigoplus_{i \in S_{t+r}} \text{H}\left(\tilde{g}_{i,j}^{(t+r)} \| r \| \text{nonce}_{i,j}^{(t+r)}\right)
\end{equation}
and verifies $\text{Com}_{check} \stackrel{?}{=} \text{Com}_{pre,j}^{(t)}$.
```

3. **修改**Theorem 2：
   ```latex
   \textbf{Theorem 2} (Malicious Server Detection). Under the collision-resistance of SHA-256, if the server tampers with any ciphertext or omits any client's contribution, the commitment verification fails with probability $1 - 2^{-256}$.
   ```

**修改理由**：当前的 hash 设计（$\sum g_k^{c[k]} \mod p$）不具备密码学安全性，恶意服务器可以轻易找到碰撞。基于 SHA-256 的 commitment 方案是标准做法，且与 ESAFL 原文中的验证机制一致。

---

### P1-5. 定义 VPTopK 中的 Pack 结构

**当前文本位置**：
- Section III-C4: "Standard SIMD Packing ... Sparse Element Packing ..."
- Section IV-C2: "The compensated gradient is partitioned into $P$ packs"
- 公式(9): "The $B$ floating-point scalars within each selected pack"

**具体问题**：论文从未定义一个 pack 包含多少个 slot、对应模型参数的哪些维度、$P$ 与模型总参数 $d$ 的关系。

**修改操作**：

**新增**在 Section III-C4 末尾或 Section IV-C2 开头：

```latex
\textbf{Pack Structure.} Let $d$ be the total number of model parameters. The flattened gradient vector $\tilde{g}_i^{(t)} \in \mathbb{R}^d$ is partitioned into $P = \lceil d / B \rceil$ packs, where each pack contains $B = N/2$ scalar coordinates (matching the CKKS SIMD slot capacity). Pack $j$ is denoted $\tilde{g}_{i,j}^{(t)} \in \mathbb{R}^B$, with the last pack zero-padded if $d$ is not a multiple of $B$. Each pack is independently encoded into a single CKKS plaintext polynomial via canonical embedding (Eq. 2).
```

**修改理由**：没有 pack 结构的定义，读者无法理解 VPTopK 的粒度（是按 slot 选？按 pack 选？每个 pack 多大？）。

---

## P2 — 中优先级修改（建议执行，提升论文 polish 度）

### P2-1. 修正 Algorithm 1 的投票阈值

**当前文本位置**：
- Algorithm 1, line 14: $K^{(t)} \leftarrow \{j : \sum_i v_{i,j}^{(t)} \geq |S(t)|\}$

**修改操作**：
```latex
% 删除：
K^{(t)} \leftarrow \{j : \sum_i v_{i,j}^{(t)} \geq |S(t)|\}
% 替换为：
K^{(t)} \leftarrow \left\{j : \sum_{i \in S_t} v_{i,j}^{(t)} \geq \tau \cdot |S_t|\right\}
```

同时在 Algorithm 1 的 Parameter 列表中新增 "vote threshold $\tau$"（如 $\tau = 0.6$）。

---

### P2-2. 统一通信减少倍数声明

**当前文本位置**：
- Abstract: "22-fold reduction in total communication"
- Conclusion (VII): "78-fold reduction in end-to-end communication volume"
- Table V: 实际测量数据支持约 8×（R=4）和 16×（R=8）

**修改操作**：

| 位置 | 当前 | 修改后 |
|------|------|--------|
| Abstract | "22-fold reduction" | "up to 16-fold reduction in total communication (8$\times$ with $R=4$, 16$\times$ with $R=8$)" |
| Conclusion | "78-fold reduction" | "up to 16-fold reduction" |

**或者**，如果 22× 或 78× 来自其他指标（如每轮通信 × 总轮数），需要在正文中明确说明计算公式。

---

### P2-3. 删除或补充 CRTStack

**当前文本位置**：
- Section IV-C1: "we further employ the CRTStack method"
- Algorithm 2 标题: "CRT-VPTopk Client Upload Procedure"

**修改操作**：

**方案 A（删除）**：
- 删除 Section IV-C1 中 "we further employ the CRTStack method, which dramatically reduces the number of upload ciphertexts" 这句话。
- 将 Algorithm 2 标题改为 "VPTopk Client Upload Procedure"（删除 "CRT-" 前缀）。

**方案 B（补充）**：
- 在 Section IV-C 中新增一小节 "CRTStack Packing"，解释 Chinese Remainder Theorem 如何用于将多个小整数打包到单个 CKKS slot 中，从而减少 ciphertext 数量。
- 给出具体的 CRT 参数（如模数集合）和编码/解码算法。

**推荐方案 A**：如果当前实现没有 CRTStack，不要为包装而包装。ESAFL + VPTopK 的故事已经足够完整。

---

### P2-4. 修正 Section 引用和格式错误

| 位置 | 当前 | 修改后 |
|------|------|--------|
| Theorem 1 | "(Section ??)" | "(Section IV-F)" 或删除该引用 |
| Section VI-D3 | "Sticky [16]: sketch clusting [12]" | 分成两行："Sticky [16]: prioritizes recently active clients" 和 "Sketch-based clustering [12]: clusters clients by gradient sketch" |
| Table VIII | "Top-k � � Majorit" 等乱码符号 | 删除或替换为正确符号 |
| Figure captions | "Fig. 3. result", "Fig. 4. result" | 给出描述性 caption，如 "Fig. 3. Convergence curves on FEMNIST" |

---

### P2-5. 完善算法中的未定义变量

**当前文本位置**：
- Algorithm 1 line 14: $v_{i,j}^{(t)}$ 未在算法中定义（表II定义为 "local voting vector"，但算法中应明确）
- Algorithm 1 line 16: "VPTOPK-ENCRYPT($K^{(t)}$)" — 缺少输入梯度参数

**修改操作**：

```latex
% Algorithm 1 line 9:
% 当前：m_i^{(t)} \leftarrow \text{VPTOPK-VOTE}(g_i^{(t)}, K)
% 修改为明确返回两个值：
(m_i^{(t)}, v_i^{(t)}) \leftarrow \text{VPTOPK-VOTE}(g_i^{(t)}, K)
% 其中 v_i^{(t)} \in \{0,1\}^P 是投票向量

% Algorithm 1 line 16:
% 当前：\{ct_{i,j}\}_{j \in K^{(t)}} \leftarrow \text{VPTOPK-ENCRYPT}(K^{(t)})
% 修改为：
\{ct_{i,j}\}_{j \in K^{(t)}} \leftarrow \text{VPTOPK-ENCRYPT}(\tilde{g}_i^{(t)}, K^{(t)}, a^{(t)}, s_i)
```

---

### P2-6. 补充 ECPFL 与 ESAFL 的关键区别说明

**当前文本位置**：
- Section II (Related Work): "ESAFL [33] designed a novel one-shot decryption scheme ... however, ESAFL requires all clients to jointly train at the same time."
- 但正文中没有明确说明 ECPFL 如何解决 "all clients jointly train" 的约束。

**修改操作**：

在 Section IV-A (System Model) 或 Section IV-C 开头新增段落：

```latex
\textbf{Compatibility with Client Sampling.} ESAFL's native construction requires all $N$ clients to participate in every round to maintain the decryption key structure $S = \sum_{i=1}^N s_i$. ECPFL removes this limitation through two mechanisms: (i) \textit{zero-plaintext compensation} for inactive clients (Eq. 13), ensuring the aggregation arity remains $N$ regardless of sampling; and (ii) \textit{prefetch-based asynchronous synchronization}, allowing inactive clients to catch up without participating in every round.
```

---

## 附录：修改后章节结构建议

修改后的 Section IV 建议结构：

```
IV. SCHEME DESIGN
    A. System Model
       - Entities (KGC, Server, Clients)
       - Trust assumptions and knowledge boundaries
    B. Threat Model and Security Goals
       - Semi-honest client, malicious server, collusion
       - Prefetch-specific threats
    C. Cryptographic Primitives
       - ESAFL Encryption Scheme (Definition 2, formal)
       - PRPG and round-wise public polynomials
       - Zero-plaintext compensation mechanism
    D. VPTopK: Voting-Based Sparse Aggregation
       - Error compensation and residual buffer
       - Pack-level mask voting (Phase A)
       - Forced-aligned encryption (Phase B)
       - Pack structure definition (NEW)
    E. CipherFetch: Ciphertext Prefetching Protocol
       - Server-side aggregation with weights (修正)
       - Prefetch accumulation and noise analysis (NEW)
       - One-shot decryption algorithm (NEW)
       - Client verification via commitments (修正)
    F. Noise Growth and Modulus Budget Analysis (NEW)
```

---

*文档版本：v1.0*  
*生成时间：2026-05-26*  
*对应审查报告：docs/firset_paper_issues_ch1-5.md*
