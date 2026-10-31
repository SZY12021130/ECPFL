# CipherFetch 四篇论文完整方案设计文档

> 基于四个核心方向：①框架完备性 ②公式闭环性 ③安全性 ④通信开销优化
> 每篇独立成文，形成完整的方案体系

---

# 第一篇：框架完备性 —— Threshold-CipherFetch: A Complete Framework for Privacy-Preserving Federated Learning with Ciphertext Prefetching

## 1.1 解决的问题

现有CKKS-FL框架存在以下完备性缺陷：
1. **密钥管理缺失**：单密钥由服务器生成并持有私钥，服务器可解密任意密文
2. **解密权限集中**：缺乏分布式解密机制，单点故障/泄露即全局崩溃
3. **掉线处理缺失**：客户端掉线后无恢复机制，预取状态无法验证
4. **前向安全缺失**：密钥泄露后历史密文不再安全
5. **系统角色模糊**：缺乏清晰的实体功能边界和信任假设

## 1.2 系统架构与实体定义

### 1.2.1 实体定义

| 实体 | 符号 | 功能 | 信任假设 | 持有密钥 |
|------|------|------|----------|----------|
| **密钥生成中心** | KGC | 初始化阈值密钥生成，分发公钥和私钥份额 | 初始化后离线，半诚实 | 不持有任何长期密钥 |
| **聚合服务器** | AS | 收集密文更新，执行同态聚合，生成并广播预取delta | 不可信（可恶意） | 仅聚合公钥 $pk_{agg}$，**无私钥** |
| **客户端** | $C_i, i \in [n]$ | 本地训练，加密上传，接收预取delta，执行阈值解密 | 半诚实（遵循协议但试图推断信息） | 私钥份额 $sk_i$ |
| **辅助节点** | $AN_j, j \in [m]$ | 协助阈值解密，执行部分解密 | 半诚实，最多 $t-1$ 个共谋 | 私钥份额 $sk_j$（可选） |
| **见证节点** | $WN_k, k \in [w]$ | 验证预取delta的正确性，生成签名 | 半诚实，最多 $t-1$ 个共谋 | 签名私钥份额 |

### 1.2.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Threshold-CipherFetch 系统架构                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐                                                             │
│   │   KGC    │  (初始化阶段活跃，生成阈值密钥后永久离线)                       │
│   │密钥生成中心│                                                             │
│   └────┬─────┘                                                             │
│        │ 分发 (pk_agg, {sk_i})                                              │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                         聚合服务器 AS                             │       │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │       │
│   │  │ 同态聚合引擎 │  │ 预取调度器   │  │ 密文Delta历史缓存        │  │       │
│   │  │ Enc-Aggregate│  │ Prefetch    │  │ Encrypted Delta History │  │       │
│   │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │       │
│   │                                                              │       │
│   │  持有：pk_agg（仅聚合公钥，无解密能力）                             │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│        ▲                          ▲                                         │
│        │ 密文梯度上传               │ 密文Delta预取广播                        │
│        │                          ▼                                         │
│   ┌────┴──────────────────────────────────────────────────────────┐        │
│   │                      客户端集群 C_1 ... C_n                      │        │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │        │
│   │  │本地训练   │  │CKKS加密  │  │密文预取   │  │阈值解密(部分解密)│   │        │
│   │  │Local    │  │Encrypt  │  │Prefetch  │  │Partial Decrypt │   │        │
│   │  │Training │  │(pk_agg) │  │Cache     │  │+ Combine       │   │        │
│   │  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘   │        │
│   │                                                                │        │
│   │  持有：sk_i（私钥份额，仅部分解密能力）                              │        │
│   └────────────────────────────────────────────────────────────────┘        │
│        │                                                                     │
│        │ 部分解密份额交换                                                      │
│        ▼                                                                     │
│   ┌────────────────────────────────────────────────────────────────┐        │
│   │              辅助/见证节点集群 AN/WN_1 ... AN/WN_m                 │        │
│   │         (执行部分解密 + 预取Delta签名认证)                          │        │
│   └────────────────────────────────────────────────────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.3 实体交互时序

### 1.3.1 初始化阶段

```
┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐     ┌─────────┐
│ KGC │     │ AS  │     │ C_i │     │ AN_j│     │  WN_k   │
└──┬──┘     └──┬──┘     └──┬──┘     └──┬──┘     └────┬────┘
   │           │           │           │             │
   │  (1) ThresholdKeyGen(λ, n, t)                     │
   │───────────────────────────────────────────────────│
   │           │           │           │             │
   │  (2) 分发 pk_agg, evk ──────►│           │             │
   │  (3) 分发 sk_i ─────────────►│           │             │
   │  (4) 分发 sk_j ───────────────────────►│             │
   │  (5) 分发签名份额 ─────────────────────────────────────►│
   │           │           │           │             │
   │◄──────────(6) 确认接收───────────────────────────────│
   │           │           │           │             │
   │  (7) KGC 永久离线                                   │
   │           │           │           │             │
```

### 1.3.2 每轮训练阶段

```
Round t:

┌─────┐     ┌─────┐     ┌─────┐     ┌─────────┐
│ AS  │     │ C_i │     │ C_j │     │  WN_k   │
└──┬──┘     └──┬──┘     └──┬──┘     └────┬────┘
   │           │           │             │
   │◄─────────(1) 密文梯度上传 ct_i      │           │             │
   │           │           │             │
   │  (2) 同态聚合 ct_agg = Σ w_i · ct_i  │           │             │
   │           │           │             │
   │  (3) 生成密文delta: δ^{(t)} = ct_agg^{(t)} - ct_agg^{(t-1)}      │
   │           │           │             │
   │──────────►(4) 请求见证签名 h = H(δ^{(t)})                         │
   │           │           │◄────────────(5) 生成签名 σ_k              │
   │           │           │             │
   │◄──────────(6) 聚合签名 Σ = Combine({σ_k})                        │
   │           │           │             │
   │  (7) 预取调度：选择目标客户端集合 PrefSet_t                       │
   │           │           │             │
   │──────────►(8) 广播 (δ^{(t)}, Σ, round_t) 给未选中客户端          │
   │           │           │             │
   │           │  (9) 验证签名 Verify(Σ, pk_WN)                        │
   │           │  (10) 若有效：ct_prefetch += δ^{(t)}                  │
   │           │  (11) 若无效：丢弃并标记                              │
   │           │           │             │
   │◄─────────(12) 选中客户端上传更新 ct_selected                     │
   │           │           │             │
   │  (13) 更新全局模型，生成新ct_agg                                   │
   │           │           │             │
   │──────────►(14) 向选中客户端广播最新全局模型（密文）               │
   │           │           │             │
   │           │  (15) Fetch补齐 + 阈值解密 → 明文模型                 │
   │           │  (16) 本地训练下一轮                                   │
   │           │           │             │
```

