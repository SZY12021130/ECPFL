# 所有方案 Mermaid 时序图代码

> 复制以下内容到支持 Mermaid 的编辑器（如 Typora、VS Code、GitHub、Mermaid Live Editor）即可渲染图形

---

## 第一篇：Threshold-CipherFetch

### 图1.1 初始化阶段

```mermaid
sequenceDiagram
    autonumber
    participant KGC as KGC<br/>(密钥生成中心)
    participant AS as AS<br/>(聚合服务器)
    participant C as C_i<br/>(客户端)
    participant AN as AN_j<br/>(辅助节点)
    participant WN as WN_k<br/>(见证节点)

    KGC->>KGC: [1] ThresholdCKKS.KeyGen(λ, n, t)<br/>采样: s_i←χ_key, a_i←U(R_qL), e_i←χ_err<br/>计算: b_i = -a_i·s_i + e_i<br/>聚合: a_agg=Σa_i, b_agg=Σb_i<br/>输出: pk_agg=(b_agg,a_agg), evk

    KGC->>AS: [2] 分发公钥<br/>(pk_agg, evk)
    KGC->>C: [3] 分发私钥份额<br/>sk_i = s_i (安全通道)
    KGC->>AN: [4] 分发AN私钥<br/>sk_j (辅助节点托管模式)
    KGC->>WN: [5] 分发见证签名份额<br/>sk_WN_k 及验证公钥 vk_WN

    AS-->>KGC: [6] 确认接收
    C-->>KGC: 确认接收
    AN-->>KGC: 确认接收
    WN-->>KGC: 确认接收

    KGC->>KGC: [7] KGC.ShredKeys()<br/>销毁所有密钥材料并永久离线

    Note over KGC,WN: Phase 0 结束后的知识边界<br/>AS.KNOWS = {pk_agg, evk}<br/>C_i.KNOWS = {sk_i, pk_agg, evk, vk_WN}<br/>AN_j.KNOWS = {sk_j, pk_agg, evk}<br/>WN_k.KNOWS = {sk_WN_k, vk_WN}<br/>∀实体: DOESNT_KNOW {s_agg}
```

### 图1.2 主训练循环（单轮）

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS<br/>(聚合服务器)
    participant C as C_i<br/>(客户端)
    participant AN as AN_j<br/>(辅助节点)
    participant WN as WN_k<br/>(见证节点)

    rect rgb(230, 245, 255)
        Note over C: [8] 检查预取缓存<br/>if ct_prefetch ≠ ∅: 进入阈值解密<br/>else: w_sync ← w_base
    end

    C->>C: [9] 本地训练<br/>w_i ← LocalTrain(D_i, w_sync, E)<br/>Δw_i ← w_i - w_sync

    C->>C: [10] (SRCA) 残差合成<br/>g_i ← Δw_i + γ·r_i

    C->>C: [11] 包级稀疏化<br/>(idx_set, g_sparse, mask) ← SparseBatches(g_i, s)

    C->>C: [12] CKKS加密<br/>ct_i ← Enc_pk_agg(g_sparse)

    C->>AS: [13] 上传密文<br/>(ct_i, mask_i) via TLS

    AS->>AS: [14] 同态聚合<br/>for each batch b:<br/>&nbsp;&nbsp;participants ← {i | mask_i[b]=1}<br/>&nbsp;&nbsp;if |participants|>0:<br/>&nbsp;&nbsp;&nbsp;&nbsp;ct_agg[b] ← Σ w_i·ct_i[b]<br/>&nbsp;&nbsp;else:<br/>&nbsp;&nbsp;&nbsp;&nbsp;ct_agg[b] ← R_global[b]

    AS->>AS: [20] 计算密文Delta<br/>δ^(t) ← ct_agg^(t) - ct_agg^(t-1)

    AS->>WN: [21] 请求见证签名<br/>h = SHA256(δ^(t)||t||pk_agg)

    WN->>WN: [22] 生成签名<br/>σ_k = H(h)^{sk_WN_k}
    WN-->>AS: [23] 返回签名份额 σ_k

    AS->>AS: [24] 聚合签名<br/>Σ ← BLS.Combine({σ_k}, |T|=t_w)

    AS->>AS: [25] 预取调度<br/>PrefSet ← SelectClients(bandwidth_budget)

    AS->>C: [26] 广播预取Delta<br/>(δ^(t), Σ, t, metadata)

    C->>C: [27] 接收并验证<br/>Verify_BLS(Σ, vk_WN, h)<br/>检查 t > last_accepted_round

    alt 验证通过且t最新
        C->>C: [28] ct_prefetch += δ^(t)<br/>last_accepted ← t
    else 重放攻击
        C->>C: [29] REJECT_REPLAY
    else 签名伪造
        C->>C: [30] REJECT_FORGERY
    end

    C->>AS: [31] 选中客户端上传更新<br/>(对未使用预取的选中客户端)

    AS->>AS: [32] 更新全局模型<br/>w_global^(t) ← w_global^(t-1) + Decrypt(ct_agg)

    AS->>AS: [33] 准备下一轮<br/>ct_agg_prev ← ct_agg^(t)
