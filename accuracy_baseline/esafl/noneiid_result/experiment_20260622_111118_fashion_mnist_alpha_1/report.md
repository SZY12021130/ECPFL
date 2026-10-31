# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260622_111118  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline\esafl\result_fix_pro\experiment_20260622_111118_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **89.51%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.3740 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 2051.94 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 244.43 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 200.47 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 41.04 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.89 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 3984.92 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 1992.53 MB / 119.44 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 1992.39 MB / 81.03 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 39.85 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 39.85 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.50x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.035 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 6250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 500 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334290 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 3343 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.72 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 119.44 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 81.03 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

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
| 1 | 81.13% | 0.6634 | 4.25s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.027s | 10.50x |
| 2 | 84.76% | 0.4212 | 4.34s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 3 | 86.01% | 0.3802 | 4.20s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.026s | 10.50x |
| 4 | 86.90% | 0.3585 | 4.34s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.027s | 10.50x |
| 5 | 87.38% | 0.3449 | 4.06s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.028s | 10.50x |
| 6 | 87.77% | 0.3348 | 4.36s | 2.39s | 1.62s | 79.66 MB | 5 | 5 | 0.027s | 10.50x |
| 7 | 88.13% | 0.3296 | 4.33s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.027s | 10.50x |
| 8 | 88.41% | 0.3263 | 4.24s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.027s | 10.50x |
| 9 | 88.69% | 0.3242 | 4.14s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.028s | 10.50x |
| 10 | 88.74% | 0.3224 | 4.36s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 11 | 88.72% | 0.3193 | 4.77s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 12 | 88.98% | 0.3172 | 6.13s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 13 | 89.06% | 0.3156 | 5.98s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 14 | 89.06% | 0.3148 | 5.99s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.028s | 10.50x |
| 15 | 89.18% | 0.3156 | 5.88s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.028s | 10.50x |
| 16 | 89.19% | 0.3159 | 6.41s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.029s | 10.50x |
| 17 | 89.25% | 0.3181 | 4.74s | 2.39s | 1.62s | 79.72 MB | 5 | 5 | 0.028s | 10.50x |
| 18 | 89.38% | 0.3170 | 4.36s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 19 | 89.41% | 0.3193 | 4.16s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.028s | 10.50x |
| 20 | 89.48% | 0.3189 | 4.21s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 21 | 89.39% | 0.3227 | 4.15s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 22 | 89.45% | 0.3239 | 4.10s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 23 | 89.44% | 0.3279 | 4.32s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.026s | 10.50x |
| 24 | 89.46% | 0.3236 | 4.38s | 2.39s | 1.62s | 79.72 MB | 5 | 5 | 0.027s | 10.50x |
| 25 | 89.49% | 0.3286 | 4.50s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.028s | 10.50x |
| 26 | 89.58% | 0.3272 | 4.41s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 27 | 89.50% | 0.3293 | 4.38s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.025s | 10.50x |
| 28 | 89.54% | 0.3327 | 4.43s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.026s | 10.50x |
| 29 | 89.68% | 0.3310 | 4.66s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.027s | 10.50x |
| 30 | 89.58% | 0.3259 | 4.75s | 2.39s | 1.62s | 79.69 MB | 5 | 5 | 0.026s | 10.50x |
| 31 | 89.68% | 0.3331 | 4.43s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 32 | 89.54% | 0.3356 | 4.43s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 33 | 89.58% | 0.3355 | 4.10s | 2.39s | 1.62s | 79.67 MB | 5 | 5 | 0.026s | 10.50x |
| 34 | 89.60% | 0.3367 | 5.90s | 2.39s | 1.62s | 79.67 MB | 5 | 5 | 0.027s | 10.50x |
| 35 | 89.47% | 0.3429 | 6.02s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.027s | 10.50x |
| 36 | 89.66% | 0.3428 | 6.25s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.028s | 10.50x |
| 37 | 89.51% | 0.3479 | 4.44s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.027s | 10.50x |
| 38 | 89.56% | 0.3505 | 6.00s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.026s | 10.50x |
| 39 | 89.51% | 0.3454 | 6.08s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 40 | 89.53% | 0.3542 | 6.09s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 41 | 89.68% | 0.3557 | 5.64s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.029s | 10.50x |
| 42 | 89.67% | 0.3550 | 6.23s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.028s | 10.50x |
| 43 | 89.76% | 0.3553 | 5.71s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |
| 44 | 89.63% | 0.3586 | 6.70s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.027s | 10.50x |
| 45 | 89.62% | 0.3647 | 5.78s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 46 | 89.57% | 0.3674 | 4.46s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.027s | 10.50x |
| 47 | 89.53% | 0.3661 | 4.27s | 2.39s | 1.62s | 79.68 MB | 5 | 5 | 0.025s | 10.50x |
| 48 | 89.49% | 0.3664 | 4.27s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.026s | 10.50x |
| 49 | 89.42% | 0.3721 | 4.31s | 2.39s | 1.62s | 79.71 MB | 5 | 5 | 0.029s | 10.50x |
| 50 | 89.51% | 0.3740 | 4.03s | 2.39s | 1.62s | 79.70 MB | 5 | 5 | 0.026s | 10.50x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 2089315285` | 1992.53 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 6250` | 6250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 500` | 500 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `2089315285/6250 = 334290` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(5)` | 326.53 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 2089315285` | 1992.53 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 2089171825` | 1992.39 MB |
| 9 | Total Communication / 总通信 | `2089315285 + 2089171825 = 4178487110` | 3984.92 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 10.5028` | 10.50x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **89.51%**，测试损失为 **0.3740**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **10.50x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.035s**。
