# FedFetch 训练机制问答文档

## 1. 训练时长与结束标志

### 1.1 要跑多少轮？
当前配置文件 `benchmark/configs/perf/femnist/STC_prefetch.yml` 中：
```yaml
rounds: 1000
```
默认需要跑满 **1000 轮** 才会自动结束。FEMNIST + ShuffleNet 通常在 300~500 轮左右就能收敛，如果你想提前结束，可以：
- 修改配置文件中 `rounds` 的值（如改为 200 或 400），然后重启 Aggregator 和 6 个 Executor。
- 或者直接按 `Ctrl+C` 中断所有 7 个窗口强行停止，已跑过的结果不会丢失。

### 1.2 代码层面的结束条件
在 `examples/prefetch/aggregator.py` 的 `round_completion_handler` 中：
```python
if self.round >= self.args.rounds:
    self.broadcast_aggregator_events(commons.SHUT_DOWN)
```
当 `self.round >= 1000` 时，Aggregator 会向所有 Executor 广播 **SHUT_DOWN**，随后 `event_monitor` 的 `while True` 循环 break，训练正式结束。

### 1.3 训练结束时你会看到什么日志？
Aggregator 窗口会依次出现：
1. **`FL Testing in round: 1000, virtual_clock: XXXX, results: {...}`**  
   第 1000 轮（满足 `eval_interval` 的倍数）会触发最终全局测试。
2. **`Wall clock: XXXX s, round: 1000, ... Training loss: X.XX`**  
   最后一轮训练完成的汇总信息。
3. **`Issue EVENT (SHUT_DOWN) to EXECUTOR (X)`**  
   逐个通知 6 个 Executor 关闭。
4. **`Terminating the aggregator ...`**  
   Aggregator 自身关闭的日志。

---

## 2. Executor 与 Client 的关系

### 2.1 核心区别
在 `SIMULATION_MODE` 下：
- **Executor（执行器）**：是真实存在的 Python 进程，负责在 GPU/CPU 上实际运行模型训练。你开了 6 个 Executor 窗口，就有 6 个真实进程。
- **Client（客户端）**：是逻辑上的数据分区。FEMNIST 数据集有 3400 个客户端，过滤后约 2800 个可行客户端。每个 Client 只是一份独立的数据子集。

### 2.2 6 个 Executor 怎么服务 2800 个 Client？
每一轮 FL：
1. Aggregator 从 2800 个客户端中**采样 30 个**（由 `num_participants=30` 决定）。
2. 这 30 个训练任务被分发给 6 个 Executor。
3. 每个 Executor **串行地**处理分配给自己的多个 Client：先加载 Client A 的数据 → 训练 → 返回结果 → 再加载 Client B 的数据 → 训练 → ...

因此，**30 个 Client 的任务在 6 个 Executor 上是分时复用的**，而不是 2800 个 Client 同时在线。

---

## 3. GPU 使用情况

配置文件里 `use_cuda: true`，说明启用了 GPU。但**是否真的在用 GPU**，需要你自己确认：

### 3.1 如何验证
1. **新开一个 PowerShell，运行 `nvidia-smi -l 1`**。如果在训练过程中能看到多个 Python 进程占用显存，说明 GPU 确实在工作。
2. **查看 Executor 日志**。如果训练速度非常快（一轮 10~20 秒），通常是 GPU 在跑；如果一轮需要几分钟，很可能是 fallback 到了 CPU。

### 3.2 常见 fallback 原因
- `cuda_device` 配置错误或被其他进程占满。
- PyTorch 的 CUDA 版本与驱动不匹配。
- `gloo` backend 在 Windows 上的某些兼容性问题。

---

## 4. 日志现象解读

### 4.1 反复出现 `Issue EVENT (client_train) to EXECUTOR (N)`
这是**完全正常的调度行为**。Aggregator 会把 30 个 client 任务逐个派发给 6 个 Executor。每当一个 Executor 完成当前任务并向 Server 请求下一个任务时，Server 就会输出一次 `Issue EVENT (client_train) to EXECUTOR (N)`。因为 30 个任务由 6 个 Executor 轮流领取，所以同一 Executor 会被重复派发多次。

### 4.2 `Summary Stats` 反复出现
Aggregator 内部有一个汇总统计模块，会在收到每个 Executor 返回的训练结果后输出一次统计摘要。30 个 Client 就意味着你会看到 30 次左右的 Summary Stats。

