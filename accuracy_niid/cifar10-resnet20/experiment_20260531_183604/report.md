# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260531_183604  
**Output Directory / 输出目录:** `accuracy_niid\cifar10-resnet20\experiment_20260531_183604`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | cifar10 | 训练数据集名称 |
| Model / 模型 | resnet20 | 神经网络架构 |
| Num Clients / 客户端数 | 50 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 50 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练epoch数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD优化器学习率 |
| Client Sampling Rate / 采样率 | 0.5 | 每轮参与训练的客户端比例 |
| IID / 独立同分布 | False | 数据分布是否IID |
| Device / 设备 | cuda | 训练设备(CPU/CUDA) |
| Upload Difference / 上传差值 | True | 是否上传模型差值而非完整权重 |

### 1.1 CKKS Parameters / CKKS加密参数

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Poly Modulus Degree / 多项式模数度 | 8192 | CKKS多项式环的维度 |
| Coeff Mod Bit Sizes / 系数模数位宽 | [60, 40, 40, 60] | 系数模数的位宽序列 |
| Global Scale / 全局缩放因子 | 1099511627776 | CKKS编码缩放因子 |
| Slot Packing / 槽打包 | True | 是否启用SIMD槽打包 |

### 1.2 Prefetch Configuration / 预取配置

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Enable Prefetch / 启用预取 | True | 是否启用CipherFetch预取 |
| Max Prefetch Round / 最大预取轮数 | 3 | 预取窗口大小R |
| Warmup Round / 预热轮数 | 1 | 预取预热轮数 |
| Overcommitment / 过承诺比例 | 1.3 | 预采样倍数OC |
| Strategy / 策略 | sticky | 客户端选择策略 |
| Sticky Group Size / 粘性组大小 | None | FedFetch中的k |
| Sticky Change Base / 替换基数 | 3 | change_num = base × OC |
| Scheduler Beta / 调度器松弛系数 | 1.0 | T_percentile松弛系数 |

