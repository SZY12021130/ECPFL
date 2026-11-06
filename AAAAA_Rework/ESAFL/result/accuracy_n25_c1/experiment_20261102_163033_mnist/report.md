# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261102_163033  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/accuracy_n25_c1\experiment_20261102_163033_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | mnist | 训练数据集名称 |
| Model / 模型 | lenet | 神经网络架构 |
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
| Final Test Accuracy / 最终测试准确率 | **99.03%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.0380 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 2283.67 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 129.22 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 47.16 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 45.67 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 2.58 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 937.50 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 468.75 MB / 28.10 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 468.75 MB / 19.06 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 9.38 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 9.38 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 2.21x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.071 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 7500 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 300 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 1311 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.78 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 28.10 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 19.06 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 300 | 31013 kbps | 30222 kbps |
| 1 | 50 | 300 | 339099 kbps | 472285 kbps |
| 2 | 50 | 300 | 254789 kbps | 181815 kbps |
| 3 | 50 | 300 | 96962 kbps | 99657 kbps |
| 4 | 50 | 300 | 39759 kbps | 18071 kbps |
| 5 | 50 | 300 | 27438 kbps | 26345 kbps |
| 6 | 50 | 300 | 105349 kbps | 21922 kbps |
| 7 | 50 | 300 | 269298 kbps | 67032 kbps |
| 8 | 50 | 300 | 28807 kbps | 12061 kbps |
| 9 | 50 | 300 | 54690 kbps | 5467 kbps |
| 10 | 50 | 300 | 41651 kbps | 44816 kbps |
| 11 | 50 | 300 | 8057 kbps | 8610 kbps |
| 12 | 50 | 300 | 279465 kbps | 261900 kbps |
| 13 | 50 | 300 | 227204 kbps | 21076 kbps |
| 14 | 50 | 300 | 93105 kbps | 23265 kbps |
| 15 | 50 | 300 | 29282 kbps | 27951 kbps |
| 16 | 50 | 300 | 123339 kbps | 36087 kbps |
| 17 | 50 | 300 | 17150 kbps | 14397 kbps |
| 18 | 50 | 300 | 93249 kbps | 6653 kbps |
| 19 | 50 | 300 | 144829 kbps | 67399 kbps |
| 20 | 50 | 300 | 103970 kbps | 9934 kbps |
| 21 | 50 | 300 | 110526 kbps | 11922 kbps |
| 22 | 50 | 300 | 650580 kbps | 37402 kbps |
| 23 | 50 | 300 | 231919 kbps | 22700 kbps |
| 24 | 50 | 300 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 76.24% | 0.6956 | 3.89s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 2 | 89.01% | 0.3328 | 3.14s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 3 | 83.78% | 0.5239 | 2.81s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.047s | 2.21x |
| 4 | 94.84% | 0.1667 | 2.66s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 5 | 94.97% | 0.1538 | 2.80s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 6 | 95.60% | 0.1547 | 2.84s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 7 | 96.67% | 0.1051 | 2.80s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 8 | 97.47% | 0.0799 | 1.77s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 9 | 97.66% | 0.0689 | 2.76s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 10 | 97.21% | 0.0816 | 2.90s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 11 | 97.61% | 0.0768 | 2.91s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 12 | 98.29% | 0.0560 | 2.87s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 13 | 98.31% | 0.0497 | 2.70s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.048s | 2.21x |
| 14 | 98.23% | 0.0563 | 2.85s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 15 | 97.43% | 0.0916 | 2.96s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 16 | 98.27% | 0.0579 | 2.59s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 17 | 97.98% | 0.0603 | 2.71s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 18 | 98.45% | 0.0482 | 3.09s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 19 | 98.52% | 0.0532 | 2.73s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 20 | 98.45% | 0.0440 | 2.97s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 21 | 98.82% | 0.0423 | 2.84s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 22 | 98.74% | 0.0391 | 2.92s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.051s | 2.21x |
| 23 | 98.88% | 0.0357 | 1.72s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 24 | 98.63% | 0.0445 | 1.76s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.049s | 2.21x |
| 25 | 98.63% | 0.0450 | 1.77s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.050s | 2.21x |
| 26 | 98.65% | 0.0425 | 1.69s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.093s | 2.21x |
| 27 | 98.76% | 0.0404 | 2.77s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.084s | 2.21x |
| 28 | 98.67% | 0.0448 | 2.95s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.090s | 2.21x |
| 29 | 98.75% | 0.0397 | 2.85s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.093s | 2.21x |
| 30 | 98.71% | 0.0403 | 2.84s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.088s | 2.21x |
| 31 | 98.82% | 0.0398 | 1.84s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.088s | 2.21x |
| 32 | 98.82% | 0.0409 | 2.64s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.083s | 2.21x |
| 33 | 98.82% | 0.0392 | 2.82s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.084s | 2.21x |
| 34 | 98.98% | 0.0354 | 2.44s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.092s | 2.21x |
| 35 | 98.96% | 0.0369 | 2.73s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.084s | 2.21x |
| 36 | 99.06% | 0.0345 | 1.76s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.087s | 2.21x |
| 37 | 98.99% | 0.0332 | 2.58s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.085s | 2.21x |
| 38 | 98.06% | 0.0709 | 2.80s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.085s | 2.21x |
| 39 | 98.64% | 0.0462 | 1.92s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.083s | 2.21x |
| 40 | 98.82% | 0.0424 | 1.70s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.082s | 2.21x |
| 41 | 99.04% | 0.0333 | 2.44s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.088s | 2.21x |
| 42 | 99.14% | 0.0320 | 2.72s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.082s | 2.21x |
| 43 | 98.96% | 0.0365 | 2.81s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.082s | 2.21x |
| 44 | 99.01% | 0.0330 | 2.59s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.083s | 2.21x |
| 45 | 98.94% | 0.0389 | 2.44s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.083s | 2.21x |
| 46 | 99.04% | 0.0335 | 2.56s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.085s | 2.21x |
| 47 | 98.91% | 0.0431 | 1.75s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.084s | 2.21x |
| 48 | 98.92% | 0.0406 | 2.32s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.086s | 2.21x |
| 49 | 98.88% | 0.0436 | 2.69s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.086s | 2.21x |
| 50 | 99.03% | 0.0380 | 2.80s | 0.56s | 0.38s | 18.75 MB | 6 | 6 | 0.090s | 2.21x |

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
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(6)` | 326.53 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 491520000` | 468.75 MB |
| 8 | Total Download / 总下载 | `model_size(177704) * selected(1250) = 491520000` | 468.75 MB |
| 9 | Total Communication / 总通信 | `491520000 + 491520000 = 983040000` | 937.50 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 2.2128` | 2.21x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **99.03%**，测试损失为 **0.0380**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **2.21x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.071s**。
