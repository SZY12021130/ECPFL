# PTopK: Packed TopK with Dual-Scale Residual Decay

> **文档定位**：`paper/ptopk_formula.md`  
> **适用范围**：CKKS-Fed 框架下客户端 PTopK 双重衰减残差补偿的端到端数学公式。  
> **写作规范**：符号系统与 `formula.md`、`mask_formula.md` 保持一致；统一使用 $g_i^{(t)}$ 表示原始梯度，$\tilde{\mathbf{g}}_{i,j}^{(t)}$ 表示补偿后第 $j$ 个 batch 的梯度。

---

## 1. 符号表

| 符号 | 含义 | 定义域 / 维度 | 备注 |
|:---|:---|:---|:---|
| $t$ | 全局轮次索引 | $t = 0, 1, \ldots, T-1$ | 共 $T$ 轮 |
| $i$ | 客户端索引 | $i \in [n] \triangleq \{1, 2, \ldots, n\}$ | |
| $j$ | Batch（包）索引 | $j \in \{0, 1, \ldots, J-1\}$ | |
| $J$ | 总 batch 数 | $J = \lceil m / S \rceil$ | |
| $S$ | 每个 batch 的 slot 数 | $S = N / 2$ | $N$ 为 CKKS `poly_modulus_degree` |
| $m$ | 模型扁平化后的总参数量 | $m \in \mathbb{Z}^+$ | |
| $g_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮的**原始梯度** | $g_i^{(t)} \in \mathbb{R}^m$ | upload_difference = true 时，$g_i^{(t)} = \theta_i^{(t)} - \theta^{(t)}$ |
| $g_{i,j}^{(t)}$ | 原始梯度第 $j$ 个 batch | $g_{i,j}^{(t)} \in \mathbb{R}^S$ | $g_{i,j}^{(t)} = \mathcal{B}_j(g_i^{(t)})$ |
| $\mathbf{r}_{i,j}^{(t)}$ | 客户端 $i$ 对 batch $j$ 的残差累加器 | $\mathbf{r}_{i,j}^{(t)} \in \mathbb{R}^S$ | PTopK 误差反馈机制 |
| $\tilde{\mathbf{g}}_{i,j}^{(t)}$ | **残差补偿后的梯度**（batch $j$） | $\tilde{\mathbf{g}}_{i,j}^{(t)} \in \mathbb{R}^S$ | 本文档核心统一符号 |
| $\rho \in (0,1]$ | 上行稀疏率 | — | 即 `sparsity_rate` |
| $\gamma_d \in (0,1]$ | 每轮自然衰减因子 | — | `decay_gamma`，防止连续多轮未选中导致残差爆炸 |
| $\gamma_s \in (0,1]$ | 跨轮陈旧衰减因子 | — | `stale_gamma`，客户端间歇性参与时的指数衰减 |
| $\mathcal{B}_j(\cdot)$ | 向量切分算子（第 $j$ 个 batch） | $\mathcal{B}_j: \mathbb{R}^m \to \mathbb{R}^S$ | 末尾不足补零 |
| $\mathcal{S}_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮选中的 batch 索引集合 | $\mathcal{S}_i^{(t)} \subseteq \{0, \ldots, J-1\}$ | $|\mathcal{S}_i^{(t)}| = \max(1, \lceil \rho J \rceil)$ |
| $u_{i,j}^{(t)}$ | 客户端 $i$ 实际上传的稀疏 batch | $u_{i,j}^{(t)} \in \mathbb{R}^S$ | 未选中位置为 $\mathbf{0}$ |
| $\Delta t_i^{(t)}$ | 客户端 $i$ 距上次参与的轮数间隔 | $\Delta t_i^{(t)} \ge 1$ | $\Delta t = 1$ 表示连续参与 |

---

## 2. Step 1：Batch 切分

将原始梯度 $g_i^{(t)}$ 扁平化后按固定 batch size $S$ 切分为 $J$ 个 batch：

$$
g_{i,j}^{(t)} = \mathcal{B}_j\bigl(g_i^{(t)}\bigr) \in \mathbb{R}^S, \quad j = 0, 1, \ldots, J-1.
$$

---

## 3. Step 2：残差补偿（Residual Compensation）

客户端 $i$ 维护一个残差累加器 $\mathbf{r}_i^{(t)} = (\mathbf{r}_{i,0}^{(t)}, \ldots, \mathbf{r}_{i,J-1}^{(t)})$，初始状态为 $\mathbf{r}_i^{(0)} = \mathbf{0}$。

在 TopK 选择之前，将历史残差加到当前各 batch 上，得到**补偿后梯度**：

$$
\boxed{
\tilde{\mathbf{g}}_{i,j}^{(t)} = g_{i,j}^{(t)} + \mathbf{r}_{i,j}^{(t)}, \quad \forall j \in \{0, \ldots, J-1\}
}
\tag{1}
$$

> **关键约定**：$\tilde{\mathbf{g}}_{i,j}^{(t)}$ 是本文档统一使用的补偿后梯度符号，替代此前各类文档中不统一的 $\hat{\mathbf{b}}_{t,k}$、$\hat{g}_{i,j}^{(t)}$ 等写法。

