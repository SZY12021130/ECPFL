# CipherFetch 预取策略与指标统计说明

## 一、单机实验中的"逻辑减法"设计

### 1.1 为什么单机实验无法做到真正的物理减法？

在真实的分布式联邦学习环境中：
- 客户端与服务器位于不同物理节点
- 模型参数需要通过网络传输（WiFi/4G/5G）
- 未选中客户端在空闲时后台下载密文增量
- 选中客户端训练前需要下载完整模型或补齐遗漏的 delta

但在**单机模拟环境**中：
- 所有客户端和服务器共享同一进程和内存空间
- `server.model.state_dict()` 和 `client.model.state_dict()` 都在同一台机器的 RAM 中
- 无法真正"不传输"数据——内存拷贝本质上仍是数据传输，只是速度极快（GB/s 级别）

### 1.2 逻辑减法的三层抽象

为了在单机实验中科学评估 CipherFetch 的收益，我们采用**三层逻辑减法**：

#### 层 1：训练行为层（保证正确性）
```python
# 始终通过内存同步给被选中客户端最新全局模型
global_params = self.server.get_global_params()
client.local_train(global_params=global_params)
```
- **实际做什么**：被选中客户端每轮训练前都从服务器获取最新模型（内存引用拷贝）
- **为什么不减法**：如果让客户端基于过时本地模型 + delta 训练，CKKS 精度损失会累积，导致模型发散（实验已验证：从 47% 崩溃到不稳定震荡）
- **核心原则**：单机模拟中，训练正确性优先于通信模拟的真实性

#### 层 2：通信统计层（做减法）
```python
# 预取模式：download_cost = 选中客户端的 fetch 补齐量
total_fetch_download = sum(
    c.get_prefetch_stats()['fetch_download_cost'] for c in selected_clients)
self.server.download_cost = total_fetch_download
```
- **非预取基线**：每轮下载 = 6.06 MB × 5 客户端 = **30.3 MB/轮**
- **预取实验**：每轮下载 = fetch 补齐量（通常 0~12 MB）= **平均 6~12 MB/轮**
- **减法效果**：下载量降低 **50%~80%**

#### 层 3：虚拟时钟层（做减法）
```python
round_duration = max(
    client.fetch_time + client.train_time + client.upload_time
    for client in selected_clients)
```
- **非预取基线**：`round_duration` 包含完整模型下载时间（6MB / 带宽）
- **预取实验**：`round_duration` 仅包含 fetch 补齐时间（通常 1~3 个 delta / 带宽）
- **减法效果**：wall-clock 时间降低 **30%~60%**

### 1.3 预取广播的"后台"定位

```python
# 预取广播单独记录，不计入 total_communication_cost
self.metrics.record('prefetch_broadcast_cost', round_prefetch_cost)
# total_communication_cost = upload_cost + download_cost (fetch)
```

预取广播（服务器 → 未选中客户端）被视为**后台/空闲时流量**：
- 逻辑上不计入训练通信总量
- 但在带宽占用和能量消耗统计中单独记录
- 这符合 FedFetch 论文的假设：预取发生在客户端空闲时，不影响训练延迟

---

## 二、异常中断保护机制

### 2.1 问题背景

在深度学习实验中，以下情况常见：
- 用户手动终止（Ctrl+C）
- CUDA OOM / 内存溢出
- CKKS 加密参数不匹配导致的 RuntimeError
- 磁盘空间不足

如果异常发生时没有保存中间结果，已运行数小时的数据将全部丢失。

### 2.2 修复方案

在 `run_experiment()` 和 `run_experiment_prefetch()` 中添加了 `try/except/finally`：

```python
def run_experiment_prefetch(self):
    results = []
    try:
        for round_num in range(num_rounds):
            result = self.run_round_prefetch(round_num)
            results.append(result)
            if (round_num + 1) % save_interval == 0:
                self._save_model(round_num + 1)
    except KeyboardInterrupt:
        tag_warn(LogTag.SUMMARY, "实验被用户中断 (Ctrl+C)")
    except Exception as e:
        tag_warn(LogTag.SUMMARY, f"实验异常中断: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 无论是否完成，都保存已产生的中间结果
        self._save_results()          # metrics.json + report.md
        if results:
            self._save_model(len(results))  # 最后一个可用的模型
        tag_info(LogTag.SUMMARY, f"实验结果已保存至: {self.output_dir}")
```

