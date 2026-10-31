# 基于 RLWE 的全流程数学推导与伪代码

> **文档定位**：本文档从 RLWE（Ring Learning With Errors）困难问题出发，严格推导 TESK-EGD-ZM + CipherFetch + PTopk 完整闭环的数学形式，给出模仿 FedPHE 论文风格的 4 个核心算法伪代码，并在半诚实模型下进行安全性分析。

---

## 一、符号表与 RLWE 基础

### 1.1 符号表

| 符号 | 含义 |
|------|------|
| $N$ | RLWE 环维度（CKKS 中 `poly_modulus_degree`，如 8192） |
| $n$ | 客户端总数 |
| $S_t \subseteq [n]$ | 第 $t$ 轮参与训练的活跃客户端集合 |
| $d$ | 模型参数总维度 |
| $m$ | 包级 batch 数量，$m = \lceil d / S \rceil$，$S = N/2$ 为 slot 数 |
| $\mathcal{R} = \mathbb{Z}[X]/(X^N + 1)$ | 分圆多项式环 |
| $\mathcal{R}_q = \mathbb{Z}_q[X]/(X^N + 1)$ | 模 $q$ 约化环 |
| $\mathbf{s} \in \mathcal{R}$ | CKKS 私钥（仅 TEE 持有） |
| $\mathbf{a} \in \mathcal{R}_q$ | 公共随机多项式（RLWE 实例的 $a$ 部分） |
| $e \leftarrow \chi$ | 从误差分布 $\chi$ 采样的小多项式 |
| $\Delta = 2^{40}$ | CKKS 缩放因子（scale） |
| $w_i = |D_i| / \sum_j |D_j|$ | 客户端 $i$ 的聚合权重 |
| $b_i \in \mathbb{R}^{S}$ | 客户端 $i$ 的私有盲化掩码（零和约束） |
| $r_t^{(i)} \in \mathbb{R}^{S}$ | 客户端 $i$ 的 PTopk 明文残差累加器 |
| $R_t \in \mathbb{R}^{S}$ | TEE 内全局残差累加器（补偿下行压缩） |
| $\text{ct} = (c_0, c_1)$ | CKKS 密文（二元组） |

### 1.2 RLWE 困难问题

**定义（决策型 RLWE）**：给定参数 $(N, q, \chi)$，区分以下两个分布是计算困难的：
- 均匀分布：$(\mathbf{a}, \mathbf{u}) \in \mathcal{R}_q^2$，其中 $\mathbf{u}$ 随机
- RLWE 分布：$(\mathbf{a}, \mathbf{b} = \mathbf{a} \cdot \mathbf{s} + \mathbf{e})$，其中 $\mathbf{s} \leftarrow \chi_{key}$，$\mathbf{e} \leftarrow \chi_{err}$

**CKKS 密文结构**：对明文多项式 $\mathbf{m} \in \mathcal{R}$（编码后的消息），
$$
\text{Enc}_{\mathbf{pk}}(\mathbf{m}) = (\mathbf{c}_0, \mathbf{c}_1) = (\mathbf{a} \cdot \mathbf{s} + \mathbf{e} + \mathbf{m},\; -\mathbf{a}) \in \mathcal{R}_q^2
$$

**解密**：
$$
\mathbf{m}' = \mathbf{c}_0 + \mathbf{c}_1 \cdot \mathbf{s} = \mathbf{m} + \mathbf{e} \pmod q
$$
误差 $\|\mathbf{e}\|_\infty$ 足够小，使得解码后 $\mathbf{m}' / \Delta \approx \mathbf{m} / \Delta$。

### 1.3 同态运算性质

CKKS 支持以下同态运算，是本文所有聚合操作的数学基础：

| 运算 | 输入 | 输出 | 数学形式 |
|------|------|------|---------|
| 加法 | $\text{ct}_1, \text{ct}_2$ | $\text{ct}_{+}$ | $\text{Dec}(\text{ct}_{+}) = \text{Dec}(\text{ct}_1) + \text{Dec}(\text{ct}_2) + e_{+}$ |
| 标量乘 | $\text{ct}, \alpha \in \mathbb{R}$ | $\text{ct}_{\times}$ | $\text{Dec}(\text{ct}_{\times}) = \alpha \cdot \text{Dec}(\text{ct}) + e_{\times}$ |
| 旋转（Rotation） | $\text{ct}, k$ | $\text{ct}_{\ll k}$ | 循环移位 slot 内容 |
| 重线性化 | $\text{ct} = (c_0, c_1, c_2)$ | $\text{ct}' = (c'_0, c'_1)$ | 密文度数从 3 降到 2 |

**关键定理（同态线性组合）**：给定密文 $\{\text{ct}_i = \text{Enc}(\mathbf{m}_i)\}$ 和标量 $\{\alpha_i\}$，
$$
\sum_i \alpha_i \cdot \text{ct}_i = \text{Enc}\left(\sum_i \alpha_i \mathbf{m}_i + \mathbf{e}_{\text{agg}}\right)
$$
其中聚合误差 $\|\mathbf{e}_{\text{agg}}\|_\infty \leq \sum_i |\alpha_i| \cdot \|\mathbf{e}_i\|_\infty$。当权重满足 $\sum_i w_i = 1$ 时，误差有界。

---

## 二、系统初始化（KGC 阶段）

### 2.1 KGC 密钥生成

**Step 0.1**：KGC 执行标准 CKKS 密钥生成：
$$
(\mathbf{s}, \mathbf{pk}, \mathbf{evk}) \leftarrow \text{CKKS.KeyGen}(\lambda, N, \{q_0, q_1, \dots, q_L\}, \Delta)
$$
其中 $\lambda$ 为安全参数，$\{q_l\}$ 为层级模数链，$\Delta = 2^{40}$ 为缩放因子。

**Step 0.2**：KGC 计算聚合权重：
$$
w_i = \frac{|D_i|}{\sum_{j=1}^n |D_j|}, \quad i = 1, \dots, n
$$

### 2.2 零和盲化掩码生成（核心安全操作）

**Step 0.3**：KGC 为每个客户端生成加权零和掩码：