```

### 图1.3 阈值解密子流程

```mermaid
sequenceDiagram
    autonumber
    participant C as C_i<br/>(客户端)
    participant AN1 as AN_1
    participant AN2 as AN_2
    participant ANt as AN_t

    C->>C: [15] 发起解密请求<br/>(当C_i被选中且ct_prefetch≠∅)

    C->>C: [16] 计算自身份额<br/>D_i = sk_i·c_1 + e_smudge<br/>σ_smudge ≥ 2^s·‖e_prefetch‖_can

    C->>AN1: [17] 发送密文和请求<br/>(ct_prefetch, "RequestPartialDec")

    AN1->>AN1: [18] 计算部分解密<br/>D_1 = sk_1·c_1 + e_smudge,1
    AN1-->>C: [19] 返回 D_1

    C->>AN2: [34] 发送请求
    AN2->>AN2: [35] 计算 D_2 = sk_2·c_1 + e_smudge,2
    AN2-->>C: [36] 返回 D_2

    Note over C,ANt: ... 重复收集 t-1 个外部份额 ...

    C->>C: [37] 计算拉格朗日系数<br/>λ_j = ∏_{k∈T,k≠j} (-k)/(j-k) mod q_l

    C->>C: [38] 组合明文<br/>m_combined = c_0 + Σ_{j∈T} λ_j·D_j

    C->>C: [39] CKKS解码<br/>Δw_cum = CKKS.Decode(m_combined)<br/>= Σ_{k=s}^t Δw_global^(k) + decode_noise

    C->>C: [40] 应用累积更新<br/>w_sync = w_base + Δw_cum<br/>= w_global^(t) ✓

    C->>C: [41] 清空缓存，更新base<br/>ct_prefetch ← ∅<br/>w_base ← w_sync

    C->>C: [42] 进入本地训练 [9]
