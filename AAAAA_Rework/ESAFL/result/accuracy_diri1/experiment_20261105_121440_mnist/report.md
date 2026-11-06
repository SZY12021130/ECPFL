# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261105_121440  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/accuracy_diri1\experiment_20261105_121440_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | mnist | 训练数据集名称 |
| Model / 模型 | lenet | 神经网络架构 |
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
| Final Test Accuracy / 最终测试准确率 | **98.10%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.0649 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 837.25 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 71.94 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 40.75 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 16.75 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 1.44 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 937.50 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 468.75 MB / 25.47 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 468.75 MB / 15.28 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 9.38 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 9.38 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.21x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.050 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 7500 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 300 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 1311 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.56 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 25.47 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 15.28 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 25 | 150 | 31013 kbps | 30222 kbps |
| 1 | 20 | 120 | 339099 kbps | 472285 kbps |
| 2 | 27 | 162 | 254789 kbps | 181815 kbps |
| 3 | 25 | 150 | 96962 kbps | 99657 kbps |
| 4 | 28 | 168 | 39759 kbps | 18071 kbps |
| 5 | 23 | 138 | 27438 kbps | 26345 kbps |
| 6 | 30 | 180 | 105349 kbps | 21922 kbps |
| 7 | 24 | 144 | 269298 kbps | 67032 kbps |
| 8 | 24 | 144 | 28807 kbps | 12061 kbps |
| 9 | 30 | 180 | 54690 kbps | 5467 kbps |
| 10 | 29 | 174 | 41651 kbps | 44816 kbps |
| 11 | 24 | 144 | 8057 kbps | 8610 kbps |
| 12 | 27 | 162 | 279465 kbps | 261900 kbps |
| 13 | 33 | 198 | 227204 kbps | 21076 kbps |
| 14 | 22 | 132 | 93105 kbps | 23265 kbps |
| 15 | 34 | 204 | 29282 kbps | 27951 kbps |
| 16 | 21 | 126 | 123339 kbps | 36087 kbps |
| 17 | 25 | 150 | 17150 kbps | 14397 kbps |
| 18 | 31 | 186 | 93249 kbps | 6653 kbps |
| 19 | 23 | 138 | 144829 kbps | 67399 kbps |
| 20 | 22 | 132 | 103970 kbps | 9934 kbps |
| 21 | 18 | 108 | 110526 kbps | 11922 kbps |
| 22 | 24 | 144 | 650580 kbps | 37402 kbps |
| 23 | 26 | 156 | 231919 kbps | 22700 kbps |
| 24 | 21 | 126 | 329695 kbps | 19824 kbps |
| 25 | 23 | 138 | 574578 kbps | 336917 kbps |
| 26 | 27 | 162 | 221339 kbps | 145221 kbps |
| 27 | 21 | 126 | 46710 kbps | 7069 kbps |
| 28 | 25 | 150 | 11993 kbps | 10052 kbps |
| 29 | 27 | 162 | 63094 kbps | 25450 kbps |
| 30 | 26 | 156 | 337046 kbps | 27064 kbps |
| 31 | 27 | 162 | 70923 kbps | 10978 kbps |
| 32 | 17 | 102 | 25433 kbps | 11948 kbps |
| 33 | 23 | 138 | 77720 kbps | 63169 kbps |
| 34 | 23 | 138 | 27070 kbps | 39392 kbps |
| 35 | 25 | 150 | 21428 kbps | 18340 kbps |
| 36 | 15 | 90 | 344229 kbps | 18358 kbps |
| 37 | 22 | 132 | 23038 kbps | 16389 kbps |
| 38 | 26 | 156 | 92157 kbps | 63300 kbps |
| 39 | 27 | 162 | 64407 kbps | 17650 kbps |
| 40 | 22 | 132 | 10447 kbps | 8379 kbps |
| 41 | 23 | 138 | 310817 kbps | 335451 kbps |
| 42 | 24 | 144 | 406173 kbps | 70384 kbps |
| 43 | 31 | 186 | 18551 kbps | 31260 kbps |
| 44 | 22 | 132 | 115313 kbps | 84637 kbps |
| 45 | 31 | 186 | 157061 kbps | 17346 kbps |
| 46 | 29 | 174 | 53345 kbps | 92982 kbps |
| 47 | 26 | 156 | 31064 kbps | 34562 kbps |
| 48 | 27 | 162 | 523223 kbps | 102692 kbps |
| 49 | 25 | 150 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 29.26% | 1.9399 | 1.42s | 0.56s | 0.18s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 2 | 84.27% | 0.5777 | 1.14s | 0.46s | 0.14s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 3 | 84.20% | 0.4727 | 1.32s | 0.56s | 0.26s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 4 | 91.69% | 0.2711 | 1.74s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 5 | 92.81% | 0.2318 | 1.66s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 6 | 94.29% | 0.1887 | 1.26s | 0.56s | 0.26s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 7 | 95.54% | 0.1434 | 1.16s | 0.56s | 0.18s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 8 | 95.87% | 0.1307 | 1.63s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 9 | 96.37% | 0.1131 | 1.74s | 0.37s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 10 | 96.77% | 0.1031 | 1.20s | 0.46s | 0.18s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 11 | 96.46% | 0.1173 | 1.25s | 0.43s | 0.18s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 12 | 97.03% | 0.0982 | 1.28s | 0.56s | 0.26s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 13 | 96.77% | 0.1029 | 1.65s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 14 | 97.35% | 0.0828 | 1.75s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 15 | 97.01% | 0.0926 | 1.59s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 16 | 97.52% | 0.0770 | 1.62s | 0.37s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 17 | 97.33% | 0.0855 | 1.67s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 18 | 97.73% | 0.0721 | 1.36s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 19 | 97.68% | 0.0681 | 1.52s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 20 | 96.99% | 0.1019 | 1.56s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 21 | 97.98% | 0.0670 | 1.57s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 22 | 97.92% | 0.0626 | 1.53s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 23 | 98.09% | 0.0630 | 1.09s | 0.46s | 0.29s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 24 | 96.21% | 0.1183 | 1.54s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 25 | 97.76% | 0.0701 | 1.66s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 26 | 98.09% | 0.0685 | 1.63s | 0.36s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 27 | 98.31% | 0.0550 | 1.23s | 0.56s | 0.17s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 28 | 98.14% | 0.0570 | 1.18s | 0.56s | 0.26s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 29 | 98.33% | 0.0525 | 1.67s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 30 | 98.28% | 0.0546 | 1.23s | 0.43s | 0.26s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 31 | 97.70% | 0.0748 | 1.24s | 0.46s | 0.29s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 32 | 98.35% | 0.0507 | 1.29s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 33 | 98.35% | 0.0510 | 1.74s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 34 | 98.28% | 0.0543 | 1.76s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 35 | 98.38% | 0.0488 | 1.31s | 0.32s | 0.26s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 36 | 98.44% | 0.0510 | 1.29s | 0.56s | 0.18s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 37 | 98.51% | 0.0472 | 1.22s | 0.56s | 0.14s | 18.75 MB | 6 | 6 | 0.046s | 2.21x |
| 38 | 98.47% | 0.0474 | 1.16s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 39 | 98.15% | 0.0582 | 1.26s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 40 | 98.54% | 0.0475 | 1.23s | 0.32s | 0.17s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 41 | 98.60% | 0.0468 | 1.75s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 42 | 98.56% | 0.0459 | 1.26s | 0.56s | 0.18s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 43 | 98.45% | 0.0506 | 1.25s | 0.46s | 0.29s | 18.75 MB | 6 | 6 | 0.045s | 2.21x |
| 44 | 98.47% | 0.0447 | 1.63s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 45 | 98.61% | 0.0455 | 1.23s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 46 | 98.27% | 0.0542 | 1.60s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 47 | 98.48% | 0.0467 | 1.64s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 48 | 98.23% | 0.0559 | 1.28s | 0.56s | 0.26s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 49 | 92.94% | 0.3096 | 1.22s | 0.56s | 0.29s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 50 | 98.10% | 0.0649 | 1.67s | 0.46s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 222130000` | 211.84 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 491520000` | 468.75 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 7500` | 7500 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 300` | 300 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `491520000/7500 = 65536` | 64.00 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(6)` | 326.65 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 491520000` | 468.75 MB |
| 8 | Total Download / 总下载 | `model_size(177704) * selected(1250) = 491520000` | 468.75 MB |
| 9 | Total Communication / 总通信 | `491520000 + 491520000 = 983040000` | 937.50 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.2128` | 2.21x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **98.10%**，测试损失为 **0.0649**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.21x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.050s**。
