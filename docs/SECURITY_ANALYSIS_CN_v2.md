# ESAFL + KGC 补偿密文方案的安全性分析（半诚实服务器版）

## 1. 威胁模型与系统假设

### 1.1 参与方与信任假设

本方案涉及三类参与方：

- **KGC（密钥生成中心）**：可信但最小化参与。在系统初始化阶段生成 MK-CKKS 密钥对、派生公共多项式序列 $\{a^{(t)}\}_{t=1}^{T}$、预计算所有补偿密文并安全分发给服务器。KGC 不参与联邦学习的训练轮次协议，不接触任何训练数据或梯度信息。
- **服务器 $\mathcal{S}$**：**半诚实（honest-but-curious）**的。服务器严格遵循协议规范执行聚合、广播和预取调度，但会试图从协议转录（transcripts）中推断单个客户端的私有梯度信息。服务器不主动篡改、不伪造虚拟客户端、不重放旧消息。
- **客户端 $\mathcal{C}_i$（$i \in [N]$）**：分为两类威胁模型：
  - **半诚实（semi-honest / honest-but-curious）**：严格遵循协议，但试图从接收到的信息中推断其他客户端的私有数据；
  - **恶意（malicious）**：可能发送错误的梯度或投票，但受限于密码学原语无法破解加密。

### 1.2 密码学假设

**假设 1（RLWE 困难性）**：对于安全参数 $\lambda$，决策性环上带误差学习（Decision-RLWE）问题在多项式环 $R_q = \mathbb{Z}_q[x]/(x^n+1)$ 上是困难的。即对于均匀随机的 $a \leftarrow R_q$、秘密 $s \leftarrow \chi$、噪声 $e \leftarrow \chi$，元组 $(a, a \cdot s + e)$ 与均匀随机元组 $(a, u)$ 计算不可区分。

**假设 2（同态哈希抗碰撞性）**：哈希函数 $\mathcal{H}: \{0,1\}^* \to \mathbb{G}$ 满足抗碰撞性和抗原像性，其中 $\mathbb{G}$ 是阶为素数 $p'$ 的循环群。

**假设 3（KGC 可信生成）**：KGC 诚实地执行密钥生成和补偿密文构造，且其私钥材料在初始化完成后被安全擦除，不被任何 adversary 获取。

---

## 2. 半诚实客户端安全性

### 2.1 安全目标

在半诚实客户端威胁模型下，我们要求：任意客户端 $i$ 无法从协议视图中推断任何其他客户端 $j \neq i$ 的本地梯度信息，即使客户端 $i$ 知道全局聚合结果。

### 2.2 理想-现实范式与模拟器

定义理想功能 $f$：输入所有客户端的本地梯度集合 $\mathcal{G} = \{\mathbf{g}_1, \dots, \mathbf{g}_N\}$，输出全局聚合梯度 $\mathbf{g}_{\text{agg}}^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} \mathbf{g}_i^{(t)}$（带适当加权）。

客户端 $i$ 在协议执行中的视图记为 $\mathsf{View}_i(\lambda, \mathcal{G})$，包含：
- 所有接收到的消息（全局模型 $\mathbf{w}^{(t)}$、同态哈希锚点 $H_{\text{pre}}^{(t)}$、解密后的累积梯度 $\mathbf{\Delta}_{\text{pre}}^{(i)}$）；
- 自身的随机数和历史状态。

**定理 1（半诚实客户端 IND-CPA 安全性）**：在假设 1（RLWE）下，对于任意非全客户端集合的半诚实客户端 $i$，存在概率多项式时间模拟器 $\mathsf{Sim}_i$，使得：

$$\bigl| \Pr[\mathcal{A}(\mathsf{View}_i) = 1] - \Pr[\mathcal{A}(\mathsf{Sim}_i(\mathbf{g}_i, f(\mathcal{G}))) = 1] \bigr| \leq \mathsf{negl}(\lambda)$$

其中 $\mathcal{A}$ 是任意 PPT 区分器。

### 2.3 证明草图

客户端 $i$ 的视图中，唯一依赖于其他客户端私有信息的部分是：
1. **密文层面**：其他客户端的密文 $c_{j,\text{up}}^{(t)}$ 上传到服务器，客户端 $i$ **从未直接接收**这些密文；
2. **聚合层面**：客户端 $i$ 最终解密得到的是累积聚合梯度 $\mathbf{\Delta}_{\text{pre}}^{(i)} = \sum_{\tau} \sum_{j \in \mathcal{S}^{(\tau)}} \mathbf{g}_j^{(\tau)}$。

