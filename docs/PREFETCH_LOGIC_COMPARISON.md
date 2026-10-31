# FedFetch vs CipherFetch 预取逻辑对比分析

> 本文档对比 **FedFetch 原始预取逻辑**（来自 `FedFetch-main/examples/prefetch/`）与 **当前项目 CipherFetch（CKKS-Fed）的预取逻辑**，分别给出示例流程，并从多个维度进行系统性对比，最后指出当前实现中存在的已知问题和逻辑缺陷。

---

## 一、FedFetch 预取逻辑示例流程

### 1.1 核心假设与数据格式

FedFetch 建立在 **FedScale** 框架之上，其核心假设：
- **数据格式**：服务器与客户端之间传输的是 **压缩后的明文梯度/模型差分**（`torch.Tensor` → `numpy.ndarray`），而非密文。
- **压缩栈**：支持 TopK/STC 稀疏化 + QSGD/EDEN/ECUQ/PowerSGD 量化/分解压缩。
- **预取单元**：每一轮聚合后，服务器生成一个 **压缩后的全局梯度更新**（`compressed_gradient`），并保存到队列中。
- **客户端透明性**：客户端完全不知道预取的存在，它每次接收的都是一个**完整的、可直接用于本地训练的模型权重**。

### 1.2 示例：3 客户端、5 轮训练的预取流程

**场景设定**：
- 客户端 A, B, C；每轮采样 2 个（K=2），OC=1.3，预取窗口 `max_prefetch_round=3`。
- 带宽：A 快，B 中，C 慢。

**Round 1**（Warmup，无预取）：
1. 服务器采样 A, B 参与训练。
2. A, B 上传本地梯度（已压缩→解压缩）。
3. 服务器聚合梯度 → `compressed_gradient[1]`，更新全局模型 → `model[1]`。
4. 保存：`server_models_queue = [model[1]]`，`server_updates_queue = [compressed_gradient[1]]`。
5. 调度器 `schedule_prefetch()` 为 Round 4（1+3）预采样：假设预采样 A, C。
   - 估计 A, C 的 fetch_time；T_percentile 计算；迭代回滚。
   - 结果：A 从 Round 2 开始预取，C 从 Round 1 开始预取（慢客户端更早开始）。

**Round 2**：
1. 服务器采样 A, B 参与训练。
2. 聚合 → `compressed_gradient[2]`，`model[2]`。
3. `server_models_queue = [model[1], model[2]]`，`server_updates_queue = [cg[1], cg[2]]`。
4. **预取调度**：为 Round 5 预采样。
5. **预取广播（背景）**：
   - C 是 Round 2 的未选中客户端，且 prefetch_schedule[C] = 1 ≤ 2。
   - 服务器通过 `get_train_update_virtual(C)` 构造 C 的预取模型：
     - `calculate_next_client_model(base_idx=0)`：以 `model[1]` 为 base，应用 `cg[2]` → 得到 `next_client_model`。
   - C 通过 gRPC 接收到这个完整模型，存在 executor 本地。

**Round 3**：
1. 采样 B, C（C 终于被选中）。
2. 聚合 → `compressed_gradient[3]`，`model[3]`。
3. **C 的训练流程**：
   - `get_train_update_virtual(C)` 返回 `next_client_model`（已包含 Round 2 的预取更新）。
   - Executor 调用 `set_train_update_virtual(model_weights)`，C 的本地模型直接加载为预取后的模型。
   - C 直接在该模型上训练，**无需手动应用任何 delta**。
4. C 上传梯度 → 服务器聚合。

**Round 4**（C 再次被选中）：
1. C 上次同步于 Round 3，期间 Round 4 的预取已经开始。
2. 服务器在 Round 4 聚合后，`server_models_queue = [..., model[4]]`。
3. `get_train_update_virtual(C)` 返回包含 Round 4 更新的完整模型。
4. C 透明接收并训练。

**关键观察**：
- 客户端始终接收 **完整模型权重**（可能是压缩后解压缩的），不是 delta。
- 服务器端维护 `server_models_queue` 和 `server_updates_queue`，通过 `calculate_next_client_model()` 动态构造客户端模型。
- 预取调度只决定 **何时开始发送预取数据**，实际数据是每轮聚合后的全局模型快照或差分。
- 压缩发生在**传输层**：模型权重被压缩后传输，客户端解压后得到完整模型。

