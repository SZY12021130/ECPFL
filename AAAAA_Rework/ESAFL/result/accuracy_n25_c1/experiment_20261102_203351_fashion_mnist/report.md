# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261102_203351  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/accuracy_n25_c1\experiment_20261102_203351_fashion_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | fashion_mnist | 训练数据集名称 |
| Model / 模型 | cnn_fmnist | 神经网络架构 |
| Num Clients / 客户端数 | 25 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 50 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练epoch数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD优化器学习率 |
| Client Sampling Rate / 采样率 | 1.0 | 每轮参与训练的客户端比例 |
| IID / 独立同分布 | True | 数据分布是否IID |
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
| Final Test Accuracy / 最终测试准确率 | **88.02%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.4290 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1734.09 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 101.73 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 39.30 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 34.68 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 2.03 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 781.25 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 390.62 MB / 23.41 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 390.62 MB / 15.89 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.81 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 7.81 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.06x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.047 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 6250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 250 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 1311 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.78 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 23.41 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 15.89 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 250 | 31013 kbps | 30222 kbps |
| 1 | 50 | 250 | 339099 kbps | 472285 kbps |
| 2 | 50 | 250 | 254789 kbps | 181815 kbps |
| 3 | 50 | 250 | 96962 kbps | 99657 kbps |
| 4 | 50 | 250 | 39759 kbps | 18071 kbps |
| 5 | 50 | 250 | 27438 kbps | 26345 kbps |
| 6 | 50 | 250 | 105349 kbps | 21922 kbps |
| 7 | 50 | 250 | 269298 kbps | 67032 kbps |
| 8 | 50 | 250 | 28807 kbps | 12061 kbps |
| 9 | 50 | 250 | 54690 kbps | 5467 kbps |
| 10 | 50 | 250 | 41651 kbps | 44816 kbps |
| 11 | 50 | 250 | 8057 kbps | 8610 kbps |
| 12 | 50 | 250 | 279465 kbps | 261900 kbps |
| 13 | 50 | 250 | 227204 kbps | 21076 kbps |
| 14 | 50 | 250 | 93105 kbps | 23265 kbps |
| 15 | 50 | 250 | 29282 kbps | 27951 kbps |
| 16 | 50 | 250 | 123339 kbps | 36087 kbps |
| 17 | 50 | 250 | 17150 kbps | 14397 kbps |
| 18 | 50 | 250 | 93249 kbps | 6653 kbps |
| 19 | 50 | 250 | 144829 kbps | 67399 kbps |
| 20 | 50 | 250 | 103970 kbps | 9934 kbps |
| 21 | 50 | 250 | 110526 kbps | 11922 kbps |
| 22 | 50 | 250 | 650580 kbps | 37402 kbps |
| 23 | 50 | 250 | 231919 kbps | 22700 kbps |
| 24 | 50 | 250 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 60.25% | 1.3179 | 2.64s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.051s | 2.06x |
| 2 | 77.26% | 0.6740 | 1.77s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 3 | 75.36% | 0.8089 | 2.17s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 4 | 76.08% | 0.7980 | 1.79s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 5 | 77.46% | 0.7491 | 1.78s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 6 | 79.82% | 0.6600 | 1.72s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 7 | 78.26% | 0.7511 | 2.58s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 8 | 76.41% | 0.8522 | 1.78s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 9 | 79.31% | 0.6817 | 1.85s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 10 | 79.60% | 0.7265 | 2.53s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 11 | 79.51% | 0.7427 | 2.63s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 12 | 83.02% | 0.5654 | 2.88s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 13 | 82.27% | 0.6072 | 2.58s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 14 | 82.78% | 0.6005 | 1.74s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 15 | 83.06% | 0.5891 | 1.66s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 16 | 85.30% | 0.5081 | 1.75s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 17 | 83.52% | 0.5375 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 18 | 84.99% | 0.4999 | 1.75s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 19 | 83.44% | 0.5837 | 3.03s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 20 | 86.56% | 0.4749 | 1.94s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 21 | 85.66% | 0.4958 | 2.94s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 22 | 82.75% | 0.6225 | 2.88s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 23 | 85.76% | 0.5017 | 1.63s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.044s | 2.06x |
| 24 | 83.28% | 0.6450 | 1.68s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.043s | 2.06x |
| 25 | 86.63% | 0.4489 | 2.28s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.044s | 2.06x |
| 26 | 85.34% | 0.5221 | 1.59s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.046s | 2.06x |
| 27 | 87.20% | 0.4076 | 1.70s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.046s | 2.06x |
| 28 | 86.46% | 0.4622 | 1.73s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.046s | 2.06x |
| 29 | 84.08% | 0.5846 | 1.62s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.047s | 2.06x |
| 30 | 87.42% | 0.4325 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.046s | 2.06x |
| 31 | 85.71% | 0.4968 | 1.64s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.045s | 2.06x |
| 32 | 86.89% | 0.4531 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 33 | 84.34% | 0.5621 | 1.72s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 34 | 86.47% | 0.4683 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 35 | 85.01% | 0.5381 | 1.73s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 36 | 85.95% | 0.5369 | 1.69s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 37 | 85.45% | 0.5971 | 1.70s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 38 | 87.62% | 0.4357 | 1.72s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 39 | 88.49% | 0.4007 | 1.73s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 40 | 87.75% | 0.4284 | 1.72s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 41 | 88.66% | 0.4059 | 1.67s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 42 | 89.22% | 0.3632 | 2.89s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 43 | 88.36% | 0.4162 | 2.93s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 44 | 88.77% | 0.4006 | 2.81s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 45 | 86.16% | 0.5422 | 2.72s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 46 | 87.96% | 0.4137 | 2.89s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 47 | 88.02% | 0.4190 | 1.61s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.041s | 2.06x |
| 48 | 89.13% | 0.3950 | 1.74s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |
| 49 | 89.22% | 0.3911 | 1.73s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.042s | 2.06x |
| 50 | 88.02% | 0.4290 | 1.73s | 0.47s | 0.32s | 15.62 MB | 5 | 5 | 0.040s | 2.06x |

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
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(5)` | 326.47 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 409600000` | 390.62 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 409600000` | 390.62 MB |
| 9 | Total Communication / 总通信 | `409600000 + 409600000 = 819200000` | 781.25 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0590` | 2.06x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **88.02%**，测试损失为 **0.4290**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.06x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.047s**。