### 4.3 `Gradients sparsification: 0.204... / Mask sparsification: 0.198...`
这说明 STC（Sparse Ternary Compression）或 GlueFL 的梯度压缩成功执行了。数值表示被保留（非零）的梯度比例，约 20% 左右，与 `total_mask_ratio=0.2` 的配置一致。

### 4.4 `Wall clock: 15 s, round: 1, ... Training loss: 3.34`
这表示**第 1 轮已经成功完成**，30 个参与者全部返回了结果，平均训练损失为 3.34，虚拟时钟推进了 15 秒。

---

## 5. FedFetch 预取机制深度解析

### 5.1 预取主体是谁？
**预取的主体，就是未来训练轮（如第 t+R 轮）才被选中的那 30 个客户端自己。**

- Aggregator 提前 `max_prefetch_round` 轮（如 3 轮）就决定了第 t+3 轮要用哪些客户端。
- 然后 Server 为这些客户端计算：它们应该从第 t 轮、t+1 轮还是 t+2 轮开始“后台下载”模型增量。
- 在 **Simulation Mode** 下，这个下载并不是操作系统层面的真实后台线程，而是 Server 在**虚拟时钟**里做的一场通信开销模拟。
- 当真正的训练轮（第 t+3 轮）到来时，Server 会把**已经应用了所有预取更新的最终模型**（`next_client_model`）直接发给 Executor。Executor 拿到后直接开始 SGD，跳过了下载等待。

### 5.2 预取增量的来源：流水线（Pipeline）模型

**不存在“客户端在第 t 轮就知道未来 Δ_{t+1}、Δ_{t+2}”的问题。** FedFetch 的预取是**逐轮累积**的流水线：

| 真实轮次 | 其他客户端在做什么 | 预取客户端 i 在做什么 |
|---------|------------------|---------------------|
| 第 t 轮 | 其他 30 个客户端训练完 → Aggregator 聚合出 `Δ_t` | 客户端 i 在后台下载 **base model + Δ_t** |
| 第 t+1 轮 | 其他 30 个客户端训练完 → 聚合出 `Δ_{t+1}` | 客户端 i 利用本轮训练时间后台下载 **Δ_{t+1}** |
| 第 t+2 轮 | 其他 30 个客户端训练完 → 聚合出 `Δ_{t+2}` | 客户端 i 利用本轮训练时间后台下载 **Δ_{t+2}** |
| 第 t+3 轮 | 客户端 i 开始正式训练 | 本地模型已经是 `M_{t+3} = M_{last} + Δ_t + Δ_{t+1} + Δ_{t+2}`，直接开始训练 |

**关键洞察：**
- 客户端 i **不需要在第 t 轮就知道 Δ_{t+1}**。它只需要在第 t 轮下载已经产生的 Δ_t，在第 t+1 轮下载刚产生的 Δ_{t+1}，依此类推。
- 这是一个**生产者-消费者流水线**：Aggregator 每轮生产一个增量 Δ，预取客户端在下一轮的训练时间里把这个 Δ 消费（下载）掉。

**代码证据（`estimate_fetch_time`）：**
```python
for j in range(r, train_round):        # j = p, p+1, ..., T-1
    time_budget = self.exp_mov_avg_dur  # 第 j 轮的训练时间（作为后台下载窗口）
    time_budget = max(0, time_budget - (update_size / dl_bw))
    if time_budget > 0:
        # 训练时间内还有剩余带宽，继续下载第 j 轮新产生的增量
        next_delta_size = self.size_eval.estimate_delta_size(l, j - 1, ...)
        update_size = max(0, next_delta_size - time_budget * dl_bw)
        l = j
```
这个循环**逐轮模拟**了预取客户端如何利用每一轮的训练时间去消化新增的 delta。

### 5.3 时间与带宽是怎么估计的？

#### 5.3.1 每轮持续时间：指数移动平均（EMA）
```python
def calculate_exp_weighted_avg(self, new_dur):
    alpha = self.args.avg_alpha  # 默认 0.125
    if self.exp_mov_avg_dur is None:
        self.exp_mov_avg_dur = new_dur
    else:
        self.exp_mov_avg_dur = alpha * new_dur + (1 - alpha) * self.exp_mov_avg_dur
```
`exp_mov_avg_dur` 代表“未来每一轮大概会持续多少秒”。