```

---

## 第二篇：公式闭环噪声递推

### 图2.1 完整公式链

```mermaid
sequenceDiagram
    autonumber
    participant RLWE as RLWE采样
    participant Thresh as 阈值密钥
    participant Enc as 编码加密
    participant Agg as 同态聚合
    participant Delta as Delta生成
    participant Pref as 预取累加
    participant Dec as 阈值解密
    participant Decode as 解码恢复

    RLWE->>RLWE: [2.1] s←χ_key<br/>[2.2] a←U(R_qL)<br/>[2.3] e←χ_err<br/>[2.4] b=-a·s+e

    RLWE->>Thresh: 分发参数
    Thresh->>Thresh: [2.5-2.10] n个参与者各采样<br/>a_agg=Σa_i, b_agg=Σb_i<br/>pk_agg=(b_agg,a_agg)<br/>sk_i=s_i

    Thresh->>Enc: 公钥就绪
    Enc->>Enc: [2.11-2.14] 消息编码<br/>z→π^{-1}(z)→σ^{-1}→m'<br/>[2.15-2.18] 加密<br/>c_0=b_agg·v+e_0+m<br/>c_1=a·v+e_1

    Enc->>Agg: 密文就绪
    Agg->>Agg: [2.19-2.20] 加权聚合<br/>ct_agg=(Σw_i·c_{i,0}, Σw_i·c_{i,1})<br/>噪声: e_agg=Σw_i·e_noise^(i)

    Agg->>Delta: 聚合密文
    Delta->>Delta: [2.21-2.22] 密文减法<br/>δ^(t)=ct_agg^(t)-ct_agg^(t-1)<br/>e_δ=e_agg^(t)-e_agg^(t-1)

    Delta->>Pref: Delta就绪
    Pref->>Pref: [2.23-2.24] 客户端累加<br/>ct_prefetch=Σ_{k=1}^R δ^(k)<br/>e_prefetch=Σ_{k=1}^R e_δ^(k)<br/>‖e_prefetch‖≤R·B_δ

    Pref->>Dec: 请求解密
    Dec->>Dec: [2.25-2.28] 部分解密<br/>D_i=sk_i·c_1+e_smudge<br/>λ_j=∏(-k)/(j-k)<br/>m_combined=c_0+Σλ_j·D_j<br/>=m+e_prefetch+e_total_smudge

    Dec->>Decode: 组合明文
    Decode->>Decode: [2.29-2.30] CKKS解码<br/>Δw_cum=(1/Δ)·σ(π(m_combined))<br/>w_sync=w_base+Δw_cum
```

---

## 第三篇：安全防御方案

### 图3.1 攻击向量全景

```mermaid
sequenceDiagram
    autonumber
    participant Attacker as 恶意AS
    participant C as C_normal<br/>(正常客户端)
    participant Ct as C_target<br/>(目标客户端)

    rect rgb(255, 230, 230)
        Note over Attacker,Ct: ATTACK-1: 选择性Delta伪造
        Attacker->>Attacker: 维护两套delta<br/>δ_correct = ct_agg^(t)-ct_agg^(t-1)<br/>δ_malicious = δ_correct + Enc(Δpoison)
        Attacker->>C: 发送 δ_correct
        Attacker->>Ct: 发送 δ_malicious
        Note right of Ct: 模型被引导偏离
    end

    rect rgb(255, 240, 230)
        Note over Attacker,Ct: ATTACK-2: Delta重放
        Attacker->>Attacker: 记录 δ^(t) (Round t)
        Attacker->>Ct: Round t+k 重放 δ^(t)
        Note right of Ct: 模型回退到t轮状态
    end

    rect rgb(255, 245, 230)
        Note over Attacker,Ct: ATTACK-3: Delta放大
        Attacker->>Attacker: δ* = α·δ (α>1)<br/>同态标量乘
        Attacker->>Ct: 发送 δ*
        Note right of Ct: 长期累积导致发散
    end

    rect rgb(255, 250, 230)
        Note over Attacker,Ct: ATTACK-4: 缓存污染
        Attacker->>Ct: 发送大量伪造小delta
        Ct->>Ct: ct_prefetch += Σδ_fake
        Note right of Ct: 累积效应显著
    end
