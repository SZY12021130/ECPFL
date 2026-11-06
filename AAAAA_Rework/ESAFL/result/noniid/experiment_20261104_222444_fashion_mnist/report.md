# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261104_222444  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/noniid\experiment_20261104_222444_fashion_mnist`  

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

## 2. Key Metrics Summary / 关键指标汇总

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final Test Accuracy / 最终测试准确率 | **88.26%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.3852 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 853.42 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 60.10 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 33.96 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 17.07 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 1.20 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 781.25 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 390.62 MB / 21.22 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 390.62 MB / 12.73 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.81 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 7.81 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.06x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.041 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 6250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 250 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 1311 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.33 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 21.22 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 12.73 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 25 | 125 | 31013 kbps | 30222 kbps |
| 1 | 20 | 100 | 339099 kbps | 472285 kbps |
| 2 | 27 | 135 | 254789 kbps | 181815 kbps |
| 3 | 25 | 125 | 96962 kbps | 99657 kbps |
| 4 | 28 | 140 | 39759 kbps | 18071 kbps |
| 5 | 23 | 115 | 27438 kbps | 26345 kbps |
| 6 | 30 | 150 | 105349 kbps | 21922 kbps |
| 7 | 24 | 120 | 269298 kbps | 67032 kbps |
| 8 | 24 | 120 | 28807 kbps | 12061 kbps |
| 9 | 30 | 150 | 54690 kbps | 5467 kbps |
| 10 | 29 | 145 | 41651 kbps | 44816 kbps |
| 11 | 24 | 120 | 8057 kbps | 8610 kbps |
| 12 | 27 | 135 | 279465 kbps | 261900 kbps |
| 13 | 33 | 165 | 227204 kbps | 21076 kbps |
| 14 | 22 | 110 | 93105 kbps | 23265 kbps |
| 15 | 34 | 170 | 29282 kbps | 27951 kbps |
| 16 | 21 | 105 | 123339 kbps | 36087 kbps |
| 17 | 25 | 125 | 17150 kbps | 14397 kbps |
| 18 | 31 | 155 | 93249 kbps | 6653 kbps |
| 19 | 23 | 115 | 144829 kbps | 67399 kbps |
| 20 | 22 | 110 | 103970 kbps | 9934 kbps |
| 21 | 18 | 90 | 110526 kbps | 11922 kbps |
| 22 | 24 | 120 | 650580 kbps | 37402 kbps |
| 23 | 26 | 130 | 231919 kbps | 22700 kbps |
| 24 | 21 | 105 | 329695 kbps | 19824 kbps |
| 25 | 23 | 115 | 574578 kbps | 336917 kbps |
| 26 | 27 | 135 | 221339 kbps | 145221 kbps |
| 27 | 21 | 105 | 46710 kbps | 7069 kbps |
| 28 | 25 | 125 | 11993 kbps | 10052 kbps |
| 29 | 27 | 135 | 63094 kbps | 25450 kbps |
| 30 | 26 | 130 | 337046 kbps | 27064 kbps |
| 31 | 27 | 135 | 70923 kbps | 10978 kbps |
| 32 | 17 | 85 | 25433 kbps | 11948 kbps |
| 33 | 23 | 115 | 77720 kbps | 63169 kbps |
| 34 | 23 | 115 | 27070 kbps | 39392 kbps |
| 35 | 25 | 125 | 21428 kbps | 18340 kbps |
| 36 | 15 | 75 | 344229 kbps | 18358 kbps |
| 37 | 22 | 110 | 23038 kbps | 16389 kbps |
| 38 | 26 | 130 | 92157 kbps | 63300 kbps |
| 39 | 27 | 135 | 64407 kbps | 17650 kbps |
| 40 | 22 | 110 | 10447 kbps | 8379 kbps |
| 41 | 23 | 115 | 310817 kbps | 335451 kbps |
| 42 | 24 | 120 | 406173 kbps | 70384 kbps |
| 43 | 31 | 155 | 18551 kbps | 31260 kbps |
| 44 | 22 | 110 | 115313 kbps | 84637 kbps |
| 45 | 31 | 155 | 157061 kbps | 17346 kbps |
| 46 | 29 | 145 | 53345 kbps | 92982 kbps |
| 47 | 26 | 130 | 31064 kbps | 34562 kbps |
| 48 | 27 | 135 | 523223 kbps | 102692 kbps |
| 49 | 25 | 125 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 71.58% | 0.7750 | 1.18s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 2 | 77.58% | 0.6391 | 0.95s | 0.38s | 0.12s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 3 | 72.78% | 0.7895 | 1.13s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 4 | 77.66% | 0.7322 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 5 | 78.50% | 0.6586 | 1.24s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 6 | 82.53% | 0.5226 | 1.12s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 7 | 80.73% | 0.5667 | 1.14s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 8 | 82.08% | 0.5505 | 1.26s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 9 | 83.60% | 0.4890 | 1.24s | 0.31s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 10 | 80.76% | 0.5976 | 0.96s | 0.38s | 0.15s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 11 | 86.12% | 0.4190 | 1.04s | 0.36s | 0.15s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 12 | 80.48% | 0.5890 | 1.12s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 13 | 84.29% | 0.4681 | 1.33s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 14 | 83.91% | 0.5074 | 1.26s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 15 | 83.88% | 0.5098 | 1.33s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 16 | 85.44% | 0.4233 | 1.26s | 0.31s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 17 | 84.33% | 0.5092 | 1.29s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 18 | 82.14% | 0.5763 | 1.21s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 19 | 82.65% | 0.5593 | 1.26s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 20 | 83.37% | 0.5272 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 21 | 85.82% | 0.4594 | 1.25s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 22 | 86.14% | 0.4339 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 23 | 83.73% | 0.5415 | 1.21s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 24 | 86.58% | 0.4073 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.044s | 2.06x |
| 25 | 85.30% | 0.4851 | 1.27s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 26 | 86.32% | 0.4340 | 1.26s | 0.30s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 27 | 83.65% | 0.5591 | 1.14s | 0.47s | 0.14s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 28 | 86.14% | 0.4621 | 1.11s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 29 | 85.05% | 0.4775 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 30 | 84.44% | 0.5199 | 1.13s | 0.36s | 0.21s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 31 | 86.71% | 0.4450 | 1.22s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.044s | 2.06x |
| 32 | 84.43% | 0.5227 | 1.21s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 33 | 86.80% | 0.4211 | 1.26s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.046s | 2.06x |
| 34 | 85.96% | 0.4432 | 1.32s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 35 | 85.14% | 0.5071 | 1.08s | 0.27s | 0.21s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 36 | 85.59% | 0.4996 | 1.14s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 37 | 85.40% | 0.4803 | 1.13s | 0.47s | 0.12s | 15.62 MB | 5 | 5 | 0.039s | 2.06x |
| 38 | 82.84% | 0.6500 | 1.36s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 39 | 86.85% | 0.4145 | 1.23s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 40 | 86.54% | 0.4379 | 0.93s | 0.27s | 0.14s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 41 | 87.82% | 0.3999 | 1.29s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 42 | 84.60% | 0.5233 | 1.13s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.039s | 2.06x |
| 43 | 86.71% | 0.4477 | 1.23s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 44 | 86.68% | 0.4178 | 1.25s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 45 | 86.55% | 0.4599 | 1.20s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.039s | 2.06x |
| 46 | 87.93% | 0.4017 | 1.25s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 47 | 84.83% | 0.5098 | 1.27s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 48 | 88.01% | 0.3770 | 1.21s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 49 | 80.59% | 0.6647 | 1.22s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 50 | 88.26% | 0.3852 | 1.24s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.044s | 2.06x |