对于第 1 点，由 RLWE 的 IND-CPA 安全性，对于任意两个明文 $\mathbf{m}_0, \mathbf{m}_1$：

$$c_{j,\text{up}}^{(t)} = \bigl[ a^{(t)} \cdot s_j + \mathsf{CRTStack}(\mathbf{g}_j) + e_j \bigr]_{R_q}$$

与随机环元素不可区分。即使客户端 $i$ 通过某些侧信道获得了 $c_{j,\text{up}}^{(t)}$（例如与服务器合谋，见第 5 节），在不知道 $s_j$ 的情况下也无法解密。

对于第 2 点，模拟器 $\mathsf{Sim}_i$ 可以直接用理想输出 $f(\mathcal{G})$ 构造一个与真实视图统计不可区分的模拟视图：因为 $\mathbf{\Delta}_{\text{pre}}^{(i)}$ 正是 $f(\mathcal{G})$ 的线性变换（累积和）。

**关键观察**：半诚实客户端 $i$ 看到的"全局聚合梯度"正是联邦学习的**设计目标**——每个客户端都需要知道聚合梯度来更新本地模型。因此，安全性的下界是：客户端 $i$ 无法获得比"聚合结果"更多的信息。

---

## 3. 客户端合谋抵抗性

### 3.1 威胁模型

假设存在一个合谋集合 $\mathcal{T} \subset [N]$，其中 $|\mathcal{T}| = t < N$。合谋客户端可以共享：
- 各自的本地梯度 $\{\mathbf{g}_i\}_{i \in \mathcal{T}}$；
- 各自的私钥片段 $\{s_i\}_{i \in \mathcal{T}}$；
- 协议执行中观察到的所有信息（解密后的聚合结果等）。

合谋目标：推断非合谋客户端 $k \notin \mathcal{T}$ 的单个梯度 $\mathbf{g}_k$。

### 3.2 信息论下界

**定理 2（合谋下界）**：在仅使用加性聚合的联邦学习中，若合谋客户端集合 $\mathcal{T}$ 满足 $|\mathcal{T}| < |\mathcal{S}^{(t)}| - 1$，则 $\mathcal{T}$ 无法以非忽略概率恢复任何非合谋客户端 $k \notin \mathcal{T}$ 的精确梯度。

**推导**：设在轮次 $t$ 中活跃客户端集合为 $\mathcal{S}^{(t)}$，解密后的聚合梯度为：

$$\mathbf{\Delta}_{\text{pre}}^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} \mathbf{g}_i^{(t)} + \tilde{E}^{(t)}$$

其中 $\tilde{E}^{(t)}$ 是残余解密噪声（可被 CRT 精确重构消除，假设噪声在整数解码边界内）。

合谋客户端已知自身的梯度之和：

$$\mathbf{G}_{\mathcal{T}} = \sum_{i \in \mathcal{T} \cap \mathcal{S}^{(t)}} \mathbf{g}_i^{(t)}$$

通过减法攻击，合谋方可获得：

$$\mathbf{G}_{\mathcal{S} \setminus \mathcal{T}} = \mathbf{\Delta}_{\text{pre}}^{(t)} - \mathbf{G}_{\mathcal{T}} = \sum_{i \in \mathcal{S}^{(t)} \setminus \mathcal{T}} \mathbf{g}_i^{(t)}$$

这是关于 $|\mathcal{S}^{(t)}| - |\mathcal{T}|$ 个未知向量、$d$ 个方程（维度）的线性系统。当：

$$|\mathcal{S}^{(t)}| - |\mathcal{T}| \geq 2$$

时，系统是**欠定的**（未知数维度 $> d$），存在无穷多解。因此，合谋方无法唯一确定任何单个 $\mathbf{g}_k$。

### 3.3 Blinding Mask 增强

如果系统启用了成对盲化掩码（pairwise blinding mask）$\mathbf{b}_{i,j}$（满足 $\sum_{i} w_i \mathbf{b}_{i,j} = \mathbf{0}$），则客户端实际加密的是：

$$\tilde{\mathbf{g}}_i = \mathbf{g}_i + \mathbf{b}_i$$

合谋客户端即使执行减法攻击，也只能得到：

$$\sum_{i \in \mathcal{S} \setminus \mathcal{T}} (\mathbf{g}_i + \mathbf{b}_i)$$

