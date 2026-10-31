# `ckks_dec` 核心循环逐行解析：公式 + 完整例子

> 对应代码：`FedPHE-main/encryption/ckks.py: ckks_dec`
>
> 功能：将服务器聚合后的密文列表解密为明文参数列表，缺失 batch 补零，非零 batch 按权重归一化。

---

## 一、代码原文

```python
for idx, cipher_serial in enumerate(cipher_list):
    if cipher_serial == 0:
        plain_list.extend([0.0] * batch_size)   # 缺失 batch 补零
    else:
        plain = ts.CKKSVector.load(ckks_ctx, cipher_serial).decrypt(sk)
        if sum_masks != []:
            plain = np.array(plain) / sum_masks[idx]   # 归一化
        plain_list.extend(plain)
```

---

## 二、数学公式描述

设总 batch 数为 $M$，每个 batch 含 $B$ 个参数。客户端收到的数据为：

- `cipher_list`：长度为 $M$ 的列表，第 $idx$ 个元素要么是密文字节串，要么是整数 `0`
- `sum_masks`：长度为 $M$ 的列表，第 $idx$ 个元素是该 batch 位置上所有提交客户端的权重之和

对每个 $idx \in \{0, 1, \dots, M-1\}$：

$$
\hat{b}_{idx} =
\begin{cases}
\underbrace{[0,\; 0,\; \dots,\; 0]}_{B \text{ 个零}}, & \text{if } \text{cipher\_list}[idx] = 0 \quad \text{（该 batch 无人提交）} \\[12pt]
\displaystyle\frac{\text{Dec}_{sk}\big(\text{cipher\_list}[idx]\big)}{\text{sum\_masks}[idx]}, & \text{otherwise} \quad \text{（该 batch 有人提交，做加权平均）}
\end{cases}
$$

最终：

$$
\text{plain\_list} = [\hat{b}_0,\; \hat{b}_1,\; \dots,\; \hat{b}_{M-1}] \in \mathbb{R}^{M \times B}
$$

---

## 三、完整数值例子

### 3.1 场景设定

| 参数 | 取值 |
|------|------|
| 客户端数 | 4（C1, C2, C3, C4） |
| 权重 | $w_1=0.3,\; w_2=0.2,\; w_3=0.3,\; w_4=0.2$ |
| Batch 总数 $M$ | 4 |
| Batch 大小 $B$ | 4 |
| TopK 比例 | 每个客户端只选 1 个 batch（$M=4$, 选 25%） |

### 3.2 各客户端选中的 Batch

| 客户端 | 选中 Batch | Mask |
|--------|-----------|------|
| C1 | 0, 3 | `[1, 0, 0, 1]` |
| C2 | 2, 3 | `[0, 0, 1, 1]` |
| C3 | 0, 3 | `[1, 0, 0, 1]` |
| C4 | 2, 3 | `[0, 0, 1, 1]` |

> 注：Batch 1 **没有任何客户端选中**。

### 3.3 各客户端提交的具体参数值

| 客户端 | Batch 0 值 | Batch 2 值 | Batch 3 值 |
|--------|-----------|-----------|-----------|
| C1 | `[1, 2, 3, 4]` | — | `[1, 1, 1, 1]` |
| C2 | — | `[10, 20, 30, 40]` | `[2, 2, 2, 2]` |
| C3 | `[5, 6, 7, 8]` | — | `[3, 3, 3, 3]` |
| C4 | — | `[50, 60, 70, 80]` | `[4, 4, 4, 4]` |

### 3.4 服务器聚合结果

服务器对每个 batch 位置独立累加（同态加法 + 密文×明文加权）：

#### Batch 0（C1, C3 提交）

$$
\text{global\_cipher}[0] = \text{Enc}([1,2,3,4]) \times 0.3 + \text{Enc}([5,6,7,8]) \times 0.3
$$

由 CKKS 同态性质：

$$
= \text{Enc}\big(\underbrace{[0.3+1.5,\; 0.6+1.8,\; 0.9+2.1,\; 1.2+2.4]}_{= [1.8,\; 2.4,\; 3.0,\; 3.6]}\big)
$$

$$
\text{sum\_mask}[0] = w_1 + w_3 = 0.3 + 0.3 = \mathbf{0.6}
$$

#### Batch 1（无人提交）