1. 独立随机采样：$\mathbf{u}_i \sim \mathcal{U}[-B, B]^{S}$，$B$ 为掩码幅度上界
2. 计算加权均值：$\mathbf{u}_{\text{mean}} = \sum_{i=1}^n w_i \mathbf{u}_i$
3. 构造零和掩码：
   $$
   \mathbf{b}_i = \mathbf{u}_i - \mathbf{u}_{\text{mean}}
   $$

**定理（零和性）**：$\{\mathbf{b}_i\}$ 满足加权零和约束：
$$
\sum_{i=1}^n w_i \mathbf{b}_i = \sum_{i=1}^n w_i (\mathbf{u}_i - \mathbf{u}_{\text{mean}}) = \mathbf{u}_{\text{mean}} - \mathbf{u}_{\text{mean}} = \mathbf{0}
$$

**隐私性质**：Client $i$ 仅知道 $\mathbf{b}_i$，不知道其他任何 $\mathbf{b}_j$（$j \neq i$）。即使 $n-2$ 个客户端合谋，它们可以重建 $\mathbf{u}_{\text{mean}}$ 的 $n-2$ 项贡献，但无法确定剩余两个客户端的具体 $\mathbf{b}_i$（仅知道其和）。

### 2.3 密钥分发与密封

**Step 0.4**：KGC 构建密钥包并密封到 TEE：
$$
\text{key\_bundle} = (\mathbf{s}, \{\mathbf{b}_i\}_{i=1}^n, \{w_i\}_{i=1}^n)
$$
$$
\text{sealed\_bundle} = \text{TEE.Seal}(\text{key\_bundle}, \text{enclave\_identity})
$$

**Step 0.5**：分发：
- KGC $\xrightarrow{\text{TLS}}$ Client $_i$：$(\mathbf{s}, \mathbf{b}_i)$
- KGC $\xrightarrow{\text{TLS}}$ Server Host：$(\mathbf{pk}, \mathbf{evk})$ + 密封包
- 广播：$\mathbf{pk}, \mathbf{evk}$ 给所有实体

**Step 0.6**：KGC 销毁所有敏感状态，永久离线。

---

## 三、每轮联邦学习闭环推导

### 3.1 Phase 1: 客户端本地训练 [Client$_i$]

Client $i$ 基于当前全局模型（上一轮同步的明文或预取累加后的状态）执行本地 SGD：
$$
\mathbf{g}_t^{(i)} = \nabla_{\boldsymbol{\theta}} \mathcal{L}_i(\boldsymbol{\theta}_t^{(i)}; D_i)
$$

将梯度展平为向量 $\mathbf{g}_t^{(i)} \in \mathbb{R}^d$，然后分块为 $m$ 个 batch：
$$
\mathbf{g}_t^{(i)} = [\mathbf{g}_{t,0}^{(i)}; \mathbf{g}_{t,1}^{(i)}; \dots; \mathbf{g}_{t,m-1}^{(i)}], \quad \mathbf{g}_{t,j}^{(i)} \in \mathbb{R}^{S}
$$

### 3.2 Phase 2: PTopk 客户端残差补偿

**PTopk 核心原理**：在稀疏化前，先把历史残差累加到当前梯度上，补偿之前轮次未上传的 batch 信息。

客户端维护明文残差累加器 $\mathbf{r}_{t-1}^{(i)} = [\mathbf{r}_{t-1,0}^{(i)}; \dots; \mathbf{r}_{t-1,m-1}^{(i)}]$。

**补偿**：
$$
\tilde{\mathbf{g}}_{t,j}^{(i)} = \mathbf{g}_{t,j}^{(i)} + \mathbf{r}_{t-1,j}^{(i)}, \quad \forall j \in [m]
$$

**包级 TopK 稀疏化**：计算每 batch 的平均绝对值，保留 top-$k$ 个 batch：
$$
\text{score}_j = \frac{1}{S} \sum_{l=1}^{S} \left|\tilde{\mathbf{g}}_{t,j,l}^{(i)}\right|
$$
$$
\mathcal{S}_t^{(i)} = \text{TopK}(\{\text{score}_j\}_{j=0}^{m-1},\; k = \lceil \rho \cdot m \rceil)
$$
其中 $\rho$ 为稀疏率（如 0.1）。

**残差更新**：
$$
\mathbf{r}_{t,j}^{(i)} =
\begin{cases}
\mathbf{0}, & j \in \mathcal{S}_t^{(i)} \quad \text{（选中 batch，信息已上传）} \\
\tilde{\mathbf{g}}_{t,j}^{(i)}, & j \notin \mathcal{S}_t^{(i)} \quad \text{（未选中，保留到下一轮）}
\end{cases}
$$

**上传内容**：仅加密选中的 batch：
$$
\mathbf{u}_{t,j}^{(i)} = \tilde{\mathbf{g}}_{t,j}^{(i)} + \mathbf{b}_{i,j}, \quad j \in \mathcal{S}_t^{(i)}
$$
其中 $\mathbf{b}_{i,j}$ 是掩码 $\mathbf{b}_i$ 的第 $j$ 个 batch 切片。

### 3.3 Phase 3: 盲化加密 [Client$_i$]

对每个选中 batch $j \in \mathcal{S}_t^{(i)}$：

1. **编码**：将实数向量编码为环元素（SIMD 编码）：
   $$
   \mathbf{z}_j^{(i)} = \text{CKKS.Encode}(\mathbf{u}_{t,j}^{(i)}, \Delta) \in \mathcal{R}
   $$
   编码后满足：$\mathbf{z}_j^{(i)}[l] \approx \Delta \cdot \mathbf{u}_{t,j,l}^{(i)}$（第 $l$ 个 slot）。

2. **加密**（基于 RLWE）：
   $$
   \text{ct}_{t,j}^{(i)} = \text{CKKS.Enc}(\mathbf{pk}, \mathbf{z}_j^{(i)}) = (\mathbf{a}_j^{(i)} \cdot \mathbf{s} + \mathbf{e}_j^{(i)} + \mathbf{z}_j^{(i)},\; -\mathbf{a}_j^{(i)}) \in \mathcal{R}_q^2
   $$

3. **序列化上传**：
   $$
   \text{ct}_{t}^{(i)} = \{\text{ct}_{t,j}^{(i)}\}_{j \in \mathcal{S}_t^{(i)}} \xrightarrow{\text{HTTPS}} \text{Server Host}
   $$

