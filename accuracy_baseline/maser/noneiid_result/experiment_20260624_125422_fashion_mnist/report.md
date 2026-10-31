# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260624
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260624_125422_fashion_mnist`

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | fashion_mnist | 训练数据集名称 |
| Model / 模型 | cnn_fmnist | 神经网络架构 |
| Num Clients / 客户端数 | 25 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 50 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练 epoch 数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD 优化器学习率 |
| Client Sampling Rate / 采样率 | 1.0 | 每轮参与训练的客户端比例 |
| Non-IID Alpha / 数据异构度 | 5 | Dirichlet 分布参数 |
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
| Final Test Accuracy / 最终测试准确率 | **90.78%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.2856 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 3077.01 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 427.05 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 399.69 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 61.54 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 8.54 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 7339.50 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 4765.81 MB / 292.51 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 2573.69 MB / 107.18 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 2383.04 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 2382.90 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 2382.77 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 190.78 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 95.32 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 51.47 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 12.49x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.037 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 7475 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 598 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334288 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334288 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.39 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 292.51 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 107.18 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 299 | 31013 kbps | 30222 kbps |
| 1 | 50 | 299 | 339099 kbps | 472285 kbps |
| 2 | 50 | 299 | 254789 kbps | 181815 kbps |
| 3 | 50 | 299 | 96962 kbps | 99657 kbps |
| 4 | 50 | 299 | 39759 kbps | 18071 kbps |
| 5 | 50 | 299 | 27438 kbps | 26345 kbps |
| 6 | 50 | 299 | 105349 kbps | 21922 kbps |
| 7 | 50 | 299 | 269298 kbps | 67032 kbps |
| 8 | 50 | 299 | 28807 kbps | 12061 kbps |
| 9 | 50 | 299 | 54690 kbps | 5467 kbps |
| 10 | 50 | 299 | 41651 kbps | 44816 kbps |
| 11 | 50 | 299 | 8057 kbps | 8610 kbps |
| 12 | 50 | 299 | 279465 kbps | 261900 kbps |
| 13 | 50 | 299 | 227204 kbps | 21076 kbps |
| 14 | 50 | 299 | 93105 kbps | 23265 kbps |
| 15 | 50 | 299 | 29282 kbps | 27951 kbps |
| 16 | 50 | 299 | 123339 kbps | 36087 kbps |
| 17 | 50 | 299 | 17150 kbps | 14397 kbps |
| 18 | 50 | 299 | 93249 kbps | 6653 kbps |
| 19 | 50 | 299 | 144829 kbps | 67399 kbps |
| 20 | 50 | 299 | 103970 kbps | 9934 kbps |
| 21 | 50 | 299 | 110526 kbps | 11922 kbps |
| 22 | 50 | 299 | 650580 kbps | 37402 kbps |
| 23 | 50 | 299 | 231919 kbps | 22700 kbps |
| 24 | 50 | 299 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 83.47% | 0.4761 | 7.30s | 4.89s | 1.82s | 123.36 MB | 125 | 125 | 0.032s | 10.44x |
| 2 | 86.82% | 0.3728 | 8.14s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.035s | 12.53x |
| 3 | 87.57% | 0.3427 | 8.35s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 4 | 88.33% | 0.3269 | 8.39s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 5 | 88.70% | 0.3155 | 8.40s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 6 | 89.06% | 0.3065 | 8.48s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 7 | 89.42% | 0.3010 | 8.33s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.035s | 12.53x |
| 8 | 89.39% | 0.2971 | 8.92s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 9 | 89.79% | 0.2916 | 9.11s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 10 | 89.85% | 0.2887 | 8.27s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 11 | 89.86% | 0.2877 | 8.33s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 12 | 89.96% | 0.2848 | 8.86s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 13 | 90.06% | 0.2819 | 8.28s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 14 | 90.13% | 0.2803 | 9.17s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 15 | 90.10% | 0.2789 | 8.28s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 16 | 90.26% | 0.2781 | 8.04s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 17 | 90.23% | 0.2780 | 8.51s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 18 | 90.17% | 0.2783 | 8.38s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 19 | 90.30% | 0.2768 | 8.28s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 20 | 90.40% | 0.2765 | 9.58s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 21 | 90.45% | 0.2763 | 9.20s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 22 | 90.52% | 0.2739 | 8.47s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 23 | 90.47% | 0.2747 | 8.28s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 24 | 90.60% | 0.2748 | 8.29s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 25 | 90.52% | 0.2747 | 9.09s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 26 | 90.50% | 0.2753 | 8.38s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 27 | 90.47% | 0.2756 | 8.21s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 28 | 90.59% | 0.2754 | 8.35s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 29 | 90.57% | 0.2765 | 8.70s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 30 | 90.60% | 0.2753 | 8.83s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 31 | 90.63% | 0.2759 | 8.25s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 32 | 90.69% | 0.2764 | 8.40s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 33 | 90.74% | 0.2771 | 8.40s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 34 | 90.65% | 0.2780 | 8.44s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 35 | 90.63% | 0.2779 | 8.60s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 36 | 90.75% | 0.2784 | 9.01s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 37 | 90.79% | 0.2781 | 8.31s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 38 | 90.76% | 0.2799 | 8.29s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 39 | 90.76% | 0.2803 | 8.28s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 40 | 90.75% | 0.2805 | 9.56s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 41 | 90.80% | 0.2802 | 8.35s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 42 | 90.80% | 0.2806 | 8.27s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 43 | 90.77% | 0.2819 | 8.93s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 44 | 90.82% | 0.2815 | 9.63s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 45 | 90.72% | 0.2827 | 8.26s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.036s | 12.53x |
| 46 | 90.81% | 0.2839 | 8.68s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 47 | 90.77% | 0.2845 | 8.81s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.038s | 12.53x |
| 48 | 90.70% | 0.2848 | 8.42s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 49 | 90.80% | 0.2856 | 8.83s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |
| 50 | 90.78% | 0.2856 | 8.13s | 5.87s | 2.15s | 147.27 MB | 150 | 150 | 0.037s | 12.53x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size)` | 190.78 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 2383.04 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 7475` | 7475 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 598` | 598 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `2498802621/7475 = 334288` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.45 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 4765.81 MB |
| 8 | Total Download / 总下载 | `② + ④` | 2573.69 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 7339.50 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 2383.04 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 2382.90 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 2382.77 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 190.78 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 427.05 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 399.69 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 2383.04 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 2382.90 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 2382.77 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 190.78 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 4765.81 MB = ① + ③
- **Total Download / 总下载:** 2573.69 MB = ② + ④
- **Total Communication / 总通信:** 7339.50 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **90.78%**，测试损失为 **0.2856**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **7339.50 MB**（约 7.17 GB），密文膨胀率为 **12.49x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **427.05 s**，其中通信时间 **399.69 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.037s**。**

