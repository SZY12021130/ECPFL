# Consensus Voting 的结构隐私泄漏问题与算法修改

## 1. 审稿意见的核心

ESP-VOTE 中每个 active client 把 binary vote bitmap $\mathbf{v}_i^{(t)}$ 直接发给 server，server 据此统计出全局 consensus mask $\mathcal{K}^{(t)}$。问题在于：

- vote mask 本身携带了 local gradient magnitude 的结构性信息。
- 在 non-IID 下，某些 packs 被反复选中会泄漏 client 的 label skew、dominant classes、rare features、training state 等。
- 论文第 5 页 Q1 声称要不暴露 selected indices，但协议却让 server 直接拿到 per-client binary masks，前后矛盾。

## 2. 两种修改策略

| 策略 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **A. 不改协议，明确承认泄漏** | 增加 "Leakage of Consensus Voting" 小节，说明 ECPFL 只保护 gradient values，不保护 sparse structure。 | 改动最小，诚实。 | 审稿人可能仍要求更强的隐私保证。 |
| **B. 改协议：对 vote masks 做安全聚合** | client 不再明文发送 $\mathbf{v}_i^{(t)}$，而是通过 SecAgg 只向 server 暴露聚合后的票数 $\bar{\mathbf{v}}^{(t)} = \sum_i \mathbf{v}_i^{(t)}$。 | 既保留原有功能，又把 per-client 结构隐私泄漏降到零；与 Q1 的声明一致。 | 需要额外一轮 SecAgg，增加少量通信/计算。 |

**推荐**：采用策略 B，并在安全分析中仍然增加一个诚实的 "Leakage of Consensus Voting" 小节，说明即使做了 SecAgg，server 仍然能看到聚合后的 consensus structure（这是任何 Top-k 稀疏化 FL 都固有的泄漏），但 gradient values 仍由 HE 保护。

---

## 3. 算法修改详情

### 3.1 主算法 \textsc{ECPFL}（Alg.~\ref{alg:main}）

把 "Send vote mask to Server" 改为 "Submit masked vote to SecAgg"，并把 "Server: Consensus" 改为 "Server: Secure Vote Aggregation and Consensus"。

```latex
% 在 Active Clients: Local Training and Voting 阶段
$(\mathbf{m}_i^{(t)}, \tilde{\mathbf{g}}_i^{(t)}) \leftarrow \textsc{ESP-Vote}(\mathbf{g}_i^{(t)}, \mathbf{r}_i, k)$\;
Submit masked vote $\mathbf{m}_i^{(t)}$ to the secure-aggregation primitive\;

% 在 Server 阶段
Collect masked votes $\{\mathbf{m}_i^{(t)}\}_{i \in \mathcal{S}^{(t)}}$\;
$\mathcal{K}^{(t)} \leftarrow \textsc{ESP-Consensus}(\{\mathbf{m}_i^{(t)}\}_{i \in \mathcal{S}^{(t)}})$\tcp*{server learns only aggregate votes}
```

### 3.2 \textsc{ESP-Vote} 与新增 \textsc{ESP-Consensus}

```latex
\Fn{\textsc{ESP-Vote}($\mathbf{g}_i^{(t)}, \mathbf{r}_i, k$)}{
    $\tilde{\mathbf{g}}_i^{(t)} \leftarrow \mathbf{g}_i^{(t)} + \mathbf{r}_i$\;
    $\mathcal{T}_i \leftarrow \text{Top-}k\text{ indices of } \bigl\{ \|\tilde{\mathbf{g}}_{i,j}^{(t)}\|_2^2 \bigr\}_{j=1}^{J}$\;
    Construct raw vote bitmap $\mathbf{v}_i^{(t)} \in \{0,1\}^{J}$ with $v_{i,j}^{(t)} = \mathbf{1}[j \in \mathcal{T}_i]$\;
    $\mathbf{m}_i^{(t)} \leftarrow \textsc{SecAgg.Mask}(\mathbf{v}_i^{(t)})$\tcp*{mask vote before sending to server}
    \Return $(\mathbf{m}_i^{(t)}, \tilde{\mathbf{g}}_i^{(t)})$\;
}

\BlankLine
\Fn{\textsc{ESP-Consensus}($\{\mathbf{m}_i^{(t)}\}_{i \in \mathcal{S}^{(t)}}$)}{
    $\bar{\mathbf{v}}^{(t)} \leftarrow \textsc{SecAgg.Aggregate}(\{\mathbf{m}_i^{(t)}\}_{i \in \mathcal{S}^{(t)}})$\tcp*{only the sum of votes is revealed}
    $\mathcal{K}^{(t)} \leftarrow \text{Top-}k\text{ indices of } \bar{\mathbf{v}}^{(t)}$\;
    \Return $\mathcal{K}^{(t)}$\;
}
```

