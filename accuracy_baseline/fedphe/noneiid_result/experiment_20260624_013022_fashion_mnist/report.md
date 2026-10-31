# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260624_013022  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline/fedphe/noneiid_result\experiment_20260624_013022_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **80.94%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.7813 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 2005.88 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 181.07 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 136.80 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 40.12 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 3.62 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4044.43 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 398.50 MB / 19.67 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3645.94 MB / 117.13 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.97 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 72.92 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.09x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.009 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 100 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334284 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 30464 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.73 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 19.67 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 117.13 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 16 | 16 | 31013 kbps | 30222 kbps |
| 1 | 11 | 11 | 339099 kbps | 472285 kbps |
| 2 | 16 | 16 | 254789 kbps | 181815 kbps |
| 3 | 42 | 42 | 96962 kbps | 99657 kbps |
| 4 | 24 | 24 | 39759 kbps | 18071 kbps |
| 5 | 8 | 8 | 27438 kbps | 26345 kbps |
| 6 | 48 | 48 | 105349 kbps | 21922 kbps |
| 7 | 20 | 20 | 269298 kbps | 67032 kbps |
| 8 | 48 | 48 | 28807 kbps | 12061 kbps |
| 9 | 8 | 8 | 54690 kbps | 5467 kbps |
| 10 | 47 | 47 | 41651 kbps | 44816 kbps |
| 11 | 26 | 26 | 8057 kbps | 8610 kbps |
| 12 | 50 | 50 | 279465 kbps | 261900 kbps |
| 13 | 31 | 31 | 227204 kbps | 21076 kbps |
| 14 | 21 | 21 | 93105 kbps | 23265 kbps |
| 15 | 44 | 44 | 29282 kbps | 27951 kbps |
| 16 | 20 | 20 | 123339 kbps | 36087 kbps |
| 17 | 16 | 16 | 17150 kbps | 14397 kbps |
| 18 | 35 | 35 | 93249 kbps | 6653 kbps |
| 19 | 43 | 43 | 144829 kbps | 67399 kbps |
| 20 | 48 | 48 | 103970 kbps | 9934 kbps |
| 21 | 22 | 22 | 110526 kbps | 11922 kbps |
| 22 | 24 | 24 | 650580 kbps | 37402 kbps |
| 23 | 24 | 24 | 231919 kbps | 22700 kbps |
| 24 | 10 | 10 | 329695 kbps | 19824 kbps |
| 25 | 12 | 12 | 574578 kbps | 336917 kbps |
| 26 | 32 | 32 | 221339 kbps | 145221 kbps |
| 27 | 26 | 26 | 46710 kbps | 7069 kbps |
| 28 | 18 | 18 | 11993 kbps | 10052 kbps |
| 29 | 35 | 35 | 63094 kbps | 25450 kbps |
| 30 | 25 | 25 | 337046 kbps | 27064 kbps |
| 31 | 10 | 10 | 70923 kbps | 10978 kbps |
| 32 | 4 | 4 | 25433 kbps | 11948 kbps |
| 33 | 49 | 49 | 77720 kbps | 63169 kbps |
| 34 | 44 | 44 | 27070 kbps | 39392 kbps |
| 35 | 27 | 27 | 21428 kbps | 18340 kbps |
| 36 | 40 | 40 | 344229 kbps | 18358 kbps |
| 37 | 8 | 8 | 23038 kbps | 16389 kbps |
| 38 | 29 | 29 | 92157 kbps | 63300 kbps |
| 39 | 23 | 23 | 64407 kbps | 17650 kbps |
| 40 | 7 | 7 | 10447 kbps | 8379 kbps |
| 41 | 16 | 16 | 310817 kbps | 335451 kbps |
| 42 | 35 | 35 | 406173 kbps | 70384 kbps |
| 43 | 14 | 14 | 18551 kbps | 31260 kbps |
| 44 | 8 | 8 | 115313 kbps | 84637 kbps |
| 45 | 6 | 6 | 157061 kbps | 17346 kbps |
| 46 | 16 | 16 | 53345 kbps | 92982 kbps |
| 47 | 16 | 16 | 31064 kbps | 34562 kbps |
| 48 | 17 | 17 | 523223 kbps | 102692 kbps |
| 49 | 31 | 31 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 15.06% | 2.3315 | 4.35s | 0.39s | 3.15s | 87.68 MB | 1 | 1 | 0.008s | 2.09x |
| 2 | 24.10% | 2.2555 | 3.22s | 0.48s | 2.05s | 85.33 MB | 1 | 1 | 0.010s | 2.09x |
| 3 | 43.76% | 1.9172 | 4.03s | 0.39s | 2.95s | 82.96 MB | 1 | 1 | 0.008s | 2.09x |
| 4 | 51.72% | 1.6965 | 2.93s | 0.39s | 1.98s | 80.60 MB | 1 | 1 | 0.010s | 2.09x |
| 5 | 54.46% | 1.6240 | 3.32s | 0.48s | 1.98s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 6 | 53.85% | 1.6653 | 2.74s | 0.48s | 1.11s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 7 | 59.60% | 1.5090 | 4.11s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 8 | 61.93% | 1.4551 | 4.32s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 9 | 62.86% | 1.4345 | 4.04s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 10 | 61.21% | 1.3872 | 2.86s | 0.39s | 1.11s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 11 | 62.19% | 1.4592 | 3.29s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 12 | 69.61% | 1.3199 | 3.06s | 0.39s | 1.39s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 13 | 68.56% | 1.3574 | 3.30s | 0.39s | 0.88s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 14 | 69.03% | 1.2927 | 4.32s | 0.30s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 15 | 68.99% | 1.3027 | 3.11s | 0.48s | 1.98s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 16 | 71.12% | 1.2535 | 3.22s | 0.37s | 1.98s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 17 | 71.19% | 1.2226 | 3.08s | 0.28s | 1.28s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 18 | 72.77% | 1.2192 | 3.12s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 19 | 72.77% | 1.1935 | 2.74s | 0.39s | 0.88s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 20 | 72.19% | 1.1927 | 4.36s | 0.30s | 2.95s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 21 | 72.47% | 1.1694 | 3.29s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 22 | 72.91% | 1.2008 | 3.15s | 0.39s | 1.98s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 23 | 73.88% | 1.1340 | 4.31s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 24 | 73.28% | 1.1878 | 3.10s | 0.28s | 1.39s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 25 | 73.59% | 1.1535 | 4.00s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 26 | 75.45% | 1.1157 | 4.03s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 27 | 76.98% | 1.1210 | 4.22s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 28 | 76.30% | 1.0606 | 4.07s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 29 | 75.65% | 1.0934 | 2.93s | 0.37s | 1.98s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 30 | 75.66% | 1.0186 | 4.15s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 31 | 77.99% | 0.9476 | 4.03s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 32 | 77.48% | 0.9938 | 4.01s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 33 | 77.96% | 0.9230 | 4.05s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.011s | 2.09x |
| 34 | 77.08% | 0.9849 | 4.13s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 35 | 79.44% | 0.8634 | 4.03s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 36 | 79.10% | 0.9299 | 4.31s | 0.30s | 2.95s | 80.60 MB | 1 | 1 | 0.007s | 2.09x |
| 37 | 81.17% | 0.8582 | 2.94s | 0.39s | 1.98s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 38 | 79.27% | 0.8812 | 3.09s | 0.37s | 1.98s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 39 | 79.89% | 0.8792 | 2.72s | 0.39s | 1.28s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 40 | 79.51% | 0.8481 | 3.99s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 41 | 81.38% | 0.7724 | 3.06s | 0.39s | 1.28s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 42 | 80.83% | 0.7888 | 4.12s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 43 | 80.54% | 0.8761 | 4.12s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 44 | 80.24% | 0.8112 | 4.13s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 45 | 81.27% | 0.8391 | 3.13s | 0.39s | 1.39s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 46 | 79.88% | 0.8077 | 4.37s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.010s | 2.09x |
| 47 | 80.86% | 0.7373 | 4.02s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 48 | 81.26% | 0.7285 | 4.23s | 0.37s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 49 | 81.40% | 0.7978 | 2.87s | 0.39s | 1.98s | 80.60 MB | 1 | 1 | 0.007s | 2.09x |
| 50 | 80.94% | 0.7813 | 2.94s | 0.39s | 1.39s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 417855601` | 398.50 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1250` | 1250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 100` | 100 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `417855601/1250 = 334284` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.48 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 417855601` | 398.50 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 3823041825` | 3645.94 MB |
| 9 | Total Communication / 总通信 | `417855601 + 3823041825 = 4240897426` | 4044.43 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0888` | 2.09x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **80.94%**，测试损失为 **0.7813**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.09x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.009s**。
