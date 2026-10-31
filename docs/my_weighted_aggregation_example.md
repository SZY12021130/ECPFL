# 我的方案 vs FedPHE：加权聚合数学例子对比

> 说明：我的方案（`crypto.py`）和 FedPHE（`server.py`）在数学上等价，但归一化时机不同。
>
> - **我的方案**：聚合时直接做加权平均（先除后加）
> - **FedPHE**：聚合时只累加不加权（先加后除），解密时再除以 `sum_mask`

---

## 一、场景设定

| 参数 | 取值 |
|------|------|
| 客户端 | 3 个（C1, C2, C3） |
| 权重 | $w_1 = 0.3,\; w_2 = 0.5,\; w_3 = 0.2$ |
| Batch 总数 | $M = 2$ |
| Batch 大小 | $B = 4$ |

### 各客户端选中的 Batch

| 客户端 | 选中 Batch | Mask |
|--------|-----------|------|
| C1 | 0 | `[1, 0]` |
| C2 | 0, 1 | `[1, 1]` |
| C3 | 1 | `[0, 1]` |

### 各客户端提交的明文参数值

| 客户端 | Batch 0 值 | Batch 1 值 |
|--------|-----------|-----------|
| C1 | $[1, 2, 3, 4]$ | — |
| C2 | $[5, 6, 7, 8]$ | $[10, 20, 30, 40]$ |
| C3 | — | $[50, 60, 70, 80]$ |

---

## 二、我的方案：聚合时直接归一化

对应代码：`crypto.py: _aggregate_sparse_updates`

```python
total_w = sum(batch_weights)
norm_weights = [w / total_w for w in batch_weights]
aggregated_batch = self.evaluator.weighted_average(batch_cts, norm_weights)
```

### 2.1 Batch 0 聚合（C1, C2 提交）

**步骤 1：计算归一化权重**

$$
\text{total\_w} = w_1 + w_2 = 0.3 + 0.5 = 0.8
$$

$$
\text{norm\_weights} = \left[\frac{0.3}{0.8},\; \frac{0.5}{0.8}\right] = [0.375,\; 0.625]
$$

**步骤 2：加权平均聚合**

$$
\text{agg}_0 = 0.375 \cdot [1, 2, 3, 4] + 0.625 \cdot [5, 6, 7, 8]
$$

逐项计算：

| 位置 | C1 贡献 $0.375 \times$ | C2 贡献 $0.625 \times$ | 加权和 |
|------|----------------------|----------------------|--------|
| 0 | $0.375 \times 1 = 0.375$ | $0.625 \times 5 = 3.125$ | $\mathbf{3.5}$ |
| 1 | $0.375 \times 2 = 0.75$ | $0.625 \times 6 = 3.75$ | $\mathbf{4.5}$ |
| 2 | $0.375 \times 3 = 1.125$ | $0.625 \times 7 = 4.375$ | $\mathbf{5.5}$ |
| 3 | $0.375 \times 4 = 1.5$ | $0.625 \times 8 = 5.0$ | $\mathbf{6.5}$ |

**聚合结果（密文）**：

$$
\text{Enc}(\text{agg}_0) = \text{Enc}([3.5,\; 4.5,\; 5.5,\; 6.5])
$$

**验证**（与加权平均公式对比）：

$$
\frac{w_1 \cdot [1,2,3,4] + w_2 \cdot [5,6,7,8]}{w_1 + w_2} = \frac{[0.3+2.5,\; 0.6+3.0,\; 0.9+3.5,\; 1.2+4.0]}{0.8} = \frac{[2.8,\; 3.6,\; 4.4,\; 5.2]}{0.8} = [3.5,\; 4.5,\; 5.5,\; 6.5] \; \checkmark
$$

### 2.2 Batch 1 聚合（C2, C3 提交）

**步骤 1：计算归一化权重**

$$
\text{total\_w} = w_2 + w_3 = 0.5 + 0.2 = 0.7
$$

