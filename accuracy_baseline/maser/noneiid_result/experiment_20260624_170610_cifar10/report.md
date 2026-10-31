# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式
**Timestamp / 时间戳:** 20260624
**Output Directory / 输出目录:** `accuracy_baseline/maser/noneiid_result/experiment_20260624_170610_cifar10`

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
| Final Test Accuracy / 最终测试准确率 | **81.34%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.5512 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实 CPU 时间 | 4693.13 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1944.85 s | 含计算与网络传输的模拟 wall-clock 时间（每轮取最慢客户端） |
| Total Simulated Comm Time / 总模拟通信时间 | 2314.63 s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |
| Avg Real Round Time / 平均真实轮次时间 | 93.86 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 38.90 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 42551.65 MB | 所有轮次上传+下载之和（理想 xMK-CKKS） |
| Total Upload / 总上传量 | 27496.61 MB / 1687.64 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 15055.04 MB / 626.99 s | 所有轮次下载开销+时间之和 |
| MASER ① 加密上传 | 13748.44 MB | 客户端原始密文更新上传累计 |
| MASER ② 聚合密文广播 | 13748.31 MB | 服务器聚合后密文下发给客户端做 partial decrypt（聚合密文=单密文） |
| MASER ③ 解密份额上传 | 13748.17 MB | 客户端 partial decrypt 份额回传累计（聚合密文=单密文） |
| MASER ④ 明文模型下发 | 1306.73 MB | 服务器解密后下发明文全局模型累计 |
| Avg Upload Cost / 平均上传开销 | 549.93 MB | 平均每轮上传通信量 |
| Avg Download Cost / 平均下载开销 | 301.10 MB | 平均每轮下载通信量 |
| Avg Expansion Ratio / 平均密文膨胀率 | 10.52x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.206 s/client | 每个客户端加密模型更新的平均耗时 |
| Total CT Blocks (Upload) / 总密文上传块数 | 43125 blocks | 所有客户端所有轮次上传的密文块总数 |
| Total Aggregated CTs (Download) / 总聚合密文下载数 | 3450 blocks | 服务器聚合后广播的密文块总数 |
| Avg Single Ciphertext Size / 平均单密文大小 | 334291 bytes | 单个客户端密文块的平均大小 |
| Avg Aggregated CT Size / 平均聚合密文大小 | 334291 bytes | 服务器聚合后密文块的平均大小（理想 xMK-CKKS：S_agg = S） |
| Key Distribution Cost / 密钥分发开销 | 861.46 MB | CKKS 公钥/Galois 密钥分发总字节数 |
| CT Upload Time / 密文上传时间 | 1687.64 s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |
| CT Download Time / 密文下载时间 | 626.99 s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |
|-----|----------------|--------------|------------------|------------------|
| 0 | 50 | 1725 | 31013 kbps | 30222 kbps |
| 1 | 50 | 1725 | 339099 kbps | 472285 kbps |
| 2 | 50 | 1725 | 254789 kbps | 181815 kbps |
| 3 | 50 | 1725 | 96962 kbps | 99657 kbps |
| 4 | 50 | 1725 | 39759 kbps | 18071 kbps |
| 5 | 50 | 1725 | 27438 kbps | 26345 kbps |
| 6 | 50 | 1725 | 105349 kbps | 21922 kbps |
| 7 | 50 | 1725 | 269298 kbps | 67032 kbps |
| 8 | 50 | 1725 | 28807 kbps | 12061 kbps |
| 9 | 50 | 1725 | 54690 kbps | 5467 kbps |
| 10 | 50 | 1725 | 41651 kbps | 44816 kbps |
| 11 | 50 | 1725 | 8057 kbps | 8610 kbps |
| 12 | 50 | 1725 | 279465 kbps | 261900 kbps |
| 13 | 50 | 1725 | 227204 kbps | 21076 kbps |
| 14 | 50 | 1725 | 93105 kbps | 23265 kbps |
| 15 | 50 | 1725 | 29282 kbps | 27951 kbps |
| 16 | 50 | 1725 | 123339 kbps | 36087 kbps |
| 17 | 50 | 1725 | 17150 kbps | 14397 kbps |
| 18 | 50 | 1725 | 93249 kbps | 6653 kbps |
| 19 | 50 | 1725 | 144829 kbps | 67399 kbps |
| 20 | 50 | 1725 | 103970 kbps | 9934 kbps |
| 21 | 50 | 1725 | 110526 kbps | 11922 kbps |
| 22 | 50 | 1725 | 650580 kbps | 37402 kbps |
| 23 | 50 | 1725 | 231919 kbps | 22700 kbps |
| 24 | 50 | 1725 | 329695 kbps | 19824 kbps |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Sim Round Time / 模拟轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|------------------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|
| 1 | 22.12% | 2.0517 | 34.72s | 31.31s | 11.71s | 791.26 MB | 800 | 800 | 0.135s | 9.76x |
| 2 | 42.21% | 1.5623 | 37.69s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.132s | 10.37x |
| 3 | 47.15% | 1.4395 | 37.60s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.129s | 10.37x |
| 4 | 51.66% | 1.3365 | 39.29s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.240s | 10.37x |
| 5 | 55.06% | 1.2381 | 38.91s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.226s | 10.37x |
| 6 | 57.56% | 1.1683 | 40.71s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.229s | 10.67x |
| 7 | 59.88% | 1.1118 | 38.28s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.225s | 10.67x |
| 8 | 61.77% | 1.0616 | 40.16s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.229s | 10.67x |
| 9 | 63.31% | 1.0246 | 39.75s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.232s | 10.67x |
| 10 | 63.96% | 0.9999 | 39.58s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.225s | 10.67x |
| 11 | 64.65% | 0.9848 | 40.23s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.225s | 10.67x |
| 12 | 67.05% | 0.9307 | 39.78s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.226s | 10.67x |
| 13 | 67.52% | 0.9140 | 39.57s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.226s | 10.67x |
| 14 | 68.49% | 0.8840 | 39.92s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.228s | 10.67x |
| 15 | 69.61% | 0.8597 | 39.80s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.238s | 10.67x |
| 16 | 70.21% | 0.8398 | 38.88s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.219s | 10.67x |
| 17 | 70.95% | 0.8192 | 39.50s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.223s | 10.67x |
| 18 | 72.00% | 0.8003 | 39.19s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.224s | 10.67x |
| 19 | 72.62% | 0.7758 | 40.02s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.227s | 10.67x |
| 20 | 72.74% | 0.7749 | 39.49s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.228s | 10.67x |
| 21 | 73.33% | 0.7628 | 38.30s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.137s | 10.67x |
| 22 | 74.51% | 0.7360 | 38.28s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.140s | 10.67x |
| 23 | 74.47% | 0.7294 | 38.03s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.126s | 10.67x |
| 24 | 75.02% | 0.7179 | 38.28s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.129s | 10.67x |
| 25 | 75.18% | 0.7147 | 38.10s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.130s | 10.67x |
| 26 | 75.64% | 0.6967 | 38.42s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.150s | 10.67x |
| 27 | 76.55% | 0.6839 | 39.92s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.228s | 10.67x |
| 28 | 76.90% | 0.6744 | 39.13s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.230s | 10.67x |
| 29 | 77.02% | 0.6672 | 39.22s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.127s | 10.67x |
| 30 | 77.44% | 0.6603 | 38.24s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.134s | 10.67x |
| 31 | 77.46% | 0.6546 | 37.50s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 32 | 77.61% | 0.6483 | 39.54s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.226s | 10.67x |
| 33 | 78.31% | 0.6385 | 38.25s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 34 | 78.12% | 0.6340 | 39.22s | 34.24s | 12.71s | 862.99 MB | 875 | 875 | 0.221s | 10.67x |
| 35 | 78.68% | 0.6206 | 38.49s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.230s | 10.37x |
| 36 | 79.09% | 0.6139 | 39.23s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.224s | 10.37x |
| 37 | 79.29% | 0.6102 | 39.30s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.219s | 10.37x |
| 38 | 79.17% | 0.6088 | 38.53s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 39 | 79.63% | 0.6014 | 39.21s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.224s | 10.37x |
| 40 | 79.60% | 0.6006 | 38.34s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 41 | 80.25% | 0.5900 | 38.91s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.225s | 10.37x |
| 42 | 80.13% | 0.5872 | 39.03s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.224s | 10.37x |
| 43 | 80.37% | 0.5808 | 39.19s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.226s | 10.37x |
| 44 | 80.62% | 0.5762 | 38.34s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 45 | 80.42% | 0.5755 | 38.78s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.222s | 10.37x |
| 46 | 81.02% | 0.5660 | 37.98s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.223s | 10.37x |
| 47 | 81.11% | 0.5638 | 38.78s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.220s | 10.37x |
| 48 | 80.96% | 0.5657 | 39.65s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.222s | 10.37x |
| 49 | 81.22% | 0.5595 | 38.35s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.229s | 10.37x |
| 50 | 81.34% | 0.5512 | 39.23s | 33.26s | 12.37s | 839.08 MB | 850 | 850 | 0.224s | 10.37x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size)` | 13748.44 MB |
| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = 43125` | 43125 blocks |
| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = 3450` | 3450 blocks |
| 5 | Avg Single CT Size / 平均单密文大小 | `14416286429/43125 = 334291` | 326.46 KB |
| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `S_agg = S_single` (理想 xMK-CKKS) | 326.46 KB |
| 7 | Total Upload / 总上传 | `① + ③` | 27496.61 MB |
| 8 | Total Download / 总下载 | `② + ④` | 15055.04 MB |
| 9 | Total Communication / 总通信 | `① + ② + ③ + ④` | 42551.65 MB |
| 10 | MASER ① 加密上传 | `sum(maser_ct_upload)` | 13748.44 MB |
| 11 | MASER ② 聚合密文广播 | `Σ 25 * nb * single_ct` | 13748.31 MB |
| 12 | MASER ③ 解密份额上传 | `Σ 25 * nb * single_ct` | 13748.17 MB |
| 13 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download)` | 1306.73 MB |
| 14 | Total Simulated Time / 总模拟时间 | `Σ max_c(local_train + ul + dl)` | 1944.85 s |
| 15 | Total Simulated Comm Time / 总模拟通信时间 | `Σ max(ul) + Σ max(dl)` | 2314.63 s |

