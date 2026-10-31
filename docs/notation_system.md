# ECPFL 统一符号系统

> 为 `firset_paper.pdf` 设计的一套分层、无冲突、符合密码学惯例的 LaTeX 符号系统，解决原论文符号混用、定义不清、视觉冲突等问题。

---

## 一、设计理念

### 1.1 五层视觉编码

通过字体即可判断概念类别：

| 层级 | 字体 | LaTeX | 用途 |
|:---:|:---:|:---|:---|
| L1 | 花体 | `\mathcal{X}` | 集合：客户端集、索引集、轮次集 |
| L2 | 等线体 | `\mathsf{x}` | 密文：所有密文相关变量 |
| L3 | 粗体 | `\mathbf{x}` | 向量：模型、梯度、掩码 |
| L4 | 黑板粗体 | `\mathbb{X}` | 数域：环、域、模数空间 |
| L5 | 斜体 | `x` | 标量：参数、索引、噪声 |

### 1.2 状态标记约定

用固定修饰符表示数据状态，避免引入新符号：

| 修饰符 | LaTeX | 语义 |
|:---:|:---:|:---|
| 无 | — | 原始 / 本地 |
| 波浪 | `\tilde{x}` | 处理后 / 补偿后 |
| 横线 | `\bar{x}` | 聚合 / 平均 |
| 圆圈上标 | `x^{\circ}` | 零值 / 补偿 |
| pre 下标 | `x_{\text{pre}}` | 预取 / 累积 |

### 1.3 位置约定

| 位置 | 约定 | 示例 |
|:---:|:---|:---|
| 上标 | 轮次 `(t)` | `\mathbf{g}_i^{(t)}` |
| 下标 | 客户端 `i` / pack `j` | `\mathsf{c}_{i,j}^{(t)}` |
| 双下标 | `客户端, pack` | `\mathbf{g}_{i,j}^{(t)}` |

---

## 二、系统与算法参数

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $n$ | `n` | 客户端总数 |
| $T$ | `T` | 总训练轮次 |
| $t$ | `t` | 当前轮次（所有时变量上标） |
| $\rho$ | `\rho` | 客户端采样率，$\rho = \|\mathcal{S}_t\| / n$ |
| $d$ | `d` | 模型总参数量 |
| $\eta$ | `\eta` | 全局学习率 |
| $E$ | `E` | 本地训练 epoch 数 |
| $P$ | `P` | 梯度 pack 总数，$P = \lceil d / B \rceil$ |
| $B$ | `B` | 每 pack 参数数（pack size） |
| $k$ | `k` | VPTopK 保留的 pack 数量 |
| $\tau$ | `\tau` | 全局掩码投票阈值，$\tau \in (0, 1]$ |
| $R$ | `R` | 预取窗口大小（Prefetch horizon） |

**关键说明**：
- `P` 与 `p`（明文模数）大小写区分，不会冲突
- `B` 仅表示 pack 内参数数，不再表示 PRG 种子或 batch 数

---

## 三、集合

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\mathcal{C}$ | `\mathcal{C}` | 所有客户端集合 $\{C_1, \dots, C_n\}$ |
| $\mathcal{S}_t$ | `\mathcal{S}_t` | 第 $t$ 轮采样的客户端集合 |
| $\bar{\mathcal{S}}_t$ | `\bar{\mathcal{S}}_t` | 第 $t$ 轮未采样的客户端集合 |
| $\mathcal{P}$ | `\mathcal{P}` | Pack 索引集合 $\{1, \dots, P\}$ |
| $\mathcal{T}_i^{(t)}$ | `\mathcal{T}_i^{(t)}` | 客户端 $i$ 本地 Top-$k$ pack 索引集 |
| $\mathcal{K}^{(t)}$ | `\mathcal{K}^{(t)}` | 全局共识 pack 索引集（服务器广播） |

**关键说明**：
- 所有集合统一用 `\mathcal` 花体
- `\mathcal{K}^{(t)}`（K = Key pack set）与 `\mathcal{T}_i^{(t)}`（T = Top-k set）区分