$$
\text{global\_cipher}[1] = 0, \quad \text{sum\_mask}[1] = \mathbf{0}
$$

#### Batch 2（C2, C4 提交）

$$
\text{global\_cipher}[2] = \text{Enc}([10,20,30,40]) \times 0.2 + \text{Enc}([50,60,70,80]) \times 0.2
$$

$$
= \text{Enc}\big(\underbrace{[2+10,\; 4+12,\; 6+14,\; 8+16]}_{= [12,\; 16,\; 20,\; 24]}\big)
$$

$$
\text{sum\_mask}[2] = w_2 + w_4 = 0.2 + 0.2 = \mathbf{0.4}
$$

#### Batch 3（C1, C2, C3, C4 全部提交）

$$
\text{global\_cipher}[3] = \text{Enc}([1,1,1,1]) \times 0.3 + \text{Enc}([2,2,2,2]) \times 0.2 + \text{Enc}([3,3,3,3]) \times 0.3 + \text{Enc}([4,4,4,4]) \times 0.2
$$

$$
= \text{Enc}\big(\underbrace{[0.3+0.4+0.9+0.8,\; \dots]}_{= [2.4,\; 2.4,\; 2.4,\; 2.4]}\big)
$$

$$
\text{sum\_mask}[3] = w_1 + w_2 + w_3 + w_4 = 0.3 + 0.2 + 0.3 + 0.2 = \mathbf{1.0}
$$

### 3.5 客户端收到的数据

```python
cipher_list = global_cipher = [
    Enc([1.8, 2.4, 3.0, 3.6]),   # Batch 0: 有密文
    0,                              # Batch 1: 无人提交，用 0 占位
    Enc([12, 16, 20, 24]),        # Batch 2: 有密文
    Enc([2.4, 2.4, 2.4, 2.4])     # Batch 3: 有密文
]

sum_masks = [0.6, 0, 0.4, 1.0]
```

### 3.6 `ckks_dec` 逐轮执行过程

#### 第 1 轮：idx = 0, cipher_serial = Enc([1.8, 2.4, 3.0, 3.6])

走 `else` 分支：

```python
plain = ts.CKKSVector.load(ckks_ctx, cipher_serial).decrypt(sk)
# plain = [1.8, 2.4, 3.0, 3.6]

plain = np.array(plain) / sum_masks[0]
# plain = [1.8, 2.4, 3.0, 3.6] / 0.6
# plain = [3.0, 4.0, 5.0, 6.0]

plain_list.extend(plain)
# plain_list = [3.0, 4.0, 5.0, 6.0]
```

**公式**：

$$
\hat{b}_0 = \frac{[1.8,\; 2.4,\; 3.0,\; 3.6]}{0.6} = [3.0,\; 4.0,\; 5.0,\; 6.0]
$$

**验证**：这就是 C1 和 C3 在 Batch 0 的加权平均：

$$
\frac{0.3 \times [1,2,3,4] + 0.3 \times [5,6,7,8]}{0.3+0.3} = \frac{[0.3+1.5,\; 0.6+1.8,\; 0.9+2.1,\; 1.2+2.4]}{0.6} = [3.0, 4.0, 5.0, 6.0] \; \checkmark
$$

#### 第 2 轮：idx = 1, cipher_serial = 0

走 `if` 分支：

```python
plain_list.extend([0.0] * batch_size)
# plain_list = [3.0, 4.0, 5.0, 6.0, 0.0, 0.0, 0.0, 0.0]
```

**公式**：

$$
\hat{b}_1 = [0,\; 0,\; 0,\; 0]
$$

> 原因：没有任何客户端选中 Batch 1，服务器该位置为 0，解密后补 4 个零。

#### 第 3 轮：idx = 2, cipher_serial = Enc([12, 16, 20, 24])

走 `else` 分支：

```python
plain = [12, 16, 20, 24]
plain = [12, 16, 20, 24] / sum_masks[2]
# plain = [12, 16, 20, 24] / 0.4
# plain = [30.0, 40.0, 50.0, 60.0]

plain_list.extend(plain)
# plain_list = [3.0, 4.0, 5.0, 6.0, 0.0, 0.0, 0.0, 0.0, 30.0, 40.0, 50.0, 60.0]
```

**公式**：

$$
\hat{b}_2 = \frac{[12,\; 16,\; 20,\; 24]}{0.4} = [30.0,\; 40.0,\; 50.0,\; 60.0]
$$

