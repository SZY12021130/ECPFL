# KGC 零和盲化掩码：Auto 模式完整公式推导

> **文档定位**：`paper/mask_formula.md`  
> **适用范围**：CKKS-Fed 框架下可插拔零和盲化掩码（`blinding_mask.compensation_mode = "auto"`）的端到端数学闭环。  
> **写作规范**：符号系统与 `rlwe_full_derivation.md`、`PAMP_framework.md` 保持一致；FL 轮次用 $t$，客户端用 $i$，梯度用 $g$，掩码用 $b$，batch 用 $j$。

---

## 目录

1. [符号与参数总表](#1-符号与参数总表)
2. [核心安全假设](#2-核心安全假设)
3. [Phase 0：KGC 离线掩码生成](#3-phase-0kgc-离线掩码生成)
4. [Phase 1：客户端本地训练](#4-phase-1客户端本地训练)
5. [Phase 2：客户端掩码注入](#5-phase-2客户端掩码注入)
6. [Phase 3：客户端稀疏化（TopK / RandK）](#6-phase-3客户端稀疏化topk--randk)
7. [Phase 4：客户端 CKKS 加密上传](#7-phase-4客户端-ckks-加密上传)
8. [Phase 5：TEE 解密](#8-phase-5tee-解密)
9. [Phase 6：TEE 明文聚合与掩码补偿](#9-phase-6tee-明文聚合与掩码补偿)
10. [Phase 7：TEE 全局残差累加（PTopK）](#10-phase-7tee-全局残差累加ptopk)
11. [Phase 8：TEE 二次压缩（TopK）](#11-phase-8tee-二次压缩topk)
12. [Phase 9：全局模型更新](#12-phase-9全局模型更新)
13. [Phase 10：TEE 重加密与输出](#13-phase-10tee-重加密与输出)
14. [闭环正确性验证](#14-闭环正确性验证)
15. [隐私分析](#15-隐私分析)
16. [Auto 补偿模式的判定逻辑](#16-auto-补偿模式的判定逻辑)

---

## 1. 符号与参数总表

| 符号 | 含义 | 定义域 / 维度 | 备注 |
|:---|:---|:---|:---|
| $t$ | 联邦学习轮次索引 | $t = 0, 1, \ldots, T-1$ | 共 $T$ 轮 |
| $n$ | 客户端总数 | $n \in \mathbb{Z}^+$ | |
| $i$ | 客户端索引 | $i \in [n] \triangleq \{1, 2, \ldots, n\}$ | |
| $w_i$ | 客户端 $i$ 的聚合权重 | $w_i > 0$, $\sum_{i=1}^n w_i = 1$ | 通常为数据量占比 $w_i = \|\mathcal{D}_i\| / \sum_{k=1}^n \|\mathcal{D}_k\|$ |
| $m$ | 模型扁平化后的总参数个数 | $m \in \mathbb{Z}^+$ | |
| $j$ | batch（包）索引 | $j \in \{0, 1, \ldots, J-1\}$ | |
| $J$ | batch 总数 | $J = \lceil m / S \rceil$ | |
| $S$ | 每个 batch 的 slot 数 | $S = N / 2$ | $N$ 为 `poly_modulus_degree` |
| $N$ | CKKS 多项式模次数 | $N \in \{4096, 8192, 16384, \ldots\}$ | 本框架默认 $N = 8192$ |
| $\theta^{(t)}$ | 第 $t$ 轮全局模型参数 | $\theta^{(t)} \in \mathbb{R}^m$ | 明文域 |
| $\theta_i^{(t)}$ | 客户端 $i$ 本地训练后的模型 | $\theta_i^{(t)} \in \mathbb{R}^m$ | |
| $g_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮的本地梯度更新 | $g_i^{(t)} \in \mathbb{R}^m$ | upload_difference = true 时，$g_i^{(t)} = \theta_i^{(t)} - \theta^{(t)}$ |
| $b_i$ | KGC 为客户端 $i$ 生成的盲化掩码 | $b_i \in \mathbb{R}^m$ | 初始化一次，跨轮次复用 |
| $b_{i,j}$ | 掩码 $b_i$ 的第 $j$ 个 batch | $b_{i,j} \in \mathbb{R}^S$ | $b_{i,j}[k] = b_i[j \cdot S + k]$ |
| $B$ | 掩码采样范围参数 | $B > 0$ | 掩码分量 $b_i[k] \sim \mathcal{U}([-B, B])$ |
| $\mathcal{B}_j(\cdot)$ | 向量切分算子（第 $j$ 个 batch） | $\mathcal{B}_j: \mathbb{R}^m \to \mathbb{R}^S$ | 末尾不足补零 |
| $\mathcal{M}_i^{(t)}$ | 客户端 $i$ 第 $t$ 轮的上传掩码 | $\mathcal{M}_i^{(t)} \in \{0, 1\}^J$ | $\mathcal{M}_{i,j}^{(t)} = 1$ 表示上传 batch $j$ |
| $S_j^{(t)}$ | 第 $t$ 轮上传了 batch $j$ 的客户端集合 | $S_j^{(t)} \subseteq [n]$ | $S_j^{(t)} = \{ i \mid \mathcal{M}_{i,j}^{(t)} = 1 \}$ |
| $W_j^{(t)}$ | batch $j$ 的归一化分母 | $W_j^{(t)} \in \mathbb{R}^+$ | $W_j^{(t)} = \sum_{i \in S_j^{(t)}} w_i$ |
| $\text{Enc}_{\text{CKKS}}(\cdot)$ | CKKS 加密函数 | 输出：CKKSVector / 字节串 | 使用公钥加密 |
| $\text{Dec}_{\text{CKKS}}(\cdot)$ | CKKS 解密函数 | 输出：$\mathbb{R}^S$ | 使用私钥解密，仅 TEE 持有 |
| $\Delta^{(t)}$ | 第 $t$ 轮聚合后的全局模型更新 | $\Delta^{(t)} \in \mathbb{R}^m$ | 稀疏或全量 |
| $R^{(t)}$ | TEE 内全局残差累加器 | $R^{(t)} \in \mathbb{R}^m$ | PTopK 误差反馈机制 |
| $R_j^{(t)}$ | 残差 $R^{(t)}$ 的第 $j$ 个 batch | $R_j^{(t)} \in \mathbb{R}^S$ | |
| $\tilde{\Delta}^{(t)}$ | TEE 二次压缩后的稀疏更新 | $\tilde{\Delta}^{(t)} \in \mathbb{R}^m$ | 未选中位置为 0 |
| $\mathcal{K}^{(t)}$ | TEE 二次压缩选中的 batch 索引集合 | $\mathcal{K}^{(t)} \subseteq \{0, \ldots, J-1\}$ | $|\mathcal{K}^{(t)}| = \lceil \kappa J \rceil$ |
| $\kappa$ | TEE 二次压缩保留比例 | $\kappa \in (0, 1]$ | 默认 $\kappa = 0.8$ |
| $\eta$ | 本地学习率 | $\eta > 0$ | |
| $\epsilon_j^{(t)}$ | batch $j$ 的掩码残差项 | $\epsilon_j^{(t)} \in \mathbb{R}^S$ | 待 TEE 补偿消除 |
| $C_j^{(t)}$ | TEE 对 batch $j$ 的补偿值 | $C_j^{(t)} \in \mathbb{R}^S$ | $C_j^{(t)} = \epsilon_j^{(t)}$ |
| $\mathcal{L}_i(\cdot)$ | 客户端 $i$ 的本地损失函数 | $\mathcal{L}_i: \mathbb{R}^m \to \mathbb{R}$ | |

---

## 2. 核心安全假设

**假设 1（KGC 可信）**：KGC 正确生成零和掩码并安全分发给各客户端与 TEE，自身不保留副本，不参与后续通信。

**假设 2（TEE 隔离性）**：TEE 内部内存与计算对外部 Host 完全隔离。TEE 持有 CKKS 私钥和掩码，Host 只能看到密文输入/输出。

**假设 3（CKKS IND-CPA）**：TenSEAL 的 CKKS 实现满足 IND-CPA 安全性，即密文不泄漏明文信息。

---

## 3. Phase 0：KGC 离线掩码生成

在联邦学习开始之前（$t = 0$），KGC 执行一次性的掩码生成与分发。

### 3.1 随机采样
对前 $n-1$ 个客户端，独立均匀采样：

$$
b_i \sim \mathcal{U}\bigl([-B, B]^m\bigr), \quad i = 1, 2, \ldots, n-1
$$

即每个分量 $b_i[k] \overset{\text{i.i.d.}}{\sim} \mathcal{U}([-B, B])$。

### 3.2 零和约束确定最后一个掩码
第 $n$ 个客户端的掩码由加权零和约束解析确定：

$$
\sum_{i=1}^{n} w_i b_i = 0 \quad \in \mathbb{R}^m
$$

解出 $b_n$：

$$
\boxed{b_n = -\frac{1}{w_n} \sum_{i=1}^{n-1} w_i b_i}
$$

### 3.3 验证
KGC 验证约束成立：

$$
\varepsilon_{\text{zero-sum}} = \Bigl\| \sum_{i=1}^{n} w_i b_i \Bigr\|_{\infty}
$$

要求 $\varepsilon_{\text{zero-sum}} \approx 0$（数值误差可忽略）。

### 3.4 按 batch 切分（与 CKKS 对齐）
对每个客户端 $i$，将 $b_i$ 切分为 $J$ 个 batch：

$$
b_{i,j} = \mathcal{B}_j(b_i) \in \mathbb{R}^S, \quad j = 0, 1, \ldots, J-1
$$

其中末尾 batch 不足 $S$ 维时补零。KGC 将 $\{(b_{i,0}, \ldots, b_{i,J-1})\}_{i=1}^n$ 分发给各客户端，同时将全部掩码集 $\{b_i\}_{i=1}^n$ 安全注入 TEE。

---

## 4. Phase 1：客户端本地训练

第 $t$ 轮，客户端 $i$ 从全局模型 $\theta^{(t)}$ 开始本地训练。

### 4.1 本地 SGD
执行 $E$ 个 epoch 的随机梯度下降：

$$
\theta_i^{(t)} = \theta^{(t)} - \eta \sum_{e=1}^{E} \nabla \mathcal{L}_i\bigl(\theta^{(t,e)}; \mathcal{B}_{i,e}\bigr)
$$

其中 $\mathcal{B}_{i,e}$ 为第 $e$ 个 epoch 的本地 mini-batch。

### 4.2 计算上传更新
本框架采用 `upload_difference = true`（上传差值），客户端计算：

$$
\boxed{g_i^{(t)} = \theta_i^{(t)} - \theta^{(t)} \in \mathbb{R}^m}
$$

$g_i^{(t)}$ 即为需要上传的本地梯度更新。

---

## 5. Phase 2：客户端掩码注入

客户端 $i$ 在加密前，将 KGC 分发的盲化掩码 $b_i$ 加到梯度更新上：

$$
\boxed{\tilde{g}_i^{(t)} = g_i^{(t)} + b_i \in \mathbb{R}^m}
$$

**关键性质**：
- 掩码注入在**明文域**完成（客户端本地）。
- 注入后的 $\tilde{g}_i^{(t)}$ 将代替原始 $g_i^{(t)}$ 进入后续加密与上传流程。
- 若第三方窃取了 $\tilde{g}_i^{(t)}$ 的密文，在 CKKS IND-CPA 假设下仍安全；即使 CKKS 被攻破，掩码 $b_i$ 提供信息论保护。

---

## 6. Phase 3：客户端稀疏化（TopK / RandK）

为减少上行通信量，客户端对 $\tilde{g}_i^{(t)}$ 执行包级稀疏化。

### 6.1 扁平化与 batch 切分
将 $\tilde{g}_i^{(t)}$ 按固定 batch_size $S$ 切分为 $J$ 个 batch：

$$
\tilde{g}_{i,j}^{(t)} = \mathcal{B}_j\bigl(\tilde{g}_i^{(t)}\bigr) \in \mathbb{R}^S, \quad j = 0, 1, \ldots, J-1
$$

### 6.2 稀疏化选择
根据策略生成上传掩码 $\mathcal{M}_i^{(t)} \in \{0, 1\}^J$：

- **TopK**：按 batch 内 $L_1$ 范数排序，保留前 $\lceil \rho J \rceil$ 个：
  $$
  \mathcal{M}_{i,j}^{(t)} = \mathbf{1}\Bigl[ j \in \text{TopK}\bigl(\{\|\tilde{g}_{i,j}^{(t)}\|_1\}_{j=0}^{J-1}, \rho\bigr) \Bigr]
  $$
- **RandK**：以轮次 $t$ 和种子为随机源，均匀随机保留 $\lceil \rho J \rceil$ 个：
  $$
  \mathcal{M}_{i,j}^{(t)} = \mathbf{1}\bigl[ j \in \text{RandK}(J, \rho, t, \text{seed}) \bigr]
  $$

其中 $\rho$ 为 `sparsity_rate`。

### 6.3 稀疏明文输出
客户端构造稀疏 batch 列表：

$$
u_{i,j}^{(t)} = \begin{cases}
\tilde{g}_{i,j}^{(t)} & \text{if } \mathcal{M}_{i,j}^{(t)} = 1 \\
0 & \text{if } \mathcal{M}_{i,j}^{(t)} = 0
\end{cases}
$$

**注意**：未选中的 batch 在本地被置零，不进入加密流程。

---

## 7. Phase 4：客户端 CKKS 加密上传

客户端对每个 $\nu_{i,j}^{(t)} \neq 0$ 的 batch 执行 CKKS 加密：

$$
\boxed{c_{i,j}^{(t)} = \text{Enc}_{\text{CKKS}}\bigl(\nu_{i,j}^{(t)}\bigr) \in \mathcal{C}, \quad \forall j \text{ s.t. } \mathcal{M}_{i,j}^{(t)} = 1}
$$

上传的稀疏密文包为：

$$
U_i^{(t)} = \left\{ c_{i,j}^{(t)} \;\middle|\; j \in \mathcal{J}_i^{(t)} \right\}, \quad \mathcal{J}_i^{(t)} = \bigl\{ j \mid \mathcal{M}_{i,j}^{(t)} = 1 \bigr\}
$$

同时上传元数据：$\{ \mathcal{M}_i^{(t)}, S, m, \text{shapes}, \text{offsets} \}$。

---

## 8. Phase 5：TEE 解密

TEE 接收客户端上传 $U_i^{(t)}$，使用私钥逐 batch 解密：

$$
\hat{u}_{i,j}^{(t)} = \text{Dec}_{\text{CKKS}}\bigl(c_{i,j}^{(t)}\bigr) = \nu_{i,j}^{(t)} = \tilde{g}_{i,j}^{(t)}, \quad \forall j \in \mathcal{J}_i^{(t)}
$$

对于 $j \notin \mathcal{J}_i^{(t)}$（客户端未上传的 batch），TEE 记为 $\text{None}$（或补零占位）。

**安全边界**：解密操作完全在 TEE 内部完成，Host 无法访问明文梯度。

---

## 9. Phase 6：TEE 明文聚合与掩码补偿

这是整个流程的**核心环节**，也是 `auto` 补偿模式的数学本质所在。

### 9.1 子集收集
对 batch $j$，定义第 $t$ 轮实际参与聚合的客户端子集：

$$
\boxed{S_j^{(t)} = \bigl\{ i \in [n] \;\big|\; \mathcal{M}_{i,j}^{(t)} = 1 \bigr\}}
$$

### 9.2 加权聚合（含掩码）
TEE 先执行标准的归一化加权平均：

$$
W_j^{(t)} = \sum_{i \in S_j^{(t)}} w_i
$$

$$
\delta_j^{(t), \text{raw}} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot \hat{u}_{i,j}^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot \tilde{g}_{i,j}^{(t)}
$$

### 9.3 展开掩码项
将 $\tilde{g}_{i,j}^{(t)} = g_{i,j}^{(t)} + b_{i,j}$ 代入：

$$
\delta_j^{(t), \text{raw}} = \underbrace{\sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot g_{i,j}^{(t)}}_{\text{目标聚合项 } \delta_j^{(t), \text{target}}} + \underbrace{\sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot b_{i,j}}_{\text{掩码残差项 } \epsilon_j^{(t)}}
$$

### 9.4 掩码残差分析
掩码残差为：

$$
\boxed{\epsilon_j^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot b_{i,j}}
$$

**关键观察**：
- **若 $S_j^{(t)} = [n]$（所有客户端都上传了 batch $j$）**：
  $$
  \epsilon_j^{(t)} = \frac{\sum_{i=1}^{n} w_i b_{i,j}}{\sum_{i=1}^{n} w_i} = \frac{0}{1} = 0
  $$
  由 KGC 的零和约束 $\sum_{i=1}^n w_i b_i = 0$，自然推出 batch 级别的零和 $\sum_{i=1}^n w_i b_{i,j} = 0$。此时**掩码自动抵消，无需补偿**。

- **若 $S_j^{(t)} \subsetneq [n]$（只有子集上传了 batch $j$，稀疏化场景）**：
  $$
  \epsilon_j^{(t)} = \frac{\sum_{i \in S_j^{(t)}} w_i b_{i,j}}{\sum_{i \in S_j^{(t)}} w_i} \neq 0 \quad \text{(一般情况)}
  $$
  子集不再满足零和约束，残差 $\epsilon_j^{(t)}$ 是一个非零随机向量。

### 9.5 TEE 显式补偿（去掩码）
TEE 持有全部掩码 $\{b_i\}_{i=1}^n$，计算补偿值：

$$
\boxed{C_j^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot b_{i,j} = \epsilon_j^{(t)}}
$$

从原始聚合结果中减去补偿：

$$
\boxed{\delta_j^{(t)} = \delta_j^{(t), \text{raw}} - C_j^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot g_{i,j}^{(t)}}
$$

**结论**：补偿后，batch $j$ 的聚合结果**完全消除了掩码影响**，仅保留干净的目标梯度聚合。

### 9.6 Auto 模式的判定逻辑
`auto` 模式的核心就是**自动检测上述两种情况**：

$$
\text{compensate}_j^{(t)} = \begin{cases}
\text{False} & \text{if } S_j^{(t)} = [n] \;\Leftrightarrow\; \text{NoSparsification} \\
\text{True}  & \text{if } S_j^{(t)} \subsetneq [n] \;\Leftrightarrow\; \text{TopK / RandK}
\end{cases}
$$

在本框架实现中，`auto` 直接根据 `sparsification.strategy` 判断：
- `strategy = "none"`：所有客户端上传全部 batch，$S_j^{(t)} = [n]$，跳过补偿计算。
- `strategy = "topk"` 或 `"randk"`：启用补偿计算。

---

## 10. Phase 7：TEE 全局残差累加（PTopK）

为补偿 TEE 二次压缩的信息损失，TEE 维护全局残差累加器 $R^{(t)} \in \mathbb{R}^m$。

### 10.1 残差加载
对 batch $j$，将上一轮残差加到当前聚合 delta 上：

$$
\hat{\delta}_j^{(t)} = \delta_j^{(t)} + R_j^{(t-1)}
$$

其中 $R_j^{(t-1)} = \mathcal{B}_j(R^{(t-1)})$。

### 10.2 初始化
首轮 $t = 0$ 时：

$$
R_j^{(-1)} = 0, \quad \forall j \in \{0, \ldots, J-1\}
$$

---

## 11. Phase 8：TEE 二次压缩（TopK）

TEE 对 $\hat{\delta}^{(t)}$ 执行包级 TopK 二次压缩，进一步减少下行通信量。

### 11.1 重要性评估
按 batch 的 $L_1$ 范数排序：

$$
\text{score}_j^{(t)} = \bigl\| \hat{\delta}_j^{(t)} \bigr\|_1, \quad j = 0, \ldots, J-1
$$

### 11.2 选中集合
保留前 $\lceil \kappa J \rceil$ 个 batch：

$$
\boxed{\mathcal{K}^{(t)} = \text{TopK}\bigl(\{\text{score}_j^{(t)}\}_{j=0}^{J-1}, \kappa\bigr)}
$$

### 11.3 更新全局残差
未选中的 batch 的误差累积到残差中：

$$
\boxed{R_j^{(t)} = \begin{cases}
0 & \text{if } j \in \mathcal{K}^{(t)} \\
\hat{\delta}_j^{(t)} & \text{if } j \notin \mathcal{K}^{(t)}
\end{cases}}
$$

### 11.4 稀疏输出
构造二次压缩后的稀疏更新：

$$
\tilde{\delta}_j^{(t)} = \begin{cases}
\hat{\delta}_j^{(t)} & \text{if } j \in \mathcal{K}^{(t)} \\
0 & \text{if } j \notin \mathcal{K}^{(t)}
\end{cases}
$$

---

## 12. Phase 9：全局模型更新

TEE 将选中的 batch delta 合并到旧全局模型上。

### 12.1 旧全局模型 batch 化
将旧全局模型 $\theta^{(t)}$ 按相同 batch 结构切分：

$$
\theta_j^{(t)} = \mathcal{B}_j(\theta^{(t)}) \in \mathbb{R}^S
$$

### 12.2 逐 batch 更新
对选中的 batch：

$$
\theta_j^{(t+1)} = \theta_j^{(t)} + \tilde{\delta}_j^{(t)}, \quad j \in \mathcal{K}^{(t)}
$$

对未选中的 batch：

$$
\theta_j^{(t+1)} = \theta_j^{(t)}, \quad j \notin \mathcal{K}^{(t)}
$$

### 12.3 拼接新全局模型
将所有 batch 拼接回完整模型：

$$
\boxed{\theta^{(t+1)} = \text{Concat}\bigl(\{\theta_j^{(t+1)}\}_{j=0}^{J-1}\bigr) \in \mathbb{R}^m}
$$

---

## 13. Phase 10：TEE 重加密与输出

TEE 将更新后的全局模型（或等价的 delta）重新加密，返回给 Host。

### 13.1 加密选中 batch
对 $j \in \mathcal{K}^{(t)}$：

$$
\boxed{\tilde{c}_j^{(t)} = \text{Enc}_{\text{CKKS}}\bigl(\tilde{\delta}_j^{(t)}\bigr) = \text{Enc}_{\text{CKKS}}\bigl(\theta_j^{(t+1)} - \theta_j^{(t)}\bigr)}
$$

### 13.2 输出密文包
TEE 输出稀疏密文 delta：

$$
\tilde{U}^{(t)} = \left\{ \tilde{c}_j^{(t)} \;\middle|\; j \in \mathcal{K}^{(t)} \right\}
$$

附带元数据：

$$
\text{Meta}^{(t)} = \left\{ \mathcal{M}^{(t)}, S, m, \text{shapes}, \text{offsets}, \kappa \right\}
$$

其中 $\mathcal{M}^{(t)} \in \{0, 1\}^J$ 为 TEE 二次压缩的掩码。

### 13.3 Host 侧处理
Host 将 $\tilde{U}^{(t)}$ 合并到旧全局密文状态，并作为预取 delta 广播给客户端。

---

## 14. 闭环正确性验证

**目标**：证明经过完整流程后，全局模型更新 $\theta^{(t+1)}$ 等价于**无掩码情况下的标准 FedAvg**（在稀疏化误差允许的范围内）。

### 14.1 无掩码基线（标准 FedAvg）
标准 FedAvg 在 batch $j$ 上的聚合为：

$$
\delta_j^{(t), \text{FedAvg}} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot g_{i,j}^{(t)}
$$

### 14.2 本框架的聚合结果
由 Phase 6 推导：

$$
\delta_j^{(t)} = \delta_j^{(t), \text{raw}} - C_j^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot g_{i,j}^{(t)} = \delta_j^{(t), \text{FedAvg}}
$$

### 14.3 误差来源对比
| 来源 | 本框架 | 标准 FedAvg + 稀疏化 |
|:---|:---|:---|
| 掩码引入的偏差 | **0**（精确抵消） | 不适用 |
| 客户端稀疏化误差 | 由客户端 PTopK 残差补偿 | 同左 |
| TEE 二次压缩误差 | 由 TEE 全局残差 $R^{(t)}$ 补偿 | 不适用（无 TEE） |
| CKKS 量化/精度损失 | ~$10^{-3}$（CKKS 固有） | 同左 |

**定理 1（掩码抵消正确性）**：在 `auto` 补偿模式下，无论稀疏化策略如何，TEE 补偿后的聚合结果满足：

$$
\forall t, \forall j \in \{0, \ldots, J-1\}: \quad \delta_j^{(t)} = \sum_{i \in S_j^{(t)}} \frac{w_i}{W_j^{(t)}} \cdot g_{i,j}^{(t)}
$$

即掩码 $b_i$ 被完全消除，不引入任何系统性偏差。

**证明**：由 Phase 6.3--6.5 的代数推导直接可得。$\square$

---

## 15. 隐私分析

### 15.1 对服务器的隐私
- **CKKS 加密**：客户端上传 $U_i^{(t)}$ 为密文，服务器（Host）在 IND-CPA 假设下无法获知 $g_i^{(t)}$ 或 $b_i$。
- **纵深防御**：即使 CKKS 被未来量子算法攻破，掩码 $b_i$ 提供额外的信息论屏障——攻击者看到的是 $g_i^{(t)} + b_i$，而 $b_i$ 是均匀随机的高维向量，与 $g_i^{(t)}$ 统计独立。

### 15.2 对客户端合谋的隐私
**场景**：$c$ 个客户端（$1 \leq c \leq n-1$）合谋，试图恢复目标客户端 $i^*$ 的梯度 $g_{i^*}^{(t)}$。

**分析**：
- 合谋方共享各自的 $(g_k^{(t)} + b_k)$ 和 $b_k$（因为合谋方知道自己的掩码）。
- 合谋方可以计算 $\sum_{k \in \text{collude}} w_k (g_k^{(t)} + b_k) - \sum_{k \in \text{collude}} w_k g_k^{(t)} = \sum_{k \in \text{collude}} w_k b_k$。
- 但目标客户端的 $b_{i^*}$ 与合谋方的 $b_k$ 之间没有线性关系（除了全局零和约束）。

**定理 2（合谋隐私）**：在 $< n-1$ 个客户端合谋的情况下，攻击者无法以优于随机猜测的概率恢复目标客户端的梯度 $g_{i^*}^{(t)}$。

**证明概要**：
全局零和约束提供 1 个线性方程：$\sum_{i=1}^n w_i b_i = 0$。
$c$ 个合谋方知道各自的 $b_k$，提供 $c$ 个已知量。
剩余的 $n - c - 1$ 个非目标、非合谋客户端的掩码未知。
当 $c < n - 1$ 时，目标掩码 $b_{i^*}$ 的自由度 $> 0$，方程组欠定。
$g_{i^*}^{(t)}$ 被 $b_{i^*}$ 一次一密式遮蔽，信息论安全。$\square$

**定理 3（$n-1$ 合谋下限）**：当 $n-1$ 个客户端合谋时，目标梯度可被精确恢复。

**证明**：$n-1$ 个合谋方已知 $\{b_k\}_{k \neq i^*}$，由零和约束：
$$b_{i^*} = -\frac{1}{w_{i^*}} \sum_{k \neq i^*} w_k b_k$$
进而 $g_{i^*}^{(t)} = (g_{i^*}^{(t)} + b_{i^*}) - b_{i^*}$。$\square$

---

## 16. Auto 补偿模式的判定逻辑

`auto` 模式是生产环境推荐配置，其判定规则与数学推导严格对应。

### 16.1 判定规则
```
if sparsification.strategy == "none":
    # 所有客户端上传全部 batch
    # S_j^{(t)} = [n], ∀j, ∀t
    # ε_j^{(t)} = 0（自动抵消）
    compensate = False
else:
    # TopK 或 RandK，子集聚合
    # S_j^{(t)} ⊆ [n]，一般 S_j^{(t)} ≠ [n]
    # ε_j^{(t)} ≠ 0（需显式补偿）
    compensate = True
```

### 16.2 等价数学表达

$$
\text{compensate}_j^{(t)} = \mathbf{1}\Bigl[ S_j^{(t)} \neq [n] \Bigr] = \mathbf{1}\Bigl[ \exists i \in [n]: \mathcal{M}_{i,j}^{(t)} = 0 \Bigr]
$$

### 16.3 模式对比

| 配置 | `compensation_mode` | 数学行为 | 收敛安全性 | 适用场景 |
|:---|:---|:---|:---|:---|
| NoSparsification + auto | 不补偿 | $\epsilon_j^{(t)} = 0$ | ✅ 安全 | 无稀疏化，掩码自动抵消 |
| TopK/RandK + auto | 补偿 | $\delta_j^{(t)} = \delta_j^{(t),\text{raw}} - C_j^{(t)}$ | ✅ 安全 | 稀疏化场景，精确去掩码 |
| 任意 + always | 补偿 | 同上 | ✅ 安全 | 保守策略，统一代码路径 |
| TopK/RandK + never | 不补偿 | $\delta_j^{(t)} = \delta_j^{(t),\text{raw}}$（含偏差） | ❌ **危险** | **禁止**：会引入系统性偏差 |

---

## 附录 A：完整流程时序图（公式版）

```
Round t
├─ Client i
│  ├─ Local Train:    θ_i^{(t)} = θ^{(t)} - η∇ℒ_i(θ^{(t)})
│  ├─ Compute delta:  g_i^{(t)} = θ_i^{(t)} - θ^{(t)}
│  ├─ Inject mask:    g̃_i^{(t)} = g_i^{(t)} + b_i
│  ├─ Sparsify:       ν_{i,j}^{(t)} = M_{i,j}^{(t)} · g̃_{i,j}^{(t)}
│  └─ Encrypt:        c_{i,j}^{(t)} = Enc(ν_{i,j}^{(t)})
│
├─ Upload → Host → TEE
│
├─ TEE
│  ├─ Decrypt:        û_{i,j}^{(t)} = Dec(c_{i,j}^{(t)}) = g̃_{i,j}^{(t)}
│  ├─ Aggregate:      δ_j^{(t),raw} = Σ_{i∈S_j^{(t)}} (w_i/W_j^{(t)}) · g̃_{i,j}^{(t)}
│  ├─ Compensate:     C_j^{(t)} = Σ_{i∈S_j^{(t)}} (w_i/W_j^{(t)}) · b_{i,j}
│  ├─ De-mask:        δ_j^{(t)} = δ_j^{(t),raw} - C_j^{(t)} = Σ (w_i/W_j^{(t)}) · g_{i,j}^{(t)}
│  ├─ Add residual:   δ̂_j^{(t)} = δ_j^{(t)} + R_j^{(t-1)}
│  ├─ TopK compress:  K^{(t)} = TopK({‖δ̂_j^{(t)}‖_1}, κ)
│  ├─ Update residual:R_j^{(t)} = δ̂_j^{(t)} · 1[j∉K^{(t)}]
│  ├─ Update model:   θ_j^{(t+1)} = θ_j^{(t)} + δ̂_j^{(t)} · 1[j∈K^{(t)}]
│  └─ Re-encrypt:     c̃_j^{(t)} = Enc(θ_j^{(t+1)} - θ_j^{(t)})
│
└─ Host
   ├─ Merge to global state
   └─ Broadcast c̃_j^{(t)} to clients (Prefetch)
```

---

## 附录 B：与 FedPHE 掩码方案的对比

| 特性 | 本框架（KGC 零和掩码） | FedPHE（PAMP 掩码） |
|:---|:---|:---|
| 掩码生成方 | KGC（离线） | 客户端两两协商 + Shamir 共享 |
| 零和约束 | $\sum w_i b_i = 0$（全局） | $m_i = s_i + \sum_j r_{ij}$，$r_{ij} = -r_{ji}$ |
| 抵消时机 | TEE 内实时 | 阈值解密后异步取消 |
| 合谋容忍 | $< n-1$ 客户端 | 取决于 Shamir 阈值 $t$ |
| 通信 overhead | 0（初始化分发） | $O(n^2)$ 两两协商 + 共享广播 |
| TEE 依赖 | 需要 TEE 做补偿 | 不需要 TEE |
| 稀疏化兼容 | **完全兼容**（auto 补偿） | 需额外适配 |