---

## 二、CipherFetch 预取逻辑示例流程

### 2.1 核心假设与数据格式

CipherFetch 建立在 **CKKS 同态加密**（TenSEAL）之上，其核心假设：
- **数据格式**：服务器与客户端之间传输的是 **CKKS 密文**（`ts.CKKSVector`），以 `__sparse__` 字典格式封装。
- **预取单元**：每一轮聚合后，服务器生成一个 **密文增量（encrypted delta）**，表示本轮全局模型的变化量。
- **客户端有状态**：客户端维护 `prefetched_state`（密文累加器），需要**手动解密并应用**到本地模型。
- **两条路径**：
  - **标准路径**：服务器 `decrypt → plaintext delta → re-encrypt`（触碰明文）。
  - **ESAFL 路径**：直接使用聚合密文作为 delta（不触碰明文，但要求 `upload_difference=True`）。

### 2.2 示例：相同场景下的预取流程

**场景设定**：
- 客户端 A, B, C；每轮采样 2 个，OC=1.3，预取窗口 `max_prefetch_round=3`。
- 使用标准路径（非 ESAFL）。

**Round 1**（Warmup，无预取）：
1. 服务器采样 A, B 参与训练。
2. A, B 上传**密文更新**（`__sparse__` 格式）。
3. 服务器调用 `super().update_global_model(aggregated_update)`：
   - 若使用量化打包（TwoTier/CRTStack/Layerwise），触发回退：`decrypt all → plaintext avg → re-encrypt`。
   - 否则：同态逐 batch 加权平均，更新 `encrypted_global_state`。
4. `update_global_model()`（PrefetchAggregationServer 重载）：
   - 保存 `prev_plain_state = get_global_params().clone()`（明文复制）。
   - 调用父类更新后，计算 `delta_plain = current_plain - prev_plain_state`。
5. `encrypt_and_stage_prefetch()`：
   - `ckks_manager.encrypt_model_update(delta_plain, skip_sparsification=True)` → 生成密文 delta。
   - 存入 `encrypted_deltas_history[0]`。
6. 调度器 `schedule_prefetch()` 为 Round 4 预采样。

**Round 2**：
1. 服务器采样 A, B 参与训练。
2. 同态聚合 → 更新全局密文状态。
3. 再次计算明文 delta → 加密 → `encrypted_deltas_history[1]`。
4. **预取广播**：
   - C 是未选中客户端，`last_synced[C] = 0`，`prefetched[C] = 0`。
   - `missing_deltas = encrypted_deltas_history[0:2]`（Round 1 和 Round 2 的 delta）。
   - 服务器调用 `merge_sparse_encrypted_updates()` 将 2 个 delta **同态累加为 1 个累积 delta**。
   - 带宽检查：`dl_time <= ema_dur`？若通过，发送给 C。
   - C.receive_prefetch_delta()：`prefetched_state = cumulative_enc`。
   - `client_prefetch_counts[C] = 2`。

**Round 3**：
1. 采样 B, C（C 被选中）。
2. C 在训练前调用 `local_train()`：
   - `fetch_remaining_deltas()`：查询服务器 `get_remaining_fetch_info(C, 3)`。
     - `total_needed = 3 - 0 = 3`，`prefetched = 2`，`remaining = 1`。
     - 服务器返回 Round 3 的 delta（1 个）。
   - C 将该 delta 合并到 `prefetched_state`（现在包含 R1+R2+R3）。
   - `apply_prefetched_state()`：
     - **一次解密**：`decrypt_model_update(prefetched_state)` → `global_delta_plain`（明文 Dict）。
     - `base_model_state`（C 上次同步时的模型）+ `global_delta_plain` → 新全局模型。
     - 若启用 local completion：`mask = |global_delta| < 1e-3`，用 C 保存的 `last_local_full_delta` 填充。
     - 写入 `self.model`，更新 `base_model_state`。
   - C 在该模型上执行本地训练。
   - 训练后：若 local_completion_enabled，保存 `last_local_full_delta = new_params - base_after_apply`。
