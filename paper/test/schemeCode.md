# CipherFetch 方案伪代码（Markdown 格式）

> 本文档提供 5 个核心算法的伪代码，与代码实现精确对应，可直接用于论文。

---

## 算法 1: TEE-Based Aggregation with Global Residual

**输入**: 
- 旧全局密文 $\text{CT}_t^{\text{global}}$（完整模型，所有 batch）
- 客户端上传集合 $\{\text{CT}_{i,t}^{\text{up}}\}_{i=1}^{m}$（稀疏格式，含 mask）
- 客户端权重 $\{\alpha_i\}_{i=1}^{m}$
- 下行压缩率 $\rho_d$，全局残差 $\mathbf{R}_t$（TEE 内部状态）

**输出**: 稀疏新全局密文 $\text{CT}_{t+1}^{\text{global}}$（仅含选中 batch）

```
Algorithm 1: TEE-Based Aggregation with Global Residual
─────────────────────────────────────────────────────────
1:  function TEE_Aggregate(CT_t^global, {CT_i,t^up}, {α_i}, ρ_d, R_t)
2:      // Step 1: Decrypt inside TEE
3:      {W_t^(k)} ← Decrypt(CT_t^global)          ▷ 解密旧全局模型 → K batches
4:      K ← number of batches in {W_t^(k)}
5:      
6:      // Step 2: Decrypt client uploads
7:      for each client i ∈ [1, m] do
8:          {u_i,k} ← Decrypt(CT_i,t^up)           ▷ mask=1 的位置有值, mask=0 为 0
9:      end for
10:     
11:     // Step 3: Per-batch weighted aggregation
12:     for each batch position k ∈ [0, K-1] do
13:         vals ← {u_i,k | u_i,k ≠ 0}
14:         if vals is empty then
15:             δ̄_t,k ← 0
16:         else
17:             δ̄_t,k ← Σ_i α_i · u_i,k            ▷ weighted average
18:         end if
19:     end for
20:     
21:     // Step 4: Add global residual
22:     for each k ∈ [0, K-1] do
23:         δ̃_t,k ← δ̄_t,k + R_t,k
24:     end for
25:     
26:     // Step 5: Top-K secondary compression
27:     S_t^down ← TopK_ρd({‖δ̃_t,k‖₁}_{k=0}^{K-1})
28:     
29:     // Step 6: Update global residual
30:     for each k ∈ [0, K-1] do
31:         if k ∈ S_t^down then
32:             R_{t+1,k} ← 0
33:         else
34:             R_{t+1,k} ← δ̃_t,k
35:         end if
36:     end for
37:     
38:     // Step 7: Update global model and re-encrypt
39:     for each k ∈ [0, K-1] do
40:         if k ∈ S_t^down then
41:             W_{t+1}^(k) ← W_t^(k) + δ̃_t,k
42:         else
43:             W_{t+1}^(k) ← W_t^(k)
44:         end if
45:     end for
46:     
47:     // Step 8: Encrypt only selected batches
48:     CT_{t+1}^global ← {Enc(W_{t+1}^(k)) | k ∈ S_t^down}
49:     mask ← [1 if k ∈ S_t^down else 0 for k in 0..K-1]
50:     
51:     return CT_{t+1}^global, mask, R_{t+1}
52: end function
```

**关键说明**:
- TEE 内部全程明文运算，Host 无法访问 TEE 内存（接口边界）
- 全局残差 $\mathbf{R}_t$ 存储在 TEE 内部，Host 不可见
- 仅返回选中的 batch 密文，未选中 batch 的信息保留在残差中

---

## 算法 2: Sparse Encrypted Update Merging

**输入**: 
- 两个稀疏加密更新 $\text{enc}_1 = (\mathbf{cts}_1, \mathbf{m}_1)$, $\text{enc}_2 = (\mathbf{cts}_2, \mathbf{m}_2)$
- 同态评估器 $\mathcal{E}$（可选，服务器端使用）

**输出**: 合并后的稀疏加密更新 $\text{enc}_{\text{merged}}$