## 2. Key Metrics Summary / 关键指标汇总

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final Test Accuracy / 最终测试准确率 | **63.78%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 1.0021 | 全局模型在测试集上的交叉熵损失 |
| Total Simulated Time / 总模拟时间 | 387.70 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Real CPU Time / 总真实CPU时间 | 1501.74 s | 单机串行执行的实际耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 16.86 s | 模拟 wall-clock 平均每轮耗时 |
| Avg Real Round Time / 平均真实轮次时间 | 65.29 s | 真实 CPU 平均每轮耗时 |
| Total Communication / 总通信量 | 12470.06 MB | 训练通信 TV = upload + FV（选中客户端实际 fetch 下载量） |
| Total Upload / 总上传量 | 12018.90 MB / 0.00 s | 所有选中客户端密文上传累计 |
| Total Download (Fetch) / 实际补下载 | 451.16 MB | 选中客户端实际 fetch 的密文增量 |
| Total Download (Prefetch) / 后台预取 | 12148.11 MB | 未选中客户端后台预取的密文增量 |
| Total Actual Download / 总实际下载 | 12599.27 MB | Fetch + Prefetch 物理下载总量 |
| Effective Download / 理论下载责任 | 451.16 MB | delta_size × 选中客户端数（用于 TV 计算） |
| Avg Upload Cost / 平均上传开销 | 522.56 MB | mean(upload_cost)/2^20 |
| Avg Effective Download / 平均理论下载 | 19.62 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 19.99x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.361 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 33.65 MB | CKKS公钥/Galois密钥分发总字节数 |
| Avg Prefetch Accum Time / 平均预取累加时间 | 0.000 s/client | 客户端同态累加密文增量的平均耗时 |
| Avg Fetch Time / 平均Fetch时间 | 0.131 s/client | 客户端下载剩余密文增量的平均耗时 |
| Avg Apply Time / 平均应用时间 | 0.111 s/client | 客户端解密并应用预取状态的平均耗时 |
| Total Prefetch Download / 预取下载总量 | 15434.84 MB | 所有客户端接收的密文增量之和 |
| Total Fetch Download / Fetch下载总量 | 451.16 MB | 所有客户端下载的剩余密文增量之和 |
| Total Prefetch Broadcast / 预取广播总量 | 15434.84 MB | 服务器向未选中客户端广播的密文增量之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 | Prefetch ↓ / 预取下载 | Fetch ↓ / 补下载 | Total ↓ / 总下载 | Score / 粘性分 |
|-----|----------------|--------------|------------------|------------------|----------------------|------------------|------------------|---------------|
| 0 | 15 | 980 | 31013 kbps | 30222 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 3.94 |
| 1 | 16 | 1039 | 339099 kbps | 472285 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.80 |
| 2 | 12 | 794 | 254789 kbps | 181815 kbps | 266.21 MB | 15.04 MB | 281.25 MB | 5.03 |
| 3 | 17 | 1115 | 96962 kbps | 99657 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 3.08 |
| 4 | 16 | 1038 | 39759 kbps | 18071 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 2.76 |
| 5 | 17 | 1117 | 27438 kbps | 26345 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 3.59 |
| 6 | 10 | 656 | 105349 kbps | 21922 kbps | 308.40 MB | 15.04 MB | 323.44 MB | 2.54 |
| 7 | 15 | 979 | 269298 kbps | 67032 kbps | 293.59 MB | 15.04 MB | 308.63 MB | 3.24 |
| 8 | 5 | 331 | 28807 kbps | 12061 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.44 |
| 9 | 3 | 201 | 54690 kbps | 5467 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 4.10 |
| 10 | 15 | 984 | 41651 kbps | 44816 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 4.33 |
| 11 | 1 | 67 | 8057 kbps | 8610 kbps | 261.72 MB | 0.00 MB | 261.72 MB | 2.38 |
| 12 | 15 | 981 | 279465 kbps | 261900 kbps | 309.53 MB | 0.00 MB | 309.53 MB | 2.42 |
| 13 | 17 | 1106 | 227204 kbps | 21076 kbps | 323.45 MB | 0.00 MB | 323.45 MB | 2.47 |
| 14 | 15 | 977 | 93105 kbps | 23265 kbps | 323.45 MB | 0.00 MB | 323.45 MB | 1.68 |
| 15 | 16 | 1049 | 29282 kbps | 27951 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 3.87 |
| 16 | 17 | 1117 | 123339 kbps | 36087 kbps | 308.63 MB | 15.04 MB | 323.67 MB | 3.00 |
| 17 | 8 | 529 | 17150 kbps | 14397 kbps | 281.24 MB | 15.04 MB | 296.28 MB | 2.16 |
| 18 | 1 | 67 | 93249 kbps | 6653 kbps | 308.40 MB | 0.00 MB | 308.40 MB | 2.84 |
| 19 | 14 | 922 | 144829 kbps | 67399 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 5.25 |
| 20 | 1 | 67 | 103970 kbps | 9934 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 3.69 |
| 21 | 5 | 323 | 110526 kbps | 11922 kbps | 293.59 MB | 0.00 MB | 293.59 MB | 2.89 |
| 22 | 12 | 778 | 650580 kbps | 37402 kbps | 293.37 MB | 0.00 MB | 293.37 MB | 5.62 |
| 23 | 14 | 918 | 231919 kbps | 22700 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 4.76 |
| 24 | 15 | 921 | 329695 kbps | 19824 kbps | 293.59 MB | 15.04 MB | 308.63 MB | 3.04 |
| 25 | 15 | 975 | 574578 kbps | 336917 kbps | 279.23 MB | 15.04 MB | 294.27 MB | 2.35 |
| 26 | 17 | 1111 | 221339 kbps | 145221 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.53 |
| 27 | 2 | 134 | 46710 kbps | 7069 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 3.55 |
| 28 | 2 | 134 | 11993 kbps | 10052 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 1.53 |
| 29 | 14 | 917 | 63094 kbps | 25450 kbps | 264.86 MB | 15.04 MB | 279.90 MB | 2.46 |
| 30 | 13 | 850 | 337046 kbps | 27064 kbps | 234.78 MB | 15.04 MB | 249.82 MB | 2.61 |
| 31 | 1 | 67 | 70923 kbps | 10978 kbps | 294.26 MB | 0.00 MB | 294.26 MB | 4.05 |
| 32 | 6 | 399 | 25433 kbps | 11948 kbps | 323.45 MB | 0.00 MB | 323.45 MB | 1.88 |
| 33 | 14 | 912 | 77720 kbps | 63169 kbps | 323.45 MB | 0.00 MB | 323.45 MB | 5.47 |
| 34 | 15 | 978 | 27070 kbps | 39392 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 5.23 |
| 35 | 18 | 1172 | 21428 kbps | 18340 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.58 |
| 36 | 14 | 916 | 344229 kbps | 18358 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 4.65 |
| 37 | 16 | 1052 | 23038 kbps | 16389 kbps | 308.40 MB | 15.04 MB | 323.44 MB | 0.87 |
| 38 | 15 | 980 | 92157 kbps | 63300 kbps | 308.41 MB | 15.04 MB | 323.45 MB | 3.50 |
| 39 | 15 | 912 | 64407 kbps | 17650 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 4.14 |
| 40 | 3 | 201 | 10447 kbps | 8379 kbps | 280.34 MB | 15.04 MB | 295.38 MB | 2.38 |
| 41 | 14 | 916 | 310817 kbps | 335451 kbps | 308.41 MB | 15.04 MB | 323.44 MB | 3.71 |
| 42 | 14 | 915 | 406173 kbps | 70384 kbps | 294.26 MB | 0.00 MB | 294.26 MB | 4.94 |
| 43 | 18 | 1179 | 18551 kbps | 31260 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.40 |
| 44 | 18 | 1175 | 115313 kbps | 84637 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.97 |
| 45 | 15 | 975 | 157061 kbps | 17346 kbps | 323.44 MB | 0.00 MB | 323.44 MB | 2.30 |
| 46 | 16 | 1047 | 53345 kbps | 92982 kbps | 293.59 MB | 15.04 MB | 308.63 MB | 2.64 |
| 47 | 17 | 1110 | 31064 kbps | 34562 kbps | 323.44 MB | 15.04 MB | 338.48 MB | 2.82 |
| 48 | 14 | 909 | 523223 kbps | 102692 kbps | 308.41 MB | 0.00 MB | 308.41 MB | 3.32 |
| 49 | 2 | 134 | 21748 kbps | 9455 kbps | 308.63 MB | 15.04 MB | 323.67 MB | 1.27 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 12.18% | 2.2823 | 36.08s | 534.01 MB | 0.372s | 20.43x |
| 2 | 24.88% | 1.9618 | 35.88s | 909.95 MB | 0.378s | 20.43x |
| 3 | 29.92% | 1.8004 | 27.90s | 594.16 MB | 0.383s | 20.43x |
| 4 | 41.50% | 1.6231 | 35.92s | 549.04 MB | 0.397s | 20.43x |
| 5 | 38.40% | 1.6225 | 16.56s | 526.02 MB | 0.384s | 20.13x |
| 6 | 38.32% | 1.6330 | 15.18s | 510.09 MB | 0.391s | 19.52x |
| 7 | 43.34% | 1.5234 | 15.63s | 526.03 MB | 0.383s | 20.13x |
| 8 | 47.04% | 1.4125 | 12.32s | 533.99 MB | 0.383s | 20.43x |
| 9 | 48.67% | 1.3882 | 12.26s | 534.01 MB | 0.387s | 20.43x |
| 10 | 53.17% | 1.3185 | 15.56s | 533.99 MB | 0.390s | 20.43x |
| 11 | 51.42% | 1.3319 | 16.27s | 518.05 MB | 0.392s | 19.82x |
| 12 | 54.44% | 1.2519 | 10.83s | 526.03 MB | 0.393s | 20.13x |
| 13 | 55.57% | 1.2213 | 15.01s | 526.02 MB | 0.385s | 20.13x |
| 14 | 57.85% | 1.1856 | 12.21s | 533.99 MB | 0.401s | 20.43x |
| 15 | 58.81% | 1.1429 | 12.18s | 526.02 MB | 0.381s | 20.13x |
| 16 | 58.90% | 1.1460 | 11.71s | 510.09 MB | 0.386s | 19.52x |
| 17 | 59.39% | 1.1200 | 14.25s | 486.18 MB | 0.384s | 18.60x |
| 18 | 56.15% | 1.1854 | 11.16s | 510.08 MB | 0.391s | 19.52x |
| 19 | 58.48% | 1.1342 | 12.12s | 533.99 MB | 0.393s | 20.43x |
| 20 | 58.22% | 1.1389 | 11.67s | 510.08 MB | 0.387s | 19.52x |
| 21 | 62.48% | 1.0471 | 11.99s | 526.01 MB | 0.385s | 20.13x |
| 22 | 63.19% | 1.0206 | 13.26s | 518.06 MB | 0.388s | 19.82x |
| 23 | 63.78% | 1.0021 | 11.77s | 494.15 MB | 0.395s | 18.91x |