---

## 4. Step 3：Batch-Level TopK 选择

按 batch 内 $\ell_1$ 范数排序，保留前 $\lceil \rho J \rceil$ 个 batch：

$$
\mathcal{S}_i^{(t)} = \operatorname{TopK}_\rho\!\left(\bigl\{\|\tilde{\mathbf{g}}_{i,j}^{(t)}\|_1\bigr\}_{j=0}^{J-1}\right), \qquad |\mathcal{S}_i^{(t)}| = \max\bigl(1, \lceil \rho J \rceil\bigr).
$$

仅选中的 batch 进入加密上传流程：

$$
u_{i,j}^{(t)} =
\begin{cases}
\tilde{\mathbf{g}}_{i,j}^{(t)} & \text{if } j \in \mathcal{S}_i^{(t)}, \\[6pt]
\mathbf{0} & \text{otherwise}.
\end{cases}
\tag{2}
$$

---

## 5. Step 4：残差更新（双重衰减机制）

根据选中结果更新残差累加器，引入两种衰减机制：

### 5.1 每轮自然衰减（$\gamma_d$）

对于**未被选中**的 batch，保留其补偿值但按 $\gamma_d$ 衰减，防止连续多轮未选中导致残差无限增长：

$$
\boxed{
\mathbf{r}_{i,j}^{(t+1)} =
\begin{cases}
\mathbf{0} & \text{if } j \in \mathcal{S}_i^{(t)} \quad \text{（已上传，残差清零）}, \\[8pt]
\gamma_d \cdot \tilde{\mathbf{g}}_{i,j}^{(t)} & \text{if } j \notin \mathcal{S}_i^{(t)} \quad \text{（未选中，保留并衰减）}.
\end{cases}
}
\tag{3}
$$

对应代码：`ptopk.py::update_residual()` 中 `if self.client_residual_decay < 0.9999: new_residual[j] *= self.client_residual_decay`。

### 5.2 跨轮陈旧衰减（$\gamma_s$）

在跨设备联邦学习中，客户端可能间歇性参与。设 $\Delta t_i^{(t)} \ge 1$ 为客户端 $i$ 距上次实际参与训练的轮数间隔。在第 $t$ 轮应用式 (1) 之前，若 $\Delta t_i^{(t)} > 1$，先对现有残差执行指数衰减：

$$
\boxed{
\mathbf{r}_{i,j}^{(t)} \;\gets\; \gamma_s^{\,\Delta t_i^{(t)} - 1} \cdot \mathbf{r}_{i,j}^{(t)}, \qquad \text{if } \Delta t_i^{(t)} > 1.
}
\tag{4}
$$

当 $\Delta t_i^{(t)} = 1$（连续参与）时，不应用陈旧衰减。

对应代码：`ptopk.py::decay_residual_by_gap(gap)` 中 `scale = gamma ** (gap - 1)`。

---

## 6. 紧凑向量形式（核心递推式）

定义元素级 TopK 掩码算子 $\mathcal{M}_\rho(\cdot)$：对输入向量保留 Top-$\rho$ 批次（按 $\ell_1$ 范数），其余位置置零。每轮训练后的 error-feedback 核心递推式为：

$$
\boxed{
\mathbf{r}_i^{(t+1)} = \gamma_d \cdot \Bigl[ \bigl(\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)}\bigr) - \mathcal{M}_\rho\bigl(\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)}\bigr) \Bigr]
}
\tag{5}
$$

等价经典 error-feedback 写法：

$$
\mathbf{r}_i^{(t+1)} = \gamma_d \cdot \Bigl[ \bigl(\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)}\bigr) - \operatorname{TopK}_\rho\bigl(\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)}\bigr) \Bigr],
\tag{5a}
$$

其中 $\operatorname{TopK}_\rho(\cdot)$ 返回仅保留 Top-$\rho$ batch、其余位置为零的向量。

> **直观解释**：方括号内就是"本轮本应上传的全部梯度减去实际上传的 TopK 部分"，即被压缩掉的信息；乘以 $\gamma_d$ 后存入残差，留待下一轮补偿。

---

## 7. 跨轮陈旧衰减（间歇性参与）

若客户端 $i$ 在第 $t$ 轮训练后，间隔 $\Delta t \ge 1$ 轮才再次参与，则在重新参与**前**对残差执行一次性指数衰减：

$$
\boxed{
\mathbf{r}_i^{(t+\Delta t)} = \gamma_s^{\,\Delta t - 1} \cdot \mathbf{r}_i^{(t+1)}
}
\tag{6}
$$

**注意**：
- 两种衰减作用于**不同时间尺度**：$\gamma_d$ 在每轮训练后立即作用，$\gamma_s$ 在重新参与前一次性作用
- 缺席期间（$t+1, \dots, t+\Delta t-1$），残差**保持不变**（代码不触碰）
- $\Delta t = 1$（连续参与）：$\gamma_s^0 = 1$，式 (6) 为 no-op，系统退化为仅式 (5)
- $\gamma_d = \gamma_s = 1$：退化为标准 PTopK（无衰减）

