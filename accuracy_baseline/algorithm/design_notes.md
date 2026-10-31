# 扰动投票机制设计说明

## 1. 文件位置

- `algorithms_with_perturbation.tex`：包含融入扰动投票后的主算法、ESP 上游模块以及正文描述段落。
- 已通过 XeLaTeX 编译验证。

## 2. 与旧逻辑的主要变化

| 环节 | 旧逻辑 | 新逻辑 |
|------|--------|--------|
| 初始化 | KGC 分发 $(s_i, S)$ 与 PRPG 种子 $B$ | 额外分发/派生两两种子 $sd_{i,j}$ |
| 客户端投票 | 上传明文投票 $\mathbf{v}_i^{(t)}$ | 上传扰动后投票 $\hat{\mathbf{v}}_i^{(t)} = [\mathbf{v}_i^{(t)} + \mathbf{z}_i^{(t)}]_M$ |
| 聚合共识 | 直接对明文投票 Top-$k$ | 服务器先加 KGC 补偿扰动 $\mathbf{z}_{\mathrm{comp}}^{(t)}$，再模 $M$ 恢复真实票数和 |
| KGC 角色 | 仅生成梯度补偿密文 | 额外根据不活跃客户端集合计算投票补偿扰动 |

## 3. 补偿扰动的正确性

对每个客户端 $c_i$，扰动定义为

$$
\mathbf{z}_i^{(t)} = \Bigl[ \sum_{j>i} \mathbf{y}_{i,j}^{(t)} - \sum_{j<i} \mathbf{y}_{j,i}^{(t)} \Bigr]_M,
\qquad \mathbf{y}_{i,j}^{(t)} = \mathsf{PRG}(sd_{i,j}, t).
$$

因为 $\mathbf{y}_{i,j}^{(t)}$ 在 $c_i$ 中为正、在 $c_j$ 中为负，全部 $N$ 个客户端的扰动之和严格为 $\mathbf{0} \pmod M$：

$$
\sum_{i=1}^N \mathbf{z}_i^{(t)} \equiv \mathbf{0} \pmod M.
$$

活跃客户端上传 $\hat{\mathbf{v}}_i^{(t)}$；不活跃客户端没有上传，因此服务器从 KGC 取得其扰动之和作为补偿：

$$
\mathbf{z}_{\mathrm{comp}}^{(t)} = \Bigl[ \sum_{k \in \bar{\mathcal{S}}^{(t)}} \mathbf{z}_k^{(t)} \Bigr]_M.
$$

服务器聚合：

$$
\bar{\mathbf{v}}^{(t)}
= \Bigl[ \sum_{i \in \mathcal{S}^{(t)}} \hat{\mathbf{v}}_i^{(t)} + \mathbf{z}_{\mathrm{comp}}^{(t)} \Bigr]_M
= \Bigl[ \sum_{i \in \mathcal{S}} \mathbf{v}_i^{(t)} + \sum_{i=1}^N \mathbf{z}_i^{(t)} \Bigr]_M
= \sum_{i \in \mathcal{S}} \mathbf{v}_i^{(t)}.
$$

因此补偿逻辑是正确的，可以精确恢复真实票数聚合。

## 4. 需要注意的问题与最佳实践

### 4.1 KGC 必须保留两两种子
原描述只说 KGC "distributes seed"，但要计算 $\mathbf{z}_{\mathrm{comp}}^{(t)}$，KGC 必须能够重构不活跃客户端的扰动。因此设计里明确：

> KGC retains a copy (or derives it from a master key).

### 4.2 KGC 与服务器之间需要通信
服务器需要把 $\bar{\mathcal{S}}^{(t)}$ 告诉 KGC，KGC 再把 $\mathbf{z}_{\mathrm{comp}}^{(t)}$ 发回。这会泄露不活跃集合给 KGC，但 KGC 是可信方，可接受。

如果希望将 $\mathbf{z}_{\mathrm{comp}}^{(t)}$ 放在公共信道上传输也**不会泄露个体投票**，因为它只是 PRG 输出的和；但此时外部窃听者也能看到 $\hat{\mathbf{v}}_i^{(t)}$ 与 $\mathbf{z}_{\mathrm{comp}}^{(t)}$，从而计算出聚合票数。若聚合共识 $\mathcal{K}^{(t)}$ 需要对窃听者保密，则应使用 KGC-服务器安全信道传输补偿扰动。

### 4.3 模数 $M$ 必须大于活跃客户端数
条件 $M > N$ 保证 $\sum_{i \in \mathcal{S}} \mathbf{v}_i^{(t)} < M$，避免模运算回绕，从而能正确比较各 pack 的得票数并取 Top-$k$。

### 4.4 至少两名活跃客户端
若某轮只有 1 名活跃客户端，则

$$
\bar{\mathbf{v}}^{(t)} = \mathbf{v}_i^{(t)} + \mathbf{z}_i^{(t)} + \mathbf{z}_{\mathrm{comp}}^{(t)} = \mathbf{v}_i^{(t)},
$$

服务器可直接获得该客户端的明文投票，个体隐私失效。因此该机制隐含要求每轮活跃客户端数 $\ge 2$。

### 4.5 客户端存储与计算开销
每个客户端保存 $N-1$ 个两两种子，每轮计算 $N-1$ 次 PRG，复杂度 $\mathcal{O}(N)$。KGC 存储/派生全部 $\binom{N}{2}$ 个种子，并计算不活跃客户端扰动，复杂度 $\mathcal{O}(N \cdot |\bar{\mathcal{S}}^{(t)}|)$。该方案适用于客户端总数 $N$ 为中小规模场景；若 $N$ 很大，需考虑更高效的密钥派生树或分层方案。

### 4.6 动态加入/退出
两两种子在初始化时绑定固定 $N$ 个客户端。若有新客户端加入或退出，需要重新执行初始化分发过程。

### 4.7 不影响梯度加密部分
投票扰动仅改变共识阶段；梯度密文 $\mathsf{ct}_{i,j}^{(t)}$ 的生成、聚合与解密流程保持不变，之前的安全证明（IND-CPA、Server Obliviousness、Collusion Resistance 等）仍然适用。