```
Algorithm 2: Sparse Encrypted Update Merging
─────────────────────────────────────────────
1:  function MergeSparseUpdates(enc_1, enc_2, ℰ)
2:      mask_1 ← enc_1.mask,   mask_2 ← enc_2.mask
3:      cts_1  ← enc_1.ciphertexts,  cts_2 ← enc_2.ciphertexts
4:      K ← length(mask_1)              ▷ total batch count
5:      
6:      merged_mask ← [0] × K
7:      merged_cts  ← empty list
8:      idx_1 ← 0,  idx_2 ← 0
9:      
10:     for each batch position i ∈ [0, K-1] do
11:         has_1 ← (mask_1[i] == 1)
12:         has_2 ← (mask_2[i] == 1)
13:         
14:         if has_1 AND has_2 then
15:             // Both have this batch: homomorphic addition
16:             if ℰ ≠ null then
17:                 ct_sum ← ℰ.Add(cts_1[idx_1], cts_2[idx_2])
18:             else
19:                 ct_sum ← cts_1[idx_1] ⊕ cts_2[idx_2]   ▷ client-side +
20:             end if
21:             merged_cts.append(ct_sum)
22:             merged_mask[i] ← 1
23:             idx_1 ← idx_1 + 1,  idx_2 ← idx_2 + 1
24:             
25:         else if has_1 then
26:             // Only enc_1 has this batch: direct reference (no +0)
27:             merged_cts.append(cts_1[idx_1])
28:             merged_mask[i] ← 1
29:             idx_1 ← idx_1 + 1
30:             
31:         else if has_2 then
32:             // Only enc_2 has this batch: direct reference (no +0)
33:             merged_cts.append(cts_2[idx_2])
34:             merged_mask[i] ← 1
35:             idx_2 ← idx_2 + 1
36:         end if
37:         // else: neither has this batch, skip (mask remains 0)
38:     end for
39:     
40:     return {__sparse__: true, ciphertexts: merged_cts, 
41:             mask: merged_mask, batch_size: enc_1.batch_size, ...}
42: end function
```

**关键说明**:
- `has_1 AND has_2` 分支执行同态加法 $\oplus$（噪声线性叠加）
- `has_1 XOR has_2` 分支**直接引用原密文**，避免 `+0` 引入额外噪声
- 时间复杂度 $O(K)$，空间复杂度 $O(|\mathcal{S}_1 \cup \mathcal{S}_2|)$

---

## 算法 3: Client-Side Prefetch Accumulation

**输入**: 
- 客户端本地预取状态 $\mathbf{P}_t^c$（稀疏加密格式，可能为 null）
- 服务器推送的密文增量 $\boldsymbol{\delta}_t$（稀疏格式）
- 当前轮次 $t$，客户端选中状态 $\text{is\_selected}$

**输出**: 更新后的预取状态 $\mathbf{P}_{t+1}^c$，或应用后的模型参数

```
Algorithm 3: Client-Side Prefetch Accumulation
──────────────────────────────────────────────
1:  function ClientPrefetch(P_t^c, δ_t, t, is_selected, ckks_mgr)
2:      
3:      // ── Branch A: Idle client receives prefetch delta ──
4:      if NOT is_selected AND δ_t ≠ null then
5:          if P_t^c == null then
6:              // First prefetch: initialize accumulator
7:              P_{t+1}^c ← Deserialize(δ_t)
8:          else
9:              // Accumulate via homomorphic addition
10:             P_{t+1}^c ← MergeSparseUpdates(P_t^c, δ_t, ℰ=null)
11:         end if
12:         num_prefetched ← num_prefetched + 1
13:         received_rounds.append(t)
14:         return P_{t+1}^c
15:     end if
16:     
17:     // ── Branch B: Selected client fetches remaining deltas ──
18:     if is_selected then
19:         fetch_info ← Server.GetRemainingDeltas(client_id, t)
20:         for each delta_dict in fetch_info.deltas do
21:             δ_rem ← Deserialize(delta_dict)
22:             if P_t^c == null then
23:                 P_t^c ← δ_rem
24:             else
25:                 P_t^c ← MergeSparseUpdates(P_t^c, δ_rem, ℰ=null)
26:             end if
27:         end for
28:         
29:         // ── Step: Apply accumulated state (single decryption) ──
30:         if P_t^c ≠ null then
31:             Δ_plain ← ckks_mgr.Decrypt(P_t^c)      ▷ ONE decryption
32:             W_base ← W_base + Δ_plain               ▷ apply to base model
33:             P_t^c ← null                            ▷ clear accumulator
34:             num_prefetched ← 0
35:             received_rounds ← []
36:         end if
37:         
38:         // ── Step: Local training ──
39:         Δ_local ← LocalTrain(W_base)
40:         CT_up ← ckks_mgr.SparseEncrypt(Δ_local)    ▷ upload sparse update
41:         return CT_up
42:     end if
43:     
44: end function
```

**关键说明**:
- Idle 客户端执行**同态加法累加**（不解密），噪声线性增长
- 被选中时执行**单次解密**应用所有预取增量（Amortized cost）
- `MergeSparseUpdates` 支持 mask 对齐：不同轮次的稀疏 delta 可能有不同的 mask

---

## 算法 4: Sticky Sampling with T-Percentile Scheduling

**输入**: 
- 候选客户端集合 $\mathcal{C}$（预采样池）
- 当前轮次 $t_{\text{cur}}$，目标轮次 $t_{\text{target}} = t_{\text{cur}} + W$
- 客户端上次同步轮次 $\{\text{last\_sync}_i\}$
- EMA 轮次耗时 $\bar{T}_{\text{round}}$，松弛系数 $\beta$，过承诺比例 $\gamma$

