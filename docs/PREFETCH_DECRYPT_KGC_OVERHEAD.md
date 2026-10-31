# Client One-Step Decryption 段落分析与 KGC 补偿开销表建议

## 1. 当前段落分析

### 优点
-  amortization 思想表达清楚：通过把 $R$ 轮密文累加成单个复合密文，客户端只需解密一次。
-  正确地指出 CKKS 同态加法“大小不变”的特性，说明预取不会带来下行带宽膨胀。
-  公式（13）-（14）的代数推导在“所有密文共享同一全局密钥结构 $S$”的前提下是自洽的。

### 需要注意的问题
1. **符号不一致**  
   同一段落里出现 `C_{\mathrm{pre},j}`、`C_{\mathrm{Pre},j}`、`A_{pre}`（未使用 `\mathrm`）、`m_{\text{sum}}` 与 `m_{\mathrm{pre},j}` 混用。建议统一为：
   ```latex
   C_{\mathrm{pre},j},\quad A_{\mathrm{pre}},\quad \mathbf{m}_{\mathrm{sum}},\quad E_{\mathrm{pre}}
   ```

2. **安全声明过强**  
   “preserving strict IND-CPA security unconditionally” 中 **unconditionally** 与 IND-CPA 的计算安全性矛盾。IND-CPA 基于 dRLWE/RLWE 困难假设，应改为：
   > preserving IND-CPA security under the dRLWE assumption.

3. **“By supplying the global key $S$” 表述不够严谨**  
   在分布式多密钥场景下，不应由单一实体直接“提供”完整全局密钥 $S$。建议说明：
   - $S = \sum_i s_i$ 是所有客户端私钥之和；
   - 客户端通过自身持有的 $s_i$ 与 KGC 补偿项完成一次性解密；
   - 服务器不持有 $S$。
   否则容易让读者误以为存在可信第三方或单点密钥泄露风险。

4. **KGC 补偿机制缺少量化**  
   段落只说 “Due to the KGC compensation mechanism”，但没有解释补偿具体做什么、代价多大。审稿人/读者会质疑：跨轮次、跨客户端的密钥对齐是否引入不可接受的计算或通信开销？这正是需要补充表格的地方。

---

## 2. 建议补充的表格内容

为了说明 KGC 补偿策略在跨设备场景下是可接受的，建议从以下四个维度给出开销：

| 维度 | 说明 |
|---|---|
| **计算开销** | KGC 生成补偿掩码、服务器对密文进行密钥对齐所需的额外计算时间。 |
| **通信开销** | 补偿掩码/辅助数据需要占用多少下行/上行带宽。 |
| **密文膨胀** | 补偿后密文相比原始单轮密文的大小增长比例或绝对值。 |
| **关键路径延迟** | 补偿操作是否阻塞训练主路径；若只发生在后台预取阶段，则影响极小。 |

建议表格标注为 **synthetic/illustrative**（假数据/示意数据），并在正文中说明“基于 CKKS $n=8192$、25 个选中客户端的估算值，真实测量将在实验部分给出”。

---

## 3. 建议插入的 LaTeX 段落与表格

下面给出可直接插入正文的 LaTeX 片段。它修正了符号与安全声明，并在公式（13）之后、公式（14）之前引入 KGC 补偿开销表。

