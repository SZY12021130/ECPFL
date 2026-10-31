# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260624
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260624_143744_cifar10`

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
| Non-IID Alpha / 数据异构度 | 0.1 | Dirichlet 分布参数 |
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
| Final Test Accuracy / 最终测试准确率 | **67.32%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 1.0272 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 4735.82 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1918.82 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 2211.11 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 94.72 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 38.38 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 40662.62 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 26237.26 MB / 1610.35 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 14425.36 MB / 600.76 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 13118.71 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 13118.63 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 13118.55 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 1306.73 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 524.75 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 288.51 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.04x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.195 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 41150 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 3292 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334288 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334288 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.36 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1610.35 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 600.76 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 1646 | 31013 kbps | 30222 kbps |
| 1 | 50 | 1646 | 339099 kbps | 472285 kbps |
| 2 | 50 | 1646 | 254789 kbps | 181815 kbps |
| 3 | 50 | 1646 | 96962 kbps | 99657 kbps |
| 4 | 50 | 1646 | 39759 kbps | 18071 kbps |
| 5 | 50 | 1646 | 27438 kbps | 26345 kbps |
| 6 | 50 | 1646 | 105349 kbps | 21922 kbps |
| 7 | 50 | 1646 | 269298 kbps | 67032 kbps |
| 8 | 50 | 1646 | 28807 kbps | 12061 kbps |
| 9 | 50 | 1646 | 54690 kbps | 5467 kbps |
| 10 | 50 | 1646 | 41651 kbps | 44816 kbps |
| 11 | 50 | 1646 | 8057 kbps | 8610 kbps |
| 12 | 50 | 1646 | 279465 kbps | 261900 kbps |
| 13 | 50 | 1646 | 227204 kbps | 21076 kbps |
| 14 | 50 | 1646 | 93105 kbps | 23265 kbps |
| 15 | 50 | 1646 | 29282 kbps | 27951 kbps |
| 16 | 50 | 1646 | 123339 kbps | 36087 kbps |
| 17 | 50 | 1646 | 17150 kbps | 14397 kbps |
| 18 | 50 | 1646 | 93249 kbps | 6653 kbps |
| 19 | 50 | 1646 | 144829 kbps | 67399 kbps |
| 20 | 50 | 1646 | 103970 kbps | 9934 kbps |
| 21 | 50 | 1646 | 110526 kbps | 11922 kbps |
| 22 | 50 | 1646 | 650580 kbps | 37402 kbps |
| 23 | 50 | 1646 | 231919 kbps | 22700 kbps |
| 24 | 50 | 1646 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 10.30% | 2.4170 | 35.43s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.214s | 10.06x |
| 2 | 10.30% | 2.2699 | 35.92s | 31.31s | 11.71s | 791.26 MB | 800 | 800 | 0.243s | 9.76x |
| 3 | 11.80% | 2.1943 | 35.85s | 31.31s | 11.71s | 791.26 MB | 800 | 800 | 0.190s | 9.76x |
| 4 | 21.52% | 2.0620 | 35.39s | 31.31s | 11.71s | 791.26 MB | 800 | 800 | 0.128s | 9.76x |
| 5 | 25.87% | 2.0124 | 36.43s | 31.31s | 11.71s | 791.26 MB | 800 | 800 | 0.132s | 9.76x |
| 6 | 28.98% | 1.9547 | 35.76s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.155s | 10.06x |
| 7 | 32.50% | 1.9190 | 34.18s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.128s | 10.06x |
| 8 | 32.92% | 1.8611 | 36.96s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.128s | 10.06x |
| 9 | 39.11% | 1.8120 | 37.05s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.127s | 10.06x |
| 10 | 34.20% | 1.7717 | 34.62s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.127s | 10.06x |
| 11 | 42.14% | 1.7127 | 34.13s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.125s | 10.06x |
| 12 | 43.03% | 1.6865 | 34.48s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.126s | 10.06x |
| 13 | 46.82% | 1.6492 | 35.06s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.217s | 10.06x |
| 14 | 42.72% | 1.6556 | 37.22s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.214s | 10.06x |
| 15 | 48.70% | 1.5566 | 44.95s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.131s | 10.06x |
| 16 | 47.21% | 1.5453 | 38.65s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.129s | 10.06x |
| 17 | 48.22% | 1.5299 | 41.58s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.135s | 10.06x |
| 18 | 48.36% | 1.4906 | 34.95s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.170s | 10.06x |
| 19 | 52.10% | 1.4655 | 40.41s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.232s | 10.06x |
| 20 | 47.96% | 1.4697 | 37.15s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.218s | 10.06x |
| 21 | 53.41% | 1.4295 | 35.61s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.222s | 10.06x |
| 22 | 51.26% | 1.4275 | 45.06s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.217s | 10.06x |
| 23 | 56.94% | 1.3568 | 35.89s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.278s | 10.06x |
| 24 | 54.16% | 1.3656 | 35.97s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.220s | 10.06x |
| 25 | 56.50% | 1.3480 | 42.78s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.217s | 10.06x |
| 26 | 56.79% | 1.3341 | 37.92s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.128s | 10.06x |
| 27 | 54.24% | 1.3394 | 35.91s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.219s | 10.06x |
| 28 | 57.96% | 1.2777 | 40.12s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.216s | 10.06x |
| 29 | 58.72% | 1.2766 | 41.57s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.216s | 10.06x |
| 30 | 58.69% | 1.2611 | 34.85s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.217s | 10.06x |
| 31 | 61.63% | 1.2247 | 44.18s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.221s | 10.06x |
| 32 | 62.30% | 1.2059 | 43.44s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.219s | 10.06x |
| 33 | 61.66% | 1.2143 | 37.76s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.221s | 10.06x |
| 34 | 61.75% | 1.1936 | 40.17s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.223s | 10.06x |
| 35 | 60.12% | 1.2141 | 35.93s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.213s | 10.06x |
| 36 | 61.64% | 1.1682 | 35.39s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.224s | 10.06x |
| 37 | 63.14% | 1.1592 | 44.74s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.223s | 10.06x |
| 38 | 63.07% | 1.1468 | 42.84s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.224s | 10.06x |
| 39 | 65.14% | 1.1093 | 44.45s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.223s | 10.06x |
| 40 | 63.12% | 1.1239 | 37.13s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.216s | 10.06x |
| 41 | 64.43% | 1.1040 | 34.27s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.225s | 10.06x |
| 42 | 65.18% | 1.1030 | 36.92s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.219s | 10.06x |
| 43 | 63.94% | 1.1040 | 36.35s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.157s | 10.06x |
| 44 | 66.82% | 1.0749 | 44.89s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.224s | 10.06x |
| 45 | 65.22% | 1.0839 | 44.31s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.216s | 10.06x |
| 46 | 65.25% | 1.0814 | 41.70s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.217s | 10.06x |
| 47 | 65.42% | 1.0730 | 39.91s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.215s | 10.06x |
| 48 | 64.81% | 1.0786 | 36.97s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.221s | 10.06x |
| 49 | 66.11% | 1.0472 | 38.51s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.229s | 10.06x |
| 50 | 67.32% | 1.0272 | 37.11s | 32.29s | 12.04s | 815.17 MB | 825 | 825 | 0.213s | 10.06x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 13118.71 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 41150` | 41150 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 3292` | 3292 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `13755962039/41150 = 334288` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.45 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 26237.26 MB |
| 8 | Total Download / 总下载 | `② + ④` | 14425.36 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 40662.62 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 13118.71 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 13118.63 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 13118.55 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 1306.73 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 1918.82 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 2211.11 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 13118.71 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 13118.63 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 13118.55 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 1306.73 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 26237.26 MB = ① + ③
- **Total Download / 总下载:** 14425.36 MB = ② + ④
- **Total Communication / 总通信:** 40662.62 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **67.32%**，测试损失为 **1.0272**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **40662.62 MB**（约 39.71 GB），密文膨胀率为 **10.04x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **1918.82 s**，其中通信时间 **2211.11 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.195s**。**