3. C 上传密文更新 → 服务器聚合。
4. 服务器 `record_client_sync(C, 3)`：`last_update_index[C] = 3`。

**关键观察**：
- 客户端接收的是 **密文增量（delta）**，不是完整模型。
- 客户端必须维护 `prefetched_state` 密文累加器，并在训练前**解密一次**。
- 服务器在标准路径下**必须触碰明文**（`prev_plain_state → delta_plain → encrypt`），无法避免。
- 多个缺失 delta 在服务器端预先同态合并为 1 个，客户端始终只解密 1 次。

---

## 三、对比分析

| 维度 | **FedFetch** | **CipherFetch** |
|------|-------------|-----------------|
| **传输数据格式** | 压缩后的明文模型权重/差分（`numpy.ndarray` 列表） | CKKS 密文增量（`__sparse__` 封装 `ts.CKKSVector`） |
| **预取单元** | 全局模型快照（`server_models_queue`）或压缩梯度（`server_updates_queue`） | 每轮全局模型的密文增量（`encrypted_deltas_history`） |
| **服务器 delta 计算** | 明文梯度聚合后直接保存，无需额外计算 delta | 标准路径：`prev_plain - current_plain` → 加密；ESAFL：复用聚合密文 |
| **客户端接收内容** | **完整模型权重**（透明，无需客户端感知） | **密文增量**（客户端需手动累加、解密、应用） |
| **客户端应用方式** | `model_adapter.set_weights()` 直接加载 | `decrypt → plaintext add → optional local completion → set_model_params()` |
| **服务器是否触碰明文** | **是**（本来就是明文 FL） | 标准路径：**是**（`decrypt→delta→re-encrypt`）；ESAFL：**否** |
| **调度策略** | T_percentile + 迭代回滚，支持 sticky sampling 和 overcommitment | T_percentile + 迭代回滚（移植自 FedFetch），支持 sticky/random/sketch_clustering |
| **压缩策略** | TopK/STC + QSGD/EDEN/ECUQ/PowerSGD（多层组合） | CKKS 槽位打包 + TopK 稀疏化 + 量化打包（CRTStack/TwoTier/LayerwiseQuantized） |
| **多轮缺失处理** | `calculate_next_client_model()` 从 base + deltas 构造完整模型 | `merge_sparse_encrypted_updates()` 同态累加为 1 个累积 delta |
| **带宽模型** | 基于实际压缩大小（`SizeEvaluator` 跟踪 mask union） | 基于密文大小（`CKKSSizeEvaluator` 用 dummy 模型测量） |
| **安全模型** | 无加密，依赖差分隐私或信任服务器 | CKKS 同态加密，目标：服务器不触碰明文（标准路径未达成） |
| **离线替换** | 支持（`enable_replace_offline`），从 sticky pool 选替代者 | **不支持**（未实现） |
| **错误反馈（Residual）** | 支持服务器端 residual + 客户端 compensation | **不支持** |
| **Local Completion** | **无此概念** | FedPHE 风格：用客户端本地值填充全局稀疏零位 |

### 3.1 预取数据格式对比

**FedFetch**：传输的是**压缩后的完整模型权重**或**base+diff**。客户端收到后直接 `set_weights()`，训练逻辑完全无感知。

**CipherFetch**：传输的是**密文增量**。客户端收到后必须：
1. 累加到 `prefetched_state`（同态加法）。
2. 训练前解密（一次 CKKS 解密，计算开销大）。
3. 将明文 delta 加到 `base_model_state` 上。
4. 可选 local completion。

这种差异导致 CipherFetch 的客户端侧逻辑远比 FedFetch 复杂，且解密是**计算瓶颈**。

### 3.2 服务器侧 delta 计算方式对比

**FedFetch**：无需显式计算 delta。每轮聚合后的 `compressed_gradient` 直接保存，客户端模型通过 `base_model + sum(gradients)` 构造。

**CipherFetch**：
- 标准路径：必须在明文空间计算 `delta = current - previous`，因为 TenSEAL 的透明密文问题导致**无法执行同态减法**（`new_global_enc - old_global_enc` 会产生透明密文，无法序列化/传输）。
- ESAFL 路径：若客户端上传的是差分（`upload_difference=True`），聚合结果本身就是 delta，可直接复用。