### 1.3.3 阈值解密阶段

```
客户端 C_i 需要解密时：

┌─────┐     ┌─────┐     ┌─────┐     ┌─────┐
│ C_i │     │AN_j1│     │AN_j2│     │AN_jt│
└──┬──┘     └──┬──┘     └──┬──┘     └──┬──┘
   │           │           │           │
   │─(1) 发送密文 ct 和 解密请求─────────►│           │           │
   │           │           │           │
   │◄────────(2) 部分解密份额 D_j1───────│           │           │
   │◄────────────────────(3) D_j2───────│           │
   │◄───────────────────────────────────(4) D_jt    │
   │           │           │           │
   │  (5) 组合解密：m = Combine({D_jk})              │
   │           │           │           │
   │  (6) 解码并应用模型更新                          │
   │           │           │           │
```

## 1.4 核心协议流程

### 算法1：Threshold-CipherFetch 初始化

```
输入：安全参数 λ，客户端数量 n，阈值 t，训练轮数 T
输出：系统参数 params，密钥材料

1. // KGC 执行（仅初始化阶段）
2. (pk_agg, evk, {sk_i}_{i∈[n]}) ← ThresholdCKKS.KeyGen(λ, n, t)
3. 
4. // 公钥和评估密钥分发给所有实体
5. for each client i ∈ [n]:
6.     Send(pk_agg, evk) to Client_i
7. Send(pk_agg, evk) to AS
8. 
9. // 私钥份额分发给客户端（或辅助节点）
10. for each client i ∈ [n]:
11.     Send(sk_i) to Client_i  // 客户端自管私钥份额
12. // 或：Send(sk_i) to AN_i  // 辅助节点托管
13. 
14. // 见证节点密钥分发（用于预取认证）
15. ({vk_WN}, {sk_WN_k}) ← BLS.ThresholdKeyGen(λ, w, t_w)
16. for each witness k ∈ [w]:
17.     Send(sk_WN_k) to WN_k
18. Send(vk_WN) to all clients
19. 
20. // KGC 销毁所有密钥材料并离线
21. KGC.ShredKeys()
22. 
23. return params = (pk_agg, evk, vk_WN)
```

### 算法2：客户端本地训练与加密

```
输入：本地数据集 D_i，当前全局模型密文 ct_global^{(t-1)}（或预取缓存）
输出：加密梯度更新 ct_i^{(t)}

1. // 若存在预取缓存，先解密
2. if ct_prefetch ≠ null:
3.     Δw_prefetch ← ThresholdDecrypt(ct_prefetch, sk_i, {AN_j})
4.     w_local ← ApplyUpdate(w_base, Δw_prefetch)
5.     ct_prefetch ← null
6. else:
7.     w_local ← w_base
8. 
9. // 本地训练
10. w_new ← LocalTrain(D_i, w_local, epochs=E)
11. Δw_i ← w_new - w_local
12. 
13. // 包级稀疏化（可选SRCA模块）
14. (idx_set, Δw_sparse, mask) ← SparseBatches(Δw_i, sparsity_rate)
15. 
16. // CKKS加密（使用聚合公钥）
17. ct_i ← CKKS.Encrypt(pk_agg, Δw_sparse, scale=Δ)
18. 
19. return (ct_i, mask)
```

### 算法3：服务器同态聚合与预取

```
输入：加密更新集合 {(ct_i, mask_i)}_{i∈S_t}，客户端权重 {w_i}
输出：预取delta δ^{(t)}，聚合签名 Σ

1. // 按batch索引分桶聚合
2. for each batch index b:
3.     participants ← {i | mask_i[b] = 1}
4.     if |participants| > 0:
5.         ct_agg[b] ← CKKS.WeightedAvg({ct_i[b]}, {w_i})
6.     else:
7.         ct_agg[b] ← R_global[b]  // 全局残差补偿（SRCA）
8. 
9. // 计算密文delta
10. if t == 0:
11.     δ^{(t)} ← ct_agg  // 第一轮无delta
12. else:
13.     δ^{(t)} ← CKKS.Sub(ct_agg, ct_agg_prev)
14. 
15. // 生成预取认证
16. h ← Hash(δ^{(t)} || round_t || timestamp)
17. {σ_k} ← RequestWitnessSignatures(h, {WN_k})
18. Σ ← BLS.CombineSignatures({σ_k})
19. 
20. // 预取调度
21. PrefSet ← PrefetchScheduler.SelectClients(bandwidth_budget)
22. for each client j ∉ S_t and j ∈ PrefSet:
23.     Send(δ^{(t)}, Σ, metadata) to Client_j
24. 
25. ct_agg_prev ← ct_agg
26. return δ^{(t)}
```

### 算法4：阈值解密

```
输入：密文 ct = (c_0, c_1)，私钥份额 sk_i，辅助节点集合 {AN_j}
输出：明文 m

1. // 客户端计算自身部分解密份额
2. D_i ← sk_i · c_1 + e_smudge  // e_smudge ← χ_smudge 为防噪声泄露的抹除噪声
3. 
4. // 收集其他t-1个份额
5. for each auxiliary node AN_j (j ≠ i):
6.     Send(c, request) to AN_j
7.     D_j ← Receive from AN_j
8. 
9. // 拉格朗日插值组合
10. m ← c_0 + Σ_{j∈T} λ_j · D_j  // λ_j 为拉格朗日系数
11. 
12. // 解码（CKKS rescale）
13. m_plain ← CKKS.Decode(m)
14. 
15. return m_plain
```

