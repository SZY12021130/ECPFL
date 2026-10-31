# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260624_005846  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline/fedphe/noneiid_result\experiment_20260624_005846_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **66.10%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 1.6163 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1857.55 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 206.19 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 153.64 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 37.15 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.12 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4042.71 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 398.49 MB / 22.15 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3644.22 MB / 131.49 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.97 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 72.88 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.09x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.008 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 100 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334282 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 30451 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.56 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 22.15 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 131.49 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 18 | 18 | 31013 kbps | 30222 kbps |
| 1 | 17 | 17 | 339099 kbps | 472285 kbps |
| 2 | 9 | 9 | 254789 kbps | 181815 kbps |
| 3 | 11 | 11 | 96962 kbps | 99657 kbps |
| 4 | 40 | 40 | 39759 kbps | 18071 kbps |
| 5 | 3 | 3 | 27438 kbps | 26345 kbps |
| 6 | 3 | 3 | 105349 kbps | 21922 kbps |
| 7 | 9 | 9 | 269298 kbps | 67032 kbps |
| 8 | 8 | 8 | 28807 kbps | 12061 kbps |
| 9 | 31 | 31 | 54690 kbps | 5467 kbps |
| 10 | 15 | 15 | 41651 kbps | 44816 kbps |
| 11 | 36 | 36 | 8057 kbps | 8610 kbps |
| 12 | 49 | 49 | 279465 kbps | 261900 kbps |
| 13 | 50 | 50 | 227204 kbps | 21076 kbps |
| 14 | 47 | 47 | 93105 kbps | 23265 kbps |
| 15 | 21 | 21 | 29282 kbps | 27951 kbps |
| 16 | 30 | 30 | 123339 kbps | 36087 kbps |
| 17 | 48 | 48 | 17150 kbps | 14397 kbps |
| 18 | 42 | 42 | 93249 kbps | 6653 kbps |
| 19 | 33 | 33 | 144829 kbps | 67399 kbps |
| 20 | 41 | 41 | 103970 kbps | 9934 kbps |
| 21 | 33 | 33 | 110526 kbps | 11922 kbps |
| 22 | 20 | 20 | 650580 kbps | 37402 kbps |
| 23 | 21 | 21 | 231919 kbps | 22700 kbps |
| 24 | 48 | 48 | 329695 kbps | 19824 kbps |
| 25 | 12 | 12 | 574578 kbps | 336917 kbps |
| 26 | 12 | 12 | 221339 kbps | 145221 kbps |
| 27 | 37 | 37 | 46710 kbps | 7069 kbps |
| 28 | 4 | 4 | 11993 kbps | 10052 kbps |
| 29 | 28 | 28 | 63094 kbps | 25450 kbps |
| 30 | 48 | 48 | 337046 kbps | 27064 kbps |
| 31 | 6 | 6 | 70923 kbps | 10978 kbps |
| 32 | 26 | 26 | 25433 kbps | 11948 kbps |
| 33 | 50 | 50 | 77720 kbps | 63169 kbps |
| 34 | 13 | 13 | 27070 kbps | 39392 kbps |
| 35 | 49 | 49 | 21428 kbps | 18340 kbps |
| 36 | 14 | 14 | 344229 kbps | 18358 kbps |
| 37 | 4 | 4 | 23038 kbps | 16389 kbps |
| 38 | 44 | 44 | 92157 kbps | 63300 kbps |
| 39 | 19 | 19 | 64407 kbps | 17650 kbps |
| 40 | 18 | 18 | 10447 kbps | 8379 kbps |
| 41 | 15 | 15 | 310817 kbps | 335451 kbps |
| 42 | 16 | 16 | 406173 kbps | 70384 kbps |
| 43 | 16 | 16 | 18551 kbps | 31260 kbps |
| 44 | 13 | 13 | 115313 kbps | 84637 kbps |
| 45 | 27 | 27 | 157061 kbps | 17346 kbps |
| 46 | 43 | 43 | 53345 kbps | 92982 kbps |
| 47 | 10 | 10 | 31064 kbps | 34562 kbps |
| 48 | 18 | 18 | 523223 kbps | 102692 kbps |
| 49 | 25 | 25 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 10.36% | 2.3317 | 4.02s | 0.37s | 3.14s | 87.64 MB | 1 | 1 | 0.005s | 2.09x |
| 2 | 24.15% | 2.2739 | 2.62s | 0.48s | 1.32s | 85.29 MB | 1 | 1 | 0.005s | 2.09x |
| 3 | 37.68% | 2.0436 | 2.67s | 0.37s | 1.98s | 82.93 MB | 1 | 1 | 0.006s | 2.09x |
| 4 | 39.68% | 2.0097 | 4.41s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 5 | 41.21% | 1.9843 | 3.58s | 0.39s | 2.28s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 6 | 41.62% | 1.9540 | 3.87s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 7 | 43.48% | 1.9324 | 4.46s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 8 | 46.32% | 1.9142 | 4.39s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 9 | 47.39% | 1.9049 | 3.88s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 10 | 47.23% | 1.8831 | 4.37s | 0.37s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 11 | 49.23% | 1.8700 | 4.00s | 0.37s | 1.39s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 12 | 51.70% | 1.8715 | 4.47s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 13 | 53.65% | 1.8418 | 3.85s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 14 | 52.64% | 1.8529 | 3.83s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 15 | 53.81% | 1.8384 | 3.85s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 16 | 54.37% | 1.8231 | 4.15s | 0.48s | 2.28s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 17 | 54.04% | 1.8131 | 4.47s | 0.37s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 18 | 55.53% | 1.8001 | 5.15s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 19 | 56.28% | 1.8007 | 4.42s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 20 | 57.15% | 1.8017 | 3.66s | 0.48s | 2.28s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 21 | 56.89% | 1.7924 | 4.38s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 22 | 56.53% | 1.7697 | 4.38s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 23 | 57.31% | 1.7777 | 4.64s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 24 | 58.61% | 1.7671 | 3.87s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 25 | 58.48% | 1.7611 | 3.87s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 26 | 59.41% | 1.7469 | 4.58s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 27 | 60.78% | 1.7317 | 4.04s | 0.48s | 1.39s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 28 | 60.93% | 1.7314 | 4.07s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 29 | 59.48% | 1.7317 | 2.64s | 0.48s | 1.39s | 80.57 MB | 1 | 1 | 0.004s | 2.09x |
| 30 | 60.81% | 1.7318 | 4.28s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 31 | 60.52% | 1.7151 | 4.37s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 32 | 61.92% | 1.7136 | 4.16s | 0.48s | 1.98s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 33 | 61.76% | 1.6990 | 3.81s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 34 | 61.76% | 1.7044 | 3.94s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 35 | 61.74% | 1.6914 | 4.26s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 36 | 62.77% | 1.6752 | 4.48s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 37 | 62.39% | 1.6770 | 3.84s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 38 | 62.47% | 1.6799 | 3.81s | 0.39s | 1.39s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 39 | 63.04% | 1.6723 | 3.81s | 0.39s | 2.28s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 40 | 63.62% | 1.6616 | 4.50s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 41 | 63.18% | 1.6641 | 4.17s | 0.48s | 1.39s | 80.57 MB | 1 | 1 | 0.009s | 2.09x |
| 42 | 62.75% | 1.6549 | 4.87s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 43 | 63.48% | 1.6508 | 4.54s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 44 | 63.21% | 1.6408 | 4.40s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 45 | 64.80% | 1.6401 | 4.27s | 0.48s | 1.39s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 46 | 64.78% | 1.6326 | 4.46s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 47 | 64.33% | 1.6249 | 4.54s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 48 | 65.39% | 1.6142 | 4.48s | 0.48s | 2.95s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |
| 49 | 65.08% | 1.6221 | 4.38s | 0.39s | 2.95s | 80.57 MB | 1 | 1 | 0.006s | 2.09x |
| 50 | 66.10% | 1.6163 | 4.25s | 0.39s | 2.28s | 80.57 MB | 1 | 1 | 0.005s | 2.09x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 417852012` | 398.49 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1250` | 1250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 100` | 100 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `417852012/1250 = 334282` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.50 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 417852012` | 398.49 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 3821238575` | 3644.22 MB |
| 9 | Total Communication / 总通信 | `417852012 + 3821238575 = 4239090587` | 4042.71 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0887` | 2.09x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **66.10%**，测试损失为 **1.6163**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.09x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.008s**。