由于 $\mathbf{b}_i$ 是客户端 $i$ 与所有其他客户端的成对掩码之和：

$$\mathbf{b}_i = \sum_{j \neq i} \mathbf{b}_{i,j}$$

合谋方 $\mathcal{T}$ 仅掌握 $\{\mathbf{b}_{i,j}\}_{i,j \in \mathcal{T}}$，无法消除涉及 $j \notin \mathcal{T}$ 的掩码项。因此，即使 $|\mathcal{S}^{(t)}| - |\mathcal{T}| = 1$（仅剩一个非合谋客户端），掩码仍然保护该客户端的梯度。

---

## 4. 半诚实服务器安全性

### 4.1 服务器的观察能力

在半诚实服务器模型下，服务器 $\mathcal{S}$ 严格遵循协议，但会记录并利用所有协议转录（protocol transcripts）来推断客户端私有信息。服务器可观察：

1. **所有上传的密文**：$\{c_{i,j,\text{up}}^{(t)}\}_{i \in \mathcal{S}^{(t)}, j \in K^{(t)}}$；
2. **所有投票向量**：$\{\mathbf{v}_i^{(t)}\}_{i \in \mathcal{S}^{(t)}}$；
3. **聚合后的全局密文**：$\{C_j^{(t)}\}_{j \in K^{(t)}}$；
4. **预取调度信息**：哪些客户端在何时接收了哪些密文；
5. **模型更新历史**：每轮全局模型的变化轨迹。

服务器的目标是：从上述观察中推断单个客户端 $i$ 的本地梯度 $\mathbf{g}_i^{(t)}$。

### 4.2 抗解密攻击

**定理 3（服务器不可解密性）**：在假设 1（RLWE）和假设 3（KGC 可信）下，半诚实服务器无法从聚合密文 $C_j^{(t)}$ 中恢复任何单个客户端的明文梯度。

**证明**：

聚合密文为：

$$C_j^{(t)} = \Bigl[ a^{(t)} \cdot S + \sum_{i \in \mathcal{S}^{(t)}} m_{i,j}^{(t)} + E^{(t)} \Bigr]_{R_q}$$

其中 $S = \sum_{\ell=1}^{N} s_\ell$ 是全局聚合私钥。服务器掌握：
- $C_j^{(t)}$（密文本身）；
- $a^{(t)}$（公共多项式，公开）；
- 所有客户端的投票向量 $\mathbf{v}_i^{(t)}$（明文）。

但服务器**不掌握任何** $s_\ell$（客户端私钥片段）。要从 $C_j^{(t)}$ 中消去 $a^{(t)} \cdot S$ 项，服务器必须计算：

$$\tilde{m} = \bigl[ C_j^{(t)} - a^{(t)} \cdot S \bigr]_{R_q}$$

由于 $S$ 未知，服务器无法执行此操作。进一步，根据 RLWE 假设，对于任意 $S \leftarrow \chi$，元组 $(a^{(t)}, a^{(t)} \cdot S + E^{(t)})$ 在 $R_q^2$ 上是均匀伪随机的。因此：

$$\Pr_{a,S,E}\bigl[\mathcal{A}(a, aS+E) = S\bigr] \leq \mathsf{negl}(\lambda)$$

即使服务器观察到所有历史密文 $\{C_j^{(\tau)}\}_{\tau=1}^{t}$，也无法建立关于 $S$ 的有效方程组，因为每轮的噪声 $E^{(\tau)}$ 独立且不可预测。

### 4.3 服务器能否从聚合梯度反推单个梯度？

服务器最终可以观察到全局模型的更新轨迹：

$$\mathbf{w}^{(t+1)} = \mathbf{w}^{(t)} - \eta \cdot \mathbf{g}_{\text{agg}}^{(t)}$$

其中 $\mathbf{g}_{\text{agg}}^{(t)} = \sum_{i \in \mathcal{S}^{(t)}} \mathbf{g}_i^{(t)}$。这是联邦学习的标准设计目标——服务器**理应知道**聚合梯度以驱动全局模型收敛。

**关键结论**：半诚实服务器无法获得比"聚合梯度"更多的信息。单个客户端的梯度 $\mathbf{g}_i^{(t)}$ 被 $|\mathcal{S}^{(t)}|-1$ 个其他客户端的梯度所掩蔽。

### 4.4 服务器能否从投票向量推断梯度？

