# CKKS-Fed-Robustness: 联邦学习 + CKKS + 攻击与防御研究平台

本项目是基于 `ckks_fed` 扩展的**鲁棒性研究平台**，专注于在联邦学习（FL）+ CKKS 同态加密环境下，系统性地研究各类攻击手段及其防御方法。

---

## 一、项目架构

```
ckks_fed_robustness/
├── ckks_fed/
│   ├── attacks/              # 攻击模块
│   │   ├── data_attacks.py   # 数据层面攻击
│   │   └── model_attacks.py  # 模型层面攻击
│   ├── defenses/             # 防御模块
│   │   ├── aggregation_rules.py    # 鲁棒聚合规则
│   │   └── anomaly_detection.py    # 异常检测过滤
│   ├── experiments/
│   │   └── attack_runner.py        # 统一实验运行器
│   ├── client.py             # 扩展支持 MaliciousClient
│   ├── server.py             # 扩展支持防御聚合
│   ├── data.py               # 扩展支持有毒数据生成
│   └── ...
├── configs/
│   └── attack_config.yaml    # 攻击实验配置
├── main_robustness.py        # 主入口
└── README.md                 # 本文件
```

---

## 二、快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行鲁棒性实验

```bash
python main_robustness.py
```

实验将自动读取 `configs/attack_config.yaml`，构建**攻击 × 防御 × 模式**的实验矩阵，依次运行并生成汇总报告。

### 3. 命令行过滤：只跑感兴趣的子集

如果你不想一次性跑完配置文件中的所有实验，可以通过命令行参数快速过滤，只运行某一组实验。

**可用参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `--attack` | 只运行指定攻击的实验 | `--attack scaling` |
| `--defense` | 只运行指定防御的实验 | `--defense median` |
| `--mode` | 只运行指定模式的实验 | `--mode plain` |
| `--config` | 指定其他配置文件 | `--config my_config.yaml` |

**常用示例：**

```bash
# 运行配置文件中全部实验（默认）
python main_robustness.py

# 只跑 Scaling 攻击的实验（过滤后只剩3个）
python main_robustness.py --attack scaling

# 只跑 Median 防御的实验
python main_robustness.py --defense median

# 组合过滤：只跑 plain 模式下 scaling 攻击的实验
python main_robustness.py --mode plain --attack scaling

# 精确到单个实验：只跑 sign_flipping + median
python main_robustness.py --attack sign_flipping --defense median
```

> 过滤逻辑是在配置文件生成的实验矩阵上二次筛选，因此即使你的 `experiments` 列表里有 18 个配置，加上 `--attack scaling` 后只会执行其中属于 Scaling 的 3 个实验。

---

## 三、攻击手段全景

攻击分为两大类：**数据层面攻击**（影响本地训练）和 **模型层面攻击**（篡改上传的模型更新）。

### 3.1 数据层面攻击 (Data-level Attacks)

| 攻击名称 | 机制 | 效果 |
|---------|------|------|
| **Label Flipping** | 将训练数据标签随机翻转、定向翻转或统一翻转到某类 | 降低全局模型准确率，产生定向误分类 |
| **Backdoor Data** | 在图像中注入触发器（如右下角白色方块），并将标签改为目标类 | 模型在正常数据上表现正常，但遇到带触发器的输入时产生后门行为 |

### 3.2 模型层面攻击 (Model-level Attacks)

| 攻击名称 | 机制 | 对抗目标 |
|---------|------|---------|
| **Sign-flipping** | 将模型更新（梯度）符号翻转 | 使全局模型向相反方向更新，破坏收敛 |
| **Scaling** | 将恶意更新乘以大系数（如 10x） | 在加权聚合中放大恶意影响，实施模型替换 |
| **Gaussian Noise** | 在更新中加入大量高斯噪声 | 作为非定向拜占庭攻击，降低模型性能 |
| **Backdoor Model** | 数据后门 + 缩放攻击组合 | 将后门注入全局模型，同时尽量维持正常准确率 |
| **Mimic (ALIE)** | 对更新进行微小但协调的偏移 | 绕过基于统计的防御，难以被检测 |
| **Constant** | 发送固定常数（如全0）更新 | 拉低全局模型性能，构造简单拜占庭行为 |

### 3.3 攻击配置示例

在 `attack_config.yaml` 的 `attacks` 字段中配置：

```yaml
attacks:
  - name: "sign_flipping"
    type: "sign_flipping"
    malicious_clients:
      count: 2          # 2个恶意客户端
      mode: "random"    # 随机选择
    data_attack:
      type: "label_flipping"
      flip_mode: "random"
      poison_rate: 1.0
    model_attack_params:
      flip_rate: 1.0
      scale: 1.0
```

---

## 四、防御手段全景

防御同样分为两类：**鲁棒聚合规则**（替换 FedAvg）和 **异常检测过滤**（聚合前清洗）。

### 4.1 鲁棒聚合规则

| 防御名称 | 核心思想 | 适用场景 |
|---------|---------|---------|
| **FedAvg** | 标准加权平均 | 基线，无攻击时最优 |
| **Median** | 逐坐标中值 | 恶意客户端较多，且更新维度独立 |
| **Trimmed Mean** | 截断两端极端值后取平均 | 已知恶意比例上限，计算高效 |
| **Krum** | 选择与其他更新最相似的一个 | 恶意客户端比例 < 50% |
| **Multi-Krum** | 选多个最可信的更新再 FedAvg | Krum 的改进版，更稳定 |
| **Geometric Median** | 最小化到所有更新距离之和 | 对异常值鲁棒，但计算开销较大 |

### 4.2 异常检测过滤

| 防御名称 | 检测机制 | 作用时机 |
|---------|---------|---------|
| **Norm Clip** | 更新范数超过中位数 N 倍则剔除 | 聚合前 |
| **Cosine Similarity** | 与参考更新（如中位数）余弦相似度过低则剔除 | 聚合前 |
| **MAD (Median Absolute Deviation)** | 基于稳健标准差剔除离群更新 | 聚合前 |
| **Multi-Criteria** | Norm Clip + Cosine Similarity 联合过滤 | 聚合前，更保守 |

### 4.3 防御配置示例

```yaml
defenses:
  - name: "trimmed_mean"
    aggregation_rule: "trimmed_mean"
    anomaly_filter: null
    params:
      trim_ratio: 0.2    # 截断 20%

  - name: "multi_krum"
    aggregation_rule: "multi_krum"
    anomaly_filter: null
    params:
      f: null            # 自动推断恶意数
```