$$
\text{norm\_weights} = \left[\frac{0.5}{0.7},\; \frac{0.2}{0.7}\right] = \left[\frac{5}{7},\; \frac{2}{7}\right] \approx [0.714,\; 0.286]
$$

**步骤 2：加权平均聚合**

$$
\text{agg}_1 = \frac{5}{7} \cdot [10, 20, 30, 40] + \frac{2}{7} \cdot [50, 60, 70, 80]
$$

逐项计算：

| 位置 | C2 贡献 $\frac{5}{7} \times$ | C3 贡献 $\frac{2}{7} \times$ | 加权和 |
|------|---------------------------|---------------------------|--------|
| 0 | $\frac{50}{7} \approx 7.143$ | $\frac{100}{7} \approx 14.286$ | $\frac{150}{7} \approx \mathbf{21.429}$ |
| 1 | $\frac{100}{7} \approx 14.286$ | $\frac{120}{7} \approx 17.143$ | $\frac{220}{7} \approx \mathbf{31.429}$ |
| 2 | $\frac{150}{7} \approx 21.429$ | $\frac{140}{7} = 20.0$ | $\frac{290}{7} \approx \mathbf{41.429}$ |
| 3 | $\frac{200}{7} \approx 28.571$ | $\frac{160}{7} \approx 22.857$ | $\frac{360}{7} \approx \mathbf{51.429}$ |

**聚合结果（密文）**：

$$
\text{Enc}(\text{agg}_1) = \text{Enc}\left(\left[\frac{150}{7},\; \frac{220}{7},\; \frac{290}{7},\; \frac{360}{7}\right]\right)
$$

**验证**：

$$
\frac{w_2 \cdot [10,20,30,40] + w_3 \cdot [50,60,70,80]}{w_2 + w_3} = \frac{[5+10,\; 10+12,\; 15+14,\; 20+16]}{0.7} = \frac{[15,\; 22,\; 29,\; 36]}{0.7} = \left[\frac{150}{7},\; \frac{220}{7},\; \frac{290}{7},\; \frac{360}{7}\right] \; \checkmark
$$

### 2.3 服务器下发结果

```python
{
    '__sparse__': True,
    'ciphertexts': [
        Enc([3.5, 4.5, 5.5, 6.5]),           # Batch 0（已归一化）
        Enc([150/7, 220/7, 290/7, 360/7])     # Batch 1（已归一化）
    ],
    'mask': [1, 1],
    '__sum_weights__': [0.8, 0.7]   # 记录了，但解密时不使用
}
```

### 2.4 客户端解密

对应代码：`crypto.py: decrypt_model_update`

```python
decrypted_batches = self.decryptor.decrypt_chunks(ciphertexts)
# 直接解密，无需再除以 sum_weights！
```

| Batch | 密文内容 | 解密结果 | 是否需要除法 |
|-------|---------|----------|-------------|
| 0 | $\text{Enc}([3.5, 4.5, 5.5, 6.5])$ | $[3.5, 4.5, 5.5, 6.5]$ | ❌ 不需要（已归一化） |
| 1 | $\text{Enc}([150/7, ...])$ | $[150/7, 220/7, 290/7, 360/7]$ | ❌ 不需要（已归一化） |

**最终明文列表**：

$$
\text{plain\_list} = [3.5,\; 4.5,\; 5.5,\; 6.5,\; 21.429,\; 31.429,\; 41.429,\; 51.429]
$$

---

## 三、FedPHE 方案：聚合时不归一化，解密时再除

对应代码：`FedPHE-main/server.py: aggregatie_weights`

```python
frac = ts.ckks_vector(ckks_ctx, [weights_client[c_id]])
res = ts.CKKSVector.load(ckks_ctx, cipher[cnt]) * frac
sum_mask[batch] += weights_client[c_id]
```

### 3.1 Batch 0 聚合（C1, C2 提交）

**步骤 1：密文 × 明文加权（不归一化）**