---

## 四、密码学基础

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\mathbb{Z}_q$ | `\mathbb{Z}_q` | 模 $q$ 整数环 |
| $R$ | `R` | 分圆多项式环 $\mathbb{Z}[X]/(X^n+1)$ |
| $R_q$ | `R_q` | 模 $q$ 分圆环 $R/qR$ |
| $n$ | `n` | RLWE 维度（多项式次数，如 8192） |
| $q$ | `q` | 密文模数 |
| $p$ | `p` | 明文模数 |
| $\chi_{\text{key}}$ | `\chi_{\text{key}}` | 密钥采样分布（如三元分布） |
| $\chi_{\text{err}}$ | `\chi_{\text{err}}` | 误差采样分布（如高斯分布） |
| $\sigma$ | `\sigma` | PRG 秘密种子（原论文 $B$） |
| $s_i$ | `s_i` | 客户端 $i$ 的私钥份额 |
| $S$ | `S` | 全局虚拟密钥 $S = \sum_{i=1}^n s_i$ |
| $a^{(t)}$ | `a^{(t)}` | 第 $t$ 轮公共多项式 |
| $\tilde{p}$ | `\tilde{p}` | 常数明文模数多项式 |
| $\text{PRPG}$ | `\text{PRPG}` | 伪随机多项式生成器 |
| $\text{Enc}$ | `\text{Enc}` | 加密算法 |
| $\text{Dec}$ | `\text{Dec}` | 解密算法 |
| $\text{Eval}$ | `\text{Eval}` | 同态求和评估 |

**关键说明**：
- PRG 种子由 `B` 改为 `\sigma`：密码学中 `\sigma` 表种子更自然，避免与 pack size `B` 冲突
- 全局密钥用大写 `S`：与客户端份额 `s_i` 形成大小写对应，直观表达「和」的关系

---

## 五、模型与梯度

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\mathbf{w}^{(t)}$ | `\mathbf{w}^{(t)}` | 第 $t$ 轮全局模型 |
| $\mathbf{w}_i^{(t)}$ | `\mathbf{w}_i^{(t)}` | 客户端 $i$ 本地模型 |
| $\mathbf{g}_i^{(t)}$ | `\mathbf{g}_i^{(t)}` | 客户端 $i$ 本地梯度 |
| $\tilde{\mathbf{g}}_i^{(t)}$ | `\tilde{\mathbf{g}}_i^{(t)}` | 残差补偿后梯度 |
| $\mathbf{r}_i^{(t)}$ | `\mathbf{r}_i^{(t)}` | 客户端 $i$ 残差缓存 |
| $\bar{\mathbf{g}}^{(t)}$ | `\bar{\mathbf{g}}^{(t)}` | 聚合梯度（FedAvg 加权） |
| $\mathbf{g}_{i,j}^{(t)}$ | `\mathbf{g}_{i,j}^{(t)}` | 客户端 $i$ 的 pack $j$（$B$ 维向量） |
| $s_{i,j}^{(t)}$ | `s_{i,j}^{(t)}` | pack $j$ 的重要性分数 $s_{i,j}^{(t)} = \|\mathbf{g}_{i,j}^{(t)}\|_2^2$ |

**关键说明**：
- 所有梯度/模型均为粗体，与标量参数严格区分
- `s_{i,j}^{(t)}` 用小写斜体，因为它是标量分数（L2-norm），不是向量

---

## 六、掩码

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\mathbf{m}_i^{(t)}$ | `\mathbf{m}_i^{(t)}` | 客户端 $i$ 本地投票掩码，$\mathbf{m}_i^{(t)} \in \{0,1\}^P$ |
| $\mathbf{M}^{(t)}$ | `\mathbf{M}^{(t)}` | 全局共识掩码，$\mathbf{M}^{(t)} \in \{0,1\}^P$ |
| $\mathbf{m}_i^{(t)}[j]$ | `\mathbf{m}_i^{(t)}[j]` | 掩码第 $j$ 个分量 |

