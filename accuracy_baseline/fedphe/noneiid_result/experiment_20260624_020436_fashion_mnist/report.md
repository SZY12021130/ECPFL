# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260624_020436  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline/fedphe/noneiid_result\experiment_20260624_020436_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **78.54%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.8229 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1776.29 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 175.90 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 130.72 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 35.53 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 3.52 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4043.74 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 398.51 MB / 22.25 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3645.24 MB / 108.47 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.97 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 72.90 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.09x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.008 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 100 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334291 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 30459 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.70 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 22.25 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 108.47 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 10 | 10 | 31013 kbps | 30222 kbps |
| 1 | 37 | 37 | 339099 kbps | 472285 kbps |
| 2 | 8 | 8 | 254789 kbps | 181815 kbps |
| 3 | 38 | 38 | 96962 kbps | 99657 kbps |
| 4 | 17 | 17 | 39759 kbps | 18071 kbps |
| 5 | 20 | 20 | 27438 kbps | 26345 kbps |
| 6 | 27 | 27 | 105349 kbps | 21922 kbps |
| 7 | 26 | 26 | 269298 kbps | 67032 kbps |
| 8 | 10 | 10 | 28807 kbps | 12061 kbps |
| 9 | 38 | 38 | 54690 kbps | 5467 kbps |
| 10 | 6 | 6 | 41651 kbps | 44816 kbps |
| 11 | 19 | 19 | 8057 kbps | 8610 kbps |
| 12 | 50 | 50 | 279465 kbps | 261900 kbps |
| 13 | 31 | 31 | 227204 kbps | 21076 kbps |
| 14 | 33 | 33 | 93105 kbps | 23265 kbps |
| 15 | 22 | 22 | 29282 kbps | 27951 kbps |
| 16 | 50 | 50 | 123339 kbps | 36087 kbps |
| 17 | 34 | 34 | 17150 kbps | 14397 kbps |
| 18 | 17 | 17 | 93249 kbps | 6653 kbps |
| 19 | 13 | 13 | 144829 kbps | 67399 kbps |
| 20 | 28 | 28 | 103970 kbps | 9934 kbps |
| 21 | 15 | 15 | 110526 kbps | 11922 kbps |
| 22 | 26 | 26 | 650580 kbps | 37402 kbps |
| 23 | 34 | 34 | 231919 kbps | 22700 kbps |
| 24 | 16 | 16 | 329695 kbps | 19824 kbps |
| 25 | 44 | 44 | 574578 kbps | 336917 kbps |
| 26 | 30 | 30 | 221339 kbps | 145221 kbps |
| 27 | 16 | 16 | 46710 kbps | 7069 kbps |
| 28 | 11 | 11 | 11993 kbps | 10052 kbps |
| 29 | 10 | 10 | 63094 kbps | 25450 kbps |
| 30 | 21 | 21 | 337046 kbps | 27064 kbps |
| 31 | 20 | 20 | 70923 kbps | 10978 kbps |
| 32 | 38 | 38 | 25433 kbps | 11948 kbps |
| 33 | 17 | 17 | 77720 kbps | 63169 kbps |
| 34 | 47 | 47 | 27070 kbps | 39392 kbps |
| 35 | 30 | 30 | 21428 kbps | 18340 kbps |
| 36 | 22 | 22 | 344229 kbps | 18358 kbps |
| 37 | 40 | 40 | 23038 kbps | 16389 kbps |
| 38 | 13 | 13 | 92157 kbps | 63300 kbps |
| 39 | 21 | 21 | 64407 kbps | 17650 kbps |
| 40 | 11 | 11 | 10447 kbps | 8379 kbps |
| 41 | 18 | 18 | 310817 kbps | 335451 kbps |
| 42 | 11 | 11 | 406173 kbps | 70384 kbps |
| 43 | 17 | 17 | 18551 kbps | 31260 kbps |
| 44 | 25 | 25 | 115313 kbps | 84637 kbps |
| 45 | 46 | 46 | 157061 kbps | 17346 kbps |
| 46 | 35 | 35 | 53345 kbps | 92982 kbps |
| 47 | 28 | 28 | 31064 kbps | 34562 kbps |
| 48 | 32 | 32 | 523223 kbps | 102692 kbps |
| 49 | 22 | 22 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 12.91% | 2.3418 | 4.68s | 0.37s | 3.15s | 87.66 MB | 1 | 1 | 0.009s | 2.09x |
| 2 | 15.97% | 2.2596 | 2.46s | 0.48s | 1.32s | 85.31 MB | 1 | 1 | 0.008s | 2.09x |
| 3 | 45.83% | 1.8858 | 3.21s | 0.48s | 1.98s | 82.95 MB | 1 | 1 | 0.009s | 2.09x |
| 4 | 53.64% | 1.6820 | 2.64s | 0.48s | 1.28s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 5 | 56.10% | 1.6043 | 4.53s | 0.30s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 6 | 61.03% | 1.5008 | 3.69s | 0.39s | 2.28s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 7 | 62.05% | 1.4311 | 2.81s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.010s | 2.09x |
| 8 | 63.97% | 1.4061 | 4.22s | 0.30s | 2.95s | 80.59 MB | 1 | 1 | 0.010s | 2.09x |
| 9 | 64.80% | 1.3528 | 3.04s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 10 | 63.38% | 1.3282 | 4.14s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 11 | 67.33% | 1.2960 | 3.01s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 12 | 67.78% | 1.2720 | 3.44s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 13 | 68.05% | 1.2598 | 3.67s | 0.48s | 1.98s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 14 | 68.57% | 1.2672 | 4.14s | 0.30s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 15 | 70.60% | 1.1786 | 3.44s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 16 | 70.44% | 1.1592 | 4.19s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 17 | 70.18% | 1.1459 | 2.66s | 0.26s | 1.28s | 80.59 MB | 1 | 1 | 0.007s | 2.09x |
| 18 | 71.67% | 1.1366 | 4.50s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 19 | 71.82% | 1.0853 | 4.18s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 20 | 73.02% | 1.0979 | 2.78s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.007s | 2.09x |
| 21 | 73.40% | 1.0396 | 4.21s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 22 | 73.10% | 1.0804 | 4.15s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 23 | 75.01% | 1.0240 | 2.51s | 0.48s | 1.09s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 24 | 74.20% | 1.0360 | 3.26s | 0.48s | 1.98s | 80.59 MB | 1 | 1 | 0.010s | 2.09x |
| 25 | 75.31% | 1.0038 | 3.70s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 26 | 75.49% | 1.0103 | 2.68s | 0.39s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 27 | 74.43% | 1.0058 | 3.19s | 0.39s | 1.98s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 28 | 76.26% | 0.9622 | 2.66s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.007s | 2.09x |
| 29 | 74.77% | 0.9887 | 3.30s | 0.48s | 1.98s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 30 | 76.52% | 0.9441 | 3.45s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 31 | 76.58% | 0.9374 | 2.96s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 32 | 76.00% | 0.9367 | 2.96s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 33 | 77.21% | 0.9430 | 4.26s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 34 | 77.34% | 0.9402 | 3.00s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 35 | 77.11% | 0.9330 | 4.36s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 36 | 77.49% | 0.8981 | 2.76s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 37 | 78.05% | 0.8874 | 4.52s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 38 | 77.25% | 0.9030 | 4.28s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 39 | 77.42% | 0.8869 | 2.78s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 40 | 78.19% | 0.8778 | 2.74s | 0.48s | 1.39s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 41 | 78.65% | 0.8680 | 4.22s | 0.31s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 42 | 78.12% | 0.8603 | 3.48s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 43 | 78.52% | 0.8510 | 3.58s | 0.48s | 2.28s | 80.59 MB | 1 | 1 | 0.010s | 2.09x |
| 44 | 78.92% | 0.8405 | 2.88s | 0.48s | 1.28s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 45 | 79.00% | 0.8303 | 4.21s | 0.30s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 46 | 79.93% | 0.8021 | 2.73s | 0.39s | 1.39s | 80.59 MB | 1 | 1 | 0.010s | 2.09x |
| 47 | 78.91% | 0.8270 | 4.16s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 48 | 79.39% | 0.8253 | 4.18s | 0.48s | 2.95s | 80.59 MB | 1 | 1 | 0.008s | 2.09x |
| 49 | 79.63% | 0.8181 | 3.12s | 0.48s | 1.98s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |
| 50 | 78.54% | 0.8229 | 4.18s | 0.37s | 2.95s | 80.59 MB | 1 | 1 | 0.009s | 2.09x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 417863588` | 398.51 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1250` | 1250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 100` | 100 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `417863588/1250 = 334291` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.67 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 417863588` | 398.51 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 3822307725` | 3645.24 MB |
| 9 | Total Communication / 总通信 | `417863588 + 3822307725 = 4240171313` | 4043.74 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0888` | 2.09x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **78.54%**，测试损失为 **0.8229**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.09x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.008s**。