```

### 图3.2 TPW防御

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS
    participant W1 as WN_1
    participant W2 as WN_2
    participant Wt as WN_tw
    participant C as C_j

    AS->>AS: [3.1] 生成Delta后请求签名<br/>h = SHA256(δ^(t).serialize()||t||τ||pk_agg)

    AS->>W1: [3.2] 发送哈希<br/>("SignRequest", h, t)
    W1->>W1: [3.3] 验证并签名<br/>if t > last_signed_round[AS]:<br/>&nbsp;&nbsp;σ_1 = H(h)^{sk_WN_1}<br/>else: REJECT
    W1-->>AS: [3.4] 返回 σ_1

    AS->>W2: [3.5] 发送哈希
    W2->>W2: [3.6] 签名 σ_2 = H(h)^{sk_WN_2}
    W2-->>AS: [3.7] 返回 σ_2

    Note over AS,Wt: ... 重复至收集 t_w 个签名 ...

    AS->>Wt: [3.8] 发送哈希
    Wt->>Wt: [3.9] 签名 σ_tw = H(h)^{sk_WN_tw}
    Wt-->>AS: [3.10] 返回 σ_tw

    AS->>AS: [3.11] 聚合签名<br/>Σ = ∏_{k∈T} σ_k^{λ_k} = H(h)^x

    AS->>C: [3.12] 广播带签名的Delta<br/>(δ^(t), Σ, t, τ)

    C->>C: [3.13] 验证<br/>h' = SHA256(δ^(t)||t||τ||pk_agg)<br/>e(Σ,g_2) == e(H(h'),PK)?<br/>t > last_accepted_round?

    alt 验证通过且t最新
        C->>C: [3.14] ACCEPT → ct_prefetch += δ^(t)
    else 重放
        C->>C: [3.15] REJECT_REPLAY
    else 伪造
        C->>C: [3.16] REJECT_FORGERY
    end
```

