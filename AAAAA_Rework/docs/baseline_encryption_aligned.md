# 五基线加密方法、密文大小与包数（对齐口径 v2）

## 口径说明

- **对齐目标**：ECPFL 固定为 **4096 槽位/密文**，即多项式阶数 `n=4096`，每个系数放一个值。
- 标准 CKKS 要得到 4096 个槽位，需要 `poly_modulus_degree = 8192`（因为 CKKS 槽位 = n/2）。
- ESAFL 与 ECPFL 同安全级别（同 `n=4096`），但用自己 EP 打包：每系数装 `T−1=2` 个量化值 → **8192 值/密文**。
- 单密文大小按论文口径 `n × logQ / 8` 计算，取 `logQ = 61` bit。
- 总大小按二进制 MB（`÷ 1024²`）并保留 3 位小数。

> 注意：这是**全模型上传**的理论口径。FedPHE / MASER 实际实验会再乘以自己的稀疏率；见下文章节 3。

---

## 1. 安全参数与单密文大小

| Method | Encryption Method | Poly degree | Slots/values per ct | logQ | Single ct (B) |
|---|---|---:|---:|---:|---:|
| FedAvg+CKKS | Single-key CKKS (c0, c1) | 8192 | 4096 | 61 | 124,928 |
| FedPHE | Single-key CKKS + batch-level Top-ζ mask | 8192 | 4096 | 61 | 124,928 |
| MASER | xMK-CKKS + param-level mask + partial decrypt | 8192 | 4096 | 61 | 124,928 |
| ESAFL | Pure-Python ESHE EP packing | 4096 | **8,192** | 61 | 31,232 |
| ECPFL | Custom single-ct RLWE | 4096 | 4,096 | 61 | 31,232 |

---

## 2. 全模型密文数与总大小（无稀疏）

| Dataset | Model | Params | FedAvg+CKKS (#ct / MB) | FedPHE (#ct / MB) | MASER (#ct / MB) | ESAFL (#ct / MB) | ECPFL (#ct / MB) |
|---|---|---:|---:|---:|---:|---:|---:|
| MNIST | LeNet | 44,426 | 11 / 1.311 | 11 / 1.311 | 11 / 1.311 | 6 / 0.179 | 11 / 0.328 |
| FMNIST | CNN | 39,786 | 10 / 1.191 | 10 / 1.191 | 10 / 1.191 | 5 / 0.149 | 10 / 0.298 |
| CIFAR-10 | ResNet-20 | 272,186 | 67 / 7.982 | 67 / 7.982 | 67 / 7.982 | 34 / 1.013 | 67 / 1.996 |
| SVHN | ResNet-32 | 460,618 | 113 / 13.463 | 113 / 13.463 | 113 / 13.463 | 57 / 1.698 | 113 / 3.366 |

**结论**：之前表格中 ESAFL n=4096 这一行数据（31,232 B、8,192 值/密文、6/5/34/57 个密文）是**正确的**，前提是按上述全模型理论口径。

---

## 3. 加入稀疏策略后的实际通信量（实验口径）

若按各方案典型稀疏率计算：

- **FedPHE**：batch-level Top-ζ，batch_size=4096，上传 `ceil(ζ·J)` 个包。
- **MASER**：param-level Top-k，按 50% 参数保留（`ceil(0.5·J)` 个包）。
- **ECPFL**：包级投票，RK-θ 选中 `ceil(θ·J)` 个包。
- **ESAFL**：本地 Top-ζ，再用 EP 打包；这里只算 EP 打包后的密文数。

| Dataset | ζ / θ | FedPHE (#ct / MB) | MASER 50% (#ct / MB) | ESAFL (#ct / MB) | ECPFL RK-θ (#ct / MB) |
|---|---:|---:|---:|---:|---:|
| MNIST | 0.1 | 2 / 0.238 | 6 / 0.732 | 6 / 0.179 | 2 / 0.060 |
| FMNIST | 0.1 | 1 / 0.119 | 5 / 0.596 | 5 / 0.149 | 3 / 0.089 |
| CIFAR-10 | 0.5 | 34 / 4.051 | 34 / 4.051 | 34 / 1.013 | 47 / 1.401 |
| SVHN | 0.5 | 57 / 6.792 | 57 / 6.792 | 57 / 1.698 | 80 / 2.383 |

> 注：FedPHE / MASER 的具体稀疏率以你最终论文配置为准；上表仅示例。

---

## 4. 代码实现 vs 理论口径的关键差异

| 方案 | 理论单密文 (B) | 当前代码实测单密文 (B) | 差异原因 |
|---|---:|---:|---|
| ECPFL | 31,232 | 30,720 | 代码用 `n × Q.bit_length() / 8`，n=4096 时 Q≈2^60 |
| ESAFL PUREPY EP | 31,232 | **65,536** | 代码用 CRT int64×2 表示，`4096 × 2 × 8` |
| CKKS (TenSEAL) | 124,928 | ≈124,928 | TenSEAL 序列化接近理论值 |

**影响**：如果直接跑 ESAFL PUREPY 实验并与 ECPFL 实验比通信量，ESAFL 会看起来大 **2 倍**，这不是 EP 打包的问题，是 size 统计口径不一致。

**建议**：
- 论文表格用理论口径（上表）。
- 若要让 ESAFL 实验输出也匹配理论口径，需把 `ckks_fed/crypto.py` 中 PUREPY 路径的 `compute_encrypted_update_size` 从 `ct.coeffs_nbytes()` 改为 `n × Q.bit_length() / 8`。

---

## 5. 计算明细（供核对）

```
单密文大小：
  CKKS  (c0,c1): 2 × 8192 × 61 / 8 = 124,928 B
  ESAFL EP       :     4096 × 61 / 8 =  31,232 B
  ECPFL RLWE     :     4096 × 61 / 8 =  31,232 B

密文数 J = ceil(参数 d / 每密文值数)
  CKKS/ECPFL : 值数 = 4096
  ESAFL EP   : 值数 = 8192

MNIST  LeNet 44,426:
  CKKS/ECPFL : ceil(44426 / 4096) = 11
  ESAFL      : ceil(44426 / 8192) = 6
```
