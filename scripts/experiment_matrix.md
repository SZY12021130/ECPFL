# CKKS-Fed / CipherFetch 实验参数矩阵

本文档定义了从基线到完整方案的 6 组递进实验，用于对比 TEE、包级稀疏化、残差补偿和密文预取各组件的贡献。

## 一、实验设计原则

### 变量控制
- **上行稀疏化**（客户端→服务器）由 `ckks.sparsification` 控制，独立于下行。
- **下行压缩**（服务器→客户端）仅存在于 TEE 路径，由 `tee.compression` 控制。
- **客户端残差**补偿的是上行稀疏化损失；TEE 全局残差补偿的是下行压缩损失。两者完全独立。
- **服务器累加器**仅在标准路径（非 TEE）生效；TEE 路径下自动失效。

### 不可出现的矛盾配置
```yaml
# ❌ 上行全量 + 客户端残差开启 → 残差永远不会被使用
ckks.sparsification.strategy: "none"
ptopk.client_residual.enabled: true

# ❌ TEE 路径 + 服务器累加器开启 → 累加器永远不会被调用
tee.enabled: true
ptopk.server_accumulator.enabled: true
```

---

## 二、实验矩阵（6 组递进对比）

### Group A — 标准加密基线（Standard Encrypted FedAvg）
无 TEE、无稀疏化、无预取、无补偿。作为精度上界和通信量上界。

```yaml
system:
  num_clients: 10
  num_rounds: 10        # Quick模式: 5
  num_epochs: 5         # Quick模式: 2
  batch_size: 64
  learning_rate: 0.01
  client_sampling_rate: 0.5
  upload_difference: true
  device: cpu

data:
  dataset: "mnist"
  iid: false
  alpha: 0.5

model:
  name: "lenet"

ckks:
  poly_modulus_degree: 8192
  coeff_mod_bit_sizes: [60, 40, 40, 60]
  global_scale: 1099511627776
  slot_packing: true
  packing:
    strategy: "merged"
  sparsification:
    strategy: "none"           # ← 无稀疏化
  ptopk:
    enable: true
    client_residual:
      enabled: false
    server_accumulator:
      enabled: false
      mode: "none"

tee:
  enabled: false               # ← TEE 关闭

prefetch:
  enable_prefetch: false       # ← 预取关闭
```

---

### Group B — 包级稀疏化基线（TopK Upload, No Compensation）
在 A 的基础上开启上行 TopK 稀疏化（50%），但关闭所有补偿器。用于观察纯稀疏化带来的精度损失。

```yaml
ckks:
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5         # ← 保留 50% batch
    batch_size: 4096
  ptopk:
    client_residual:
      enabled: false           # ← 无残差补偿
    server_accumulator:
      enabled: false

tee:
  enabled: false

prefetch:
  enable_prefetch: false
```

---

### Group C — TEE 全量聚合（TEE + Full Downlink）
在 B 的基础上引入 TEE，但关闭 TEE 下行压缩。TEE 只做明文聚合 + 全量加密回传，不维护全局残差。用于对比 TEE 本身（而非压缩）的影响。

```yaml
ckks:
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5
  ptopk:
    client_residual:
      enabled: false
    server_accumulator:
      enabled: false

tee:
  enabled: true
  compression:
    enabled: false             # ← TEE 全量回传
    sparsity_rate: 0.5

prefetch:
  enable_prefetch: false
```

---

### Group D — TEE 压缩下行（TEE + TopK Downlink）
在 C 的基础上开启 TEE 下行 TopK 压缩（50%）。此时上下行均有稀疏化，但无任何补偿。用于观察双边稀疏化叠加的精度损失。

```yaml
ckks:
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5
  ptopk:
    client_residual:
      enabled: false
    server_accumulator:
      enabled: false

tee:
  enabled: true
  compression:
    enabled: true              # ← TEE 压缩开启
    sparsity_rate: 0.5

prefetch:
  enable_prefetch: false
```

---

### Group E — TEE 压缩 + 客户端残差（Full TEE with Error Feedback）
在 D 的基础上开启 PTopk 客户端残差补偿。这是**不带预取的完整 TEE 方案**。

```yaml
ckks:
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5
  ptopk:
    client_residual:
      enabled: true            # ← 客户端残差开启
    server_accumulator:
      enabled: false

tee:
  enabled: true
  compression:
    enabled: true
    sparsity_rate: 0.5

prefetch:
  enable_prefetch: false
```

---

### Group F — CipherFetch 完整方案（TEE + Prefetch + Error Feedback）
在 E 的基础上开启密文预取（CipherFetch）。这是**本框架的完整形态**。

```yaml
ckks:
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5
  ptopk:
    client_residual:
      enabled: true
    server_accumulator:
      enabled: false

tee:
  enabled: true
  compression:
    enabled: true
    sparsity_rate: 0.5

prefetch:
  enable_prefetch: true        # ← 预取开启
  max_prefetch_round: 3
  overcommitment: 1.0
  scheduler_beta: 0.5
  sticky_decay: 0.9
  use_sticky_sampling: true
  warmup_round: 1
```

---

## 三、预期对比结论

| 对比组 | 说明 | 预期观察 |
|--------|------|----------|
| A vs B | 纯稀疏化效应 | B 的精度可能低于 A，通信量大幅下降 |
| B vs C | TEE 全量聚合效应 | 精度应相近（TEE 本身不改变算法），但服务器计算模式变化 |
| C vs D | 下行压缩效应 | D 的通信量更低，但若无补偿精度可能进一步下降 |
| D vs E | 客户端残差补偿效应 | E 的精度应显著回升，接近 C 甚至 A |
| E vs F | 密文预取效应 | F 的收敛速度（轮次到达相同精度）应更快，或等精度下有效时间更短 |

---

## 四、运行方式

### 快速验证（Quick Mode）
每组 5 轮 × 2 epochs，约 6-8 分钟/组，6 组约 40-50 分钟：

```bash
# Windows PowerShell
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python scripts/run_experiments.py --mode quick
```

### 完整实验（Full Mode）
每组 10 轮 × 5 epochs，约 15-25 分钟/组，6 组约 2-3 小时：

```bash
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python scripts/run_experiments.py --mode full
```

### 单组运行

```bash
$env:KMP_DUPLICATE_LIB_OK="TRUE"
python scripts/run_experiments.py --mode quick --groups A C E
```

---

## 五、输出结构

运行结束后，结果保存在：

```
results/
  experiment_20260506_153000_A_std_baseline/     # Group A
  experiment_20260506_153800_B_topk_upload/      # Group B
  ...
scripts/
  experiment_results.json                          # 汇总对比表
  experiment_report.md                             # 自动生成的对比报告
```

`experiment_results.json` 包含每组实验的：
- 最终测试准确率 / 损失
- 总通信量 / 平均每轮通信量
- 总虚拟时间 / 平均每轮时间
- 膨胀率、加密时间等 CKKS 指标
- 预取相关指标（仅 F 组）
