# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260621_221332  
**Output Directory / 输出目录:** `accuracy_baseline/maser/result_fix_pro\experiment_20260621_221332_svhn`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | svhn | 训练数据集名称 |
| Model / 模型 | resnet32 | 神经网络架构 |
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
| Final Test Accuracy / 最终测试准确率 | **95.82%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.1663 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 7970.99 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 3308.35 s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |
| Total Simulated Comm Time / 总模拟通信时间 | 3955.82 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 159.42 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 66.17 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 72725.48 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 46991.57 MB / 69.14 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 25733.91 MB / 12.36 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 23495.78 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 23495.78 MB | 服务器聚合后密文下发给客户端做 partial decrypt |
| MASER ③ 解密份额上传 | 23495.78 MB | 客户端 partial decrypt 份额回传累计 |
| MASER ④ 明文模型下发 | 2238.13 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 904.48 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 479.33 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.50x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.357 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 73700 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 5896 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334289 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334289 bytes | 服务器聚合后密文块的平均大小 |
| Key Distribution Cost / 密钥分发开销 | 861.36 MB | CKKS公钥/Galois密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 2884.12 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 1071.71 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 2948 | 31013 kbps | 30222 kbps |
| 1 | 50 | 2948 | 339099 kbps | 472285 kbps |
| 2 | 50 | 2948 | 254789 kbps | 181815 kbps |
| 3 | 50 | 2948 | 96962 kbps | 99657 kbps |
| 4 | 50 | 2948 | 39759 kbps | 18071 kbps |
| 5 | 50 | 2948 | 27438 kbps | 26345 kbps |
| 6 | 50 | 2948 | 105349 kbps | 21922 kbps |
| 7 | 50 | 2948 | 269298 kbps | 67032 kbps |
| 8 | 50 | 2948 | 28807 kbps | 12061 kbps |
| 9 | 50 | 2948 | 54690 kbps | 5467 kbps |
| 10 | 50 | 2948 | 41651 kbps | 44816 kbps |
| 11 | 50 | 2948 | 8057 kbps | 8610 kbps |
| 12 | 50 | 2948 | 279465 kbps | 261900 kbps |
| 13 | 50 | 2948 | 227204 kbps | 21076 kbps |
| 14 | 50 | 2948 | 93105 kbps | 23265 kbps |
| 15 | 50 | 2948 | 29282 kbps | 27951 kbps |
| 16 | 50 | 2948 | 123339 kbps | 36087 kbps |
| 17 | 50 | 2948 | 17150 kbps | 14397 kbps |
| 18 | 50 | 2948 | 93249 kbps | 6653 kbps |
| 19 | 50 | 2948 | 144829 kbps | 67399 kbps |
| 20 | 50 | 2948 | 103970 kbps | 9934 kbps |
| 21 | 50 | 2948 | 110526 kbps | 11922 kbps |
| 22 | 50 | 2948 | 650580 kbps | 37402 kbps |
| 23 | 50 | 2948 | 231919 kbps | 22700 kbps |
| 24 | 50 | 2948 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果
| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 19.96% | 2.2454 | 2564.39s | 1962.52s | 1314.64s | 1431.56 MB | 58 | 58 | 0.344s | 10.33x |
| 2 | 40.68% | 1.7349 | 2520.26s | 1928.69s | 1292.00s | 1407.67 MB | 58 | 58 | 0.347s | 10.15x |
| 3 | 81.52% | 0.6389 | 2431.99s | 1861.02s | 1246.73s | 1359.80 MB | 58 | 57 | 0.346s | 9.79x |
| 4 | 87.19% | 0.4241 | 2564.38s | 1962.52s | 1314.64s | 1431.52 MB | 58 | 57 | 0.345s | 10.33x |
| 5 | 89.48% | 0.3510 | 2608.50s | 1996.36s | 1337.27s | 1455.47 MB | 58 | 55 | 0.357s | 10.51x |
| 6 | 90.91% | 0.3108 | 2652.63s | 2030.20s | 1359.91s | 1479.40 MB | 58 | 55 | 0.348s | 10.68x |
| 7 | 91.31% | 0.2940 | 2652.60s | 2030.20s | 1359.91s | 1479.40 MB | 58 | 58 | 0.369s | 10.68x |
| 8 | 92.10% | 0.2681 | 2652.58s | 2030.20s | 1359.91s | 1479.38 MB | 58 | 58 | 0.348s | 10.68x |
| 9 | 92.40% | 0.2610 | 2652.65s | 2030.20s | 1359.91s | 1479.40 MB | 58 | 59 | 0.348s | 10.68x |
| 10 | 92.82% | 0.2517 | 2652.65s | 2030.20s | 1359.91s | 1479.37 MB | 58 | 59 | 0.618s | 10.68x |
| 11 | 93.27% | 0.2349 | 2652.65s | 2030.19s | 1359.91s | 1479.38 MB | 58 | 60 | 0.359s | 10.68x |
| 12 | 93.35% | 0.2309 | 2608.48s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 60 | 0.361s | 10.51x |
| 13 | 93.46% | 0.2275 | 2608.48s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 60 | 0.355s | 10.51x |
| 14 | 93.48% | 0.2293 | 2608.50s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 60 | 0.359s | 10.51x |
| 15 | 93.92% | 0.2136 | 2608.50s | 1996.36s | 1337.27s | 1455.48 MB | 58 | 60 | 0.372s | 10.51x |
| 16 | 94.01% | 0.2130 | 2608.49s | 1996.36s | 1337.27s | 1455.47 MB | 58 | 60 | 0.358s | 10.51x |
| 17 | 94.16% | 0.2077 | 2608.49s | 1996.37s | 1337.27s | 1455.46 MB | 58 | 60 | 0.357s | 10.51x |
| 18 | 94.24% | 0.2061 | 2608.47s | 1996.36s | 1337.27s | 1455.47 MB | 58 | 60 | 0.353s | 10.51x |
| 19 | 94.32% | 0.2025 | 2608.50s | 1996.36s | 1337.27s | 1455.44 MB | 58 | 60 | 0.358s | 10.50x |
| 20 | 94.51% | 0.1998 | 2608.45s | 1996.36s | 1337.27s | 1455.41 MB | 58 | 60 | 0.364s | 10.50x |
| 21 | 94.42% | 0.2009 | 2608.55s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 60 | 0.349s | 10.51x |
| 22 | 94.73% | 0.1930 | 2608.49s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 60 | 0.361s | 10.50x |
| 23 | 94.71% | 0.1918 | 2608.49s | 1996.36s | 1337.27s | 1455.47 MB | 58 | 59 | 0.388s | 10.51x |
| 24 | 94.80% | 0.1912 | 2608.48s | 1996.36s | 1337.27s | 1455.43 MB | 58 | 59 | 0.357s | 10.50x |
| 25 | 94.86% | 0.1885 | 2608.51s | 1996.36s | 1337.27s | 1455.46 MB | 58 | 59 | 0.356s | 10.50x |
| 26 | 94.95% | 0.1851 | 2608.53s | 1996.36s | 1337.27s | 1455.49 MB | 57 | 59 | 0.344s | 10.51x |
| 27 | 95.02% | 0.1857 | 2608.49s | 1996.36s | 1337.27s | 1455.49 MB | 57 | 59 | 0.344s | 10.51x |
| 28 | 95.21% | 0.1803 | 2608.52s | 1996.37s | 1337.27s | 1455.50 MB | 57 | 59 | 0.334s | 10.51x |
| 29 | 95.12% | 0.1813 | 2608.47s | 1996.36s | 1337.27s | 1455.51 MB | 57 | 59 | 0.367s | 10.51x |
| 30 | 95.14% | 0.1807 | 2608.48s | 1996.36s | 1337.27s | 1455.45 MB | 57 | 59 | 0.332s | 10.50x |
| 31 | 95.28% | 0.1774 | 2608.48s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.351s | 10.51x |
| 32 | 95.24% | 0.1810 | 2608.64s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.344s | 10.51x |
| 33 | 95.26% | 0.1785 | 2608.50s | 1996.36s | 1337.27s | 1455.48 MB | 57 | 59 | 0.347s | 10.51x |
| 34 | 95.19% | 0.1797 | 2608.48s | 1996.36s | 1337.27s | 1455.45 MB | 57 | 59 | 0.346s | 10.50x |
| 35 | 95.35% | 0.1767 | 2608.48s | 1996.36s | 1337.27s | 1455.49 MB | 57 | 59 | 0.335s | 10.51x |
| 36 | 95.47% | 0.1709 | 2608.52s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.343s | 10.51x |
| 37 | 95.41% | 0.1746 | 2608.53s | 1996.37s | 1337.27s | 1455.44 MB | 57 | 59 | 0.359s | 10.50x |
| 38 | 95.42% | 0.1754 | 2608.47s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.352s | 10.50x |
| 39 | 95.51% | 0.1730 | 2608.49s | 1996.36s | 1337.27s | 1455.47 MB | 57 | 59 | 0.346s | 10.51x |
| 40 | 95.53% | 0.1751 | 2608.50s | 1996.37s | 1337.27s | 1455.47 MB | 57 | 59 | 0.349s | 10.51x |
| 41 | 95.45% | 0.1743 | 2608.48s | 1996.36s | 1337.27s | 1455.47 MB | 57 | 59 | 0.345s | 10.51x |
| 42 | 95.46% | 0.1757 | 2608.50s | 1996.36s | 1337.27s | 1455.48 MB | 57 | 59 | 0.344s | 10.51x |
| 43 | 95.45% | 0.1756 | 2608.62s | 1996.36s | 1337.27s | 1455.48 MB | 57 | 59 | 0.348s | 10.51x |
| 44 | 95.59% | 0.1698 | 2608.07s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.342s | 10.51x |
| 45 | 95.66% | 0.1718 | 2607.50s | 1996.36s | 1337.27s | 1455.48 MB | 57 | 59 | 0.355s | 10.51x |
| 46 | 95.64% | 0.1697 | 2608.69s | 1996.36s | 1337.27s | 1455.46 MB | 57 | 59 | 0.369s | 10.51x |
| 47 | 95.79% | 0.1700 | 2608.55s | 1996.36s | 1337.27s | 1455.45 MB | 57 | 59 | 0.346s | 10.50x |
| 48 | 95.67% | 0.1710 | 2608.57s | 1996.36s | 1337.27s | 1455.43 MB | 57 | 59 | 0.351s | 10.50x |
| 49 | 95.69% | 0.1752 | 2608.63s | 1996.36s | 1337.27s | 1455.45 MB | 57 | 59 | 0.354s | 10.50x |
| 50 | 95.82% | 0.1663 | 2608.61s | 1996.36s | 1337.27s | 1455.50 MB | 57 | 59 | 0.344s | 10.51x |


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
| 9 | MASER ② 聚合密文广播 | `num_selected * num_batches * agg_ct_size` |
| 10 | MASER ③ 解密份额上传 | `num_selected * num_batches * agg_ct_size` |
| 11 | MASER ④ 明文模型下发 | `global_model_size_bytes * num_selected_clients` |
| 7 | Expansion Ratio / 膨胀率 | `total_ciphertext_size / total_plaintext_size` |

