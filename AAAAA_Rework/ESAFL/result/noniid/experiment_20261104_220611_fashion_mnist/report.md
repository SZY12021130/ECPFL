# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261104_220611  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/noniid\experiment_20261104_220611_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **87.81%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.4220 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1083.53 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 65.62 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 33.96 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 21.67 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 1.31 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 781.25 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 390.62 MB / 21.22 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 390.62 MB / 12.73 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.81 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 7.81 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.06x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.051 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 6250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 250 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 1311 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.55 MB | CKKS公钥/Galois密钥分发总字节数 |
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
| 1 | 77.42% | 0.6384 | 2.06s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 2 | 74.64% | 0.7007 | 1.57s | 0.38s | 0.12s | 15.62 MB | 5 | 5 | 0.072s | 2.06x |
| 3 | 74.13% | 0.7475 | 1.72s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.075s | 2.06x |
| 4 | 84.72% | 0.4533 | 1.83s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 5 | 82.79% | 0.5038 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.073s | 2.06x |
| 6 | 85.40% | 0.4329 | 1.63s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 7 | 84.14% | 0.5007 | 1.60s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 8 | 85.13% | 0.4695 | 1.65s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 9 | 84.10% | 0.5051 | 1.65s | 0.31s | 0.32s | 15.62 MB | 5 | 5 | 0.072s | 2.06x |
| 10 | 84.90% | 0.4777 | 1.59s | 0.38s | 0.15s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 11 | 85.84% | 0.4175 | 1.63s | 0.36s | 0.15s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 12 | 78.01% | 0.7884 | 1.60s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 13 | 84.57% | 0.4768 | 1.62s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.072s | 2.06x |
| 14 | 84.14% | 0.5607 | 1.61s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.099s | 2.06x |
| 15 | 84.26% | 0.5156 | 1.59s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 16 | 81.73% | 0.5754 | 1.52s | 0.31s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 17 | 79.62% | 0.6667 | 1.52s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 18 | 85.27% | 0.4761 | 1.52s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 19 | 86.70% | 0.4200 | 1.08s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 20 | 86.61% | 0.4140 | 1.15s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 21 | 82.39% | 0.6270 | 1.13s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 22 | 86.91% | 0.4006 | 1.16s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 23 | 88.00% | 0.3820 | 1.05s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 24 | 85.45% | 0.4795 | 1.19s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 25 | 83.88% | 0.5643 | 1.17s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 26 | 82.77% | 0.6273 | 1.17s | 0.30s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 27 | 86.85% | 0.4386 | 1.16s | 0.47s | 0.14s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 28 | 87.02% | 0.4385 | 1.16s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 29 | 86.01% | 0.4805 | 1.21s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.067s | 2.06x |
| 30 | 87.88% | 0.3650 | 1.06s | 0.36s | 0.21s | 15.62 MB | 5 | 5 | 0.066s | 2.06x |
| 31 | 87.40% | 0.4069 | 1.09s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.067s | 2.06x |
| 32 | 88.11% | 0.3675 | 1.07s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 33 | 86.14% | 0.4896 | 1.16s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 34 | 88.39% | 0.3735 | 1.11s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 35 | 83.27% | 0.5547 | 1.04s | 0.27s | 0.21s | 15.62 MB | 5 | 5 | 0.068s | 2.06x |
| 36 | 85.70% | 0.4544 | 1.17s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 37 | 88.40% | 0.3633 | 1.08s | 0.47s | 0.12s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 38 | 85.63% | 0.5060 | 1.04s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 39 | 86.14% | 0.4707 | 1.13s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 40 | 86.90% | 0.4296 | 0.97s | 0.27s | 0.14s | 15.62 MB | 5 | 5 | 0.072s | 2.06x |
| 41 | 87.47% | 0.4119 | 1.16s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 42 | 85.68% | 0.5107 | 1.14s | 0.47s | 0.15s | 15.62 MB | 5 | 5 | 0.069s | 2.06x |
| 43 | 88.78% | 0.3624 | 1.09s | 0.38s | 0.25s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 44 | 86.37% | 0.4572 | 1.16s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 45 | 87.74% | 0.4272 | 1.15s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 46 | 87.04% | 0.4313 | 1.16s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.103s | 2.06x |
| 47 | 85.69% | 0.4922 | 1.20s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |
| 48 | 87.85% | 0.3864 | 1.14s | 0.47s | 0.21s | 15.62 MB | 5 | 5 | 0.068s | 2.06x |
| 49 | 88.21% | 0.3834 | 1.15s | 0.47s | 0.25s | 15.62 MB | 5 | 5 | 0.071s | 2.06x |
| 50 | 87.81% | 0.4220 | 1.17s | 0.38s | 0.32s | 15.62 MB | 5 | 5 | 0.070s | 2.06x |

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
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(5)` | 326.28 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 409600000` | 390.62 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 409600000` | 390.62 MB |
| 9 | Total Communication / 总通信 | `409600000 + 409600000 = 819200000` | 781.25 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0590` | 2.06x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **87.81%**，测试损失为 **0.4220**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.06x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.051s**。