$$
\text{global\_cipher}[0] = \text{Enc}([1,2,3,4]) \times 0.3 + \text{Enc}([5,6,7,8]) \times 0.5
$$

由 CKKS 同态性质（密文 × 明文 = 明文缩放后的密文，密文 + 密文 = 相加后的密文）：

$$
= \text{Enc}([0.3 \times 1 + 0.5 \times 5,\; 0.3 \times 2 + 0.5 \times 6,\; \dots])
$$

$$
= \text{Enc}([0.3+2.5,\; 0.6+3.0,\; 0.9+3.5,\; 1.2+4.0])
$$

$$
= \text{Enc}([2.8,\; 3.6,\; 4.4,\; 5.2])
$$

**步骤 2：记录权重和**

$$
\text{sum\_mask}[0] = w_1 + w_2 = 0.3 + 0.5 = \mathbf{0.8}
$$

### 3.2 Batch 1 聚合（C2, C3 提交）

**步骤 1：密文 × 明文加权（不归一化）**

$$
\text{global\_cipher}[1] = \text{Enc}([10,20,30,40]) \times 0.5 + \text{Enc}([50,60,70,80]) \times 0.2
$$

$$
= \text{Enc}([5+10,\; 10+12,\; 15+14,\; 20+16])
$$

$$
= \text{Enc}([15,\; 22,\; 29,\; 36])
$$

**步骤 2：记录权重和**

$$
\text{sum\_mask}[1] = w_2 + w_3 = 0.5 + 0.2 = \mathbf{0.7}
$$

### 3.3 服务器下发结果

```python
[
    sum_mask,      # [0.8, 0.7]
    global_cipher  # [Enc([2.8,3.6,4.4,5.2]), Enc([15,22,29,36])]
]
```

### 3.4 客户端解密

对应代码：`FedPHE-main/encryption/ckks.py: ckks_dec`

```python
plain = ts.CKKSVector.load(ckks_ctx, cipher_serial).decrypt(sk)
if sum_masks != []:
    plain = np.array(plain) / sum_masks[idx]   # ← 关键：解密时除以 sum_mask
```

| Batch | 密文内容 | 解密后 | 除以 sum_mask | 最终结果 |
|-------|---------|--------|--------------|----------|
| 0 | $\text{Enc}([2.8, 3.6, 4.4, 5.2])$ | $[2.8, 3.6, 4.4, 5.2]$ | $/\; 0.8$ | $[3.5, 4.5, 5.5, 6.5]$ |
| 1 | $\text{Enc}([15, 22, 29, 36])$ | $[15, 22, 29, 36]$ | $/\; 0.7$ | $[150/7, 220/7, 290/7, 360/7]$ |

**最终明文列表**：

$$
\text{plain\_list} = [3.5,\; 4.5,\; 5.5,\; 6.5,\; 21.429,\; 31.429,\; 41.429,\; 51.429]
$$

---

## 四、两种方案对比总结

### 4.1 数学等价性验证

| Batch | 我的方案结果 | FedPHE 结果 | 是否一致 |
|-------|------------|------------|---------|
| 0 | $[3.5, 4.5, 5.5, 6.5]$ | $[3.5, 4.5, 5.5, 6.5]$ | ✓ |
| 1 | $[21.429, 31.429, 41.429, 51.429]$ | $[21.429, 31.429, 41.429, 51.429]$ | ✓ |

**两种方案数学完全等价**。

