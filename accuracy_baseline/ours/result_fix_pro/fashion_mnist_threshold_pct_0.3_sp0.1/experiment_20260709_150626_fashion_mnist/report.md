# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260709_150626  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline\ours\result_fix_pro\fashion_mnist_threshold_pct_0.3_sp0.1\experiment_20260709_150626_fashion_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | fashion_mnist | 训练数据集名称 |
| Model / 模型 | cnn_fmnist | 神经网络架构 |
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
| Final Test Accuracy / 最终测试准确率 | **74.59%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 1.0414 | 全局模型在测试集上的交叉熵损失 |
| Total Simulated Time / 总模拟时间 | 216.38 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 42.68 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Total Real CPU Time / 总真实CPU时间 | 3027.51 s | 单机串行执行的实际耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.33 s | 模拟 wall-clock 平均每轮耗时 |
| Avg Real Round Time / 平均真实轮次时间 | 60.55 s | 真实 CPU 平均每轮耗时 |
| Total Communication / 总通信量 | 424.10 MB | 训练通信 TV = upload + FV（选中客户端实际 fetch 下载量） |
| Total Upload / 总上传量 | 414.45 MB / 41.15 s | 所有选中客户端密文上传累计 |
| Total Download (Fetch) / 实际补下载 | 9.65 MB | 选中客户端实际 fetch 的密文增量 |
| Total Download (Prefetch) / 后台预取 | 483.02 MB | 未选中客户端后台预取的密文增量 |
| Total Actual Download / 总实际下载 | 492.68 MB | Fetch + Prefetch 物理下载总量 |
| Effective Download / 理论下载责任 | 9.65 MB | delta_size × 选中客户端数（用于 TV 计算） |
| Avg Upload Cost / 平均上传开销 | 8.29 MB | mean(upload_cost)/2^20 |
| Avg Effective Download / 平均理论下载 | 0.19 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.17x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.011 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1300 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 0 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334290 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334290 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 33.64 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 41.15 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 1.53 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |
| Avg Prefetch Accum Time / 平均预取累加时间 | 0.000 s/client | 客户端同态累加密文增量的平均耗时 |
| Avg Fetch Time / 平均Fetch时间 | 0.008 s/client | 客户端下载剩余密文增量的平均耗时 |
| Avg Apply Time / 平均应用时间 | 0.004 s/client | 客户端解密并应用预取状态的平均耗时 |
| Total Prefetch Download / 预取下载总量 | 553.28 MB | 所有客户端接收的密文增量之和 |
| Total Fetch Download / Fetch下载总量 | 9.65 MB | 所有客户端下载的剩余密文增量之和 |
| Total Prefetch Broadcast / 预取广播总量 | 553.28 MB | 服务器向未选中客户端广播的密文增量之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 | Prefetch ↓ / 预取下载 | Fetch ↓ / 补下载 | Total ↓ / 总下载 | Score / 粘性分 |
|-----|----------------|--------------|------------------|------------------|----------------------|------------------|------------------|---------------|
| 0 | 17 | 19 | 8192 kbps | 3318 kbps | 11.00 MB | 0.00 MB | 11.00 MB | 2.77 |
| 1 | 35 | 36 | 7455 kbps | 3643 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 2.49 |
| 2 | 3 | 3 | 8192 kbps | 4096 kbps | 11.00 MB | 0.45 MB | 11.45 MB | 4.68 |
| 3 | 31 | 32 | 8192 kbps | 3419 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 2.54 |
| 4 | 35 | 36 | 7936 kbps | 3326 kbps | 11.22 MB | 0.00 MB | 11.22 MB | 2.44 |
| 5 | 34 | 34 | 7270 kbps | 4096 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 3.37 |
| 6 | 26 | 28 | 6641 kbps | 3603 kbps | 9.88 MB | 0.45 MB | 10.33 MB | 1.81 |
| 7 | 33 | 34 | 8192 kbps | 4096 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 1.92 |
| 8 | 6 | 7 | 7276 kbps | 4096 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 5.26 |
| 9 | 32 | 34 | 8192 kbps | 3287 kbps | 10.77 MB | 0.45 MB | 11.22 MB | 3.50 |
| 10 | 32 | 34 | 8192 kbps | 4096 kbps | 10.77 MB | 0.22 MB | 11.00 MB | 4.22 |
| 11 | 35 | 37 | 7669 kbps | 3532 kbps | 11.45 MB | 0.00 MB | 11.45 MB | 3.58 |
| 12 | 30 | 31 | 8192 kbps | 3828 kbps | 11.22 MB | 0.22 MB | 11.45 MB | 5.11 |
| 13 | 19 | 21 | 6858 kbps | 3435 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 4.40 |
| 14 | 26 | 26 | 8192 kbps | 4096 kbps | 9.88 MB | 0.22 MB | 10.10 MB | 3.76 |
| 15 | 10 | 11 | 8192 kbps | 4096 kbps | 8.75 MB | 0.22 MB | 8.98 MB | 2.23 |
| 16 | 32 | 32 | 8192 kbps | 4096 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 4.30 |
| 17 | 30 | 31 | 7794 kbps | 4096 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 2.74 |
| 18 | 31 | 32 | 8192 kbps | 4096 kbps | 10.10 MB | 0.22 MB | 10.32 MB | 3.26 |
| 19 | 24 | 25 | 8192 kbps | 4096 kbps | 11.00 MB | 0.45 MB | 11.45 MB | 3.26 |
| 20 | 34 | 35 | 8192 kbps | 3352 kbps | 11.00 MB | 0.22 MB | 11.22 MB | 2.32 |
| 21 | 34 | 35 | 7300 kbps | 3751 kbps | 11.22 MB | 0.45 MB | 11.67 MB | 5.31 |
| 22 | 31 | 32 | 6815 kbps | 3658 kbps | 11.22 MB | 0.45 MB | 11.67 MB | 5.14 |
| 23 | 33 | 34 | 6885 kbps | 3732 kbps | 10.32 MB | 0.22 MB | 10.55 MB | 3.19 |
| 24 | 33 | 35 | 8192 kbps | 3875 kbps | 11.22 MB | 0.22 MB | 11.45 MB | 4.67 |
| 25 | 30 | 32 | 7767 kbps | 3620 kbps | 10.33 MB | 0.22 MB | 10.55 MB | 4.74 |
| 26 | 33 | 34 | 7428 kbps | 4096 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 5.03 |
| 27 | 34 | 35 | 8192 kbps | 4096 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 4.40 |
| 28 | 1 | 1 | 7114 kbps | 4096 kbps | 11.22 MB | 0.00 MB | 11.22 MB | 3.32 |
| 29 | 37 | 39 | 7089 kbps | 3898 kbps | 11.22 MB | 0.22 MB | 11.45 MB | 2.64 |
| 30 | 8 | 8 | 8192 kbps | 4096 kbps | 10.77 MB | 0.00 MB | 10.77 MB | 2.28 |
| 31 | 36 | 38 | 8192 kbps | 4096 kbps | 11.00 MB | 0.45 MB | 11.45 MB | 2.44 |
| 32 | 11 | 11 | 8192 kbps | 4096 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 2.15 |
| 33 | 32 | 33 | 7304 kbps | 3329 kbps | 10.10 MB | 0.00 MB | 10.10 MB | 1.59 |
| 34 | 33 | 34 | 7587 kbps | 3715 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 4.19 |
| 35 | 34 | 35 | 7245 kbps | 4096 kbps | 11.45 MB | 0.00 MB | 11.45 MB | 3.04 |
| 36 | 3 | 4 | 8192 kbps | 3792 kbps | 11.67 MB | 0.00 MB | 11.67 MB | 2.77 |
| 37 | 3 | 3 | 8192 kbps | 3925 kbps | 10.77 MB | 0.00 MB | 10.77 MB | 5.24 |
| 38 | 36 | 38 | 8192 kbps | 4029 kbps | 11.45 MB | 0.00 MB | 11.45 MB | 2.03 |
| 39 | 32 | 32 | 7422 kbps | 3681 kbps | 11.00 MB | 0.22 MB | 11.22 MB | 6.95 |
| 40 | 1 | 2 | 8192 kbps | 3707 kbps | 11.45 MB | 0.00 MB | 11.45 MB | 2.18 |
| 41 | 17 | 17 | 8192 kbps | 4096 kbps | 11.00 MB | 0.45 MB | 11.45 MB | 2.55 |
| 42 | 12 | 14 | 7862 kbps | 3636 kbps | 10.32 MB | 0.67 MB | 11.00 MB | 3.03 |
| 43 | 31 | 31 | 8192 kbps | 4096 kbps | 11.45 MB | 0.00 MB | 11.45 MB | 3.99 |
| 44 | 32 | 32 | 6851 kbps | 3354 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 2.67 |
| 45 | 33 | 35 | 6913 kbps | 4096 kbps | 11.22 MB | 0.22 MB | 11.45 MB | 4.82 |
| 46 | 4 | 5 | 8192 kbps | 3968 kbps | 10.77 MB | 0.22 MB | 11.00 MB | 3.79 |
| 47 | 32 | 33 | 6762 kbps | 3902 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 4.95 |
| 48 | 34 | 35 | 8192 kbps | 4096 kbps | 11.22 MB | 0.22 MB | 11.45 MB | 2.11 |
| 49 | 5 | 5 | 8192 kbps | 4096 kbps | 11.45 MB | 0.22 MB | 11.67 MB | 2.11 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 12.72% | 2.3389 | 7.87s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 2 | 19.22% | 2.2625 | 5.69s | 0.79s | 0.27s | 13.58 MB | 1 | 0 | 0.010s | 2.09x |
| 3 | 46.16% | 1.9134 | 5.60s | 0.79s | 0.55s | 11.11 MB | 1 | 0 | 0.010s | 2.09x |
| 4 | 53.08% | 1.7134 | 7.45s | 1.59s | 0.70s | 16.84 MB | 1 | 0 | 0.010s | 4.18x |
| 5 | 54.70% | 1.6458 | 5.33s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 6 | 57.01% | 1.6016 | 5.51s | 0.78s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 7 | 59.36% | 1.5570 | 5.10s | 0.78s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 8 | 59.64% | 1.5335 | 4.70s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 9 | 60.69% | 1.5084 | 4.95s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 10 | 61.43% | 1.4915 | 5.32s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.012s | 2.09x |
| 11 | 62.18% | 1.4690 | 5.04s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.012s | 2.09x |
| 12 | 62.41% | 1.4510 | 4.66s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 13 | 63.32% | 1.4384 | 4.45s | 0.78s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 14 | 63.42% | 1.4176 | 5.84s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 15 | 64.13% | 1.3997 | 4.66s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 16 | 65.24% | 1.3885 | 4.26s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 17 | 65.33% | 1.3658 | 4.32s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 18 | 65.52% | 1.3688 | 4.48s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 19 | 66.35% | 1.3453 | 4.34s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 20 | 66.94% | 1.3382 | 6.53s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 21 | 65.91% | 1.3394 | 4.79s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 22 | 67.17% | 1.3223 | 4.32s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 23 | 67.07% | 1.3149 | 2.02s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 24 | 67.45% | 1.3012 | 2.06s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 25 | 67.22% | 1.2949 | 2.27s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 26 | 68.41% | 1.2791 | 2.08s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 27 | 68.22% | 1.2735 | 2.11s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 28 | 68.87% | 1.2531 | 2.35s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 29 | 68.73% | 1.2491 | 2.08s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 30 | 68.73% | 1.2396 | 2.03s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 31 | 69.47% | 1.2260 | 1.99s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 32 | 69.66% | 1.2137 | 2.21s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 33 | 68.86% | 1.2247 | 2.00s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 34 | 69.56% | 1.2050 | 2.12s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 35 | 69.34% | 1.2142 | 2.52s | 0.78s | 0.00s | 7.97 MB | 1 | 0 | 0.012s | 2.09x |
| 36 | 69.69% | 1.2019 | 2.22s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.013s | 2.09x |
| 37 | 69.79% | 1.1835 | 2.24s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.012s | 2.09x |
| 38 | 70.00% | 1.1778 | 6.23s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 39 | 70.06% | 1.1723 | 5.61s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 40 | 70.60% | 1.1662 | 4.43s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 41 | 70.18% | 1.1629 | 4.43s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 42 | 70.68% | 1.1579 | 5.08s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.012s | 2.09x |
| 43 | 70.74% | 1.1455 | 4.59s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 44 | 71.06% | 1.1405 | 7.19s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 45 | 71.04% | 1.1317 | 5.03s | 0.80s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 46 | 71.22% | 1.1358 | 4.33s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.010s | 2.09x |
| 47 | 71.20% | 1.1240 | 4.64s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 48 | 71.42% | 1.1230 | 6.17s | 0.79s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |
| 49 | 74.50% | 1.0482 | 5.94s | 1.59s | 0.00s | 15.94 MB | 1 | 0 | 0.011s | 4.18x |
| 50 | 74.59% | 1.0414 | 5.20s | 0.78s | 0.00s | 7.97 MB | 1 | 0 | 0.011s | 2.09x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 200050000` | 190.78 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 434577583` | 414.45 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1300` | 1300 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 0` | 0 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `434577583/1300 = 334290` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.46 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 434577583` | 414.45 MB |
| 8 | Total Download (Fetch) / 实际补下载 | `sum(fetch_download_cost) = 10119920` | 9.65 MB |
| 9 | Total Communication / 总通信 | `434577583 + 10119920 = 444697503` | 424.10 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.1723` | 2.17x |