**关键说明**：
- 掩码是 $P$ 维 0-1 向量，所以用粗体
- `\mathbf{m}_i`（小写 m）= 本地掩码，`\mathbf{M}`（大写 M）= 全局掩码

---

## 七、密文

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\mathsf{c}_{i,j}^{(t)}$ | `\mathsf{c}_{i,j}^{(t)}` | 客户端 $i$ 的 pack $j$ 密文 |
| $\mathsf{c}_{k,j}^{(t),\circ}$ | `\mathsf{c}_{k,j}^{(t),\circ}` | 客户端 $k$ 的零补偿密文（$k \notin \mathcal{S}_t$） |
| $\mathsf{C}_j^{(t)}$ | `\mathsf{C}_j^{(t)}` | pack $j$ 的聚合密文 |
| $\boldsymbol{\delta}_j^{(t)}$ | `\boldsymbol{\delta}_j^{(t)}` | pack $j$ 的 Delta 密文 |
| $\mathsf{C}_{\text{pre},j}^{(t)}$ | `\mathsf{C}_{\text{pre},j}^{(t)}` | 预取累加密文（客户端本地维护） |
| $\mathsf{C}_{\text{fetch},j}$ | `\mathsf{C}_{\text{fetch},j}` | 客户端 Fetch 阶段下载的密文 |

**关键说明**：
- 密文全部用 `\mathsf` 等线体，与明文变量形成视觉隔离
- 单密文用小写 `\mathsf{c}`，聚合密文用大写 `\mathsf{C}`
- 零补偿密文用上标 `\circ`，简洁且不占下标空间
- Delta 密文用 `\boldsymbol{\delta}`（粗体 δ），保留希腊字母传统，同时加粗表示密文向量

---

## 八、验证与承诺

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $H$ | `H` | 密码学哈希函数（如 SHA-256） |
| $\text{com}_{i,j}^{(t)}$ | `\text{com}_{i,j}^{(t)}` | 客户端 $i$ 对 pack $j$ 的承诺 |
| $\text{Com}_j^{(t)}$ | `\text{Com}_j^{(t)}` | pack $j$ 的聚合承诺 |
| $\Sigma^{(t)}$ | `\Sigma^{(t)}` | 第 $t$ 轮阈值签名 |
| $\text{PK}$ | `\text{PK}` | KGC 公钥 |
| $\text{VK}$ | `\text{VK}` | 验证公钥 |

**关键说明**：
- `com` 和 `Com` 用 `\text` 罗马体，表示它们是算法输出而非数学变量
- `\Sigma^{(t)}` 用大写希腊字母表示签名，与加密密文 `\mathsf` 字体区分

---

## 九、噪声分析

| 符号 | LaTeX | 含义 |
|:---:|:---|:---|
| $\nu_{\text{enc}}$ | `\nu_{\text{enc}}` | 单轮加密噪声 |
| $\nu_{\text{agg}}$ | `\nu_{\text{agg}}` | 聚合噪声 |
| $\nu_{\delta}$ | `\nu_{\delta}` | Delta 计算噪声 |
| $\nu_{\text{pre}}$ | `\nu_{\text{pre}}` | 预取累积噪声 |
| $\nu_{\text{dec}}$ | `\nu_{\text{dec}}` | 解密后残余噪声 |
| $B_{\nu}$ | `B_{\nu}` | 噪声上界（bound） |
| $B_{\text{err}}$ | `B_{\text{err}}` | 误差多项式上界 |

**关键说明**：
- 噪声统一用 `\nu`（nu），下标区分来源
- `B_{\nu}` 表示 Bound on nu，命名直观

---

## 十、核心公式重写

### 10.1 ESAFL 加密