### 图3.3 ACD认证

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS
    participant C as C_j

    AS->>AS: [3.17] 生成认证标签<br/>h = SHA256(m^(t))<br/>nonce ← {0,1}^96<br/>(c_tag, tag) = AES-GCM_{k_auth}(h, nonce)

    AS->>C: [3.18] 广播带标签的Delta<br/>(δ^(t), c_tag, nonce, t)

    C->>C: [3.19] 接收并缓存<br/>ct_prefetch += δ^(t)<br/>store (c_tag, nonce)

    Note over C: 训练前解密时验证

    C->>C: [3.20] 解密得到 m'<br/>h' = SHA256(m')
    C->>C: AES-GCM_{k_auth}.Verify(c_tag, tag, nonce)

    alt 验证通过
        C->>C: [3.21] ACCEPT → apply update
    else 验证失败
        C->>C: [3.22] REJECT → rollback to last verified state
    end
```

### 图3.4 ZKPP零知识证明

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS (Prover)
    participant C as C_j (Verifier)

    AS->>AS: [3.23] 构造约束电路 C(x,w):<br/>x = (pk_agg, h_old, h_new, δ^(t))<br/>w = (w^(t), w^(t-1), v, e_0, e_1, {w_i})<br/>约束:<br/>1. δ^(t)_0 = b_agg·v+e_0+(w^(t)-w^(t-1))<br/>2. δ^(t)_1 = a·v+e_1<br/>3. w^(t) = Σ_i w_i·w_i^(local)<br/>4. ‖e_0‖≤B_err, ‖e_1‖≤B_err<br/>5. h_old = Commit(w^(t-1))<br/>6. h_new = Commit(w^(t))

    AS->>AS: [3.24] 生成证明<br/>π ← ZK.Prove(C, x, w)

    AS->>C: [3.25] 广播<br/>(δ, π, x)

    C->>C: [3.26] 验证证明<br/>b ← ZK.Verify(C, x, π)

    alt b == True
        C->>C: [3.27] ACCEPT → ct_prefetch += δ^(t)
    else
        C->>C: [3.28] REJECT
    end
```

---

## 第四篇：SRCA通信优化

### 图4.1 客户端残差累积

```mermaid
sequenceDiagram
    autonumber
    participant C as C_i<br/>SRCA客户端

    C->>C: [4.1] 初始化<br/>r_i^(0) = 0

    loop 每轮训练
        C->>C: [4.2] 输入 raw_gradient Δw_i^(t)

        C->>C: [4.3] 残差合成<br/>g_i^(t) = Δw_i^(t) + γ·r_i^(t-1)

        C->>C: [4.4] 包级稀疏化<br/>(idx, g_sparse, mask) = SparseBatches(g_i^(t), s)

        C->>C: [4.5] CKKS加密<br/>ct_i^(t) = Enc_pk_agg(g_sparse)

        C->>C: [4.6] 残差更新<br/>for each batch b:<br/>&nbsp;&nbsp;if mask[b]==1: r_i^(t)[b]=0<br/>&nbsp;&nbsp;else: r_i^(t)[b]=g_i^(t)[b]

        C->>C: [4.7] 衰减 (可选)<br/>r_i^(t) = γ·r_i^(t)
    end

    C->>C: [4.8] 输出 ct_i^(t), r_i^(t)
```

### 图4.2 服务器聚合与残差补偿

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS<br/>SRCA服务器
    participant C as C_j

    AS->>AS: [4.9] 输入 {(ct_i, mask_i)}_{i∈S_t}

    AS->>AS: [4.10] 按batch分桶聚合<br/>for each batch b:<br/>&nbsp;&nbsp;participants = {i | mask_i[b]=1}

    alt |participants| > 0
        AS->>AS: [4.11] 正常聚合<br/>ct_agg[b] = WeightedAvg({ct_i[b]}, {w_i})
    else
        AS->>AS: [4.12] 全局残差补偿<br/>ct_agg[b] = R_global^(t-1)[b]
    end

    AS->>AS: [4.13] 更新全局残差<br/>for each batch b:<br/>&nbsp;&nbsp;if |participants|==0:<br/>&nbsp;&nbsp;&nbsp;&nbsp;R_global[b] = γ_R·R_global[b] + FreshResidual<br/>&nbsp;&nbsp;else:<br/>&nbsp;&nbsp;&nbsp;&nbsp;R_global[b] = γ_R·R_global[b]

    AS->>AS: [4.14] 生成Delta<br/>δ^(t) = ct_agg^(t) - ct_agg^(t-1)

    AS->>AS: [4.15] 残差感知预取调度<br/>for j∉S_t:<br/>&nbsp;&nbsp;priority[j] = α·‖r_j‖ + (1-α)·feasible[j]

    AS->>AS: [4.16] PrefSet = TopK(priority, budget)

    AS->>C: [4.17] 广播预取<br/>for j in PrefSet: AS→C_j: δ^(t)
```

---

## 融合方案：SecureRes-Fetch 总流程

### 图5.1 端到端完整流程

```mermaid
sequenceDiagram
    autonumber
    participant KGC as KGC
    participant AS as AS
    participant C as C_i
    participant AN as AN_j
    participant WN as WN_k
    participant M as Monitor

    rect rgb(230, 255, 230)
        Note over KGC,M: PHASE 0: 系统初始化
        KGC->>KGC: [P0-1] ThresholdCKKS.KeyGen(λ,n,t)
        KGC->>AS: [P0-2a] pk_agg, evk
        KGC->>C: [P0-2b] sk_i
        KGC->>AN: [P0-2c] sk_j
        KGC->>WN: [P0-2d] sk_WN_k, vk_WN
        KGC->>KGC: [P0-3] KGC.ShredKeys()<br/>KGC永久离线
    end

    rect rgb(230, 245, 255)
        Note over KGC,M: PHASE 1: 主训练循环 (Round t)

        C->>C: [P1-1] 检查预取缓存<br/>if ct_prefetch≠∅: goto [P1-19]<br/>else: w_sync←w_base

        C->>C: [P1-2] 本地训练<br/>w_i=LocalTrain(D_i,w_sync,E)<br/>Δw_i=w_i-w_sync

        C->>C: [P1-3] SRCA残差合成<br/>g_i=Δw_i+γ·r_i

        C->>C: [P1-4] 包级稀疏化<br/>(idx,g_sparse,mask)=Sparse(g_i,s)

        C->>C: [P1-5] 自适应稀疏率<br/>s=AdaptiveSparsity(t,T)

        C->>C: [P1-6] CKKS加密<br/>ct_i=Enc_pk_agg(g_sparse)

        C->>AS: [P1-7] 上传密文<br/>(ct_i,mask_i) via TLS

        AS->>AS: [P1-8] 同态聚合<br/>按batch聚合，空batch用R_global补偿

        AS->>AS: [P1-9] 更新全局残差<br/>R_global←γ_R·R_global+FreshResidual

        AS->>AS: [P1-10] 计算Delta<br/>δ^(t)=ct_agg^(t)-ct_agg^(t-1)

        AS->>WN: [P1-11] 请求TPW签名<br/>h=SHA256(δ^(t)||t||pk_agg)

        WN->>WN: [P1-12] 签名<br/>σ_k=H(h)^{sk_WN_k}
        WN-->>AS: 返回σ_k

        AS->>AS: [P1-13] 聚合签名<br/>Σ=BLS.Combine({σ_k})

        AS->>AS: [P1-14] 残差感知预取调度<br/>PrefSet=BandwidthAwareSchedule(...)

        AS->>C: [P1-15] 广播预取<br/>(δ^(t),Σ,t,metadata)

        C->>C: [P1-16] 验证<br/>Verify_BLS(Σ,vk_WN,h)<br/>检查t>last_accepted

        C->>C: [P1-17] 若通过: ct_prefetch+=δ^(t)

        alt 阈值解密触发
            C->>C: [P1-19] 计算自身份额<br/>D_i=sk_i·c_1+e_smudge
            C->>AN: [P1-20] 请求外部份额
            AN->>AN: 计算 D_j=sk_j·c_1+e_smudge
            AN-->>C: 返回 D_j
            C->>C: [P1-21] 拉格朗日组合<br/>m=c_0+Σλ_j·D_j
            C->>C: [P1-22] 解码<br/>Δw_cum=CKKS.Decode(m)
            C->>C: [P1-23] 应用更新<br/>w_sync=w_base+Δw_cum<br/>ct_prefetch=∅, w_base=w_sync
        end

        C->>C: [P1-24] 本地训练 (继续)<br/>...回到P1-3
    end

    rect rgb(255, 245, 230)
        Note over KGC,M: 异常处理路径

        alt TPW验证失败
            C->>C: [E-2] 丢弃δ
            C->>M: [E-3] 报告SuspiciousDelta
        else 重放攻击
            C->>C: [E-7] 丢弃δ，记录日志
        else 预算不足(Budget<θ_boot)
            C->>AS: [E-11] RequestFullSync
            AS->>C: [E-12] ct_agg^(t) (完整密文)
            C->>C: [E-13] 单轮解密 (安全)
        end
    end

    rect rgb(255, 230, 255)
        Note over KGC,M: PHASE 2: 训练结束
        C->>C: [P2-1] 最终模型<br/>w_final=w_base+ThresholdDecrypt(ct_prefetch_residual)
    end
```

### 图5.2 多轮预取累积示例

```mermaid
sequenceDiagram
    autonumber
    participant AS as AS
    participant C3 as C_3<br/>(未选中客户端)
    participant C1 as C_1

    Note over AS,C1: Round 1
    AS->>C3: δ^(1)
    C3->>C3: ct = δ^(1)

    Note over AS,C1: Round 2
    AS->>C3: δ^(2)
    C3->>C3: ct = δ^(1)+δ^(2)

    Note over AS,C1: Round 3
    AS->>C1: δ^(3) (C_1未选中)
    C1->>C1: ct = δ^(3)

    Note over AS,C1: C_3被选中！
    C3->>AS: Request δ^(3)
    AS->>C3: δ^(3)
    C3->>C3: ct = (δ^(1)+δ^(2))+δ^(3)
    C3->>C3: ThresholdDecrypt(ct)→Δw_cum
    C3->>C3: w_sync=w_base+Δw_cum<br/>ct=∅, w_base=w_sync
    C3->>C3: 训练 → 上传

    Note over AS,C1: Round 4 (C_3连续选中)
    C3->>C3: ct=∅, w_sync=w_base<br/>直接训练 → 上传
```
```

---

*使用方法：将上述代码块中的内容复制到 [Mermaid Live Editor](https://mermaid.live) 或任何支持 Mermaid 的 Markdown 渲染器中即可看到渲染后的时序图。*
