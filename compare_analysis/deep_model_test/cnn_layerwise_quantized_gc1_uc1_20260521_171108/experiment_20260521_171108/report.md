# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260521_171108  
**Output Directory / 输出目录:** `E:\GithubProjects\ckks_fed_robustness\compare_analysis\deep_model_test\cnn_layerwise_quantized_gc1_uc1_20260521_171108\experiment_20260521_171108`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | cifar10 | 训练数据集名称 |
| Model / 模型 | cnn | 神经网络架构 |
| Num Clients / 客户端数 | 100 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 3 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 2 | 每轮本地训练epoch数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.0005 | SGD优化器学习率 |
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
| Final Test Accuracy / 最终测试准确率 | **17.69%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 2.1367 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 264.55 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 1135.48 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Avg Real Round Time / 平均真实轮次时间 | 44.09 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 189.25 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 2761.94 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 1348.56 MB / 0.00 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 1413.38 MB / 0.00 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 224.76 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 235.56 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 20.80x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.269 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 3383.28 MB | CKKS公钥/Galois密钥分发总字节数 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 |
|-----|----------------|--------------|
| 0 | 3 | 94 |
| 1 | 1 | 47 |
| 2 | 1 | 47 |
| 3 | 3 | 94 |
| 4 | 2 | 47 |
| 5 | 2 | 47 |
| 6 | 2 | 94 |
| 7 | 1 | 0 |
| 8 | 0 | 0 |
| 9 | 4 | 47 |
| 10 | 4 | 141 |
| 11 | 1 | 47 |
| 12 | 2 | 0 |
| 13 | 2 | 47 |
| 14 | 4 | 141 |
| 15 | 3 | 47 |
| 16 | 1 | 0 |
| 17 | 3 | 94 |
| 18 | 2 | 0 |
| 19 | 2 | 94 |
| 20 | 2 | 0 |
| 21 | 1 | 0 |
| 22 | 1 | 0 |
| 23 | 2 | 47 |
| 24 | 1 | 47 |
| 25 | 1 | 0 |
| 26 | 4 | 94 |
| 27 | 0 | 0 |
| 28 | 1 | 0 |
| 29 | 0 | 0 |
| 30 | 2 | 0 |
| 31 | 3 | 94 |
| 32 | 1 | 47 |
| 33 | 2 | 47 |
| 34 | 1 | 47 |
| 35 | 1 | 47 |
| 36 | 0 | 0 |
| 37 | 3 | 94 |
| 38 | 1 | 47 |
| 39 | 3 | 47 |
| 40 | 4 | 94 |
| 41 | 2 | 94 |
| 42 | 4 | 94 |
| 43 | 0 | 0 |
| 44 | 4 | 94 |
| 45 | 2 | 0 |
| 46 | 1 | 0 |
| 47 | 0 | 0 |
| 48 | 1 | 0 |
| 49 | 3 | 94 |
| 50 | 1 | 0 |
| 51 | 1 | 47 |
| 52 | 1 | 47 |
| 53 | 4 | 47 |
| 54 | 2 | 47 |
| 55 | 3 | 47 |
| 56 | 2 | 47 |
| 57 | 1 | 0 |
| 58 | 2 | 94 |
| 59 | 1 | 0 |
| 60 | 3 | 47 |
| 61 | 2 | 47 |
| 62 | 1 | 47 |
| 63 | 0 | 0 |
| 64 | 1 | 47 |
| 65 | 2 | 47 |
| 66 | 1 | 0 |
| 67 | 0 | 0 |
| 68 | 1 | 47 |
| 69 | 1 | 0 |
| 70 | 1 | 0 |
| 71 | 1 | 0 |
| 72 | 2 | 47 |
| 73 | 2 | 0 |
| 74 | 3 | 94 |
| 75 | 1 | 0 |
| 76 | 1 | 0 |
| 77 | 4 | 94 |
| 78 | 0 | 0 |
| 79 | 2 | 47 |
| 80 | 2 | 47 |
| 81 | 1 | 47 |
| 82 | 1 | 0 |
| 83 | 4 | 47 |
| 84 | 3 | 94 |
| 85 | 2 | 47 |
| 86 | 0 | 0 |
| 87 | 2 | 47 |
| 88 | 4 | 94 |
| 89 | 2 | 47 |
| 90 | 3 | 94 |
| 91 | 2 | 94 |
| 92 | 1 | 47 |
| 93 | 3 | 47 |
| 94 | 3 | 94 |
| 95 | 0 | 0 |
| 96 | 2 | 47 |
| 97 | 1 | 47 |
| 98 | 1 | 47 |
| 99 | 2 | 47 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 9.54% | 2.3045 | 8.00s | 21.61 MB | 0.277s | 20.80x |
| 2 | 9.54% | 2.3045 | 8.02s | 21.61 MB | 0.296s | 20.80x |
| 3 | 9.54% | 2.3045 | 8.09s | 21.61 MB | 0.295s | 20.80x |
| 4 | 9.18% | 2.3045 | 370.26s | 899.03 MB | 0.289s | 0.00x |
| 5 | 19.55% | 2.2344 | 370.77s | 899.05 MB | 0.283s | 0.00x |
| 6 | 17.69% | 2.1367 | 370.35s | 899.02 MB | 0.286s | 0.00x |

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
| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = 67971600` | 64.82 MB |
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 1414065353` | 1348.56 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 4230` | 4230 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 1414065353` | 1348.56 MB |
| 5 | Total Download / 总下载 | `model_size(755240) * selected(180) = 1482033990` | 1413.38 MB |
| 6 | Total Communication / 总通信 | `1414065353 + 1482033990 = 2896099343` | 2761.94 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 20.8038` | 20.80x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **6** 轮训练，最终测试准确率达到 **17.69%**，测试损失为 **2.1367**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **20.80x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.269s**。