#### 5.3.2 带宽：来自静态设备配置文件，恒定不变
在 `examples/prefetch/client_metadata.py` 中：
```python
self.dl_bandwidth = speed["dl_kbps"]
```
这个值来自 `device_conf_file`（`client_device_capacity_ul_dl`），**每个客户端的带宽在实验开始时就固定了，整个训练过程中不变**。

#### 5.3.3 能下载的总量 = 预计时间 × 带宽
在 `estimate_fetch_time` 中：
```python
round_download_amount = self.exp_mov_avg_dur * dl_bw
```
这表示：在每一轮 `exp_mov_avg_dur` 秒的训练时间里，客户端利用后台带宽最多能下载多少 bit。

### 5.4 `schedule_prefetch` 算法流程与示例

这是核心调度器，代码在 `examples/prefetch/aggregator.py` 第 964-989 行。它的目标是：**让慢的客户端尽早开始预取，快的客户端可以稍晚开始。**

#### 算法流程
1. 初始时，假设所有客户端都从**最早轮次** `cur_round` 开始预取。
2. 对每个候选轮次 `r`（从 `cur_round` 到 `cur_round + max_prefetch_round`），计算剩余客户端如果从 `r` 开始预取，还需要多少额外下载时间 `fetch_time`。
3. 根据分位数阈值 `T_percentile` 筛选：下载时间小于阈值的客户端被视为“来得及”。
4. **来得及的客户端被正式安排到第 `r` 轮开始预取**；来不及的客户端被移出列表，保留之前更早的安排。

#### 具体示例
假设 `cur_round=10`，`max_prefetch_round=3`，目标训练轮 `T=13`。选了 5 个客户端 A~E：

**Step 1：r = 10（最早开始）**
- 估算 `fetch_time(i, 10, 10)`：A=2s, B=4s, C=8s, D=15s, E=25s
- 假设 `T_percentile` 为 15s。过滤 `fetch_time < 15` → **A, B, C 成功**。
- D, E 失败，被移出。D 和 E **保持默认安排 `prefetch_schedule = 10`**（必须最早开始）。

**Step 2：r = 11**
- `clients_can_finish = [A, B, C]`
- 估算 `fetch_time(i, 11, 10)`：A=1s, B=2s, C=5s
- 假设 `T_percentile` 重算为 4s。C 失败（5s > 4s），被移出。**C 保持 `prefetch_schedule = 10`**。
- A, B 成功，**更新为 `prefetch_schedule = 11`**。

**Step 3：r = 12**
- `clients_can_finish = [A, B]`
- 估算 `fetch_time(i, 12, 10)`：A=0.5s, B=1s
- 都通过。**A, B 更新为 `prefetch_schedule = 12`**。

**最终调度结果：**
| Client | 预取开始轮 | 说明 |
|--------|-----------|------|
| E | 10 | 最慢，必须最早开始，给足 3 轮窗口 |
| D | 10 | 较慢，必须最早开始 |
| C | 10 | 中等速度，需要 3 轮窗口 |
| B | 12 | 较快，提前 1 轮开始即可 |
| A | 12 | 最快，提前 1 轮开始即可 |

### 5.5 Server 扣除预取通信量，这合理吗？

**在 Simulation 模式下，这是完全合理的。**

#### 原因 1：FedScale 本身就是估算型模拟器
FedScale 中的所有时间都不是物理测量的，而是算出来的：
- 训练时间 = `augmentation_factor * batch_size * local_steps * compute_speed`
- 通信时间 = `download_size / dl_bw`

既然训练和通信时间都是估算的，那么**把已经重叠掉的后台下载时间从总通信量里扣除**，只是把“预取带来了时间重叠”这一物理事实正确地反映到虚拟时钟里。

#### 原因 2：真实世界就是这样的
在真实部署（Deployment Mode）中，客户端 i 的背景线程会：
1. 在第 10 轮花 2 秒下载 Δ_10；
2. 在第 11 轮花 2 秒下载 Δ_11；
3. 在第 12 轮花 2 秒下载 Δ_12；
4. 第 13 轮开始训练时，本地模型已经是最新的，不需要再花下载时间。

Simulation 中 Server 把这 6 秒从总通信开销里扣除，与真实世界完全一致。如果不扣除，模拟结果就退化为普通 FedAvg，完全体现不出预取的加速效果。

