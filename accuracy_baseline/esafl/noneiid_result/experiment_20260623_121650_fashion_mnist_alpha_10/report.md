# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260623_121650  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline/esafl/noneiid_result\experiment_20260623_121650_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **90.10%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.3544 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 2102.81 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 222.73 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 200.48 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 42.06 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.45 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 3985.03 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 1992.54 MB / 119.44 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 1992.49 MB / 81.04 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 39.85 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 39.85 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.50x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.035 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 6250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 500 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334293 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 3344 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.87 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 119.44 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 81.04 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

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
| 1 | 82.57% | 0.5282 | 5.18s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.048s | 10.50x |
| 2 | 85.28% | 0.4065 | 5.22s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.048s | 10.50x |
| 3 | 86.52% | 0.3714 | 5.22s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.048s | 10.50x |
| 4 | 87.40% | 0.3509 | 5.19s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.048s | 10.50x |
| 5 | 87.98% | 0.3371 | 5.20s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 6 | 88.15% | 0.3292 | 5.17s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.048s | 10.50x |
| 7 | 88.43% | 0.3227 | 5.20s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.043s | 10.50x |
| 8 | 88.70% | 0.3180 | 5.19s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 9 | 88.89% | 0.3138 | 5.21s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.046s | 10.50x |
| 10 | 89.12% | 0.3152 | 5.22s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.046s | 10.50x |
| 11 | 89.19% | 0.3115 | 4.99s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.048s | 10.50x |
| 12 | 89.36% | 0.3100 | 5.23s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 13 | 89.49% | 0.3108 | 5.14s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.046s | 10.50x |
| 14 | 89.65% | 0.3096 | 5.19s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 15 | 89.60% | 0.3095 | 5.25s | 2.39s | 1.62s | 79.72 MB | 5 | 5 | 0.051s | 10.50x |
| 16 | 89.69% | 0.3117 | 5.24s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.047s | 10.50x |
| 17 | 89.94% | 0.3099 | 5.04s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.047s | 10.50x |
| 18 | 89.91% | 0.3119 | 4.11s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 19 | 89.96% | 0.3114 | 4.09s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.044s | 10.50x |
| 20 | 89.94% | 0.3130 | 4.01s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.050s | 10.50x |
| 21 | 90.00% | 0.3108 | 4.10s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.050s | 10.50x |
| 22 | 89.92% | 0.3123 | 4.06s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.048s | 10.50x |
| 23 | 90.01% | 0.3127 | 4.12s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 24 | 89.98% | 0.3160 | 4.09s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.048s | 10.50x |
| 25 | 89.99% | 0.3156 | 4.06s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.049s | 10.50x |
| 26 | 90.15% | 0.3182 | 4.08s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.048s | 10.50x |
| 27 | 90.15% | 0.3200 | 4.06s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 28 | 90.15% | 0.3197 | 4.07s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.046s | 10.50x |
| 29 | 90.18% | 0.3180 | 4.07s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.047s | 10.50x |
| 30 | 90.06% | 0.3208 | 4.06s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.046s | 10.50x |
| 31 | 90.13% | 0.3222 | 4.07s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.047s | 10.50x |
| 32 | 90.21% | 0.3241 | 4.06s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.047s | 10.50x |
| 33 | 90.13% | 0.3274 | 4.09s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.046s | 10.50x |
| 34 | 90.17% | 0.3252 | 4.09s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.046s | 10.50x |
| 35 | 90.14% | 0.3295 | 4.08s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 36 | 90.12% | 0.3279 | 4.08s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.051s | 10.50x |
| 37 | 90.16% | 0.3334 | 4.09s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.051s | 10.50x |
| 38 | 90.19% | 0.3355 | 4.09s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.048s | 10.50x |
| 39 | 90.12% | 0.3358 | 4.08s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 40 | 90.14% | 0.3382 | 4.08s | 2.39s | 1.62s | 79.72 MB | 5 | 5 | 0.046s | 10.50x |
| 41 | 90.14% | 0.3410 | 4.11s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.047s | 10.50x |
| 42 | 90.22% | 0.3428 | 4.08s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.046s | 10.50x |
| 43 | 90.18% | 0.3426 | 4.08s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 44 | 90.11% | 0.3439 | 4.08s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.046s | 10.50x |
| 45 | 90.14% | 0.3472 | 4.08s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 46 | 90.21% | 0.3465 | 4.07s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.047s | 10.50x |
| 47 | 90.17% | 0.3457 | 4.09s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.045s | 10.50x |
| 48 | 90.09% | 0.3493 | 4.09s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.046s | 10.50x |
| 49 | 90.27% | 0.3531 | 4.09s | 2.39s | 1.62s | 79.67 MB | 5 | 5 | 0.046s | 10.50x |
| 50 | 90.10% | 0.3544 | 4.08s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.047s | 10.50x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 2089333174` | 1992.54 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 6250` | 6250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 500` | 500 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `2089333174/6250 = 334293` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(5)` | 326.38 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 2089333174` | 1992.54 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 2089273200` | 1992.49 MB |
| 9 | Total Communication / 总通信 | `2089333174 + 2089273200 = 4178606374` | 3985.03 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 10.5029` | 10.50x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **90.10%**，测试损失为 **0.3544**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **10.50x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.035s**。