**输出**: 预取调度表 $\{\text{start\_round}_i\}_{i \in \mathcal{C}}$

```
Algorithm 4: Sticky Sampling with T-Percentile Scheduling
──────────────────────────────────────────────────────────
1:  function SchedulePrefetch(𝒞, t_cur, {last_sync_i}, T̄_round, β, γ, W)
2:      t_target ← t_cur + W
3:      prefetch_schedule ← {i: t_cur for i in 𝒞}
4:      r_min ← t_cur
5:      𝒞_finish ← 𝒞
6:      T_percentile ← +∞
7:      
8:      for r ∈ [t_cur, t_cur + W] do
9:          // Estimate fetch time for each client if starting from r
10:         fetch_times ← {
11:             i: EstimateFetchTime(i, r, r_min, last_sync_i, t_cur)
12:             for i in 𝒞_finish
13:         }
14:         
15:         if T_percentile == +∞ then
16:             pct ← 100 × (1 + β×(γ-1)) / γ
17:             T_percentile ← Percentile(fetch_times.values(), pct)
18:             // First filter: keep clients with fetch_time < T_percentile
19:             𝒞_finish ← {i ∈ 𝒞_finish | fetch_times[i] < T_percentile}
20:         end if
21:         
22:         // Subsequent filter: keep clients with fetch_time ≤ T_percentile
23:         𝒞_finish ← {i ∈ 𝒞_finish | fetch_times[i] ≤ T_percentile}
24:         
25:         // If all original clients can finish, raise r_min
26:         if |𝒞_finish| == |𝒞| then
27:             r_min ← min(r, t_target)
28:             T_percentile ← Percentile(fetch_times.values(), pct)
29:         end if
30:         
31:         // Set start_round for clients that can finish
32:         for i ∈ 𝒞_finish do
33:             prefetch_schedule[i] ← r
34:         end for
35:         
36:         if 𝒞_finish is empty then
37:             break
38:         end if
39:     end for
40:     
41:     // Rollback failed clients to earliest start
42:     for i ∈ 𝒞 \ 𝒞_finish do
43:         prefetch_schedule[i] ← r_min
44:     end for
45:     
46:     return prefetch_schedule, r_min
47: end function
48: 
49: function EstimateFetchTime(client_id, start, r_min, last_sync, t_cur)
50:     dl_bw ← BandwidthSimulator.GetDLBandwidth(client_id)   ▷ bits/s
51:     if dl_bw ≤ 0 then return +∞ end if
52:     
53:     round_dl ← T̄_round × dl_bw
54:     // Size of updates from last_sync to start
55:     update_size ← SizeEvaluator.Estimate(last_sync, start)
56:     t_target ← t_cur + W
57:     l ← start
58:     
59:     for j ∈ [start, t_target) do
60:         time_budget ← T̄_round
61:         time_budget ← max(0, time_budget - update_size / dl_bw)
62:         
63:         if time_budget > 0 then
64:             next_delta ← SizeEvaluator.Estimate(l, j)
65:             update_size ← max(0, next_delta - time_budget × dl_bw)
66:             l ← j + 1
67:         else
68:             update_size ← update_size - round_dl
69:         end if
70:     end for
71:     
72:     final_delta ← SizeEvaluator.Estimate(l, t_target - 1)
73:     remaining ← update_size + final_delta
74:     return remaining / dl_bw
75: end function
```

**关键说明**:
- `T_percentile` 公式: $\text{pct} = 100 \times \frac{1 + \beta(\gamma-1)}{\gamma}$
- 当 $\gamma = 1$（无过承诺）时，$\text{pct} = 100$，等价于 $T_{\max}$
- 当 $\gamma = 2, \beta = 0.5$ 时，$\text{pct} = 75$，取第 75 百分位
- 带宽不足的客户端被回退到 `r_min`（最早开始预取）

---

## 算法 5: Complete CipherFetch FL Round

**输入**: 
- 全局状态（服务器）: 加密全局模型 $\text{CT}_t^{\text{global}}$，TEE 处理器 $\mathcal{T}$
- 客户端集合: $\{c_i\}_{i=1}^{C}$，采样率 $q$， sticky 分数 $\{\text{score}_i\}$
- Prefetch 调度器 $\mathcal{S}$，带宽模拟器 $\mathcal{B}$

**输出**: 更新后的全局模型 $\text{CT}_{t+1}^{\text{global}}$，虚拟时钟增量