#### 代码中的扣除逻辑
在 `tictak_client_tasks` 中（第 303-355 行）：
```python
pre_size += update_size          # 预取期间已经下载了多少
...
for j in range(p, train_round):
    time_budget = max(0, time_budget - update_size / dl_bw)
    if time_budget > 0:
        pre_size += next_delta_size   # 本轮增量也在预取期间被后台下载了
        ...
    else:
        update_size -= round_durations[j] * dl_bw  # 本轮带宽只能消化这么多

dl_size = update_size + final_delta   # 到训练轮开始时，还剩多少没下载完
```
`dl_size` 就是**扣除预取成果后**，客户端在训练轮真正需要花的下载量。这确保了虚拟时钟能够准确反映预取带来的收益。

---

## 7. 补充概念详解

### 7.1 指数移动平均（EMA）靠谱吗？

**结论：它是一个工程上可用的近似，但不完美。**

在 `config_parser.py` 中，EMA 的参数默认是：
```python
parser.add_argument('--avg_alpha', type=float, default=0.125)
```
`alpha=0.125` 意味着新的 round duration 只占 12.5% 权重，历史占 87.5%，这相当于一个**非常平滑的低通滤波器**（类似 TCP 里估计 RTT 的做法）。

**靠谱的场景**：
- 数据集和模型固定后，每轮训练时间通常会在一个稳定范围内小幅波动。
- 在 FedScale 的 simulation 中，所有时间本来就是算出来的（不是物理实测的），用 EMA 来做调度决策是足够合理的。

**不靠谱的场景**：
- 如果突然出现大批量慢客户端被选中，真实 round duration 会骤增，但 EMA 反应迟钝。
- 如果客户端的可用性和网络带宽剧烈波动，EMA 无法捕捉突变。

因此，EMA 是**调度器的一个简化假设**。论文里通常也会配合 `prefetch_scheduler_beta` 等参数给它留一些安全余量。

### 7.2 客户端采样是随机选取的吗？

**取决于你用的采样模式。** 在 `STC_prefetch.yml` 里：
```yaml
sampling_strategy: UNIFORM
```

对应的代码在 `fedscale/cloud/client_manager.py` 第 220-229 行：
```python
if self.mode == "oort" and self.count > 1:
    pickled_clients = self.ucb_sampler.select_participant(...)
else:
    self.rng.shuffle(clients_online)
    client_len = min(num_of_clients, len(clients_online) - 1)
    pickled_clients = clients_online[:client_len]
```

**三种常见模式：**
1. **UNIFORM（默认）**：在所有当前在线的客户端中 **随机打乱 (`rng.shuffle`)**，然后取前 N 个。这是最基础的随机均匀采样。
2. **OORT**：用多臂老虎机（UCB）根据历史训练速度和损失来**有偏向地**选择“高价值”客户端，而不是纯随机。
3. **STICKY**：`PrefetchClientManager` 实现的一种特殊采样。它维护一个 **sticky group**（每轮保留大部分上一轮的客户端），只替换其中一小部分（change group）。这样做的好处是可以让同一批客户端连续参与多轮，提高预取效率。

你当前配置 `UNIFORM` + `enable_prefetch=True` 意味着：
- 每轮从在线客户端中**纯随机**选 30 个。
- 但由于 Prefetch 逻辑会提前 `max_prefetch_round` 轮预采样，所以采样决定是提前锁定的。

### 7.3 论文说的“模型陈旧（Model Staleness）”指的是什么？

**模型陈旧 = 客户端本地训练时使用的模型版本，已经落后于服务器当前的最新全局模型。**

在同步联邦学习（如 FedAvg）里，理想情况下所有客户端都应该用**第 R 轮最新聚合后的全局模型**进行训练。但由于通信延迟、掉队者、异步聚合等因素，有些客户端拿到并开始训练时，全局模型已经推进到第 R+1、R+2 甚至更高轮次了。

**在 FedFetch 的语境下，模型陈旧主要来源于两个场景：**
1. **预取客户端的延迟同步**：如果一个客户端因为网络慢，从预取开始到真正训练期间没能把所有增量下载完，它训练时用的模型就不是最新的。
2. **异步 FL（Async FL）**：在 FedScale 的 `async_aggregator.py` 中，明确用到了 `staleness scaling`：
   ```python
   inverted_staleness = 1 / (1 + self.round - self.client_task_model_version[results['client_id']]) ** 0.5
   ```
   这里 `self.round - self.client_task_model_version` 就是**陈旧度**——表示客户端的更新是基于多少轮之前的模型算出来的。陈旧度越大，这个更新在聚合时的权重就越小。