```latex
\mathsf{c}_{i,j}^{(t)} = \left[ a^{(t)} \cdot s_i + \tilde{p} \cdot e_{i,j}^{(t)} + \text{Encode}\bigl(\mathbf{g}_{i,j}^{(t)}\bigr) \right]_q \in R_q
```

**改进**：`\mathsf{c}` 一眼识别为密文；`\text{Encode}` 显式标注编码步骤，避免小写 `p` 与明文模数 `p` 冲突。

---

### 10.2 聚合密文

```latex
\mathsf{C}_j^{(t)} = \sum_{i \in \mathcal{S}_t} \alpha_i \cdot \mathsf{c}_{i,j}^{(t)} + \sum_{k \in \bar{\mathcal{S}}_t} \mathsf{c}_{k,j}^{(t),\circ} \quad \in R_q
```

其中权重 $\alpha_i = |D_i| / \sum_{j \in \mathcal{S}_t} |D_j|$。

**改进**：`\mathcal{S}_t` / `\bar{\mathcal{S}}_t` 视觉清晰；`\circ` 上标简洁表示 compensation；显式引入 FedAvg 权重 `\alpha_i`。

---

### 10.3 Delta 密文

```latex
\boldsymbol{\delta}_j^{(t)} = \mathsf{C}_j^{(t)} \ominus \mathsf{C}_j^{(t-1)} = \mathsf{C}_j^{(t)} + (-1) \otimes \mathsf{C}_j^{(t-1)} \quad \in R_q
```

**改进**：`\ominus` 表示同态减法（与明文减法 `-` 区分）；`\boldsymbol{\delta}` 粗体 δ 表示密文域的 delta。

---

### 10.4 预取累加

```latex
\mathsf{C}_{\text{pre},j}^{(t)} = \bigoplus_{r=0}^{R-1} \boldsymbol{\delta}_j^{(t+r)} = \left[ \sum_{r=0}^{R-1} \boldsymbol{\delta}_j^{(t+r)} \right]_q \quad \in R_q
```

**改进**：`\mathsf{C}_{\text{pre}}` 下标 "pre" 直观；`\bigoplus` 强调同态性质。

---

### 10.5 残差补偿与掩码更新

```latex
\tilde{\mathbf{g}}_i^{(t)} = \mathbf{g}_i^{(t)} + \mathbf{r}_i^{(t-1)}
```

```latex
\mathbf{m}_i^{(t)}[j] = \begin{cases} 1 & \text{if } j \in \mathcal{T}_i^{(t)} \\ 0 & \text{otherwise} \end{cases}
```

```latex
\mathbf{r}_i^{(t)} = \tilde{\mathbf{g}}_i^{(t)} \odot \bigl( \mathbf{1} - \mathbf{M}^{(t)} \bigr)
```

**改进**：`\tilde{\mathbf{g}}` 波浪 + 粗体 = 补偿后梯度向量；`\odot` 表示逐元素乘法（Hadamard product）。

---

## 十一、LaTeX 导言区配置

将以下内容加入论文导言区即可使用本符号系统：

```latex
%% ============================================================
%% ECPFL Unified Notation System
%% ============================================================

% 基础数学包
\usepackage{amsmath, amssymb, amsthm, amsfonts}
\usepackage{bm}

% 同态运算符
\newcommand{\homadd}{\oplus}
\newcommand{\homsub}{\ominus}
\newcommand{\hommul}{\otimes}
\newcommand{\homsum}{\bigoplus}

% 零补偿密文上标
\newcommand{\comp}{\circ}

% 常用集合
\newcommand{\Clients}{\mathcal{C}}
\newcommand{\Sampled}{\mathcal{S}}
\newcommand{\Unsampled}{\bar{\mathcal{S}}}
\newcommand{\Packs}{\mathcal{P}}
\newcommand{\TopK}{\mathcal{T}}
\newcommand{\Consensus}{\mathcal{K}}

% 噪声符号
\newcommand{\noise}[1]{\nu_{\text{#1}}}
\newcommand{\noisebound}{B_{\nu}}

% 算法宏
\newcommand{\Enc}{\text{Enc}}
\newcommand{\Dec}{\text{Dec}}
\newcommand{\Eval}{\text{Eval}}
\newcommand{\PRPG}{\text{PRPG}}
\newcommand{\KeyGen}{\text{KeyGen}}
\newcommand{\Com}{\text{Com}}
\newcommand{\com}{\text{com}}
```

