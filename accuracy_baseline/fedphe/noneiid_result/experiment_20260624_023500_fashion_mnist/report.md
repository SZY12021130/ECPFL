# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260624_023500  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline/fedphe/noneiid_result\experiment_20260624_023500_fashion_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **79.29%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.8067 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1752.72 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 221.63 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 167.13 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 35.05 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.43 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4044.46 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 398.50 MB / 22.16 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3645.96 MB / 144.97 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 7.97 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 72.92 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.09x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.008 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 1250 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 100 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334285 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 30466 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.82 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 22.16 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 144.97 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 9 | 9 | 31013 kbps | 30222 kbps |
| 1 | 5 | 5 | 339099 kbps | 472285 kbps |
| 2 | 6 | 6 | 254789 kbps | 181815 kbps |
| 3 | 21 | 21 | 96962 kbps | 99657 kbps |
| 4 | 20 | 20 | 39759 kbps | 18071 kbps |
| 5 | 10 | 10 | 27438 kbps | 26345 kbps |
| 6 | 7 | 7 | 105349 kbps | 21922 kbps |
| 7 | 7 | 7 | 269298 kbps | 67032 kbps |
| 8 | 24 | 24 | 28807 kbps | 12061 kbps |
| 9 | 33 | 33 | 54690 kbps | 5467 kbps |
| 10 | 24 | 24 | 41651 kbps | 44816 kbps |
| 11 | 46 | 46 | 8057 kbps | 8610 kbps |
| 12 | 44 | 44 | 279465 kbps | 261900 kbps |
| 13 | 48 | 48 | 227204 kbps | 21076 kbps |
| 14 | 20 | 20 | 93105 kbps | 23265 kbps |
| 15 | 10 | 10 | 29282 kbps | 27951 kbps |
| 16 | 17 | 17 | 123339 kbps | 36087 kbps |
| 17 | 36 | 36 | 17150 kbps | 14397 kbps |
| 18 | 21 | 21 | 93249 kbps | 6653 kbps |
| 19 | 25 | 25 | 144829 kbps | 67399 kbps |
| 20 | 19 | 19 | 103970 kbps | 9934 kbps |
| 21 | 24 | 24 | 110526 kbps | 11922 kbps |
| 22 | 35 | 35 | 650580 kbps | 37402 kbps |
| 23 | 31 | 31 | 231919 kbps | 22700 kbps |
| 24 | 27 | 27 | 329695 kbps | 19824 kbps |
| 25 | 6 | 6 | 574578 kbps | 336917 kbps |
| 26 | 17 | 17 | 221339 kbps | 145221 kbps |
| 27 | 42 | 42 | 46710 kbps | 7069 kbps |
| 28 | 23 | 23 | 11993 kbps | 10052 kbps |
| 29 | 21 | 21 | 63094 kbps | 25450 kbps |
| 30 | 37 | 37 | 337046 kbps | 27064 kbps |
| 31 | 44 | 44 | 70923 kbps | 10978 kbps |
| 32 | 32 | 32 | 25433 kbps | 11948 kbps |
| 33 | 17 | 17 | 77720 kbps | 63169 kbps |
| 34 | 35 | 35 | 27070 kbps | 39392 kbps |
| 35 | 30 | 30 | 21428 kbps | 18340 kbps |
| 36 | 26 | 26 | 344229 kbps | 18358 kbps |
| 37 | 27 | 27 | 23038 kbps | 16389 kbps |
| 38 | 21 | 21 | 92157 kbps | 63300 kbps |
| 39 | 12 | 12 | 64407 kbps | 17650 kbps |
| 40 | 44 | 44 | 10447 kbps | 8379 kbps |
| 41 | 47 | 47 | 310817 kbps | 335451 kbps |
| 42 | 21 | 21 | 406173 kbps | 70384 kbps |
| 43 | 8 | 8 | 18551 kbps | 31260 kbps |
| 44 | 41 | 41 | 115313 kbps | 84637 kbps |
| 45 | 50 | 50 | 157061 kbps | 17346 kbps |
| 46 | 11 | 11 | 53345 kbps | 92982 kbps |
| 47 | 32 | 32 | 31064 kbps | 34562 kbps |
| 48 | 26 | 26 | 523223 kbps | 102692 kbps |
| 49 | 11 | 11 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 15.94% | 2.3419 | 4.86s | 0.48s | 3.15s | 87.68 MB | 1 | 1 | 0.008s | 2.09x |
| 2 | 16.91% | 2.2634 | 3.69s | 0.39s | 2.05s | 85.32 MB | 1 | 1 | 0.011s | 2.09x |
| 3 | 46.54% | 1.8841 | 3.88s | 0.39s | 2.28s | 82.96 MB | 1 | 1 | 0.008s | 2.09x |
| 4 | 53.63% | 1.6573 | 4.41s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 5 | 58.79% | 1.5556 | 4.45s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 6 | 62.17% | 1.4966 | 3.64s | 0.39s | 2.28s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 7 | 62.55% | 1.4179 | 4.41s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 8 | 64.69% | 1.3676 | 4.35s | 0.31s | 2.95s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 9 | 66.25% | 1.3204 | 4.43s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 10 | 67.85% | 1.2797 | 4.40s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 11 | 68.04% | 1.2615 | 4.49s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 12 | 69.11% | 1.2224 | 4.73s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 13 | 69.90% | 1.1961 | 4.50s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 14 | 70.89% | 1.1586 | 4.49s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 15 | 70.74% | 1.1558 | 4.39s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 16 | 71.91% | 1.1606 | 4.44s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 17 | 73.45% | 1.0939 | 4.13s | 0.48s | 2.28s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 18 | 73.55% | 1.1011 | 4.32s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 19 | 73.71% | 1.0711 | 4.34s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 20 | 74.36% | 1.0527 | 4.31s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 21 | 73.70% | 1.0581 | 4.36s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 22 | 74.20% | 1.0191 | 4.75s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 23 | 74.44% | 1.0229 | 4.35s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 24 | 75.66% | 1.0125 | 4.35s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 25 | 75.00% | 1.0040 | 4.48s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 26 | 75.39% | 0.9751 | 4.36s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 27 | 76.39% | 0.9569 | 4.81s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 28 | 75.96% | 0.9534 | 4.58s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 29 | 76.79% | 0.9522 | 4.36s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 30 | 77.06% | 0.9255 | 4.51s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 31 | 76.98% | 0.9243 | 4.43s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 32 | 76.59% | 0.9258 | 4.78s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 33 | 77.68% | 0.8968 | 4.71s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 34 | 77.92% | 0.8852 | 4.46s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 35 | 78.40% | 0.8927 | 4.60s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.012s | 2.09x |
| 36 | 78.56% | 0.8683 | 4.40s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 37 | 78.47% | 0.8661 | 4.78s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 38 | 78.29% | 0.8639 | 4.41s | 0.48s | 2.95s | 80.60 MB | 1 | 1 | 0.009s | 2.09x |
| 39 | 78.55% | 0.8583 | 4.34s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 40 | 78.13% | 0.8622 | 4.76s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 41 | 77.72% | 0.8571 | 4.44s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |
| 42 | 78.73% | 0.8488 | 4.68s | 0.39s | 2.95s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 43 | 78.51% | 0.8411 | 4.50s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 44 | 78.85% | 0.8343 | 4.31s | 0.39s | 2.95s | 80.60 MB | 1 | 1 | 0.008s | 2.09x |
| 45 | 78.78% | 0.8299 | 4.34s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.007s | 2.09x |
| 46 | 79.13% | 0.8213 | 4.32s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 47 | 79.50% | 0.8128 | 4.48s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 48 | 79.79% | 0.8080 | 4.37s | 0.37s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 49 | 78.49% | 0.8105 | 4.45s | 0.31s | 2.95s | 80.61 MB | 1 | 1 | 0.009s | 2.09x |
| 50 | 79.29% | 0.8067 | 4.53s | 0.48s | 2.95s | 80.61 MB | 1 | 1 | 0.008s | 2.09x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 417856068` | 398.50 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 1250` | 1250 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 100` | 100 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `417856068/1250 = 334285` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.57 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 417856068` | 398.50 MB |
| 8 | Total Download / 总下载 | `model_size(160040) * selected(1250) = 3823065025` | 3645.96 MB |
| 9 | Total Communication / 总通信 | `417856068 + 3823065025 = 4240921093` | 4044.46 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.0888` | 2.09x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **79.29%**，测试损失为 **0.8067**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.09x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.008s**。