**为什么陈旧是个问题？**
- 陈旧梯度的方向可能和当前全局最优方向不一致，导致收敛变慢甚至震荡。
- FedFetch 的核心动机之一，就是通过**预取减少通信等待时间**，让更多客户端能在最新模型上训练，从而**降低模型陈旧度**。

### 7.4 客户端掉线（Dropout / Offline）指的是什么？

**掉线 = 在 Simulation 中，客户端在特定时刻 `cur_time` 处于“不可用”状态。**

FedScale 为每个客户端维护了一个 **user trace**（活动轨迹），记录了该设备在什么时间段在线、什么时间段离线（例如手机锁屏、没电、没 Wi-Fi）。

代码中通过 `isClientActive` 判断：
```python
def isClientActive(self, client_id, cur_time):
    return self.client_metadata[...].is_active(cur_time)
```

**在 FedFetch 的预取过程中，掉线会带来两个后果：**
1. **预取期间掉线**：客户端从第 p 轮开始预取，但在 p+1 轮时 trace 显示它离线了。那么它就无法继续下载后续增量，会被标记为 `prefetch_lost_clients`。
2. **训练期间掉线**：客户端被选中参加本轮训练，但在应该返回结果时离线了，会被标记为 `round_lost_clients` 或 `round_stragglers`。

**系统的应对策略**：
- `overcommitment` 超额采样：多选一些客户端作为备胎。
- `enable_replace_offline`：如果预取期间某个客户端掉线，可以用另一个在线客户端替换它。

### 7.5 OC（Overcommitment）是什么？

**OC = Overcommitment（超额承诺/超额采样）。**

在你的配置里：
```yaml
overcommitment: 1.3
num_participants: 30
```

**含义：**
- 每轮**实际需要** 30 个客户端的更新。
- 但 Aggregator 会**采样 30 × 1.3 = 39 个客户端**。
- 然后从 39 个里面**只取最快的 30 个**，剩下的 9 个因为太慢或掉线被丢弃（称为 stragglers）。

**代码体现**：
在 `examples/prefetch/client_manager.py` 中：
```python
self.sample_num = self.args.num_participants * self.args.overcommitment
```
然后在 `tictak_client_tasks` 中，Aggregator 会计算这 39 个客户端的预计完成时间，只保留前 30 个最快的。

**为什么需要 OC？**
联邦学习中客户端的设备和网络差异极大（heterogeneity）。如果不超额采样，一旦选中的 30 个里有几个特别慢，整个 round 就会被它们拖垮（straggler 问题）。**多选 30% 作为缓冲池，可以显著降低 round duration 的尾部延迟。**

**代价**：
- 多采样了 9 个客户端，但这些客户端在训练中途被丢弃，浪费了一些计算资源。
- 在 Simulation 中这种浪费只是虚拟时钟的估算，不会真的跑完；在真实部署中则确实存在一定的资源开销。

---

## 8. 带宽配置文件长什么样？为什么用固定值？

### 8.1 文件格式
配置文件路径：
```
benchmark/dataset/data/device_info/client_device_capacity_ul_dl
```

这是一个 **Python pickle 序列化的二进制文件**。我用 Python 读取后的结构如下：

```python
Type: <class 'dict'>
Keys: [0, 1, 2, 3, 4, ...]
  0: {'computation': 42.0, 'communication': 2051.12, 'dl_kbps': 114.04, 'ul_kbps': 8350.13}
  1: {'computation': 146.0, 'communication': 4596.31, 'dl_kbps': 78019.37, 'ul_kbps': 15962.05}
  2: {'computation': 140.0, 'communication': 4456.18, 'dl_kbps': 266609.63, 'ul_kbps': 305141.91}
Total entries: 9242
```

每个 key 是一个客户端（或设备模板）的 ID，value 是一个字典，包含 4 个字段：
- **`computation`**（float，单位 ms/sample）：该设备的推理/计算速度。数值越小代表设备越快。
- **`communication`**（float）：总通信延迟的预估值。
- **`dl_kbps`**（float，单位 kbps）：下行带宽（下载速度）。
- **`ul_kbps`**（float，单位 kbps）：上行带宽（上传速度）。

