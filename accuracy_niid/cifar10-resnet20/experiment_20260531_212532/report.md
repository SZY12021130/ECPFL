# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260531_212532  
**Output Directory / 输出目录:** `accuracy_niid\cifar10-resnet20\experiment_20260531_212532`  

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
| Final Test Accuracy / 最终测试准确率 | **65.64%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.9590 | 全局模型在测试集上的交叉熵损失 |
| Total Simulated Time / 总模拟时间 | 429.02 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Real CPU Time / 总真实CPU时间 | 1161.31 s | 单机串行执行的实际耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 15.32 s | 模拟 wall-clock 平均每轮耗时 |
| Avg Real Round Time / 平均真实轮次时间 | 41.48 s | 真实 CPU 平均每轮耗时 |
| Total Communication / 总通信量 | 15044.40 MB | 训练通信 TV = upload + FV（选中客户端实际 fetch 下载量） |
| Total Upload / 总上传量 | 14593.24 MB / 0.00 s | 所有选中客户端密文上传累计 |
| Total Download (Fetch) / 实际补下载 | 451.16 MB | 选中客户端实际 fetch 的密文增量 |
| Total Download (Prefetch) / 后台预取 | 14987.91 MB | 未选中客户端后台预取的密文增量 |
| Total Actual Download / 总实际下载 | 15439.06 MB | Fetch + Prefetch 物理下载总量 |
| Effective Download / 理论下载责任 | 451.16 MB | delta_size × 选中客户端数（用于 TV 计算） |
| Avg Upload Cost / 平均上传开销 | 521.19 MB | mean(upload_cost)/2^20 |
| Avg Effective Download / 平均理论下载 | 16.11 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 19.94x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.223 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 33.66 MB | CKKS公钥/Galois密钥分发总字节数 |
| Avg Prefetch Accum Time / 平均预取累加时间 | 0.000 s/client | 客户端同态累加密文增量的平均耗时 |
| Avg Fetch Time / 平均Fetch时间 | 0.108 s/client | 客户端下载剩余密文增量的平均耗时 |
| Avg Apply Time / 平均应用时间 | 0.086 s/client | 客户端解密并应用预取状态的平均耗时 |
| Total Prefetch Download / 预取下载总量 | 18961.48 MB | 所有客户端接收的密文增量之和 |
| Total Fetch Download / Fetch下载总量 | 451.16 MB | 所有客户端下载的剩余密文增量之和 |
| Total Prefetch Broadcast / 预取广播总量 | 18961.48 MB | 服务器向未选中客户端广播的密文增量之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 | Prefetch ↓ / 预取下载 | Fetch ↓ / 补下载 | Total ↓ / 总下载 | Score / 粘性分 |
|-----|----------------|--------------|------------------|------------------|----------------------|------------------|------------------|---------------|
| 0 | 17 | 1104 | 31013 kbps | 30222 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 4.52 |
| 1 | 20 | 1240 | 339099 kbps | 472285 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 2.55 |
| 2 | 18 | 1183 | 254789 kbps | 181815 kbps | 353.74 MB | 15.04 MB | 368.78 MB | 2.80 |
| 3 | 21 | 1369 | 96962 kbps | 99657 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 2.43 |
| 4 | 18 | 1106 | 39759 kbps | 18071 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 4.53 |
| 5 | 20 | 1317 | 27438 kbps | 26345 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.80 |
| 6 | 19 | 1178 | 105349 kbps | 21922 kbps | 380.90 MB | 15.04 MB | 395.94 MB | 2.26 |
| 7 | 18 | 1112 | 269298 kbps | 67032 kbps | 366.31 MB | 15.04 MB | 381.35 MB | 3.61 |
| 8 | 5 | 330 | 28807 kbps | 12061 kbps | 382.25 MB | 15.04 MB | 397.29 MB | 1.07 |
| 9 | 3 | 201 | 54690 kbps | 5467 kbps | 381.58 MB | 15.04 MB | 396.62 MB | 2.46 |
| 10 | 21 | 1309 | 41651 kbps | 44816 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 2.07 |
| 11 | 1 | 67 | 8057 kbps | 8610 kbps | 314.02 MB | 0.00 MB | 314.02 MB | 1.81 |
| 12 | 19 | 1172 | 279465 kbps | 261900 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.45 |
| 13 | 20 | 1236 | 227204 kbps | 21076 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.20 |
| 14 | 20 | 1239 | 93105 kbps | 23265 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.03 |
| 15 | 18 | 1109 | 29282 kbps | 27951 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 5.11 |
| 16 | 17 | 1123 | 123339 kbps | 36087 kbps | 367.66 MB | 15.04 MB | 382.70 MB | 5.28 |
| 17 | 11 | 719 | 17150 kbps | 14397 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 1.92 |
| 18 | 1 | 67 | 93249 kbps | 6653 kbps | 381.13 MB | 0.00 MB | 381.13 MB | 1.46 |
| 19 | 18 | 1183 | 144829 kbps | 67399 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 4.65 |
| 20 | 1 | 67 | 103970 kbps | 9934 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 1.68 |
| 21 | 6 | 387 | 110526 kbps | 11922 kbps | 365.86 MB | 0.00 MB | 365.86 MB | 1.63 |
| 22 | 17 | 1036 | 650580 kbps | 37402 kbps | 365.87 MB | 0.00 MB | 365.87 MB | 3.63 |
| 23 | 19 | 1181 | 231919 kbps | 22700 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.47 |
| 24 | 19 | 1182 | 329695 kbps | 19824 kbps | 366.31 MB | 15.04 MB | 381.35 MB | 2.98 |
| 25 | 17 | 1043 | 574578 kbps | 336917 kbps | 351.27 MB | 15.04 MB | 366.31 MB | 4.52 |
| 26 | 20 | 1240 | 221339 kbps | 145221 kbps | 381.58 MB | 15.04 MB | 396.61 MB | 3.56 |
| 27 | 2 | 134 | 46710 kbps | 7069 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 3.69 |
| 28 | 2 | 134 | 11993 kbps | 10052 kbps | 367.89 MB | 0.00 MB | 367.89 MB | 4.34 |
| 29 | 19 | 1174 | 63094 kbps | 25450 kbps | 365.87 MB | 15.04 MB | 380.91 MB | 3.59 |
| 30 | 17 | 1047 | 337046 kbps | 27064 kbps | 306.83 MB | 15.04 MB | 321.87 MB | 2.06 |
| 31 | 1 | 67 | 70923 kbps | 10978 kbps | 337.81 MB | 0.00 MB | 337.81 MB | 2.76 |
| 32 | 7 | 459 | 25433 kbps | 11948 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 2.08 |
| 33 | 18 | 1107 | 77720 kbps | 63169 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 4.93 |
| 34 | 20 | 1300 | 27070 kbps | 39392 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 3.05 |
| 35 | 19 | 1174 | 21428 kbps | 18340 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 5.40 |
| 36 | 18 | 1175 | 344229 kbps | 18358 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 3.47 |
| 37 | 13 | 859 | 23038 kbps | 16389 kbps | 381.13 MB | 15.04 MB | 396.16 MB | 2.25 |
| 38 | 18 | 1114 | 92157 kbps | 63300 kbps | 366.99 MB | 15.04 MB | 382.03 MB | 2.98 |
| 39 | 17 | 1111 | 64407 kbps | 17650 kbps | 381.80 MB | 0.00 MB | 381.80 MB | 4.68 |
| 40 | 3 | 201 | 10447 kbps | 8379 kbps | 316.94 MB | 15.04 MB | 331.97 MB | 2.16 |
| 41 | 16 | 1048 | 310817 kbps | 335451 kbps | 380.90 MB | 15.04 MB | 395.94 MB | 4.72 |
| 42 | 17 | 1105 | 406173 kbps | 70384 kbps | 366.09 MB | 0.00 MB | 366.09 MB | 5.09 |
| 43 | 22 | 1375 | 18551 kbps | 31260 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 1.97 |
| 44 | 20 | 1243 | 115313 kbps | 84637 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 4.47 |
| 45 | 16 | 978 | 157061 kbps | 17346 kbps | 395.94 MB | 0.00 MB | 395.94 MB | 4.34 |
| 46 | 17 | 1047 | 53345 kbps | 92982 kbps | 366.31 MB | 15.04 MB | 381.35 MB | 5.03 |
| 47 | 20 | 1244 | 31064 kbps | 34562 kbps | 395.94 MB | 15.04 MB | 410.98 MB | 3.89 |
| 48 | 17 | 1045 | 523223 kbps | 102692 kbps | 380.90 MB | 0.00 MB | 380.90 MB | 3.35 |
| 49 | 2 | 134 | 21748 kbps | 9455 kbps | 380.90 MB | 15.04 MB | 395.94 MB | 3.07 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 11.59% | 2.2846 | 34.28s | 534.01 MB | 0.225s | 20.43x |
| 2 | 25.42% | 1.9424 | 34.30s | 909.97 MB | 0.219s | 20.43x |
| 3 | 30.62% | 1.7881 | 27.28s | 594.14 MB | 0.219s | 20.43x |
| 4 | 41.70% | 1.6212 | 34.28s | 549.03 MB | 0.219s | 20.43x |
| 5 | 38.19% | 1.6244 | 15.40s | 518.06 MB | 0.221s | 19.82x |
| 6 | 37.96% | 1.6419 | 15.21s | 526.03 MB | 0.220s | 20.13x |
| 7 | 43.22% | 1.5364 | 15.38s | 518.06 MB | 0.216s | 19.82x |
| 8 | 47.42% | 1.4098 | 11.58s | 533.99 MB | 0.219s | 20.43x |
| 9 | 48.32% | 1.3993 | 10.92s | 534.00 MB | 0.222s | 20.43x |
| 10 | 52.79% | 1.3154 | 15.03s | 526.02 MB | 0.223s | 20.13x |
| 11 | 50.15% | 1.3509 | 15.59s | 526.02 MB | 0.219s | 20.13x |
| 12 | 53.02% | 1.2773 | 10.88s | 533.99 MB | 0.221s | 20.43x |
| 13 | 55.20% | 1.2266 | 15.22s | 534.00 MB | 0.221s | 20.43x |
| 14 | 57.99% | 1.1781 | 11.39s | 526.03 MB | 0.219s | 20.13x |
| 15 | 58.30% | 1.1470 | 10.92s | 534.01 MB | 0.225s | 20.43x |
| 16 | 56.17% | 1.2069 | 10.44s | 510.09 MB | 0.226s | 19.52x |
| 17 | 59.71% | 1.1075 | 14.14s | 494.14 MB | 0.225s | 18.91x |
| 18 | 58.94% | 1.1158 | 14.14s | 494.14 MB | 0.218s | 18.91x |
| 19 | 55.94% | 1.1784 | 12.34s | 502.12 MB | 0.220s | 19.21x |
| 20 | 59.60% | 1.0976 | 11.24s | 518.05 MB | 0.219s | 19.82x |
| 21 | 55.91% | 1.1836 | 10.57s | 518.05 MB | 0.219s | 19.82x |
| 22 | 60.92% | 1.0630 | 11.72s | 533.99 MB | 0.220s | 20.43x |
| 23 | 59.17% | 1.0959 | 10.43s | 510.07 MB | 0.223s | 19.52x |
| 24 | 60.47% | 1.0740 | 10.58s | 526.03 MB | 0.220s | 20.13x |
| 25 | 60.85% | 1.0494 | 12.51s | 510.08 MB | 0.220s | 19.52x |
| 26 | 61.81% | 1.0330 | 12.88s | 526.03 MB | 0.222s | 20.13x |
| 27 | 62.42% | 1.0188 | 9.96s | 494.14 MB | 0.222s | 18.91x |
| 28 | 65.64% | 0.9590 | 10.44s | 510.08 MB | 0.217s | 19.52x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 767317600` | 731.77 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 15302119954` | 14593.24 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 45775` | 45775 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 15302119954` | 14593.24 MB |
| 5 | Total Download / 总下载 | `sum(fetch_download_cost) = 473071877` | 451.16 MB |
| 6 | Total Communication / 总通信 | `15302119954 + 473071877 = 15775191831` | 15044.40 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 19.9424` | 19.94x |

### 5.3 Prefetch Communication Analysis / 预取通信分析

- **Total Upload / 总上传开销:** 14593.24 MB — 所有选中客户端密文上传的累计量
- **Fetch Volume (FV) / 补下载量:** 451.16 MB — 选中客户端实际 fetch 下载量（已扣除预取覆盖部分）
- **Training Communication (TV) / 训练通信:** 15044.40 MB = Upload(14593.24 MB) + FV(451.16 MB)
  ✅ 验证通过: Upload(14593.24 MB) + FV(451.16 MB) = TV(15044.40 MB)
  — TV 对齐 FedFetch 论文定义：TV = Upload + FV（不含后台预取）
- **Prefetch Broadcast / 预取广播:** 18961.48 MB — 服务器向未选中客户端后台广播的密文增量
- **Prefetch Download / 预取下载:** 18961.48 MB — 未选中客户端后台接收的密文增量
- **Prefetch + Fetch + Broadcast / 后台总流量:** 38374.11 MB = Prefetch DL(18961.48) + Fetch DL(451.16) + Broadcast(18961.48)
- **Effective Download / 理论下载责任:** 757.91 MB — 每轮 delta_size × 选中客户端数（预取节省率计算基准）
- **Prefetch Savings / 预取节省:** 306.75 MB — Effective Download 与实际 FV 的差值
- **Baseline (no prefetch) / 无预取基线:** 757.91 MB — 完整模型下载(1.05 MB × 725 次)

> **Note / 说明:**
> 1. **FV** = 选中客户端实际 fetch 下载量。TV = Upload + FV（FedFetch 论文定义）。
> 2. **Effective Download** = delta_size × 选中客户端数，是理论下载责任，仅用于计算预取节省率。
> 3. **Prefetch** = 后台/空闲时流量，不计入 TV，但计入物理总下行带宽。
> 4. 预取的核心优势是**将训练前的同步下载变为后台增量推送**，降低 wall-clock 延迟。

### 5.4 FedFetch Key Metrics (TT / FT / TV / FV) / FedFetch 核心指标

以下指标对齐 FedFetch 论文定义，用于量化预取机制的时序与通信优势：

| Metric / 指标 | Symbol / 符号 | Formula / 公式 | Substitution / 代入 | Value / 数值 | Description / 说明 |
|---------------|---------------|----------------|---------------------|--------------|-------------------|
| Training Time / 训练时间 | **TT** | `mean(total_round_time)` | `429.02/28` | 15.32 s/轮 | 每轮 wall-clock 延迟（最慢客户端完成时间） |
| Fetch Time / 补下载时间 | **FT** | `mean(fetch_time)` | `78.39/725` | 0.11 s/轮 | 选中客户端下载剩余密文增量的时间 |
| Training Volume / 训练通信 | **TV** | `mean(total_communication_cost)/2^20` | `15775191831.00/28/1048576` | 537.30 MB/轮 | 每轮训练产生的总通信量（不含后台预取） |
| Fetch Volume / 补下载量 | **FV** | `mean(download_cost)/2^20` | `473071877.00/28/1048576` | 16.11 MB/轮 | 选中客户端补充下载的密文增量 |
| Prefetch Volume / 预取量 | **PV** | `mean(prefetch_broadcast_cost)/2^20` | `19882550395.00/28/1048576` | 677.20 MB/轮 | 服务器后台广播的密文增量（不计入 TV） |

> **Parallelism / 并行性说明:** 当前实现中，预取广播在每轮训练完成后、下一轮开始前进行，
> 属于**串行调度**。预取通信量不计入 TV（训练通信），因此总通信对比是公平的；
> 预取节省的是选中客户端训练前的 fetch 等待时间，这是 FedFetch 降低 wall-clock 延迟的核心机制。

### 5.5 EMA Round Duration Analysis / EMA 轮次持续时间分析

以下指标记录每轮结束后指数移动平均（EMA）估计的轮次持续时间，用于预取调度的带宽预算计算。

**EMA平滑系数 alpha = 0.125**

| Round / 轮次 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 |
|--------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| EMA Pred(s)  | N/A | 34.28 | 34.28 | 33.40 | 33.51 | 31.25 | 29.24 | 27.51 | 25.52 | 23.69 | 22.61 | 21.73 | 20.38 | 19.73 | 18.69 | 17.72 | 16.81 | 16.47 | 16.18 | 15.70 | 15.14 | 14.57 | 14.22 | 13.74 | 13.35 | 13.24 | 13.20 | 12.79 |
| Real Time(s)| 34.28 | 34.30 | 27.28 | 34.28 | 15.40 | 15.21 | 15.38 | 11.58 | 10.92 | 15.03 | 15.59 | 10.88 | 15.22 | 11.39 | 10.92 | 10.44 | 14.14 | 14.14 | 12.34 | 11.24 | 10.57 | 11.72 | 10.43 | 10.58 | 12.51 | 12.88 | 9.96 | 10.44 |

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final EMA Duration / 最终 EMA 持续时间 | 12.50 s | 实验结束时 EMA 估计的单轮持续时间 |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **28** 轮训练，最终测试准确率达到 **65.64%**，测试损失为 **0.9590**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **19.94x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.223s**。
- **Prefetch / 预取优化:** 启用 **CipherFetch (FedFetch-style)** 密文预取机制。
- **Training Communication / 训练通信:** 总训练通信 **15405460.77 KB**（上传 14943476.52 KB + 下载 461984.25 KB）。
- **Download Saved / 节省下载:** 选中客户端避免完整模型下载，共节省 **314111.25 KB**.