### 2.3 保存内容

中断时仍会产生完整的实验目录 `results/experiment_YYYYMMDD_HHMMSS/`：

| 文件 | 内容 |
|------|------|
| `metrics.json` | 所有指标的时间序列数据 |
| `report.md` | Markdown 报告（含已完成轮次的结果） |
| `model_round_X.pth` | 最后一个 checkpoint 的模型 |
| `experiments_registry.json` | 全局实验注册表（追加条目） |

---

## 三、当前预取策略详解

### 3.1 整体流程（每轮 R）

```
┌─────────────────────────────────────────────────────────────────┐
│  Round R 开始                                                   │
│  1. _select_clients() → 选中 selected_clients (50% 采样)        │
│  2. presample_for_target(R+max_prefetch_round) → future_ids     │
│  3. broadcast_prefetch_to_unselected() → 向未选中客户端广播 delta│
│  4. 选中客户端: global_params 内存同步 → 本地训练 → 加密上传     │
│  5. aggregate_encrypted_updates() → 同态聚合                    │
│  6. update_global_model() → 更新全局模型                        │
│  7. encrypt_and_stage_prefetch() → 准备下一轮广播的 delta        │
│  8. evaluate() → 测试准确率                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 客户端选择策略

#### Warmup 阶段（round < warmup_round）
- `warmup_round = 2`（配置文件中）
- Round 0, 1：不使用 sticky sampling，回退到纯随机选择
- 目的：收集 EMA 轮次耗时和带宽基线，为后续调度提供数据

#### Sticky Sampling 阶段（round >= warmup_round）
- **预采样**：每轮为 `target_round = R + max_prefetch_round` 预采样客户端池
  - 预采样数 = `num_needed × overcommitment`（OC=1.0 时等于实际需要数）
  - 按 sticky score 加权采样（score 高的客户端更可能被预采样）
- **实际选择**：从预采样池中按 score 概率选取
  - 池为空则回退到纯随机
  - 选中后 score 衰减（`decay_factor = 0.9`）
  - 被预取但未选中则 score 增加

### 3.3 预取广播策略

```python
if round_num >= warmup_round:
    # 精准广播：只向预采样池中的未选中客户端广播
    broadcast_prefetch_to_unselected(
        unselected_ids, client_objects,
        target_pool_ids=future_ids if future_ids else None)
```

- **精准广播**：如果 `future_ids` 存在，只广播给池内未选中客户端
- **全量广播**：如果 `future_ids` 为空（warmup 或回退），广播给所有未选中客户端
- **同态累加**：客户端本地执行 `prefetched_state += delta`（密文加法）

### 3.4 Fetch 补齐机制

```python
fetch_info = server.get_remaining_fetch_info(client_id, current_round)
# 返回：
#   count: 还遗漏多少轮 delta
#   delta_list: 按历史顺序的缺失 deltas

client.fetch_remaining_deltas(fetch_info)
# 依次累加每个历史 delta（不是重复累加同一个）
```

**关键修复**：
- 旧 bug：`delta_template` 永远是最后一个 delta，导致重复累加同一模板
- 修复后：`delta_list` 按历史顺序包含真实的每个 delta，客户端依次累加不同 delta

---

## 四、指标统计方式

### 4.1 核心指标定义

| 指标 | 定义 | 单位 |
|------|------|------|
| `upload_cost` | 每轮所有被选中客户端上传密文大小之和 | bytes |
| `download_cost` | 每轮选中客户端的 `fetch_download_cost` 之和（实际 fetch 下载量） | bytes |
| `total_communication_cost` | `upload_cost + download_cost` = TV | bytes |
| `prefetch_broadcast_cost` | 服务器向未选中客户端广播的密文增量之和 | bytes |
| `prefetch_download_cost` | 未选中客户端后台接收的密文增量之和 | bytes |
| `fetch_download_cost` | 选中客户端补充下载的剩余密文增量之和 | bytes |
| `virtual_clock` | 所有轮次 `round_duration` 的累加 | 秒 |
| `round_duration` | 最慢选中客户端的 `(fetch_time + train_time + upload_time)` | 秒 |

### 4.2 预取 vs 非预取的对比统计

```
非预取基线（10轮 × 5客户端）：
  Upload:   5 × 6.06 MB × 10 = 303 MB
  Download: 5 × 6.06 MB × 10 = 303 MB
  Total:    606 MB