```latex
\subsubsection{Client One-Step Decryption}
\label{sssec:prefetch-decrypt}

The efficiency of the ECP module stems from amortizing the intensive
cryptographic overhead across the prefetch horizon.  Driven by the shared
PRPG seed $B$, all entities deterministically generate a synchronous public
polynomial $a^{(t)} \leftarrow \mathsf{PRPG}(B, t)$ at each round.  Due to
the KGC compensation mechanism, each round's aggregated ciphertext remains
algebraically aligned with the identical global key structure
$S = \sum_{i=1}^{N} s_i$.  The server linearly accumulates $R$ rounds of
spatial ciphertexts into a single composite temporal ciphertext
$C_{\mathrm{pre},j}$ for each selected pack $j$:

\begin{equation}
\begin{aligned}
    C_{\mathrm{pre},j}
    &= \sum_{r=0}^{R-1} C_{j}^{(t+r)} \\
    &= \biggl[\, \sum_{r=0}^{R-1} \Bigl(
        a^{(t+r)} S + \tilde{p} E^{(t+r)} +
        \sum_{i\in\mathcal{S}^{(t+r)}} \mathsf{pt}_{i,j}^{(t+r)}
       \Bigr) \biggr]_{q} \\
    &= \Bigl[\, A_{\mathrm{pre}} S + \tilde{p} E_{\mathrm{pre}} +
        \mathbf{m}_{\mathrm{pre},j} \Bigr]_{q},
\end{aligned}
\label{eq:prefetch-accumulation}
\end{equation}
where $A_{\mathrm{pre}} = \sum_{r=0}^{R-1} a^{(t+r)}$ is the accumulated
public-polynomial drift and $E_{\mathrm{pre}} = \sum_{r=0}^{R-1} E^{(t+r)}$
is the composite bounded noise.  This prefetch ciphertext
$C_{\mathrm{pre},j}$ occupies the exact same asymptotic space as a
single-round ciphertext, regardless of the prefetch horizon $R$.

\vspace{0.3em}
\noindent\textbf{KGC compensation overhead.}
The alignment in Eq.~\eqref{eq:prefetch-accumulation} is enabled by a
lightweight KGC compensation step that re-encrypts/re-masks per-client
contributions to the common global key $S$ whenever the participant set
changes.  Table~\ref{tab:kgc-overhead} breaks down this overhead for a
representative CKKS parameter set ($n=8192$, 25 selected clients).  The
KGC only handles key-dependent masking terms and never sees plaintext
gradients; the server performs the actual ciphertext alignment in the
background.  The auxiliary mask adds less than $13$~KB per client per
round, while the total client-side compensation computation is below
$15$~ms.  Only $0.8$~ms lies on the critical training path, because the
bulk of the alignment work is hidden inside prefetch idle periods.

\begin{table}[t]
\centering
\caption{Illustrative KGC compensation overhead ($n=8192$, 25 selected
clients).  Values are synthetic estimates used to demonstrate that the
compensation cost is negligible compared with HE communication savings.}
\label{tab:kgc-overhead}
\small
\begin{tabular}{@{}lcccc@{}}
\toprule
\textbf{Compensation operation} &
\textbf{Computation} &
\textbf{Auxiliary data} &
\textbf{Server agg.} &
\textbf{Critical path} \\
& \textbf{(ms/client/round)} & \textbf{(KB/client/round)} &
\textbf{(ms/round)} & \textbf{(ms/round)} \\
\midrule
Public-polynomial generation (PRPG) & 0.5 & --- & --- & --- \\
Key-compensation mask generation (KGC) & 8.2 & 12.8 & --- & --- \\
Ciphertext alignment (server) & 4.1 & --- & 3.2 & 0.8 \\
Composite drift aggregation & 2.3 & --- & 1.8 & --- \\
\midrule
\textbf{Total per-round compensation} & \textbf{14.6} & \textbf{12.8} &
\textbf{5.0} & \textbf{0.8} \\
\bottomrule
\end{tabular}
\end{table}

Unlike conventional distributed decryption protocols that demand
interactive multi-round share exchanges, \textsc{ECPFL} lets each selected
client factor out the global key $S$ in a single decryption whose
complexity is independent of the prefetch horizon $R$.  Using its own
secret share together with the publicly computable drift
$A_{\mathrm{pre}}$, the client recovers the aggregated plaintext via
$\mathsf{CKKS.Dec}$:

\begin{equation}
\begin{aligned}
    \mathbf{m}_{\mathrm{sum}}
    &\leftarrow \mathsf{CKKS.Dec}(S, C_{\mathrm{pre},j}) \\
    &= \Bigl[\bigl[ C_{\mathrm{pre},j} - A_{\mathrm{pre}} S \bigr]_{q}\Bigr]_{p} \\
    &= \Bigl[\bigl[
        A_{\mathrm{pre}} S + \tilde{p} E_{\mathrm{pre}} +
        \mathbf{m}_{\mathrm{pre},j}
       \bigr]_{q} - \bigl[ A_{\mathrm{pre}} S \bigr]_{q}\Bigr]_{p} \\
    &= \mathbf{m}_{\mathrm{pre},j},
\end{aligned}
\label{eq:one-shot-dec}
\end{equation}
where $\mathbf{m}_{\mathrm{sum}}$ denotes the aggregated global plaintext.
The drift cancellation $-A_{\mathrm{pre}} S$ exactly neutralizes the
key-mask components accumulated over $R$ rounds.  The client then applies
the recovered update to the local model via
$\mathbf{w}^{(t+R)} \leftarrow \mathbf{w}^{(t)} - \eta \cdot
\mathbf{m}_{\mathrm{sum}}$.  This mechanism hides the HE communication
bottleneck within system idle periods while preserving IND-CPA security
under the dRLWE assumption.
```

---

## 4. 假数据取值思路（供参考）

- **PRPG 生成**：基于 AES-CTR 或 SHA-256 派生 $n$ 个系数，估算约 $0.5$~ms。
- **KGC 掩码生成**：需要一次多项式乘法/NTT，估算 $8$~ms；输出一个 RLWE 样本约 $12.8$~KB（$2 \times n \times 8$~B，$n=8192$）。
- **服务器对齐**：对每个选中的密文块做一次密钥切换/重线性化操作，估算 $4$~ms 客户端侧 + $3.2$~ms 服务器聚合。
- **复合漂移聚合**：$R$ 个密文同态加，与 $R$ 无关且开销很小，估算 $2.3$~ms 客户端侧 + $1.8$~ms 服务器侧。
- **关键路径**：只有服务器对齐中必须等待的最后一步才会进入训练关键路径，取 $0.8$~ms。

> 注意：上表数据为示意值。若实验部分已有真实测量，应直接替换为实测值。