---

## 五、实验矩阵与运行逻辑

`AttackExperimentRunner` 会自动构建如下实验矩阵：

```
对每个 mode in [plain, encrypted]:
  ├── baseline: 无攻击 + FedAvg
  ├── attack_1 + defense_1
  ├── attack_1 + defense_2
  ├── attack_1 + defense_3
  ├── attack_2 + defense_1
  ├── attack_2 + defense_2
  └── ...
```

每个实验独立运行，结果保存为 JSON，最终生成 `summary_report.md` 汇总对比。

---

## 六、各攻击的最佳防御实践

以下基于联邦学习鲁棒性研究的文献和实验经验，给出应对每种攻击的推荐防御策略：

### 6.1 应对 Sign-flipping / Scaling / Constant 攻击

**特征**：更新方向明显异常，范数可能过大或过小。

**推荐防御**：
1. **Trimmed Mean**：直接截断极端值，对方向翻转和常数攻击非常有效。
2. **Multi-Krum**：选择最"正常"的更新，排除明显离群的恶意客户端。
3. **Norm Clip + FedAvg**：先过滤掉范数异常大的更新，再用 FedAvg 聚合。

### 6.2 应对 Gaussian Noise 攻击

**特征**：更新被大量噪声污染，统计上与正常更新差异大。

**推荐防御**：
1. **Median**：中值对高斯噪声有很强的抑制作用。
2. **Trimmed Mean**：截断掉噪声导致的极端值。
3. **MAD 过滤**：基于稳健标准差检测并剔除被噪声严重污染的更新。

### 6.3 应对 Backdoor Model 攻击

**特征**：恶意客户端先进行正常训练（甚至表现更好），然后放大后门更新。更新方向可能并不异常，范数可能被刻意控制。

**推荐防御**：
1. **Multi-Krum / Krum**：如果后门更新数量较少，这些聚合规则可以将其排除。
2. **Cosine Similarity Filter**：检测与大多数客户端方向不一致的更新。
3. **Multi-Criteria Filter**：结合范数和方向检测，增加过滤成功率。
4. **服务器端差分隐私**：聚合时添加少量噪声，可以稀释后门影响。

> ⚠️ **注意**：后门攻击是联邦学习中最难防御的攻击之一，尤其是当恶意客户端知道防御机制并进行了针对性规避（如 ALIE）时。在 CKKS 加密环境下，由于服务器无法直接查看单个客户端的明文更新，防御难度进一步增加。

### 6.4 应对 Mimic / ALIE 攻击

**特征**：攻击者发送精心计算的、看起来正常的更新，统计上与诚实更新难以区分。

**推荐防御**：
1. **Geometric Median**：比 Krum 更难被绕过，对协调偏移有一定抵抗力。
2. **Trimmed Mean**：如果攻击者数量在截断比例内，可以有效中和。
3. **增加客户端数量**：ALIE 的有效性随总客户端数增加而下降。

---

## 七、在 CKKS 加密环境下的特殊考量

### 7.1 攻击是否对加密有效？

**有效**。CKKS 同态加密保护的是单个客户端更新的**隐私性**，但加密是**同态的**——服务器可以直接对密文进行加权聚合。如果恶意客户端上传了被篡改的明文更新并加密，那么聚合后的结果依然会包含攻击的影响。

换句话说：
- **隐私保护**：CKKS 阻止服务器看到单个客户端的更新内容
- **鲁棒性**：CKKS **不阻止** 恶意客户端的影响进入全局模型

### 7.2 在加密环境下如何部署防御？

当前框架的聚合流程是：
1. 服务器收到所有客户端的 CKKS 密文更新
2. 服务器在密文上执行同态加权聚合
3. 辅助节点（HelperNode）解密**聚合后的结果**

这意味着：
- **基于单客户端梯度的防御**（如 Krum、Trimmed Mean、Norm Clip）在标准 CKKS 流程中无法直接部署，因为服务器看不到单个更新的明文。

**解决方案与研究方向**：
1. **方案A（本平台采用的研究方式）**：在明文实验中完整研究攻击与防御；在加密实验中仅展示攻击对最终精度的影响（证明 CKKS 不能自动抵御攻击）。
2. **方案B（辅助节点增强）**：让 HelperNode 在解密每个客户端更新后执行异常检测，再重新聚合。这会牺牲部分同态聚合的效率，但可实现防御。
3. **方案C（安全聚合 + 零知识证明）**：更高级的方案，超出本平台当前范围，但可作为后续研究方向。

本平台目前以**方案A**为主，帮助研究者：
- 全面理解各种攻击在明文下的行为
- 掌握各种防御方法的有效性
- 明确认识到：隐私保护与鲁棒性是两个独立的问题，需要分别解决

---

## 八、扩展建议

你可以在本平台基础上进一步扩展：

1. **更多数据集**：尝试 CIFAR-10、Fashion-MNIST、EMNIST
2. **更复杂的模型**：从 LeNet 切换到 MobileNetV2 或 DenseNet
3. **自适应攻击**：让恶意客户端根据当前全局模型动态调整攻击策略
4. **联邦后门评估**：设计专门的 Backdoor Accuracy 评估指标
5. **加密防御结合**：在 HelperNode 增加逐客户端解密-检测-再聚合的流程

---

## 九、引用

如果你在研究中使用了本平台，欢迎引用原始 CKKS-Fed 框架：

```bibtex
@article{ckks_fed_2026,
  title={CKKS-Fed: Adaptive Noise Management for Single-Key Homomorphic Encryption in Federated Learning},
  author={Anonymous},
  journal={arXiv preprint},
  year={2026}
}
```

---

## 十一、CipherFetch 预取机制详解

> 本节详细描述 CipherFetch（FedFetch 风格）密文预取联邦学习的完整机制，包括核心概念、系统架构、实体交互时序、数学案例与代码实现细节。

### 10.1 核心概念

**CipherFetch** 是一种面向 CKKS 同态加密联邦学习的密文预取机制，核心思想是：

> **未被选中的客户端在空闲时间后台接收服务器广播的密文增量（delta），通过同态加法累加到本地缓存。当被选中参与训练时，只需一次性解密并应用缓存状态，无需在训练前等待下载。**

