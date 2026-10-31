# CKKS-Fed / CipherFetch 项目架构全梳理

> 基于代码库全面阅读与模块分析  
> 总代码量：~13,800 行（ckks_fed/ 目录下 37 个 Python 文件）

---

## 一、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              实验入口层                                       │
│  main.py ──► CKKSFedExperiment                                               │
│    ├── MetricsCollector (指标收集)                                           │
│    ├── _init_components() (初始化)                                           │
│    ├── run_round_plain() / run_round_encrypted()                            │
│    └── run_experiment()                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   数据与模型    │           │   客户端层     │           │   服务端层     │
│   data.py     │◄─────────►│  client.py    │◄─────────►│  server.py    │
│   models.py   │           │  (Federated   │           │  (Aggregation │
│               │           │   /Prefetch/  │           │   Server)     │
│               │           │   Malicious)  │           │               │
└───────────────┘           └───────┬───────┘           └───────┬───────┘
                                    │                           │
                    ┌───────────────┴───────────────┐           │
                    ▼                               ▼           ▼
            ┌───────────────┐           ┌───────────────────────────────┐
            │  加密与打包层   │           │         聚合与防御层            │
            │   crypto.py   │           │  defenses/aggregation_rules.py│
            │   packing.py  │           │  defenses/anomaly_detection.py│
            │sparsification │           │  global_mask_vote.py          │
            │   ptopk.py    │           │                               │
            └───────────────┘           └───────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│  客户端选择层   │       │   TEE 层       │
│client_select. │       │ tee_enclave.py│
│   .py         │       │ server_tee.py │
└───────────────┘       │ tee_simulator │
                        └───────────────┘
        ┌───────────┐
        ▼           ▼
┌───────────────┐ ┌───────────────┐
│  带宽模拟器     │ │  盲化掩码层    │
│ bandwidth_sim │ │ blinding_mask │
└───────────────┘ └───────────────┘
        │
        ▼