## 1.5 威胁模型

| 威胁类型 | 攻击者能力 | 防御目标 | 本框架防护机制 |
|----------|-----------|----------|---------------|
| **恶意服务器** | 可偏离协议，发送伪造delta，解密企图 | 服务器无法获知任何明文梯度 | 无私钥+预取证验证+阈值解密 |
| **半诚实客户端** | 遵循协议但试图推断其他客户端数据 | 单客户端无法解密 | 阈值t-out-of-n，需t个份额 |
| **客户端共谋** | ≤ t-1个客户端共享私钥份额 | 保护诚实客户端隐私 | Shamir共享的(t-1)-隐私性 |
| **服务器+客户端共谋** | 服务器+t-1个客户端联合 | 诚实客户端梯度机密性 | 辅助节点独立持份，服务器无份 |
| **预取投毒** | 服务器伪造/重放delta | 客户端只接受合法delta | TPW阈值签名+轮次序列验证 |
| **噪声泄露攻击** | 从解密噪声恢复密钥 | 防止IND-CPA-D攻击 | Smudging噪声+噪声刷新 |
| **掉线攻击** | 大规模客户端掉线 | 保证聚合可完成 | 仅需t个节点在线即可解密 |
| **前向安全** | 历史密钥泄露 | 历史密文仍安全 | 周期性密钥更新（可选） |

---

# 第二篇：公式闭环性 —— From RLWE to Threshold-CKKS-FL: A Complete Formalization of Homomorphic Aggregation with Partial Decryption

## 2.1 解决的问题

现有CKKS-FL方案存在以下公式层面的缺陷：
1. **缺乏从RLWE到完整协议的公式链**：多数方案仅罗列CKKS加解密，无阈值扩展
2. **部分解密公式缺失**：分布式解密的数学描述不完整
3. **预取场景噪声模型缺失**：多轮同态累加后的噪声增长无递推公式
4. **安全性证明缺乏形式化**：无基于模拟器的严格安全证明

## 2.2 基础定义与符号

### 2.2.1 数学基础

**定义2.1（分圆多项式环）**：
设 $N = 2^k$ 为2的幂次，分圆多项式 $\Phi_{2N}(X) = X^N + 1$。定义环：
$$R = \mathbb{Z}[X]/(X^N + 1), \quad R_q = R/qR$$

**定义2.2（RLWE分布）**：
对于 $a \leftarrow U(R_q)$, $s \leftarrow \chi_{key}$, $e \leftarrow \chi_{err}$，RLWE样本为 $(a, b = a \cdot s + e \mod q)$。

**决策性RLWE假设**：区分 $(a, a \cdot s + e)$ 与 $(a, u)$（$u$ 均匀随机）是困难的。

**定义2.3（离散高斯分布）**：
$$D_{R,\sigma}(x) \propto \exp(-\pi \|x\|^2/\sigma^2)$$

### 2.2.2 符号表

| 符号 | 含义 |
|------|------|
| $N$ | 环维度（多项式次数） |
| $L$ | 乘法深度（模数链层数） |
| $q_0 < q_1 < ... < q_L$ | 模数链 |
| $\Delta = 2^p$ | 缩放因子 |
| $\chi_{key}$ | 密钥采样分布（通常为 $HWT(h)$，汉明重量为h的稀疏分布） |
| $\chi_{err}$ | 误差采样分布（$D_{R,\sigma}$） |
| $\chi_{enc}$ | 加密随机性分布 |
| $\|e\|_{can}$ | 规范嵌入范数（Canonical Embedding Norm） |
| $\lfloor \cdot \rceil$ | 舍入到最近整数 |

## 2.3 CKKS基础算法公式

### 2.3.1 密钥生成

**算法2.1（CKKS.KeyGen）**：

输入：安全参数 $\lambda$，环维度 $N$，模数链 $\{q_0, ..., q_L\}$
输出：私钥 $sk$，公钥 $pk$，评估密钥 $evk$

$$
\begin{aligned}
1.& \quad s \leftarrow \chi_{key} \\
2.& \quad a \leftarrow U(R_{q_L}) \\
3.& \quad e \leftarrow \chi_{err} \\
4.& \quad b = -a \cdot s + e \pmod{q_L} \\
5.& \quad pk = (b, a) \\
6.& \quad evk = \text{SwitchKeyGen}(s^2, s) \\
7.& \quad \text{return } (s, pk, evk)
\end{aligned}
$$

### 2.3.2 编码与加密

**算法2.2（CKKS.Encode）**：

输入：消息向量 $z \in \mathbb{C}^{N/2}$，缩放因子 $\Delta$
输出：明文多项式 $m \in R$

$$
\begin{aligned}
1.& \quad \pi^{-1}(z) \in \mathbb{C}^N \text{（共轭对称扩展）} \\
2.& \quad m' = \lfloor \Delta \cdot \sigma^{-1}(\pi^{-1}(z)) \rceil \in R \\
3.& \quad m = m' \mod q_L \\
4.& \quad \text{return } m
\end{aligned}
$$

其中 $\sigma: R \to \mathbb{C}^N$ 为规范嵌入（复数域FFT），$\pi^{-1}$ 为逆蝶形变换。

**算法2.3（CKKS.Encrypt）**：

输入：公钥 $pk = (b, a)$，明文 $m \in R_{q_L}$
输出：密文 $ct = (c_0, c_1) \in R_{q_L}^2$

$$
\begin{aligned}
1.& \quad v \leftarrow \chi_{enc} \\
2.& \quad e_0, e_1 \leftarrow \chi_{err} \\
3.& \quad c_0 = b \cdot v + e_0 + m \pmod{q_L} \\
4.& \quad c_1 = a \cdot v + e_1 \pmod{q_L} \\
5.& \quad \text{return } (c_0, c_1)
\end{aligned}
$$

**解密正确性**：

$$
\begin{aligned}
c_0 + c_1 \cdot s &= (bv + e_0 + m) + (av + e_1)s \\
&= (-as + e)v + e_0 + m + avs + e_1 s \\
&= m + ev + e_0 + e_1 s \pmod{q_L}
\end{aligned}
$$

噪声定义为：$e_{noise} = ev + e_0 + e_1 s$