**这是 CipherFetch 最核心的安全缺陷**：标准路径下服务器必须解密全局模型、计算明文差分、再加密，违背了"服务器永不触碰明文"的设计目标。

### 3.3 客户端接收与应用方式对比

**FedFetch 的透明性**：
```python
# executor.py
model_weights = train_config["model"]  # 完整模型
self.model_adapter.set_weights(model_weights)  # 直接加载
# 客户端 train() 方法完全不需要知道预取
```

**CipherFetch 的有状态性**：
```python
# client.py
prefetched_state = merge_sparse_encrypted_updates(...)  # 密文累加
decrypted_delta = ckks_manager.decrypt_model_update(prefetched_state)  # 解密
new_model = base_model_state + decrypted_delta  # 明文加法
self.set_model_params(new_model)  # 加载
```

### 3.4 调度策略对比

两者都采用 **T_percentile 调度 + 迭代回滚**，但实现细节有差异：

| 方面 | FedFetch | CipherFetch |
|------|----------|-------------|
| `T_percentile` 公式 | `percentile = 100 × (1 + β × (OC-1)) / OC` | 相同 |
| 客户端采样策略 | Sticky + Change（维护 fast client pool） | Sticky / Random / SketchClustering |
| `max_prefetch_round` | 预采样 `max_prefetch_round` 轮后的客户端 | 相同 |
| `estimate_fetch_time` | 模拟带宽 credit 累积 | 相同逻辑，但存在 **off-by-one bug**（见第 4 节） |

### 3.5 压缩策略对比

**FedFetch 的压缩是传输核心**：
- TopK/STC 稀疏化减少非零元素数量。
- QSGD/EDEN/ECUQ 量化减少每个元素的比特数。
- PowerSGD 用低秩分解。
- 服务器跟踪 `mask_record_list` 计算 union-of-masks 的精确传输大小。

**CipherFetch 的压缩是加密辅助**：
- CKKS 天然将多个参数打包到一个密文槽位中（slot_count ≈ 8192/16384）。
- TopK 稀疏化减少 batch 数量（一个 batch 对应一个 CKKSVector）。
- 量化打包（CRTStack/TwoTier/LayerwiseQuantized）将浮点数量化为整数后再打包，进一步减少 batch 数。
- **关键问题**：当启用量化打包时，服务器聚合**回退到明文**（`decrypt→avg→re-encrypt`），失去了同态聚合的意义。

### 3.6 安全模型对比

**FedFetch**：无加密，属于传统联邦学习。安全依赖：
- 差分隐私（若启用）。
- 安全聚合（Secure Aggregation）可额外叠加，但原论文未涉及。

**CipherFetch**：目标是通过 CKKS 实现**服务器不触碰明文**。但：
- 标准路径因透明密文问题而**失败**。
- ESAFL 路径理论上可行，但要求 `upload_difference=True` 且 ESAFL 适配器正确实现。
- 量化打包的回退路径再次**暴露明文**。

### 3.7 多轮缺失处理对比

**FedFetch**：
- 客户端 `last_update_index` 跟踪上次同步轮次。
- 若缺失多轮，`calculate_size_base_and_delta()` 计算 base 模型 + 所有缺失 deltas 的大小。
- 实际传输时，`get_train_update_virtual()` 返回一个**已经构造好的完整模型**。

**CipherFetch**：
- 同样跟踪 `last_update_index` 和 `client_prefetch_counts`。
- 服务器端用 `merge_sparse_encrypted_updates()` 将多个缺失 deltas **同态累加为 1 个**。
- 客户端只需解密 1 次，无论缺失多少轮。
- **优势**：同态加法不改变密文大小（单个 batch 层面），理论上比 FedFetch 传输逐轮 delta 更高效。

---

## 四、当前实现存在的问题与逻辑缺陷

### 4.1 标准路径下的明文泄露（安全缺陷）

**位置**：`server.py:update_global_model()`（标准路径）

