# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261104_131315  
**Output Directory / 输出目录:** `AAAAA_Rework/FedPHE/result\experiment_20261104_131315_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **87.18%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.4076 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1267.14 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 194.46 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 157.53 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 25.34 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 3.89 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4045.91 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 1195.50 MB / 59.42 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 2850.40 MB / 98.11 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 23.91 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 57.01 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 6.27x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.014 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 3750 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 150 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334287 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 15692 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.48 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 59.42 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 98.11 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 34 | 102 | 31013 kbps | 30222 kbps |
| 1 | 10 | 30 | 339099 kbps | 472285 kbps |
| 2 | 44 | 132 | 254789 kbps | 181815 kbps |
| 3 | 24 | 72 | 96962 kbps | 99657 kbps |
| 4 | 8 | 24 | 39759 kbps | 18071 kbps |
| 5 | 17 | 51 | 27438 kbps | 26345 kbps |
| 6 | 25 | 75 | 105349 kbps | 21922 kbps |
| 7 | 27 | 81 | 269298 kbps | 67032 kbps |
| 8 | 38 | 114 | 28807 kbps | 12061 kbps |
| 9 | 20 | 60 | 54690 kbps | 5467 kbps |
| 10 | 15 | 45 | 41651 kbps | 44816 kbps |
| 11 | 20 | 60 | 8057 kbps | 8610 kbps |
| 12 | 32 | 96 | 279465 kbps | 261900 kbps |
| 13 | 42 | 126 | 227204 kbps | 21076 kbps |
| 14 | 29 | 87 | 93105 kbps | 23265 kbps |
| 15 | 30 | 90 | 29282 kbps | 27951 kbps |
| 16 | 30 | 90 | 123339 kbps | 36087 kbps |
| 17 | 40 | 120 | 17150 kbps | 14397 kbps |
| 18 | 16 | 48 | 93249 kbps | 6653 kbps |
| 19 | 15 | 45 | 144829 kbps | 67399 kbps |
| 20 | 28 | 84 | 103970 kbps | 9934 kbps |
| 21 | 12 | 36 | 110526 kbps | 11922 kbps |
| 22 | 19 | 57 | 650580 kbps | 37402 kbps |
| 23 | 21 | 63 | 231919 kbps | 22700 kbps |
| 24 | 19 | 57 | 329695 kbps | 19824 kbps |
| 25 | 23 | 69 | 574578 kbps | 336917 kbps |
| 26 | 16 | 48 | 221339 kbps | 145221 kbps |
| 27 | 12 | 36 | 46710 kbps | 7069 kbps |
| 28 | 50 | 150 | 11993 kbps | 10052 kbps |
| 29 | 29 | 87 | 63094 kbps | 25450 kbps |
| 30 | 48 | 144 | 337046 kbps | 27064 kbps |
| 31 | 13 | 39 | 70923 kbps | 10978 kbps |
| 32 | 28 | 84 | 25433 kbps | 11948 kbps |
| 33 | 14 | 42 | 77720 kbps | 63169 kbps |
| 34 | 15 | 45 | 27070 kbps | 39392 kbps |
| 35 | 10 | 30 | 21428 kbps | 18340 kbps |
| 36 | 41 | 123 | 344229 kbps | 18358 kbps |
| 37 | 41 | 123 | 23038 kbps | 16389 kbps |
| 38 | 10 | 30 | 92157 kbps | 63300 kbps |
| 39 | 12 | 36 | 64407 kbps | 17650 kbps |
| 40 | 43 | 129 | 10447 kbps | 8379 kbps |
| 41 | 35 | 105 | 310817 kbps | 335451 kbps |
| 42 | 23 | 69 | 406173 kbps | 70384 kbps |
| 43 | 19 | 57 | 18551 kbps | 31260 kbps |
| 44 | 22 | 66 | 115313 kbps | 84637 kbps |
| 45 | 23 | 69 | 157061 kbps | 17346 kbps |
| 46 | 23 | 69 | 53345 kbps | 92982 kbps |
| 47 | 16 | 48 | 31064 kbps | 34562 kbps |
| 48 | 22 | 66 | 523223 kbps | 102692 kbps |
| 49 | 47 | 141 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 47.33% | 1.8767 | 5.43s | 1.18s | 2.95s | 103.56 MB | 3 | 3 | 0.017s | 6.27x |
| 2 | 72.61% | 0.8123 | 3.84s | 1.43s | 1.66s | 96.50 MB | 3 | 3 | 0.020s | 6.27x |
| 3 | 83.15% | 0.4752 | 3.73s | 0.93s | 2.28s | 84.72 MB | 3 | 3 | 0.021s | 6.27x |
| 4 | 84.33% | 0.4534 | 3.86s | 1.18s | 1.76s | 80.02 MB | 3 | 3 | 0.020s | 6.27x |
| 5 | 85.25% | 0.4246 | 3.74s | 0.91s | 2.28s | 80.02 MB | 3 | 3 | 0.016s | 6.27x |
| 6 | 85.75% | 0.4150 | 3.49s | 0.94s | 1.76s | 80.02 MB | 3 | 3 | 0.019s | 6.27x |
| 7 | 79.26% | 0.6822 | 3.46s | 1.43s | 1.76s | 80.02 MB | 3 | 3 | 0.016s | 6.27x |
| 8 | 85.84% | 0.4215 | 4.27s | 1.18s | 2.28s | 80.02 MB | 3 | 3 | 0.013s | 6.27x |
| 9 | 86.48% | 0.3950 | 4.34s | 0.83s | 1.53s | 80.02 MB | 3 | 3 | 0.017s | 6.27x |
| 10 | 83.17% | 0.4816 | 4.61s | 0.83s | 1.53s | 80.02 MB | 3 | 3 | 0.018s | 6.27x |
| 11 | 83.75% | 0.4552 | 3.71s | 1.43s | 2.28s | 80.02 MB | 3 | 3 | 0.015s | 6.27x |
| 12 | 83.91% | 0.4540 | 3.71s | 1.43s | 2.28s | 80.02 MB | 3 | 3 | 0.013s | 6.27x |
| 13 | 82.68% | 0.4973 | 3.55s | 1.11s | 1.76s | 80.02 MB | 3 | 3 | 0.018s | 6.27x |
| 14 | 82.60% | 0.4893 | 3.87s | 1.43s | 2.28s | 80.02 MB | 3 | 3 | 0.016s | 6.27x |
| 15 | 83.39% | 0.4752 | 3.78s | 0.94s | 1.76s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 16 | 83.80% | 0.4698 | 3.61s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.019s | 6.27x |
| 17 | 83.53% | 0.4712 | 3.71s | 0.94s | 2.28s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 18 | 80.45% | 0.9097 | 4.50s | 0.94s | 1.76s | 80.03 MB | 3 | 3 | 0.020s | 6.27x |
| 19 | 74.16% | 1.2687 | 3.49s | 1.11s | 1.76s | 80.02 MB | 3 | 3 | 0.021s | 6.27x |
| 20 | 79.17% | 0.6775 | 3.44s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.018s | 6.27x |
| 21 | 77.28% | 0.7786 | 3.44s | 0.83s | 1.53s | 80.03 MB | 3 | 3 | 0.013s | 6.27x |
| 22 | 81.41% | 0.5802 | 3.70s | 1.43s | 2.28s | 80.03 MB | 3 | 3 | 0.020s | 6.27x |
| 23 | 71.87% | 1.7045 | 3.58s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 24 | 82.05% | 0.9190 | 3.73s | 0.93s | 1.76s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 25 | 82.78% | 0.8067 | 3.62s | 1.43s | 1.76s | 80.02 MB | 3 | 3 | 0.014s | 6.27x |
| 26 | 73.56% | 1.0677 | 3.63s | 0.94s | 1.76s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 27 | 80.01% | 0.6593 | 3.95s | 1.11s | 2.28s | 80.02 MB | 3 | 3 | 0.010s | 6.27x |
| 28 | 81.86% | 0.5637 | 3.63s | 1.43s | 1.53s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 29 | 79.80% | 0.8610 | 3.73s | 1.18s | 2.28s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 30 | 80.57% | 0.6397 | 4.11s | 1.43s | 2.28s | 80.02 MB | 3 | 3 | 0.010s | 6.27x |
| 31 | 79.97% | 0.7309 | 4.45s | 1.18s | 2.28s | 80.03 MB | 3 | 3 | 0.010s | 6.27x |
| 32 | 81.77% | 0.5646 | 4.39s | 0.93s | 1.76s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 33 | 82.99% | 0.5453 | 4.54s | 0.94s | 1.76s | 80.02 MB | 3 | 3 | 0.012s | 6.27x |
| 34 | 74.55% | 1.0798 | 4.47s | 0.93s | 1.76s | 80.02 MB | 3 | 3 | 0.010s | 6.27x |
| 35 | 81.69% | 0.5942 | 4.70s | 1.43s | 2.28s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 36 | 80.15% | 0.9944 | 4.52s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 37 | 75.40% | 1.1137 | 4.53s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 38 | 75.94% | 1.3784 | 3.74s | 1.11s | 2.28s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 39 | 84.43% | 0.4929 | 3.85s | 1.11s | 1.76s | 80.02 MB | 3 | 3 | 0.012s | 6.27x |
| 40 | 87.09% | 0.3958 | 3.76s | 1.18s | 2.28s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 41 | 86.70% | 0.4256 | 3.56s | 1.43s | 1.76s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 42 | 87.00% | 0.3883 | 3.51s | 0.94s | 1.76s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 43 | 84.86% | 0.4989 | 3.87s | 0.94s | 2.28s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 44 | 87.31% | 0.3790 | 3.50s | 1.43s | 1.76s | 80.02 MB | 3 | 3 | 0.012s | 6.27x |
| 45 | 84.58% | 0.4709 | 3.60s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.013s | 6.27x |
| 46 | 80.53% | 0.7061 | 3.67s | 1.43s | 2.28s | 80.03 MB | 3 | 3 | 0.011s | 6.27x |
| 47 | 81.65% | 1.2704 | 3.55s | 1.18s | 1.76s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 48 | 81.57% | 0.6175 | 3.66s | 1.18s | 2.28s | 80.02 MB | 3 | 3 | 0.011s | 6.27x |
| 49 | 87.17% | 0.4195 | 3.60s | 1.43s | 1.76s | 80.03 MB | 3 | 3 | 0.012s | 6.27x |
| 50 | 87.18% | 0.4076 | 3.75s | 1.18s | 2.28s | 80.02 MB | 3 | 3 | 0.013s | 6.27x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 200050000` | 190.78 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 1253576511` | 1195.50 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 3750` | 3750 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 150` | 150 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `1253576511/3750 = 334287` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(3)` | 326.46 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 1253576511` | 1195.50 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 2988863550` | 2850.40 MB |
| 9 | Total Communication / 总通信 | `1253576511 + 2988863550 = 4242440061` | 4045.91 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 6.2663` | 6.27x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **87.18%**，测试损失为 **0.4076**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **6.27x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.014s**。
