# 修改后的完整段落（Q1 → Q2 → ECP → Fig → \subsubsection）

```latex
Therefore, ciphertext prefetching does not reduce communication cost via 
content-agnostic compression. Rather, its efficiency improvement stems 
from \textit{amortizing the fixed per-ciphertext overhead across $R$ 
rounds of gradient accumulation}: the server temporally aggregates $R$ 
consecutive global deltas into a single composite ciphertext, and clients 
decrypt exactly once per selection instead of every round.

Addressing this problem requires further consideration of two key 
questions.

\textbf{Q1. Alignment of sparse pack indices.} We employ pack-level 
Top-$K$ sparsification to reduce upstream volume, but each client's 
local gradient structure differs, causing their selected packs to occupy 
different batch indices in the \texttt{\_\_sparse\_\_} layout. If left 
unresolved, server-side homomorphic merging and client-side One-Shot 
Decryption become impossible because ciphertexts at misaligned positions 
cannot be directly added or decrypted.

\textbf{Q2. Ciphertext size invariance.} Under CKKS, a ciphertext has 
fixed polynomial dimension regardless of plaintext content. Naively 
prefetching a full model every $R$ rounds would degenerate to standard 
FedAvg with no bandwidth savings. The prefetching unit must therefore be 
reconciled with the ciphertext granularity: we need to control not the 
content but the \textit{number of batches} being transmitted.

\noindent\textbf{Our solutions.} To answer Q1, we adopt a \emph{global 
mask voting} mechanism (\textsc{VPTopk}, Alg.~\ref{alg:upload}): all 
active clients upload lightweight plaintext vote vectors; the server 
computes a majority-vote consensus set $K^{(t)}$ and broadcasts it back. 
Every client then encrypts \textit{only} packs within $K^{(t)}$, ensuring 
that all ciphertexts share identical batch indices. To answer Q2, we 
design \emph{Batch-Level Gap Prefetching}: the server streams ciphertexts 
at the granularity of individual batches (not full models) during client 
idle periods. Because \textsc{VPTopk} enforces sparsity, the number of 
active batches per round is far smaller than the full parameter count, 
which is the ciphertext-domain analogue of FedFetch's plaintext vector 
compression. Together, these two mechanisms form the \textbf{ECP} 
protocol.

% %%%插入跨设备图片
\begin{figure}[t]
  \centering
  \includegraphics[width=0.95\linewidth]{../figures/cipherfetch_final_.pdf}
  \caption{\textbf{ECP workflow.} In the Prepare Phase (round $t$), the 
    server presamples active clients for round $t^* = t + R$ and 
    publishes the global consensus pack set $K^{(t)}$. During the 
    Prefetch Phase, idle clients asynchronously receive batch-level 
    ciphertext deltas from the server, who has temporally merged $R$ 
    rounds of global updates into a single cumulative ciphertext. 
    Slower devices initiate prefetching earlier to mask communication 
    latency. In the Train Phase (round $t^*$), synchronized clients 
    execute a brief residual fetch, One-Shot Decryption, and local 
    training, effectively hiding the HE communication bottleneck within 
    system idle periods.}
  \label{fig:cipherfetch}
\end{figure}

%------------------------------------------------------------------------------
\subsubsection{Efficient Ciphertext Prefetching}
\label{sssec:prefetch-accumulation}

Unlike plaintext prefetching that pushes complete model snapshots, our 
ECP exploits the idle intervals between client selections to 
asynchronously stream encrypted deltas in the background. As illustrated 
in Fig.~\ref{fig:cipherfetch}, after the server presamples the active 
client set $\mathcal{S}^{(t^*)}$ for round $t^* = t+R$ during the Prepare 
Phase, unselected clients enter the Prefetch Phase. Crucially, the 
server performs \emph{temporal homomorphic aggregation} on the cloud: it 
merges the pack-level ciphertexts from round $t$ through $t^*-1$ into a 
single composite delta. Because CKKS homomorphic addition is strictly 
size-invariant, this server-side temporal compression ensures that the 
cumulative ciphertext maintains a constant polynomial dimension, thereby 
averting any downstream bandwidth expansion.

The Prefetch Phase is also \emph{heterogeneous}: fast clients $c_1$ 
begin prefetching later and finish quickly, while bandwidth-constrained 
clients $c_N$ start earlier to ensure completion before $t^*$. When a 
client is finally selected at $t^*$, it executes a brief 
\emph{Ciphertext Fetch} (blue block) to retrieve any missing batches, 
followed by \emph{One-Shot Decryption} of the accumulated buffer and 
local training.

The efficiency gain therefore stems from \textit{(i) shifting downstream 
traffic from the congested Train Phase to idle gaps}, and 
\textit{(ii) amortizing one CKKS decryption over $R$ rounds}: clients 
no longer block on per-round downloads at selection time, and the server 
never transmits more than one pack-sized ciphertext per idle round to 
any given client.

To enable seamless homomorphic addition across consecutive rounds, the 
server must first ensure that each round's aggregated ciphertext 
algebraically aligns with the exact same global key structure 
$S = \sum_{i=1}^N s_i$, despite dynamic client dropouts.

Subsequently, instead of downloading updates round-by-round, the server 
temporally aggregates $R$ consecutive rounds. Due to the size-invariant 
property of CKKS, stacking $R$ rounds compresses the temporal dimension 
into a single composite ciphertext $C_{\mathrm{pre},j}^{(t)}$:
\begin{equation}
    C_{\mathrm{pre},j}^{(t)} = \bigoplus_{r=0}^{R-1} C_{j}^{(t+r)} 
    = \Bigl[\, \Delta_a^{(t)} S + 
    \sum_{r=0}^{R-1}\sum_{i\in\mathcal{S}^{(t+r)}} 
    m_{i,j}^{(t+r)} + E_{\mathrm{pre}}^{(t)} \,\Bigr]_{R_q},
    \label{eq:prefetch-accumulation}
\end{equation}
where $\Delta_a^{(t)} = \sum_{r=0}^{R-1} a^{(t+r)}$ is the accumulated 
public-polynomial drift and $E_{\mathrm{pre}}^{(t)} = 
\sum_{r=0}^{R-1} E^{(t+r)}$ is the composite noise. The prefetch 
ciphertext $C_{\mathrm{pre},j}^{(t)}$ occupies the same asymptotic space 
as a single-round ciphertext, regardless of the prefetch horizon $R$.
```

---

## 修改要点总结

| 位置 | 修改内容 |
|------|---------|
| Q1 | 明确问题：pack-level Top-K 导致 batch index misalignment，使同态合并和一次性解密不可能 |
| Q2 | 明确问题：CKKS 密文大小不变，全模型预取会退化为 FedAvg，必须在 batch 数量上做"压缩" |
| 解决方案 Q1 | **全局掩码投票 (VPTopk)**：服务器计算共识集合 $K^{(t)}$，所有客户端只加密 $K^{(t)}$ 中的 packs，强制 batch 索引对齐 |
| 解决方案 Q2 | **Batch-Level Gap Prefetching**：服务器在 batch 粒度上推送密文，VPTopk 稀疏化控制 batch 数量 → 类比 FedFetch 的明文向量压缩 |
| Fig 描述 | 增加 $K^{(t)}$ 发布和 temporal merge 的说明 |
| \subsubsection | 明确"server performs temporal homomorphic aggregation on the cloud"，而非客户端本地累加 |
| 公式 | $\sum$ 改为 $\bigoplus$（同态加符号），下标 $q$ 改为 $R_q$（与 notation 一致） |