**稀疏密文格式**：
$$
\text{upload}_t^{(i)} = \{\text{`__sparse__'}: \text{True},\; \text{`ciphertexts'}: [\text{ct}_{t,j_1}^{(i)}, \dots],\; \text{`mask'}: [m_0, m_1, \dots, m_{m-1}]\}
$$
其中 $m_j = 1$ 当且仅当 $j \in \mathcal{S}_t^{(i)}$。

### 3.4 Phase 4: 服务器密文聚合 [Server Host]

Server Host 对所有活跃客户端的稀疏密文执行**按 batch 位置对齐**的加权聚合。

对 batch 位置 $j \in [m]$，设提交了该 batch 的客户端集合为 $\mathcal{C}_j = \{i : j \in \mathcal{S}_t^{(i)}\}$。令这些客户端的归一化权重为 $\tilde{w}_i = w_i / \sum_{k \in \mathcal{C}_j} w_k$。

**同态加权平均**：
$$
\text{ct}_{\text{agg},j} = \sum_{i \in \mathcal{C}_j} \tilde{w}_i \cdot \text{ct}_{t,j}^{(i)}
$$

展开 RLWE 结构：
$$
\begin{aligned}
\text{ct}_{\text{agg},j} &= \sum_{i \in \mathcal{C}_j} \tilde{w}_i \cdot (\mathbf{a}_{i,j} \mathbf{s} + \mathbf{e}_{i,j} + \mathbf{z}_j^{(i)},\; -\mathbf{a}_{i,j}) \\
&= \left(\left(\sum_i \tilde{w}_i \mathbf{a}_{i,j}\right) \mathbf{s} + \sum_i \tilde{w}_i \mathbf{e}_{i,j} + \sum_i \tilde{w}_i \mathbf{z}_j^{(i)},\; -\sum_i \tilde{w}_i \mathbf{a}_{i,j}\right) \\
&= \text{Enc}\left(\mathbf{pk},\; \sum_{i \in \mathcal{C}_j} \tilde{w}_i \mathbf{z}_j^{(i)}\right) + \mathbf{e}_{\text{agg},j}
\end{aligned}
$$

其中聚合误差 $\mathbf{e}_{\text{agg},j} = \sum_i \tilde{w}_i \mathbf{e}_{i,j}$，满足 $\|\mathbf{e}_{\text{agg},j}\| \leq \max_i \|\mathbf{e}_{i,j}\|$（权重归一化后）。

**解码后的明文内容**：
$$
\text{Dec}(\text{ct}_{\text{agg},j}) / \Delta \approx \sum_{i \in \mathcal{C}_j} \tilde{w}_i \cdot (\mathbf{g}_{t,j}^{(i)} + \mathbf{r}_{t-1,j}^{(i)} + \mathbf{b}_{i,j})
$$

### 3.5 Phase 5: TEE 解密、掩码抵消与全局残差 [TEE]

TEE 从 Server Host 接收聚合密文 $\{\text{ct}_{\text{agg},j}\}$，执行以下操作：

**Step 5.1 解封**：$(\mathbf{s}, \{\mathbf{b}_i\}, \{w_i\}) \leftarrow \text{TEE.Unseal}(\text{sealed\_bundle})$

**Step 5.2 逐 batch 解密**：对 $j \in [m]$：
$$
\boldsymbol{\delta}_{\text{plain},j} = \text{CKKS.Dec}(\mathbf{s}, \text{ct}_{\text{agg},j}) = \sum_{i \in \mathcal{C}_j} \tilde{w}_i (\mathbf{g}_{t,j}^{(i)} + \mathbf{r}_{t-1,j}^{(i)} + \mathbf{b}_{i,j}) + \boldsymbol{\epsilon}_j
$$
其中 $\boldsymbol{\epsilon}_j$ 为 CKKS 近似噪声，$\|\boldsymbol{\epsilon}_j\|_\infty \ll \Delta$。

**Step 5.3 掩码抵消**：TEE 利用密封存储的完整掩码集，精确计算加权掩码残差：
$$
\boldsymbol{\beta}_j = \sum_{i \in \mathcal{C}_j} \tilde{w}_i \cdot \mathbf{b}_{i,j}
$$
$$
\boldsymbol{\delta}_{\text{pure},j} = \boldsymbol{\delta}_{\text{plain},j} - \boldsymbol{\beta}_j = \sum_{i \in \mathcal{C}_j} \tilde{w}_i (\mathbf{g}_{t,j}^{(i)} + \mathbf{r}_{t-1,j}^{(i)}) + \boldsymbol{\epsilon}_j
$$

**关键性质**：掩码精确抵消后，结果仅含真实梯度和 PTopk 残差（以及可忽略的 CKKS 噪声）。

**Step 5.4 全局残差累加**：TEE 维护全局残差 $\mathbf{R}_{t-1} = [\mathbf{R}_{t-1,0}; \dots; \mathbf{R}_{t-1,m-1}]$，补偿下行 TopK 压缩损失。

补偿值：
$$
\mathbf{c}_{t,j} = \boldsymbol{\delta}_{\text{pure},j} + \mathbf{R}_{t-1,j}
$$

**Step 5.5 TEE 内二次包级 TopK**：
$$
\mathcal{S}_t^{\text{TEE}} = \text{TopK}(\{\|\mathbf{c}_{t,j}\|_1 / S\}_{j=0}^{m-1},\; k^{\text{TEE}} = \lceil \rho^{\text{TEE}} \cdot m \rceil)
$$

压缩后上传内容：
$$
\tilde{\boldsymbol{\delta}}_{t,j} =
\begin{cases}
\mathbf{c}_{t,j}, & j \in \mathcal{S}_t^{\text{TEE}} \\
\mathbf{0}, & j \notin \mathcal{S}_t^{\text{TEE}}
\end{cases}
$$

**Step 5.6 更新全局残差**：
$$
\mathbf{R}_{t,j} =
\begin{cases}
\mathbf{0}, & j \in \mathcal{S}_t^{\text{TEE}} \quad \text{（信息已下发）} \\
\mathbf{c}_{t,j}, & j \notin \mathcal{S}_t^{\text{TEE}} \quad \text{（累积到下一轮）}
\end{cases}
$$

