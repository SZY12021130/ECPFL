# firset_paper.pdf 第1–5章问题审查报告

> **审查范围**：Chapter I (Introduction) – Chapter V (Security Analysis)  
> **审查维度**：符号一致性、定义严谨性、逻辑连贯性、数学正确性  
> **严重程度**：🔴 严重（影响理解/证明） / 🟡 中度（需要澄清） / 🟢 轻微（建议修正）

---

## 一、符号不一致（Notation Inconsistency）

### 1.1 轮次符号混用：$t$ vs $r$

| 位置 | 符号 | 上下文 |
|------|------|--------|
| 表II (Summary of Key Notations) | $T, t$ | $T$ 总轮数，$t$ 当前迭代 |
| Section III-B | $t$ | 标准FedAvg轮次索引 |
| Section IV-D | $t$ | 主轮次索引 |
| Algorithm 2 | 无显式轮次 | 仅使用上标 $(t)$ |
| Section IV-C2 公式(6)-(8) | 无下标 | 突然省略轮次下标 |

**问题**：论文在表II明确定义 $t$ 为"current iteration"，但在正文多处（如Section IV-C2的公式6-8）省略轮次下标，导致读者无法区分局部变量与轮次相关变量。

**建议**：全文统一使用上标 $(t)$ 或 $(r)$ 标记轮次相关量，避免局部公式中省略。

---

### 1.2 Pack / Batch / Slot 数量符号：$J$ vs $P$ vs $B$

| 位置 | 使用的符号 | 含义 |
|------|-----------|------|
| 表II | $J, j$ | Total batches and batch index |
| Section IV-C2 | $P$ packs | "partitioned into $P$ packs" |
| 公式(7) | $j \in [J]$ | pack索引范围 |
| Algorithm 2 line 4 | $j \in [P]$ | 但输入参数是 $J$ |
| Section III-C4 | $B$ | "B floating-point scalars within each selected pack" |
| 表II | $B$ | 在"Global Mask Vote"部分被定义为"total batch数" |

**问题**：$J, P, B$ 三个符号混用指代相同或相近概念。
- Algorithm 2 输入说 "Number of packs $J$"，但循环体内写 $j \in [P]$，这是直接的符号矛盾。
- 表II中 $B$ 既在密码学参数中表示 slot 数，又在 GMV 中表示总 batch 数。

**建议**：统一术语体系——
- 用 $P$ 表示 pack 总数（VPTopK 的粒度）
- 用 $B$ 或 $N/2$ 表示每个 pack 内包含的 CKKS slot 数
- 删除 $J$ 或明确定义为 $J = P$（若二者等价）

---

### 1.3 客户端集合符号：$S(t)$ vs $S_t$ vs $S_{active}$

| 位置 | 符号 | 含义 |
|------|------|------|
| 表II | $S(t), D(t)$ | Activate / Deactivated client subset |
| Section III-B | $S_t \subseteq [N]$ | 选中的客户端子集 |
| Section IV-A1 | $S_{active} \subseteq U$ | 动态选中的训练队列 |
| Section IV-D2 | $S(t), D(t)$ | 活跃/停用客户端 |
| Algorithm 1 | $S(t)$ | 用于投票计数 |

**问题**：
- Section III-B 用 $S_t$（下标），表II和后续用 $S(t)$（函数式），Section IV-A1 又用 $S_{active}$（单词下标）。
- 表II定义 $U = \{U_1, ..., U_N\}$ 为客户端集合，但后文（如Section IV-A1）突然改用 $\{C_i\}$ 或 $\{C_i\}_{i=1}^N$。

**建议**：全文统一使用 $S_t$（或 $\mathcal{S}_t$）表示第 $t$ 轮选中的客户端集合，$\bar{S}_t$ 表示未选中集合。

---

### 1.4 密文符号格式不统一

