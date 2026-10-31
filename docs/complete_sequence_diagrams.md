# 所有方案完整时序图与算法流程

> 本文档包含四篇论文全部方案的详细时序图，每个步骤带序号标识，完整展现算法流程

---

# 目录

1. [第一篇：Threshold-CipherFetch 完整时序图](#第一篇threshold-cipherfetch-完整时序图)
2. [第二篇：阈值CKKS公式闭环 时序图](#第二篇阈值ckks公式闭环-时序图)
3. [第三篇：安全防御方案 时序图](#第三篇安全防御方案-时序图)
4. [第四篇：SRCA通信优化 时序图](#第四篇srca通信优化-时序图)
5. [融合方案：SecureRes-Fetch 总时序图](#融合方案secureres-fetch-总时序图)

---

# 第一篇：Threshold-CipherFetch 完整时序图

## 图1.1 初始化阶段：阈值密钥生成与分发

```
┌─────┐          ┌─────┐          ┌─────┐          ┌─────┐          ┌─────────┐
│ KGC │          │ AS  │          │ C_i │          │ AN_j│          │  WN_k   │
└──┬──┘          └──┬──┘          └──┬──┘          └──┬──┘          └────┬────┘
   │                │                │                │                  │
   │  [1] KGC本地执行 ThresholdCKKS.KeyGen(λ, n, t)                       │
   │  ├── 采样: s_i ← χ_key, a_i ← U(R_qL), e_i ← χ_err                 │
   │  ├── 计算: b_i = -a_i·s_i + e_i                                    │
   │  ├── 聚合: a_agg = Σa_i, b_agg = Σb_i                              │
   │  ├── 构造: pk_agg = (b_agg, a_agg)                                 │
   │  ├── 生成: evk = JointSwitchKeyGen({s_i²}, {s_i})                  │
   │  └── 输出: {sk_i = s_i}_{i∈[n]}                                    │
   │                │                │                │                  │
   │  [2] 分发公钥 ─────────────────────────────────────────────────────>│
   │  KGC → All: (pk_agg, evk)                                          │
   │                │                │                │                  │
   │  [3] 分发私钥份额 ────────────────────────>│                       │
   │  KGC → C_i: sk_i (通过安全通道)                                      │
   │                │                │                │                  │
   │  [4] 分发AN私钥 ──────────────────────────────────────>│            │
   │  KGC → AN_j: sk_j (若采用辅助节点托管模式)                            │
   │                │                │                │                  │
   │  [5] 分发见证签名份额 ──────────────────────────────────────────────────────>│
   │  KGC → WN_k: sk_WN_k                                              │
   │  KGC → All: vk_WN (验证公钥)                                        │
   │                │                │                │                  │
   │◄─[6] 确认接收 ──────────────────────────────────────────────────────│
   │                │                │                │                  │
   │  [7] KGC销毁所有密钥材料并永久离线                                     │
   │  KGC.Shred({s_agg, {s_i}, a, {e_i}})                               │
   │                │                │                │                  │
   ═══════════════════════════════════════════════════════════════════════
   Phase 0结束后的知识状态:
   AS.KNOWS = {pk_agg, evk}
   C_i.KNOWS = {sk_i, pk_agg, evk, vk_WN}
   AN_j.KNOWS = {sk_j, pk_agg, evk}
   WN_k.KNOWS = {sk_WN_k, vk_WN}
   ∀实体: DOESNT_KNOW {s_agg}
   ═══════════════════════════════════════════════════════════════════════
```

## 图1.2 主循环：单轮完整训练流程

```
┌─────┐          ┌─────┐          ┌─────┐          ┌─────────┐
│ AS  │          │ C_i │          │ AN_j│          │  WN_k   │
└──┬──┘          └──┬──┘          └──┬──┘          └────┬────┘
   │                │                │                  │
   ═══════════════════════════════════════════════════════
   ROUND t 开始
   ═══════════════════════════════════════════════════════
   │                │                │                  │
   │                │  [8] 客户端检查预取缓存              │
   │                │  if ct_prefetch ≠ ∅:               │
   │                │    进入 [15]-[19] 阈值解密阶段      │
   │                │  else:                             │
   │                │    w_sync ← w_base                 │
   │                │                │                  │
   │                │  [9] 本地训练                       │
   │                │  w_i ← LocalTrain(D_i, w_sync, E) │
   │                │  Δw_i ← w_i - w_sync              │
   │                │                │                  │
   │                │  [10] (可选SRCA) 残差合成           │
   │                │  g_i ← Δw_i + γ·r_i               │
   │                │                │                  │
   │                │  [11] 包级稀疏化                     │
   │                │  (idx_set, g_sparse, mask) ←      │
   │                │    SparseBatches(g_i, s)          │
   │                │                │                  │
   │                │  [12] CKKS加密 (使用聚合公钥)        │
   │                │  ct_i ← (b_agg·v + e_0 + m_i,     │
   │                │           a·v + e_1)              │
   │                │                │                  │
   │◄─[13] 上传密文 ──────────────────────────────│    │
   │  C_i → AS: (ct_i, mask_i) via TLS            │    │
   │                │                │                  │
   │  [14] AS执行同态聚合                            │
   │  for each batch b:                             │
   │    participants ← {i | mask_i[b] = 1}         │
   │    if |participants| > 0:                     │
   │      ct_agg[b] ← Σ_i∈participants w_i·ct_i[b]│
   │    else:                                       │
   │      ct_agg[b] ← R_global[b] (残差补偿)        │
   │                │                │                  │
   │  [20] 计算密文Delta                             │
   │  δ^(t) ← ct_agg^(t) - ct_agg^(t-1)            │
   │                │                │                  │
   │  [21] AS请求见证签名                            │
   │  AS → WN_k: h = SHA256(δ^(t)||t||pk_agg)     │
   │                │                │    │             │
   │                │                │◄───[22] WN_k生成签名
   │                │                │    σ_k = H(h)^{sk_WN_k}
   │                │                │    │             │
   │◄─[23] 返回签名份额 ──────────────────────────────│
   │                │                │                  │
   │  [24] AS聚合签名                               │
   │  Σ ← BLS.Combine({σ_k}, |T| = t_w)            │
   │                │                │                  │
   │  [25] 预取调度                                 │
   │  PrefSet ← SelectClients(bandwidth_budget)    │
   │                │                │                  │
   │  [26] 广播预取Delta ──────────────────────────>│
   │  AS → C_j (j∉S_t ∩ j∈PrefSet):                │
   │    (δ^(t), Σ, t, metadata)                    │
   │                │                │                  │
   │                │  [27] 未选中客户端接收并验证       │
   │                │  if Verify_BLS(Σ, vk_WN, h):    │
   │                │    if t > last_accepted_round:  │
   │                │      [28] ct_prefetch += δ^(t) │
   │                │      last_accepted ← t         │
   │                │    else:                        │
   │                │      [29] REJECT (重放攻击)     │
   │                │  else:                          │
   │                │    [30] REJECT (伪造delta)      │
   │                │                │                  │
   │◄─[31] 选中客户端上传更新 ──────────────────────│
   │  (对未使用预取的选中客户端)                      │
   │                │                │                  │
   │  [32] AS更新全局模型                             │
   │  w_global^(t) ← w_global^(t-1) + Decrypt(ct_agg)│
   │                │                │                  │
   │  [33] AS准备下一轮                              │
   │  ct_agg_prev ← ct_agg^(t)                      │
   │                │                │                  │
   ═══════════════════════════════════════════════════════
   ROUND t 结束
   ═══════════════════════════════════════════════════════
```

## 图1.3 阈值解密子流程（详细展开）

```
┌─────┐          ┌─────┐          ┌─────┐          ┌─────┐
│ C_i │          │AN_j1│          │AN_j2│          │AN_jt│
└──┬──┘          └──┬──┘          └──┬──┘          └──┬──┘
   │                │                │                │
   │  [15] 客户端发起解密请求                        │
   │  (当C_i被选中训练，且ct_prefetch ≠ ∅时触发)     │
   │                │                │                │
   │  [16] C_i计算自身部分解密份额                    │
   │  D_i ← sk_i · c_1 + e_smudge                 │
   │  其中 e_smudge ← D_{R,σ_smudge}              │
   │  σ_smudge ≥ 2^s · ‖e_prefetch‖_can           │
   │                │                │                │
   │─[17] 发送密文和请求 ──────────────────────────>│
   │  C_i → AN_j1: (ct_prefetch, "RequestPartialDec")│
   │                │                │                │
   │                │  [18] AN_j1计算部分解密         │
   │                │  D_j1 ← sk_j1 · c_1 + e_smudge1│
   │                │                │                │
   │◄─[19] 返回D_j1 ───────────────────────────────│
   │                │                │                │
   │─[34] 发送请求 ────────────────────────────────────>│
   │  C_i → AN_j2: (ct_prefetch, "RequestPartialDec")│
   │                │                │                │
   │                │                │  [35] AN_j2计算 │
   │                │                │  D_j2 ← sk_j2 · c_1 + e_smudge2
   │                │                │                │
   │◄─[36] 返回D_j2 ───────────────────────────────────│
   │                │                │                │
   │  ... (重复t-1次，收集t-1个外部份额)              │
   │                │                │                │
   │  [37] C_i本地组合所有份额                        │
   │  for each j ∈ T (包括自己和t-1个AN):            │
   │    λ_j ← ∏_{k∈T,k≠j} (-k)/(j-k) mod q_l       │
   │                │                │                │
   │  [38] 拉格朗日插值组合                           │
   │  m_combined ← c_0 + Σ_{j∈T} λ_j · D_j         │
   │                │                │                │
   │  [39] CKKS解码                                  │
   │  Δw_cum ← CKKS.Decode(m_combined)              │
   │  = Σ_{k=s}^t Δw_global^(k) + decode_noise      │
   │                │                │                │
   │  [40] 应用累积更新                              │
   │  w_sync ← w_base + Δw_cum                      │
   │  = w_global^(t)  (由正确性定理保证)             │
   │                │                │                │
   │  [41] 清空预取缓存，更新base                     │
   │  ct_prefetch ← ∅                              │
   │  w_base ← w_sync                               │
   │                │                │                │
   │  [42] 进入本地训练 [9]                          │
   │                │                │                │
```

## 图1.4 知识边界状态转换图

```
Phase 0: 初始化
─────────────────────────────────────────
KGC.KNOWS = {s_agg, {sk_i}, pk_agg, evk}
KGC → All: pk_agg, evk
KGC → C_i: sk_i
KGC: ShredKeys() → KGC.KNOWS = ∅

Phase 1: 加密上传
─────────────────────────────────────────
C_i.KNOWS += {Δw_i, D_i}
C_i → AS: ct_i = Enc_pk_agg(Δw_i)
AS.KNOWS += {ct_i}  // 但无法解密

Phase 2: 聚合
─────────────────────────────────────────
AS.KNOWS += {ct_agg = Σw_i·ct_i}
// AS仍无法解密

Phase 3: 预取
─────────────────────────────────────────
AS → C_j: δ^(t) = ct_agg^(t) - ct_agg^(t-1)
C_j.KNOWS += {δ^(t)}
C_j: ct_prefetch += δ^(t)
// C_j仍无法单独解密

Phase 4: 阈值解密
─────────────────────────────────────────
C_i → AN_j: Request PartialDec
AN_j → C_i: D_j = sk_j·c_1 + e_smudge
C_i: Combine({D_j}, ct_prefetch) → Δw_cum
C_i.KNOWS += {Δw_cum}

Phase 5: 训练
─────────────────────────────────────────
C_i: w_sync = w_base + Δw_cum
C_i: w_new = LocalTrain(D_i, w_sync)
```

---

# 第二篇：阈值CKKS公式闭环 时序图

## 图2.1 从RLWE到明文恢复的完整公式链

```
阶段: RLWE采样
─────────────────────────────────────────────────────────
[2.1] 采样密钥:   s ← χ_key
[2.2] 采样公钥分量: a ← U(R_qL)
[2.3] 采样误差:   e ← χ_err
[2.4] 计算:       b = -a·s + e (mod qL)

输出: (a, b) 满足 b ≈ a·s + e
安全性: 基于决策性RLWE假设，(a,b)≈(a,u)

阶段: 阈值密钥生成
─────────────────────────────────────────────────────────
[2.5] 每个参与者i采样: s_i ← χ_key, a_i ← U(R_qL), e_i ← χ_err
[2.6] 计算本地公钥:    b_i = -a_i·s_i + e_i
[2.7] 聚合公钥分量:    a_agg = Σa_i
[2.8] 聚合公钥:        b_agg = Σb_i = -a_agg·s_agg + e_agg
                        其中 s_agg = Σs_i, e_agg = Σe_i
[2.9] 输出聚合公钥:    pk_agg = (b_agg, a_agg)
[2.10] 分发私钥份额:   sk_i = s_i

阶段: 消息编码
─────────────────────────────────────────────────────────
[2.11] 输入消息:      z ∈ C^{N/2} (梯度向量)
[2.12] 共轭对称扩展:   π^{-1}(z) ∈ C^N
[2.13] 逆FFT:         m' = ⌊Δ·σ^{-1}(π^{-1}(z))⌉ ∈ R
[2.14] 模约化:         m = m' mod qL

阶段: 加密
─────────────────────────────────────────────────────────
[2.15] 采样随机性:     v ← χ_enc, e_0,e_1 ← χ_err
[2.16] 计算密文分量:   c_0 = b_agg·v + e_0 + m
[2.17]                    c_1 = a·v + e_1
[2.18] 输出密文:       ct = (c_0, c_1)

加密正确性验证:
c_0 + c_1·s_agg = (-a·s_agg + e_agg)v + e_0 + m + (av + e_1)s_agg
                = m + e_agg·v + e_0 + e_1·s_agg
                = m + e_noise

阶段: 同态聚合
─────────────────────────────────────────────────────────
[2.19] 输入:          {ct_i = (c_{i,0}, c_{i,1})}_{i∈S_t}
[2.20] 加权聚合:      ct_agg = (Σw_i·c_{i,0}, Σw_i·c_{i,1})
                      = (b_agg·v_agg + e_agg,0 + m_agg,
                         a·v_agg + e_agg,1)

噪声分析:
e_agg = Σw_i·e_noise^(i)
E[‖e_agg‖²] = Σw_i²·E[‖e_noise^(i)‖²]
当 w_i ≈ 1/n 时: E[‖e_agg‖²] ≈ E[‖e_noise‖²]/n

阶段: Delta生成
─────────────────────────────────────────────────────────
[2.21] 密文减法:      δ^(t) = ct_agg^(t) - ct_agg^(t-1)
                      = (Δc_0, Δc_1)
[2.22] Delta噪声:     e_δ = e_agg^(t) - e_agg^(t-1)
                      ‖e_δ‖ ≤ ‖e_agg^(t)‖ + ‖e_agg^(t-1)‖

阶段: 预取累加
─────────────────────────────────────────────────────────
[2.23] 客户端累加:    ct_prefetch = Σ_{k=s}^t δ^(k)
[2.24] 累积噪声:      e_prefetch = Σ_{k=s}^t e_δ^(k)
                      ‖e_prefetch‖ ≤ R·B_δ

阶段: 部分解密
─────────────────────────────────────────────────────────
[2.25] 客户端计算:     D_i = sk_i·c_1 + e_smudge
[2.26] 辅助节点计算:   D_j = sk_j·c_1 + e_smudge,j
[2.27] 拉格朗日系数:  λ_j = ∏_{k∈T,k≠j} (-k)/(j-k)
[2.28] 组合:          m_combined = c_0 + Σλ_j·D_j

组合正确性:
m_combined = c_0 + c_1·Σλ_j·s_j + Σλ_j·e_smudge,j
           = c_0 + c_1·s_agg + e_total_smudge
           = m + e_prefetch + e_total_smudge

阶段: 解码
─────────────────────────────────────────────────────────
[2.29] CKKS解码:      Δw_cum = Decode(m_combined)
                      = (1/Δ)·σ(π(m_combined))
[2.30] 模型更新:      w_sync = w_base + Δw_cum
```

## 图2.2 噪声增长完整递推图

```
噪声源                噪声表达式                    上界
─────────────────────────────────────────────────────────
初始加密噪声:         e_noise = e_agg·v + e_0 + e_1·s   B_clean
                     
聚合后噪声:           e_agg = Σw_i·e_noise^(i)         B_agg ≈ B_clean/√n

Delta噪声:            e_δ = e_agg^(t) - e_agg^(t-1)    B_δ ≤ 2·B_agg

预取累积噪声:         e_prefetch = Σ_{k=1}^R e_δ^(k)   R·B_δ

Smudging噪声:         e_smudge,j ← D_{R,σ_smudge}      σ_smudge ≥ 2^s·‖e_prefetch‖

组合后总噪声:         e_total = e_prefetch + Σλ_j·e_smudge,j
                                                        ≤ R·B_δ + t·λ_max·σ_smudge

解密条件:             log₂(‖e_total‖·√N) < log₂(q_l)
                     
Bootstrapping触发:    Budget = log₂(q_l) - log₂(‖e_total‖·√N) - s_smudge < θ_boot
```

---

# 第三篇：安全防御方案 时序图

## 图3.1 攻击向量全景图

```
攻击者: 恶意服务器 AS
─────────────────────────────────────────────────────────
[ATTACK-1] 选择性Delta伪造
   AS维护两套delta:
     δ_correct = ct_agg^(t) - ct_agg^(t-1)
     δ_malicious = δ_correct + Enc(Δpoison)
   
   AS → C_normal: δ_correct
   AS → C_target: δ_malicious
   
   效果: 目标客户端模型被引导偏离
   检测难度: ★★★★★ (密文内容不可见)

[ATTACK-2] Delta重放
   AS记录 δ^(t) (Round t)
   AS在 Round t+k 重放 δ^(t) 给 C_j
   
   C_j: ct_prefetch += δ^(t) (过期delta)
   效果: 客户端模型回退到t轮状态
   检测难度: ★★★★☆ (需轮次验证)

[ATTACK-3] Delta放大
   δ* = α·δ (α > 1, 同态标量乘)
   
   AS → C_j: δ*
   C_j累积后相当于Scaled更新
   效果: 长期累积导致模型发散
   检测难度: ★★★★☆

[ATTACK-4] 预取缓存污染
   AS向C_j发送大量伪造小delta
   C_j: ct_prefetch += Σδ_fake
   
   效果: 累积效应显著
   检测难度: ★★★☆☆
```

## 图3.2 TPW防御方案时序图

```
┌─────┐          ┌─────┐          ┌─────┐          ┌─────┐          ┌─────┐
│ AS  │          │WN_1 │          │WN_2 │          │WN_tw│          │ C_j │
└──┬──┘          └──┬──┘          └──┬──┘          └──┬──┘          └──┬──┘
   │                │                │                │                │
   │  [3.1] AS生成Delta后请求签名                       │                │
   │  h ← SHA256(δ^(t).serialize() || t || τ || pk_agg)│                │
   │                │                │                │                │
   │─[3.2] 发送哈希 ────────────────────────────────────────────────>│
   │  AS → WN_k: ("SignRequest", h, t)                                │
   │                │                │                │                │
   │                │  [3.3] WN_1验证并签名                           │
   │                │  if t > last_signed_round[AS]:                 │
   │                │    σ_1 = H(h)^{sk_WN_1} ∈ G_1                  │
   │                │    last_signed_round[AS] ← t                   │
   │                │  else:                                          │
   │                │    REJECT (重放签名请求)                         │
   │                │                │                │                │
   │◄─[3.4] 返回σ_1 ─────────────────────────────────────────────────│
   │                │                │                │                │
   │─[3.5] 发送哈希 ────────────────────────────────────────────────>│
   │  AS → WN_2: ("SignRequest", h, t)                                │
   │                │                │                │                │
   │                │                │  [3.6] WN_2签名                │
   │                │                │  σ_2 = H(h)^{sk_WN_2}         │
   │                │                │                │                │
   │◄─[3.7] 返回σ_2 ─────────────────────────────────────────────────│
   │                │                │                │                │
   │  ... (重复至收集t_w个签名)                                       │
   │                │                │                │                │
   │─[3.8] 发送哈希 ────────────────────────────────────────────────────────>│
   │  AS → WN_tw: ("SignRequest", h, t)                                    │
   │                │                │                │    │             │
   │                │                │                │ [3.9] WN_tw签名  │
   │                │                │                │ σ_tw = H(h)^{sk_WN_tw}
   │                │                │                │    │             │
   │◄─[3.10] 返回σ_tw ──────────────────────────────────────────────────────│
   │                │                │                │                │
   │  [3.11] AS聚合签名                               │                │
   │  Σ = ∏_{k∈T} σ_k^{λ_k} = H(h)^{Σλ_k·sk_WN_k}   │                │
   │    = H(h)^x  (其中x为完整签名密钥)                │                │
   │                │                │                │                │
   │  [3.12] AS广播带签名的Delta ────────────────────────────────────>│
   │  AS → C_j: (δ^(t), Σ, t, τ)                                    │
   │                │                │                │                │
   │                │                │                │  [3.13] C_j验证  │
   │                │                │                │  h' = SHA256(δ^(t)||t||τ||pk_agg)
   │                │                │                │  if e(Σ, g_2) == e(H(h'), PK):
   │                │                │                │    if t > last_accepted_round:
   │                │                │                │      [3.14] ACCEPT → ct_prefetch += δ^(t)
   │                │                │                │      last_accepted ← t
   │                │                │                │    else:
   │                │                │                │      [3.15] REJECT_REPLAY
   │                │                │                │  else:
   │                │                │                │    [3.16] REJECT_FORGERY
   │                │                │                │
```

## 图3.3 ACD认证方案时序图

```
┌─────┐          ┌─────┐
│ AS  │          │ C_j │
└──┬──┘          └──┬──┘
   │                │
   │  [3.17] AS生成Delta认证标签
   │  // AS在生成δ^(t)时已知明文m^(t)
   │  h = SHA256(m^(t))
   │  nonce ← {0,1}^96
   │  (c_tag, tag) = AES-GCM_{k_auth}(h, nonce)
   │                │
   │─[3.18] 广播带标签的Delta ───────>│
   │  AS → C_j: (δ^(t), c_tag, nonce, t)
   │                │
   │                │  [3.19] C_j接收并缓存
   │                │  ct_prefetch += δ^(t)
   │                │  store (c_tag, nonce) for later verification
   │                │
   │                │  // 训练前解密时验证
   │                │  [3.20] C_j解密δ^(t)后得到m'
   │                │  h' = SHA256(m')
   │                │  if AES-GCM_{k_auth}.Verify(c_tag, tag, nonce) == h':
   │                │    [3.21] ACCEPT → apply update
   │                │  else:
   │                │    [3.22] REJECT → rollback to last verified state
   │                │
```

## 图3.4 ZKPP零知识证明方案时序图

```
┌─────┐          ┌─────┐          ┌─────┐
│ AS  │          │Prover│         │ C_j │
└──┬──┘          └──┬──┘          └──┬──┘
   │                │                │
   │  [3.23] AS作为Prover生成ZK证明
   │  
   │  公共输入 x = (pk_agg, h_old, h_new, δ^(t))
   │  私密输入 w = (w^(t), w^(t-1), v, e_0, e_1, {w_i, w_i^(local)})
   │  
   │  约束电路 C(x,w):
   │    1. δ^(t)_0 == b_agg·v + e_0 + (w^(t) - w^(t-1))
   │    2. δ^(t)_1 == a·v + e_1
   │    3. w^(t) == Σ_i w_i · w_i^(local)
   │    4. ‖e_0‖ ≤ B_err AND ‖e_1‖ ≤ B_err
   │    5. h_old == Commit(w^(t-1))
   │    6. h_new == Commit(w^(t))
   │                │
   │  [3.24] 生成证明
   │  π ← ZK.Prove(C, x, w)
   │                │
   │─[3.25] 广播(δ, π, x) ────────────>│
   │                │                │
   │                │                │  [3.26] C_j验证证明
   │                │                │  b ← ZK.Verify(C, x, π)
   │                │                │  if b == True:
   │                │                │    [3.27] ACCEPT → ct_prefetch += δ^(t)
   │                │                │  else:
   │                │                │    [3.28] REJECT
   │                │                │
```

---

# 第四篇：SRCA通信优化 时序图

## 图4.1 SRCA客户端残差累积流程

```
┌─────────────────────────────────────────────────────────┐
│              SRCA客户端状态机                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [4.1] 初始化: r_i^(0) = 0                              │
│                                                          │
│  [4.2] 每轮开始:                                        │
│    输入: raw_gradient Δw_i^(t)                          │
│                                                          │
│    [4.3] 残差合成:                                      │
│      g_i^(t) = Δw_i^(t) + γ · r_i^(t-1)                │
│      // 将上轮未传输信息加入本轮梯度                     │
│                                                          │
│    [4.4] 包级稀疏化:                                    │
│      (idx_set, g_sparse, mask) = SparseBatches(g_i^(t), s)
│      // 选择Top-K或Rand-K batch                        │
│                                                          │
│    [4.5] 加密上传:                                      │
│      ct_i^(t) = CKKS.Encrypt(pk_agg, g_sparse)         │
│                                                          │
│    [4.6] 残差更新:                                      │
│      for each batch b:                                  │
│        if mask[b] == 1:  // 本batch被选中传输            │
│          r_i^(t)[b] = 0                                 │
│        else:  // 本batch未被选中                         │
│          r_i^(t)[b] = g_i^(t)[b]  // 保留到下一轮        │
│                                                          │
│    [4.7] 衰减 (可选):                                   │
│      r_i^(t) = γ · r_i^(t)                             │
│                                                          │
│  [4.8] 输出: ct_i^(t), r_i^(t)                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 图4.2 SRCA服务器全局残差补偿流程

```
┌─────────────────────────────────────────────────────────┐
│            SRCA服务器聚合与预取流程                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [4.9] 输入: {(ct_i, mask_i)}_{i∈S_t}                  │
│                                                          │
│  [4.10] 按batch分桶聚合:                                │
│    for each batch b:                                    │
│      participants = {i | mask_i[b] == 1}               │
│                                                          │
│      [4.11] if |participants| > 0:                     │
│        ct_agg[b] = WeightedAvg({ct_i[b]}, {w_i})       │
│        // 正常聚合                                      │
│                                                          │
│      [4.12] else:  // 没有任何客户端选中此batch          │
│        ct_agg[b] = R_global^(t-1)[b]                   │
│        // 使用全局残差补偿                              │
│                                                          │
│  [4.13] 更新全局残差:                                   │
│    for each batch b:                                    │
│      if |participants| == 0:                            │
│        R_global^(t)[b] = γ_R · R_global^(t-1)[b] +      │
│                           FreshResidual[b]              │
│      else:                                              │
│        R_global^(t)[b] = γ_R · R_global^(t-1)[b]       │
│                                                          │
│  [4.14] 生成Delta:                                     │
│    δ^(t) = ct_agg^(t) - ct_agg^(t-1)                   │
│                                                          │
│  [4.15] 残差感知预取调度:                                │
│    for each client j not in S_t:                       │
│      priority[j] = ComputeResidualPriority(j)           │
│      // 基于客户端残差大小、带宽、历史命中率              │
│                                                          │
│    [4.16] PrefSet = TopK(priority, bandwidth_budget)   │
│                                                          │
│  [4.17] 广播预取:                                      │
│    for j in PrefSet:                                    │
│      AS → C_j: δ^(t)                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 图4.3 自适应稀疏率调整流程

```
┌─────────────────────────────────────────────────────────┐
│          自适应稀疏率状态机                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [4.18] 根据训练轮次动态调整参数:                        │
│                                                          │
│    if t < T/4:        // 预热期                         │
│      [4.19] s = 0.50     // 50%稀疏率                  │
│      [4.20] γ = 0.95     // 高残差保留                 │
│      [4.21] γ_R = 0.95   // 高全局残差保留             │
│                                                          │
│    elif t < 3T/4:     // 稳定期                         │
│      [4.22] s = 0.30     // 30%稀疏率                  │
│      [4.23] γ = 0.90     // 标准残差衰减               │
│      [4.24] γ_R = 0.90   // 标准全局残差衰减           │
│                                                          │
│    else:              // 精调期                         │
│      [4.25] s = 0.15     // 15%稀疏率                  │
│      [4.26] γ = 0.85     // 激进残差衰减               │
│      [4.27] γ_R = 0.85   // 激进全局残差衰减           │
│                                                          │
│  [4.28] 可选: 基于收敛速度自适应调整                     │
│    if accuracy_improvement < threshold:                 │
│      [4.29] s = s * 1.2  // 增加稀疏率                 │
│    if loss_variance > threshold:                        │
│      [4.30] s = s * 0.8  // 降低稀疏率                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 图4.4 带宽感知预取调度流程

```
┌─────────────────────────────────────────────────────────┐
│          带宽感知预取调度算法                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [4.31] 输入:                                           │
│    - 客户端集合 C = {C_1, ..., C_n}                    │
│    - 选中集合 S_t                                       │
│    - 带宽配置 {BW_j^down, BW_j^up}                     │
│    - EMA轮次耗时 D_avg                                  │
│                                                          │
│  [4.32] 计算每个未选中客户端的预取能力:                  │
│    for j ∉ S_t:                                         │
│      missing_rounds = t - last_sync[j]                 │
│      missing_size = missing_rounds · |δ|               │
│                                                          │
│      [4.33] 理论下载时间:                                │
│        T_download = missing_size / BW_j^down           │
│                                                          │
│      [4.34] 预取可行性:                                  │
│        if T_download <= D_avg · β:  // β为松弛因子       │
│          feasible[j] = True                             │
│        else:                                            │
│          feasible[j] = False                            │
│                                                          │
│  [4.35] 残差优先级排序:                                  │
│    for j ∉ S_t:                                         │
│      residual_norm[j] = ‖r_j^(t)‖                      │
│      priority[j] = α·residual_norm[j] +                 │
│                     (1-α)·feasible[j]                  │
│                                                          │
│  [4.36] 选择预取目标:                                    │
│    candidates = SortByPriority({j | feasible[j] = True})│
│    bandwidth_consumed = 0                               │
│    PrefSet = ∅                                          │
│                                                          │
│    [4.37] for j in candidates:                         │
│      if bandwidth_consumed + |δ| <= budget:            │
│        PrefSet.add(j)                                   │
│        bandwidth_consumed += |δ|                       │
│      else:                                              │
│        break                                            │
│                                                          │
│  [4.38] 输出: PrefSet                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

# 融合方案：SecureRes-Fetch 总时序图

## 图5.1 完整端到端流程（含全部四篇方案）

```
┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────────┐
│ KGC │    │ AS  │    │ C_i │    │ AN_j│    │ WN_k│    │ Monitor │
└──┬──┘    └──┬──┘    └──┬──┘    └──┬──┘    └──┬──┘    └────┬────┘
   │          │          │          │          │            │
   ═════════════════════════════════════════════════════════════════
   PHASE 0: 系统初始化
   ═════════════════════════════════════════════════════════════════
   │          │          │          │          │            │
   │[P0-1] ThresholdCKKS.KeyGen(λ,n,t)                               │
   │─────────────────────────────────────────────────────────────────│
   │          │          │          │          │            │
   │[P0-2] 分发密钥材料                                               │
   │ KGC→AS: (pk_agg, evk)                                           │
   │ KGC→C_i: sk_i                                                   │
   │ KGC→AN_j: sk_j                                                  │
   │ KGC→WN_k: sk_WN_k                                               │
   │ KGC→All: vk_WN                                                  │
   │          │          │          │          │            │
   │[P0-3] KGC永久离线                                               │
   │          │          │          │          │            │
   ═════════════════════════════════════════════════════════════════
   PHASE 1: 主训练循环 (Round t = 1 to T)
   ═════════════════════════════════════════════════════════════════
   │          │          │          │          │            │
   │          │          │[P1-1] 检查预取缓存                          │
   │          │          │ if ct_prefetch ≠ ∅:                       │
   │          │          │   goto [P1-19] 阈值解密                     │
   │          │          │ else:                                      │
   │          │          │   w_sync ← w_base                         │
   │          │          │          │          │            │
   │          │          │[P1-2] 本地训练                              │
   │          │          │ w_i ← LocalTrain(D_i, w_sync, E)         │
   │          │          │ Δw_i ← w_i - w_sync                       │
   │          │          │          │          │            │
   │          │          │[P1-3] (SRCA) 残差合成                      │
   │          │          │ g_i ← Δw_i + γ·r_i                       │
   │          │          │          │          │            │
   │          │          │[P1-4] (SRCA) 包级稀疏化                    │
   │          │          │ (idx, g_sparse, mask) = Sparse(g_i, s)   │
   │          │          │          │          │            │
   │          │          │[P1-5] (自适应稀疏率) 根据阶段调整s         │
   │          │          │ s = AdaptiveSparsity(t, T)               │
   │          │          │          │          │            │
   │          │          │[P1-6] CKKS加密                              │
   │          │          │ ct_i ← Enc_pk_agg(g_sparse)              │
   │          │          │          │          │            │
   │          │◄─────────[P1-7] 上传密文─────────────────────────────│
   │          │          │ C_i → AS: (ct_i, mask_i) via TLS         │
   │          │          │          │          │            │
   │          │[P1-8] 同态聚合                                         │
   │          │ for each batch b:                                     │
   │          │   participants = {i | mask_i[b]=1}                   │
   │          │   if |participants|>0:                               │
   │          │     ct_agg[b] = Σ w_i·ct_i[b]                        │
   │          │   else:                                               │
   │          │     ct_agg[b] = R_global[b] (残差补偿)                │
   │          │          │          │          │            │
   │          │[P1-9] 更新全局残差                                    │
   │          │ R_global ← γ_R·R_global + FreshResidual             │
   │          │          │          │          │            │
   │          │[P1-10] 计算密文Delta                                  │
   │          │ δ^(t) = ct_agg^(t) - ct_agg^(t-1)                   │
   │          │          │          │          │            │
   │          │[P1-11] 请求TPW见证签名                                │
   │          │ h = SHA256(δ^(t)||t||pk_agg)                         │
   │          │───────────────────────────────>│          │            │
   │          │          │          │          │[P1-12] WN_k签名      │
   │          │          │          │          │ σ_k = H(h)^{sk_WN_k} │
   │          │          │          │          │            │
   │          │◄─────────────────────────────────────────│            │
   │          │          │          │          │            │
   │          │[P1-13] 聚合签名 Σ = BLS.Combine({σ_k})               │
   │          │          │          │          │            │
   │          │[P1-14] (SRCA) 残差感知预取调度                        │
   │          │ PrefSet = BandwidthAwareSchedule(                     │
   │          │   {C_j}, {BW_j}, {r_j}, D_avg, budget)               │
   │          │          │          │          │            │
   │          │[P1-15] 广播预取Delta───────────────────────────────>│
   │          │ AS→C_j: (δ^(t), Σ, t, metadata)                      │
   │          │          │          │          │            │
   │          │          │[P1-16] 客户端验证                           │
   │          │          │ if Verify_BLS(Σ, vk_WN, h):               │
   │          │          │   if t > last_accepted:                    │
   │          │          │     [P1-17] ct_prefetch += δ^(t)          │
   │          │          │     last_accepted = t                     │
   │          │          │   else: [P1-18] REJECT_REPLAY             │
   │          │          │ else: [P1-18b] REJECT_FORGERY             │
   │          │          │          │          │            │
   │          │          │[P1-19] (当被选中时) 阈值解密               │
   │          │          │ if ct_prefetch ≠ ∅:                       │
   │          │          │   D_i = sk_i·c_1 + e_smudge              │
   │          │          │   for j in selected_ANs:                  │
   │          │          │     ──────────────────────>│              │
   │          │          │          │   [P1-20] AN_j计算            │
   │          │          │          │   D_j = sk_j·c_1 + e_smudge  │
   │          │          │          │◄───────────────────────       │
   │          │          │   [P1-21] 拉格朗日组合                      │
   │          │          │   m = c_0 + Σλ_j·D_j                     │
   │          │          │   [P1-22] 解码                            │
   │          │          │   Δw_cum = CKKS.Decode(m)                │
   │          │          │   [P1-23] 应用更新                        │
   │          │          │   w_sync = w_base + Δw_cum               │
   │          │          │   ct_prefetch = ∅                        │
   │          │          │   w_base = w_sync                        │
   │          │          │          │          │            │
   │          │          │[P1-24] 本地训练 (继续)                     │
   │          │          │ w_i = LocalTrain(D_i, w_sync)            │
   │          │          │ ... (回到P1-3)                            │
   │          │          │          │          │            │
   │          │[P1-25] (Monitor) 可选延迟验证                        │
   │          │─────────────────────────────────────────────────────>│
   │          │          │          │          │            │
   │          │          │          │          │ [P1-26] 每k轮验证  │
   │          │          │          │          │ if accuracy_drop: │
   │          │          │          │          │   trigger_alert() │
   │          │          │          │          │   rollback()      │
   │          │          │          │          │            │
   ═════════════════════════════════════════════════════════════════
   PHASE 2: 训练结束
   ═════════════════════════════════════════════════════════════════
   │          │          │          │          │            │
   │          │          │[P2-1] 最终模型输出                          │
   │          │          │ w_final = w_base + ThresholdDecrypt(       │
   │          │          │              ct_prefetch_residual)         │
   │          │          │          │          │            │
```

## 图5.2 多轮预取累积的时序示例

```
时间轴 →

Round 1:
  AS: 聚合 → 生成δ^(1)
  AS → C_3: δ^(1) (C_3未选中)
  C_3: ct_prefetch = δ^(1)

Round 2:
  AS: 聚合 → 生成δ^(2)
  AS → C_3: δ^(2)
  C_3: ct_prefetch = δ^(1) + δ^(2)
  
Round 3:
  AS: 聚合 → 生成δ^(3)
  AS → C_1: δ^(3) (C_1未选中)
  C_1: ct_prefetch = δ^(3)
  
  C_3被选中了！
  C_3: 需要 Fetch δ^(3) (只缺最新一轮)
  C_3 → AS: "Request δ^(3)"
  AS → C_3: δ^(3)
  C_3: ct_prefetch = (δ^(1)+δ^(2)) + δ^(3) = Σ_{k=1}^3 δ^(k)
  C_3: ThresholdDecrypt(ct_prefetch) → Δw_cum
  C_3: w_sync = w_base + Δw_cum = w_global^(3)
  C_3: 训练 → 上传ct_3
  C_3: ct_prefetch = ∅, w_base = w_sync

Round 4:
  C_3又被选中了！(连续选中)
  C_3: ct_prefetch = ∅ (上轮已清空)
  C_3: w_sync = w_base (已经是w_global^(4))
  C_3: 训练 → 上传ct_3
```

## 图5.3 异常处理流程

```
┌─────────────────────────────────────────────────────────┐
│                 异常处理状态机                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [E-1] TPW验证失败                                      │
│    C_j收到(δ, Σ, t)                                     │
│    if Verify_BLS(Σ) == False:                          │
│      [E-2] 丢弃δ                                       │
│      [E-3] 向Monitor报告"SuspiciousDeltaFromAS"       │
│      [E-4] 若连续3次失败，标记AS为不可信               │
│      [E-5] 回退到明文同步模式(紧急降级)                │
│                                                          │
│  [E-6] 重放攻击检测                                     │
│    if t <= last_accepted_round:                        │
│      [E-7] 丢弃δ                                       │
│      [E-8] 记录重放尝试日志                            │
│                                                          │
│  [E-9] 阈值解密失败                                     │
│    if Budget(ct_prefetch) < θ_boot:                   │
│      [E-10] 触发紧急同步                               │
│      [E-11] C_j → AS: "RequestFullSync"               │
│      [E-12] AS → C_j: ct_agg^(t) (完整全局模型密文)   │
│      [E-13] C_j直接解密ct_agg^(t) (单轮噪声，安全)    │
│      [E-14] ct_prefetch = ∅                           │
│                                                          │
│  [E-15] 辅助节点掉线                                    │
│    if available_ANs < t:                               │
│      [E-16] 等待其他AN上线                             │
│      [E-17] 或请求其他客户端协助解密                   │
│      [E-18] 若t个客户端在线，可无需AN直接解密          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

*本文档包含四篇论文全部方案的完整时序图，每个步骤带序号标识，可直接用于论文中的协议描述部分。*
