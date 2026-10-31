# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260616_124019  
**Output Directory / 输出目录:** `accuracy_baseline/fedphe/result_fix_pro\experiment_20260616_124019_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | mnist | 训练数据集名称 |
| Model / 模型 | lenet | 神经网络架构 |
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
| Final Test Accuracy / 最终测试准确率 | **98.69%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.0418 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 878.55 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 201.50 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 179.41 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 17.57 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 4.03 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 3930.45 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 797.03 MB / 43.92 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 3133.42 MB / 126.38 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 15.94 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 62.67 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 3.76x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.008 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 2500 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 200 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334283 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334297 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 1691.63 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 48.92 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 130.50 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 9 | 18 | 31013 kbps | 30222 kbps |
| 1 | 25 | 50 | 339099 kbps | 472285 kbps |
| 2 | 22 | 44 | 254789 kbps | 181815 kbps |
| 3 | 27 | 54 | 96962 kbps | 99657 kbps |
| 4 | 47 | 94 | 39759 kbps | 18071 kbps |
| 5 | 11 | 22 | 27438 kbps | 26345 kbps |
| 6 | 19 | 38 | 105349 kbps | 21922 kbps |
| 7 | 40 | 80 | 269298 kbps | 67032 kbps |
| 8 | 15 | 30 | 28807 kbps | 12061 kbps |
| 9 | 31 | 62 | 54690 kbps | 5467 kbps |
| 10 | 12 | 24 | 41651 kbps | 44816 kbps |
| 11 | 50 | 100 | 8057 kbps | 8610 kbps |
| 12 | 38 | 76 | 279465 kbps | 261900 kbps |
| 13 | 13 | 26 | 227204 kbps | 21076 kbps |
| 14 | 25 | 50 | 93105 kbps | 23265 kbps |
| 15 | 50 | 100 | 29282 kbps | 27951 kbps |
| 16 | 17 | 34 | 123339 kbps | 36087 kbps |
| 17 | 28 | 56 | 17150 kbps | 14397 kbps |
| 18 | 40 | 80 | 93249 kbps | 6653 kbps |
| 19 | 41 | 82 | 144829 kbps | 67399 kbps |
| 20 | 18 | 36 | 103970 kbps | 9934 kbps |
| 21 | 38 | 76 | 110526 kbps | 11922 kbps |
| 22 | 27 | 54 | 650580 kbps | 37402 kbps |
| 23 | 17 | 34 | 231919 kbps | 22700 kbps |
| 24 | 24 | 48 | 329695 kbps | 19824 kbps |
| 25 | 46 | 92 | 574578 kbps | 336917 kbps |
| 26 | 44 | 88 | 221339 kbps | 145221 kbps |
| 27 | 15 | 30 | 46710 kbps | 7069 kbps |
| 28 | 25 | 50 | 11993 kbps | 10052 kbps |
| 29 | 27 | 54 | 63094 kbps | 25450 kbps |
| 30 | 43 | 86 | 337046 kbps | 27064 kbps |
| 31 | 23 | 46 | 70923 kbps | 10978 kbps |
| 32 | 35 | 70 | 25433 kbps | 11948 kbps |
| 33 | 13 | 26 | 77720 kbps | 63169 kbps |
| 34 | 22 | 44 | 27070 kbps | 39392 kbps |
| 35 | 14 | 28 | 21428 kbps | 18340 kbps |
| 36 | 7 | 14 | 344229 kbps | 18358 kbps |
| 37 | 32 | 64 | 23038 kbps | 16389 kbps |
| 38 | 10 | 20 | 92157 kbps | 63300 kbps |
| 39 | 23 | 46 | 64407 kbps | 17650 kbps |
| 40 | 7 | 14 | 10447 kbps | 8379 kbps |
| 41 | 11 | 22 | 310817 kbps | 335451 kbps |
| 42 | 28 | 56 | 406173 kbps | 70384 kbps |
| 43 | 14 | 28 | 18551 kbps | 31260 kbps |
| 44 | 14 | 28 | 115313 kbps | 84637 kbps |
| 45 | 15 | 30 | 157061 kbps | 17346 kbps |
| 46 | 23 | 46 | 53345 kbps | 92982 kbps |
| 47 | 35 | 70 | 31064 kbps | 34562 kbps |
| 48 | 11 | 22 | 523223 kbps | 102692 kbps |
| 49 | 29 | 58 | 21748 kbps | 9455 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 44.58% | 1.8108 | 4.50s | 0.96s | 2.99s | 103.62 MB | 2 | 2 | 0.008s | 3.76x |
| 2 | 83.37% | 0.5957 | 4.47s | 0.74s | 2.80s | 89.48 MB | 2 | 2 | 0.008s | 3.76x |
| 3 | 90.07% | 0.3613 | 4.05s | 0.96s | 2.61s | 84.74 MB | 2 | 2 | 0.008s | 3.76x |
| 4 | 93.60% | 0.2207 | 4.00s | 0.61s | 2.51s | 80.03 MB | 2 | 2 | 0.007s | 3.76x |
| 5 | 94.10% | 0.1910 | 3.95s | 0.79s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 6 | 94.18% | 0.1863 | 4.07s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 7 | 95.99% | 0.1264 | 4.06s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 8 | 96.34% | 0.1143 | 3.95s | 0.78s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 9 | 96.69% | 0.1030 | 4.03s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 10 | 96.90% | 0.0932 | 3.99s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 11 | 97.19% | 0.0883 | 3.95s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 12 | 97.41% | 0.0790 | 3.97s | 0.61s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 13 | 97.44% | 0.0764 | 3.94s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 14 | 97.22% | 0.0808 | 3.97s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 15 | 97.82% | 0.0666 | 3.85s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 16 | 97.74% | 0.0660 | 3.99s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 17 | 97.76% | 0.0649 | 4.04s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 18 | 97.95% | 0.0616 | 4.04s | 0.95s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 19 | 98.07% | 0.0585 | 3.97s | 0.79s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 20 | 98.04% | 0.0580 | 3.99s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 21 | 98.20% | 0.0557 | 3.98s | 0.78s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 22 | 98.09% | 0.0551 | 4.06s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 23 | 98.00% | 0.0588 | 4.00s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 24 | 98.09% | 0.0550 | 4.00s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 25 | 98.18% | 0.0554 | 4.02s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.009s | 3.76x |
| 26 | 98.32% | 0.0525 | 4.02s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 27 | 98.36% | 0.0503 | 4.00s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 28 | 98.37% | 0.0500 | 4.02s | 0.79s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 29 | 98.41% | 0.0479 | 3.99s | 0.62s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 30 | 98.32% | 0.0478 | 4.03s | 0.95s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 31 | 98.49% | 0.0448 | 4.10s | 0.79s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 32 | 98.36% | 0.0471 | 3.96s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 33 | 98.40% | 0.0467 | 4.00s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.006s | 3.76x |
| 34 | 98.53% | 0.0458 | 3.98s | 0.79s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 35 | 98.59% | 0.0463 | 3.96s | 0.78s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 36 | 98.55% | 0.0453 | 4.42s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.008s | 3.76x |
| 37 | 98.41% | 0.0504 | 4.05s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.009s | 3.76x |
| 38 | 98.27% | 0.0535 | 3.95s | 0.96s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 39 | 98.49% | 0.0478 | 3.98s | 0.78s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 40 | 98.52% | 0.0468 | 3.98s | 0.78s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 41 | 98.51% | 0.0452 | 4.04s | 0.79s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 42 | 98.59% | 0.0467 | 4.06s | 0.74s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 43 | 98.66% | 0.0444 | 4.05s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 44 | 98.73% | 0.0443 | 3.99s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 45 | 98.66% | 0.0442 | 4.00s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 46 | 98.63% | 0.0426 | 3.95s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.009s | 3.76x |
| 47 | 98.69% | 0.0418 | 4.04s | 0.79s | 2.51s | 77.66 MB | 2 | 2 | 0.008s | 3.76x |
| 48 | 98.69% | 0.0459 | 4.06s | 0.96s | 2.51s | 77.66 MB | 2 | 2 | 0.007s | 3.76x |
| 49 | 98.69% | 0.0414 | 3.98s | 0.78s | 2.51s | 77.67 MB | 2 | 2 | 0.007s | 3.76x |
| 50 | 98.69% | 0.0418 | 4.02s | 0.78s | 2.51s | 77.66 MB | 2 | 2 | 0.006s | 3.76x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 835707529` | 796.99 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 2500` | 2500 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 200` | 200 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `835707529/2500 = 334283` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size(1)` | 326.45 KB |
| 7 | Total Upload / 总上传 | `sum(upload_cost) = 835707529` | 796.99 MB |
| 8 | Total Download / 总下载 | `model_size(177704) * selected(1250) = 3285633300` | 3133.42 MB |
| 9 | Total Communication / 总通信 | `835707529 + 3285633300 = 4121340829` | 3930.42 MB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 3.7622` | 3.76x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **98.69%**，测试损失为 **0.0418**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **3.76x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.008s**。