相比传统 CKKS-Fed（每轮训练前下载完整加密全局模型），CipherFetch 将**训练时延中的下载等待**转移到了**后台空闲时间**，从而降低每轮 wall-clock 延迟。

**关键术语：**

| 术语 | 含义 |
|------|------|
| **Delta** | 每轮聚合后产生的密文增量，即本轮全局模型与上一轮的全局模型之差 |
| **Prefetch** | 服务器向未选中客户端广播 delta，客户端用同态加法累加到本地缓存 |
| **Fetch** | 被选中客户端训练前，下载尚未预取到的缺失 deltas |
| **Sticky Sampling** | 为 future rounds 预采样客户端池，被预取但未选中的客户端获得 sticky score，提高未来被选中的概率 |
| **Overcommitment (OC)** | 预采样池大小 = 实际需要数 × OC，OC>1 提供冗余以应对随机采样偏差 |
| **Warmup** | 前 N 轮不调度预取，用于收集 EMA 轮次耗时和带宽基线 |

**同态加法不变性**：多个 deltas 同态累加后，密文大小**不变**，始终等于单个 delta 大小。预取减少的是"需要 fetch 的客户端数量"和"训练时等待时间"，而非单个客户端的 fetch 数据量。

---

### 10.2 系统架构与实体

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CipherFetch 系统架构                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  服务器端 (PrefetchAggregationServer)                                        │
│  ├── 全局模型管理：维护 plaintext global model + encrypted global state      │
│  ├── 加密增量历史 (encrypted_deltas_history)：按轮次存储每轮产生的密文 delta │
│  ├── 虚拟时钟 (virtual_clock)：模拟 wall-clock 时间，计算每轮持续时间        │
│  ├── 预取调度：调用 broadcast_prefetch_to_unselected() 广播缺失 deltas      │
│  └── 聚合：aggregate_encrypted_updates() 执行同态加权平均                     │
│                                                                             │
│  客户端端 (PrefetchFederatedClient)                                          │
│  ├── 本地模型 + base_model_state（上次同步时的全局模型）                     │
│  ├── prefetched_state：同态累加的密文缓存（CKKS 密文向量）                   │
│  ├── fetch_remaining_deltas()：训练前下载缺失 deltas 并同态累加              │
│  ├── apply_prefetched_state()：一次性解密累加状态并应用到 base model         │
│  └── local_train()：基于最新全局模型执行本地训练                             │
│                                                                             │
│  调度器 (PrefetchScheduler)                                                  │
│  ├── presample_for_target(round)：为目标轮次预采样客户端池                   │
│  └── 带宽预算计算：基于 EMA 轮次耗时和客户端带宽决定是否调度预取              │
│                                                                             │
│  粘性采样 (StickySamplingManager)                                            │
│  ├── 维护 presample_pool: {target_round: {client_id: score}}               │
│  ├── update_on_prefetch()：被预取客户端获得 sticky score 提升               │
│  └── cleanup(round)：删除过期的预采样池                                     │
│                                                                             │
│  带宽模拟器 (BandwidthSimulator)                                             │
│  ├── 为每个客户端生成异构上下行带宽 (kbps)                                   │
│  └── estimate_download_time/upload_time()：基于带宽估计传输时间              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 10.3 完整流程（预取模式）

#### Phase 0: 初始化
1. 服务器初始化全局模型，生成 CKKS 统一上下文（single-key），分发给所有客户端
2. StickySamplingManager 初始化 sticky_group
3. PrefetchScheduler 加载带宽配置

#### Phase 1: 每轮主循环（`run_round_prefetch`）

```
Round R 开始
│
├─→ Step 1: 客户端选择
│   ├─ 从当前轮次的预采样池 (presample_pool[R]) 中选择客户端
│   ├─ 若池不存在，回退到随机采样
│   └─ 输出: selected_clients (size = num_clients × sample_rate)
│
├─→ Step 2: 预取调度（非 warmup 轮）
│   ├─ 为 future rounds (R+1 .. R+max_prefetch_round) 预采样客户端池
│   ├─ 计算带宽预算：是否能在 EMA 轮次耗时内完成预取广播
│   └─ 若预算充足，触发 broadcast_prefetch_to_unselected()
│
├─→ Step 3: 选中客户端训练
│   ├─ 对每个 client in selected_clients:
│   │   ├─ fetch_remaining_deltas(): 下载自上次同步后缺失的 deltas
│   │   │   └─ 服务器可预先同态累加多个 deltas 为 1 个（减少 fetch 次数）
│   │   ├─ apply_prefetched_state(): 解密缓存并应用到 base model
│   │   └─ local_train(): 基于最新全局模型执行本地训练
│   └─ 输出: client_updates (明文梯度/差值)
│
├─→ Step 4: 加密上传
│   ├─ 每个客户端用 CKKS 加密本地更新
│   └─ 输出: encrypted_updates (密文)
│
├─→ Step 5: 同态聚合
│   ├─ 服务器在密文上执行加权平均 (FedAvg)
│   ├─ 更新 plaintext global model
│   └─ 生成新的 encrypted global state
│
├─→ Step 6: 加密增量准备
│   └─ 计算本轮 delta = new_encrypted_state - old_encrypted_state
│   └─ 存入 encrypted_deltas_history[R]
│
├─→ Step 7: 预取广播（训练完成后）
│   └─ broadcast_prefetch_to_unselected(): 向预采样池中的未选中客户端
│      广播自其上次同步以来所有缺失的 deltas
│
├─→ Step 8: 虚拟时钟推进
│   ├─ calculate_round_duration(): 计算本轮持续时间 = max(选中客户端完成时间)
│   └─ advance_virtual_clock(): 推进全局虚拟时钟
│
├─→ Step 9: 记录同步状态
│   └─ record_client_sync(): 更新每个选中客户端的 last_update_index
│
└─→ Round R 结束
```

**通信统计原则**（对齐 FedFetch 论文定义）：
- **Fetch Volume (FV)** = 选中客户端实际 fetch 下载量 `sum(fetch_download_cost)`（已扣除预取覆盖部分）
- **训练通信 TV** = `upload_cost + FV`（选中客户端产生的通信）
- **总通信 Total Comm** = `upload + fetch_download + prefetch_broadcast`（含后台预取，用于与不预取版本对比）
- **Prefetch Broadcast** 属于后台流量，不计入 TV

---

### 10.4 实体交互时序图