### 5.2 Substituted Values / 数值代入

| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |
|---|---------------|-------------------|---------------|
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 2346850000` | 2.19 GB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 24637114230` | 22.95 GB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 73700` | 73700 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 5896` | 5896 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `24637114230/73700 = 334289` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `= single_ct_size (ideal xMK-CKKS assumption)` | 326.45 KB |
| 7 | Total Upload / 总上传 | `maser_ct_upload + maser_partial_dec_upload = 24637114230 + 24637114230` | 45.89 GB |
| 8 | Total Download / 总下载 | `maser_agg_ct_download + maser_plaintext_download = 24637114230 + 2346850000` | 25.13 GB |
| 9 | Total Communication / 总通信 | `49274228460 + 26983964230 = 76258192690` | 71.02 GB |
| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 10.4980` | 10.50x |
| 11 | MASER ① 加密上传 | `sum(maser_ct_upload) = 24637114230` | 22.95 GB |
| 12 | MASER ② 聚合密文广播 | `= maser_ct_upload (ideal xMK-CKKS assumption) = 24637114230` | 22.95 GB |
| 13 | MASER ③ 解密份额上传 | `= maser_ct_upload (ideal xMK-CKKS assumption) = 24637114230` | 22.95 GB |
| 14 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download) = 2346850000` | 2.19 GB |


### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 22.95 GB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 22.95 GB — 服务器聚合后的密文下发给所有客户端（按 xMK-CKKS 理想假设：聚合密文大小 = 单密文大小）
- **③ Partial Decryption Upload / 解密份额上传:** 22.95 GB — 客户端 partial decrypt 份额回传（按 xMK-CKKS 理想假设）
- **④ Plaintext Model Download / 明文模型下发:** 2.19 GB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 45.89 GB = ① + ③
- **Total Download / 总下载:** 25.13 GB = ② + ④
- **Total Communication / 总通信:** 71.02 GB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

> **Note / 说明：** 本报告中的 MASER ②、③ 以及 Section 4 的 `Comm` 列按 xMK-CKKS 论文理想假设折算，即聚合密文大小与单个密文大小相等。当前 MASER 底层实现仍使用 MK-CKKS 同态加法，实际运行中聚合密文会膨胀；此处数值为理论对比口径。Section 4 的 `Round Time`、`Upload Time`、`Download Time` 仍为原模拟执行时的 wall-clock 记录。


## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **95.82%**，测试损失为 **0.1663**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **10.50x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.357s**。