### 5.3 Prefetch Communication Analysis / 预取通信分析

- **Total Upload / 总上传开销:** 414.45 MB — 所有选中客户端密文上传的累计量
- **Fetch Volume (FV) / 补下载量:** 9.65 MB — 选中客户端实际 fetch 下载量（已扣除预取覆盖部分）
- **Training Communication (TV) / 训练通信:** 424.10 MB = Upload(414.45 MB) + FV(9.65 MB)
  ✅ 验证通过: Upload(414.45 MB) + FV(9.65 MB) = TV(424.10 MB)
  — TV 对齐 FedFetch 论文定义：TV = Upload + FV（不含后台预取）
- **Prefetch Broadcast / 预取广播:** 553.28 MB — 服务器向未选中客户端后台广播的密文增量
- **Prefetch Download / 预取下载:** 553.28 MB — 未选中客户端后台接收的密文增量
- **Prefetch + Fetch + Broadcast / 后台总流量:** 1116.22 MB = Prefetch DL(553.28) + Fetch DL(9.65) + Broadcast(553.28)
- **Effective Download / 理论下载责任:** 190.78 MB — 每轮 delta_size × 选中客户端数（预取节省率计算基准）
- **Prefetch Savings / 预取节省:** 181.13 MB — Effective Download 与实际 FV 的差值
- **Baseline (no prefetch) / 无预取基线:** 190.78 MB — 完整模型下载(0.15 MB × 1250 次)