以下时序图展示第 3 轮（非 warmup）的完整交互过程，假设 10 个客户端、采样率 0.5（每轮 5 个选中）、Overcommitment=2.0（预采样池 10 个）。

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Server │     │   Sticky    │     │ Prefetch     │     │  Selected   │     │  Unselected  │
│         │     │  Sampling   │     │  Scheduler   │     │  Clients    │     │   Clients    │
└────┬────┘     └──────┬──────┘     └──────┬───────┘     └──────┬──────┘     └──────┬───────┘
     │                 │                   │                    │                   │
     │  (1) presample_for_target(R+3)     │                    │                   │
     │────────────────>│                   │                    │                   │
     │                 │  (2) 生成预采样池  │                    │                   │
     │                 │  (pool_size=10)   │                    │                   │
     │<────────────────│                   │                    │                   │
     │                 │                   │                    │                   │
     │  (3) 从 pool[R] 中选择 5 个客户端   │                    │                   │
     │────────────────────────────────────>│                    │                   │
     │                 │                   │  (4) 返回 selected  │                    │
     │<────────────────────────────────────│                    │                   │
     │                 │                   │                    │                   │
     │  (5) get_remaining_fetch_info(cid)  │                    │                   │
     │─────────────────────────────────────────────────────────>│                   │
     │                 │                   │                    │  (6) 计算缺失 deltas│
     │                 │                   │                    │  (last_synced+prefetched│
     │                 │                   │                    │   to current_round)    │
     │<─────────────────────────────────────────────────────────│                   │
     │                 │                   │                    │                   │
     │  (7) 服务器同态累加缺失 deltas 为 1 个 │                    │                   │
     │     返回 {count:1, size:delta_size} │                    │                   │
     │─────────────────────────────────────────────────────────>│                   │
     │                 │                   │                    │                   │
     │                 │                   │                    │  (8) fetch & 同态累加 │
     │                 │                   │                    │  (9) 解密并应用缓存   │
     │                 │                   │                    │  (10) local_train()  │
     │                 │                   │                    │  (11) encrypt_update │
     │─────────────────────────────────────────────────────────│                   │
     │                 │                   │                    │  返回 encrypted_update│
     │                 │                   │                    │                   │
     │  (12) aggregate_encrypted_updates() │                    │                   │
     │       同态加权平均，更新全局模型       │                    │                   │
     │                 │                   │                    │                   │
     │  (13) encrypt_and_stage_prefetch()  │                    │                   │
     │       生成 delta 并存入历史           │                    │                   │
     │                 │                   │                    │                   │
     │  (14) broadcast_prefetch_to_unselected(pool_unselected) │                    │
     │────────────────────────────────────────────────────────────────────────────────>│
     │                 │                   │                    │                   │
     │                 │                   │                    │                   │  (15) receive_prefetch_delta()
     │                 │                   │                    │                   │       同态累加到本地缓存
     │                 │                   │                    │                   │
     │  (16) record_client_sync(selected)  │                    │                   │
     │  (17) advance_virtual_clock()       │                    │                   │
     │                 │                   │                    │                   │
```

**关键交互说明：**

1. **预采样 (Steps 1-4)**：Sticky Sampling 提前为 future rounds 决定候选池，OC=2.0 意味着池大小是实际需要数的 2 倍。
2. **Fetch (Steps 5-9)**：选中客户端训练前，服务器计算其缺失的 deltas，可预先同态累加多个 deltas 为 1 个（减少通信次数）。客户端下载后解密应用到 base model。
3. **训练与上传 (Steps 10-11)**：客户端基于最新模型训练，加密差值上传。
4. **预取广播 (Steps 14-15)**：训练完成后，服务器向预采样池中的未选中客户端广播缺失 deltas。这些客户端在后台用同态加法累加，不干扰当前训练。

---

### 10.5 预取数学案例

以下用一个具体数值案例说明 CipherFetch 如何减少训练时延。

**场景设定：**
- 10 个客户端，每轮采样 5 个（sample_rate=0.5）
- 每个 delta 大小 = 6 MB
- 客户端下行带宽 = 1 Mbps（约 125 KB/s）
- 客户端上行带宽 = 0.5 Mbps（约 62.5 KB/s）
- 本地训练时间 = 10 s
- 加密时间 = 0.1 s
- Warmup = 2 轮，总轮数 = 5 轮

#### Case 1: 传统 CKKS-Fed（无预取）

每轮流程（选中客户端）：
1. 下载完整加密全局模型：6 MB / 1 Mbps = **48 s**
2. 本地训练：**10 s**
3. 加密上传：6 MB / 0.5 Mbps = **96 s**
4. 总单客户端耗时 = 48 + 10 + 96 = **154 s**

每轮 wall-clock 时间（假设 5 个客户端并行）：**154 s**
5 轮总时间 = 5 × 154 = **770 s**

#### Case 2: CipherFetch（有预取）

**Warmup 轮次（Round 1-2）：**
- 无预取广播，选中客户端需 fetch 所有缺失 deltas
- Round 1: 无缺失 delta（首次训练），时间 = 0 + 10 + 96 = **106 s**
- Round 2: 需 fetch 1 个 delta = 6 MB，下载 = 48 s，时间 = 48 + 10 + 96 = **154 s**

**预取轮次（Round 3-5）：**
- 假设预取覆盖了 3/5 的选中客户端（它们已有缓存，无需 fetch）
- 2 个客户端仍需 fetch 1 个 delta = 48 s
- 3 个客户端无需 fetch = 0 s

每轮 wall-clock 时间 = max(有 fetch 客户端时间, 无 fetch 客户端时间)
= max(48 + 10 + 96, 0 + 10 + 96) = **154 s**

等等，这样看 wall-clock 时间没有减少？因为 wall-clock 时间由最慢的客户端决定。

**关键洞察**：CipherFetch 的优势在以下场景更明显：
1. **异构带宽环境**：快客户端预取更多，慢客户端成为瓶颈时，预取确保大部分客户端无需等待
2. **多轮 delta 累积**：当客户端多轮未被选中时，fetch 需要下载多个 deltas。预取将这些下载分散到多轮空闲时间
3. **与完整模型下载对比**：如果传统方案每轮下载完整模型（而非 delta），预取优势更大

**修正案例（更 realistic）：**

假设传统方案每轮下载**完整加密模型**（6 MB），而 CipherFetch 只需 fetch **缺失 deltas**。

| 轮次 | 传统方案（下载完整模型） | CipherFetch（fetch deltas） | 预取广播（后台） |
|------|------------------------|----------------------------|----------------|
| R1   | 下载 6 MB = 48 s       | 0 s（首次训练）            | 0 s（warmup）  |
| R2   | 下载 6 MB = 48 s       | fetch 1 delta = 48 s       | 0 s（warmup）  |
| R3   | 下载 6 MB = 48 s       | 2 客户端 fetch 1δ=48s, 3 客户端已预取=0s | 5 客户端各预取 1δ |
| R4   | 下载 6 MB = 48 s       | 1 客户端 fetch 1δ=48s, 4 客户端已预取=0s | 5 客户端各预取 1δ |
| R5   | 下载 6 MB = 48 s       | 2 客户端 fetch 1δ=48s, 3 客户端已预取=0s | 5 客户端各预取 1δ |

**Wall-clock 时间对比：**
- 传统方案每轮 = 48（下载）+ 10（训练）+ 96（上传）= **154 s**
- CipherFetch 每轮 = max(fetch_time) + 10 + 96
  - R1: 0 + 10 + 96 = **106 s**
  - R2: 48 + 10 + 96 = **154 s**
  - R3-R5: 48 + 10 + 96 = **154 s**（最慢客户端仍需 fetch）

**通信量对比（5 轮）：**
- 传统方案：每轮 5 客户端 × (6MB 下载 + 6MB 上传) = 60 MB/轮 × 5 = **300 MB**
- CipherFetch：
  - Upload: 5 × 6MB × 5轮 = 150 MB
  - Fetch: 约 10 次 × 6MB = 60 MB
  - Prefetch Broadcast: 约 15 次 × 6MB = 90 MB（后台）
  - 训练通信 TV = 150 + 60 = **210 MB**（比传统方案少 30%）
  - 总通信 = 150 + 60 + 90 = **300 MB**（公平对比总量相同）

**实际优势**：在异构带宽下，预取使得**大部分客户端**无需在训练前等待下载，只有极少数"掉队"客户端需要 fetch。虚拟时钟（模拟 wall-clock）显著降低。

---

### 10.6 代码细节

#### 10.6.1 关键类继承关系

```python
# ckks_fed/client.py
class FederatedClient:
    """基础客户端：本地训练、模型管理"""
    def local_train(self, global_params=None): ...
    def get_model_params(self): ...
    def set_model_params(self, params): ...

