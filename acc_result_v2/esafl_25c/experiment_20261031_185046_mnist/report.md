# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261031_185046  
**Output Directory / 输出目录:** `acc_result_v2/esafl_25c\experiment_20261031_185046_mnist`  

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
| Final Test Accuracy / 最终测试准确率 | **95.94%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.3839 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1854.39 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 172.33 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 94.32 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 37.09 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 3.45 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 1875.00 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 937.50 MB / 56.20 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 937.50 MB / 38.13 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 18.75 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 18.75 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 4.43x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.057 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 7500 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 300 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 131072 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 2621 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.82 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 56.20 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 38.13 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

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
| 1 | 31.81% | 2.2138 | 4.23s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.088s | 4.43x |
| 2 | 27.47% | 1.8476 | 4.43s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.086s | 4.43x |
| 3 | 85.66% | 1.2370 | 4.32s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.087s | 4.43x |
| 4 | 89.81% | 0.9653 | 3.08s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 5 | 91.96% | 0.8039 | 2.57s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 6 | 85.14% | 0.8037 | 2.77s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 7 | 91.86% | 0.7011 | 4.58s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 8 | 86.51% | 0.8117 | 4.85s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 9 | 55.96% | 0.9713 | 2.71s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 10 | 91.69% | 0.6214 | 2.90s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.085s | 4.43x |
| 11 | 93.59% | 0.5509 | 2.72s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 12 | 61.91% | 1.0326 | 2.74s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 13 | 92.89% | 0.5733 | 2.74s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 14 | 94.15% | 0.5179 | 2.72s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 15 | 93.61% | 0.5313 | 2.74s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 16 | 94.66% | 0.4951 | 2.94s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 17 | 71.65% | 0.7606 | 2.76s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 18 | 85.93% | 0.6788 | 2.81s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 19 | 94.52% | 0.5384 | 2.69s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 20 | 95.22% | 0.4752 | 2.72s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 21 | 95.12% | 0.4496 | 2.79s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.096s | 4.43x |
| 22 | 95.34% | 0.4289 | 2.50s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 23 | 93.13% | 0.5025 | 2.71s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 24 | 91.87% | 0.5236 | 4.81s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 25 | 95.21% | 0.4713 | 4.67s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.084s | 4.43x |
| 26 | 91.35% | 0.5466 | 4.27s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 27 | 94.66% | 0.4748 | 2.83s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 28 | 95.47% | 0.4415 | 2.74s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 29 | 92.56% | 0.5220 | 3.11s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.078s | 4.43x |
| 30 | 95.24% | 0.4458 | 4.07s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.076s | 4.43x |
| 31 | 95.82% | 0.4094 | 2.57s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.078s | 4.43x |
| 32 | 96.10% | 0.3986 | 2.68s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.077s | 4.43x |
| 33 | 96.13% | 0.3901 | 4.83s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 34 | 96.13% | 0.3826 | 3.53s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.078s | 4.43x |
| 35 | 96.16% | 0.3731 | 3.70s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.077s | 4.43x |
| 36 | 96.16% | 0.3698 | 5.30s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.078s | 4.43x |
| 37 | 94.08% | 0.4511 | 4.89s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 38 | 95.32% | 0.4141 | 4.25s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 39 | 95.77% | 0.3892 | 5.73s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |
| 40 | 96.03% | 0.3751 | 4.81s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 41 | 96.15% | 0.3663 | 5.00s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 42 | 96.10% | 0.3765 | 4.46s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.083s | 4.43x |
| 43 | 95.96% | 0.4011 | 2.76s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.084s | 4.43x |
| 44 | 96.27% | 0.3759 | 2.83s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.082s | 4.43x |
| 45 | 95.22% | 0.4053 | 2.80s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 46 | 95.87% | 0.3805 | 2.74s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 47 | 96.22% | 0.3582 | 2.79s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 48 | 79.75% | 0.7234 | 2.70s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.079s | 4.43x |
| 49 | 95.18% | 0.4175 | 2.75s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.080s | 4.43x |
| 50 | 95.94% | 0.3839 | 2.70s | 1.12s | 0.76s | 37.50 MB | 6 | 6 | 0.081s | 4.43x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 983040000` | 937.50 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 7500` | 7500 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 300` | 300 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `983040000/7500 = 131072` | 128.00 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(6)` | 325.70 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 983040000` | 937.50 MB |
| 8 | Total Download / 总下载 | `model_size(177704) * selected(1250) = 983040000` | 937.50 MB |
| 9 | Total Communication / 总通信 | `983040000 + 983040000 = 1966080000` | 1875.00 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 4.4255` | 4.43x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **95.94%**，测试损失为 **0.3839**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **4.43x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.057s**。
