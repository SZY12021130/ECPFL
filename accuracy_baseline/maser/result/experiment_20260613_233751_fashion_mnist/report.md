# CKKS-Fed Experiment Report / 实验报告

**Experiment Mode / 实验模式:** CKKS-Fed (Encrypted) / 加密模式  
**Timestamp / 时间戳:** 20260613_233751  
**Output Directory / 输出目录:** `./accuracy_baseline/maser/result\experiment_20260613_233751_fashion_mnist`  

## 1. Configuration Summary / 配置摘要

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Dataset / 数据集 | fashion_mnist | 训练数据集名称 |
| Model / 模型 | lenet | 神经网络架构 |
| Num Clients / 客户端数 | 25 | 参与联邦学习的总客户端数 |
| Num Rounds / 轮数 | 50 | 联邦学习总轮数 |
| Local Epochs / 本地轮数 | 3 | 每轮本地训练epoch数 |
| Batch Size / 批次大小 | 64 | 本地训练批次大小 |
| Learning Rate / 学习率 | 0.001 | SGD优化器学习率 |
| Client Sampling Rate / 采样率 | 1.0 | 每轮参与训练的客户端比例 |
| IID / 独立同分布 | False | 数据分布是否IID |
| Device / 设备 | cpu | 训练设备(CPU/CUDA) |
| Upload Difference / 上传差值 | True | 是否上传模型差值而非完整权重 |

### 1.1 CKKS Parameters / CKKS加密参数

| Parameter / 参数 | Value / 值 | Description / 说明 |
|------------------|-----------|-------------------|
| Poly Modulus Degree / 多项式模数度 | 8192 | CKKS多项式环的维度 |
| Coeff Mod Bit Sizes / 系数模数位宽 | [40, 20, 40] | 系数模数的位宽序列 |
| Global Scale / 全局缩放因子 | 1048576 | CKKS编码缩放因子 |
| Slot Packing / 槽打包 | True | 是否启用SIMD槽打包 |

## 2. Key Metrics Summary / 关键指标汇总

| Metric / 指标 | Value / 数值 | Description / 含义 |
|---------------|-------------|-------------------|
| Final Test Accuracy / 最终测试准确率 | **88.99%** | 全局模型在测试集上的最终精度 |
| Final Test Loss / 最终测试损失 | 0.3389 | 全局模型在测试集上的交叉熵损失 |
| Total Real CPU Time / 总真实CPU时间 | 1700.08 s | 单机串行执行的实际耗时 |
| Total Simulated Time / 总模拟时间 | 2348.89 s | 含网络传输的模拟 wall-clock 时间（可横向对比） |
| Avg Real Round Time / 平均真实轮次时间 | 34.00 s | 真实 CPU 平均每轮耗时 |
| Avg Sim Round Time / 平均模拟轮次时间 | 46.98 s | 模拟 wall-clock 平均每轮耗时 |
| Total Communication / 总通信量 | 3511.76 MB | 所有轮次上传+下载之和 |
| Total Upload / 总上传量 | 1448.24 MB / 0.00 s | 所有轮次上传开销+时间之和 |
| Total Download / 总下载量 | 2063.52 MB / 0.00 s | 所有轮次下载开销+时间之和 |
| Avg Upload Cost / 平均上传开销 | 28.96 MB | mean(upload_cost)/2^20 |
| Avg Download Cost / 平均下载开销 | 41.27 MB | mean(download_cost)/2^20 |
| Avg Expansion Ratio / 平均密文膨胀率 | 6.84x | 密文大小相对明文的平均倍数 |
| Avg Encryption Time / 平均加密时间 | 0.025 s/client | 每个客户端加密模型更新的平均耗时 |
| Key Distribution Cost / 密钥分发开销 | 315.77 MB | CKKS公钥/Galois密钥分发总字节数 |

## 3. Client Participation & Statistics / 客户端参与统计与详情