**Step 5.7 更新全局模型明文**：设旧全局模型为 $\mathbf{W}_{t-1}$（TEE 缓存），
$$
\mathbf{W}_{t,j} = \mathbf{W}_{t-1,j} + \tilde{\boldsymbol{\delta}}_{t,j}, \quad \forall j \in [m]
$$

**Step 5.8 重新加密选中 batch**：仅对 $j \in \mathcal{S}_t^{\text{TEE}}$ 加密：
$$
\text{ct}_{t,j}^{\text{new}} = \text{CKKS.Enc}(\mathbf{pk}, \text{CKKS.Encode}(\mathbf{W}_{t,j}, \Delta))
$$

TEE 输出到 Server Host：
$$
\text{tee\_result}_t = \{\text{`ciphertexts'}: [\text{ct}_{t,j}^{\text{new}}]_{j \in \mathcal{S}_t^{\text{TEE}}},\; \text{`mask'}: [\mathbb{1}_{j \in \mathcal{S}_t^{\text{TEE}}}]\}
$$

### 3.6 Phase 6: Host 稀疏 Delta 计算与全局状态更新 [Server Host]

**Step 6.1 合并到旧全局密文**：对旧全局密文的 batch 列表，用 TEE 返回的新密文替换选中位置：
$$
\text{ct}_{\text{global},j}^{(t)} =
\begin{cases}
\text{ct}_{t,j}^{\text{new}}, & j \in \mathcal{S}_t^{\text{TEE}} \\
\text{ct}_{\text{global},j}^{(t-1)}, & j \notin \mathcal{S}_t^{\text{TEE}}
\end{cases}
$$

**Step 6.2 计算稀疏 Delta（供客户端下载）**：
$$
\text{ct}_{\Delta,j} = \text{ct}_{\text{global},j}^{(t)} - \text{ct}_{\text{global},j}^{(t-1)}, \quad j \in \mathcal{S}_t^{\text{TEE}}
$$

由于同态减法的线性性：
$$
\text{Dec}(\text{ct}_{\Delta,j}) / \Delta \approx \mathbf{W}_{t,j} - \mathbf{W}_{t-1,j} = \tilde{\boldsymbol{\delta}}_{t,j}
$$

**Step 6.3 更新全局状态**：
$$
\text{encrypted\_global\_state}_t = \{\text{ct}_{\text{global},j}^{(t)}\}_{j=0}^{m-1}
$$

### 3.7 Phase 7: 密文预取 Delta 的同态累加与解密应用 [Client ↔ Server]

#### 3.7.1 预取广播 [Server Host → Client]

Server Host 将稀疏 delta 密文 $\text{ct}_{\Delta}$ 广播给**未选中客户端**（以及选中客户端，供下一轮使用）。

对 Client $i$：
$$
\text{ct}_{\Delta} \xrightarrow{\text{HTTPS}} \text{Client}_i
$$

#### 3.7.2 客户端同态累加 [Client$_i$]

Client $i$ 维护本地密文缓存 $\text{prefetched\_state}$（初始为 $\emptyset$）。收到 $\text{ct}_{\Delta}$ 后执行同态加法：

若 $\text{prefetched\_state} = \emptyset$：
$$
\text{prefetched\_state} \leftarrow \text{ct}_{\Delta}
$$

否则：
$$
\text{prefetched\_state} \leftarrow \text{CKKS.Add}(\text{prefetched\_state}, \text{ct}_{\Delta})
$$

**数学推导**：设 Client $i$ 已缓存了 $k$ 轮的 deltas $\text{ct}_{\Delta}^{(t_1)}, \dots, \text{ct}_{\Delta}^{(t_k)}$，则：
$$
\text{Dec}(\text{prefetched\_state}) / \Delta \approx \sum_{l=1}^k \tilde{\boldsymbol{\delta}}_{t_l}
$$

同态加法后密文大小**不变**，始终等于单个密文大小。

#### 3.7.3 训练前：解密并应用 [Client$_i$]

当 Client $i$ 被选中参与训练时，执行以下步骤：

1. **一次性解密缓存**：
   $$
   \boldsymbol{\Delta}_{\text{plain}} = \text{CKKS.Dec}(\mathbf{s}, \text{prefetched\_state}) / \Delta
   $$

2. **应用到 base model**：设 base model 为 $\mathbf{W}_{\text{base}}$（上次同步时的全局模型），
   $$
   \mathbf{W}_{\text{current}} = \mathbf{W}_{\text{base}} + \boldsymbol{\Delta}_{\text{plain}}
   $$

3. **清空缓存**：
   $$
   \text{prefetched\_state} \leftarrow \emptyset
   $$

4. **本地训练**：基于 $\mathbf{W}_{\text{current}}$ 计算梯度。

**关键不变量**：应用后，$\mathbf{W}_{\text{current}}$ 等于最新全局模型（不含本地梯度）。

### 3.8 闭环总结

一轮完整的闭环包含以下数学关系链：

$$
\boxed{
\begin{aligned}
&\text{Client}_i: && \mathbf{g}_t^{(i)} \xrightarrow{+\mathbf{r}_{t-1}^{(i)}} \tilde{\mathbf{g}}_t^{(i)} \xrightarrow{+\mathbf{b}_i} \mathbf{u}_t^{(i)} \xrightarrow{\text{TopK}} \text{ct}_t^{(i)} \\
&\text{Server}: && \{\text{ct}_t^{(i)}\} \xrightarrow{\text{HomAdd+ScalarMult}} \text{ct}_{\text{agg}} \\
&\text{TEE}: && \text{ct}_{\text{agg}} \xrightarrow{\text{Dec}} \boldsymbol{\delta}_{\text{plain}} \xrightarrow{-\boldsymbol{\beta}} \boldsymbol{\delta}_{\text{pure}} \xrightarrow{+\mathbf{R}_{t-1}} \mathbf{c}_t \xrightarrow{\text{TopK}} \tilde{\boldsymbol{\delta}}_t \\
&\text{TEE}: && \mathbf{W}_{t-1} + \tilde{\boldsymbol{\delta}}_t = \mathbf{W}_t \xrightarrow{\text{Enc}} \text{ct}_t^{\text{new}} \\
&\text{Host}: && \text{ct}_t^{\text{new}} - \text{ct}_{t-1} = \text{ct}_{\Delta} \\
&\text{Client}_i: && \text{ct}_{\Delta} \xrightarrow{\text{HomAdd}} \text{prefetched\_state} \xrightarrow{\text{Dec}} \boldsymbol{\Delta}_{\text{plain}} \xrightarrow{+\mathbf{W}_{\text{base}}} \mathbf{W}_{\text{current}}
\end{aligned}
}
$$

---

## 四、PTopk 核心原理的严格数学表述

PTopk 基于 STC (Sparse Ternary Compression) 的 Error-Feedback 机制，在同态加密 + 包级打包框架下的适配。

### 4.1 客户端残差累加器

**定义**：Client $i$ 维护明文残差序列 $\{\mathbf{r}_t^{(i)}\}_{t \geq 0}$，初始 $\mathbf{r}_0^{(i)} = \mathbf{0}$。

**递推关系**：
$$
\mathbf{r}_t^{(i)} = (\mathbf{g}_t^{(i)} + \mathbf{r}_{t-1}^{(i)}) - \text{TopK}(\mathbf{g}_t^{(i)} + \mathbf{r}_{t-1}^{(i)}, \rho)
$$

**定理（信息守恒）**：对任意 batch $j$ 和轮次 $t$，有：
$$
\sum_{\tau=0}^{t} \text{TopK}(\mathbf{g}_\tau^{(i)} + \mathbf{r}_{\tau-1}^{(i)}, \rho)_j + \mathbf{r}_{t,j}^{(i)} = \sum_{\tau=0}^{t} \mathbf{g}_{\tau,j}^{(i)}
$$

**证明**：对单轮，$\text{TopK}(\cdot)_j + \mathbf{r}_{t,j}^{(i)} = \mathbf{g}_{t,j}^{(i)} + \mathbf{r}_{t-1,j}^{(i)}$。累加即得。

**意义**：无论压缩率 $\rho$ 多低，PTopk 保证**所有梯度信息最终都会上传**到服务器，只是被分散到多个轮次。收敛性不受稀疏率影响（仅收敛速度）。

### 4.2 服务器累加器（明文域）

服务器端可选维护累加器 $\mathbf{A}_t$，支持三种模式：

**none 模式**：
$$
\mathbf{A}_t = \boldsymbol{\delta}_{\text{pure}}, \quad \mathbf{W}_{t+1} = \mathbf{W}_t + \eta \cdot \mathbf{A}_t
$$

**delayed 模式**（每隔 $K$ 轮同步）：
$$
\mathbf{A}_t = \mathbf{A}_{t-1} + \eta \cdot \boldsymbol{\delta}_{\text{pure}}
$$
$$
\mathbf{W}_{t+1} =
\begin{cases}
\mathbf{W}_t + \mathbf{A}_t, & t \equiv 0 \pmod K \\
\mathbf{W}_t, & \text{otherwise}
\end{cases}
$$

**momentum 模式**：
$$
\mathbf{A}_t = \beta \cdot \mathbf{A}_{t-1} + (1-\beta) \cdot \eta \cdot \boldsymbol{\delta}_{\text{pure}}
$$
$$
\mathbf{W}_{t+1} = \mathbf{W}_t + \mathbf{A}_t
$$

**注意**：TEE 开启时，Host 侧服务器累加器自动禁用（`server_mode = 'none'`），避免与 TEE 全局残差 $R_t$ 双重补偿。

### 4.3 TEE 全局残差 vs PTopk 客户端残差

| 特性 | PTopk 客户端残差 $\mathbf{r}_t^{(i)}$ | TEE 全局残差 $\mathbf{R}_t$ |
|------|--------------------------------------|---------------------------|
| 位置 | 客户端本地明文 | TEE 隔离内存明文 |
| 补偿对象 | 客户端上行 TopK 压缩 | 服务器下行 TopK 压缩 |
| 更新规则 | 未选中保留，选中清零 | 未选中保留，选中清零 |
| 公式 | $\mathbf{r}_t = (\mathbf{g} + \mathbf{r}_{t-1}) - \text{TopK}(\cdot)$ | $\mathbf{R}_t = (\boldsymbol{\delta} + \mathbf{R}_{t-1}) - \text{TopK}(\cdot)$ |
| 隐私暴露 | 仅在客户端本地 | 仅在 TEE 隔离内存 |

---

## 五、全流程伪代码

> 以下四个算法模仿 FedPHE 论文风格，覆盖系统初始化、客户端上传、TEE 聚合与预取、客户端下载应用四个阶段。

### 算法 1: 系统初始化 (System Initialization)

```
Algorithm 1: System Initialization (KGC)
────────────────────────────────────────────────────────
Input: Security parameter λ, ring dimension N,
       coefficient modulus chain {q_l}_{l=0}^L,
       scale Δ, number of clients n, datasets {D_i}
Output: Key bundles distributed to all entities

1:  (sk, pk, evk) ← CKKS.KeyGen(λ, N, {q_l}, Δ)
    ▷ Generate single-key CKKS key pair

2:  for i = 1 to n do
3:      w_i ← |D_i| / Σ_j |D_j|
        ▷ Compute aggregation weights

4:  for i = 1 to n do
5:      u_i ← U[-B, B]^{N/2}
        ▷ Sample independent random masks

6:  u_mean ← Σ_{i=1}^n w_i · u_i

7:  for i = 1 to n do
8:      b_i ← u_i - u_mean
        ▷ Construct zero-sum masks

9:  assert Σ_i w_i · b_i = 0
    ▷ Verify zero-sum property

10: key_bundle ← (sk, {b_i}_{i=1}^n, {w_i}_{i=1}^n)

11: sealed_bundle ← TEE.Seal(key_bundle, enclave_identity)

12: for i = 1 to n do
13:     Send (sk, b_i) to Client_i via TLS
        ▷ Client_i learns only its own mask

14: Send (pk, evk) to Server Host via TLS
15: Send sealed_bundle to Server Host → load into TEE
16: Broadcast pk, evk to all entities

17: KGC.DestroyAllSensitiveState()
    ▷ KGC goes offline permanently
```

### 算法 2: 客户端训练与加密上传 (Client Upload)

```
Algorithm 2: Client Training and Encrypted Upload
────────────────────────────────────────────────────────
Input: Global model W, local dataset D_i, mask b_i,
       PTopk residual r^{(i)}, sparsity rate ρ,
       CKKS public key pk, batch size S
Output: Sparse encrypted update upload_i

1:  g_i ← ∇_θ L_i(W; D_i)
    ▷ Local training (SGD)

2:  [g_{i,0}; ...; g_{i,m-1}] ← FlattenAndSplit(g_i, S)
    ▷ Split into m batches of size S = N/2

3:  ┌─ PTopk Client Residual ───────────────────────┐
4:  │  for j = 0 to m-1 do                          │
5:  │      g̃_{i,j} ← g_{i,j} + r_j^{(i)}            │
6:  │                                               │
7:  │  score_j ← (1/S) Σ_l |g̃_{i,j,l}|             │
8:  │  S_selected ← TopK({score_j}, ⌈ρ·m⌉)          │
9:  │                                               │
10: │  for j = 0 to m-1 do                          │
11: │      if j ∈ S_selected then r_j^{(i)} ← 0     │
12: │      else r_j^{(i)} ← g̃_{i,j}                 │
13: └────────────────────────────────────────────────┘

14: ┌─ Blind and Encrypt ───────────────────────────┐
15: │  ciphertexts ← []                              │
16: │  mask ← [0]^m                                  │
17: │  for j ∈ S_selected do                         │
18: │      u_{i,j} ← g̃_{i,j} + b_{i,j}              │
19: │      z_j ← CKKS.Encode(u_{i,j}, Δ)            │
20: │      ct_j ← CKKS.Enc(pk, z_j)                 │
21: │      ciphertexts.append(ct_j.serialize())      │
22: │      mask[j] ← 1                               │
23: └────────────────────────────────────────────────┘

24: upload_i ← {`__sparse__`: True,
               `ciphertexts`: ciphertexts,
               `mask`: mask,
               `batch_size`: S,
               `total_elements`: d,
               `shapes`: layer_shapes,
               `offsets`: layer_offsets}

25: Send upload_i to Server Host via HTTPS
```

### 算法 3: TEE 聚合、全局残差与预取准备 (TEE Aggregation)

```
Algorithm 3: TEE Aggregation with Global Residual
────────────────────────────────────────────────────────
Input: Old global ciphertext ct_{global}^{(t-1)},
       Client uploads {upload_i}_{i∈S_active},
       Client weights {w_i}, sealed_bundle,
       TEE sparsity rate ρ^{TEE}, learning rate η
Output: New global ciphertext ct_{global}^{(t)},
        Sparse delta ct_Δ for prefetch

1:  (sk, {b_i}, {w_i}) ← TEE.Unseal(sealed_bundle)

2:  W_old ← TEE.LoadCachedPlainModel()
    ▷ TEE maintains plaintext cache of global model

3:  ┌─ Decrypt and Aggregate per Batch ─────────────┐
4:  │  for j = 0 to m-1 do                          │
5:  │      C_j ← {i : upload_i.mask[j] = 1}         │
6:  │      if C_j = ∅ then                           │
7:  │          δ_{pure,j} ← 0                        │
8:  │          continue                              │
9:  │                                               │
10: │      w̃_i ← w_i / Σ_{k∈C_j} w_k                │
11: │      ct_{agg,j} ← Σ_{i∈C_j} w̃_i · ct_{i,j}   │
12: │                                               │
13: │      δ_{plain,j} ← CKKS.Dec(sk, ct_{agg,j})   │
14: │      β_j ← Σ_{i∈C_j} w̃_i · b_{i,j}           │
15: │      δ_{pure,j} ← δ_{plain,j} - β_j           │
16: │            ▷ Mask cancellation in TEE          │
17: └────────────────────────────────────────────────┘

18: ┌─ Global Residual Compensation ─────────────────┐
19: │  R ← TEE.LoadGlobalResidual()                  │
20: │  for j = 0 to m-1 do                          │
21: │      c_j ← δ_{pure,j} + R_j                   │
22: │                                               │
23: │  S_tee ← TopK({‖c_j‖_1/S}, ⌈ρ^{TEE}·m⌉)      │
24: │                                               │
25: │  for j = 0 to m-1 do                          │
26: │      if j ∈ S_tee then                        │
27: │          δ̃_j ← c_j                             │
28: │          R_j ← 0                               │
29: │      else                                      │
30: │          δ̃_j ← 0                               │
31: │          R_j ← c_j                             │
32: │  TEE.SaveGlobalResidual(R)                    │
33: └────────────────────────────────────────────────┘

34: ┌─ Update Plain Model and Re-encrypt ────────────┐
35: │  for j = 0 to m-1 do                          │
36: │      W_{t,j} ← W_{old,j} + η·δ̃_j              │
37: │                                               │
38: │  ct_new ← []                                   │
39: │  for j ∈ S_tee do                             │
40: │      z_j ← CKKS.Encode(W_{t,j}, Δ)            │
41: │      ct_j ← CKKS.Enc(pk, z_j)                 │
42: │      ct_new.append(ct_j)                       │
43: │                                               │
44: │  TEE.SavePlainModel(W_t)                       │
45: └────────────────────────────────────────────────┘

46: ┌─ Compute Sparse Delta on Host ─────────────────┐
47: │  ct_Δ ← []                                     │
48: │  for j ∈ S_tee do                             │
49: │      Δct_j ← ct_{new,j} - ct_{global,j}^{(t-1)}│
50: │      ct_Δ.append(Δct_j.serialize())            │
51: └────────────────────────────────────────────────┘

52: ct_{global}^{(t)} ← Merge(ct_{global}^{(t-1)}, ct_new, S_tee)

53: ┌─ Security Cleanup ─────────────────────────────┐
54: │  MemoryZeroize(sk, {b_i}, δ_{pure}, δ̃, W_old) │
55: └────────────────────────────────────────────────┘

56: return (ct_{global}^{(t)}, ct_Δ, S_tee)
```

### 算法 4: 客户端预取接收与训练前应用 (Client Prefetch & Apply)

```
Algorithm 4: Client Prefetch Reception and Pre-training Apply
────────────────────────────────────────────────────────
Input: Prefetch delta ct_Δ (or ∅),
       Client secret key sk, base model W_base,
       prefetched_state (cached ciphertext)
Output: Updated local model W_current for training

1:  ┌─ Receive Prefetch Delta ──────────────────────┐
2:  │  if ct_Δ ≠ ∅ then                              │
3:  │      if prefetched_state = ∅ then              │
4:  │          prefetched_state ← ct_Δ               │
5:  │      else                                      │
6:  │          prefetched_state ←                    │
7:  │              CKKS.Add(prefetched_state, ct_Δ) │
8:  │          ▷ Homomorphic addition, size unchanged│
9:  └────────────────────────────────────────────────┘

10: ┌─ Apply Before Training ────────────────────────┐
11: │  if prefetched_state ≠ ∅ then                  │
12: │      Δ_plain ← CKKS.Dec(sk, prefetched_state) │
13: │      Δ_plain ← Δ_plain / Δ                     │
14: │                                               │
15: │      W_current ← W_base + Δ_plain             │
16: │      ▷ Apply accumulated deltas to base model  │
17: │                                               │
18: │      prefetched_state ← ∅                      │
19: │      W_base ← W_current                        │
20: │  else                                          │
21: │      W_current ← W_base                        │
22: └────────────────────────────────────────────────┘

23: return W_current
```

---

## 六、威胁模型分析

### 6.1 攻击者能力定义

| 实体 | 能力 | 目标 |
|------|------|------|
| **半诚实客户端** (Honest-but-Curious Client) | 遵循协议，但试图从收到的信息中推断其他客户端的梯度 | 重建 $g_j$（$j \neq i$） |
| **半诚实服务器** (Honest-but-Curious Server) | 遵循聚合协议，但试图解密单个客户端更新 | 重建 $g_i$ |
| **恶意服务器** (Malicious Server) | 可篡改聚合权重、伪造预取 delta、选择性丢弃客户端更新 | 破坏模型收敛或提取隐私 |
| **客户端合谋** ($k$-Collusion) | $k$ 个客户端共享信息，联合推断非合谋客户端的梯度 | 绕过盲化掩码保护 |
| **TEE 侧信道攻击者** | 通过时序、缓存、功耗等侧信道推断 TEE 内数据 | 提取 sk 或明文梯度 |

### 6.2 安全性分析

#### 定理 1：对半诚实服务器的 IND-CPA 安全性

**陈述**：Server Host 无法从密文 upload$_i$ 中获得 Client $i$ 的明文梯度 $\mathbf{g}_i$ 的任何信息。

**证明**：
1. upload$_i$ 是标准 CKKS 密文，其语义安全性基于 RLWE 困难假设。
2. Server Host 仅持有 $\mathbf{pk}$，不持有 $\mathbf{sk}$（sk 仅在 TEE 密封存储中）。
3. 在决策型 RLWE 假设下，$(\mathbf{a}, \mathbf{a}\mathbf{s} + \mathbf{e} + \mathbf{m})$ 与均匀分布不可区分。
4. 因此，Server Host 对 upload$_i$ 的视图与对随机密文的视图计算不可区分。

**结论**：Server Host 对单个客户端更新具有 IND-CPA 安全性。

#### 定理 2：对半诚实客户端的梯度隐私性

**陈述**：在零和掩码保护下，半诚实 Client $j$ 无法从聚合结果中推断 Client $i$（$j \neq i$）的明文梯度。

**证明**：
1. Client $j$ 知道 $(\mathbf{s}, \mathbf{b}_j)$，但不知道 $\mathbf{b}_i$（$i \neq j$）。
2. 若 Client $j$ 解密聚合密文（假设它能获取），得到：
   $$
   \boldsymbol{\delta}_{\text{plain}} = \sum_k \tilde{w}_k (\mathbf{g}_k + \mathbf{r}_k + \mathbf{b}_k) + \boldsymbol{\epsilon}
   $$
3. Client $j$ 可减去自己的贡献 $\tilde{w}_j(\mathbf{g}_j + \mathbf{r}_j + \mathbf{b}_j)$，但剩余项仍包含 $\mathbf{b}_i$（$i \neq j$）。
4. 由于 $\mathbf{b}_i$ 是 $[-B, B]$ 上的均匀随机向量，剩余项是 $\mathbf{g}_i$ 与均匀噪声的叠加，信息论上不可分离。
5. 即使 $n-2$ 个客户端合谋，它们知道 $\sum_{k \neq i,j} \tilde{w}_k \mathbf{b}_k$，但零和约束仅给出 $\tilde{w}_i \mathbf{b}_i + \tilde{w}_j \mathbf{b}_j = -\sum_{k \neq i,j} \tilde{w}_k \mathbf{b}_k$。两个未知数一个方程，无法确定 $\mathbf{b}_i$。

**结论**：在 $< n-1$ 合谋下，盲化掩码提供信息论隐私保护。

#### 定理 3：对合谋客户端的攻击下界

**陈述**：若 $k = n-1$ 个客户端合谋，它们可以完全恢复非合谋客户端的梯度。

**证明**：
1. $n-1$ 个合谋客户端知道 $\{\mathbf{b}_j\}_{j \in \text{collusion}}$。
2. 由零和约束 $\sum_i w_i \mathbf{b}_i = \mathbf{0}$，可解出：
   $$
   \mathbf{b}_{\text{target}} = -\frac{1}{w_{\text{target}}} \sum_{j \in \text{collusion}} w_j \mathbf{b}_j
   $$
3. 知道 $\mathbf{b}_{\text{target}}$ 后，可从聚合结果中精确减去其贡献，恢复目标客户端梯度。

**缓解**：在实际 cross-silo FL 中，机构数量 $n$ 较小（如 5-20），但机构间存在法律约束和声誉机制，$n-1$ 合谋的概率极低。对于更高安全需求，可引入差分隐私在 Client 加密前添加校准噪声。

#### 定理 4：TEE 信任边界的安全性

**陈述**：TEE 内数据对 Server Host 和外部攻击者不可访问。

**依赖假设**：
1. TEE 硬件实现正确（Intel SGX/ARM TrustZone 无已知漏洞）。
2. 远程 attestation 成功验证 enclave 代码完整性。
3. 侧信道攻击（缓存时序、功耗分析）通过恒定时间实现和噪声注入缓解。

**证明概要**：
- TEE 内存通过硬件加密隔离，Server Host OS 无法读取。
- Sealed bundle 仅可被具有正确 enclave identity 的实例解封。
- 即使 Server Host 完全沦陷，无法提取 TEE 内存中的 sk 或明文梯度。

#### 定理 5：预取 Delta 的完整性

**陈述**：恶意 Server 无法通过篡改预取 delta 来破坏客户端模型，因为任何篡改都会被客户端的本地训练抵消。

**注意**：这不是真正的安全性定理，而是鲁棒性观察。恶意 Server 确实可以发送错误的 delta，导致客户端本地模型偏离正确全局模型。但由于：
1. 客户端上传的是本地梯度差值，不依赖于全局模型的绝对值；
2. 下一轮聚合会重新校正；

系统对小的 delta 篡改具有自恢复能力。但持续的大幅度篡改会导致收敛失败。

**严格安全需求**：可对预取 delta 附加数字签名（Server 私钥签名，Client 公钥验证），确保 delta 来源可信。

### 6.3 威胁矩阵总结

| 威胁 | 影响 | 防御机制 | 残余风险 |
|------|------|---------|---------|
| 半诚实服务器窥探单客户端梯度 | 隐私泄露 | RLWE + 盲化掩码 | 无（计算安全） |
| 半诚实客户端窥探其他客户端梯度 | 隐私泄露 | 零和掩码 | 需 $< n-1$ 合谋 |
| $n-1$ 客户端合谋 | 完全泄露目标梯度 | 法律约束 + 可选 DP | 信息论上限 |
| 恶意服务器篡改聚合权重 | 模型损坏 | TEE 内密封权重验证 | TEE 被攻破 |
| 恶意服务器丢弃客户端更新 | 收敛变慢 | 客户端本地监控精度 | 无法检测选择性丢弃 |
| TEE 侧信道攻击 | sk/梯度泄露 | 恒定时间 + 噪声 | 高级侧信道仍可能 |
| 预取 delta 中间人篡改 | 客户端模型损坏 | HTTPS + 可选签名 | 证书被劫持 |

---

## 七、与 README 文档的一致性检查

### 7.1 设计目标一致性

| README 描述 | 本文档对应 | 一致性 |
|------------|-----------|--------|
| "加权零和盲化掩码解决客户端合谋漏洞" | 定理 2、3 的零和掩码推导 | ✅ 一致 |
| "TEE 内解密 → 掩码抵消 → 模型更新" | 算法 3 Step 5.2-5.3 | ✅ 一致 |
| "PTopk 客户端残差 + 服务器累加器" | 第 4 节 PTopk 数学表述 | ✅ 一致 |
| "TEE 开启时 Host 侧累加器自动禁用" | 第 4.3 节 TEE vs PTopk 对比 | ✅ 一致 |
| "密文预取：同态加法累加，大小不变" | 第 3.7.2 节同态加法推导 | ✅ 一致 |
| "fetch 时服务器预先同态累加多个 deltas" | 算法 3 输出 ct_Δ 为单密文 | ✅ 一致 |
| "KGC 初始化后离线" | 算法 1 Step 17 | ✅ 一致 |

### 7.2 实现细节一致性

| 代码实现 | 本文档公式 | 一致性 |
|---------|-----------|--------|
| `tee_simulator.py` 中 `weighted_average` 先归一化后累加 | 第 3.4 节 $\tilde{w}_i = w_i / \sum w_k$ | ✅ 一致 |
| `_compute_sparse_delta` 中 `evaluator.sub` | 第 3.6 节 $\text{ct}_\Delta = \text{ct}_{\text{new}} - \text{ct}_{\text{old}}$ | ✅ 一致 |
| `_merge_tee_result` 反序列化为 CKKSVector | 第 3.6 节 $\text{ct}_{\text{global},j}^{(t)}$ 替换逻辑 | ✅ 一致 |
| `ptopk.py` 中 `update_residual` 选中清零 | 第 3.2 节残差更新规则 | ✅ 一致 |
| `client.py` 中 `receive_prefetch_delta` 同态累加 | 算法 4 Step 6-7 | ✅ 一致 |
| `apply_prefetched_state` 解密后加到 base model | 算法 4 Step 15 | ✅ 一致 |

### 7.3 差异与澄清

| 差异点 | README 描述 | 本文档/代码实际 | 说明 |
|--------|------------|----------------|------|
| 下行通信量 | README 假设 TEE 路径下行是稀疏 delta | 非 Prefetch 路径实际下行是完整模型 | 设计意图 vs 当前实现的分层：Prefetch 路径实现真正下行压缩，非 Prefetch 路径依赖完整模型获取 |
| 服务器累加器 | README 第 12.4 Step 6 描述 delayed/momentum | 代码中 TEE 开启时 `server_mode = 'none'` | 为避免 TEE 全局残差 $R_t$ 与 Host 累加器双重补偿，TEE 路径禁用 Host 累加器 |
| 掩码生成 | README 描述 KGC 生成 | 当前代码中 TEE 路径暂未实现掩码 | 掩码为 TESK-EGD-ZM 的完整方案设计，代码实现中 TEE 路径当前为简化版（无掩码），但架构预留了接口 |

### 7.4 结论

本文档的数学推导、伪代码设计与威胁模型分析与 README 文档及代码实现**高度一致**。核心差异在于：

1. **README 描述的是完整设计蓝图**（含掩码、完整闭环），本文档严格按该蓝图推导。
2. **当前代码实现为分层可插拔架构**：TEE 路径可先独立运行（无明文掩码），后续通过 `TEEProcessor` 扩展即可无缝接入掩码抵消逻辑。
3. **非 Prefetch 路径的下行压缩**：当前实现中客户端每轮获取完整模型，这是架构兼容性的折中。启用 Prefetch 后自动切换为稀疏 delta 下发，实现 README 描述的完整闭环。

---

*文档生成时间：2026-04-28*
*对应代码版本：ckks_fed_robustness TEE 方案①实现*