class PrefetchFederatedClient(FederatedClient):
    """预取客户端：扩展密文缓存和预取管理"""
    def __init__(self, ...):
        self.prefetched_state = None          # 同态累加的密文缓存
        self.total_prefetch_download_cost = 0 # 累计预取下载量
        self.total_fetch_download_cost = 0    # 累计 fetch 下载量
        self.last_synced_round = -1           # 上次同步的轮次
        self.base_model_state = None          # 上次同步时的模型状态

    def receive_prefetch_delta(self, delta, delta_size, from_round):
        """接收预取 delta，同态累加到本地缓存"""
        if self.prefetched_state is None:
            self.prefetched_state = delta
        else:
            self.prefetched_state = self._homomorphic_add(
                self.prefetched_state, delta)
        self.total_prefetch_download_cost += delta_size

    def fetch_remaining_deltas(self, current_round, server, ...):
        """训练前：fetch 缺失 deltas 并应用"""
        fetch_info = server.get_remaining_fetch_info(self.client_id, current_round)
        if fetch_info:
            # 下载并同态累加
            for delta in fetch_info['deltas']:
                self.prefetched_state = self._homomorphic_add(...)
            self.total_fetch_download_cost += fetch_info['total_size']

    def apply_prefetched_state(self, ckks_manager):
        """一次性解密缓存并应用到 base model"""
        if self.prefetched_state is not None:
            decrypted = ckks_manager.decrypt_vector(self.prefetched_state)
            self._apply_to_model(decrypted)
            self.prefetched_state = None

    def local_train_with_prefetch(self, current_round, server, ckks_manager, ...):
        """完整训练流程：fetch → apply → train"""
        self.fetch_remaining_deltas(current_round, server, ...)
        self.apply_prefetched_state(ckks_manager)
        update, loss, acc = self.local_train(global_params=None)
        self.last_synced_round = current_round
        return update, loss, acc
```

#### 10.6.2 服务器预取广播

```python
# ckks_fed/server.py
class PrefetchAggregationServer(AggregationServer):
    def __init__(self, ...):
        self.encrypted_deltas_history = []    # [{delta, size, from_round}, ...]
        self.last_update_index = {}           # client_id -> 上次同步的 delta 索引
        self.client_prefetch_counts = {}      # client_id -> 已预取的 delta 数量
        self.global_virtual_clock = 0.0

    def broadcast_prefetch_to_unselected(self, unselected_ids, client_objects,
                                         target_pool_ids=None):
        """向未选中客户端广播缺失 deltas"""
        pool_set = set(target_pool_ids) if target_pool_ids else None
        ids_to_broadcast = [cid for cid in unselected_ids
                           if cid in pool_set] if pool_set else unselected_ids

        for cid in ids_to_broadcast:
            last_synced = self.last_update_index.get(cid, 0)
            prefetched = self.client_prefetch_counts.get(cid, 0)
            start_idx = last_synced + prefetched
            missing_deltas = self.encrypted_deltas_history[start_idx:]

            client = client_objects[cid]
            for delta_info in missing_deltas:
                client.receive_prefetch_delta(
                    delta_info['delta'], delta_info['size'], delta_info['from_round'])
                self.client_prefetch_counts[cid] += 1

    def get_remaining_fetch_info(self, client_id, current_round, is_warmup=False):
        """计算客户端还需 fetch 的 deltas"""
        last_synced = self.last_update_index.get(client_id, 0)
        total_needed = max(0, current_round - last_synced)
        prefetched = self.client_prefetch_counts.get(client_id, 0)
        remaining = max(0, total_needed - prefetched)

        if remaining == 0:
            return None

        # 获取缺失的 deltas
        deltas_to_fetch = self.encrypted_deltas_history[
            last_synced + prefetched : last_synced + prefetched + remaining]

        # 服务器预先同态累加多个 deltas 为 1 个（减少通信次数）
        if len(deltas_to_fetch) > 1:
            merged_delta = deltas_to_fetch[0]['delta']
            for di in deltas_to_fetch[1:]:
                merged_delta = self.ckks_manager.homomorphic_add(merged_delta, di['delta'])
            # 同态加法后大小不变
            return {'count': 1, 'total_size': deltas_to_fetch[0]['size'],
                    'deltas': [merged_delta]}
        else:
            return {'count': 1, 'total_size': deltas_to_fetch[0]['size'],
                    'deltas': [deltas_to_fetch[0]['delta']]}

    def calculate_round_duration(self, selected_ids, client_objects, current_round):
        """计算本轮持续时间 = max(选中客户端完成时间)"""
        durations = []
        for cid in selected_ids:
            client = client_objects[cid]
            # 计算 fetch 时间（基于带宽模拟器）
            fetch_info = self.get_remaining_fetch_info(cid, current_round)
            fetch_time = 0.0
            if fetch_info:
                size_bits = fetch_info['total_size'] * 8
                fetch_time = self.bandwidth_simulator.estimate_download_time(cid, size_bits)

            # 总时间 = fetch + 训练 + 加密 + 上传
            total_time = (fetch_time + client.local_train_time +
                          client.encryption_time +
                          self.bandwidth_simulator.estimate_upload_time(
                              cid, client.ciphertext_size * 8))
            durations.append(total_time)

        round_duration = max(durations) if durations else 0.0
        return round_duration