> **Note / 说明:**
> 1. **FV** = 选中客户端实际 fetch 下载量。TV = Upload + FV（FedFetch 论文定义）。
> 2. **Effective Download** = delta_size × 选中客户端数，是理论下载责任，仅用于计算预取节省率。
> 3. **Prefetch** = 后台/空闲时流量，不计入 TV，但计入物理总下行带宽。
> 4. 预取的核心优势是**将训练前的同步下载变为后台增量推送**，降低 wall-clock 延迟。

### 5.4 FedFetch Key Metrics (TT / FT / TV / FV) / FedFetch 核心指标

以下指标对齐 FedFetch 论文定义，用于量化预取机制的时序与通信优势：

| Metric / 指标 | Symbol / 符号 | Formula / 公式 | Substitution / 代入 | Value / 数值 | Description / 说明 |
|---------------|---------------|----------------|---------------------|--------------|-------------------|
| Training Time / 训练时间 | **TT** | `mean(total_round_time)` | `216.38/50` | 4.33 s/轮 | 每轮 wall-clock 延迟（最慢客户端完成时间） |
| Fetch Time / 补下载时间 | **FT** | `mean(fetch_time)` | `10.33/1250` | 0.01 s/轮 | 选中客户端下载剩余密文增量的时间 |
| Training Volume / 训练通信 | **TV** | `mean(total_communication_cost)/2^20` | `444697503.00/50/1048576` | 8.48 MB/轮 | 每轮训练产生的总通信量（不含后台预取） |
| Fetch Volume / 补下载量 | **FV** | `mean(download_cost)/2^20` | `10119920.00/50/1048576` | 0.19 MB/轮 | 选中客户端补充下载的密文增量 |
| Prefetch Volume / 预取量 | **PV** | `mean(prefetch_broadcast_cost)/2^20` | `580158876.00/50/1048576` | 11.07 MB/轮 | 服务器后台广播的密文增量（不计入 TV） |

