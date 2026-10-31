# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260624
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260624_182441_cifar10`

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | cifar10 | 训练数据集名称 |
| Model / 模型 | resnet20 | 神经网络架构 |
| Num Clients / 客户端数 | 25 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 50 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练 epoch 数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD 优化器学习率 |
| Client Sampling Rate / 采样率 | 1.0 | 每轮参与训练的客户端比例 |
| Non-IID Alpha / 数据异构度 | 10 | Dirichlet 分布参数 |
| IID / 独立同分布 | False | 数据分布是否 IID |
| Device / 设备 | cuda | 训练设备 (CPU/CUDA) |
| Upload Difference / 上传差值 | True | 是否上传模型差值而非完整权重 |

### 1.1 CKKS Parameters / CKKS 加密参数

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Poly Modulus Degree / 多项式模数度 | 8192 | CKKS 多项式环的维度 |
| Coeff Mod Bit Sizes / 系数模数位宽 | [60, 40, 40, 60] | 系数模数的位宽序列 |
| Global Scale / 全局缩放因子 | 1099511627776 | CKKS 编码缩放因子 |
| Slot Packing / 槽打包 | True | 是否启用 SIMD 槽打包 |

## 2. Key Metrics Summary / 关键指标汇总

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final Test Accuracy / 最终测试准确率 | **81.55%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.5500 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 4275.94 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1941.87 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 2330.44 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 85.52 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 38.84 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 42840.20 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 27688.97 MB / 1699.45 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 15151.22 MB / 630.99 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 13844.03 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 13844.49 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 13844.95 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 1306.73 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 553.78 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 303.02 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.59x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.181 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 43425 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 3474 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334289 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334289 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.40 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1699.45 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 630.99 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 1737 | 31013 kbps | 30222 kbps |
| 1 | 50 | 1737 | 339099 kbps | 472285 kbps |
| 2 | 50 | 1737 | 254789 kbps | 181815 kbps |
| 3 | 50 | 1737 | 96962 kbps | 99657 kbps |
| 4 | 50 | 1737 | 39759 kbps | 18071 kbps |
| 5 | 50 | 1737 | 27438 kbps | 26345 kbps |
| 6 | 50 | 1737 | 105349 kbps | 21922 kbps |
| 7 | 50 | 1737 | 269298 kbps | 67032 kbps |
| 8 | 50 | 1737 | 28807 kbps | 12061 kbps |
| 9 | 50 | 1737 | 54690 kbps | 5467 kbps |
| 10 | 50 | 1737 | 41651 kbps | 44816 kbps |
| 11 | 50 | 1737 | 8057 kbps | 8610 kbps |
| 12 | 50 | 1737 | 279465 kbps | 261900 kbps |
| 13 | 50 | 1737 | 227204 kbps | 21076 kbps |
| 14 | 50 | 1737 | 93105 kbps | 23265 kbps |
| 15 | 50 | 1737 | 29282 kbps | 27951 kbps |
| 16 | 50 | 1737 | 123339 kbps | 36087 kbps |
| 17 | 50 | 1737 | 17150 kbps | 14397 kbps |
| 18 | 50 | 1737 | 93249 kbps | 6653 kbps |
| 19 | 50 | 1737 | 144829 kbps | 67399 kbps |
| 20 | 50 | 1737 | 103970 kbps | 9934 kbps |
| 21 | 50 | 1737 | 110526 kbps | 11922 kbps |
| 22 | 50 | 1737 | 650580 kbps | 37402 kbps |
| 23 | 50 | 1737 | 231919 kbps | 22700 kbps |
| 24 | 50 | 1737 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 24.59% | 1.9654 | 35.98s | 31.31s | 11.71s | 791.29 MB | 800 | 800 | 0.217s | 9.76x |
| 2 | 42.53% | 1.5497 | 39.00s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.224s | 10.37x |
| 3 | 47.47% | 1.4292 | 39.04s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.225s | 10.37x |
| 4 | 52.12% | 1.3122 | 40.17s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.224s | 10.67x |
| 5 | 56.13% | 1.2236 | 39.87s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.223s | 10.67x |
| 6 | 58.98% | 1.1505 | 40.40s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.227s | 10.67x |
| 7 | 60.49% | 1.0990 | 39.95s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.227s | 10.67x |
| 8 | 61.91% | 1.0645 | 40.19s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.224s | 10.67x |
| 9 | 63.34% | 1.0170 | 39.63s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.224s | 10.67x |
| 10 | 64.98% | 0.9826 | 39.60s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.227s | 10.67x |
| 11 | 66.43% | 0.9494 | 40.21s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.228s | 10.67x |
| 12 | 67.39% | 0.9215 | 39.85s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.225s | 10.67x |
| 13 | 68.18% | 0.9011 | 39.43s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.228s | 10.67x |
| 14 | 69.48% | 0.8715 | 39.88s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.228s | 10.67x |
| 15 | 69.59% | 0.8641 | 39.71s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.225s | 10.67x |
| 16 | 70.46% | 0.8448 | 39.04s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.225s | 10.67x |
| 17 | 71.20% | 0.8161 | 39.57s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.220s | 10.67x |
| 18 | 71.75% | 0.8014 | 39.34s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.227s | 10.67x |
| 19 | 72.58% | 0.7908 | 39.72s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.228s | 10.67x |
| 20 | 73.08% | 0.7743 | 39.47s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.242s | 10.67x |
| 21 | 73.55% | 0.7573 | 39.85s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.232s | 10.67x |
| 22 | 74.02% | 0.7405 | 39.64s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.227s | 10.67x |
| 23 | 74.83% | 0.7269 | 39.34s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.225s | 10.67x |
| 24 | 74.77% | 0.7251 | 39.88s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.221s | 10.67x |
| 25 | 75.24% | 0.7123 | 39.60s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.136s | 10.67x |
| 26 | 75.85% | 0.6991 | 38.47s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.126s | 10.67x |
| 27 | 76.33% | 0.6839 | 38.25s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.125s | 10.67x |
| 28 | 76.75% | 0.6761 | 38.01s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.135s | 10.67x |
| 29 | 77.16% | 0.6633 | 38.05s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.132s | 10.67x |
| 30 | 77.63% | 0.6563 | 38.42s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.128s | 10.67x |
| 31 | 77.96% | 0.6440 | 38.17s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.132s | 10.67x |
| 32 | 78.18% | 0.6380 | 38.17s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.139s | 10.67x |
| 33 | 78.69% | 0.6350 | 38.09s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.135s | 10.67x |
| 34 | 78.61% | 0.6277 | 38.32s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.129s | 10.67x |
| 35 | 79.11% | 0.6192 | 38.08s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.134s | 10.67x |
| 36 | 79.31% | 0.6102 | 38.36s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.128s | 10.67x |
| 37 | 79.56% | 0.6079 | 38.41s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.136s | 10.67x |
| 38 | 79.63% | 0.6030 | 39.62s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.144s | 10.67x |
| 39 | 80.08% | 0.5951 | 37.43s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.149s | 10.37x |
| 40 | 80.00% | 0.5926 | 38.87s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.153s | 10.67x |
| 41 | 80.14% | 0.5896 | 39.40s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.156s | 10.67x |
| 42 | 80.26% | 0.5890 | 38.01s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.148s | 10.37x |
| 43 | 80.59% | 0.5784 | 37.59s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.138s | 10.37x |
| 44 | 80.77% | 0.5729 | 38.31s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.135s | 10.67x |
| 45 | 80.96% | 0.5631 | 37.27s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.137s | 10.37x |
| 46 | 81.02% | 0.5646 | 38.10s | 34.24s | 12.71s | 863.02 MB | 875 | 875 | 0.140s | 10.67x |
| 47 | 81.07% | 0.5600 | 37.86s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.146s | 10.37x |
| 48 | 81.36% | 0.5567 | 37.66s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.231s | 10.37x |
| 49 | 81.51% | 0.5547 | 37.24s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.130s | 10.37x |
| 50 | 81.55% | 0.5500 | 37.36s | 33.26s | 12.37s | 839.11 MB | 850 | 850 | 0.125s | 10.37x |

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
| 8 | MASER ① 加密上传 | `sum(client ciphertext sizes)` |
| 9 | MASER ② 聚合密文广播 | `num_selected * num_batches * single_ct_size` |
| 10 | MASER ③ 解密份额上传 | `num_selected * num_batches * single_ct_size` |
| 11 | MASER ④ 明文模型下发 | `global_model_size_bytes * num_selected_clients` |
| 7 | Expansion Ratio / 膨胀率 | `total_ciphertext_size / total_plaintext_size` |

### 5.2 Substituted Values / 数值代入

| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |
|---|---------------|-------------------|---------------|
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size)` | 1306.73 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 13844.03 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 43425` | 43425 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 3474` | 3474 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `14516515265/43425 = 334289` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.45 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 27688.97 MB |
| 8 | Total Download / 总下载 | `② + ④` | 15151.22 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 42840.20 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 13844.03 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 13844.49 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 13844.95 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 1306.73 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 1941.87 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 2330.44 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 13844.03 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 13844.49 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 13844.95 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 1306.73 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 27688.97 MB = ① + ③
- **Total Download / 总下载:** 15151.22 MB = ② + ④
- **Total Communication / 总通信:** 42840.20 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **81.55%**，测试损失为 **0.5500**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **42840.20 MB**（约 41.84 GB），密文膨胀率为 **10.59x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **1941.87 s**，其中通信时间 **2330.44 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.181s**。**