```

#### 10.6.3 Sticky Sampling 调度

```python
# ckks_fed/sticky_sampling.py
class StickySamplingManager:
    def __init__(self, num_clients, sample_rate, overcommitment=2.0, ...):
        self.presample_pool = {}  # {target_round: {client_id: score}}
        self.sticky_group = set()
        self.overcommitment = overcommitment

    def presample_for_target(self, target_round, num_needed):
        """为目标轮次预采样客户端池"""
        pool_size = int(num_needed * self.overcommitment)
        # 从 sticky_group 优先选择高分客户端
        candidates = sorted(self.sticky_group, key=lambda c: self.scores.get(c, 0),
                           reverse=True)
        selected = candidates[:pool_size]
        # 补充随机客户端
        remaining = [c for c in range(self.num_clients) if c not in selected]
        selected += random.sample(remaining, pool_size - len(selected))

        self.presample_pool[target_round] = {cid: self.scores.get(cid, 1.0)
                                              for cid in selected}
        return selected

    def update_on_prefetch(self, client_id, was_selected):
        """被预取但未选中的客户端获得 sticky score 提升"""
        if not was_selected:
            self.scores[client_id] = self.scores.get(client_id, 1.0) / self.decay

    def cleanup(self, current_round):
        """删除过期的预采样池"""
        expired = [r for r in self.presample_pool if r < current_round]
        for r in expired:
            del self.presample_pool[r]
```

#### 10.6.4 主循环入口

```python
# main.py
class CKKSFedPrefetchExperiment:
    def run_round_prefetch(self, round_num):
        # 1. 选择客户端
        selected_clients = self._select_clients_for_round(round_num)
        selected_ids = [c.client_id for c in selected_clients]

        # 2. 调度预取（为 future rounds 预采样）
        if not is_warmup:
            future_ids = self.sticky_manager.get_presample_pool(round_num + 1)
            self.prefetch_scheduler.schedule_prefetch(...)

        # 3. 选中客户端训练（含 fetch + apply + train）
        for client in selected_clients:
            update, loss, acc = client.local_train_with_prefetch(
                round_num, self.server, self.ckks_manager, ...)

        # 4. 加密上传
        encrypted_updates = [client.encrypt_update(u, self.ckks_manager)
                             for u in client_updates]

        # 5. 同态聚合
        aggregated = self.server.aggregate_encrypted_updates(...)
        self.server.update_global_model(aggregated)

        # 6. 生成 delta 并加入历史
        enc_info = self.server.encrypt_and_stage_prefetch(self.ckks_manager)

        # 7. 预取广播（向未选中客户端广播缺失 deltas）
        unselected = [c for c in self.clients if c.client_id not in selected_ids]
        round_prefetch_cost = self.server.broadcast_prefetch_to_unselected(...)

        # 8. 虚拟时钟推进
        round_duration = self.server.calculate_round_duration(selected_ids, ...)
        self.server.advance_virtual_clock(round_duration)

        # 9. 记录同步
        for client in selected_clients:
            self.server.record_client_sync(client.client_id, round_num)
```

#### 10.6.5 关键配置参数

```yaml
# configs/config.yaml
prefetch:
  enable_prefetch: true        # 是否启用预取
  use_sticky_sampling: false   # 是否启用粘性采样
  max_prefetch_round: 3        # 最大提前预取轮数（窗口大小）
  warmup_round: 2              # 预热轮数
  overcommitment: 2.0          # 过承诺比例（池大小 = 需要数 × OC）
  scheduler_beta: 0.5          # 调度器松弛系数
  sticky_decay: 0.9            # 粘性分数衰减因子
  sticky_group_size: 8         # 粘性组大小
  sticky_change_num: 1         # 每轮替换的客户端数