**问题**：
```python
prev_plain_state = {k: v.clone() for k, v in self.get_global_params().items()}
super().update_global_model(aggregated_update, learning_rate)
delta_plain = {name: current_plain_state[name] - prev_plain_state[name] for name in prev_plain_state}
encrypted_delta = ckks_manager.encrypt_model_update(delta_plain, skip_sparsification=True)
```

服务器在每一步预取中都必须：
1. 解密当前全局密文状态（`get_global_params()` 内部调用 `decrypt_model_update`）。
2. 保存明文副本。
3. 计算明文差分。
4. 重新加密。

**后果**：
- 服务器**每轮都触碰全局模型明文**，完全违背了同态加密 FL 的安全假设。
- 仅 ESAFL 路径（`upload_difference=True`）可避免此问题。

**根因**：TenSEAL 中，两个用相同公钥/相同 context 加密的密文相减会产生 **transparent ciphertext**（透明密文），TenSEAL 拒绝序列化/传输此类密文。因此无法直接计算 `delta_enc = new_global_enc - old_global_enc`。

**修复方向**：
- 强制使用 ESAFL 路径（`upload_difference=True`）。
- 或换用支持 transparent ciphertext 的 CKKS 库（如 Microsoft SEAL 的 C++ API 可直接处理）。
- 或改用**多密钥 CKKS**（ESAFL 的 native 模式），但 TenSEAL 不支持。

---

### 4.2 ESAFL 路径的边界条件缺失

**位置**：`server.py:update_global_model()`（ESAFL 分支）

**问题**：
```python
if self.esafl_enabled and self._is_encrypted_update(aggregated_update):
    self.current_delta_encrypted_esafl = aggregated_update
```

代码假设 `aggregated_update` 一定是 delta（即 `upload_difference=True`）。但如果 `upload_difference=False`，客户端上传的是**完整模型**，聚合结果也是完整模型，而非 delta。

**后果**：服务器会错误地将一个**完整模型的密文**当作 delta 存入 `encrypted_deltas_history`，导致客户端应用后模型参数爆炸（delta 语义错误）。

**修复**：在 ESAFL 分支中增加断言或条件检查：
```python
assert self.upload_difference, "ESAFL prefetch requires upload_difference=True"
```

---

### 4.3 Fetch 阶段合并后大小测量不一致

**位置**：`server.py:get_remaining_fetch_info()`

**问题**：
```python
merged_delta = {
    'delta': cumulative_enc,
    'size': deltas_to_fetch[0]['size'],  # BUG: 未测量合并后实际大小
    ...
}
```

当客户端缺失多个 deltas 时，服务器正确地将它们同态合并为 `cumulative_enc`，但**返回的大小是 `deltas_to_fetch[0]['size']`**，而非 `compute_encrypted_update_size(cumulative_enc)`。

虽然同态加法不改变单个密文的大小，但 `merge_sparse_encrypted_updates` 的 mask 取并集后，**batch 列表可能变长**（两个 mask 不同时，输出 mask 更长）。这导致 `cumulative_enc` 的实际大小可能大于单个 delta。

**后果**：
- 带宽模拟中 fetch 阶段的下载时间被**低估**。
- `client.fetch_time` 统计不准确。

**修复**：合并后调用 `ckks_manager.compute_encrypted_update_size(cumulative_enc)`，与 `broadcast_prefetch_to_unselected` 保持一致。

---

### 4.4 调度器 off-by-one bug

**位置**：`prefetch_scheduler.py:estimate_fetch_time()`

**问题**：
```python
for j in range(start_round, target_round):
    time_budget = self.exp_mov_avg_dur
    time_budget = max(0, time_budget - (update_size / dl_bw))
    if time_budget > 0:
        # BUG: j != start_round 时，应为 estimate_delta_size(l, j)
        next_delta_size = self.size_evaluator.estimate_delta_size(l, j - 1)
        update_size = max(0, next_delta_size - time_budget * dl_bw)
        l = j
```

当 `j != start_round` 时，代码使用 `estimate_delta_size(l, j - 1)`。但此时 `l` 已经被更新为 `j`（上一轮迭代结束时的赋值），因此 `estimate_delta_size(j, j-1)` 返回 **0**。