```
Algorithm 5: Complete CipherFetch FL Round
──────────────────────────────────────────
1:  function CipherFetchRound(t, CT_t^global, {c_i}, q, {score_i}, 𝒯, 𝒮, ℬ)
2:      
3:      // ── Phase 1: Client Selection ──
4:      m ← ⌈C × q⌉                              ▷ number of selected clients
5:      n_pool ← ⌈m × γ⌉                         ▷ sticky pool size
6:      𝒞_selected ← StickySelect({c_i}, m, n_pool, {score_i})
7:      
8:      // ── Phase 2: Fetch' + Apply (selected clients) ──
9:      for each client c_i ∈ 𝒞_selected do
10:         c_i.FetchRemainingDeltas()            ▷ download missing deltas
11.         c_i.ApplyPrefetchedState()            ▷ ONE decryption + apply
12.         W_i ← c_i.GetModel()                   ▷ now at latest global state
13.     end for
14.     
15.     // ── Phase 3: Local Training ──
16.     updates ← empty list
17.     for each client c_i ∈ 𝒞_selected do
18.         Δ_i ← c_i.LocalTrain(W_i, num_epochs)
19.         CT_i^up ← c_i.SparseEncrypt(Δ_i)       ▷ upload difference
20.         updates.append(CT_i^up)
21.     end for
22.     
23.     // ── Phase 4: TEE Aggregation ──
24.     CT_tee, mask, R_{t+1} ← 𝒯.Aggregate(
25.         CT_t^global, updates, {α_i}, ρ_d, R_t
26.     )
27.     
28.     // ── Phase 5: Host computes sparse delta ──
29.     δ_t^sparse ← HomomorphicSubtract(CT_tee, CT_t^global, mask)
30.     StoreDeltaToHistory(t, δ_t^sparse)
31.     
32.     // ── Phase 6: Merge TEE result to global state ──
33.     CT_{t+1}^global ← MergeToGlobal(CT_t^global, CT_tee, mask)
34.     
35.     // ── Phase 7: Prefetch Scheduling & Broadcast ──
36.     𝒞_future ← StickyPreSample({c_i}, m, n_pool, t+W)
37.     {start_i}, r_min ← 𝒮.SchedulePrefetch(
38.         𝒞_future, t, {last_sync_i}, T̄_round, β, γ, W
39.     )
40.     
41.     // Broadcast delta to clients who should prefetch starting now
42.     for each client c_j ∈ {i ∈ 𝒞_future | start_i == t} do
43.         if BandwidthCheck(c_j, δ_t^sparse) then
44.             c_j.ReceivePrefetchDelta(δ_t^sparse, t)
45.         end if
46.     end for
47.     
48.     // ── Phase 8: Update sticky scores ──
49.     for each client c_i do
50.         if c_i ∈ 𝒞_future \ 𝒞_selected then
51.             score_i ← score_i + 1                 ▷ prefetched but not selected
52.         else if c_i ∈ 𝒞_selected then
53.             score_i ← score_i × β_decay            ▷ decay after selection
54.         end if
55.     end for
56.     
57.     // ── Phase 9: Virtual clock update ──
58.     upload_times ← {ℬ.EstimateUploadTime(c_i, CT_i^up) | c_i ∈ 𝒞_selected}
59.     train_times  ← {c_i.train_time | c_i ∈ 𝒞_selected}
60.     fetch_times  ← {c_i.fetch_time | c_i ∈ 𝒞_selected}
61.     round_duration ← max_i {fetch_times[i] + train_times[i] + upload_times[i]}
62.     virtual_clock ← virtual_clock + round_duration
63.     
64.     return CT_{t+1}^global, R_{t+1}, virtual_clock
65. end function
```

**关键说明**:
- 被选中的客户端执行 **Fetch' → Apply → Compute → Upload** 流水线
- 未被选中的客户端在后台执行 **Prefetch**（同态累加，不解密）
- TEE 负责明文聚合 + 二次压缩，Host 负责密文减法和 Prefetch 广播
- 虚拟时钟模拟真实 wall-clock 时间，受最慢客户端瓶颈制约

---

## 附录: 符号速查

| 符号 | 含义 |
|------|------|
| $\text{CT}$ / $\text{ct}$ | CKKS 密文（全局模型 / 单个 batch） |
| $\oplus$ | 同态加法 |
| $\mathcal{T}$ | TEE 处理器（可信执行环境） |
| $\mathcal{S}$ | Prefetch 调度器 |
| $\mathcal{B}$ | 带宽模拟器 |
| $\mathbf{R}_t$ | TEE 全局残差（内部状态） |
| $\mathbf{P}_t^c$ | 客户端 $c$ 的预取累加器 |
| $\rho_d$ / $\rho_u$ | 下行 / 上行稀疏率 |
| $\gamma$ / $\beta$ | 过承诺比例 / 松弛系数 |
| $W$ | 预取窗口大小 |
| $K$ | 总 batch 数 |
| $m$ | 每轮选中客户端数 |