| 位置 | 密文符号 | 格式 |
|------|---------|------|
| 表II | $c_i^{(t)}$ | 单字母上标 |
| 公式(10) | $ct_{i,j}^{(t)}$ | 双下标（client, pack） |
| 公式(14) | $C_j^{(t)}$ | 大写（聚合密文） |
| 公式(15) | $C_{pre,j}^{(t)}$ | 大写+prescript |
| Algorithm 2 | $ct_{(i,t_j),up}$ | 奇怪的括号组合 |
| 公式(18)(19) | $ct_{i,j,0}, ct_{i,j,1}$ | 标准CKKS对 |
| Section IV-D2 | $C_{p(r)e}$ | 文本中写 $C_{pre}$ 但括号打断 |

**问题**：密文符号在单多项式形式（ESAFL式）和密文对形式（标准CKKS）之间反复横跳。

---

### 1.5 学习率与权重符号缺失/矛盾

| 位置 | 问题描述 |
|------|---------|
| Section III-B 公式(1) | 使用 $w_i = |D_i|/|D|$ 作为权重，但 $|D| = \sum_j |D_j|$ 从未定义 |
| 公式(14) | 聚合密文 $C_j^{(t)}$ 使用简单求和，没有任何权重 |
| Algorithm 3 line 17 | 模型更新为 $w_i^{(t)} \leftarrow w_i^{(sync)} - m_{sum}$，缺少学习率 $\eta$ |
| 公式(17) | 突然出现 $\eta$：$w^{(t+R)} \leftarrow w^{(t)} - \eta \cdot m_{sum}$ |

**问题**：论文在公式(1)中明确定义了FedAvg加权聚合，但在后续的密文聚合公式中完全忽略了权重，变成简单平均。这导致**算法描述与数学公式不一致**。

---

### 1.6 稀疏率符号：$K$ vs $\tau$ vs $K_{up}$

| 位置 | 符号 | 含义 |
|------|------|------|
| Section IV-C2 | top-$K$ | 保留的pack数量 |
| Section IV-C2 | $\tau \in (0,1]$ | 投票阈值（"threshold $\tau$"） |
| 表II | $K_{up}, K_{down}$ | "Upstream and downstream sparsity bounds" |
| Section IV-C4 / Algorithm 2 | 无显式稀疏率 | 未定义 $K$ 与 $P$ 的比例关系 |

**问题**：表II定义了 $K_{up}, K_{down}$，但正文中从未使用。正文使用 top-$K$ 和 $\tau$，但没有说明二者关系（$\tau$ 是投票阈值，不是稀疏率）。

---

## 二、定义不清（Ambiguous Definitions）

### 2.1 🔴 MK-CKKS 加密方案从未正式定义

**问题描述**：
- Introduction和Related Work多次声称使用"multi-key CKKS" (MK-CKKS)。
- 但论文从未给出MK-CKKS的正式算法定义（KeyGen, Enc, Dec, Eval）。
- 公式(10)的加密形式 $[a^{(t)} \cdot s_i + \tilde{p} \cdot e + pt]_q$ 是**ESAFL的ESHE加密**（单多项式），不是标准MK-CKKS。
- 公式(18)(19)又突然变成标准CKKS密文对 $(ct_0, ct_1)$。

**影响**：读者无法判断论文到底基于哪种加密方案，安全证明的归约基础不清晰。

**建议**：
1. 明确选择一种方案（推荐基于ESAFL的ESHE，因为公式已经适配）。
2. 给出完整的算法元组定义：$(\text{Setup}, \text{KeyGen}, \text{Enc}, \text{Dec}, \text{Eval})$。
3. 删除所有与所选方案矛盾的公式。

---

### 2.2 🔴 "One-shot O(1) Decryption" 缺乏算法定义

**问题描述**：
- 论文核心卖点之一是"one-shot O(1) decryption"（Abstract, Introduction, Section IV-D）。
- 但公式(17)显示解密需要：
  $$p_{pre,j}^{(t)} = [C_{pre,j}^{(t)} - (a^{(t)}) \cdot S]_q$$
  其中 $(a^{(t)}) = \sum_{r=0}^{R-1} a^{(t+r)}$。
- 客户端需要生成/存储 $R$ 个不同的 $a^{(t+r)}$（或种子），这不是 $O(1)$。
- 论文从未定义"one-shot decryption"的算法步骤、输入输出、复杂度。