---

## 8. 特殊情形与配置建议

| 情形 | 参数设置 | 残差更新公式 | 适用场景 |
|:---|:---|:---|:---|
| **标准 PTopK**（无衰减） | $\gamma_d = 1, \gamma_s = 1$ | $\mathbf{r}_i^{(t+1)} = (\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)}) - \operatorname{TopK}_\rho(\mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t)})$ | 连续参与、IID 场景 |
| 仅自然衰减 | $\gamma_d < 1, \gamma_s = 1$ | $\mathbf{r}_i^{(t+1)} = \gamma_d \cdot \mathbf{r}_i^{(t)}$（未选中 batch） | 高频参与、需控制残差累积 |
| 仅陈旧衰减 | $\gamma_d = 1, \gamma_s < 1$ | $\mathbf{r}_i^{(t)} = \gamma_s^{\Delta t - 1} \cdot \mathbf{r}_i^{(t_{\text{last}})}$ | 低频参与、间歇性同步 |
| **推荐配置** | $\gamma_d = 0.3, \gamma_s = 0.5$ | 双重衰减同时生效 | 非 IID 跨设备 FL（本文实验配置） |

---

## 9. 与现有文档的符号映射

| 本文档符号 | `formula.md` | `mask_formula.md` | 代码对应 |
|:---|:---|:---|:---|
| $g_i^{(t)}$ | $\boldsymbol{\Delta}_t$（客户端完整更新） | $g_i^{(t)}$ | `client_grad` |
| $\tilde{\mathbf{g}}_{i,j}^{(t)}$ | $\hat{\mathbf{b}}_{t,k}$ | — | `compensated[j]` |
| $\mathbf{r}_{i,j}^{(t)}$ | $\mathbf{r}_{t,k}$ | $r_i^{(r)}$ | `client_residual[j]` |
| $\gamma_d$ | — | — | `client_residual_decay` |
| $\gamma_s$ | — | — | `client_residual_stale_gamma` |
| $\mathcal{S}_i^{(t)}$ | $\mathcal{S}_t$ | $\mathcal{M}_i^{(t)}$ | `selected_indices` |
| $u_{i,j}^{(t)}$ | $\text{Upload}_t$ | $u_{i,j}^{(t)}$ | 加密上传的 batch |

---

## 10. 收敛性质（非正式命题）

**命题（残差消逝性）**。若梯度序列 $\{\mathbf{g}_i^{(t)}\}_{t\ge 0}$ 有界，且衰减因子满足 $\gamma_d \in (0,1)$ 或 $\gamma_s \in (0,1)$，则残差范数的期望衰减至零：

$$
\lim_{t\to\infty} \mathbb{E}\bigl[\|\mathbf{r}_i^{(t)}\|_2\bigr] = 0.
$$

进而，累积上传量渐近收敛于累积原始梯度：

$$
\sum_{\tau=0}^{t} u_i^{(\tau)} \;\xrightarrow{t\to\infty}\; \sum_{\tau=0}^{t} \mathbf{g}_i^{(\tau)},
$$

保证聚合的无偏性。

---

## 11. 代码实现索引

| 公式 | 代码位置 | 函数 |
|:---|:---|:---|
| 式 (1) 残差补偿 | `ckks_fed/ptopk.py` | `PTopkModule.apply_residual()` |
| 式 (3) 残差更新 | `ckks_fed/ptopk.py` | `PTopkModule.update_residual()` |
| 式 (4) 陈旧衰减 | `ckks_fed/ptopk.py` | `PTopkModule.decay_residual_by_gap()` |
| 式 (2) TopK 选择 | `ckks_fed/ptopk.py` | `PTopkWrappedStrategy.select_batches()` |
| 包装器入口 | `ckks_fed/ptopk.py` | `PTopkModule.wrap_strategy()` |
| 互斥模式开关 | `ckks_fed/ptopk.py` | `PTopkModule.client_residual.mutually_exclusive` |

### 互斥模式配置

```yaml
ptopk:
  client_residual:
    mutually_exclusive: false  # false=顺序相乘（默认），true=互斥模式
```

- **`false`（顺序相乘）**：连续参与时每轮对未选中 batch 乘 $\gamma_d$；缺席回来后先整体乘 $\gamma_s^{\Delta t-1}$，再在本轮训练后对未选中 batch 乘 $\gamma_d$。
- **`true`（互斥）**：连续参与时只用 $\gamma_d$；缺席回来后只用 $\gamma_s^{\Delta t-1}$，**跳过该轮的 $\gamma_d$**。

---

## 参考文献

1. Sattler, F., Wiedemann, S., Müller, K. R., & Samek, W. (2020). Robust and communication-efficient federated learning from non-iid data. *IEEE Transactions on Neural Networks and Learning Systems*, 31(9), 3400-3413.（STC / Error Feedback）
2. 本项目代码：`ckks_fed/ptopk.py`（双重衰减实现）