> **Parallelism / 并行性说明:** 当前实现中，预取广播在每轮训练完成后、下一轮开始前进行，
> 属于**串行调度**。预取通信量不计入 TV（训练通信），因此总通信对比是公平的；
> 预取节省的是选中客户端训练前的 fetch 等待时间，这是 FedFetch 降低 wall-clock 延迟的核心机制。

### 5.5 EMA Round Duration Analysis / EMA 轮次持续时间分析

以下指标记录每轮结束后指数移动平均（EMA）估计的轮次持续时间，用于预取调度的带宽预算计算。

**EMA平滑系数 alpha = 0.125**

| Round / 轮次 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40 | 41 | 42 | 43 | 44 | 45 | 46 | 47 | 48 | 49 | 50 |
|--------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|----------|
| EMA Pred(s)  | N/A | 7.87 | 7.60 | 7.35 | 7.36 | 7.11 | 6.91 | 6.68 | 6.43 | 6.25 | 6.13 | 6.00 | 5.83 | 5.66 | 5.68 | 5.55 | 5.39 | 5.26 | 5.16 | 5.06 | 5.24 | 5.19 | 5.08 | 4.70 | 4.37 | 4.10 | 3.85 | 3.63 | 3.47 | 3.30 | 3.14 | 3.00 | 2.90 | 2.79 | 2.70 | 2.68 | 2.62 | 2.57 | 3.03 | 3.35 | 3.49 | 3.61 | 3.79 | 3.89 | 4.30 | 4.39 | 4.39 | 4.42 | 4.64 | 4.80 |
| Real Time(s)| 7.87 | 5.69 | 5.60 | 7.45 | 5.33 | 5.51 | 5.10 | 4.70 | 4.95 | 5.32 | 5.04 | 4.66 | 4.45 | 5.84 | 4.66 | 4.26 | 4.32 | 4.48 | 4.34 | 6.53 | 4.79 | 4.32 | 2.02 | 2.06 | 2.27 | 2.08 | 2.11 | 2.35 | 2.08 | 2.03 | 1.99 | 2.21 | 2.00 | 2.12 | 2.52 | 2.22 | 2.24 | 6.23 | 5.61 | 4.43 | 4.43 | 5.08 | 4.59 | 7.19 | 5.03 | 4.33 | 4.64 | 6.17 | 5.94 | 5.20 |

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final EMA Duration / 最终 EMA 持续时间 | 4.85 s | 实验结束时 EMA 估计的单轮持续时间 |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **74.59%**，测试损失为 **1.0414**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.17x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.011s**。
- **Prefetch / 预取优化:** 启用 **CipherFetch (FedFetch-style)** 密文预取机制。
- **Training Communication / 训练通信:** 总训练通信 **434274.91 KB**（上传 424392.17 KB + 下载 9882.73 KB）。
- **Download Saved / 节省下载:** 选中客户端避免完整模型下载，共节省 **185478.59 KB**.
