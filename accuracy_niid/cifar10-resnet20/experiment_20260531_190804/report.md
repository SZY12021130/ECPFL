# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260531_190804  
**Output Directory / 输出目录:** `accuracy_niid\cifar10-resnet20\experiment_20260531_190804`  

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
| Final Test Accuracy / 最终测试准确率 | **65.52%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.9692 | 全局模型在测试集上的交叉熵损失 |
| Total Simulated Time / 总模拟时间 | 371.60 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Real CPU Time / 总真实CPU时间 | 1478.21 s | 单机串行执行的实际耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 17.70 s | 模拟 wall-clock 平均每轮耗时 |
| Avg Real Round Time / 平均真实轮次时间 | 70.39 s | 真实 CPU 平均每轮耗时 |
| Total Communication / 总通信量 | 11611.69 MB | 训练通信 TV = upload + FV（选中客户端实际 fetch 下载量） |
| Total Upload / 总上传量 | 11166.14 MB / 0.00 s | 所有选中客户端密文上传累计 |
| Total Download (Fetch) / 实际补下载 | 445.54 MB | 选中客户端实际 fetch 的密文增量 |
| Total Download (Prefetch) / 后台预取 | 11390.35 MB | 未选中客户端后台预取的密文增量 |
| Total Actual Download / 总实际下载 | 11835.90 MB | Fetch + Prefetch 物理下载总量 |
| Effective Download / 理论下载责任 | 445.54 MB | delta_size × 选中客户端数（用于 TV 计算） |
| Avg Upload Cost / 平均上传开销 | 531.72 MB | mean(upload_cost)/2^20 |
| Avg Effective Download / 平均理论下载 | 21.22 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 20.35x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.388 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 33.62 MB | CKKS公钥/Galois密钥分发总字节数 |
| Avg Prefetch Accum Time / 平均预取累加时间 | 0.000 s/client | 客户端同态累加密文增量的平均耗时 |
| Avg Fetch Time / 平均Fetch时间 | 0.141 s/client | 客户端下载剩余密文增量的平均耗时 |
| Avg Apply Time / 平均应用时间 | 0.112 s/client | 客户端解密并应用预取状态的平均耗时 |
| Total Prefetch Download / 预取下载总量 | 14323.55 MB | 所有客户端接收的密文增量之和 |
| Total Fetch Download / Fetch下载总量 | 445.54 MB | 所有客户端下载的剩余密文增量之和 |
| Total Prefetch Broadcast / 预取广播总量 | 14323.55 MB | 服务器向未选中客户端广播的密文增量之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 | Prefetch ↓ / 预取下载 | Fetch ↓ / 补下载 | Total ↓ / 总下载 | Score / 粘性分 |
|-----|----------------|--------------|------------------|------------------|----------------------|------------------|------------------|---------------|
| 0 | 13 | 803 | 31013 kbps | 30222 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 4.65 |
| 1 | 15 | 935 | 339099 kbps | 472285 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 2.21 |
| 2 | 13 | 799 | 254789 kbps | 181815 kbps | 254.54 MB | 14.81 MB | 269.35 MB | 3.63 |
| 3 | 15 | 1001 | 96962 kbps | 99657 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 3.57 |
| 4 | 13 | 868 | 39759 kbps | 18071 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 3.78 |
| 5 | 16 | 1000 | 27438 kbps | 26345 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 3.26 |
| 6 | 12 | 734 | 105349 kbps | 21922 kbps | 284.61 MB | 15.04 MB | 299.65 MB | 4.72 |
| 7 | 13 | 801 | 269298 kbps | 67032 kbps | 269.57 MB | 14.81 MB | 284.39 MB | 4.00 |
| 8 | 5 | 335 | 28807 kbps | 12061 kbps | 284.61 MB | 14.81 MB | 299.43 MB | 3.53 |
| 9 | 3 | 200 | 54690 kbps | 5467 kbps | 299.65 MB | 14.81 MB | 314.46 MB | 2.70 |
| 10 | 14 | 866 | 41651 kbps | 44816 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 4.33 |
| 11 | 1 | 66 | 8057 kbps | 8610 kbps | 270.47 MB | 0.00 MB | 270.47 MB | 1.25 |
| 12 | 13 | 868 | 279465 kbps | 261900 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 3.80 |
| 13 | 15 | 933 | 227204 kbps | 21076 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.95 |
| 14 | 15 | 934 | 93105 kbps | 23265 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.62 |
| 15 | 14 | 933 | 29282 kbps | 27951 kbps | 299.65 MB | 14.81 MB | 314.46 MB | 3.68 |
| 16 | 13 | 866 | 123339 kbps | 36087 kbps | 269.57 MB | 14.81 MB | 284.39 MB | 4.00 |
| 17 | 9 | 602 | 17150 kbps | 14397 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 2.09 |
| 18 | 1 | 67 | 93249 kbps | 6653 kbps | 284.84 MB | 0.00 MB | 284.84 MB | 2.42 |
| 19 | 14 | 867 | 144829 kbps | 67399 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 4.61 |
| 20 | 1 | 67 | 103970 kbps | 9934 kbps | 299.65 MB | 14.81 MB | 314.46 MB | 1.82 |
| 21 | 6 | 402 | 110526 kbps | 11922 kbps | 269.80 MB | 0.00 MB | 269.80 MB | 1.05 |
| 22 | 11 | 733 | 650580 kbps | 37402 kbps | 269.80 MB | 0.00 MB | 269.80 MB | 4.14 |
| 23 | 14 | 867 | 231919 kbps | 22700 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 3.77 |
| 24 | 14 | 866 | 329695 kbps | 19824 kbps | 269.57 MB | 15.04 MB | 284.61 MB | 2.30 |
| 25 | 13 | 800 | 574578 kbps | 336917 kbps | 254.99 MB | 14.81 MB | 269.80 MB | 2.91 |
| 26 | 17 | 1068 | 221339 kbps | 145221 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 1.88 |
| 27 | 2 | 134 | 46710 kbps | 7069 kbps | 299.65 MB | 14.81 MB | 314.46 MB | 4.10 |
| 28 | 2 | 134 | 11993 kbps | 10052 kbps | 285.06 MB | 0.00 MB | 285.06 MB | 3.38 |
| 29 | 14 | 932 | 63094 kbps | 25450 kbps | 269.57 MB | 15.04 MB | 284.61 MB | 2.19 |
| 30 | 10 | 600 | 337046 kbps | 27064 kbps | 209.64 MB | 14.81 MB | 224.46 MB | 4.31 |
| 31 | 1 | 67 | 70923 kbps | 10978 kbps | 269.80 MB | 0.00 MB | 269.80 MB | 2.05 |
| 32 | 7 | 467 | 25433 kbps | 11948 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.43 |
| 33 | 14 | 868 | 77720 kbps | 63169 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 3.94 |
| 34 | 15 | 1000 | 27070 kbps | 39392 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.80 |
| 35 | 16 | 1069 | 21428 kbps | 18340 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 2.19 |
| 36 | 13 | 801 | 344229 kbps | 18358 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 4.51 |
| 37 | 12 | 733 | 23038 kbps | 16389 kbps | 284.84 MB | 14.81 MB | 299.65 MB | 2.54 |
| 38 | 11 | 667 | 92157 kbps | 63300 kbps | 269.58 MB | 14.81 MB | 284.39 MB | 6.23 |
| 39 | 15 | 934 | 64407 kbps | 17650 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.44 |
| 40 | 3 | 201 | 10447 kbps | 8379 kbps | 268.67 MB | 14.81 MB | 283.49 MB | 2.26 |
| 41 | 12 | 800 | 310817 kbps | 335451 kbps | 284.61 MB | 15.04 MB | 299.65 MB | 3.58 |
| 42 | 14 | 868 | 406173 kbps | 70384 kbps | 269.80 MB | 0.00 MB | 269.80 MB | 3.14 |
| 43 | 15 | 934 | 18551 kbps | 31260 kbps | 299.65 MB | 14.81 MB | 314.46 MB | 4.11 |
| 44 | 15 | 1002 | 115313 kbps | 84637 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 3.96 |
| 45 | 14 | 868 | 157061 kbps | 17346 kbps | 299.65 MB | 0.00 MB | 299.65 MB | 2.55 |
| 46 | 13 | 866 | 53345 kbps | 92982 kbps | 269.57 MB | 15.04 MB | 284.61 MB | 3.29 |
| 47 | 16 | 1000 | 31064 kbps | 34562 kbps | 299.65 MB | 14.81 MB | 314.47 MB | 2.47 |
| 48 | 11 | 665 | 523223 kbps | 102692 kbps | 284.61 MB | 0.00 MB | 284.61 MB | 5.20 |
| 49 | 2 | 134 | 21748 kbps | 9455 kbps | 284.84 MB | 14.81 MB | 299.65 MB | 2.10 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 20.18% | 2.0379 | 33.81s | 526.03 MB | 0.381s | 20.13x |
| 2 | 28.91% | 1.8241 | 34.35s | 904.36 MB | 0.392s | 20.43x |
| 3 | 37.62% | 1.6400 | 28.08s | 594.15 MB | 0.382s | 20.43x |
| 4 | 42.28% | 1.5324 | 34.32s | 549.05 MB | 0.387s | 20.43x |
| 5 | 44.18% | 1.4804 | 16.97s | 534.00 MB | 0.385s | 20.43x |
| 6 | 47.80% | 1.4114 | 16.58s | 533.99 MB | 0.396s | 20.43x |
| 7 | 50.16% | 1.3374 | 17.04s | 534.00 MB | 0.381s | 20.43x |
| 8 | 54.06% | 1.2811 | 12.17s | 533.99 MB | 0.385s | 20.43x |
| 9 | 55.36% | 1.2395 | 11.49s | 526.02 MB | 0.387s | 20.13x |
| 10 | 56.29% | 1.1954 | 16.54s | 534.00 MB | 0.417s | 20.43x |
| 11 | 58.22% | 1.1555 | 17.08s | 534.01 MB | 0.390s | 20.43x |
| 12 | 59.70% | 1.1228 | 11.71s | 534.00 MB | 0.390s | 20.43x |
| 13 | 60.25% | 1.1003 | 16.22s | 526.02 MB | 0.381s | 20.13x |
| 14 | 61.98% | 1.0560 | 12.00s | 526.03 MB | 0.386s | 20.13x |
| 15 | 62.68% | 1.0529 | 11.55s | 534.00 MB | 0.391s | 20.43x |
| 16 | 63.55% | 1.0157 | 11.58s | 534.00 MB | 0.386s | 20.43x |
| 17 | 63.73% | 1.0146 | 16.27s | 534.00 MB | 0.384s | 20.43x |
| 18 | 64.46% | 0.9944 | 16.51s | 534.00 MB | 0.383s | 20.43x |
| 19 | 65.84% | 0.9598 | 13.93s | 534.00 MB | 0.388s | 20.43x |
| 20 | 66.51% | 0.9408 | 11.97s | 526.03 MB | 0.384s | 20.13x |
| 21 | 65.52% | 0.9692 | 11.42s | 526.02 MB | 0.395s | 20.13x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 575488200` | 548.83 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 11708548107` | 11166.14 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 35025` | 35025 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 11708548107` | 11166.14 MB |
| 5 | Total Download / 总下载 | `sum(fetch_download_cost) = 467187779` | 445.54 MB |
| 6 | Total Communication / 总通信 | `11708548107 + 467187779 = 12175735886` | 11611.69 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 20.3454` | 20.35x |

### 5.3 Prefetch Communication Analysis / 预取通信分析

- **Total Upload / 总上传开销:** 11166.14 MB — 所有选中客户端密文上传的累计量
- **Fetch Volume (FV) / 补下载量:** 445.54 MB — 选中客户端实际 fetch 下载量（已扣除预取覆盖部分）
- **Training Communication (TV) / 训练通信:** 11611.69 MB = Upload(11166.14 MB) + FV(445.54 MB)
  ✅ 验证通过: Upload(11166.14 MB) + FV(445.54 MB) = TV(11611.69 MB)
  — TV 对齐 FedFetch 论文定义：TV = Upload + FV（不含后台预取）
- **Prefetch Broadcast / 预取广播:** 14323.55 MB — 服务器向未选中客户端后台广播的密文增量
- **Prefetch Download / 预取下载:** 14323.55 MB — 未选中客户端后台接收的密文增量
- **Prefetch + Fetch + Broadcast / 后台总流量:** 29092.65 MB = Prefetch DL(14323.55) + Fetch DL(445.54) + Broadcast(14323.55)
- **Effective Download / 理论下载责任:** 574.96 MB — 每轮 delta_size × 选中客户端数（预取节省率计算基准）
- **Prefetch Savings / 预取节省:** 129.42 MB — Effective Download 与实际 FV 的差值
- **Baseline (no prefetch) / 无预取基线:** 574.96 MB — 完整模型下载(1.05 MB × 550 次)

> **Note / 说明:**
> 1. **FV** = 选中客户端实际 fetch 下载量。TV = Upload + FV（FedFetch 论文定义）。
> 2. **Effective Download** = delta_size × 选中客户端数，是理论下载责任，仅用于计算预取节省率。
> 3. **Prefetch** = 后台/空闲时流量，不计入 TV，但计入物理总下行带宽。
> 4. 预取的核心优势是**将训练前的同步下载变为后台增量推送**，降低 wall-clock 延迟。

### 5.4 FedFetch Key Metrics (TT / FT / TV / FV) / FedFetch 核心指标

以下指标对齐 FedFetch 论文定义，用于量化预取机制的时序与通信优势：

| Metric / 指标 | Symbol / 符号 | Formula / 公式 | Substitution / 代入 | Value / 数值 | Description / 说明 |
|---------------|---------------|----------------|---------------------|--------------|-------------------|
| Training Time / 训练时间 | **TT** | `mean(total_round_time)` | `371.60/21` | 17.70 s/轮 | 每轮 wall-clock 延迟（最慢客户端完成时间） |
| Fetch Time / 补下载时间 | **FT** | `mean(fetch_time)` | `77.31/550` | 0.14 s/轮 | 选中客户端下载剩余密文增量的时间 |
| Training Volume / 训练通信 | **TV** | `mean(total_communication_cost)/2^20` | `12175735886.00/21/1048576` | 552.94 MB/轮 | 每轮训练产生的总通信量（不含后台预取） |
| Fetch Volume / 补下载量 | **FV** | `mean(download_cost)/2^20` | `467187779.00/21/1048576` | 21.22 MB/轮 | 选中客户端补充下载的密文增量 |
| Prefetch Volume / 预取量 | **PV** | `mean(prefetch_broadcast_cost)/2^20` | `15019331962.00/21/1048576` | 682.07 MB/轮 | 服务器后台广播的密文增量（不计入 TV） |

> **Parallelism / 并行性说明:** 当前实现中，预取广播在每轮训练完成后、下一轮开始前进行，
> 属于**串行调度**。预取通信量不计入 TV（训练通信），因此总通信对比是公平的；
> 预取节省的是选中客户端训练前的 fetch 等待时间，这是 FedFetch 降低 wall-clock 延迟的核心机制。

### 5.5 EMA Round Duration Analysis / EMA 轮次持续时间分析

以下指标记录每轮结束后指数移动平均（EMA）估计的轮次持续时间，用于预取调度的带宽预算计算。

**EMA平滑系数 alpha = 0.125**

| Round / 轮次 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|--------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| EMA Pred(s)  | N/A | 33.81 | 33.88 | 33.15 | 33.30 | 31.26 | 29.42 | 27.88 | 25.91 | 24.11 | 23.17 | 22.40 | 21.07 | 20.46 | 19.40 | 18.42 | 17.57 | 17.40 | 17.29 | 16.87 | 16.26 |
| Real Time(s)| 33.81 | 34.35 | 28.08 | 34.32 | 16.97 | 16.58 | 17.04 | 12.17 | 11.49 | 16.54 | 17.08 | 11.71 | 16.22 | 12.00 | 11.55 | 11.58 | 16.27 | 16.51 | 13.93 | 11.97 | 11.42 |

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final EMA Duration / 最终 EMA 持续时间 | 15.65 s | 实验结束时 EMA 估计的单轮持续时间 |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **21** 轮训练，最终测试准确率达到 **65.52%**，测试损失为 **0.9692**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **20.35x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.388s**。
- **Prefetch / 预取优化:** 启用 **CipherFetch (FedFetch-style)** 密文预取机制。
- **Training Communication / 训练通信:** 总训练通信 **11890367.08 KB**（上传 11434129.01 KB + 下载 456238.07 KB）。
- **Download Saved / 节省下载:** 选中客户端避免完整模型下载，共节省 **132524.04 KB**.