```

---

## 十二、TESK-EGD-ZM 方案流程（实体顺序视图）

> **TESK-EGD-ZM** = TEE-Encapsulated Single-Key CKKS with Zero-Sum Client Masking  
> 本节按**实体执行的时间顺序**，完整描述从系统初始化到每轮联邦学习的闭环流程。

### 12.1 实体定义与信任边界

| 实体 | 代号 | 持有的敏感信息 | 信任级别 | 说明 |
|------|------|---------------|---------|------|
| **KGC** | 密钥生成中心 | 初始化阶段持有 sk、{b_i} | 完全可信，初始化后离线 | 生成密钥和掩码，分发后销毁所有状态 |
| **Client_i** | 第 i 个客户端 | (sk, b_i) | 半可信（可能窥探其他客户端） | n 个客户端，共享 sk 但各自掩码隔离 |
| **Server Host** | 服务器主机 | pk, evk, 明文模型 | 不可信 | 执行密文聚合、通信调度，**不接触 sk** |
| **TEE** | 可信执行环境 | **密封存储** (sk, {b_i}, {w_i}) | 硬件级可信 | 在隔离内存中执行解密、掩码抵消、模型更新 |

**通信通道**：
- KGC → Client_i：TLS 一对一（传输 sk + b_i）
- KGC → Server Host：TLS（传输 sealed_bundle）
- Client_i ↔ Server Host：HTTPS（密文上传/预取下载）
- Server Host ↔ TEE：ECALL/OCALL 模拟（同一物理机内部）

---

### 12.2 方案概览

TESK-EGD-ZM 在标准单密钥 CKKS-FL 基础上，引入**加权零和盲化掩码**解决客户端合谋漏洞：

1. **客户端加密前**：在梯度上叠加私有掩码 $b_i$（其他客户端不知道）
2. **服务器聚合**：对盲化密文执行标准同态加权平均
3. **TEE 解密后**：利用密封存储的完整掩码集 $\{b_i\}$，精确减去加权掩码残差 $\beta_j$
4. **结果**：恢复无偏的真实加权梯度，误差仅来自 CKKS 近似噪声

```
┌─────────┐    TLS    ┌─────────────┐    HTTPS    ┌─────────────┐
│   KGC   │──────────>│  Client_i   │<───────────>│ Server Host │
│ (离线)  │    TLS    │  (sk, b_i)  │   ct_upload │  (pk, 明文) │
└─────────┘──────────>│             │             │      │      │
       │              └─────────────┘             │      │      │
       │ sealed_bundle                            │  ECALL│      │
       └─────────────────────────────────────────>│      ▼      │
                                                  │    ┌───┐    │
                                                  │    │TEE│    │
                                                  │    │sk │    │
                                                  │    │{bi}   │
                                                  │    └───┘    │
                                                  │      │      │
                                                  │  ct_prefetch│
                                                  │      ▼      │
                                                  │  Client_i   │
                                                  └─────────────┘
```

---

### 12.3 Phase 0: 系统初始化（KGC 主导）

**执行实体顺序**：KGC → (Client_1, ..., Client_n, Server Host) → KGC 离线

```
Step 0.1  [KGC] 生成 CKKS 密钥对
          (sk, pk, evk) ← CKKS.KeyGen(λ, N=8192, coeff_mod, Δ=2^40)

Step 0.2  [KGC] 计算聚合权重
          w_i = |D_i| / Σ_j |D_j|,  i = 1,...,n

Step 0.3  [KGC] 生成加权零和掩码
          u_i ~ U[-B, B]^{N/2}          (独立随机采样)
          u_mean = Σ_i w_i u_i          (加权均值)
          b_i = u_i - u_mean            (零和掩码)
          验证: Σ_i w_i b_i = 0

Step 0.4  [KGC] 构建密钥包并密封
          key_bundle = (sk, {b_i}, {w_i})
          sealed_bundle = TEE.Seal(key_bundle, enclave_identity)
          code_hash = Hash(enclave_binary)
          Quote_E = TEE.GenerateQuote(code_hash)

Step 0.5  [KGC] 分发（按严格顺序）
          ├─→ (sk, b_i) ──TLS──> Client_i    (一对一通道，Client_i 不知道 b_j)
          ├─→ sealed_bundle ──TLS──> Server Host ──加载──> TEE
          ├─→ pk, evk ──广播──> 所有实体
          └─→ Quote_E ──广播──> 所有实体（远程 attestation）

Step 0.6  [KGC] 销毁所有敏感状态，永久离线
```

**初始化后的密钥分布状态**：

| 实体 | 知道的密钥/掩码 | 不知道的 |
|------|----------------|---------|
| Client_i | sk, b_i | b_j (j≠i) |
| Server Host | pk, evk | sk, 所有 b_i |
| TEE (密封) | sk, {b_1,...,b_n}, {w_i} | 无（完整视图） |

---

### 12.4 Phase 1: 每轮联邦学习（Round R）

**执行实体顺序**：Client → Server Host → TEE → Server Host → Client

#### Step 1: 客户端本地训练 [Client_i]

```
[Client_i]
  │
  ├─ 基于上一轮同步的全局模型执行本地训练
  ├─ 计算原始梯度 g_i = ∇L_i(θ_t)
  └─ 输出: g_i (明文梯度向量)
```

#### Step 2: 客户端残差 + 盲化 + 稀疏化 [Client_i]

```
[Client_i]
  │
  ├─ Step 2.1 应用 PTopk 客户端残差
  │     g_input = g_i + client_residual
  │
  ├─ Step 2.2 叠加盲化掩码（核心安全操作）
  │     g_blinded = g_input + b_i      (逐元素相加)
  │     ▶ 即使密文被截获，解密后看到的是 g_input + b_i，无法分离真实梯度
  │
  ├─ Step 2.3 包级稀疏化
  │     将 g_blinded 分块为 m 个 batch
  │     计算每 batch L2 范数
  │     S_selected = TopK({norm_j}, k = ceil(sparsity_rate × m))
  │     client_residual[unselected] += batch_j  (未选中部分保留)
  │
  └─ Step 2.4 加密选中 batch
        对 j ∈ S_selected:
            z_j = CKKS.Encode(batch_j, Δ)
            ct_j = CKKS.Enc(pk, z_j)
        输出: ct_i_sparse = {ciphertexts: [ct_j], mask: [...], ...}
```

#### Step 3: 密文上传 [Client_i → Server Host]

```
[Client_i] ──HTTPS──> [Server Host]
  │
  └─ 上传 ct_i_sparse（仅选中 batch 的密文）
```

#### Step 4: 服务器密文聚合 [Server Host]

```
[Server Host]
  │
  ├─ 接收所有活跃客户端的 {ct_i_sparse}_{i∈S_active}
  │
  └─ 按 batch 位置逐批聚合（同态运算，无需解密）
        对 batch j:
            S_j = {i : j ∈ S_selected^{(i)}}
            ct_agg,j = Σ_{i∈S_j} w_i × ct_{i,j}
        输出: ct_agg_sparse