服务器观察到每个客户端的 Top-$K$ 投票向量 $\mathbf{v}_i^{(t)}$。这泄露了哪些 pack 对客户端 $i$ 最重要，但没有泄露：
- 具体的梯度数值；
- 非 Top-$K$ pack 的任何信息；
- 梯度方向的具体分量。

**定理 4（投票隐私）**：在仅知道投票向量 $\mathbf{v}_i^{(t)}$ 而不知道密钥 $s_i$ 的情况下，服务器无法以非忽略概率重构客户端 $i$ 的原始梯度 $\mathbf{g}_i^{(t)}$。

**证明**：投票向量 $\mathbf{v}_i^{(t)}$ 仅编码了 $J$ 个 packs 中哪些属于 Top-$K$。对于每个选中的 pack $j \in \mathcal{T}_i$，其内部的具体梯度值 $m_{i,j}^{(t)}$ 仍被加密在 $c_{i,j,\text{up}}^{(t)}$ 中。由定理 3，服务器无法解密这些密文。

---

## 5. 客户端-服务器合谋边界

### 5.1 威胁模型

假设客户端子集 $\mathcal{T} \subset [N]$ 与半诚实服务器 $\mathcal{S}$ 合谋。合谋方共享：
- 服务器端的所有观察（密文、投票、聚合结果）；
- 合谋客户端的私钥片段 $\{s_i\}_{i \in \mathcal{T}}$ 和本地梯度 $\{\mathbf{g}_i\}_{i \in \mathcal{T}}$。

合谋目标：推断非合谋客户端 $k \notin \mathcal{T}$ 的单个梯度。

### 5.2 部分合谋的不可解密性

**定理 5（部分合谋安全性）**：即使服务器与客户端子集 $\mathcal{T} \subsetneq [N]$ 合谋，只要 $|\mathcal{T}| < N$，合谋方无法恢复任何非合谋客户端 $k \notin \mathcal{T}$ 的明文梯度。

**证明**：

合谋方掌握 $\{s_i\}_{i \in \mathcal{T}}$ 和服务器端的所有密文。要解密聚合密文，需要全局私钥：

$$S = \sum_{i \in \mathcal{T}} s_i + \sum_{k \notin \mathcal{T}} s_k$$

令 $S_{\mathcal{T}} = \sum_{i \in \mathcal{T}} s_i$（合谋方已知），$S_{\neg\mathcal{T}} = \sum_{k \notin \mathcal{T}} s_k$（未知）。则：

$$C_j^{(t)} = \bigl[ a^{(t)}(S_{\mathcal{T}} + S_{\neg\mathcal{T}}) + \sum_{i \in \mathcal{S}} m_{i,j}^{(t)} + E^{(t)} \bigr]_{R_q}$$

合谋方只能计算：

$$C_j^{(t)} - a^{(t)} S_{\mathcal{T}} = \bigl[ a^{(t)} S_{\neg\mathcal{T}} + \sum_{i \in \mathcal{S}} m_{i,j}^{(t)} + E^{(t)} \bigr]_{R_q}$$

剩余项 $a^{(t)} S_{\neg\mathcal{T}}$ 仍然受 RLWE 保护。由于 $S_{\neg\mathcal{T}}$ 是至少一个独立均匀秘密的线性组合（当 $|\mathcal{T}| < N$ 时），根据假设 1，$a^{(t)} S_{\neg\mathcal{T}} + E$ 仍然是伪随机的。

### 5.3 最坏情况分析

考虑最坏情况：某轮次仅有一个客户端 $i$ 在线（$|\mathcal{S}^{(t)}| = 1$），且该客户端恰好与服务器合谋。

聚合密文退化为：

$$C_j^{(t)} = c_{i,j,\text{up}}^{(t)} \oplus \bigoplus_{k \neq i} c_{\text{comp},j}^{(t,k)}$$

展开：

$$C_j^{(t)} = \Bigl[ a^{(t)} s_i + m_{i,j}^{(t)} + e_{i,j}^{(t)} + \sum_{k \neq i} (a^{(t)} s_k + e_{\text{comp},j}^{(t,k)}) \Bigr]_{R_q}$$

$$= \Bigl[ a^{(t)} S + m_{i,j}^{(t)} + E_{\text{total}} \Bigr]_{R_q}$$

合谋方掌握 $s_i$ 和 $C_j^{(t)}$，可计算：