## 5. Communication & Ciphertext Details / 通信与密文计算详情

### 5.1 Formula Definitions / 公式定义

| # | Metric / 指标 | Formula / 公式 |
|---|---------------|----------------|
| 1 | Plaintext Size / 明文大小 | `sum(v.numel() * 4 for v in model_update.values())` |
| 2 | Ciphertext Size / 密文大小 | `sum(len(ct.serialize()) for ct in encrypted_update.values())` |
| 3 | Ciphertext Blocks / 密文块数 | `sum(len(v) for v in encrypted_update.values())` |
| 4 | Upload Cost / 上传开销 | `sum(ciphertext_size of selected clients)` |
| 5 | Fetch Volume (FV) / 补下载量 | `sum(fetch_download_cost)` |
| 6 | Effective Download / 理论下载责任 | `delta_size * num_selected_clients per round` |
| 7 | Total Communication (TV) / 训练通信 | `upload_cost + fetch_download_cost` |
| 7 | Expansion Ratio / 膨胀率 | `total_ciphertext_size / total_plaintext_size` |

### 5.2 Substituted Values / 数值代入

| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |
|---|---------------|-------------------|---------------|
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 655508464` | 625.14 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 13079418944` | 12473.51 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 39126` | 39126 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 12602728166` | 12018.90 MB |
| 5 | Total Download / 总下载 | `sum(fetch_download_cost) = 473076510` | 451.16 MB |
| 6 | Total Communication / 总通信 | `12602728166 + 473076510 = 13075804676` | 12470.06 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 19.9949` | 19.99x |

### 5.3 Prefetch Communication Analysis / 预取通信分析

- **Total Upload / 总上传开销:** 12018.90 MB — 所有选中客户端密文上传的累计量
- **Fetch Volume (FV) / 补下载量:** 451.16 MB — 选中客户端实际 fetch 下载量（已扣除预取覆盖部分）
- **Training Communication (TV) / 训练通信:** 12470.06 MB = Upload(12018.90 MB) + FV(451.16 MB)
  ✅ 验证通过: Upload(12018.90 MB) + FV(451.16 MB) = TV(12470.06 MB)
  — TV 对齐 FedFetch 论文定义：TV = Upload + FV（不含后台预取）
- **Prefetch Broadcast / 预取广播:** 15434.84 MB — 服务器向未选中客户端后台广播的密文增量
- **Prefetch Download / 预取下载:** 15434.84 MB — 未选中客户端后台接收的密文增量
- **Prefetch + Fetch + Broadcast / 后台总流量:** 31320.83 MB = Prefetch DL(15434.84) + Fetch DL(451.16) + Broadcast(15434.84)
- **Effective Download / 理论下载责任:** 627.23 MB — 每轮 delta_size × 选中客户端数（预取节省率计算基准）
- **Prefetch Savings / 预取节省:** 176.07 MB — Effective Download 与实际 FV 的差值
- **Baseline (no prefetch) / 无预取基线:** 627.23 MB — 完整模型下载(1.05 MB × 600 次)

> **Note / 说明:**
> 1. **FV** = 选中客户端实际 fetch 下载量。TV = Upload + FV（FedFetch 论文定义）。
> 2. **Effective Download** = delta_size × 选中客户端数，是理论下载责任，仅用于计算预取节省率。
> 3. **Prefetch** = 后台/空闲时流量，不计入 TV，但计入物理总下行带宽。
> 4. 预取的核心优势是**将训练前的同步下载变为后台增量推送**，降低 wall-clock 延迟。

### 5.4 FedFetch Key Metrics (TT / FT / TV / FV) / FedFetch 核心指标

以下指标对齐 FedFetch 论文定义，用于量化预取机制的时序与通信优势：

| Metric / 指标 | Symbol / 符号 | Formula / 公式 | Substitution / 代入 | Value / 数值 | Description / 说明 |
|---------------|---------------|----------------|---------------------|--------------|-------------------|
| Training Time / 训练时间 | **TT** | `mean(total_round_time)` | `387.70/23` | 16.86 s/轮 | 每轮 wall-clock 延迟（最慢客户端完成时间） |
| Fetch Time / 补下载时间 | **FT** | `mean(fetch_time)` | `78.39/600` | 0.13 s/轮 | 选中客户端下载剩余密文增量的时间 |
| Training Volume / 训练通信 | **TV** | `mean(total_communication_cost)/2^20` | `13075804676.00/23/1048576` | 542.18 MB/轮 | 每轮训练产生的总通信量（不含后台预取） |
| Fetch Volume / 补下载量 | **FV** | `mean(download_cost)/2^20` | `473076510.00/23/1048576` | 19.62 MB/轮 | 选中客户端补充下载的密文增量 |
| Prefetch Volume / 预取量 | **PV** | `mean(prefetch_broadcast_cost)/2^20` | `16184598569.00/23/1048576` | 671.08 MB/轮 | 服务器后台广播的密文增量（不计入 TV） |

> **Parallelism / 并行性说明:** 当前实现中，预取广播在每轮训练完成后、下一轮开始前进行，
> 属于**串行调度**。预取通信量不计入 TV（训练通信），因此总通信对比是公平的；
> 预取节省的是选中客户端训练前的 fetch 等待时间，这是 FedFetch 降低 wall-clock 延迟的核心机制。

### 5.5 EMA Round Duration Analysis / EMA 轮次持续时间分析

以下指标记录每轮结束后指数移动平均（EMA）估计的轮次持续时间，用于预取调度的带宽预算计算。

**EMA平滑系数 alpha = 0.125**

| Round / 轮次 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|--------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| EMA Pred(s)  | N/A | 36.08 | 36.05 | 35.03 | 35.14 | 32.82 | 30.62 | 28.74 | 26.69 | 24.89 | 23.72 | 22.79 | 21.29 | 20.51 | 19.47 | 18.56 | 17.70 | 17.27 | 16.51 | 15.96 | 15.42 | 14.99 | 14.78 |
| Real Time(s)| 36.08 | 35.88 | 27.90 | 35.92 | 16.56 | 15.18 | 15.63 | 12.32 | 12.26 | 15.56 | 16.27 | 10.83 | 15.01 | 12.21 | 12.18 | 11.71 | 14.25 | 11.16 | 12.12 | 11.67 | 11.99 | 13.26 | 11.77 |

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final EMA Duration / 最终 EMA 持续时间 | 14.40 s | 实验结束时 EMA 估计的单轮持续时间 |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **23** 轮训练，最终测试准确率达到 **63.78%**，测试损失为 **1.0021**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **19.99x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.361s**。
- **Prefetch / 预取优化:** 启用 **CipherFetch (FedFetch-style)** 密文预取机制。
- **Training Communication / 训练通信:** 总训练通信 **12769340.50 KB**（上传 12307351.72 KB + 下载 461988.78 KB）。
- **Download Saved / 节省下载:** 选中客户端避免完整模型下载，共节省 **180297.16 KB**.