**后果**：
- 对于非首轮回滚的客户端，`start_round + 1` 这一轮的 delta 大小被错误估计为 0。
- 调度器认为客户端在这一轮"不需要下载任何东西"，多给了虚假的带宽 credit。
- 实际效果是调度器**系统性保守**：客户端被分配更早的 prefetch start，降低了预取效率。

**修复**：
```python
next_delta_size = self.size_evaluator.estimate_delta_size(l, j)  # j, not j-1
```

---

### 4.5 Local Completion 的硬编码阈值问题

**位置**：`client.py:apply_prefetched_state()`

**问题**：
```python
mask = torch.abs(global_delta) < 1e-3
completed = torch.where(mask, local_val, base_params[name] + global_delta)
```

`1e-3` 是硬编码的全局阈值，未考虑：
- 不同模型参数的量级差异（LeNet 的 bias 可能 < 1e-3 是正常的，ResNet 的 conv weight 也可能 < 1e-3）。
- 不同层的尺度差异（BatchNorm 的 running_mean  vs. conv 的 weight）。
- CKKS 解密引入的噪声（小值可能被噪声淹没）。

**后果**：
- 对于大尺度层， legitimate 的小更新被错误替换为客户端的 stale local value。
- 对于小尺度层，噪声导致的假阳性 mask 使客户端保留了过时的本地值。
- 深层模型（DeepCNN/VGGNoBN）对此更敏感，可能导致 BN 统计量不匹配或训练发散。

**修复方向**：
- 使用逐层自适应阈值（如 `threshold = 0.01 * max(abs(global_delta))`）。
- 或基于参数分布统计（如 `threshold = mean(abs(global_delta)) * 0.1`）。

---

### 4.6 client_prefetch_counts 状态不一致

**位置**：`server.py`（多处）

**问题**：
- `client_prefetch_counts` **仅在 `broadcast_prefetch_to_unselected` 中更新**。
- 当客户端被选中训练时，它通过 `fetch_remaining_deltas()` 从服务器获取剩余 deltas，但 `client_prefetch_counts` **不会因此增加**。

**后果**：
- 若某客户端被选中训练后，又在后续轮次未被选中，`get_remaining_fetch_info()` 会基于过时的 `client_prefetch_counts` 计算缺失 deltas，可能**重复发送**已 fetch 过的 deltas。
- 虽然 `calculate_round_duration` 通过 `_current_server_round` 避免了部分问题，但其他直接读取 `client_prefetch_counts` 的逻辑存在隐患。

**修复**：在 `get_remaining_fetch_info` 或客户端 fetch 后，增加服务器端的状态同步机制。

---

### 4.7 CKKSSizeEvaluator 的 r_min 参数被忽略

**位置**：`prefetch_scheduler.py:CKKSSizeEvaluator.estimate_size_base_and_delta()`

**问题**：
```python
def estimate_size_base_and_delta(self, r_min, r, last_synced_round):
    return self.estimate_delta_size(max(last_synced_round, 1), r)
```

参数 `r_min` 完全未被使用。在 FedFetch 中，`r_min` 决定了 base model 的索引，影响 base model 的传输大小。但在 CipherFetch 中，由于传输的是 delta 而非 base model，`r_min` 理论上不影响大小。

**后果**：
- 代码与 FedFetch 的语义不一致，若未来引入 base model 传输（如 DoCoFL 模式），此函数会返回错误结果。
- 文档与实现不一致。

---

### 4.8 量化打包导致同态聚合回退

**位置**：`crypto.py:_aggregate_sparse_updates()`

**问题**：
```python
if packing_metadata and (hasattr(packing_metadata, 'quant_bits') or hasattr(packing_metadata, 'layers')):
    # Integer encoding is noise-sensitive to homomorphic multiplication
    # Fallback: decrypt all → average in plaintext → re-pack and re-encrypt
```

当启用 CRTStack/TwoTier/LayerwiseQuantized 打包时：
- 客户端上传的更新是**量化后的整数编码**（打包在 CKKS 槽位中）。
- 服务器侧的同态加权平均需要**乘以权重系数**（如 `1/N` 或 `weight_i`）。
- CKKS 的乘法会增加噪声，而整数编码对噪声极为敏感（解包时整数边界可能偏移）。