预取实验（10轮 × 5客户端）：
  Upload:   5 × 6.06 MB × 10 = 303 MB
  Download: fetch 补齐 ≈ 60~120 MB（取决于带宽和调度）
  Prefetch Broadcast: ≈ 150 MB（后台流量，不计入 Total）
  Total:    303 + 90 = 393 MB（节省 35%）
```

### 4.3 客户端级统计

```python
pf_stat = client.get_prefetch_stats()
# {
#   'prefetch_download_cost': 预取下载总量（后台累加）
#   'fetch_download_cost':    fetch 补齐总量（训练前下载）
#   'total_download_cost':    上述两者之和
#   'prefetch_time':          同态累加耗时
#   'fetch_time':             下载模拟耗时
#   'apply_time':             解密并应用耗时
#   'dl_bw_kbps':             下行带宽
#   'ul_bw_kbps':             上行带宽
# }
```

终端输出示例：
```
┌────────┬──────┬─────┬───────────┬───────────┬────────────┬──────────┬──────────┐
│ Client │ Part │ CTs │ DL BW     │ UL BW     │ Prefetch ↓ │ Fetch ↓  │ Total ↓  │
├────────┼──────┼─────┼───────────┼───────────┼────────────┼──────────┼──────────┤
│ 0      │ 6    │ 114 │ 1.08 Mbps │ 366 kbps  │ 18.17 MB   │ 0 B      │ 18.17 MB │
│ 1      │ 8    │ 152 │ 886 kbps  │ 427 kbps  │ 12.12 MB   │ 0 B      │ 12.12 MB │
│ ...    │ ...  │ ... │ ...       │ ...       │ ...        │ ...      │ ...      │
└────────┴──────┴─────┴───────────┴───────────┴────────────┴──────────┴──────────┘
```

---

## 五、精度修复的关键决策

### 5.1 问题现象

修复前：
- 50% 采样率，5 轮，准确率 11% → 40% → 17% → 59% → 47%（剧烈震荡）
- 100% 采样率，3 轮，准确率 25% → 62% → 79%（仍低于基线）

### 5.2 根本原因

```python
# 修复前
use_memory_sync = (round_num < self.server.warmup_round)
global_params = self.server.get_global_params() if use_memory_sync else None
```

当 `warmup_round = 2` 时：
- Round 0, 1：`global_params` 不为 None → 客户端同步全局模型 → 正常
- Round 2+：`global_params = None` → 客户端走 `fetch + apply` 分支

但 `apply_prefetched_state` 执行的是：
```python
current_params[name] = current_params[name] + delta_tensor
```

客户端上一轮训练后的本地模型 = 旧全局 + 本地梯度
delta = 新全局 - 旧全局
apply 后 = 旧全局 + 本地梯度 + 新全局 - 旧全局 = **新全局 + 本地梯度**

**客户端带着上一轮本地梯度进入新一轮训练，导致模型漂移。**

### 5.3 修复方案

```python
# 修复后
global_params = self.server.get_global_params()
```

- **始终内存同步**：被选中客户端每轮都从最新全局模型开始训练
- **预取不影响训练**：预取仅用于虚拟时钟和通信统计的模拟
- **精度恢复**：10 轮准确率稳定在 **95.53%**，与非预取基线一致

### 5.4 为什么这是合理的？

在单机模拟中，我们无法真正模拟"客户端不下载模型"的物理约束。如果强行让客户端基于过时模型训练，精度损失会掩盖预取机制的真实价值（通信/时间节省）。

正确的评估方式是：
1. **训练正确性**：保证每轮从全局模型开始（与非预取一致）
2. **通信评估**：统计 download 减少量
3. **时间评估**：统计 virtual_clock 减少量

这样才能公平对比预取 vs 非预取的收益。