┌───────────────┐
│  攻击与实验     │
│attacks/*.py   │
│experiments/   │
│attack_runner  │
└───────────────┘
```

---

## 二、四大核心数据流

### 数据流 A：明文联邦学习 (Baseline)

```
Server: global_model (明文)
    │
    ▼ [Select 30 clients]
Client.local_train(global_params)
    ├── decrypt? ❌ (直接接收明文)
    ├── train N epochs
    └── return model_update (明文Tensor字典)
    │
    ▼ [Upload]
Server.aggregate_plain_updates()
    ├── _apply_defense()     ← 异常检测 + 鲁棒聚合
    └── 加权平均 → aggregated_update
    │
    ▼
Server.update_global_model()  ← 直接加到 global_model
    │
    ▼
Server.evaluate(test_loader)
```

### 数据流 B：CKKS 标准加密路径 (Scheme ②)

```
Server: encrypted_global_state (CKKS密文)
    │
    ▼ [Select 30 clients]
Client.local_train(encrypted_global_params)
    ├── decrypt global model  ← CKKS decrypt
    ├── train N epochs
    └── return model_update (明文Tensor字典)
    │
    ▼ [Encrypt on client]
Client.encrypt_update() → CKKSManager.encrypt_model_update()
    ├── flatten all params → batches (batch_size = slot_count)
    ├── sparsification? (TopK/RandK) → mask
    ├── packing? (Merged/TwoTier/CRTStack/LayerwiseQuantized)
    └── encrypt each batch → List[CKKSVector]
    │
    ▼ [Upload __sparse__ dict]
Server.aggregate_encrypted_updates()
    ├── per-batch homomorphic weighted_average()
    └── return aggregated_encrypted (__sparse__)
    │
    ▼
Server.update_global_model()
    ├── _update_encrypted_global_state()
    │   ├── 有量化metadata? → decrypt→明文加→re-encrypt (fallback)
    │   └── 无量化? → 同态加法逐batch累加
    └── _sync_model_from_encrypted_state() → 解密用于eval
    │
    ▼
Server.evaluate(test_loader)
```

### 数据流 C：TEE 可信执行路径 (Scheme ①)

```
Clients upload encrypted_updates
    │
    ▼
[Host] host_homomorphic_aggregate()  ← 可选预聚合
    │   (将n个客户端密文压缩为每batch 1个)
    ▼
[Host] TEEProxy.process_round() → ECALL
    │
    ▼
[Enclave] EnclaveMemory.decrypt_and_update()
    ├── decrypt with sk (Host不可见)
    ├── plaintext aggregation & averaging
    ├── update internal model_state
    └── re-encrypt with pk
    │
    ▼
Returns: (ct_global_bytes, prefetch_map)
    │
    ▼
[Host] Server stores ct_global, distributes prefetch
```

**关键设计**：私钥(sk)只在 Enclave 内存中，Host 服务器只有公钥(pk)。

### 数据流 D：FedFetch 预取路径 (Scheme ③)

```
Unselected Client (Round r):
    │
    ▼ [Background]
Server.broadcast_prefetch_to_unselected()
    ├── 计算该客户端缺失的所有delta
    ├── merge_sparse_encrypted_updates() → 累积为单个密文
    └── Client.receive_prefetch_delta()
        └── 本地同态累加到 prefetched_state

Selected Client (Round r+3):
    │
    ▼ [Fetch Phase]
Client.fetch_remaining_deltas()
    └── 下载还没预取到的剩余delta
    │
    ▼ [Apply Phase - 仅一次解密]
Client.apply_prefetched_state()
    ├── 解密 prefetched_state → plaintext_delta
    ├── base_model + delta → latest global model
    ├── Local Completion (FedPHE):
    │   └── global_delta≈0的位置用上轮本地值填充
    └── 清缓存
    │
    ▼ [Compute Phase]
Client.local_train()  ← 从最新全局模型开始训练
    │
    ▼ [Upload]
encrypt_update() → upload
```

**核心 invariant**：无论预取了多少轮，客户端只执行 **一次解密**。

---

## 三、模块详解

### 3.1 实验入口 (main.py, ~2096行)

| 类/方法 | 职责 |
|---------|------|
| `MetricsCollector` | 收集 30+ 种指标：时间、通信、精度、密文数量、预取统计、TEE统计 |
| `CKKSFedExperiment.__init__()` | 加载YAML配置、设随机种子、创建设备、初始化所有组件 |
| `_init_components()` | 数据加载 → 全局模型 → CKKSManager → Server → Clients → 选择策略 |
| `run_round_plain()` | 明文轮：选客户端 → 本地训练 → 明文聚合 → 评估 |
| `run_round_encrypted()` | 加密轮：选客户端 → 解密训练 → 加密上传 → 同态聚合 → 评估 |
| `run_experiment()` | 循环 num_rounds 轮，自动保存结果和Markdown报告 |

**配置驱动**：所有组件通过 `config.yaml` 统一配置，无需改代码即可切换策略。

### 3.2 客户端层 (client.py, ~899行)

```
FederatedClient (标准加密客户端)
├── local_train()
│   ├── 支持 encrypted_global_params 解密
│   ├── 梯度裁剪 (torch.nn.utils.clip_grad_norm_)
│   ├── 学习率调度器 (Step/Cosine/Exponential)
│   └── 更新裁剪 (layerwise_mean / global_norm)
├── encrypt_update() → 调用 CKKSManager
└── get_model_params() / set_model_params() (含BN running stats)

PrefetchFederatedClient (预取客户端)
├── receive_prefetch_delta()      ← 未选中时接收密文delta
├── fetch_remaining_deltas()      ← 选中时下载剩余delta
├── apply_prefetched_state()      ← 单次解密 + 本地补全
└── local_train() (重写: Fetch→Apply→Compute→Upload)

MaliciousClient / MaliciousSimpleClient
└── local_train() → super() → model_attack.attack(update)
```

### 3.3 服务端层 (server.py, ~1165行)

| 方法 | 职责 |
|------|------|
| `init_encrypted_global_state()` | 将初始明文模型加密为 `encrypted_global_state` |
| `aggregate_plain_updates()` | 明文聚合入口：防御过滤 → 鲁棒聚合 → 通信统计 |
| `aggregate_encrypted_updates()` | 密文聚合入口：委托 CKKSManager 同态加权平均 |
| `_apply_defense()` | 两阶段防御：(1) 异常检测过滤 (2) 鲁棒聚合规则 |
| `_update_encrypted_global_state()` | 密文状态更新：同态加法或 decrypt→add→re-encrypt fallback |
| `process_encrypted_round_via_tee()` | TEE路径：Host预聚合 → TEE解密/聚合/重加密 |
| `run_global_mask_vote()` | 全局掩码投票：客户端TopK掩码 → 服务端union/threshold/topk |

**PrefetchAggregationServer 扩展**：
- `encrypt_and_stage_prefetch()` — 加密delta并存入历史
- `broadcast_prefetch_to_unselected()` — 带宽感知的预取广播
- `calculate_round_duration()` — EMA 轮次时长估计

### 3.4 加密与打包层

#### crypto.py (~894行) — CKKSManager

```
CKKSContext      ← TenSEAL CKKS上下文 (poly_modulus_degree, scale, mod链)
CKKSEncryptor    ← 明文编码 + 加密
CKKSDecryptor    ← 解密 + Tensor重建
CKKSEvaluator    ← 同态运算 (+, -, ×scalar, weighted_average)
CKKSManager      ← 整合以上 + PackingStrategy + SparsificationStrategy + PTopkModule
```

**核心方法**：
- `encrypt_model_update()` → `__sparse__` 格式密文字典
- `decrypt_model_update()` → 从 `__sparse__` 恢复 Tensor 字典
- `aggregate_encrypted_updates()` → 同态加权聚合
- `merge_sparse_encrypted_updates()` → 两个稀疏更新同态相加

**__sparse__ 格式**：
```python
{
    '__sparse__': True,
    'ciphertexts': [CKKSVector, ...],   # 仅包含被选中的batch
    'mask': [1, 0, 1, 1, 0, ...],       # 哪些batch存在
    'batch_size': 4096,
    'total_elements': 62006,
    'shapes': {'conv1.weight': [6,3,5,5], ...},
    'offsets': {'conv1.weight': (0, 450), ...},
    'packing_metadata': {...},           # 可选：量化/打包元数据
}
```

#### packing.py (~699行) — 6种打包策略

| 策略 | 核心思想 | 量化 | Scale粒度 |
|------|---------|------|----------|
| `LayerwisePacking` | 默认占位，crypto.py退回到逐层处理 | 无 | N/A |
| `MergedPacking` | 所有层拼成一根长条，按slot分块 | 无 | N/A |
| `ConjugatePacking` | 实部/虚部分存两个值，slot翻倍 | 无 | N/A |
| `TwoTierPacking` | per-block min-max量化到16-bit | 16-bit | per-block |
| `CRTStackPacking` | per-layer 8-bit量化 + CRT压缩 | 8-bit | per-layer |
| `LayerwiseQuantizedPacking` | per-layer 16-bit量化后合并 | 16-bit | per-layer |

**关键设计**：`create_zero_chunk()` 必须被量化策略覆盖，确保 mask=0 的位置解密后是浮点 0，而不是编码空间中的 0。

#### sparsification.py (~189行)

- `TopKSparsification` — 按重要性分数选 top k% batch
- `RandKSparsification` — 随机选 k% batch
- `NoSparsification` — 全选

**与PTopk集成**：如果启用 client_residual，自动包装为 `PTopkWrappedStrategy`。

#### ptopk.py (~237行) — Persistent TopK

- **Client**: `apply_residual()` → 补偿历史残差 → `select_batches()` → `update_residual()` → 保存未上传部分
- **Server**: `server_update_plain()` → 支持 delayed / momentum 累积器模式

### 3.5 防御层

#### defenses/aggregation_rules.py (~210行)

| 规则 | 算法 | 抗拜占庭能力 |
|------|------|------------|
| `fedavg` | 加权平均 | 弱 |
| `median` | 坐标中位数 | 中 |
| `trimmed_mean` | 截断均值 | 中 |
| `krum` | 几何近邻选最优 | 强 |
| `multi_krum` | Krum选多个再平均 | 强 |
| `geometric_median` | Weiszfeld迭代 | 强 |

#### defenses/anomaly_detection.py (~202行)

- `norm_clip_updates` — L2范数超过中位数×倍数的丢弃
- `cosine_similarity_filter` — 与中位数更新余弦相似度过低的丢弃
- `median_absolute_deviation_filter` — MAD异常检测
- `multi_criteria_filter` — 组合上述方法

**统一fallback**：如果全部更新被过滤，保留"最正常"的一个。

### 3.6 客户端选择层 (client_selection.py, ~1269行)

| 策略 | 核心机制 | 适用场景 |
|------|---------|---------|
| `random` | 纯随机 | 基线 |
| `sticky` | 粘性分组，减少切换开销 | 联邦学习经典 |
| `sketch_clustering` | MinHash签名 + KMeans聚类 | 异构模型/数据 |
| `poc` (Power-of-Choice) | 随机采样d个，选loss最低的 | 快速收敛 |
| `tifl` | 按带宽分层，轮询选择 | 异构系统 |
| `haccs` | KMeans聚类 + 比例配额 | 公平性 |
| `oort` | ε-贪心探索-利用 | 高效参与 |

**PrefetchPoolManager**：策略无关的预采样池，支持 `overcommitment` 超量预取。

### 3.7 攻击层

#### attacks/model_attacks.py (~179行)

| 攻击 | 效果 |
|------|------|
| `sign_flipping` | 以概率翻转更新符号 |
| `scaling` | 放大更新幅度 (如10×) |
| `gaussian_noise` | 注入高斯噪声 |
| `mimic_alie` | ALIE攻击：按标准差偏移，规避统计检测 |
| `backdoor_model` | 放大后门训练后的更新 |
| `constant` | 替换为常数 (默认全零) |

#### attacks/data_attacks.py (~201行)

- `LabelFlippingAttack` — 标签翻转 (random/targeted/all_to_one)
- `BackdoorDataAttack` — 空间触发器后门 (5种位置)

### 3.8 辅助模块

| 模块 | 职责 |
|------|------|
| `blinding_mask.py` (~400行) | 成对盲化掩码：KGC生成对称种子，客户端加掩码，TEE精确补偿，加权求和归零 |
| `bandwidth_simulator.py` (~197行) | 异构带宽模拟：Uniform/Lognormal/FedFetch真实 trace |
| `prefetch_scheduler.py` (~333行) | T_percentile调度：决定客户端何时开始预取，确保fetch_time ≤ EMA_duration的某百分位 |
| `log_utils.py` (~387行) | 统一日志格式：emoji标签、表格、banner、对齐输出 |
| `plotting.py` (~620行) | 实验结果可视化：精度曲线、通信柱状图、时间分解、summary table |

### 3.9 TEE 与 ESAFL 层

| 模块 | 职责 |
|------|------|
| `tee_enclave.py` (~282行) | EnclaveMemory模拟：sealed sk、解密-聚合-更新-重加密、访问审计日志 |
| `server_tee.py` (~283行) | TEEAggregationServer：ECALL/OCALL代理、公钥-only CKKSManager |
| `tee_simulator.py` (~817行) | 更完整的TEE模拟器（含压缩、残差、延迟模式） |
| `esafl_crypto.py` (~239行) | ESAFL协议适配器：SIMULATION模式（单密钥）、NATIVE模式（预留） |
| `split_key_crypto.py` (~656行) | 分片密钥：KGC生成 shares，多方 partial_decrypt 后组合 |
| `threshold_crypto.py` (~329行) | 门限加密：(t,n) 门限方案 |
| `edge_node.py` (~120行) | EdgeNode：HTTP服务提供 partial_decrypt，EdgeNodeClient远程调用 |
| `host_aggregator.py` (~129行) | Host侧同态预聚合：n个客户端 → 每batch 1个密文 |

---

## 四、配置驱动的设计哲学

整个项目采用 **YAML 配置驱动**，所有可插拔模块通过工厂函数创建：

```yaml
system:
  num_clients: 100
  num_rounds: 30
  num_epochs: 3
  learning_rate: 0.001
  client_sampling_rate: 0.3
  upload_difference: true
  gradient_clipping: {enabled: false, max_norm: 1.0}
  update_clipping: {enabled: false, method: layerwise_mean, clip_factor: 3.0}

data:
  dataset: cifar10        # mnist / fashion_mnist / cifar10 / cifar100 / svhn / emnist / femnist
  num_classes: 10
  iid: false
  alpha: 0.5

model:
  name: cnn_cifar         # lenet / cnn / cnn_cifar / cnn_fmnist / deepcnn / vggnobn / resnet18 / resnet20 / mobilenetv2

ckks:
  poly_modulus_degree: 8192
  coeff_mod_bit_sizes: [60, 40, 40, 60]
  global_scale: 1099511627776
  slot_packing: true
  packing:
    strategy: merged      # merged / layerwise / twotier / crtstack / layerwise_quantized / conjugate
    quant_bits: 16
  sparsification:
    strategy: none        # none / topk / randk
    sparsity_rate: 0.1
    batch_size: 4096

defense:
  aggregation_rule: fedavg    # fedavg / median / trimmed_mean / krum / multi_krum / geometric_median
  anomaly_detection: none    # none / norm_clip / cosine_similarity / mad / multi_criteria

client_selection:
  strategy: random           # random / sticky / sketch_clustering / poc / tifl / haccs / oort

prefetch:
  enable_prefetch: false
  max_prefetch_round: 3
  overcommitment: 1.3

tee:
  enabled: false

esafl:
  enabled: false

blinding_mask:
  enabled: false

global_mask_vote:
  mode: none                 # none / union / threshold / topk
```

---

## 五、关键设计决策总结

| 决策 | 说明 | 影响 |
|------|------|------|
| **统一密钥模型** | 所有客户端共享同一CKKS上下文（非多密钥） | 简化实现，但安全性弱于MASER等多密钥方案 |
| **Server持有sk** | 服务器可解密全局模型用于评估 | 信任模型：server是honest-but-curious，不泄露单个客户端更新 |
| **__sparse__格式** | 所有密文更新统一字典结构 | 聚合逻辑高度统一，支持稀疏+密集混合 |
| **量化fallback** | 有量化metadata时，同态聚合退化为decrypt→avg→re-encrypt | 保证精度，但失去同态聚合的隐私保护（server看到聚合后的明文） |
| **Batch-level稀疏** | 稀疏化在batch粒度（非元素粒度） | 保持CKKS SIMD对齐，简化密文管理 |
| **Local Completion** | 全局sparse delta为0的位置用本地值补全 | 解决TopK导致的信息丢失和BN失配 |
| **Upload Difference** | 上传 `new-old` 而非完整权重 | 减少数值范围，有利于量化精度 |
| **ESAFL SIMULATION模式** | 多密钥协议用单密钥模拟 | 可验证协议逻辑，等待TenSEAL支持真多密钥 |