**影响**：核心贡献的表述缺乏形式化支撑，审稿人可能质疑其有效性。

**建议**：
1. 给出 One-Shot Decrypt 算法的伪代码。
2. 明确复杂度：若 $a^{(t)} = \text{PRPG}(t, B)$，则生成 $(a^{(t)})$ 需要 $O(R \cdot \text{PRPG})$ 时间，不是 $O(1)$。
3. 或者修正表述为"single ciphertext decryption"（指只需解密一个密文，而不是复杂度O(1)）。

---

### 2.3 🟡 Homomorphic Hash 定义自相矛盾

**问题描述**：
- 表II定义 $H$ 为 "hash cyclic group" 的运算。
- 公式(11): $H_{j,up}^{(t)} = H(ct_{i,j}^{(t)})$ —— 单参数。
- 公式(16): $H_{pre,j}^{(t)} = H(C_{pre,j}^{(t)}, a^{(t)}, t, t+R)$ —— 四参数。
- 公式(24): $h_{i,j}^{(t)} = \sum_{k=0}^{d-1} g_k^{c[k]} \mod p$ —— 指数和形式。
- 公式(25): $H_{pre}^{(t)} = \sum_i \sum_r h_{i,j}^{(t+r)} \mod p$ —— 线性聚合。
- Algorithm 3 line 13: "if $h_{chk} \neq H_{pre}^{(t)} \mod p$" —— $h_{chk}$ 是客户端重新计算的hash，但计算方法未定义。

**问题**：
- 公式(24)的hash不是密码学安全的（指数和可被轻易伪造）。
- 公式(25)假设hash可线性聚合，但公式(24)的指数和不具备这种同态性。
- 如果服务器是恶意的，它可以同时篡改密文和 $H_{pre}^{(t)}$，使验证通过。

---

### 2.4 🟡 Zero-Plaintext Compensation 机制逻辑断裂

**问题描述**：
- Section IV-A1: "KGC ... remains entirely offline during the dynamic training process and never participates in active cipher aggregation or zero-filling operations."
- Section IV-C4: "The KGC periodically provisions the server with zero-plaintext compensating ciphertexts..."
- Section IV-D2: "the server securely injects the KGC-provisioned zero-plaintext compensations..."

**矛盾**：KGC 在 Phase 0 后"永久离线"，但后续却"周期性提供"补偿密文。如果 KGC 离线，谁来生成这些补偿密文？

**建议**：
1. 明确补偿密文的生成方式（预生成？服务器自行生成？）。
2. 若服务器自行生成，需证明这不破坏安全性（因为服务器不持有 $s_k$）。
3. 或者修改 KGC 为"在线但被动"，仅在请求时提供补偿密文。

---

### 2.5 🟢 CRTStack 方法徒有其名

**问题描述**：
- Section IV-C1提到"we further employ the CRTStack method, which dramatically reduces the number of upload ciphertexts."
- Algorithm 2 被命名为 "CRT-VPTopk Client Upload Procedure"。
- 但 Algorithm 2 和正文没有任何地方解释或实现 CRTStack。

**建议**：要么补充 CRTStack 的定义和工作原理，要么删除相关引用。

---

### 2.6 🟡 Pack / Slot / Batch 三者关系未定义

**问题描述**：
- 论文混用三个术语：slot（CKKS概念）、pack（VPTopK概念）、batch（通用ML概念）。
- 从未定义：
  - 一个 pack 包含多少个 slot？
  - 一个 pack 对应模型参数的哪些维度？
  - $P$ 个 pack 如何映射到 $K = \lceil M/B \rceil$ 个 CKKS ciphertext？

**建议**：增加一个"Packing Strategy"小节，明确定义：
- 模型参数 → flatten → 分块为 $P$ 个 pack → 每个 pack 编码到 CKKS plaintext slots。

---

## 三、逻辑不连贯（Logical Disconnects）

### 3.1 🔴 加密方案前后矛盾

**问题描述**：论文在三处使用了三种不同的加密公式：

