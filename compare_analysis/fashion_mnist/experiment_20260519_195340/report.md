# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260519_195340  
**Output Directory / 输出目录:** `./compare_analysis/fashion_mnist\experiment_20260519_195340`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | fashion_mnist | 训练数据集名称 |
| Model / 模型 | cnn_fmnist | 神经网络架构 |
| Num Clients / 客户端数 | 100 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 30 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练epoch数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD优化器学习率 |
| Client Sampling Rate / 采样率 | 0.3 | 每轮参与训练的客户端比例 |
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
| Final Test Accuracy / 最终测试准确率 | **11.23%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 2.3058 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1223.88 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 297.34 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Avg Real Round Time / 平均真实轮次时间 | 40.80 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 9.91 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 860.77 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 0.00 MB / 0.00 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 860.77 MB / 0.00 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 0.00 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 28.69 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 0.00x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.018 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 3383.57 MB | CKKS公钥/Galois密钥分发总字节数 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 |
|-----|----------------|--------------|
| 0 | 12 | 0 |
| 1 | 8 | 0 |
| 2 | 5 | 0 |
| 3 | 10 | 0 |
| 4 | 11 | 0 |
| 5 | 10 | 0 |
| 6 | 5 | 0 |
| 7 | 11 | 0 |
| 8 | 10 | 0 |
| 9 | 7 | 0 |
| 10 | 13 | 0 |
| 11 | 7 | 0 |
| 12 | 10 | 0 |
| 13 | 4 | 0 |
| 14 | 7 | 0 |
| 15 | 10 | 0 |
| 16 | 8 | 0 |
| 17 | 7 | 0 |
| 18 | 6 | 0 |
| 19 | 8 | 0 |
| 20 | 11 | 0 |
| 21 | 13 | 0 |
| 22 | 6 | 0 |
| 23 | 9 | 0 |
| 24 | 8 | 0 |
| 25 | 12 | 0 |
| 26 | 7 | 0 |
| 27 | 8 | 0 |
| 28 | 9 | 0 |
| 29 | 8 | 0 |
| 30 | 6 | 0 |
| 31 | 10 | 0 |
| 32 | 6 | 0 |
| 33 | 5 | 0 |
| 34 | 5 | 0 |
| 35 | 11 | 0 |
| 36 | 5 | 0 |
| 37 | 15 | 0 |
| 38 | 12 | 0 |
| 39 | 8 | 0 |
| 40 | 8 | 0 |
| 41 | 9 | 0 |
| 42 | 7 | 0 |
| 43 | 5 | 0 |
| 44 | 11 | 0 |
| 45 | 9 | 0 |
| 46 | 12 | 0 |
| 47 | 10 | 0 |
| 48 | 11 | 0 |
| 49 | 11 | 0 |
| 50 | 6 | 0 |
| 51 | 10 | 0 |
| 52 | 10 | 0 |
| 53 | 9 | 0 |
| 54 | 11 | 0 |
| 55 | 13 | 0 |
| 56 | 10 | 0 |
| 57 | 11 | 0 |
| 58 | 9 | 0 |
| 59 | 15 | 0 |
| 60 | 5 | 0 |
| 61 | 10 | 0 |
| 62 | 6 | 0 |
| 63 | 10 | 0 |
| 64 | 10 | 0 |
| 65 | 9 | 0 |
| 66 | 7 | 0 |
| 67 | 6 | 0 |
| 68 | 9 | 0 |
| 69 | 7 | 0 |
| 70 | 14 | 0 |
| 71 | 5 | 0 |
| 72 | 15 | 0 |
| 73 | 4 | 0 |
| 74 | 7 | 0 |
| 75 | 12 | 0 |
| 76 | 4 | 0 |
| 77 | 14 | 0 |
| 78 | 9 | 0 |
| 79 | 12 | 0 |
| 80 | 14 | 0 |
| 81 | 11 | 0 |
| 82 | 8 | 0 |
| 83 | 14 | 0 |
| 84 | 8 | 0 |
| 85 | 3 | 0 |
| 86 | 8 | 0 |
| 87 | 8 | 0 |
| 88 | 8 | 0 |
| 89 | 9 | 0 |
| 90 | 11 | 0 |
| 91 | 7 | 0 |
| 92 | 12 | 0 |
| 93 | 5 | 0 |
| 94 | 9 | 0 |
| 95 | 7 | 0 |
| 96 | 14 | 0 |
| 97 | 9 | 0 |
| 98 | 9 | 0 |
| 99 | 11 | 0 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 11.23% | 2.3058 | 8.63s | 28.68 MB | 0.019s | 0.00x |
| 2 | 11.23% | 2.3058 | 9.46s | 28.71 MB | 0.018s | 0.00x |
| 3 | 11.23% | 2.3058 | 10.20s | 28.70 MB | 0.017s | 0.00x |
| 4 | 11.23% | 2.3058 | 10.04s | 28.68 MB | 0.016s | 0.00x |
| 5 | 11.23% | 2.3058 | 9.61s | 28.69 MB | 0.016s | 0.00x |
| 6 | 11.23% | 2.3058 | 9.54s | 28.69 MB | 0.017s | 0.00x |
| 7 | 11.23% | 2.3058 | 9.97s | 28.67 MB | 0.016s | 0.00x |
| 8 | 11.23% | 2.3058 | 10.19s | 28.69 MB | 0.013s | 0.00x |
| 9 | 11.23% | 2.3058 | 9.80s | 28.70 MB | 0.012s | 0.00x |
| 10 | 11.23% | 2.3058 | 9.94s | 28.70 MB | 0.012s | 0.00x |
| 11 | 11.23% | 2.3058 | 10.10s | 28.69 MB | 0.012s | 0.00x |
| 12 | 11.23% | 2.3058 | 9.81s | 28.70 MB | 0.012s | 0.00x |
| 13 | 11.23% | 2.3058 | 9.77s | 28.68 MB | 0.012s | 0.00x |
| 14 | 11.23% | 2.3058 | 10.17s | 28.70 MB | 0.012s | 0.00x |
| 15 | 11.23% | 2.3058 | 9.82s | 28.69 MB | 0.012s | 0.00x |
| 16 | 11.23% | 2.3058 | 9.65s | 28.70 MB | 0.012s | 0.00x |
| 17 | 11.23% | 2.3058 | 10.04s | 28.70 MB | 0.012s | 0.00x |
| 18 | 11.23% | 2.3058 | 10.08s | 28.69 MB | 0.013s | 0.00x |
| 19 | 11.23% | 2.3058 | 10.22s | 28.69 MB | 0.012s | 0.00x |
| 20 | 11.23% | 2.3058 | 10.00s | 28.69 MB | 0.012s | 0.00x |
| 21 | 11.23% | 2.3058 | 10.11s | 28.70 MB | 0.012s | 0.00x |
| 22 | 11.23% | 2.3058 | 9.92s | 28.70 MB | 0.012s | 0.00x |
| 23 | 11.23% | 2.3058 | 10.03s | 28.69 MB | 0.012s | 0.00x |
| 24 | 11.23% | 2.3058 | 10.05s | 28.69 MB | 0.012s | 0.00x |
| 25 | 11.23% | 2.3058 | 10.19s | 28.70 MB | 0.012s | 0.00x |
| 26 | 11.23% | 2.3058 | 10.16s | 28.69 MB | 0.012s | 0.00x |
| 27 | 11.23% | 2.3058 | 10.22s | 28.67 MB | 0.012s | 0.00x |
| 28 | 11.23% | 2.3058 | 9.58s | 28.70 MB | 0.012s | 0.00x |
| 29 | 11.23% | 2.3058 | 10.07s | 28.70 MB | 0.012s | 0.00x |
| 30 | 11.23% | 2.3058 | 9.99s | 28.69 MB | 0.012s | 0.00x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 144036000` | 137.36 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 0` | 0.00 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 0` | 0 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 0` | 0.00 MB |
| 5 | Total Download / 总下载 | `model_size(160040) * selected(900) = 902583810` | 860.77 MB |
| 6 | Total Communication / 总通信 | `0 + 902583810 = 902583810` | 860.77 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 0.0000` | 0.00x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **30** 轮训练，最终测试准确率达到 **11.23%**，测试损失为 **2.3058**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **0.00x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.018s**。