| CID | Part / 参与轮次 | CTs / 密文数 |
|-----|----------------|--------------|
| 0 | 50 | 386 |
| 1 | 50 | 386 |
| 2 | 50 | 386 |
| 3 | 50 | 386 |
| 4 | 50 | 386 |
| 5 | 50 | 386 |
| 6 | 50 | 386 |
| 7 | 50 | 386 |
| 8 | 50 | 386 |
| 9 | 50 | 386 |
| 10 | 50 | 386 |
| 11 | 50 | 386 |
| 12 | 50 | 386 |
| 13 | 50 | 386 |
| 14 | 50 | 386 |
| 15 | 50 | 386 |
| 16 | 50 | 386 |
| 17 | 50 | 386 |
| 18 | 50 | 386 |
| 19 | 50 | 386 |
| 20 | 50 | 386 |
| 21 | 50 | 386 |
| 22 | 50 | 386 |
| 23 | 50 | 386 |
| 24 | 50 | 386 |

## 4. Per-Round Results / 每轮详细结果

| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Comm / 通信量 | Encrypt / 加密耗时 | Expansion / 膨胀率 |
|--------------|----------------------|---------------------|----------------------|---------------|---------------------|---------------------|
| 1 | 64.67% | 1.0748 | 44.33s | 67.56 MB | 0.034s | 6.20x |
| 2 | 73.82% | 0.6737 | 41.08s | 63.72 MB | 0.033s | 5.31x |
| 3 | 76.82% | 0.5914 | 44.40s | 67.58 MB | 0.029s | 6.20x |
| 4 | 78.82% | 0.5503 | 44.43s | 67.48 MB | 0.023s | 6.20x |
| 5 | 80.22% | 0.5187 | 44.43s | 67.47 MB | 0.022s | 6.20x |
| 6 | 81.78% | 0.4883 | 44.39s | 67.52 MB | 0.022s | 6.20x |
| 7 | 82.67% | 0.4694 | 44.49s | 67.54 MB | 0.023s | 6.20x |
| 8 | 83.70% | 0.4477 | 44.47s | 67.55 MB | 0.021s | 6.20x |
| 9 | 84.33% | 0.4322 | 44.50s | 67.51 MB | 0.021s | 6.20x |
| 10 | 84.15% | 0.4250 | 44.46s | 67.51 MB | 0.021s | 6.20x |
| 11 | 85.13% | 0.4067 | 44.41s | 67.57 MB | 0.021s | 6.20x |
| 12 | 85.59% | 0.3974 | 47.90s | 71.30 MB | 0.022s | 7.09x |
| 13 | 85.88% | 0.3924 | 47.82s | 71.28 MB | 0.022s | 7.08x |
| 14 | 85.87% | 0.3856 | 44.39s | 67.54 MB | 0.023s | 6.20x |
| 15 | 86.31% | 0.3773 | 47.84s | 71.33 MB | 0.021s | 7.08x |
| 16 | 86.72% | 0.3702 | 44.55s | 67.61 MB | 0.021s | 6.20x |
| 17 | 86.58% | 0.3662 | 47.75s | 71.27 MB | 0.021s | 7.08x |
| 18 | 86.88% | 0.3626 | 47.76s | 71.19 MB | 0.020s | 7.08x |
| 19 | 87.08% | 0.3570 | 48.35s | 71.30 MB | 0.021s | 7.08x |
| 20 | 87.14% | 0.3565 | 47.91s | 71.36 MB | 0.021s | 7.09x |
| 21 | 87.18% | 0.3554 | 48.00s | 71.29 MB | 0.021s | 7.08x |
| 22 | 87.67% | 0.3499 | 47.83s | 71.23 MB | 0.020s | 7.08x |
| 23 | 87.71% | 0.3477 | 48.08s | 71.31 MB | 0.021s | 7.08x |
| 24 | 87.84% | 0.3464 | 47.90s | 71.30 MB | 0.021s | 7.08x |
| 25 | 87.90% | 0.3453 | 47.84s | 71.36 MB | 0.021s | 7.08x |
| 26 | 87.92% | 0.3426 | 47.80s | 71.26 MB | 0.026s | 7.08x |
| 27 | 87.96% | 0.3410 | 48.18s | 71.32 MB | 0.030s | 7.09x |
| 28 | 87.91% | 0.3379 | 47.87s | 71.28 MB | 0.024s | 7.08x |
| 29 | 88.16% | 0.3358 | 48.05s | 71.34 MB | 0.021s | 7.09x |
| 30 | 88.13% | 0.3387 | 47.89s | 71.24 MB | 0.019s | 7.08x |
| 31 | 88.15% | 0.3373 | 47.86s | 71.25 MB | 0.019s | 7.09x |
| 32 | 88.28% | 0.3350 | 48.06s | 71.33 MB | 0.019s | 7.08x |
| 33 | 88.48% | 0.3337 | 48.13s | 71.33 MB | 0.018s | 7.08x |
| 34 | 88.24% | 0.3335 | 48.28s | 71.24 MB | 0.018s | 7.09x |
| 35 | 88.49% | 0.3331 | 48.04s | 71.25 MB | 0.019s | 7.08x |
| 36 | 88.48% | 0.3320 | 47.84s | 71.37 MB | 0.019s | 7.08x |
| 37 | 88.67% | 0.3318 | 47.95s | 71.24 MB | 0.018s | 7.09x |
| 38 | 88.67% | 0.3325 | 48.21s | 71.31 MB | 0.018s | 7.09x |
| 39 | 88.66% | 0.3330 | 47.86s | 71.24 MB | 0.018s | 7.09x |
| 40 | 88.72% | 0.3362 | 47.90s | 71.22 MB | 0.018s | 7.08x |
| 41 | 88.73% | 0.3344 | 47.94s | 71.32 MB | 0.019s | 7.08x |
| 42 | 88.73% | 0.3332 | 47.92s | 71.34 MB | 0.019s | 7.09x |
| 43 | 88.61% | 0.3372 | 47.94s | 71.28 MB | 0.018s | 7.08x |
| 44 | 88.89% | 0.3386 | 47.97s | 71.35 MB | 0.018s | 7.09x |
| 45 | 88.51% | 0.3369 | 48.02s | 71.27 MB | 0.019s | 7.09x |
| 46 | 88.74% | 0.3358 | 47.73s | 71.27 MB | 0.018s | 7.09x |
| 47 | 88.86% | 0.3399 | 48.46s | 71.26 MB | 0.017s | 7.08x |
| 48 | 88.78% | 0.3362 | 47.93s | 71.25 MB | 0.019s | 7.08x |
| 49 | 88.79% | 0.3376 | 47.91s | 71.28 MB | 0.021s | 7.08x |
| 50 | 88.99% | 0.3389 | 47.84s | 71.21 MB | 0.018s | 7.08x |

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
| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = 1518593791` | 1448.24 MB |
| 3 | Total CT Blocks / 总密文块 | `sum(num_ciphertexts) = 9650` | 9650 blocks |
| 4 | Total Upload / 总上传 | `sum(upload_cost) = 1518593791` | 1448.24 MB |
| 5 | Total Download / 总下载 | `model_size(177704) * selected(1250) = 2163752425` | 2063.52 MB |
| 6 | Total Communication / 总通信 | `1518593791 + 2163752425 = 3682346216` | 3511.76 MB |
| 7 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = 6.8365` | 6.84x |

## 6. Conclusion / 结论

- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。
- **Accuracy / 准确率:** 经过 **50** 轮训练，最终测试准确率达到 **88.99%**，测试损失为 **0.3389**。
- **Communication Overhead / 通信开销:** CKKS 密文引入 **6.84x** 的通信膨胀率。
- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **0.025s**。