| 位置 | 加密公式 | 所属方案 |
|------|---------|---------|
| 公式(10) | $ct = [a^{(t)} \cdot s_i + \tilde{p} \cdot e + pt]_q$ | ESAFL/ESHE |
| 公式(18)(19) | $ct_0 = [a_t \cdot s_i + \tilde{p} \cdot e_0 + m]_q$, $ct_1 = [-a_t + \tilde{p} \cdot e_1]_q$ | 标准CKKS（但 $ct_1$ 缺少 $s_i$） |
| 表II描述 | "MK-CKKS" | 多密钥CKKS（无公式） |

**公式(19)的错误**：$ct_1 = [-a_t + \tilde{p} \cdot e_1]_q$ 缺少 $s_i$ 的绑定。标准CKKS密文对中，$ct_1$ 通常是 $a$（与密钥无关），但这里的加密声称是"client encryption scheme"，却没有任何客户端特有的信息在 $ct_1$ 中。

**影响**：安全证明（Theorem 1）基于RLWE，但RLWE样本需要 $(a, a \cdot s + e)$ 结构。公式(19)的 $ct_1$ 不包含 $s_i$，导致安全归约不成立。

---

### 3.2 🔴 聚合权重消失

**问题描述**：
- Section III-B 公式(1): $w_{t+1} = w_t - \eta \sum_{i \in S_t} \frac{|D_i|}{|D|} g_i$（加权FedAvg）
- 公式(14): $C_j^{(t)} = \sum_{i \in S(t)} ct_{i,j}^{(t)} + \sum_{k \in D(t)} ct_{k,j}^{(comp)}$（简单求和，无权重）

**矛盾**：密文聚合没有实现FedAvg的加权平均。若客户端数据量不均，简单求和会偏向大数据量客户端（如果所有客户端都参与），或在小采样下产生偏差。

**建议**：
- 若确实使用简单求和，明确说明并论证其合理性（如 cross-device 场景下数据均衡假设）。
- 若需要加权，补充同态标量乘法（$w_i \otimes ct_i$）的公式和噪声分析。

---

### 3.3 🔴 KGC 离线 but 持续服务

**问题描述**：
- Phase 0: "KGC then permanently goes offline"
- Section IV-C4: "KGC periodically provisions the server with zero-plaintext compensating ciphertexts"
- Section IV-D2: "KGC-provisioned zero-plaintext compensations"

**逻辑断裂**：永久离线的实体无法"周期性提供"任何内容。

**建议**：
- 方案A：KGC 预生成所有轮次的补偿密文，在初始化时一次性发送给服务器。
- 方案B：修改协议让服务器（或其他在线实体）生成补偿密文。
- 方案C：将 KGC 重新定义为"半在线"状态（仅在请求时响应）。

---

### 3.4 🟡 Hash 验证无法防御恶意服务器

**问题描述**：
- Theorem 2声称homomorphic hash可检测服务器篡改。
- 但验证方程(26): $H(C_{pre}^{(t)}) \stackrel{?}{=} H_{pre}^{(t)} \mod p$
- $H_{pre}^{(t)}$ 是服务器聚合并发送的，$C_{pre}^{(t)}$ 也是服务器发送的。
- 如果服务器同时篡改 $C_{pre}^{(t)}$ 和 $H_{pre}^{(t)}$（或重新计算后者），客户端无法检测。

**逻辑漏洞**：验证需要trusted anchor，但论文中没有这样的anchor。

**建议**：
- 引入客户端侧 commitments：每个客户端在加密前对梯度做承诺，服务器聚合承诺后广播。
- 或者使用数字签名链（如Section IV-C2末尾提到的"signed hash chain"），但需给出完整协议。

---

### 3.5 🟡 噪声分析完全缺失

**问题描述**：
- Section IV-D2提到"noise growth... constraining the maximum prefetch window given the CKKS modulus budget"。
- 但论文没有给出：
  - 单轮噪声上界
  - $R$ 轮累积噪声公式
  - CKKS模数链的具体参数
  - Bootstrapping触发条件