### 4.2 流程对比图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           两种方案流程对比                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  【我的方案：聚合时归一化】                                                    │
│                                                                             │
│  Batch 0:  C1(0.3)·[1,2,3,4]  +  C2(0.5)·[5,6,7,8]                          │
│            ─────────────────────────────────────────                        │
│                         0.3 + 0.5                                           │
│            = Enc([3.5, 4.5, 5.5, 6.5])  ← 已经是加权平均                     │
│                                                                             │
│  客户端解密: Dec(Enc([3.5, 4.5, 5.5, 6.5])) = [3.5, 4.5, 5.5, 6.5]          │
│            ↑ 无需再除                                                        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  【FedPHE：聚合时不归一化】                                                    │
│                                                                             │
│  Batch 0:  Enc([1,2,3,4])×0.3  +  Enc([5,6,7,8])×0.5                        │
│            = Enc([0.3+2.5, 0.6+3.0, 0.9+3.5, 1.2+4.0])                      │
│            = Enc([2.8, 3.6, 4.4, 5.2])  ← 未归一化（加权和）                  │
│                                                                             │
│  同时记录: sum_mask[0] = 0.3 + 0.5 = 0.8                                    │
│                                                                             │
│  客户端解密: Dec(Enc([2.8, 3.6, 4.4, 5.2])) = [2.8, 3.6, 4.4, 5.2]         │
│            再除以 sum_mask[0] = 0.8                                          │
│            = [2.8, 3.6, 4.4, 5.2] / 0.8                                      │
│            = [3.5, 4.5, 5.5, 6.5]                                            │
│            ↑ 解密后再除                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 核心差异表

| 特性 | **我的方案** | **FedPHE** |
|------|-----------|-----------|
| **归一化时机** | 聚合时（服务器端） | 解密时（客户端端） |
| **服务器计算** | `weighted_average(cts, norm_weights)` | `ct * weight` 累加 |
| **服务器存储** | 聚合后的密文 + mask | 未归一化密文 + `sum_mask` |
| **客户端解密** | `Dec(cipher)`（直接解密） | `Dec(cipher) / sum_mask`（解密后再除） |
| **通信量** | 相同（都发密文列表） | 相同 |
| **`__sum_weights__` 用途** | 记录但解密不使用 | 必须传给客户端用于解密 |

### 4.4 各自的优缺点

| | **我的方案** | **FedPHE** |
|---|---|---|
| **优点** | 客户端解密逻辑简单，无需处理除法 | 服务器聚合逻辑简单（只做乘加），归一化延迟到客户端 |
| **缺点** | 服务器聚合时需要计算归一化权重并做加权平均（如果 `weighted_average` 内部是逐个乘加，则和 FedPHE 服务器工作量相同） | 客户端解密时需要知道 `sum_mask`，且要处理浮点除法；若 `sum_mask=0` 需补零 |

---

## 五、关键代码对照

### 5.1 我的方案（`crypto.py`）

```python
# _aggregate_sparse_updates
for batch_idx in range(batch_num):
    batch_cts = []
    batch_weights = []

    for client_idx, update in enumerate(encrypted_updates):
        if update['mask'][batch_idx] == 1:
            ct_idx = sum(update['mask'][:batch_idx])
            batch_cts.append(update['ciphertexts'][ct_idx])
            batch_weights.append(weights[client_idx])
            sum_weights_per_batch[batch_idx] += weights[client_idx]

    if len(batch_cts) > 0:
        total_w = sum(batch_weights)                     # ← 计算该 batch 的权重和
        norm_weights = [w / total_w for w in batch_weights]  # ← 归一化
        aggregated_batch = self.evaluator.weighted_average(
            batch_cts, norm_weights                       # ← 聚合时直接加权平均
        )
        aggregated_ciphertexts.append(aggregated_batch)
        aggregated_mask[batch_idx] = 1
```

### 5.2 FedPHE（`server.py`）

```python
# aggregatie_weights (CKKS + TopK)
frac = ts.ckks_vector(ckks_ctx, [weights_client[c_id]])

for batch in range(batch_num):
    if mask[batch]:
        cnt = 0
        for i in range(batch):
            if mask[i]:
                cnt += 1
        res = ts.CKKSVector.load(ckks_ctx, cipher[cnt]) * frac  # ← 密文×明文加权
        sum_mask[batch] += weights_client[c_id]                 # ← 记录权重和

        if global_cipher[batch]:
            res += ts.CKKSVector.load(ckks_ctx, global_cipher[batch])
        global_cipher[batch] = res.serialize()                   # ← 累加，不归一化
```

---

*文档结束*