在代码中，Aggregator 启动时会通过 `load_client_profile()` 把这个字典加载进来，然后按 `client_id % 9242` 的方式为每个 FEMNIST 客户端映射一个设备模板（因为 FEMNIST 有 2800+ 个客户端，而设备模板有 9242 个）。

### 8.2 为什么带宽是固定的？

**因为这是 Simulation，所有时间都是“估算”出来的，而不是物理实测的。**

FedScale/FedFetch 的设计初衷是：
> 在不需要真实部署成千上万台物理设备的前提下，模拟大规模联邦学习的系统行为。

在这个框架里：
- 训练时间 = `computation × batch_size × local_steps × augmentation_factor`
- 通信时间 = `download_size / dl_bw + upload_size / ul_bw`

这些公式里的 `computation`、`dl_kbps`、`ul_kbps` 都来自这个静态配置文件。它们本质上是对真实世界设备能力（如 AI Benchmark 的手机性能排行榜）的一种**采样和建模**。

### 8.3 这样做合理吗？

**合理，但有前提。**

#### 合理的原因
1. **实验可重复（Reproducible）**：固定带宽意味着任何人、任何时间跑这个实验，只要配置相同，结果就一样。这对学术研究至关重要。
2. **控制变量**：FedFetch 的核心贡献是“预取调度策略”。为了 isolates 这个变量，研究者需要把其他因素（如网络波动）固定下来，才能清晰地比较“有预取 vs 无预取”的性能差异。
3. **反映设备异构性（Heterogeneity）**：虽然单个客户端的带宽不变，但不同客户端之间的带宽差异极大（从 114 kbps 到 266 Mbps），这足以模拟真实联邦学习中“手机 vs 平板 vs 高端机”的巨大性能差距。
4. **工程简化**：动态网络模型（如 WiFi 切换、信号衰减、基站拥塞）会极大地增加模拟复杂度。固定带宽是一个被广泛接受的 baseline 假设。

#### 局限性与不合理之处
1. **不能反映真实网络的动态波动**：现实中你的手机带宽可能在 10 Mbps 和 100 kbps 之间剧烈跳变，而模拟中它永远是 266 Mbps。
2. **忽略了地理位置和时段影响**：晚上 8 点的小区基站拥塞、地铁上的信号盲区，这些在固定带宽文件里完全没有体现。
3. **预取调度器对带宽突变的适应性未知**：因为带宽是固定的，FedFetch 的 EMA 调度器和 `schedule_prefetch` 算法无法测试在“突然断网”或“带宽骤降”场景下的鲁棒性。

### 8.4 更现实的替代方案（研究中常见）
如果研究者想做得更真实，通常会采用以下两种方式之一：
1. **时变带宽 trace**：把带宽文件从 `client_id → 固定值` 改成 `client_id → 时间序列`，每一轮根据时间戳查表。这样可以在模拟中复现真实的网络波动数据。
2. **概率模型**：给带宽加一个随机噪声（如对数正态分布），每轮根据分布采样一个瞬时带宽。

但在 **FedFetch 的原论文和默认代码中，使用的是固定带宽模型**。这既是合理的简化，也是你需要理解的边界条件。

---

## 9. 总结

1. **训练时长**：默认 1000 轮，可随时修改 `rounds` 或 `Ctrl+C` 中断。
2. **Executor vs Client**：6 个 Executor 是真实进程，2800 个 Client 是逻辑数据分区；每轮 30 个 Client 的任务在 6 个 Executor 上串行分时执行。
3. **GPU**：配置已开启 `use_cuda=true`，建议通过 `nvidia-smi` 和训练速度交叉验证。
4. **日志**：反复 `Issue EVENT` 和 `Summary Stats` 是正常调度行为；`Wall clock` 和 `Training loss` 证明轮次已完成。
5. **预取机制**：
   - 主体是未来的训练客户端自己；
   - 增量来自“一轮产生、一轮下载”的流水线；
   - 时间用 EMA 估计，带宽用固定值；
   - `schedule_prefetch` 让慢客户端早开始、快客户端晚开始；
   - Server 扣除预取量是 Simulation 中正确反映时间重叠的合理做法。