- 公式(15)定义 $E_{pre}^{(t)} = \sum_{r=0}^{R-1} E_j^{(t+r)}$ 为"composite noise"，但 $E_j^{(t)}$ 本身未定义噪声分布。
- 公式(17)中出现 $\tilde{E}_{pre}^{(t)}$（"residual decryption noise"），无定义。

**影响**：对于CKKS方案，噪声分析是审稿人必查的内容。缺失这部分会严重影响论文可信度。

**建议**：补充完整的噪声增长分析，包括：
1. 单轮加密噪声 $\|e_{enc}\|_{can}$ 的上界。
2. 聚合后噪声（$|S_t|$ 个密文相加）。
3. Delta计算后的噪声（两密文相减）。
4. $R$ 轮预取累积噪声 $R \cdot B_\delta$。
5. 解密后噪声与CKKS解码精度的关系。
6. 给定模数链 $[60, 40, 40, 60]$ 时的最大 prefetch 窗口 $R_{max}$。

---

### 3.6 🟡 模型更新方向矛盾

**问题描述**：
- Section III-B 公式(1): $w_{t+1} = w_t - \eta \sum g_i$（梯度下降，减法更新）
- Algorithm 3 line 17: $w_i^{(t)} \leftarrow w_i^{(sync)} - m_{sum}$（减法更新）
- 但预取的是模型增量（delta），即 $w^{(t)} - w^{(t-1)}$ 的密文。
- 如果预取的是增量，同步时应该是**加法**：$w_{sync} = w_{base} + \Delta w_{cum}$。

**矛盾**：论文声称预取的是模型更新增量，但解密后却用减法应用到模型上。这在数学上导致 $w_{sync} = w_{base} - (w_{current} - w_{base}) = 2w_{base} - w_{current}$，完全错误。

**建议**：明确预取的是梯度增量还是模型增量，并统一更新方向。
- 若为梯度累积：$w_{sync} = w_{base} - \eta \cdot g_{cum}$
- 若为模型增量：$w_{sync} = w_{base} + \Delta w_{cum}$

---

### 3.7 🟢 Section / Algorithm 引用错误

| 位置 | 错误描述 |
|------|---------|
| Section IV-C1 | "Algorithm 2, executing in two tightly coupled phases" — Algorithm 2确实标注了Phase A/B |
| Section IV-D2 | 引用"Algorithm 3"但在page 9时Algorithm 3尚未出现（在page 10） |
| Theorem 1 | "Collective decryption via partial decryption shares (Section ??)" — 未完成的交叉引用 |
| Section VI-D3 | "Sticky [16]: sketch clusting [12]" — 格式错误，两个不同策略合并 |

---

### 3.8 🟢 图表与正文数据不一致

| 位置 | 声明 | 实际数据 |
|------|------|---------|
| Abstract | "22-fold reduction in total communication" | Table V: 134.4MB → 16.8MB ≈ 8× |
| Abstract | "4.5-fold training speedup" | 正文: 3.2× |
| Conclusion | "78-fold reduction" | 无对应数据支持 |

**建议**：统一所有数据声明，确保Abstract、正文、Conclusion完全一致。

---

### 3.9 🟢 Algorithm 1 逻辑错误

**问题描述**：
- Algorithm 1 line 14: $K^{(t)} \leftarrow \{j : \sum_i v_{i,j}^{(t)} \geq |S(t)|\}$
- 这里比较的是投票和与 $|S(t)|$（客户端数量），不是与 $\tau \cdot |S(t)|$。
- 这意味着需要**所有**活跃客户端都投票给某个pack，它才能被选中——这不是majority vote，是unanimous vote。
- 但正文Section IV-C2描述的是"global majority vote with threshold $\tau \in (0,1]$"。

**建议**：修正为 $K^{(t)} \leftarrow \{j : \sum_i v_{i,j}^{(t)} \geq \tau \cdot |S(t)|\}$。

---

## 四、数学正确性疑问

### 4.1 🟡 公式(14)的代数正确性