### 2.3.3 同态运算

**加法**：
$$ct_{add} = (c_{0,1} + c_{0,2}, \; c_{1,1} + c_{1,2})$$

**标量乘法**：
$$ct_{scalar} = (\alpha \cdot c_0, \; \alpha \cdot c_1)$$

**乘法（含重线性化）**：
$$ct_{mult} = (c_{0,1}c_{0,2}, \; c_{0,1}c_{1,2} + c_{1,1}c_{0,2}, \; c_{1,1}c_{1,2}) \xrightarrow{evk} (d_0, d_1)$$

乘法后噪声：$\|e_{mult}\|_{can} \leq C_1 \cdot \|e_1\| \cdot \|e_2\| + C_2 \cdot (\|e_1\| + \|e_2\|) + C_3$

## 2.4 阈值CKKS公式体系

### 2.4.1 分布式密钥生成

**算法2.4（ThresholdCKKS.KeyGen）**：

基于Mouchet et al.的阈值CKKS协议，使用Shamir秘密共享。

输入：安全参数 $\lambda$，参与者数 $n$，阈值 $t$
输出：聚合公钥 $pk_{agg}$，评估密钥 $evk$，私钥份额 $\{sk_i\}_{i \in [n]}$

$$
\begin{aligned}
1.& \quad \text{Each participant } i \in [n] \text{ samples:} \\
2.& \quad s_i \leftarrow \chi_{key}, \quad a_i \leftarrow U(R_{q_L}), \quad e_i \leftarrow \chi_{err} \\
3.& \quad b_i = -a_i \cdot s_i + e_i \pmod{q_L} \\
4.& \quad \text{Participants jointly compute } a_{agg} = \sum_{i=1}^n a_i \\
5.& \quad \text{Each participant computes share of } b_{agg}: \\
6.& \quad b_{agg} = \sum_{i=1}^n (-a_{agg} \cdot s_i + e_i) = -a_{agg} \cdot s_{agg} + e_{agg} \\
7.& \quad \text{where } s_{agg} = \sum_{i=1}^n s_i, \quad e_{agg} = \sum_{i=1}^n e_i \\
8.& \quad pk_{agg} = (b_{agg}, a_{agg}) \\
9.& \quad sk_i = s_i \text{（ participant } i \text{'s secret share）} \\
10.& \quad evk = \text{JointSwitchKeyGen}(\{s_i^2\}, \{s_i\}) \\
11.& \quad \text{return } (pk_{agg}, evk, \{sk_i\})
\end{aligned}
$$

**注意**：实际实现中，$a_{agg}$ 可由任一参与者生成并广播，因为 $a$ 是公共参数。

### 2.4.2 阈值加密

**算法2.5（ThresholdCKKS.Encrypt）**：

使用聚合公钥加密，与标准CKKS加密形式相同：

$$
\begin{aligned}
1.& \quad v \leftarrow \chi_{enc}, \quad e_0, e_1 \leftarrow \chi_{err} \\
2.& \quad c_0 = b_{agg} \cdot v + e_0 + m \pmod{q_L} \\
3.& \quad c_1 = a_{agg} \cdot v + e_1 \pmod{q_L} \\
4.& \quad \text{return } (c_0, c_1)
\end{aligned}
$$

**解密结构**：
$$c_0 + c_1 \cdot s_{agg} = m + e_{noise}$$

其中 $s_{agg} = \sum_{i=1}^n s_i$ 为完整私钥，但**没有任何单一实体持有 $s_{agg}$**。

### 2.4.3 部分解密（核心创新公式）

**算法2.6（ThresholdCKKS.PartialDec）**：

输入：密文 $ct = (c_0, c_1)$，私钥份额 $sk_i = s_i$，随机数 $\rho_i$
输出：部分解密份额 $D_i$

$$
\begin{aligned}
1.& \quad e_{smudge} \leftarrow D_{R, \sigma_{smudge}} \quad \text{// Smudging噪声} \\
2.& \quad D_i = s_i \cdot c_1 + e_{smudge} \pmod{q_l} \\
3.& \quad \text{return } D_i
\end{aligned}
$$

**Smudging噪声的大小**：
为达到统计安全参数 $s$，需要：
$$\sigma_{smudge} \geq 2^s \cdot \|e_{noise}\|_{can}$$

实践中，PALISADE使用 $s = 20$（20比特统计安全），Lattigo使用类似参数。

**算法2.7（ThresholdCKKS.Combine）**：

输入：密文 $ct = (c_0, c_1)$，t个部分解密份额 $\{D_j\}_{j \in T}$，其中 $|T| = t$
输出：明文近似值 $\tilde{m}$

$$
\begin{aligned}
1.& \quad \text{For each } j \in T, \text{ compute Lagrange coefficient:} \\
2.& \quad \lambda_j = \prod_{k \in T, k \neq j} \frac{-k}{j - k} \pmod{q_l} \\
3.& \quad \text{// 在Shamir共享中，} s_{agg} = \sum_{j \in T} \lambda_j \cdot s_j \\
4.& \quad m_{combined} = c_0 + \sum_{j \in T} \lambda_j \cdot D_j \pmod{q_l} \\
5.& \quad \tilde{m} = \text{CKKS.Decode}(m_{combined}) \\
6.& \quad \text{return } \tilde{m}
\end{aligned}
$$

**组合正确性验证**：

$$
\begin{aligned}
m_{combined} &= c_0 + \sum_{j \in T} \lambda_j \cdot (s_j \cdot c_1 + e_{smudge,j}) \\
&= c_0 + c_1 \cdot \sum_{j \in T} \lambda_j s_j + \sum_{j \in T} \lambda_j e_{smudge,j} \\
&= c_0 + c_1 \cdot s_{agg} + e_{total\_smudge} \\
&= m + e_{noise} + e_{total\_smudge}
\end{aligned}
$$

其中 $e_{total\_smudge} = \sum_{j \in T} \lambda_j e_{smudge,j}$ 为组合后的总smudging噪声。

### 2.4.4 同态聚合公式（联邦学习场景）

设 $n$ 个客户端，第 $i$ 个客户端上传密文 $ct_i = (c_{i,0}, c_{i,1})$，数据量权重 $w_i = |D_i|/|D_{total}|$。

**加权平均聚合**：

$$
\begin{aligned}
ct_{agg} &= \sum_{i=1}^n w_i \cdot ct_i \\
&= \left(\sum_{i=1}^n w_i c_{i,0}, \; \sum_{i=1}^n w_i c_{i,1}\right) \\
&= \left(\sum_i w_i(b_{agg}v_i + e_{i,0} + m_i), \; \sum_i w_i(a_{agg}v_i + e_{i,1})\right) \\
&= \left(b_{agg}\sum_i w_i v_i + \sum_i w_i e_{i,0} + \sum_i w_i m_i, \; a_{agg}\sum_i w_i v_i + \sum_i w_i e_{i,1}\right)
\end{aligned}
$$

设 $v_{agg} = \sum_i w_i v_i$，$e_{agg,0} = \sum_i w_i e_{i,0}$，$e_{agg,1} = \sum_i w_i e_{i,1}$，$m_{agg} = \sum_i w_i m_i$：

$$ct_{agg} = (b_{agg} v_{agg} + e_{agg,0} + m_{agg}, \; a_{agg} v_{agg} + e_{agg,1})$$

**聚合噪声分析**：

$$
\|e_{agg}\|_{can} = \|e_{agg,0} + e_{agg,1} \cdot s_{agg}\|_{can} \leq \sum_i w_i \|e_{i,0} + e_{i,1} \cdot s_{agg}\|_{can}$$

由于 $\sum_i w_i = 1$ 且噪声独立：

$$\mathbb{E}[\|e_{agg}\|^2] \leq \sum_i w_i^2 \cdot \mathbb{E}[\|e_i\|^2]$$

**关键结论**：加权聚合后的噪声方差按 $w_i^2$ 加权，当客户端数据均衡时（$w_i \approx 1/n$），噪声方差降低约 $n$ 倍。

### 2.4.5 密文预取噪声递推公式（核心创新）

**问题**：客户端在 $r$ 轮内收到预取delta并同态累加，噪声如何增长？

设第 $k$ 轮的delta为 $\delta^{(k)}$，客户端累积密文为：

$$ct_{prefetch}^{(t)} = \sum_{k=s}^t \delta^{(k)}$$

每个 $\delta^{(k)} = ct_{agg}^{(k)} - ct_{agg}^{(k-1)}$ 的噪声为 $e_{\delta}^{(k)}$。

**引理2.8（预取累积噪声上界）**：
经过 $r$ 轮预取累积后的总噪声满足：

$$\|e_{prefetch}^{(t)}\|_{can} \leq \sum_{k=s}^t \|e_{\delta}^{(k)}\|_{can} + \sum_{k=s}^{t-1} \|e_{carry}^{(k)}\|_{can}$$

其中 $e_{carry}^{(k)}$ 为模数切换（rescaling）引入的携带噪声。

**定理2.9（预取场景噪声预算）**：
设每轮delta噪声上界为 $B_{\delta}$，预取窗口为 $R$ 轮，则累积噪声上界为：

$$\|e_{prefetch}\|_{can} \leq R \cdot B_{\delta} + (R-1) \cdot B_{rescale}$$

为保证解密正确，需要：

$$\log_2(R \cdot B_{\delta} + (R-1) \cdot B_{rescale}) + s_{smudge} < \log_2(q_l)$$

其中 $q_l$ 为当前层级模数，$s_{smudge}$ 为smudging噪声的比特数。

**Bootstrapping触发条件**：
当噪声预算低于阈值 $\theta_{boot}$ 时触发：

$$\text{Budget}(ct) = \log_2(q_l) - \log_2(\|e\|_{can} \cdot \sqrt{N}) - s_{smudge} < \theta_{boot}$$

**预取优化策略**：
- 缩短预取窗口 $R$（减少累积噪声）
- 定期重置预取缓存（客户端主动同步，清空累积噪声）
- 自适应调整：根据当前噪声预算动态调整 $R$

## 2.5 安全证明框架

### 2.5.1 安全定义

**定义2.10（阈值语义安全）**：
阈值CKKS方案满足 $(t, n)$-语义安全，如果对于任意PPT敌手 $\mathcal{A}$ 腐蚀最多 $t-1$ 个参与者：

$$|\Pr[\text{Exp}_{\mathcal{A}}^{IND}(\lambda) = 1] - \frac{1}{2}| \leq \text{negl}(\lambda)$$

### 2.5.2 模拟器构造

**定理2.11（Threshold-CipherFetch半诚实安全）**：
在决策性RLWE假设下，Threshold-CipherFetch协议满足半诚实安全。

**证明概要**：

1. **密钥生成阶段**：模拟器 $\mathcal{S}$ 生成 $(pk', \{sk'_i\})$ 替换真实密钥。由RLWE假设，$pk'$ 与真实 $pk_{agg}$ 计算不可区分。

2. **加密阶段**：对于诚实客户端，$\mathcal{S}$ 用全零消息加密；对于腐败客户端，用真实消息。由CKKS的IND-CPA安全，二者不可区分。

3. **聚合阶段**：同态聚合仅涉及密文运算，不引入额外信息。

4. **部分解密阶段**：对于诚实参与者的部分解密份额，$\mathcal{S}$ 生成随机 $D_j^*$。由smudging噪声的统计安全性，真实 $D_j$ 与随机值统计不可区分。

5. **预取阶段**：预取delta为密文，敌手视图与真实协议一致。

---

# 第三篇：安全性 —— Secure Prefetch: Defending Against Poisoning and Forgery in Ciphertext Prefetching for Federated Learning

## 3.1 解决的问题

密文预取引入的全新安全挑战：
1. **Delta完整性**：客户端如何验证收到的预取delta未被篡改？
2. **Delta新鲜性**：如何防止旧delta被重放？
3. **服务器作恶**：恶意服务器可定向投毒特定客户端
4. **不可抵赖性**：如何追踪伪造delta的责任方？

## 3.2 威胁模型

### 3.2.1 攻击者能力

| 攻击者 | 能力 | 目标 |
|--------|------|------|
| **恶意服务器** | 可伪造/篡改/选择性广播delta；可解密尝试（但无私钥） | 破坏模型收敛或推断客户端隐私 |
| **中间人** | 可拦截/修改预取通道通信 | 重放或篡改delta |
| **恶意客户端** | 可发送虚假梯度；可尝试伪造其他客户端预取 | 污染全局模型 |
| **服务器+客户端联盟** | 联合攻击特定目标客户端 | 定向隐私泄露或模型破坏 |

### 3.2.2 安全目标

1. **Delta认证性（Authenticity）**：每个delta可验证其来源和完整性
2. **Delta新鲜性（Freshness）**：防止重放攻击
3. **不可伪造性（Unforgeability）**：无足够见证节点无法伪造合法delta
4. **可追溯性（Accountability）**：可追踪恶意delta到责任服务器/节点

## 3.3 攻击向量详细分析

### 3.3.1 攻击1：选择性Delta伪造（Selective Delta Forging）

**攻击流程**：
```
服务器维护两套delta：
  - δ_correct：正确的聚合delta
  - δ_malicious = δ_correct + Δpoison：加入投毒偏移

Round t:
  for client in selected_clients:
    发送 δ_correct（保证全局聚合正确）
  for client in target_clients:
    发送 δ_malicious（定向投毒）
```

**检测难度**：由于delta是密文，目标客户端无法预知正确内容，投毒隐蔽。

### 3.3.2 攻击2：Delta重放（Delta Replay）

**攻击流程**：
```
攻击者记录Round t的delta: δ^{(t)}
在Round t+k 重放 δ^{(t)} 给特定客户端

客户端累积：ct_prefetch += δ^{(t)}（过期delta）
结果：客户端模型回退到t轮状态
```

### 3.3.3 攻击3：Delta放大（Delta Amplification）

**攻击流程**：
```
服务器将delta乘以放大系数 α > 1：
  δ^{(t)*} = α · δ^{(t)}  （同态标量乘）

客户端累积后，相当于被施加了Scaled更新
长期累积导致模型发散或偏向特定方向
```

### 3.3.4 攻击4：预取缓存污染（Prefetch Cache Pollution）

**攻击流程**：
```
攻击者向客户端发送大量伪造delta填充其预取缓存
当客户端被选中时，解密应用累积的污染delta
即使单个delta影响小，累积效应显著
```

## 3.4 防御方案

### 3.4.1 方案A：Threshold Prefetch Witness (TPW)

#### 设计原理
引入 $w$ 个见证节点，采用 $(t_w, w)$-阈值签名。每个delta需获得至少 $t_w$ 个见证节点的签名才能被客户端接受。

#### 数学构造

**BLS阈值签名**：

设 $\mathbb{G}_1, \mathbb{G}_2, \mathbb{G}_T$ 为双线性映射群，$e: \mathbb{G}_1 \times \mathbb{G}_2 \to \mathbb{G}_T$。

**密钥生成**：
$$
\begin{aligned}
& \text{Master secret: } x \leftarrow \mathbb{Z}_p \\
& \text{Master public key: } PK = g_2^x \in \mathbb{G}_2 \\
& \text{Share for node } i: sk_i = x \cdot f(i) \text{ where } f \text{ is degree } t_w-1 \text{ polynomial} \\
& \text{Verification key for node } i: VK_i = g_2^{sk_i}
\end{aligned}
$$

**签名**：
见证节点 $i$ 对消息 $M$（delta的哈希）签名：
$$\sigma_i = H(M)^{sk_i} \in \mathbb{G}_1$$

**聚合**：
服务器收集 $t_w$ 个签名份额，使用拉格朗日插值聚合：
$$\Sigma = \prod_{i \in T} \sigma_i^{\lambda_i} = H(M)^{\sum \lambda_i sk_i} = H(M)^x$$

其中 $\lambda_i$ 为拉格朗日系数。

**验证**：
客户端验证：
$$e(\Sigma, g_2) \stackrel{?}{=} e(H(M), PK)$$

#### 完整协议

```
算法 TPW_Generate
输入：delta δ^{(t)}, 轮次 r, 时间戳 τ
输出：聚合签名 Σ

1. h ← SHA256(δ^{(t)}.serialize() || r || τ || pk_agg)
2. for each witness node WN_k:
3.     Send(h) to WN_k
4.     σ_k ← Receive from WN_k  // σ_k = H(h)^{sk_k}
5. Σ ← BLS.Combine({σ_k}_{k∈T}, |T| = t_w)
6. return (Σ, r, τ)

算法 TPW_Verify
输入：delta δ, 签名 Σ, 轮次 r, 时间戳 τ, 公钥 PK
输出：True/False

1. h ← SHA256(δ.serialize() || r || τ || pk_agg)
2. if e(Σ, g_2) == e(H(h), PK):
3.     if r > last_accepted_round:  // 防重放
4.         return True
5. return False
```

#### 安全性分析

**定理3.1（TPW不可伪造性）**：在CDH假设下，没有 $t_w$ 个见证节点共谋，敌手无法伪造有效签名。

**证明概要**：
- BLS签名的安全性基于CDH假设
- 阈值BLS需要 $t_w$ 个份额才能重构完整私钥 $x$
- 仅 $t_w-1$ 个份额无法生成有效签名（由Shamir共享的 $(t_w-1)$-隐私性）

### 3.4.2 方案B：Authenticated Ciphertext Delta (ACD)

#### 设计原理
对每个delta附加一个轻量级的认证标签，客户端解密后验证。

#### 数学构造

使用AES-GCM认证加密：

$$
\begin{aligned}
& \text{Shared key: } k_{auth} \text{ (derived from DH key exchange)} \\
& \text{For delta } \delta^{(t)} \text{ with plaintext } m^{(t)}: \\
& \quad h^{(t)} = \text{SHA256}(m^{(t)}) \\
& \quad (c_{tag}^{(t)}, tag) = \text{AES-GCM}_{k_{auth}}(h^{(t)}, nonce_t) \\
& \text{Broadcast: } (\delta^{(t)}, c_{tag}^{(t)}, nonce_t)
\end{aligned}
$$

客户端验证：
$$
\begin{aligned}
& m' = \text{Decrypt}(\delta^{(t)}) \\
& h' = \text{SHA256}(m') \\
& \text{Verify AES-GCM}_{k_{auth}}(c_{tag}^{(t)}, tag, nonce_t) \stackrel{?}{=} h'
\end{aligned}
$$

#### 优缺点
- **优点**：实现简单，计算高效
- **缺点**：需解密后才能验证；密钥分发需安全通道

### 3.4.3 方案C：Zero-Knowledge Prefetch Proof (ZKPP)

#### 设计原理
服务器生成zk-SNARK证明，证明delta确实是对应明文差值的正确加密，客户端无需解密即可验证。

#### 证明关系

**公共输入**：
- $pk_{agg} = (b_{agg}, a_{agg})$
- $h_{old} = \text{Commit}(w^{(t-1)})$
- $h_{new} = \text{Commit}(w^{(t)})$
- $\delta^{(t)} = (c_0, c_1)$

**私密输入（witness）**：
- $w^{(t)}, w^{(t-1)}$
- 加密随机数 $v, e_0, e_1$
- 聚合权重和客户端更新

**约束**：
$$
\begin{aligned}
& c_0 = b_{agg} \cdot v + e_0 + (w^{(t)} - w^{(t-1)}) \\
& c_1 = a_{agg} \cdot v + e_1 \\
& w^{(t)} = \sum_i w_i \cdot w_i^{(local)} \\
& \|e_0\|, \|e_1\| \leq B_{err}
\end{aligned}
$$

#### 实践建议
由于ZK-SNARK生成开销高，采用**延迟验证**：
- 每 $k$ 轮（如 $k=5$）生成一个聚合ZK证明
- 客户端定期验证，异常时触发回滚

## 3.5 组合安全策略

| 威胁 | TPW | ACD | ZKPP | 推荐组合 |
|------|-----|-----|------|---------|
| 伪造delta | ✅ | ✅ | ✅ | TPW（即时阻止） |
| 重放攻击 | ✅(轮次检查) | ⚠️ | ✅ | TPW+轮次序列号 |
| 放大攻击 | ⚠️ | ✅ | ✅ | ZKPP（验证约束） |
| 选择性投毒 | ✅ | ⚠️ | ✅ | TPW+ZKPP |
| 缓存污染 | ✅ | ✅ | ✅ | 全组合 |

---

# 第四篇：通信开销优化 —— Residual-Aware Sparse Ciphertext Prefetching: Minimizing Communication in Encrypted Federated Learning

## 4.1 解决的问题

1. **密文膨胀**：CKKS密文是明文的10-100倍，通信瓶颈严重
2. **稀疏化信息丢失**：包级稀疏化丢弃70%信息（30%稀疏率时）
3. **预取冗余**：预取delta可能包含客户端已同步的信息
4. **上下行不对称**：上行（客户端→服务器）和下行（服务器→客户端）优化策略不同

## 4.2 核心设计：RS2CP (Residual-aware Sparse Secure Ciphertext Prefetching)

### 4.2.1 三层优化架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    RS2CP 三层通信优化架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 3: 语义优化（应用层）                                     │
│  ├─ 残差累积 SRCA：避免信息丢失，允许更高稀疏率                    │
│  ├─ 自适应稀疏率：根据训练阶段动态调整                             │
│  └─ 重要性感知选择：优先传输变化大的参数                           │
│                                                                 │
│  Layer 2: 编码优化（表示层）                                     │
│  ├─ 包级稀疏化：仅加密Top-K/Rand-K batch                         │
│  ├─ 量化编码：BatchCrypt风格的低精度编码                          │
│  └─ 差分编码：传输delta而非完整模型                                │
│                                                                 │
│  Layer 1: 传输优化（网络层）                                     │
│  ├─ 密文预取：后台异步传输，降低训练时延                           │
│  ├─ 多delta同态累加：服务器预合并多个delta                        │
│  └─ 带宽感知调度：根据客户端带宽动态调整预取策略                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2.2 SRCA残差累积详解

**动机**：
标准包级稀疏化丢弃未选中batch，导致：
$$\text{信息保留率} = \text{稀疏率} = s$$

SRCA通过残差累积实现：
$$\text{有效信息保留率} \to 100\% \text{（延迟传输）}$$

**客户端算法**：

$$
\begin{aligned}
& \text{Initialize: } r_i^{(0)} = 0 \\
& \text{For each round } t: \\
& \quad g_i^{(t)} = \Delta w_i^{(t)} + \gamma \cdot r_i^{(t-1)} \quad \text{// 合成梯度} \\
& \quad (idx^{(t)}, g_{sparse}^{(t)}) = \text{TopK}(|g_i^{(t)}|, k = s \cdot B) \\
& \quad \text{Upload: } ct_i^{(t)} = \text{Enc}(g_{sparse}^{(t)}) \\
& \quad r_i^{(t)} = g_i^{(t)} - \text{Unsparse}(g_{sparse}^{(t)}, idx^{(t)}) \\
& \quad \text{// 未选中位置保持原值，选中位置置零}
\end{aligned}
$$

**服务器全局残差补偿**：

当某个batch $b$ 在某轮没有任何客户端选中时：
$$ct_{agg}[b] = R_{global}^{(t-1)}[b]$$

全局残差更新：
$$R_{global}^{(t)}[b] = \gamma_R \cdot R_{global}^{(t-1)}[b] + \text{FreshResidual}[b]$$

其中 $\gamma_R \in (0,1)$ 为全局残差衰减率。

### 4.2.3 自适应稀疏率

**训练阶段划分**：

| 阶段 | 轮次范围 | 梯度特征 | 推荐稀疏率 | SRCA衰减率 |
|------|----------|----------|-----------|-----------|
| 预热期 | 0~T/4 | 变化剧烈，噪声容忍高 | 50% | γ=0.95 |
| 稳定期 | T/4~3T/4 | 收敛中，需稳定更新 | 30% | γ=0.90 |
| 精调期 | 3T/4~T | 微调敏感，需高精度 | 15% | γ=0.85 |

### 4.2.4 预取调度优化

**多delta预合并**：

客户端 $j$ 从轮次 $s$ 到 $t$ 缺失的delta，服务器预合并：

$$\Delta_{merged}^{(s,t)} = \sum_{k=s}^t \delta^{(k)}$$

由于同态加法不改变密文大小：
$$|\Delta_{merged}| = |\delta^{(k)}|$$

**带宽感知预取**：

客户端 $j$ 的下行带宽为 $BW_j$，预取预算为 $B$（时间）。

可预取的delta数量：
$$N_j = \left\lfloor \frac{B \cdot BW_j}{|\delta|} \right\rfloor$$

调度策略：
- 若 $N_j \geq t - s$：发送全部缺失delta（合并为1个）
- 若 $N_j < t - s$：发送最近 $N_j$ 轮的合并delta，旧delta留待下次

## 4.3 通信复杂度分析

### 4.3.1 上行通信（客户端→服务器）

**基准方案（无优化）**：
$$U_{baseline} = n \cdot |w| \cdot C_{expansion}$$

其中 $C_{expansion}$ 为密文膨胀系数（CKKS约20-50倍）。

**RS2CP方案**：
$$U_{RS2CP} = n \cdot |w| \cdot s \cdot C_{expansion} \cdot C_{quant}$$

其中 $s$ 为稀疏率，$C_{quant}$ 为量化压缩系数（BatchCrypt约0.3-0.5）。

**优化比**：
$$\text{Ratio}_{upload} = \frac{U_{RS2CP}}{U_{baseline}} = s \cdot C_{quant}$$

当 $s = 0.3$, $C_{quant} = 0.4$ 时：
$$\text{Ratio}_{upload} = 0.12 \quad \text{(约8.3倍压缩)}$$

### 4.3.2 下行通信（服务器→客户端）

**基准方案（无预取）**：
$$D_{baseline} = |S_t| \cdot |w| \cdot C_{expansion}$$

其中 $S_t$ 为每轮选中客户端集合。

**RS2CP方案（有预取）**：

Fetch阶段（被选中时）：
$$D_{fetch} = |S_t| \cdot |w| \cdot s \cdot \alpha_{miss}$$

其中 $\alpha_{miss}$ 为未预取覆盖率（如20%）。

Prefetch阶段（后台）：
$$D_{prefetch} = (n - |S_t|) \cdot |w| \cdot s \cdot p_{prefetch}$$

其中 $p_{prefetch}$ 为预取参与率。

**关键指标**：
- **Training Volume (TV)** = Upload + Fetch（训练时实际等待的流量）
- **Total Volume** = TV + Prefetch（含后台的总流量）

FedFetch论文指出：TV降低约60%，Total增加约12%。

RS2CP在加密场景下的预估：
- TV降低：50-70%（稀疏化+预取）
- Total增加：15-25%（密文预取开销大于明文）

### 4.3.3 虚拟时钟分析

**单轮训练时间**：
$$T_{round} = \max_{i \in S_t} \{T_{fetch}^{(i)} + T_{compute}^{(i)} + T_{upload}^{(i)}\}$$

预取优化后：
$$T_{fetch}^{(i)} = \frac{|\Delta_{missing}| \cdot C_{expansion}}{BW_i^{down}}$$

由于预取覆盖大部分缺失delta：
$$|\Delta_{missing}| \ll |w| \Rightarrow T_{fetch}^{(i)} \approx 0$$

**端到端加速**：
$$\text{Speedup} = \frac{\sum_t T_{round}^{(baseline)}}{\sum_t T_{round}^{(RS2CP)}} \approx 1.3 \sim 2.0$$

## 4.4 实验设计

### 4.4.1 对比基线

| 基线 | 描述 |
|------|------|
| Vanilla-FL | 明文FedAvg，无加密无预取 |
| CKKS-Fed | 标准CKKS加密联邦学习，无预取 |
| BatchCrypt | 量化+批量加密 |
| FedFetch | 明文预取（INFOCOM'25） |
| **RS2CP (本方案)** | 阈值CKKS + SRCA + 密文预取 |

### 4.4.2 评估指标

1. **准确率**：测试集top-1准确率
2. **上行通信量**：总加密上传字节数
3. **下行Fetch量**：训练时实际下载字节数
4. **总通信量**：含预取后台流量的总字节数
5. **端到端时间**：达到目标准确率的wall-clock时间
6. **稀疏率影响**：不同稀疏率下的准确率-通信权衡曲线

### 4.4.3 预期结果

| 指标 | CKKS-Fed | FedFetch(明文) | RS2CP(本方案) |
|------|----------|---------------|--------------|
| MNIST准确率 | 97% | 98% | 97.5% |
| 稀疏率 | 100% | N/A | 30% |
| 上行通信 | 100x | 1x | 12x |
| 下行Fetch | 100x | 15x | 20x |
| 端到端时间 | 100x | 1.3x | 1.5x |

*注：以Vanilla-FL通信量为1x基准*

---

# 附录：四篇文章关系与组合发表策略

## 文章依赖关系

```
文章2（公式闭环）─────┐
                      ├──► 文章1（框架完备性）────► 文章3（安全性）
文章4（通信优化）─────┘         │                        │
                               │                        │
                               └────────► 最终整合论文（可选）
```

## 发表策略建议

| 文章 | 目标会议/期刊 | 优先级 | 理由 |
|------|-------------|--------|------|
| 文章2：公式闭环 | CRYPTO/EUROCRYPT | 高 | 纯密码学贡献，顶会认可度高 |
| 文章3：安全性 | IEEE S&P / NDSS | 高 | 安全协议创新，系统安全顶会 |
| 文章1：框架完备性 | IEEE TDSC | 中 | 系统架构设计，期刊适合长文 |
| 文章4：通信优化 | INFOCOM / SIGMETRICS | 中 | 通信优化，网络顶会 |
| 整合版 | IEEE TIFS | 低（最后做） | 四合一长文，顶级期刊 |

## 代码实现优先级

1. **第一阶段**（2周）：实现文章4的SRCA模块 + 基础预取优化
2. **第二阶段**（2周）：实现文章1的阈值密钥生成 + 部分解密
3. **第三阶段**（2周）：实现文章3的TPW签名验证
4. **第四阶段**（2周）：完善文章2的噪声分析公式 + 实验验证
