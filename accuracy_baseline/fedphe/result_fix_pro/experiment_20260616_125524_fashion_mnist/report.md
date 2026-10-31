# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260616_125524  
**Output Directory / 输出目录:** `accuracy_baseline/fedphe/result_fix_pro\experiment_20260616_125524_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **79.02%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.8466 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 920.37 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 179.43 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 176.30 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 18.41 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 3.59 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4044.49 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 398.55 MB / 18.78 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3645.94 MB / 128.76 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.97 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 72.92 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.09x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.005 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 100 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334295 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334328 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.83 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 24.46 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 151.84 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 30 | 30 | 31013 kbps | 30222 kbps |
| 1 | 13 | 13 | 339099 kbps | 472285 kbps |
| 2 | 43 | 43 | 254789 kbps | 181815 kbps |
| 3 | 24 | 24 | 96962 kbps | 99657 kbps |
| 4 | 5 | 5 | 39759 kbps | 18071 kbps |
| 5 | 18 | 18 | 27438 kbps | 26345 kbps |
| 6 | 16 | 16 | 105349 kbps | 21922 kbps |
| 7 | 35 | 35 | 269298 kbps | 67032 kbps |
| 8 | 44 | 44 | 28807 kbps | 12061 kbps |
| 9 | 11 | 11 | 54690 kbps | 5467 kbps |
| 10 | 19 | 19 | 41651 kbps | 44816 kbps |
| 11 | 22 | 22 | 8057 kbps | 8610 kbps |
| 12 | 26 | 26 | 279465 kbps | 261900 kbps |
| 13 | 37 | 37 | 227204 kbps | 21076 kbps |
| 14 | 37 | 37 | 93105 kbps | 23265 kbps |
| 15 | 40 | 40 | 29282 kbps | 27951 kbps |
| 16 | 41 | 41 | 123339 kbps | 36087 kbps |
| 17 | 44 | 44 | 17150 kbps | 14397 kbps |
| 18 | 20 | 20 | 93249 kbps | 6653 kbps |
| 19 | 19 | 19 | 144829 kbps | 67399 kbps |
| 20 | 19 | 19 | 103970 kbps | 9934 kbps |
| 21 | 17 | 17 | 110526 kbps | 11922 kbps |
| 22 | 14 | 14 | 650580 kbps | 37402 kbps |
| 23 | 24 | 24 | 231919 kbps | 22700 kbps |
| 24 | 20 | 20 | 329695 kbps | 19824 kbps |
| 25 | 14 | 14 | 574578 kbps | 336917 kbps |
| 26 | 9 | 9 | 221339 kbps | 145221 kbps |
| 27 | 8 | 8 | 46710 kbps | 7069 kbps |
| 28 | 50 | 50 | 11993 kbps | 10052 kbps |
| 29 | 26 | 26 | 63094 kbps | 25450 kbps |
| 30 | 50 | 50 | 337046 kbps | 27064 kbps |
| 31 | 10 | 10 | 70923 kbps | 10978 kbps |
| 32 | 23 | 23 | 25433 kbps | 11948 kbps |
| 33 | 10 | 10 | 77720 kbps | 63169 kbps |
| 34 | 32 | 32 | 27070 kbps | 39392 kbps |
| 35 | 5 | 5 | 21428 kbps | 18340 kbps |
| 36 | 39 | 39 | 344229 kbps | 18358 kbps |
| 37 | 43 | 43 | 23038 kbps | 16389 kbps |
| 38 | 11 | 11 | 92157 kbps | 63300 kbps |
| 39 | 6 | 6 | 64407 kbps | 17650 kbps |
| 40 | 48 | 48 | 10447 kbps | 8379 kbps |
| 41 | 34 | 34 | 310817 kbps | 335451 kbps |
| 42 | 24 | 24 | 406173 kbps | 70384 kbps |
| 43 | 15 | 15 | 18551 kbps | 31260 kbps |
| 44 | 21 | 21 | 115313 kbps | 84637 kbps |
| 45 | 21 | 21 | 157061 kbps | 17346 kbps |
| 46 | 31 | 31 | 53345 kbps | 92982 kbps |
| 47 | 13 | 13 | 31064 kbps | 34562 kbps |
| 48 | 23 | 23 | 523223 kbps | 102692 kbps |
| 49 | 46 | 46 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 12.74% | 2.3389 | 3.97s | 0.39s | 3.15s | 87.69 MB | 1 | 1 | 0.004s | 2.09x |
| 2 | 14.14% | 2.2673 | 3.51s | 0.48s | 2.35s | 85.33 MB | 1 | 1 | 0.005s | 2.09x |
| 3 | 43.53% | 1.9056 | 3.40s | 0.31s | 2.28s | 82.97 MB | 1 | 1 | 0.005s | 2.09x |
| 4 | 52.88% | 1.7049 | 3.80s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 5 | 57.11% | 1.5727 | 3.38s | 0.48s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 6 | 61.87% | 1.5052 | 3.41s | 0.28s | 1.98s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 7 | 58.43% | 1.4560 | 3.40s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 8 | 64.67% | 1.4111 | 3.79s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.006s | 2.09x |
| 9 | 62.51% | 1.3759 | 3.42s | 0.48s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 10 | 63.51% | 1.3686 | 3.80s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 11 | 68.08% | 1.2948 | 3.32s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 12 | 68.23% | 1.2688 | 3.37s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.006s | 2.09x |
| 13 | 66.43% | 1.3085 | 3.54s | 0.48s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 14 | 68.62% | 1.2389 | 3.80s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 15 | 70.05% | 1.2042 | 3.78s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 16 | 72.14% | 1.1824 | 3.40s | 0.37s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 17 | 70.18% | 1.2008 | 3.30s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 18 | 70.26% | 1.1599 | 3.50s | 0.31s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 19 | 75.05% | 1.0982 | 3.80s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 20 | 73.61% | 1.1235 | 3.74s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 21 | 76.14% | 1.0820 | 3.40s | 0.48s | 2.28s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 22 | 73.07% | 1.0911 | 3.39s | 0.31s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 23 | 75.01% | 1.0554 | 3.36s | 0.48s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 24 | 75.80% | 1.0243 | 3.83s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 25 | 76.35% | 1.0269 | 3.51s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 26 | 77.29% | 1.0003 | 3.68s | 0.39s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 27 | 77.15% | 0.9981 | 3.43s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 28 | 75.71% | 1.0087 | 3.80s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 29 | 78.30% | 0.9570 | 3.32s | 0.39s | 2.28s | 80.60 MB | 1 | 1 | 0.004s | 2.09x |
| 30 | 76.57% | 0.9919 | 3.80s | 0.30s | 2.95s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 31 | 76.70% | 0.9795 | 3.82s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 32 | 76.90% | 0.9652 | 3.37s | 0.48s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 33 | 76.69% | 0.9670 | 3.81s | 0.31s | 2.95s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 34 | 78.65% | 0.9149 | 3.80s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 35 | 76.77% | 0.9298 | 3.81s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 36 | 78.89% | 0.9054 | 3.36s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 37 | 79.38% | 0.8899 | 3.32s | 0.39s | 2.28s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |
| 38 | 78.19% | 0.9141 | 3.81s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.004s | 2.09x |
| 39 | 78.27% | 0.8885 | 3.79s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 40 | 78.34% | 0.8972 | 3.74s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 41 | 77.89% | 0.8894 | 3.48s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 42 | 79.29% | 0.8777 | 3.48s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 43 | 79.29% | 0.8652 | 3.39s | 0.31s | 2.28s | 80.60 MB | 1 | 1 | 0.006s | 2.09x |
| 44 | 78.69% | 0.8749 | 3.78s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.004s | 2.09x |
| 45 | 78.76% | 0.8585 | 3.56s | 0.37s | 2.28s | 80.60 MB | 1 | 1 | 0.004s | 2.09x |
| 46 | 78.25% | 0.8792 | 3.80s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 47 | 80.01% | 0.8275 | 3.77s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.004s | 2.09x |
| 48 | 78.74% | 0.8536 | 3.40s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 49 | 79.27% | 0.8292 | 3.39s | 0.31s | 2.28s | 80.61 MB | 1 | 1 | 0.005s | 2.09x |
| 50 | 79.02% | 0.8466 | 3.79s | 0.31s | 2.95s | 80.60 MB | 1 | 1 | 0.005s | 2.09x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 417868381` | 398.51 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1250` | 1250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 100` | 100 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `417868381/1250 = 334295` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.46 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 417868381` | 398.51 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 3823046300` | 3645.94 MB |
| 9 | Total Communication / 总通信 | `417868381 + 3823046300 = 4240914681` | 4044.45 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0888` | 2.09x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **79.02%**，测试损失为 **0.8466**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.09x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.005s**。