$$C_j^{(t)} = \sum_{i \in S(t)} ct_{i,j}^{(t)} + \sum_{k \in D(t)} ct_{k,j}^{(comp)} = [a^{(t)} S + \tilde{p} E_j^{(t)} + \sum_{i \in S(t)} m_{i,j}^{(t)}]_q$$

**问题**：
- 左边是多项式在 $R_q$ 上的加法（模 $q$）。
- 右边将加法结果直接展开为三项和，这假设了加法不引起模溢出。
- 对于CKKS，密文加法确实是在 $R_q$ 上进行的，但展开式成立的前提是 $ct_{i,j}^{(t)}$ 确实具有 $[a^{(t)} s_i + \tilde{p} e + m]_q$ 的形式。
- 这再次依赖于ESAFL加密，而非标准MK-CKKS。

### 4.2 🟡 公式(15)的 $a^{(t)}$ 定义

$$C_{pre,j}^{(t)} = \sum_{r=0}^{R-1} C_j^{(t+r)} = [a^{(t)} S + \tilde{p} \sum_{r,i} m_{i,j}^{(t+r)} + E_{pre}^{(t)}]_q$$

其中定义 $(a^{(t)}) = \sum_{r=0}^{R-1} a^{(t+r)}$。

**问题**：
- 若 $a^{(t)} = \text{PRPG}(t, B)$，则 $(a^{(t)})$ 不是任何轮次的合法PRPG输出。
- 解密时需要 $(a^{(t)}) \cdot S$，但 $(a^{(t)})$ 是一个和，不是单个多项式。
- 虽然代数上 $[\sum C_j]_q = [\sum (a^{(t+r)} S + ...)]_q = [(\sum a^{(t+r)}) S + ...]_q$，但这对模运算成立的前提是中间结果不溢出。

### 4.3 🟢 公式(19)缺少 $s_i$

$$ct_{i,j,1} = [-a_t + \tilde{p} \cdot e_1]_q$$

**问题**：这是标准CKKS的公钥分量，与客户端密钥 $s_i$ 无关。但论文声称这是"client encryption scheme"，每个客户端有独立的 $s_i$。如果 $ct_1$ 不包含 $s_i$ 相关的信息，那么密文就不绑定到特定客户端，多密钥聚合的动机被削弱。

---

## 五、严重程度汇总

| 问题类别 | 🔴 严重 | 🟡 中度 | 🟢 轻微 | 合计 |
|----------|--------|--------|--------|------|
| 符号不一致 | 1 | 4 | 1 | 6 |
| 定义不清 | 2 | 3 | 1 | 6 |
| 逻辑不连贯 | 3 | 3 | 3 | 9 |
| 数学正确性 | 0 | 2 | 1 | 3 |
| **合计** | **6** | **12** | **6** | **24** |

---

## 六、优先修正建议

### 必须立即修正（P0 - 阻断性）
1. **统一加密方案**：选择ESAFL/ESHE或标准CKKS，删除所有矛盾的公式。
2. **修正模型更新方向**：明确预取增量是加法还是减法，确保 $w_{sync} = w_{global}$。
3. **解决KGC离线矛盾**：明确补偿密文的来源和生成方式。
4. **补充噪声分析**：给出完整的噪声增长模型和最大prefetch窗口。

### 强烈建议修正（P1 - 高优先级）
5. **统一符号体系**：$t$ vs $r$，$J$ vs $P$ vs $B$，$S_t$ vs $S(t)$。
6. **定义One-shot Decryption**：给出算法伪代码和实际复杂度。
7. **修正聚合权重**：要么实现加权聚合，要么明确说明使用简单平均。
8. **修正Hash验证逻辑**：当前设计无法防御恶意服务器。

### 建议修正（P2 - 中优先级）
9. **修正Algorithm 1的投票阈值**：$|S(t)|$ → $\tau \cdot |S(t)|$。
10. **统一数据声明**：22× vs 8× vs 78×。
11. **删除或补充CRTStack相关内容**。
12. **完成未闭合的Section引用**（"Section ??"）。

---

*审查完成时间：2026-05-26*  
*审查者：Kimi Code CLI*  
*审查范围：firset_paper.pdf Chapter I – Chapter V*
