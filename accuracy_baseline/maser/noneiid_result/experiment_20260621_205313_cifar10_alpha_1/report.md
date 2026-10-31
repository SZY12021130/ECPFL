# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260621
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260621_205313_cifar10_alpha_1`

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
| Non-IID Alpha / 数据异构度 | 1.0 | Dirichlet 分布参数 |
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
| Final Test Accuracy / 最终测试准确率 | **80.64%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.5786 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 4791.65 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1927.93 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 2279.22 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 95.83 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 38.56 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 41905.48 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 27065.83 MB / 1661.20 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 14839.65 MB / 618.02 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 13533.20 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 13532.92 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 13532.64 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 1306.73 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 541.32 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 296.79 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.36x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.209 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 42450 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 3396 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334289 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334289 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.48 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1661.20 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 618.02 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 1698 | 31013 kbps | 30222 kbps |
| 1 | 50 | 1698 | 339099 kbps | 472285 kbps |
| 2 | 50 | 1698 | 254789 kbps | 181815 kbps |
| 3 | 50 | 1698 | 96962 kbps | 99657 kbps |
| 4 | 50 | 1698 | 39759 kbps | 18071 kbps |
| 5 | 50 | 1698 | 27438 kbps | 26345 kbps |
| 6 | 50 | 1698 | 105349 kbps | 21922 kbps |
| 7 | 50 | 1698 | 269298 kbps | 67032 kbps |
| 8 | 50 | 1698 | 28807 kbps | 12061 kbps |
| 9 | 50 | 1698 | 54690 kbps | 5467 kbps |
| 10 | 50 | 1698 | 41651 kbps | 44816 kbps |
| 11 | 50 | 1698 | 8057 kbps | 8610 kbps |
| 12 | 50 | 1698 | 279465 kbps | 261900 kbps |
| 13 | 50 | 1698 | 227204 kbps | 21076 kbps |
| 14 | 50 | 1698 | 93105 kbps | 23265 kbps |
| 15 | 50 | 1698 | 29282 kbps | 27951 kbps |
| 16 | 50 | 1698 | 123339 kbps | 36087 kbps |
| 17 | 50 | 1698 | 17150 kbps | 14397 kbps |
| 18 | 50 | 1698 | 93249 kbps | 6653 kbps |
| 19 | 50 | 1698 | 144829 kbps | 67399 kbps |
| 20 | 50 | 1698 | 103970 kbps | 9934 kbps |
| 21 | 50 | 1698 | 110526 kbps | 11922 kbps |
| 22 | 50 | 1698 | 650580 kbps | 37402 kbps |
| 23 | 50 | 1698 | 231919 kbps | 22700 kbps |
| 24 | 50 | 1698 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 19.77% | 2.0958 | 37.78s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.203s | 10.06x |
| 2 | 33.70% | 1.7069 | 37.10s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.202s | 10.06x |
| 3 | 43.42% | 1.5111 | 39.47s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.207s | 10.37x |
| 4 | 47.90% | 1.4136 | 39.88s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.206s | 10.37x |
| 5 | 53.10% | 1.2906 | 38.94s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 6 | 55.80% | 1.2170 | 38.36s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.206s | 10.37x |
| 7 | 58.38% | 1.1496 | 38.28s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 8 | 60.79% | 1.0896 | 38.67s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.207s | 10.37x |
| 9 | 62.37% | 1.0478 | 39.99s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.206s | 10.37x |
| 10 | 63.56% | 1.0107 | 37.62s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 11 | 64.97% | 0.9768 | 39.87s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 12 | 65.44% | 0.9632 | 37.84s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 13 | 66.82% | 0.9211 | 38.39s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 14 | 68.29% | 0.8907 | 37.87s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 15 | 69.03% | 0.8733 | 37.48s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.207s | 10.37x |
| 16 | 69.58% | 0.8581 | 38.35s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 17 | 70.02% | 0.8424 | 38.90s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 18 | 71.51% | 0.8100 | 38.32s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 19 | 71.79% | 0.8009 | 37.52s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 20 | 72.45% | 0.7862 | 39.45s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 21 | 72.76% | 0.7780 | 37.85s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.218s | 10.37x |
| 22 | 73.26% | 0.7653 | 37.49s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 23 | 74.03% | 0.7463 | 36.85s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 24 | 74.42% | 0.7364 | 37.69s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 25 | 74.76% | 0.7286 | 39.93s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 26 | 74.79% | 0.7209 | 38.74s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 27 | 75.32% | 0.7111 | 37.61s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 28 | 75.84% | 0.6938 | 36.86s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 29 | 75.60% | 0.7041 | 40.29s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 30 | 76.36% | 0.6820 | 37.25s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 31 | 76.71% | 0.6734 | 37.50s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 32 | 76.32% | 0.6884 | 39.66s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 33 | 77.54% | 0.6518 | 40.44s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 34 | 77.36% | 0.6519 | 40.49s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 35 | 77.31% | 0.6521 | 39.97s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.218s | 10.37x |
| 36 | 78.27% | 0.6311 | 38.28s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 37 | 78.22% | 0.6355 | 39.49s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 38 | 78.78% | 0.6202 | 39.65s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 39 | 78.95% | 0.6163 | 37.50s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 40 | 78.97% | 0.6149 | 39.44s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 41 | 79.01% | 0.6162 | 36.52s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.208s | 10.37x |
| 42 | 79.36% | 0.6040 | 38.31s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 43 | 79.42% | 0.5986 | 38.36s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 44 | 79.48% | 0.6061 | 39.45s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 45 | 79.96% | 0.5920 | 37.84s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 46 | 80.57% | 0.5838 | 40.30s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.210s | 10.37x |
| 47 | 80.25% | 0.5873 | 38.72s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.207s | 10.37x |
| 48 | 80.61% | 0.5731 | 38.39s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.211s | 10.37x |
| 49 | 80.93% | 0.5718 | 38.31s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |
| 50 | 80.64% | 0.5786 | 38.66s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.209s | 10.37x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 13533.20 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 42450` | 42450 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 3396` | 3396 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `14190587267/42450 = 334289` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.45 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 27065.83 MB |
| 8 | Total Download / 总下载 | `② + ④` | 14839.65 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 41905.48 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 13533.20 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 13532.92 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 13532.64 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 1306.73 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 1927.93 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 2279.22 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 13533.20 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 13532.92 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 13532.64 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 1306.73 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 27065.83 MB = ① + ③
- **Total Download / 总下载:** 14839.65 MB = ② + ④
- **Total Communication / 总通信:** 41905.48 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **80.64%**，测试损失为 **0.5786**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **41905.48 MB**（约 40.92 GB），密文膨胀率为 **10.36x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **1927.93 s**，其中通信时间 **2279.22 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.209s**。**