### 5.2.1 MASER Communication Structure / MASER 通信结构

- **① Encrypted Upload / 加密上传:** 13748.44 MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新
- **② Aggregated CT Broadcast / 聚合密文广播:** 13748.31 MB — 服务器聚合后的密文下发给所有客户端（理想 xMK-CKKS：S_agg = S_single）
- **③ Partial Decryption Upload / 解密份额上传:** 13748.17 MB — 客户端 partial decrypt 份额回传（理想 xMK-CKKS）
- **④ Plaintext Model Download / 明文模型下发:** 1306.73 MB — 服务器解密后下发明文全局模型
- **Total Upload / 总上传:** 27496.61 MB = ① + ③
- **Total Download / 总下载:** 15055.04 MB = ② + ④
- **Total Communication / 总通信:** 42551.65 MB = ① + ② + ③ + ④
  ✅ 验证通过：分量加总与总上传/总下载一致

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **81.34%**，测试损失为 **0.5512**。
- **Communication Overhead / 通信开销:** 在理想 xMK-CKKS 假设下，MASER 总通信量为 **42551.65 MB**（约 41.55 GB），密文膨胀率为 **10.52x**。**
- **End-to-End Simulated Time / 端到端模拟时间:** 按每轮最慢客户端计算，总模拟时间为 **1944.85 s**，其中通信时间 **2314.63 s**。**
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.206s**。**

