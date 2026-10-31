# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260622_022957  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\accuracy_baseline\esafl\test_multikey\experiment_20260622_022957_svhn`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | svhn | 训练数据集名称 |
| Model / 模型 | resnet32 | 神经网络架构 |
| Num Clients / 客户端数 | 25 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 5 | 联邦学习总轮数 |
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
| Final Test Accuracy / 最终测试准确率 | **19.59%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 2.2873 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 710.41 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 194.52 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 228.54 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 142.08 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 38.90 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 4543.02 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 2271.51 MB / 136.15 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 2271.51 MB / 92.39 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 454.30 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 454.30 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.20x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.342 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 7125 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 570 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334295 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 33430 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 845.84 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 136.15 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 92.39 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 5 | 285 | 31013 kbps | 30222 kbps |
| 1 | 5 | 285 | 339099 kbps | 472285 kbps |
| 2 | 5 | 285 | 254789 kbps | 181815 kbps |
| 3 | 5 | 285 | 96962 kbps | 99657 kbps |
| 4 | 5 | 285 | 39759 kbps | 18071 kbps |
| 5 | 5 | 285 | 27438 kbps | 26345 kbps |
| 6 | 5 | 285 | 105349 kbps | 21922 kbps |
| 7 | 5 | 285 | 269298 kbps | 67032 kbps |
| 8 | 5 | 285 | 28807 kbps | 12061 kbps |
| 9 | 5 | 285 | 54690 kbps | 5467 kbps |
| 10 | 5 | 285 | 41651 kbps | 44816 kbps |
| 11 | 5 | 285 | 8057 kbps | 8610 kbps |
| 12 | 5 | 285 | 279465 kbps | 261900 kbps |
| 13 | 5 | 285 | 227204 kbps | 21076 kbps |
| 14 | 5 | 285 | 93105 kbps | 23265 kbps |
| 15 | 5 | 285 | 29282 kbps | 27951 kbps |
| 16 | 5 | 285 | 123339 kbps | 36087 kbps |
| 17 | 5 | 285 | 17150 kbps | 14397 kbps |
| 18 | 5 | 285 | 93249 kbps | 6653 kbps |
| 19 | 5 | 285 | 144829 kbps | 67399 kbps |
| 20 | 5 | 285 | 103970 kbps | 9934 kbps |
| 21 | 5 | 285 | 110526 kbps | 11922 kbps |
| 22 | 5 | 285 | 650580 kbps | 37402 kbps |
| 23 | 5 | 285 | 231919 kbps | 22700 kbps |
| 24 | 5 | 285 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 7.59% | 2.3016 | 39.40s | 27.23s | 18.48s | 908.57 MB | 57 | 57 | 0.324s | 10.20x |
| 2 | 7.59% | 2.2984 | 38.75s | 27.23s | 18.48s | 908.62 MB | 57 | 57 | 0.335s | 10.20x |
| 3 | 7.59% | 2.2945 | 38.82s | 27.23s | 18.48s | 908.56 MB | 57 | 57 | 0.329s | 10.20x |
| 4 | 19.59% | 2.2904 | 38.85s | 27.23s | 18.48s | 908.63 MB | 57 | 57 | 0.328s | 10.20x |
| 5 | 19.59% | 2.2873 | 38.69s | 27.23s | 18.48s | 908.64 MB | 57 | 57 | 0.326s | 10.20x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 233453000` | 222.64 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 2381850392` | 2271.51 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 7125` | 7125 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 570` | 570 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `2381850392/7125 = 334295` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(57)` | 326.48 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 2381850392` | 2271.51 MB |
| 8 | Total Download / 总下载 | `model_size(1877480) * selected(125) = 2381849000` | 2271.51 MB |
| 9 | Total Communication / 总通信 | `2381850392 + 2381849000 = 4763699392` | 4543.02 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 10.2027` | 10.20x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **5** 轮训练，最终测试准确率达到 **19.59%**，测试损失为 **2.2873**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **10.20x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.342s**。