**验证**：

$$
\frac{0.2 \times [10,20,30,40] + 0.2 \times [50,60,70,80]}{0.2+0.2} = \frac{[2+10,\; 4+12,\; 6+14,\; 8+16]}{0.4} = [30, 40, 50, 60] \; \checkmark
$$

#### 第 4 轮：idx = 3, cipher_serial = Enc([2.4, 2.4, 2.4, 2.4])

走 `else` 分支：

```python
plain = [2.4, 2.4, 2.4, 2.4]
plain = [2.4, 2.4, 2.4, 2.4] / sum_masks[3]
# plain = [2.4, 2.4, 2.4, 2.4] / 1.0
# plain = [2.4, 2.4, 2.4, 2.4]

plain_list.extend(plain)
# plain_list = [3.0, 4.0, 5.0, 6.0,
#               0.0, 0.0, 0.0, 0.0,
#               30.0, 40.0, 50.0, 60.0,
#               2.4, 2.4, 2.4, 2.4]
```

**公式**：

$$
\hat{b}_3 = \frac{[2.4,\; 2.4,\; 2.4,\; 2.4]}{1.0} = [2.4,\; 2.4,\; 2.4,\; 2.4]
$$

**验证**：

$$
\frac{0.3 \times [1,1,1,1] + 0.2 \times [2,2,2,2] + 0.3 \times [3,3,3,3] + 0.2 \times [4,4,4,4]}{1.0}
$$

$$
= [0.3+0.4+0.9+0.8,\; \dots] = [2.4, 2.4, 2.4, 2.4] \; \checkmark
$$

### 3.7 最终输出

```python
plain_list = [
    3.0,  4.0,  5.0,  6.0,    # Batch 0: 加权平均结果
    0.0,  0.0,  0.0,  0.0,    # Batch 1: 补零（无人提交）
    30.0, 40.0, 50.0, 60.0,   # Batch 2: 加权平均结果
    2.4,  2.4,  2.4,  2.4     # Batch 3: 加权平均结果
]
```

---

## 四、关键要点总结

### 4.1 为什么 `cipher_serial == 0` 要补零？

因为 TopK 稀疏化后，每个客户端只提交部分 batch。服务器聚合后的 `global_cipher` 是一个长度为 $M$ 的列表：

- 有客户端提交的 batch 位置：存放密文字节串
- **无人提交的 batch 位置**：存放整数 `0`（占位符）

客户端解密时需要把所有 batch 位置补齐，否则无法还原完整参数列表。

### 4.2 为什么除以 `sum_masks[idx]` 而不是总权重？

**按 batch 独立归一化**是 FedPHE 的核心设计：

| 问题 | 如果用总权重（0.3+0.2+0.3+0.2=1.0） | 用 `sum_masks[idx]` |
|------|-----------------------------------|-------------------|
| Batch 0 只除以 1.0 | $[1.8,2.4,3.0,3.6]/1.0 = [1.8,2.4,3.0,3.6]$ ❌ 错误 | $[1.8,2.4,3.0,3.6]/0.6 = [3.0,4.0,5.0,6.0]$ ✓ 正确 |
| Batch 2 只除以 1.0 | $[12,16,20,24]/1.0 = [12,16,20,24]$ ❌ 错误 | $[12,16,20,24]/0.4 = [30,40,50,60]$ ✓ 正确 |

**原因**：每个 batch 位置只聚合了部分客户端，分母应该是**该 batch 上实际提交的客户端权重之和**，而不是全局所有客户端的权重之和。

### 4.3 公式本质

这段代码的数学本质是：

$$
\text{plain\_list} = \left[
\frac{\sum_{i \in S_0} w_i \cdot b_0^{(i)}}{\sum_{i \in S_0} w_i},
\;
\mathbf{0}_B,
\;
\frac{\sum_{i \in S_2} w_i \cdot b_2^{(i)}}{\sum_{i \in S_2} w_i},
\;
\frac{\sum_{i \in S_3} w_i \cdot b_3^{(i)}}{\sum_{i \in S_3} w_i}
\right]
$$

其中 $S_j = \{i \mid \mathbf{m}^{(i)}[j] = 1\}$ 是选中 batch $j$ 的客户端集合，$\mathbf{0}_B$ 是长度为 $B$ 的零向量。

---

*文档结束*
