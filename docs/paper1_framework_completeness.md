# 第一篇（完整版）：Threshold-CipherFetch
# A Complete Framework for Privacy-Preserving Federated Learning with Ciphertext Prefetching

> 本文档为第一篇论文的完整方案设计，包含完整的公式闭环推导、实体交互流程、知识边界定义、解密与训练流程。

---

## 目录

1. [引言与问题定义](#一引言与问题定义)
2. [系统架构与实体知识边界](#二系统架构与实体知识边界)
3. [数学基础与符号体系](#三数学基础与符号体系)
4. [完整公式闭环](#四完整公式闭环)
   - 4.1 初始化阶段：阈值密钥生成
   - 4.2 加密阶段：客户端本地加密
   - 4.3 上传阶段：密文传输
   - 4.4 聚合阶段：服务器同态聚合
   - 4.5 Delta生成阶段：密文差分
   - 4.6 预取阶段：密文广播与客户端累加
   - 4.7 解密阶段：阈值部分解密与组合
   - 4.8 训练阶段：明文恢复与模型更新
5. [实体交互协议](#五实体交互协议)
6. [威胁模型与安全分析](#六威胁模型与安全分析)
7. [正确性证明](#七正确性证明)
8. [复杂度分析](#八复杂度分析)

---

## 一、引言与问题定义

### 1.1 现有方案的完备性缺陷

现有CKKS-FL方案（包括我们的CipherFetch初版）存在以下完备性缺陷：

| 缺陷编号 | 缺陷描述 | 影响 | 本文解决方案 |
|----------|---------|------|-------------|
| F-1 | **密钥集中管理**：单密钥由服务器生成并持有私钥 | 服务器可解密任意密文，完全破坏隐私 | 阈值密钥生成，服务器不持私钥 |
| F-2 | **解密权限集中**：缺乏分布式解密机制 | 单点故障/泄露即全局崩溃 | t-out-of-n部分解密 |
| F-3 | **实体边界模糊**：缺乏清晰的角色定义和知识边界 | 无法形式化安全证明 | 五实体精确定义 |
| F-4 | **交互流程断裂**：从加密到解密缺乏完整公式链 | 无法验证协议正确性 | 完整八阶段公式闭环 |
| F-5 | **掉线处理缺失**：客户端掉线后无恢复机制 | 系统鲁棒性差 | 仅需t个节点在线 |
| F-6 | **预取安全空白**：密文delta的完整性无验证 | 服务器可定向投毒 | 阈值见证签名(TPW) |

### 1.2 本文贡献

**贡献1**：提出Threshold-CipherFetch框架，首次将**阈值CKKS**、**密文预取**、**包级稀疏化**、**阈值见证认证**完整集成。

**贡献2**：建立从**阈值密钥生成→加密→聚合→Delta生成→预取→部分解密→明文恢复→模型更新**的完整公式闭环。

**贡献3**：精确定义五实体的**知识边界**（Knows/Doesn't Know），使安全证明可形式化。

**贡献4**：设计基于BLS阈值签名的预取证认证机制(TPW)，解决密文预取中的完整性问题。

---

## 二、系统架构与实体知识边界

### 2.1 五实体定义

| 实体 | 符号 | 功能定位 | 信任假设 |
|------|------|---------|---------|
| **密钥生成中心** | KGC | 一次性执行阈值密钥生成，之后离线 | 初始化阶段半诚实，之后永久离线 |
| **聚合服务器** | AS | 执行同态聚合、预取调度、Delta广播 | **不可信（可恶意）** |
| **客户端** | $C_i, i \in [n]$ | 本地训练、加密上传、接收预取、阈值解密 | 半诚实 |
| **辅助节点** | $AN_j, j \in [m]$ | 协助阈值解密（持有私钥份额） | 半诚实，≤ t-1个可共谋 |
| **见证节点** | $WN_k, k \in [w]$ | 验证Delta正确性并签名 | 半诚实，≤ t_w-1个可共谋 |

### 2.2 知识边界（Knowledge Boundary）

这是本文的核心设计之一——**明确每个实体知道什么、不知道什么**。

#### 2.2.1 密钥生成中心 KGC

```
KGC.KNOWS = {
    初始化阶段临时知道：
    - 所有私钥份额 {sk_i}_{i∈[n]}
    - 完整私钥 s_agg = Σ sk_i
    - 聚合公钥 pk_agg
    
    生成密钥后：
    - 销毁所有密钥材料
    - 永久离线
}

KGC.DOESNT_KNOW = {
    - 任何训练数据
    - 任何模型参数
    - 任何密文内容
}
```

#### 2.2.2 聚合服务器 AS

```
AS.KNOWS = {
    - 聚合公钥 pk_agg = (b_agg, a_agg)
    - 评估密钥 evk
    - 所有密文更新 {ct_i}  
    - 所有密文Delta {δ^(t)}
    - 客户端的掩码模式 {mask_i}（若使用稀疏化）
    - 通信元数据（谁上传了、何时上传）
}

AS.DOESNT_KNOW = {  ★★★ 关键安全边界 ★★★
    - 任何私钥份额 sk_i
    - 完整私钥 s_agg
    - 任何明文梯度 Δw_i
    - 任何明文模型参数 w
    - 任何解密后的内容
    
    结论：AS 看到的一切都是密文，无法解密任何信息
}
```

#### 2.2.3 客户端 $C_i$

```
C_i.KNOWS = {
    - 自己的私钥份额 sk_i
    - 聚合公钥 pk_agg
    - 自己的本地数据 D_i
    - 自己的本地模型参数
    - 接收到的密文Delta δ^(t)
    - 见证公钥 vk_WN（用于验证签名）
    - 预取缓存 ct_prefetch
}

C_i.DOESNT_KNOW = {
    - 其他客户端的私钥份额 sk_j (j≠i)
    - 完整私钥 s_agg
    - 其他客户端的本地数据 D_j (j≠i)
    - 其他客户端的明文梯度 Δw_j
    - 全局明文模型（除非通过阈值解密恢复）
}
```

#### 2.2.4 辅助节点 $AN_j$

```
AN_j.KNOWS = {
    - 自己的私钥份额 sk_j
    - 聚合公钥 pk_agg
    - 接收到的密文（用于部分解密）
}

AN_j.DOESNT_KNOW = {
    - 其他节点的私钥份额
    - 完整私钥 s_agg
    - 解密后的明文（除非t个节点联合）
}
```

#### 2.2.5 见证节点 $WN_k$

```
WN_k.KNOWS = {
    - 自己的签名私钥份额 sk_WN_k
    - 接收到的Delta哈希（用于签名）
}

WN_k.DOESNT_KNOW = {
    - 任何私钥份额 sk_i
    - 任何明文内容
    - 完整签名私钥
}
```

### 2.3 知识边界图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         知识边界可视化                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  KGC: 初始化时知道所有密钥 → 生成后立即销毁 → 永久离线                    │
│       [sk_1, sk_2, ..., sk_n, s_agg] → ∅                                │
│                                                                          │
│  AS: 仅知道密文和公钥                                                     │
│       [pk_agg, evk, {ct_i}, {δ^(t)}]                                    │
│       不知道: [任何 sk, 任何明文]                                         │
│                                                                          │
│  C_i: 知道自己的份额和本地数据                                            │
│       [sk_i, D_i, w_i, ct_prefetch]                                     │
│       不知道: [sk_j(j≠i), s_agg, D_j, Δw_j]                             │
│                                                                          │
│  AN_j: 知道自己的份额                                                   │
│       [sk_j]                                                            │
│       不知道: [sk_k(k≠j), s_agg, 明文]                                   │
│                                                                          │
│  WN_k: 知道自己的签名份额                                               │
│       [sk_WN_k]                                                         │
│       不知道: [sk_WN_l(l≠k), 完整签名密钥, 任何明文]                     │
│                                                                          │
│  ★ 关键安全性质：没有任何单一实体知道完整私钥 s_agg ★                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、数学基础与符号体系

### 3.1 基础定义

**定义3.1（分圆多项式环）**：
设 $N = 2^k$，分圆多项式 $\Phi_{2N}(X) = X^N + 1$。定义：
$$R = \mathbb{Z}[X]/(X^N + 1), \quad R_q = R/qR$$

**定义3.2（RLWE分布）**：
对于安全参数 $\lambda$，采样 $a \leftarrow U(R_q)$, $s \leftarrow \chi_{key}$, $e \leftarrow \chi_{err}$，RLWE样本为：
$$(a, b = a \cdot s + e \mod q)$$

**决策性RLWE假设**：区分RLWE样本与均匀随机样本 $(a, u)$ 是困难的。

**定义3.3（离散高斯分布）**：
$$D_{R,\sigma}(x) \propto \exp(-\pi \|x\|^2 / \sigma^2)$$

### 3.2 符号表

| 符号 | 含义 | 典型值 |
|------|------|--------|
| $N$ | 环维度 | 4096, 8192, 16384 |
| $L$ | 乘法深度 | 3-10 |
| $q_0 < q_1 < ... < q_L$ | 模数链 | $q_i = p_i \cdot q_{i-1}$ |
| $\Delta = 2^p$ | 缩放因子 | $2^{20}$ ~ $2^{40}$ |
| $\chi_{key}$ | 密钥分布 | HWT(h)，汉明重量h |
| $\chi_{err}$ | 误差分布 | $D_{R,\sigma}$，$\sigma \approx 3.2$ |
| $\chi_{enc}$ | 加密随机性 | $D_{R,\sigma}$ |
| $n$ | 客户端数量 | 10-1000 |
| $t$ | 阈值（部分解密所需最少节点） | $t \leq n/2$ |
| $s$ | 稀疏率 | 0.1-0.5 |
| $\|e\|_{can}$ | 规范嵌入范数 | — |

### 3.3 实体状态符号

| 符号 | 含义 |
|------|------|
| $w^{(t)}$ | 第t轮全局模型 |
| $w_i^{(t)}$ | 客户端i第t轮本地模型 |
| $\Delta w_i^{(t)} = w_i^{(t)} - w^{(t-1)}$ | 客户端i第t轮梯度更新 |
| $ct_i^{(t)}$ | 客户端i第t轮加密更新 |
| $ct_{agg}^{(t)}$ | 第t轮聚合密文 |
| $\delta^{(t)} = ct_{agg}^{(t)} - ct_{agg}^{(t-1)}$ | 第t轮密文Delta |
| $ct_{prefetch,i}^{(t)}$ | 客户端i第t轮预取缓存 |
| $r_i^{(t)}$ | 客户端i第t轮残差缓存（SRCA） |

---

## 四、完整公式闭环

> 本文的核心创新：建立从密钥生成到模型更新的完整八阶段公式链。

### 阶段一：初始化 —— 阈值密钥生成

**输入**：安全参数 $\lambda$，参与者数 $n$，阈值 $t$
**输出**：$pk_{agg}$，$evk$，$\{sk_i\}_{i \in [n]}$

#### 步骤1.1：分布式密钥生成

每个参与者 $i \in [n]$（客户端或辅助节点）独立采样：

$$
\begin{aligned}
s_i &\leftarrow \chi_{key} \quad &&\text{// 私钥份额} \\
a_i &\leftarrow U(R_{q_L}) \quad &&\text{// 公钥分量} \\
e_i &\leftarrow \chi_{err} \quad &&\text{// 误差}
\end{aligned}
$$

计算本地公钥分量：
$$b_i = -a_i \cdot s_i + e_i \pmod{q_L}$$

#### 步骤1.2：聚合公钥构造

所有参与者广播 $(a_i, b_i)$，共同计算：

$$
\begin{aligned}
a_{agg} &= \sum_{i=1}^n a_i \pmod{q_L} \\
b_{agg} &= \sum_{i=1}^n b_i = \sum_{i=1}^n (-a_i s_i + e_i) \pmod{q_L}
\end{aligned}
$$

**关键公式（聚合公钥结构）**：

$$
\boxed{b_{agg} = -a_{agg} \cdot s_{agg} + e_{agg} + \sum_{i \neq j} a_i s_j}
$$

其中：
- $s_{agg} = \sum_{i=1}^n s_i$ 为**完整私钥（无单一实体知道）**
- $e_{agg} = \sum_{i=1}^n e_i$ 为聚合误差

**简化构造**（实际采用）：
为简化，令所有 $a_i = a$（统一随机源），则：

$$
\begin{aligned}
a_{agg} &= a \\
b_{agg} &= -a \cdot s_{agg} + e_{agg}
\end{aligned}
$$

聚合公钥：
$$\boxed{pk_{agg} = (b_{agg}, a_{agg}) = (-a \cdot s_{agg} + e_{agg}, \; a)}$$

#### 步骤1.3：评估密钥生成

通过联合协议生成重线性化密钥：
$$evk = \text{JointSwitchKeyGen}(\{s_i^2\}_{i=1}^n, \{s_i\}_{i=1}^n)$$

具体地，每个参与者 $i$ 贡献：
$$evk_i = \text{SwitchKeyGen}_i(s_i^2, s_i)$$

组合为全局评估密钥：
$$evk = \sum_{i=1}^n evk_i$$

#### 步骤1.4：私钥份额分发

KGC通过安全通道分发：
- 向客户端 $C_i$ 发送 $sk_i = s_i$
- 向辅助节点 $AN_j$ 发送 $sk_j = s_j$（若采用辅助节点托管模式）

#### 步骤1.5：KGC离线

KGC销毁所有中间状态：
$$\text{KGC.Shred}(s_{agg}, \{s_i\}, a, \{e_i\})$$

**阶段一结束后的知识状态**：
- AS知道：$pk_{agg}$，$evk$
- $C_i$知道：$sk_i$，$pk_{agg}$，$evk$
- 没有任何实体知道 $s_{agg}$

---

### 阶段二：加密 —— 客户端本地加密

**输入**：客户端梯度 $\Delta w_i^{(t)} \in \mathbb{R}^d$，聚合公钥 $pk_{agg} = (b_{agg}, a)$
**输出**：密文 $ct_i^{(t)} = (c_{i,0}, c_{i,1})$

#### 步骤2.1：消息编码

将梯度向量编码为CKKS明文多项式：

$$
\begin{aligned}
m_i &= \text{CKKS.Encode}(\Delta w_i, \Delta) \\
&= \left\lfloor \Delta \cdot \sigma^{-1}(\pi^{-1}(\Delta w_i)) \right\rceil \in R_{q_L}
\end{aligned}
$$

#### 步骤2.2：CKKS加密（使用聚合公钥）

采样加密随机性：
$$v \leftarrow \chi_{enc}, \quad e_0, e_1 \leftarrow \chi_{err}$$

计算密文：

$$
\begin{aligned}
c_{i,0} &= b_{agg} \cdot v + e_0 + m_i \pmod{q_L} \\
c_{i,1} &= a \cdot v + e_1 \pmod{q_L}
\end{aligned}
$$

**核心加密公式**：

$$
\boxed{ct_i = (c_{i,0}, c_{i,1}) = (\underbrace{b_{agg}v + e_0 + m_i}_{c_{i,0}}, \; \underbrace{av + e_1}_{c_{i,1}})}$$

#### 步骤2.3：加密正确性验证

解密结构（仅用于验证，实际由t个节点联合完成）：

$$
\begin{aligned}
c_{i,0} + c_{i,1} \cdot s_{agg} &= (b_{agg}v + e_0 + m_i) + (av + e_1)s_{agg} \\
&= (-as_{agg} + e_{agg})v + e_0 + m_i + avs_{agg} + e_1 s_{agg} \\
&= m_i + \underbrace{e_{agg}v + e_0 + e_1 s_{agg}}_{e_{noise}} \pmod{q_L}
\end{aligned}
$$

噪声项：
$$\boxed{e_{noise}^{(i)} = e_{agg}v + e_0 + e_1 s_{agg}}$$

噪声上界（由CKKS标准分析）：
$$\|e_{noise}^{(i)}\|_{can} \leq B_{clean} = 8\sqrt{2}\sigma N + 6\sigma\sqrt{N} + 16\sigma\sqrt{hN}$$

---

### 阶段三：上传 —— 密文传输

**输入**：密文 $ct_i^{(t)}$
**输出**：服务器接收到的密文

#### 传输过程

客户端 $C_i$ 通过TLS通道发送：
$$C_i \xrightarrow{TLS} AS: \quad ct_i^{(t)}$$

**安全性质**：
- AS收到密文，但**无法解密**（不持有任何 $sk_j$）
- 中间人攻击者只能看到密文，无法获知明文

---

### 阶段四：聚合 —— 服务器同态聚合

**输入**：密文集合 $\{ct_i^{(t)}\}_{i \in S_t}$，权重 $\{w_i = |D_i|/|D_{total}|\}$
**输出**：聚合密文 $ct_{agg}^{(t)}$

#### 步骤4.1：加权同态聚合

对每个密文执行标量乘法（权重）和加法：

$$
\begin{aligned}
ct_{agg}^{(t)} &= \sum_{i \in S_t} w_i \cdot ct_i^{(t)} \\
&= \left(\sum_{i \in S_t} w_i c_{i,0}, \; \sum_{i \in S_t} w_i c_{i,1}\right)
\end{aligned}
$$

展开：

$$
\begin{aligned}
ct_{agg}^{(t)} = \Big(& \underbrace{b_{agg} v_{agg} + e_{agg,0} + m_{agg}}_{c_{agg,0}}, \; \\
  & \underbrace{a v_{agg} + e_{agg,1}}_{c_{agg,1}}\Big)
\end{aligned}
$$

其中：
- $v_{agg} = \sum_i w_i v_i$
- $e_{agg,0} = \sum_i w_i e_{i,0}$
- $e_{agg,1} = \sum_i w_i e_{i,1}$
- $m_{agg} = \sum_i w_i m_i = \text{Encode}(\sum_i w_i \Delta w_i)$

**核心聚合公式**：

$$
\boxed{ct_{agg}^{(t)} = (b_{agg} v_{agg} + e_{agg,0} + m_{agg}, \; a v_{agg} + e_{agg,1})}$$

#### 步骤4.2：聚合噪声分析

聚合后的解密结构：

$$
\begin{aligned}
c_{agg,0} + c_{agg,1} \cdot s_{agg} &= m_{agg} + e_{agg,0} + e_{agg,1} s_{agg} \\
&= m_{agg} + \sum_i w_i (e_{i,0} + e_{i,1} s_{agg}) \\
&= m_{agg} + \sum_i w_i e_{noise}^{(i)}
\end{aligned}
$$

聚合噪声：
$$\boxed{e_{agg}^{(t)} = \sum_{i \in S_t} w_i e_{noise}^{(i)}}$$

**噪声方差分析**：
由于各客户端噪声独立：

$$
\mathbb{E}[\|e_{agg}\|^2] = \sum_{i \in S_t} w_i^2 \cdot \mathbb{E}[\|e_{noise}^{(i)}\|^2]$$

当数据均衡时（$w_i \approx 1/|S_t|$）：
$$\mathbb{E}[\|e_{agg}\|^2] \approx \frac{1}{|S_t|} \cdot \mathbb{E}[\|e_{noise}\|^2]$$

**关键结论**：聚合噪声方差**降低约 $|S_t|$ 倍**（客户端越多，聚合越稳定）。

---

### 阶段五：Delta生成 —— 密文差分

**输入**：当前轮聚合密文 $ct_{agg}^{(t)}$，上轮聚合密文 $ct_{agg}^{(t-1)}$
**输出**：密文Delta $\delta^{(t)}$

#### 步骤5.1：密文减法

$$
\delta^{(t)} = ct_{agg}^{(t)} - ct_{agg}^{(t-1)}$$

分量形式：

$$
\begin{aligned}
\delta^{(t)} &= (\delta_0^{(t)}, \delta_1^{(t)}) \\
&= (c_{agg,0}^{(t)} - c_{agg,0}^{(t-1)}, \; c_{agg,1}^{(t)} - c_{agg,1}^{(t-1)})
\end{aligned}
$$

展开：

$$
\begin{aligned}
\delta_0^{(t)} &= b_{agg}(v_{agg}^{(t)} - v_{agg}^{(t-1)}) + (e_{agg,0}^{(t)} - e_{agg,0}^{(t-1)}) + (m_{agg}^{(t)} - m_{agg}^{(t-1)}) \\
\delta_1^{(t)} &= a(v_{agg}^{(t)} - v_{agg}^{(t-1)}) + (e_{agg,1}^{(t)} - e_{agg,1}^{(t-1)})
\end{aligned}
$$

**核心Delta公式**：

$$
\boxed{\delta^{(t)} = (b_{agg} \Delta v + \Delta e_0 + \Delta m_{agg}, \; a \Delta v + \Delta e_1)}$$

其中 $\Delta m_{agg} = m_{agg}^{(t)} - m_{agg}^{(t-1)} = \text{Encode}(\Delta w_{global}^{(t)})$

#### 步骤5.2：Delta噪声分析

Delta噪声为上轮和本轮噪声之差：
$$e_{\delta}^{(t)} = e_{agg}^{(t)} - e_{agg}^{(t-1)}$$

由于噪声独立：
$$\|e_{\delta}^{(t)}\|_{can} \leq \|e_{agg}^{(t)}\|_{can} + \|e_{agg}^{(t-1)}\|_{can} \leq 2 B_{agg}$$

---

### 阶段六：预取 —— 密文广播与客户端累加

**输入**：密文Delta $\delta^{(t)}$，目标客户端集合 $PrefSet_t$
**输出**：客户端预取缓存更新

#### 步骤6.1：服务器广播

AS向未选中客户端广播：
$$AS \xrightarrow{} C_j: \quad (\delta^{(t)}, \Sigma^{(t)}, t)$$

其中 $\Sigma^{(t)}$ 为TPW阈值签名，$t$ 为轮次号。

#### 步骤6.2：客户端验证

客户端验证：

$$
\text{Verify}_{vk_{WN}}(\Sigma^{(t)}, H(\delta^{(t)} \| t)) \stackrel{?}{=} \text{True}$$

且：
$$t > t_{last\_accepted} \quad \text{// 防重放}$$

#### 步骤6.3：客户端同态累加

若验证通过，客户端累加到预取缓存：

$$
\boxed{ct_{prefetch}^{(t)} = ct_{prefetch}^{(t-1)} + \delta^{(t)}}$$

展开：

$$
\begin{aligned}
ct_{prefetch}^{(t)} &= \sum_{k=s}^t \delta^{(k)} \\
&= \sum_{k=s}^t (ct_{agg}^{(k)} - ct_{agg}^{(k-1)}) \\
&= ct_{agg}^{(t)} - ct_{agg}^{(s-1)}
\end{aligned}
$$

**关键性质**：预取缓存 = 最新全局模型密文 - 上次同步时的全局模型密文

#### 步骤6.4：预取噪声累积分析

设预取窗口为 $R = t - s + 1$ 轮，每轮Delta噪声上界为 $B_\delta$。

累积噪声：

$$
\boxed{\|e_{prefetch}^{(t)}\|_{can} \leq \sum_{k=s}^t \|e_{\delta}^{(k)}\|_{can} \leq R \cdot B_\delta}$$

**Bootstrapping触发条件**：

为保证解密正确，需要：

$$
\log_2(R \cdot B_\delta) + s_{smudge} < \log_2(q_l)$$

其中 $q_l$ 为当前层级模数，$s_{smudge}$ 为smudging噪声比特数。

当噪声预算不足时，触发Bootstrapping或要求客户端主动同步（清空缓存）。

---

### 阶段七：解密 —— 阈值部分解密与组合

**输入**：预取缓存密文 $ct_{prefetch}^{(t)} = (c_0, c_1)$，客户端私钥份额 $sk_i = s_i$
**输出**：明文梯度累积 $\Delta w_{cum}$

#### 步骤7.1：客户端计算部分解密份额

客户端 $C_i$ 计算：

$$
\boxed{D_i = s_i \cdot c_1 + e_{smudge} \pmod{q_l}}$$

其中 $e_{smudge} \leftarrow D_{R, \sigma_{smudge}}$ 为**Smudging噪声**。

**Smudging噪声大小**：
为达到统计安全参数 $s$：
$$\sigma_{smudge} \geq 2^s \cdot \|e_{prefetch}\|_{can}$$

实践中取 $s = 20$（20比特统计安全）。

#### 步骤7.2：收集其他t-1个部分解密份额

客户端向 $t-1$ 个辅助节点（或其他客户端）请求部分解密：

$$
\begin{aligned}
C_i &\xrightarrow{request} AN_j: \quad ct_{prefetch} \\
AN_j &\xrightarrow{response} C_i: \quad D_j = s_j \cdot c_1 + e_{smudge,j}
\end{aligned}
$$

#### 步骤7.3：拉格朗日插值组合

设 $T$ 为参与解密的节点集合，$|T| = t$。计算拉格朗日系数：

$$
\lambda_j = \prod_{k \in T, k \neq j} \frac{-k}{j - k} \pmod{q_l}$$

组合明文：

$$
\boxed{m_{combined} = c_0 + \sum_{j \in T} \lambda_j \cdot D_j \pmod{q_l}}$$

#### 步骤7.4：组合正确性证明

展开组合公式：

$$
\begin{aligned}
m_{combined} &= c_0 + \sum_{j \in T} \lambda_j (s_j \cdot c_1 + e_{smudge,j}) \\
&= c_0 + c_1 \cdot \sum_{j \in T} \lambda_j s_j + \sum_{j \in T} \lambda_j e_{smudge,j} \\
&= c_0 + c_1 \cdot s_{agg} + e_{total\_smudge} \quad \text{// 由Shamir共享重构性质} \\
&= m_{prefetch} + e_{prefetch} + e_{total\_smudge}
\end{aligned}
$$

其中：
- $m_{prefetch}$ 为预取缓存的明文
- $e_{prefetch}$ 为预取累积噪声
- $e_{total\_smudge} = \sum_j \lambda_j e_{smudge,j}$ 为总smudging噪声

#### 步骤7.5：CKKS解码

$$
\Delta w_{cum} = \text{CKKS.Decode}(m_{combined}) = \frac{1}{\Delta} \cdot \sigma(\pi(m_{combined}))$$

**解密后明文**：

$$
\boxed{\Delta w_{cum} = \sum_{k=s}^t \Delta w_{global}^{(k)} + \text{decode\_noise}}$$

即客户端获得了从上次同步到当前轮的所有全局模型更新之和。

---

### 阶段八：训练 —— 明文恢复与模型更新

**输入**：明文梯度累积 $\Delta w_{cum}$，上次同步的base模型 $w_{base}$
**输出**：更新后的本地模型 $w_{local}$

#### 步骤8.1：模型同步

客户端将预取累积应用到base模型：

$$
\boxed{w_{sync}^{(t)} = w_{base} + \Delta w_{cum}}$$

由预取缓存性质：
$$w_{sync}^{(t)} = w_{base} + \sum_{k=s}^t \Delta w_{global}^{(k)} = w_{global}^{(t)}$$

即客户端成功恢复到最新全局模型！

#### 步骤8.2：本地训练

客户端在本地数据 $D_i$ 上训练：

$$
w_i^{(t+1)} = w_{sync}^{(t)} - \eta \cdot \nabla \mathcal{L}(w_{sync}^{(t)}; D_i)$$

#### 步骤8.3：计算上传梯度

$$
\Delta w_i^{(t+1)} = w_i^{(t+1)} - w_{sync}^{(t)}$$

#### 步骤8.4：残差累积（SRCA，可选）

若启用SRCA：

$$
\begin{aligned}
g_i^{(t+1)} &= \Delta w_i^{(t+1)} + \gamma \cdot r_i^{(t)} \\
r_i^{(t+1)} &= g_i^{(t+1)} - \text{Sparse}(g_i^{(t+1)})
\end{aligned}
$$

上传 $ct_i^{(t+1)} = \text{Enc}_{pk_{agg}}(\text{Sparse}(g_i^{(t+1)}))$

#### 步骤8.5：进入下一轮

清空预取缓存：
$$ct_{prefetch} \leftarrow \emptyset, \quad w_{base} \leftarrow w_{sync}^{(t)}$$

---

## 五、实体交互协议

### 5.1 完整交互时序图

```
Phase 0: 初始化
─────────────────────────────────────────────────────────
KGC → All:  (pk_agg, evk)
KGC → C_i:  sk_i
KGC → AN_j: sk_j  (可选)
KGC → WN_k: sk_WN_k
KGC: 永久离线


Phase 1: 本地训练与加密（每轮，每个选中客户端）
─────────────────────────────────────────────────────────
C_i: 
  1. w_sync ← Apply(w_base, ThresholdDecrypt(ct_prefetch))
  2. w_i ← LocalTrain(D_i, w_sync)
  3. Δw_i ← w_i - w_sync
  4. (可选SRCA) g_i ← Δw_i + γ·r_i
  5. ct_i ← CKKS.Encrypt(pk_agg, Sparse(g_i))
  
C_i → AS: (ct_i, mask_i)


Phase 2: 同态聚合（服务器）
─────────────────────────────────────────────────────────
AS:
  1. 收集 {(ct_i, mask_i)}_{i∈S_t}
  2. ct_agg ← Σ_{i∈S_t} w_i · ct_i  （逐batch加权平均）
  3. δ^(t) ← ct_agg - ct_agg_prev   （密文减法）


Phase 3: 预取证生成（服务器+见证节点）
─────────────────────────────────────────────────────────
AS → WN_k: h = SHA256(δ^(t) || t || pk_agg)
WN_k → AS: σ_k = BLS.Sign(sk_WN_k, h)
AS:
  4. Σ ← BLS.Combine({σ_k})


Phase 4: 预取广播（服务器→未选中客户端）
─────────────────────────────────────────────────────────
AS → C_j (j ∉ S_t):
  (δ^(t), Σ, t, metadata)

C_j:
  1. if BLS.Verify(vk_WN, Σ, H(δ^(t)||t)) == True:
  2.    if t > last_round:
  3.        ct_prefetch ← ct_prefetch + δ^(t)
  4.        last_round ← t
  5.    else:
  6.        Reject (重放攻击)
  7. else:
  8.    Reject (伪造delta)


Phase 5: 阈值解密（客户端被选中时）
─────────────────────────────────────────────────────────
C_i:
  1. 若 ct_prefetch ≠ ∅:
  2.    D_i ← sk_i · c_1 + e_smudge   （自身部分解密）
  3.    for j in selected_ANs:
  4.        D_j ← RequestPartialDec(AN_j, ct_prefetch)
  5.    Δw_cum ← Combine({D_j}, ct_prefetch)
  6.    w_sync ← w_base + Δw_cum
  7.    ct_prefetch ← ∅
  8.    w_base ← w_sync
  9. else:
  10.   w_sync ← w_base   （已是最新）


Phase 6: 训练与上传（回到Phase 1）
─────────────────────────────────────────────────────────
C_i:
  w_i ← LocalTrain(D_i, w_sync)
  Δw_i ← w_i - w_sync
  ...
```

### 5.2 消息格式定义

| 消息类型 | 发送方 | 接收方 | 内容 | 加密/认证 |
|---------|--------|--------|------|----------|
| KeyShare | KGC | C_i/AN_j | $sk_i$ | 安全通道 |
| Upload | C_i | AS | $(ct_i, mask_i)$ | TLS |
| WitnessReq | AS | WN_k | $h = H(\delta \| t)$ | 认证通道 |
| WitnessResp | WN_k | AS | $\sigma_k$ | 认证通道 |
| Prefetch | AS | C_j | $(\delta, \Sigma, t)$ | TLS |
| PartDecReq | C_i | AN_j | $ct_{prefetch}$ | TLS |
| PartDecResp | AN_j | C_i | $D_j$ | TLS |

---

## 六、威胁模型与安全分析

### 6.1 威胁模型

**定义6.1（威胁模型）**：

| 威胁类型 | 攻击者能力 | 防御目标 |
|---------|-----------|---------|
| **恶意服务器** | AS可伪造delta、选择性广播、尝试解密 | AS无法获知任何明文 |
| **半诚实客户端** | 遵循协议但试图推断其他客户端数据 | 单客户端无法解密 |
| **客户端共谋** | ≤ t-1个客户端共享私钥份额 | 诚实客户端隐私保护 |
| **服务器+客户端共谋** | AS + ≤ t-1个客户端联合 | 仍需 ≥t个诚实节点 |
| **辅助节点共谋** | ≤ t-1个AN节点共谋 | 无法解密诚实客户端 |
| **预取投毒** | 伪造/重放/放大delta | 客户端拒绝非法delta |
| **噪声泄露攻击** | 从解密噪声恢复密钥 | Smudging噪声保护 |
| **掉线攻击** | 大规模节点掉线 | ≥t个节点在线即可 |

### 6.2 安全定理

**定理6.2（服务器无知性）**：
在Threshold-CipherFetch中，聚合服务器AS在整个协议执行过程中，**无法以超过negl(λ)的概率解密任何密文**。

**证明**：
1. AS不持有任何私钥份额 $sk_i$
2. AS仅知道 $pk_{agg}$ 和密文
3. 由决策性RLWE假设，从 $(pk_{agg}, ct)$ 恢复明文是困难的
4. 即使AS记录所有历史密文，仍无法解密

**定理6.3（阈值解密安全性）**：
最多 $t-1$ 个参与者共谋，无法恢复完整私钥 $s_{agg}$ 或解密任何密文。

**证明**：
1. 私钥 $s_{agg}$ 通过 $(t, n)$-Shamir秘密共享分发
2. Shamir共享具有 $(t-1)$-隐私性：任何 $t-1$ 个份额不泄露任何信息
3. 因此 $t-1$ 个共谋者无法重构 $s_{agg}$
4. 无法重构 $s_{agg}$ 则无法执行标准解密

**定理6.4（预取证不可伪造性）**：
在CDH假设下，没有 $t_w$ 个见证节点共谋，敌手无法伪造有效的TPW签名。

**证明**：
见第三篇方案文档。

### 6.3 知识边界安全分析

| 攻击场景 | 敌手知识 | 能否解密？ | 原因 |
|---------|---------|-----------|------|
| 仅AS | $pk_{agg}$, 密文 | ❌ 不能 | 无私钥份额 |
| AS + C_i | + $sk_i$ | ❌ 不能 | 仅1个份额，< t |
| AS + {C_i}_{i=1}^{t-1} | + t-1个份额 | ❌ 不能 | 仍 < t |
| AS + {C_i}_{i=1}^{t} | + t个份额 | ✅ 能 | 达到阈值 |
| {C_i}_{i=1}^{t-1}（无AS）| t-1个份额 | ❌ 不能 | 缺少密文通道 |
| {AN_j}_{j=1}^{t-1} | t-1个AN份额 | ❌ 不能 | 仍 < t |

---

## 七、正确性证明

### 7.1 协议正确性

**定理7.1（Threshold-CipherFetch正确性）**：
若所有参与者诚实执行协议，则每轮训练后，每个客户端的本地模型等于全局模型：

$$w_{sync}^{(t)} = w_{global}^{(t)}$$

**证明**：

**基础情况**（$t=0$）：
所有客户端从相同初始模型 $w^{(0)}$ 开始，显然成立。

**归纳假设**：
假设在轮次 $t-1$ 时，$w_{sync}^{(t-1)} = w_{global}^{(t-1)}$。

**归纳步骤**（轮次 $t$）：
1. 客户端上传梯度 $\Delta w_i^{(t)} = w_i^{(t)} - w_{global}^{(t-1)}$
2. 服务器聚合：$\Delta w_{global}^{(t)} = \sum_i w_i \Delta w_i^{(t)}$
3. 全局模型更新：$w_{global}^{(t)} = w_{global}^{(t-1)} + \Delta w_{global}^{(t)}$
4. Delta生成：$\delta^{(t)}$ 加密了 $\Delta w_{global}^{(t)}$
5. 客户端预取累积：$\Delta w_{cum} = \sum_{k=s}^t \Delta w_{global}^{(k)}$
6. 客户端同步：$w_{sync}^{(t)} = w_{base} + \Delta w_{cum} = w_{global}^{(s-1)} + \sum_{k=s}^t \Delta w_{global}^{(k)} = w_{global}^{(t)}$

证毕。

### 7.2 解密正确性

**定理7.2（阈值解密正确性）**：
给定密文 $ct = (c_0, c_1)$ 加密明文 $m$，通过ThresholdCKKS.Combine正确组合 $t$ 个部分解密份额后：

$$\text{Combine}(\{D_j\}_{j \in T}, ct) = m + e_{noise} + e_{smudge\_total}$$

其中 $e_{smudge\_total}$ 不影响CKKS解码（在误差容限内）。

**证明**：
已在阶段七中展开证明。

---

## 八、复杂度分析

### 8.1 计算复杂度

| 操作 | 复杂度 | 执行方 |
|------|--------|--------|
| 阈值密钥生成 | $O(n \cdot N \log N)$ | KGC（一次性） |
| CKKS加密 | $O(N \log N)$ | 客户端 |
| 同态标量乘 | $O(N \log N)$ | 服务器 |
| 同态加法 | $O(N)$ | 服务器/客户端 |
| 部分解密 | $O(N \log N)$ | 客户端/AN |
| 组合解密 | $O(t \cdot N)$ | 客户端 |
| TPW签名 | $O(1)$ 双线性对 | 见证节点 |
| TPW验证 | $O(1)$ 双线性对 | 客户端 |

### 8.2 通信复杂度

| 通信 | 复杂度 | 说明 |
|------|--------|------|
| 公钥分发 | $O(n \cdot |pk|)$ | 一次性 |
| 私钥份额分发 | $O(n \cdot |sk|)$ | 一次性 |
| 梯度上传 | $O(|S_t| \cdot s \cdot |w| \cdot C_{exp})$ | 每轮 |
| Delta广播 | $O((n-|S_t|) \cdot |w| \cdot C_{exp})$ | 每轮 |
| 部分解密请求 | $O(t \cdot |ct|)$ | 按需 |
| 见证签名 | $O(w \cdot |h|)$ | 每轮 |

其中 $C_{exp}$ 为密文膨胀系数（CKKS约20-50倍），$s$ 为稀疏率。

---

*本文档为Threshold-CipherFetch框架的完整设计方案，涵盖从密钥生成到模型训练的完整公式闭环、实体交互流程、知识边界定义和安全分析。可与第二篇（公式深度推导）、第三篇（安全增强）、第四篇（通信优化）组合形成完整的论文体系。*