## 5. Communication & Ciphertext Details / 通信与密文计算详情

### 5.1 Formula Definitions / 公式定义

| # | Metric / 指标 | Formula / 公式 |
|---|---------------|----------------|
| 1 | Plaintext Size / 明文大小 | `sum(v.numel() * 4 for v in model_update.values())` |
| 2 | Ciphertext Size / 密文大小 | `sum(len(ct.serialize()) for ct in encrypted_update.values())` |
| 3 | Ciphertext Blocks / 密文块数 | `sum(len(v) for v in encrypted_update.values())` |
| 4 | Upload Cost / 上传开销 | `sum(ciphertext_size of selected clients)` |
| 5 | Download Cost / 下载开销 | `global_model_size_bytes * num_selected_clients` |
| 6 | Total Communication / 总通信 | `upload_cost + download_cost` |
| 7 | Expansion Ratio / 膨胀率 | `total_ciphertext_size / total_plaintext_size` |

### 5.2 Substituted Values / 数值代入

| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |
|---|---------------|-------------------|---------------|
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 198930000` | 189.71 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 409600000` | 390.62 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 6250` | 6250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 250` | 250 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `409600000/6250 = 65536` | 64.00 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(5)` | 326.51 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 409600000` | 390.62 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 409600000` | 390.62 MB |
| 9 | Total Communication / 总通信 | `409600000 + 409600000 = 819200000` | 781.25 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0590` | 2.06x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **88.26%**，测试损失为 **0.3852**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.06x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.041s**。