**后果**：
- 服务器**被迫回退到明文聚合**：解密所有客户端更新 → 明文加权平均 → 重新打包加密。
- 这导致：
  1. 服务器触碰明文（安全降级）。
  2. 计算开销大幅增加（解密 N 个客户端 + 重新加密）。
  3. 失去了 CKKS 同态聚合的核心优势。

**修复方向**：
- 预先将权重编码到 CKKS 的 `plain` 中，使用**纯密文乘法-重缩放**（需精细控制 scale）。
- 或使用**BFV/BGV**（整数友好）替代 CKKS（但需重新设计整个加密层）。
- 或改用**部分同态聚合**：只同态加（不加权），权重通过客户端本地缩放实现。

---

### 4.9 Transparent Ciphertext 的根本限制

**根因**：TenSEAL 的 CKKSVector 在以下操作后产生 transparent ciphertext：
- `enc_a - enc_b`，其中 `enc_a` 和 `enc_b` 用**相同公钥、相同 context** 加密。
- 结果密文的噪声为 0，TenSEAL 出于安全考虑拒绝序列化。

**影响**：
- 无法直接计算 `delta_enc = new_global_enc - old_global_enc`。
- 无法直接计算 `global_enc = sum(client_encs) / N`（除法即乘以明文 `1/N`，但聚合前的求和若涉及相同 context 的密文，也可能触发透明问题）。

**当前规避方案**：
- ESAFL 路径：利用客户端上传的差分密文直接作为 delta，避免服务器端减法。
- 标准路径：被迫使用明文 detour。

**长期方案**：
- 迁移到 Microsoft SEAL C++ API（支持 transparent ciphertext 的显式处理）。
- 使用多密钥方案（如 ESAFL 的 native 模式，但 TenSEAL 不支持 relin/switch-key）。
- 每个客户端使用独立公钥（需要复杂的 key-switching 基础设施）。

---

### 4.10 TopK 稀疏化 + 预取的语义冲突

**位置**：`crypto.py:encrypt_model_update()` / `server.py`

**问题**：
- 服务器 staging prefetch delta 时使用 `skip_sparsification=True`（完整密文 delta）。
- 但客户端上传时使用 TopK 稀疏化（只上传部分 batch）。
- 服务器聚合时，同态加法仅覆盖被更新的 batch。

**后果**：
- 预取的 delta 是**完整的**（所有参数都更新了），但客户端实际上传的是**稀疏的**（只有 TopK 参数更新了）。
- 这本身不是问题（预取的是全局 delta，不是客户端本地 delta）。
- 真正的问题是：**local completion 的必要性正是由 TopK 导致的**。如果服务器端不使用 TopK（或使用更少的稀疏化），local completion 的复杂性可以避免。
- 当前设计将 TopK 稀疏化（通信优化）与 local completion（精度修复）耦合在一起，增加了系统复杂度。

---

## 五、总结

| 方面 | 评估 |
|------|------|
| **与 FedFetch 架构对齐度** | 高。调度策略（T_percentile）、预取窗口、overcommitment 均正确移植。 |
| **同态加密集成度** | 中。CKKS 密文累加器设计正确，但标准路径存在安全回退。 |
| **安全性** | **低（标准路径）/ 中（ESAFL 路径）**。标准路径下服务器每轮触碰明文。 |
| **性能** | 中。密文合并优化减少了传输量，但 CKKS 解密是计算瓶颈。 |
| **正确性** | 中。存在 off-by-one bug、大小测量不一致、ESAFL 边界检查缺失等问题。 |
| **可维护性** | 中。两条路径（标准/ESAFL）+ 量化回退 + local completion 使逻辑复杂。 |

**最关键的待修复问题**（按优先级排序）：
1. **标准路径明文泄露**（安全缺陷）→ 强制 ESAFL 路径或换库。
2. **ESAFL 边界检查缺失**（正确性缺陷）→ 增加 `upload_difference=True` 断言。
3. **fetch 阶段大小测量不一致**（统计缺陷）→ 合并后调用 `compute_encrypted_update_size`。
4. **调度器 off-by-one**（性能缺陷）→ 修正 `j-1` 为 `j`。
5. **量化回退明文聚合**（性能+安全缺陷）→ 设计纯同态加权方案或换方案。