```

> **关键性质**：同态聚合保持线性，盲化项在聚合中自然累积：
> $$\text{ct}_{\text{agg},j} = \sum_{i \in S_j} w_i \cdot \text{Enc}(pk, g_{i,j} + b_{i,j}) = \text{Enc}\left(pk, \sum_{i \in S_j} w_i (g_{i,j} + b_{i,j})\right)$$

#### Step 5: TEE 解密 + 掩码抵消 [TEE]（核心步骤）

```
[Server Host] ──ECALL──> [TEE]
                              │
  Step 5.1  加载密封状态      │
            (sk, {b_i}, {w_i}) ← Unseal(sealed_bundle)
            M_t ← LoadModelFromSecureMemory()
                              │
  Step 5.2  逐 batch 解密     │
            对 batch j:
                m_dec,j = Dec(sk, ct_agg,j)
                z_j = CKKS.Decode(m_dec,j)
                δ_plain,j = Re(z_j)[:S]
                              │
            此时 δ_plain,j = Σ_{i∈S_j} w_i (g_{i,j} + b_{i,j})
                           = Σ_{i∈S_j} w_i g_{i,j}  +  β_j
                           = 真实梯度  +  掩码残差
                              │
  Step 5.3  掩码抵消（安全核心） │
            对 batch j:
                β_j = Σ_{i∈S_j} w_i × b_{i,j}     (TEE 持有全部 b_i，可精确计算)
                δ_pure,j = δ_plain,j − β_j
                              │
            结果: δ_pure,j = Σ_{i∈S_j} w_i g_{i,j}  (误差仅来自 CKKS 噪声)
                              │
  Step 5.4  重组完整梯度       │
            δ_pure = ReconstructFromBatches({δ_pure,j}, mask, d)
```

#### Step 6: PTopk 服务器累加器 [TEE]

```
[TEE]
  │
  ├─ delayed 模式:
  │     server_accumulator += δ_pure × lr
  │     若 round % sync_interval == 0:
  │         δ_acc = server_accumulator.clone()
  │         server_accumulator.zero_()
  │     否则:
  │         δ_acc = 0 (跳过本轮更新)
  │
  ├─ momentum 模式:
  │     acc = β × acc + (1−β) × δ_pure × lr
  │     δ_acc = acc.clone()
  │
  └─ none 模式:
        δ_acc = δ_pure × lr
```

#### Step 7: 模型更新 [TEE]

```
[TEE]
  │
  └─ M_{t+1} = M_t + δ_acc
```

#### Step 8: 重新加密全局状态 [TEE]

```
[TEE]
  │
  ├─ ct_global = CKKS.Enc(pk, Pack(M_{t+1}))
  └─ 将 ct_global 写回 Server Host 的加密全局状态
```

#### Step 9: 密文预取 [TEE → Server Host → Client_i]

```
[TEE]
  │
  ├─ 对每个客户端 i:
  │     Δ_prefetch_i = ComputePrefetch(M_{t+1}, M_t, i)
  │     ct_prefetch_i = CKKS.Enc(pk, Δ_prefetch_i)
  │
  └─ 输出 {ct_prefetch_i} 到 Server Host

[Server Host]
  │
  └─ 通过 HTTPS 将 ct_prefetch_i 发送给 Client_i

[Client_i]
  │
  ├─ 接收 ct_prefetch_i
  ├─ Δ_plain = CKKS.Decrypt(sk, ct_prefetch_i)
  ├─ M_local = M_local + Δ_plain
  └─ 清除预取缓存
```

> **预取安全性**：ct_prefetch_i 是标准 CKKS 密文，窃听者/Server Host 无 sk 无法解密。

#### Step 10: 安全清理 [TEE]

```
[TEE]
  │
  └─ 内存清零:
      sk ← 0
      {b_i} ← 0
      δ_pure ← 0
      δ_acc ← 0
      {Δ_prefetch_i} ← 0
```

---

### 12.5 实体交互时序图（单轮）

```
Time ────────────────────────────────────────────────────────────────────────>

[KGC]        (离线，不参与每轮执行)

[Client_1]   ┌训练┐  ┌盲化+稀疏┐  ┌加密┐  ┌──────等待──────┐  ┌解密预取┐
             └────┘  └────────┘  └────┘  │                │  └────────┘
                                          │                │
[Client_2]   ┌训练┐  ┌盲化+稀疏┐  ┌加密┐  │                │  ┌解密预取┐
             └────┘  └────────┘  └────┘  │                │  └────────┘
                                          │                │
[Client_n]   ┌训练┐  ┌盲化+稀疏┐  ┌加密┐  │                │  ┌解密预取┐
             └────┘  └────────┘  └────┘  │                │  └────────┘
                                          ▼                ▼
[Server Host]        ┌──────────────────────────────────────┐
                     │  接收密文 → 同态聚合 → 转发 TEE     │
                     └──────────────────────────────────────┘
                                          │
                                          ▼
[TEE]                                   ┌──────────────────┐
                                        │ 解密 → 掩码抵消  │
                                        │ → PTopk → 更新   │
                                        │ → 重加密 → 预取  │
                                        └──────────────────┘
                                          │
                                          ▼
[Server Host]                           ┌──────────────────┐
                                        │ 接收 ct_global   │
                                        │ 分发 ct_prefetch │
                                        └──────────────────┘
```

---

### 12.6 安全状态追踪（每轮）

| 步骤 | 操作实体 | sk 暴露位置 | 掩码 $\{b_i\}$ 暴露位置 | 明文梯度暴露位置 |
|------|---------|------------|----------------------|----------------|
| 1-2 | Client | Client 本地内存 | 仅 $b_i$（Client_i 知道） | Client 本地 |
| 3 | Client → Server Host | 无 | 无 | 无（密文传输） |
| 4 | Server Host | 无 | 无 | 无（密文聚合） |
| 5-7 | TEE | **TEE 隔离内存** | **TEE 隔离内存** | **TEE 隔离内存** |
| 8-9 | TEE → Client | Client 本地内存 | 仅 $b_i$ | Client 本地（预取 delta） |
| 10 | TEE | 已清零 | 已清零 | 已清零 |

> **结论**：明文梯度 $g_i$ 仅在 Client 本地和 TEE 隔离内存中出现，Server Host 全程无法访问任何单个客户端的明文更新。

---

### 12.7 与标准单密钥 CKKS-FL 的关键区别

| 特性 | 标准单密钥 CKKS-FL | **TESK-EGD-ZM** |
|------|-------------------|-----------------|
| 客户端间保密性 | ❌ 无（共享 sk，任意客户端可解密其他客户端） | ✅ **有**（盲化掩码隔离） |
| sk 存储位置 | 客户端 + Server/HelperNode | **仅 TEE 密封存储** |
| 聚合正确性 | 精确 | **精确**（掩码精确抵消） |
| 合谋抵抗 | ❌ n-1 合谋 = 完全泄露 | ⚠️ **需 < n-1 合谋**（零和约束限制） |
| 额外计算 | 无 | TEE 内 $O(d)$ 掩码抵消 |
| 额外通信 | 无 | 无（仅初始化分发掩码） |

---

## 十二、License

MIT License