$$C_j^{(t)} - a^{(t)} s_i = \Bigl[ a^{(t)} \underbrace{\sum_{k \neq i} s_k}_{S_{\neg i}} + m_{i,j}^{(t)} + E_{\text{total}} \Bigr]_{R_q}$$

但 $S_{\neg i} = \sum_{k \neq i} s_k$ 仍然是 RLWE 秘密。合谋方无法区分 $a^{(t)} S_{\neg i} + m_{i,j}^{(t)} + E$ 与 $a^{(t)} S_{\neg i} + E'$（另一个噪声样本）。因此，即使在这种极端情况下，**单个客户端与服务器合谋仍然无法解密**。

### 5.4 完全合谋：安全性崩溃

当 $\mathcal{T} = [N]$（所有客户端与服务器合谋）时，$S_{\neg\mathcal{T}} = 0$，合谋方完全掌握 $S$。此时：

$$\tilde{m} = \bigl[ C_j^{(t)} - a^{(t)} S \bigr]_{R_q} = \sum_{i \in \mathcal{S}} m_{i,j}^{(t)} + E^{(t)}$$

安全性完全崩溃，合谋方可精确恢复聚合明文。这是安全聚合的理论下界：**无法抵抗所有参与方的合谋**，任何方案都不例外。

---

## 6. 补偿密文的安全性

### 6.1 零明文是否泄露信息？

KGC 生成的补偿密文明文为 $\mathbf{0}$，但结构上包含新鲜噪声：

$$c_{\text{comp},j}^{(t,k)} = \bigl[ a^{(t)} s_k + e_{\text{comp},j}^{(t,k)} \bigr]_{R_q}$$

**引理 1**：对于任意两个不同的掉线客户端 $k_1, k_2$，其补偿密文 $c_{\text{comp},j}^{(t,k_1)}$ 和 $c_{\text{comp},j}^{(t,k_2)}$ 在计算上不可区分（假设 $s_{k_1}, s_{k_2}$ 独立均匀分布）。

**证明**：由 RLWE 假设，$(a^{(t)}, a^{(t)} s_k + e)$ 对不同的 $s_k$ 都是伪随机的，且分布相同。因此，补偿密文不泄露掉线客户端的身份信息。

### 6.2 补偿密文 vs 真实密文的不可区分性

比较活跃客户端密文 $c_{i,j,\text{up}}^{(t)} = [a^{(t)} s_i + m_{i,j}^{(t)} + e_i]_{R_q}$ 与补偿密文 $c_{\text{comp},j}^{(t,k)} = [a^{(t)} s_k + e_k]_{R_q}$。

从服务器视角：两者都呈 RLWE 分布。服务器即使知道哪些客户端掉线（从而知道哪些密文是补偿），也无法从中提取任何信息（明文为 0）。更重要的是，服务器**无法将补偿密文与真实密文区分开**（如果它试图猜测），因为它们的分布相同。

---

## 7. 与标准安全聚合的对比

| 攻击场景 | Bonawitz et al. (SecAgg) | ESAFL + KGC 补偿 |
|---------|--------------------------|------------------|
| 服务器单独 | 无法解密 | 无法解密（无 $S$） |
| $t < N/2$ 客户端合谋 | 安全 | 安全（RLWE + 欠定系统） |
| 客户端+服务器合谋 | 安全若 $t < N/2$ | 安全除非 $t = N$ |
| 全合谋 | 崩溃 | 崩溃（理论下界） |

ESAFL + KGC 补偿的优势在于：**服务器与任意客户端子集合谋都无法解密**，必须收集全部 $N$ 个私钥片段。而在标准 SecAgg 中，服务器与超过 $N/2$ 个客户端合谋即可破解。

---

## 8. 总结

ESAFL + KGC 零密文补偿方案的安全性建立在以下核心支柱上：

1. **RLWE 困难性**：保证密文对任何无密钥方的不可区分性；
2. **多密钥分散**：全局密钥 $S = \sum_{i=1}^{N} s_i$ 被 $N$ 个客户端分别持有，不存在单点泄露；
3. **KGC 可信最小化**：KGC 仅参与初始化，不接触训练数据，负责密钥生成和补偿密文供应；
4. **半诚实服务器的限制**：即使服务器记录所有转录，无 $S$ 仍无法解密任何个体信息。

该方案在半诚实客户端、客户端合谋、半诚实服务器、以及部分客户端-服务器合谋四种威胁模型下均提供可证明的安全性，仅在**所有 $N$ 个客户端与服务器完全合谋**时达到理论安全下界。