### 3.3 为什么只需要聚合后的票数？

Consensus 只需要知道每个 pack 被多少 client 选中，即 $\bar{v}_j^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} v_{i,j}^{(t)}$。Server 拿到这个聚合向量后取 Top-$k$ 即可得到 $\mathcal{K}^{(t)}$，完全不需要知道任何单个 client 的 $\mathbf{v}_i^{(t)}$。

SecAgg 可以用任何标准实现（如 Bonawitz et al. 的 pairwise masking、shamir secret sharing、或基于服务器的 additive secret sharing），在论文中作为黑盒 \textsc{SecAgg.Mask} / \textsc{SecAgg.Aggregate} 即可。

---

## 4. 建议新增的 "Leakage of Consensus Voting" 小节（LaTeX）

```latex
\subsection{Leakage of Consensus Voting}
\label{ssec:leakage-voting}

The consensus voting step determines which packs will be updated in round $t$.
A naive implementation would require each active client to send its raw vote
bitmap $\mathbf{v}_i^{(t)}$ directly to the server, thereby revealing the exact
sparse structure of its local gradient magnitude pattern.  In a non-IID
federation, such per-client structure can leak coarse information about the
client's label distribution, dominant classes, or rare features, even though the
actual gradient values remain hidden by HE.

\textsc{ECPFL} avoids this per-client leakage by aggregating the vote bitmaps
through a standard secure-aggregation primitive.  Each client submits a masked
version $\mathbf{m}_i^{(t)} = \textsc{SecAgg.Mask}(\mathbf{v}_i^{(t)})$; the server
learns only the aggregate vote count
\begin{equation}
    \bar{\mathbf{v}}^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} \mathbf{v}_i^{(t)},
\end{equation}
from which it derives the consensus pack set $\mathcal{K}^{(t)}$ by taking the
Top-$k$ indices.  Consequently, no individual client's pack-selection pattern is
ever exposed.

It is important to note, however, that the final consensus set
$\mathcal{K}^{(t)}$ itself is public to all active clients and to the server.
Thus, while \textsc{ECPFL} protects both (i) individual vote masks and (ii) the
encrypted gradient values inside each selected pack, it does reveal the
population-level sparse structure---i.e., which packs the federation as a whole
considers important in each round.  This is the same structural leakage
inherent to any Top-$k$ sparsified FL scheme; ECPFL does not worsen it, and it
additionally provides value-level protection through CKKS encryption.
```

---

## 5. 已应用的文件修改

- `paper/main.tex` 已直接修改并编译通过：
  - Alg.~\ref{alg:main} 中把 vote mask 明文传输改为 SecAgg-masked vote 提交。
  - Alg.~\ref{alg:upload} 中 \textsc{ESP-Vote} 增加 \textsc{SecAgg.Mask} 步骤。
  - Alg.~\ref{alg:upload} 中新增 \textsc{ESP-Consensus} 函数，只暴露聚合票数。
  - 顺手修复了该文件中原本导致编译报错的 algorithm2e 用法：
    - 用 `\SetKwInput{KwParam}{Parameters}` 和 `\SetKw{Return}{return}` 定义缺失命令；
    - 把 `\SetCommentSty{footnotesize\sffamily\color{blue}}` 改为使用 `\textcolor` 的包装宏 `\CommentStyle`，避免 `\color` 在 `\csname` 展开时崩溃；
    - 去掉 `\tcp` 后面的 `\\`。
  - 现在 `xelatex main.tex` 可以成功编译（仅余 "Float too large" 与字体替代警告，属于版面和字体问题，不影响算法内容）。

如果不需要 protocol 修改、只想保留明文 vote 并承认泄漏，可以把 `paper/main.tex` 中相关行回退，并直接插入第 4 节的 "Leakage of Consensus Voting" 小节。
