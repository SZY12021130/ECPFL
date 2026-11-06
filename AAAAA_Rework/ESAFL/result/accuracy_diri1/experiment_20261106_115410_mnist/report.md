# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20261106_115410  
**Output Directory / 输出目录:** `AAAAA_Rework/ESAFL/result/accuracy_diri1\experiment_20261106_115410_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | mnist | 训练数据集名称 |
| Model / 模型 | lenet | 神经网络架构 |
| Num Clients / 客户端数 | 50 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 2 | 联邦学习总轮数 |
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
| Final Test Accuracy / 最终测试准确率 | **55.92%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 1.3550 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 40.18 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 3.66 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 2.46 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 20.09 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 1.83 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 68.75 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 34.38 MB / 1.88 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 34.38 MB / 0.59 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 17.19 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 17.19 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 4.06x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.100 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 550 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 22 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 65536 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 32768 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.74 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1.88 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 0.59 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 1 | 11 | 31013 kbps | 30222 kbps |
| 1 | 0 | 0 | 339099 kbps | 472285 kbps |
| 2 | 1 | 11 | 254789 kbps | 181815 kbps |
| 3 | 1 | 11 | 96962 kbps | 99657 kbps |
| 4 | 2 | 22 | 39759 kbps | 18071 kbps |
| 5 | 0 | 0 | 27438 kbps | 26345 kbps |
| 6 | 1 | 11 | 105349 kbps | 21922 kbps |
| 7 | 0 | 0 | 269298 kbps | 67032 kbps |
| 8 | 1 | 11 | 28807 kbps | 12061 kbps |
| 9 | 1 | 11 | 54690 kbps | 5467 kbps |
| 10 | 1 | 11 | 41651 kbps | 44816 kbps |
| 11 | 0 | 0 | 8057 kbps | 8610 kbps |
| 12 | 2 | 22 | 279465 kbps | 261900 kbps |
| 13 | 1 | 11 | 227204 kbps | 21076 kbps |
| 14 | 1 | 11 | 93105 kbps | 23265 kbps |
| 15 | 1 | 11 | 29282 kbps | 27951 kbps |
| 16 | 1 | 11 | 123339 kbps | 36087 kbps |
| 17 | 1 | 11 | 17150 kbps | 14397 kbps |
| 18 | 1 | 11 | 93249 kbps | 6653 kbps |
| 19 | 1 | 11 | 144829 kbps | 67399 kbps |
| 20 | 1 | 11 | 103970 kbps | 9934 kbps |
| 21 | 1 | 11 | 110526 kbps | 11922 kbps |
| 22 | 1 | 11 | 650580 kbps | 37402 kbps |
| 23 | 1 | 11 | 231919 kbps | 22700 kbps |
| 24 | 2 | 22 | 329695 kbps | 19824 kbps |
| 25 | 1 | 11 | 574578 kbps | 336917 kbps |
| 26 | 2 | 22 | 221339 kbps | 145221 kbps |
| 27 | 0 | 0 | 46710 kbps | 7069 kbps |
| 28 | 0 | 0 | 11993 kbps | 10052 kbps |
| 29 | 1 | 11 | 63094 kbps | 25450 kbps |
| 30 | 2 | 22 | 337046 kbps | 27064 kbps |
| 31 | 2 | 22 | 70923 kbps | 10978 kbps |
| 32 | 2 | 22 | 25433 kbps | 11948 kbps |
| 33 | 1 | 11 | 77720 kbps | 63169 kbps |
| 34 | 1 | 11 | 27070 kbps | 39392 kbps |
| 35 | 0 | 0 | 21428 kbps | 18340 kbps |
| 36 | 0 | 0 | 344229 kbps | 18358 kbps |
| 37 | 1 | 11 | 23038 kbps | 16389 kbps |
| 38 | 1 | 11 | 92157 kbps | 63300 kbps |
| 39 | 2 | 22 | 64407 kbps | 17650 kbps |
| 40 | 0 | 0 | 10447 kbps | 8379 kbps |
| 41 | 1 | 11 | 310817 kbps | 335451 kbps |
| 42 | 1 | 11 | 406173 kbps | 70384 kbps |
| 43 | 0 | 0 | 18551 kbps | 31260 kbps |
| 44 | 1 | 11 | 115313 kbps | 84637 kbps |
| 45 | 2 | 22 | 157061 kbps | 17346 kbps |
| 46 | 2 | 22 | 53345 kbps | 92982 kbps |
| 47 | 1 | 11 | 31064 kbps | 34562 kbps |
| 48 | 1 | 11 | 523223 kbps | 102692 kbps |
| 49 | 1 | 11 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 47.93% | 1.5461 | 1.95s | 1.03s | 0.33s | 34.38 MB | 11 | 11 | 0.104s | 4.06x |
| 2 | 55.92% | 1.3550 | 1.71s | 0.85s | 0.26s | 34.38 MB | 11 | 11 | 0.098s | 4.06x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 8885200` | 8.47 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 36044800` | 34.38 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 550` | 550 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 22` | 22 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `36044800/550 = 65536` | 64.00 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(11)` | 326.55 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 36044800` | 34.38 MB |
| 8 | Total Download / 总下载 | `model_size(177704) * selected(50) = 36044800` | 34.38 MB |
| 9 | Total Communication / 总通信 | `36044800 + 36044800 = 72089600` | 68.75 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 4.0567` | 4.06x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **2** 轮训练，最终测试准确率达到 **55.92%**，测试损失为 **1.3550**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **4.06x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.100s**。