---

## 十二、迁移对照表

| 概念 | 原论文 | 新系统 | 迁移理由 |
|:---|:---|:---|:---|
| PRG 种子 | `B` | `σ` | 避免与 pack size `B` 冲突 |
| 客户端集合 | `S(t)`, `S_t`, `S_active` | `\mathcal{S}_t` | 统一为花体集合符号 |
| 未采样集合 | `D(t)` | `\bar{\mathcal{S}}_t` | 上划线表补集，数学惯例 |
| Pack 总数 | `J`, `P` 混用 | `P` | 统一为 `P`，首字母联想 |
| 单密文 | `c`, `ct`, `ct_{i,j}` | `\mathsf{c}_{i,j}^{(t)}` | 等线体视觉隔离密文域 |
| 聚合密文 | `C`, `C_j^{(t)}` | `\mathsf{C}_j^{(t)}` | 等线体大写 |
| 预取密文 | `C_{pre}`, `C_{p(r)e}` | `\mathsf{C}_{\text{pre},j}^{(t)}` | 下标 `\text{pre}` 直观 |
| 零补偿密文 | `ct^{(comp)}` | `\mathsf{c}^{\circ}` | `\circ` 上标简洁不占下标 |
| Delta 密文 | `\delta`（斜体） | `\boldsymbol{\delta}` | 粗体表示密文向量 |
| 本地梯度 | `g_i^{(t)}` | `\mathbf{g}_i^{(t)}` | 粗体表向量 |
| 补偿梯度 | `\tilde{g}_i^{(t)}` | `\tilde{\mathbf{g}}_i^{(t)}` | 粗体 + 波浪 |
| 聚合梯度 | `G`（大写） | `\bar{\mathbf{g}}^{(t)}` | 横线表聚合 |
| 本地掩码 | `m_i^{(t)}` | `\mathbf{m}_i^{(t)}` | 粗体 0-1 向量 |
| 全局掩码 | `M^{(t)}`, `K^{(t)}` | `\mathbf{M}^{(t)}` | 大写 M 表全局，粗体向量 |
| 投票阈值 | `\tau`（未使用） | `\tau` | 新引入，与正文描述一致 |
| 噪声 | `E`, `e`, `\tilde{E}` | `\nu_{\text{enc}}`, `\nu_{\text{agg}}` | 统一 `\nu` + 下标 |
| Hash | `H`, `h`, `H_{pre}` | `H`, `\text{Com}` | 聚合承诺用 `\text` 罗马体 |
| 轮次 | `t`, `r` 混用 | `t` | 全部统一 |

---

## 十三、设计原则总结

| 原则 | 实现方式 | 效果 |
|:---|:---|:---|
| **视觉分层** | 花体(集合) / 等线(密文) / 粗体(向量) / 黑板(数域) | 读者一眼判断概念类别 |
| **状态固定** | `\tilde`=处理后 / `\bar`=聚合 / `\circ`=零补偿 / `\text{pre}`=预取 | 避免引入新字母 |
| **位置约定** | 上标=轮次 / 下标=客户端+pack | 减少记忆负担 |
| **无冲突** | 种子`\sigma`≠pack size `B` / 集合`\mathcal{S}`≠密钥`S` | 彻底消除歧义 |
| **符合惯例** | `\chi`表分布 / `\nu`表噪声 / `\oplus`表同态加 | 密码学审稿人熟悉 |

---

*符号系统设计：Kimi Code CLI*  
*对应论文：firset_paper.pdf (ECPFL)*  
*配套文档：docs/firset_paper_issues_ch1-5.md, docs/firset_paper_revision_guide.md*
