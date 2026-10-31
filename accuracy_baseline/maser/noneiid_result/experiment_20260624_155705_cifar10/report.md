# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260624
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260624_155705_cifar10`

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
| Non-IID Alpha / 数据异构度 | 0.5 | Dirichlet 分布参数 |
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
| Final Test Accuracy / 最终测试准确率 | **78.42%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.6148 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 4121.55 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1899.28 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 2276.61 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 82.43 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 37.99 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 41857.82 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 27034.06 MB / 1659.25 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 14823.76 MB / 617.36 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 13517.28 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 13517.03 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 13516.78 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 1306.73 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 540.68 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 296.48 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.34x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.174 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 42400 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 3392 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334290 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334290 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.29 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1659.25 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 617.36 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 1696 | 31013 kbps | 30222 kbps |
| 1 | 50 | 1696 | 339099 kbps | 472285 kbps |
| 2 | 50 | 1696 | 254789 kbps | 181815 kbps |
| 3 | 50 | 1696 | 96962 kbps | 99657 kbps |
| 4 | 50 | 1696 | 39759 kbps | 18071 kbps |
| 5 | 50 | 1696 | 27438 kbps | 26345 kbps |
| 6 | 50 | 1696 | 105349 kbps | 21922 kbps |
| 7 | 50 | 1696 | 269298 kbps | 67032 kbps |
| 8 | 50 | 1696 | 28807 kbps | 12061 kbps |
| 9 | 50 | 1696 | 54690 kbps | 5467 kbps |
| 10 | 50 | 1696 | 41651 kbps | 44816 kbps |
| 11 | 50 | 1696 | 8057 kbps | 8610 kbps |
| 12 | 50 | 1696 | 279465 kbps | 261900 kbps |
| 13 | 50 | 1696 | 227204 kbps | 21076 kbps |
| 14 | 50 | 1696 | 93105 kbps | 23265 kbps |
| 15 | 50 | 1696 | 29282 kbps | 27951 kbps |
| 16 | 50 | 1696 | 123339 kbps | 36087 kbps |
| 17 | 50 | 1696 | 17150 kbps | 14397 kbps |
| 18 | 50 | 1696 | 93249 kbps | 6653 kbps |
| 19 | 50 | 1696 | 144829 kbps | 67399 kbps |
| 20 | 50 | 1696 | 103970 kbps | 9934 kbps |
| 21 | 50 | 1696 | 110526 kbps | 11922 kbps |
| 22 | 50 | 1696 | 650580 kbps | 37402 kbps |
| 23 | 50 | 1696 | 231919 kbps | 22700 kbps |
| 24 | 50 | 1696 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 16.10% | 2.2389 | 37.42s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.221s | 10.06x |
| 2 | 33.80% | 1.7828 | 39.60s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.216s | 10.06x |
| 3 | 40.50% | 1.6286 | 38.01s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.222s | 10.06x |
| 4 | 46.16% | 1.4767 | 39.05s | 32.28s | 12.04s | 815.16 MB | 825 | 825 | 0.214s | 10.06x |
| 5 | 47.58% | 1.4279 | 37.98s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.215s | 10.37x |
| 6 | 53.36% | 1.2913 | 40.13s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.218s | 10.37x |
| 7 | 55.98% | 1.2209 | 38.01s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.220s | 10.37x |
| 8 | 58.08% | 1.1684 | 37.73s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.219s | 10.37x |
| 9 | 59.13% | 1.1285 | 37.28s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.221s | 10.37x |
| 10 | 61.00% | 1.0931 | 38.83s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.220s | 10.37x |
| 11 | 61.19% | 1.0845 | 39.53s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.230s | 10.37x |
| 12 | 63.02% | 1.0350 | 37.67s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.227s | 10.37x |
| 13 | 63.61% | 1.0176 | 39.03s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.229s | 10.37x |
| 14 | 65.20% | 0.9782 | 41.86s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.233s | 10.37x |
| 15 | 66.10% | 0.9524 | 37.45s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.228s | 10.37x |
| 16 | 67.02% | 0.9280 | 38.58s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.161s | 10.37x |
| 17 | 66.66% | 0.9383 | 37.70s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.133s | 10.37x |
| 18 | 68.48% | 0.8913 | 37.10s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.222s | 10.37x |
| 19 | 68.51% | 0.8822 | 39.21s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.222s | 10.37x |
| 20 | 69.75% | 0.8536 | 43.64s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.227s | 10.37x |
| 21 | 70.11% | 0.8457 | 42.16s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.230s | 10.37x |
| 22 | 70.74% | 0.8290 | 37.07s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.223s | 10.37x |
| 23 | 71.16% | 0.8184 | 37.86s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.224s | 10.37x |
| 24 | 71.14% | 0.8147 | 39.11s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.226s | 10.37x |
| 25 | 71.95% | 0.7937 | 36.27s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.123s | 10.37x |
| 26 | 72.35% | 0.7893 | 38.22s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.123s | 10.37x |
| 27 | 72.61% | 0.7755 | 36.35s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.123s | 10.37x |
| 28 | 73.62% | 0.7557 | 36.57s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.125s | 10.37x |
| 29 | 73.59% | 0.7546 | 36.47s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.129s | 10.37x |
| 30 | 73.98% | 0.7405 | 36.17s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.128s | 10.37x |
| 31 | 74.10% | 0.7427 | 36.73s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.127s | 10.37x |
| 32 | 75.11% | 0.7081 | 36.88s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.128s | 10.37x |
| 33 | 74.95% | 0.7130 | 37.33s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.130s | 10.37x |
| 34 | 75.16% | 0.7066 | 37.45s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.124s | 10.37x |
| 35 | 75.65% | 0.6904 | 36.05s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.134s | 10.37x |
| 36 | 75.82% | 0.6897 | 36.64s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.132s | 10.37x |
| 37 | 75.85% | 0.6890 | 37.67s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.132s | 10.37x |
| 38 | 76.57% | 0.6702 | 36.98s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.216s | 10.37x |
| 39 | 76.93% | 0.6637 | 36.25s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.135s | 10.37x |
| 40 | 76.74% | 0.6604 | 39.99s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.133s | 10.37x |
| 41 | 77.35% | 0.6530 | 36.64s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.132s | 10.37x |
| 42 | 77.32% | 0.6503 | 38.43s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.135s | 10.37x |
| 43 | 77.60% | 0.6457 | 36.70s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.130s | 10.37x |
| 44 | 77.83% | 0.6317 | 40.04s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.135s | 10.37x |
| 45 | 77.96% | 0.6310 | 36.24s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.135s | 10.37x |
| 46 | 77.36% | 0.6379 | 36.56s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.134s | 10.37x |
| 47 | 78.19% | 0.6180 | 36.25s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.135s | 10.37x |
| 48 | 78.35% | 0.6185 | 37.81s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.134s | 10.37x |
| 49 | 78.85% | 0.6029 | 39.00s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.132s | 10.37x |
| 50 | 78.42% | 0.6148 | 37.59s | 33.26s | 12.37s | 839.07 MB | 850 | 850 | 0.133s | 10.37x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 13517.28 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 42400` | 42400 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 3392` | 3392 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `14173891333/42400 = 334290` | 326.45 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.45 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 27034.06 MB |
| 8 | Total Download / 总下载 | `② + ④` | 14823.76 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 41857.82 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 13517.28 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 13517.03 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 13516.78 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 1306.73 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 1899.28 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 2276.61 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 13517.28 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 13517.03 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 13516.78 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 1306.73 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 27034.06 MB = ① + ③
- **Total Download / 总下载:** 14823.76 MB = ② + ④
- **Total Communication / 总通信:** 41857.82 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **78.42%**，测试损失为 **0.6148**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **41857.82 MB**（约 40.88 GB），密文膨胀率为 **10.34x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **1899.28 s**，其中通信时间 **2276.61 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.174s**。**

