# FedPHE 完整数值例子：CKKS + TopK 稀疏化全流程

> 本文档基于 FedPHE 代码实现（`encryption/ckks.py`、`server.py`、`client.py`）构建一个**可手工演算**的完整数值例子，展示从明文模型参数 → Batch 分块 → TopK 掩码 → CKKS 加密 → 同态加权聚合 → 归一化解密 → 稀疏补全的全流程。
>
> 所有数值均经过验证，可直接对应代码中的公式。

---

## 一、符号约定与超参数

| 符号 | 含义 | 本例取值 |
|------|------|----------|
| $N$ | 模型参数量 | $N = 8$ |
| $B$ | Batch Size（每个 CKKS 明文向量打包的参数个数） | $B = 4$ |
| $M$ | Batch 总数 | $M = \lceil N/B \rceil = 2$ |
| $K$ | TopK 稀疏比例 | $K = 0.5$（保留 50% 的 batch） |
| $n$ | 客户端数量 | $n = 2$ |
| $w_1, w_2$ | 客户端权重（样本数占比） | $w_1 = 0.6,\; w_2 = 0.4$ |
| $\text{Enc}(\cdot), \text{Dec}(\cdot)$ | CKKS 加解密函数 | 同态支持：加法、密文×明文 |

---

## 二、Step 0：客户端本地训练后的模型参数

### 2.1 客户端 1（C1）

本地训练后，模型参数扁平化为一个一维列表（对应 `client.py: params_tolist`）：

$$
\mathbf{p}^{(1)} = [\underbrace{0.5,\; -0.3,\; 0.8,\; -0.2}_{\text{Batch }0},\; \underbrace{0.1,\; 0.4,\; -0.6,\; 0.9}_{\text{Batch }1}] \in \mathbb{R}^8
$$

### 2.2 客户端 2（C2）

$$
\mathbf{p}^{(2)} = [\underbrace{0.2,\; -0.1,\; 0.3,\; -0.4}_{\text{Batch }0},\; \underbrace{0.5,\; -0.2,\; 0.1,\; 0.3}_{\text{Batch }1}] \in \mathbb{R}^8
$$

---

## 三、Step 1：Batch 分块

对应代码：`encryption/ckks.py: ckks_enc`，公式：

$$
\text{batch\_num} = \left\lceil \frac{\text{len}(\text{plain\_list})}{\text{batch\_size}} \right\rceil
$$

将每个客户端的参数切分为 $M=2$ 个 batch，每个 batch $B=4$ 个元素。

### 3.1 C1 的 Batch 划分

| Batch 索引 | 元素 | 对应参数 |
|-----------|------|----------|
| $b_0^{(1)}$ | $[0.5, -0.3, 0.8, -0.2]$ | $\mathbf{p}^{(1)}[0:4]$ |
| $b_1^{(1)}$ | $[0.1, 0.4, -0.6, 0.9]$ | $\mathbf{p}^{(1)}[4:8]$ |

### 3.2 C2 的 Batch 划分

| Batch 索引 | 元素 | 对应参数 |
|-----------|------|----------|
| $b_0^{(2)}$ | $[0.2, -0.1, 0.3, -0.4]$ | $\mathbf{p}^{(2)}[0:4]$ |
| $b_1^{(2)}$ | $[0.5, -0.2, 0.1, 0.3]$ | $\mathbf{p}^{(2)}[4:8]$ |

---

## 四、Step 2：TopK 稀疏化与掩码生成

对应代码：`encryption/ckks.py: ckks_enc`，核心公式：

$$
\text{topk} = \lceil \text{batch\_num} \times K \rceil
$$

对每个 batch 计算平均绝对值：

$$
\text{avg\_list}[i] = \frac{1}{B} \sum_{j=0}^{B-1} \left| b_i[j] \right|
$$

保留 avg(|x|) 最大的 topk 个 batch，生成掩码：

$$
\text{mask}[i] = 
\begin{cases}
1, & \text{if batch } i \text{ 被选中} \\
0, & \text{otherwise}
\end{cases}
$$

### 4.1 C1 的 TopK 计算

- Batch 0：$\text{avg}_0^{(1)} = \frac{|0.5| + |-0.3| + |0.8| + |-0.2|}{4} = \frac{0.5+0.3+0.8+0.2}{4} = \mathbf{0.45}$
- Batch 1：$\text{avg}_1^{(1)} = \frac{|0.1| + |0.4| + |-0.6| + |0.9|}{4} = \frac{0.1+0.4+0.6+0.9}{4} = \mathbf{0.50}$

TopK 数量：$\text{topk} = \lceil 2 \times 0.5 \rceil = 1$，选择 avg 最大的 **Batch 1**。

**C1 掩码**：

$$
\mathbf{m}^{(1)} = [0,\; 1]
$$

**C1 待加密数据**：只加密 Batch 1

$$
\text{cipher}^{(1)} = \left[ \text{Enc}\left([0.1,\; 0.4,\; -0.6,\; 0.9]\right) \right]
$$

> 注意：`cipher` 列表长度为 1（只有被选中的 batch），但 `mask` 列表长度仍为 2（标记所有 batch 的选中状态）。

### 4.2 C2 的 TopK 计算

- Batch 0：$\text{avg}_0^{(2)} = \frac{|0.2| + |-0.1| + |0.3| + |-0.4|}{4} = \frac{0.2+0.1+0.3+0.4}{4} = \mathbf{0.25}$
- Batch 1：$\text{avg}_1^{(2)} = \frac{|0.5| + |-0.2| + |0.1| + |0.3|}{4} = \frac{0.5+0.2+0.1+0.3}{4} = \mathbf{0.275}$

TopK 数量：$\text{topk} = 1$，选择 avg 最大的 **Batch 1**。

**C2 掩码**：

$$
\mathbf{m}^{(2)} = [0,\; 1]
$$

**C2 待加密数据**：

$$
\text{cipher}^{(2)} = \left[ \text{Enc}\left([0.5,\; -0.2,\; 0.1,\; 0.3]\right) \right]
$$

### 4.3 客户端发送消息

| 客户端 | 发送内容 | 格式（对应代码 `client.py: pipe.send`） |
|--------|----------|--------------------------------------|
| C1 | $[\text{rank}=1,\; \mathbf{m}^{(1)}=[0,1],\; \text{cipher}^{(1)}]$ | `[rank, mask, cipher]` |
| C2 | $[\text{rank}=2,\; \mathbf{m}^{(2)}=[0,1],\; \text{cipher}^{(2)}]$ | `[rank, mask, cipher]` |

---

## 五、Step 3：服务器同态加权聚合

对应代码：`server.py: aggregatie_weights`，核心逻辑：

```python
frac = ts.ckks_vector(ckks_ctx, [weights_client[c_id]])  # 明文权重向量
res = ts.CKKSVector.load(ckks_ctx, cipher[cnt]) * frac    # 密文 × 明文（同态乘法）
# 累加到全局密文
```

### 5.1 聚合公式

对每个 batch $j \in \{0, 1\}$，服务器维护：

- 全局密文累加器：$\text{global\_cipher}[j]$（初始为 0）
- 权重累加器：$\text{sum\_mask}[j]$（初始为 0）

对每个客户端 $i$，若 $\mathbf{m}^{(i)}[j] = 1$，则：

$$
\text{global\_cipher}[j] \;\mathrel{+}=\; \text{cipher}^{(i)}[\text{cnt}] \times w_i
$$

$$
\text{sum\_mask}[j] \;\mathrel{+}=\; w_i
$$

其中 $\text{cnt}$ 是 $\mathbf{m}^{(i)}[0:j]$ 中 1 的个数（即 cipher 列表中的索引，对应代码：
```python
cnt = 0
for i in range(batch):
    if mask[i]:
        cnt += 1
```
）

### 5.2 本例聚合过程

#### Batch 0

- C1：$\mathbf{m}^{(1)}[0] = 0$ → 跳过
- C2：$\mathbf{m}^{(2)}[0] = 0$ → 跳过

结果：

$$
\text{global\_cipher}[0] = 0, \quad \text{sum\_mask}[0] = 0
$$

#### Batch 1

- C1：$\mathbf{m}^{(1)}[1] = 1$，$\text{cnt} = 1$（mask[0:1] 中 1 的个数为 1）
  - 同态乘法：$\text{Enc}([0.1, 0.4, -0.6, 0.9]) \times 0.6 = \text{Enc}([0.06, 0.24, -0.36, 0.54])$
  - 累加：$\text{global\_cipher}[1] = \text{Enc}([0.06, 0.24, -0.36, 0.54])$
  - 权重累加：$\text{sum\_mask}[1] = 0.6$

- C2：$\mathbf{m}^{(2)}[1] = 1$，$\text{cnt} = 1$
  - 同态乘法：$\text{Enc}([0.5, -0.2, 0.1, 0.3]) \times 0.4 = \text{Enc}([0.20, -0.08, 0.04, 0.12])$
  - 累加：$\text{global\_cipher}[1] = \text{Enc}([0.06, 0.24, -0.36, 0.54]) + \text{Enc}([0.20, -0.08, 0.04, 0.12])$
  - 由 CKKS 同态加法：$\text{global\_cipher}[1] = \text{Enc}([0.26, 0.16, -0.32, 0.66])$
  - 权重累加：$\text{sum\_mask}[1] = 0.6 + 0.4 = \mathbf{1.0}$

### 5.3 聚合结果

| Batch | 全局密文 | 权重和 |
|-------|----------|--------|
| 0 | $0$（占位符） | $0$ |
| 1 | $\text{Enc}([0.26,\; 0.16,\; -0.32,\; 0.66])$ | $1.0$ |

服务器将 $[\text{sum\_mask},\; \text{global\_cipher}]$ 通过队列下发给所有客户端。

---

## 六、Step 4：客户端解密与归一化

对应代码：`encryption/ckks.py: ckks_dec`，核心逻辑：

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

### 6.1 客户端接收数据

每个客户端从队列获取：

$$
\text{involved\_frac} = \text{sum\_mask} = [0,\; 1.0]
$$

$$
\text{global\_weights} = \text{global\_cipher} = [0,\; \text{Enc}([0.26, 0.16, -0.32, 0.66])]
$$

> 注：代码中 `cipher_list` 的 batch 0 位置为 `0`（Python 整数），表示该 batch 没有密文，需要补零。

### 6.2 解密过程

对每个 batch 索引 $idx$：

- **Batch 0**（$idx=0$）：$\text{cipher\_serial} = 0$ → 补零：$[0, 0, 0, 0]$
- **Batch 1**（$idx=1$）：解密
  - $\text{Dec}(\text{Enc}([0.26, 0.16, -0.32, 0.66])) = [0.26, 0.16, -0.32, 0.66]$
  - 归一化：除以 $\text{sum\_mask}[1] = 1.0$
  - 结果：$[0.26, 0.16, -0.32, 0.66]$

### 6.3 解密后全局参数列表

$$
\mathbf{g} = [\underbrace{0,\; 0,\; 0,\; 0}_{\text{Batch }0},\; \underbrace{0.26,\; 0.16,\; -0.32,\; 0.66}_{\text{Batch }1}] \in \mathbb{R}^8
$$

---

## 七、Step 5：稀疏补全（TopK 恢复）

对应代码：`client.py: params_tomodel`，核心逻辑：

```python
if args.isSpars == 'topk':
    for idx_tmp in range(len(tmp)):
        if tmp[idx_tmp] == 0 and (idx_tmp == len(tmp)-1 or tmp[idx_tmp+1] == 0):
            tmp[idx_tmp] = params_list[idx_cnt + idx_tmp]  # 用本地参数补全
```

### 7.1 补全规则

对于全局列表 $\mathbf{g}$ 中值为 0 的位置，用**客户端本地参数** $\mathbf{p}^{(i)}$ 对应位置的值填充。

### 7.2 C1 补全后

C1 本地参数：$\mathbf{p}^{(1)} = [0.5, -0.3, 0.8, -0.2, 0.1, 0.4, -0.6, 0.9]$

| 索引 | 全局 $\mathbf{g}$ | C1 本地 $\mathbf{p}^{(1)}$ | 补全后 |
|------|------------------|---------------------------|--------|
| 0 | $0$ | $0.5$ | $0.5$ |
| 1 | $0$ | $-0.3$ | $-0.3$ |
| 2 | $0$ | $0.8$ | $0.8$ |
| 3 | $0$ | $-0.2$ | $-0.2$ |
| 4 | $0.26$ | $0.1$ | $0.26$（保留全局）|
| 5 | $0.16$ | $0.4$ | $0.16$（保留全局）|
| 6 | $-0.32$ | $-0.6$ | $-0.32$（保留全局）|
| 7 | $0.66$ | $0.9$ | $0.66$（保留全局）|

补全后 C1 的模型参数：

$$
\mathbf{g}^{(1)} = [0.5,\; -0.3,\; 0.8,\; -0.2,\; 0.26,\; 0.16,\; -0.32,\; 0.66]
$$

### 7.3 C2 补全后

C2 本地参数：$\mathbf{p}^{(2)} = [0.2, -0.1, 0.3, -0.4, 0.5, -0.2, 0.1, 0.3]$

| 索引 | 全局 $\mathbf{g}$ | C2 本地 $\mathbf{p}^{(2)}$ | 补全后 |
|------|------------------|---------------------------|--------|
| 0 | $0$ | $0.2$ | $0.2$ |
| 1 | $0$ | $-0.1$ | $-0.1$ |
| 2 | $0$ | $0.3$ | $0.3$ |
| 3 | $0$ | $-0.4$ | $-0.4$ |
| 4 | $0.26$ | $0.5$ | $0.26$（保留全局）|
| 5 | $0.16$ | $-0.2$ | $0.16$（保留全局）|
| 6 | $-0.32$ | $0.1$ | $-0.32$（保留全局）|
| 7 | $0.66$ | $0.3$ | $0.66$（保留全局）|

补全后 C2 的模型参数：

$$
\mathbf{g}^{(2)} = [0.2,\; -0.1,\; 0.3,\; -0.4,\; 0.26,\; 0.16,\; -0.32,\; 0.66]
$$

### 7.4 补全效果说明

- **Batch 1（参数 4-7）**：已被全局聚合（加权平均），所有客户端保持一致：$[0.26, 0.16, -0.32, 0.66]$
- **Batch 0（参数 0-3）**：未被选中聚合，每个客户端保留自己的本地参数

这正是 TopK 稀疏化的核心思想：**只通信和聚合最重要的参数，其余参数保持本地不变**，从而大幅减少通信量。

---

## 八、公式汇总（对应论文与代码）

### 8.1 Batch 划分

$$
M = \left\lceil \frac{N}{B} \right\rceil, \quad
b_j = \mathbf{p}[j \cdot B : (j+1) \cdot B], \quad j = 0, 1, \dots, M-1
$$

> 代码：`ckks_enc: batch_num = int(np.ceil(len(plain_list) / batch_size))`

### 8.2 TopK 掩码生成

$$
\text{avg}_j = \frac{1}{B} \sum_{k=0}^{B-1} |b_j[k]|, \quad
\text{topk} = \lceil M \cdot K \rceil
$$

$$
\mathbf{m}[j] = 
\begin{cases}
1, & \text{if } \text{avg}_j \text{ 属于 topk 个最大值} \\
0, & \text{otherwise}
\end{cases}
$$

> 代码：`ckks_enc: avg_list = [np.average(np.abs(batch)) for batch in plain_batchs]`

### 8.3 CKKS 加密（Batch 级）

$$
c_j = \text{Enc}(b_j), \quad \forall j \text{ s.t. } \mathbf{m}[j] = 1
$$

> 代码：`ts.ckks_vector(ckks_ctx, plain_list[i]).serialize()`

### 8.4 同态加权聚合

对每个 batch $j$：

$$
\text{global\_cipher}[j] = \sum_{i: \mathbf{m}^{(i)}[j]=1} c_{\text{cnt}(i,j)}^{(i)} \times w_i
$$

$$
\text{sum\_mask}[j] = \sum_{i: \mathbf{m}^{(i)}[j]=1} w_i
$$

其中 $c_{\text{cnt}(i,j)}^{(i)}$ 是客户端 $i$ 的第 $j$ 个 batch 的密文（在 cipher 列表中的索引为 $\text{cnt}(i,j) = \sum_{k=0}^{j-1} \mathbf{m}^{(i)}[k]$）。

> 代码：`server.py: res = ts.CKKSVector.load(ckks_ctx, cipher[cnt]) * frac`
>
> 注意：这里的 $w_i$ 是以**明文 CKKS 向量**形式参与运算（`frac = ts.ckks_vector(ckks_ctx, [weights_client[c_id]])`），利用 CKKS 的**密文 × 明文**同态乘法特性。这与论文中可能描述的 $E(w_i)$（加密权重）不同，代码实现中为效率做了优化。

### 8.5 解密归一化

对每个 batch $j$：

$$
\hat{b}_j =
\begin{cases}
\underbrace{[0, \dots, 0]}_{B}, & \text{if } \text{sum\_mask}[j] = 0 \\
\text{Dec}(\text{global\_cipher}[j]) \;/\; \text{sum\_mask}[j], & \text{otherwise}
\end{cases}
$$

> 代码：`ckks_dec: plain = np.array(plain) / sum_masks[idx]`

### 8.6 全局参数重构

$$
\mathbf{g} = [\hat{b}_0,\; \hat{b}_1,\; \dots,\; \hat{b}_{M-1}]
$$

### 8.7 稀疏补全

对每个位置 $t$：

$$
\mathbf{g}^{(i)}[t] =
\begin{cases}
\mathbf{p}^{(i)}[t], & \text{if } \mathbf{g}[t] = 0 \\
\mathbf{g}[t], & \text{otherwise}
\end{cases}
$$

> 代码：`client.py: if tmp[idx_tmp] == 0: tmp[idx_tmp] = params_list[idx_cnt + idx_tmp]`

---

## 九、与论文理论公式的对照说明

用户提到的论文公式（推测来自 FedPHE 论文的 Secure Weighted Aggregation 章节）：

> **论文公式（推测）**：
> $$
> R = r + r_d \quad \text{(global obfuscating factor)}
> $$
> $$
> C_t = \sum_i E(p_{t,i}) \cdot C_{t,i}
> $$
> $$
> M_t = \sum_i p_{t,i} \cdot M_{t,i}
> $$

### 9.1 代码实现与论文公式的映射

| 论文符号 | 代码对应 | 说明 |
|---------|----------|------|
| $C_{t,i}$ | `cipher[cnt]` | 客户端 $i$ 的第 $t$ 个 batch 的密文 |
| $p_{t,i}$ | `weights_client[c_id]` | 客户端 $i$ 的聚合权重 |
| $E(p_{t,i})$ | `frac = ts.ckks_vector(ckks_ctx, [weights_client[c_id]])` | 代码中**未加密**权重，直接用明文 CKKS 向量 |
| $C_t$ | `global_cipher[batch]` | 聚合后的全局密文 |
| $M_{t,i}$ | `mask[batch]` | 客户端 $i$ 的 batch 掩码 |
| $M_t$ | `sum_mask[batch]` | 聚合后的权重和（作为归一化分母）|
| $R$ | **未直接实现** | `R = r + r_d` 是论文中的混淆因子，CKKS 本身具有语义安全性，无需额外混淆；Paillier 实现中有 `apply_obfuscator` |

### 9.2 关键差异

1. **权重加密**：论文中 $E(p_{t,i})$ 表示**加密后的权重**，但代码中 CKKS 实现使用**明文权重**直接做密文×明文乘法。这是因为：
   - CKKS 的密文 × 明文运算不会泄露明文权重的信息（权重本身已经是公开信息，即样本数占比）
   - 加密权重会增加额外的计算和通信开销，对收敛结果无影响

2. **混淆因子 $R$**：论文中的 $R = r + r_d$ 用于增强安全性，代码中：
   - CKKS：TenSEAL 内部已实现重线性化和重缩放，无需额外混淆
   - Paillier：`encryption/paillier.py: apply_obfuscator` 使用了随机数 $r$ 做密文混淆（$c' = c \cdot r^n \pmod{n^2}$），对应论文中的 obfuscating factor

---

## 十、全流程数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              第 1 轮联邦学习                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐                    ┌──────────┐                    ┌────────┐ │
│  │ Client 1 │                    │ Client 2 │                    │ Server │ │
│  └────┬─────┘                    └────┬─────┘                    └───┬────┘ │
│       │                               │                              │      │
│       │  p^(1) = [0.5,-0.3,0.8,-0.2, │  p^(2) = [0.2,-0.1,0.3,-0.4, │      │
│       │         0.1,0.4,-0.6,0.9]     │         0.5,-0.2,0.1,0.3]    │      │
│       │                               │                              │      │
│       │  Step 1: Batch 分块            │  Step 1: Batch 分块           │      │
│       │  b0=[0.5,-0.3,0.8,-0.2]       │  b0=[0.2,-0.1,0.3,-0.4]      │      │
│       │  b1=[0.1,0.4,-0.6,0.9]        │  b1=[0.5,-0.2,0.1,0.3]       │      │
│       │                               │                              │      │
│       │  Step 2: TopK 掩码             │  Step 2: TopK 掩码            │      │
│       │  avg=[0.45, 0.50]             │  avg=[0.25, 0.275]            │      │
│       │  m^(1) = [0, 1]               │  m^(2) = [0, 1]               │      │
│       │                               │                              │      │
│       │  Step 3: CKKS 加密             │  Step 3: CKKS 加密            │      │
│       │  c^(1) = [Enc(b1)]            │  c^(2) = [Enc(b1)]            │      │
│       │                               │                              │      │
│       │───────── [1, [0,1], c^(1)] ───┼──────────────────────────────>│      │
│       │                               │                              │      │
│       │                               │────── [2, [0,1], c^(2)] ─────>│      │
│       │                               │                              │      │
│       │                               │                    Step 4: 同态聚合   │
│       │                               │                    ┌─────────────┐   │
│       │                               │                    │ Batch 0:    │   │
│       │                               │                    │   skip (mask=0) │
│       │                               │                    │ Batch 1:    │   │
│       │                               │                    │   c1*0.6 +  │   │
│       │                               │                    │   c2*0.4    │   │
│       │                               │                    │   = Enc([   │   │
│       │                               │                    │     0.26,   │   │
│       │                               │                    │     0.16,   │   │
│       │                               │                    │    -0.32,   │   │
│       │                               │                    │     0.66])  │   │
│       │                               │                    │ sum_mask=1.0│   │
│       │                               │                    └─────────────┘   │
│       │                               │                              │      │
│       │<──────────────────────────────┼──────── [sum_mask, global_cipher] ───│
│       │                               │                              │      │
│       │                               │<─────────────────────────────│      │
│       │                               │                              │      │
│       │  Step 5: 解密归一化            │  Step 5: 解密归一化           │      │
│       │  g = [0,0,0,0, 0.26,0.16,     │  g = [0,0,0,0, 0.26,0.16,    │      │
│       │      -0.32,0.66]              │      -0.32,0.66]             │      │
│       │                               │                              │      │
│       │  Step 6: 稀疏补全              │  Step 6: 稀疏补全             │      │
│       │  g^(1) = [0.5,-0.3,0.8,-0.2,  │  g^(2) = [0.2,-0.1,0.3,-0.4, │      │
│       │          0.26,0.16,-0.32,0.66]│          0.26,0.16,-0.32,0.66]│      │
│       │                               │                              │      │
│       │  （Batch 0 保持本地，Batch 1    │  （Batch 0 保持本地，Batch 1   │      │
│       │   已全局聚合一致）               │   已全局聚合一致）              │      │
│       │                               │                              │      │
└───────┴───────────────────────────────┴──────────────────────────────┴──────┘
```

---

## 十一、数值验证

### 11.1 Batch 1 的加权平均验证

Batch 1 在全局聚合后应该等于两个客户端 Batch 1 的加权平均：

$$
\text{Expected} = w_1 \cdot b_1^{(1)} + w_2 \cdot b_1^{(2)} = 0.6 \cdot [0.1, 0.4, -0.6, 0.9] + 0.4 \cdot [0.5, -0.2, 0.1, 0.3]
$$

逐项计算：

| 参数索引 | C1 贡献 $0.6 \times$ | C2 贡献 $0.4 \times$ | 加权和 | 解密结果 |
|---------|---------------------|---------------------|--------|----------|
| 4 | $0.6 \times 0.1 = 0.06$ | $0.4 \times 0.5 = 0.20$ | $0.26$ | $0.26$ ✓ |
| 5 | $0.6 \times 0.4 = 0.24$ | $0.4 \times (-0.2) = -0.08$ | $0.16$ | $0.16$ ✓ |
| 6 | $0.6 \times (-0.6) = -0.36$ | $0.4 \times 0.1 = 0.04$ | $-0.32$ | $-0.32$ ✓ |
| 7 | $0.6 \times 0.9 = 0.54$ | $0.4 \times 0.3 = 0.12$ | $0.66$ | $0.66$ ✓ |

再除以 sum_mask = 1.0，结果不变。

**验证通过。**

### 11.2 通信量对比

| 方案 | 每个客户端发送密文数量 | 本例（M=2, topk=1）| 压缩率 |
|------|----------------------|-------------------|--------|
| 全量 CKKS | $M = 2$ | 2 个密文 | $1\times$ |
| TopK 稀疏 | $\lceil M \cdot K \rceil = 1$ | 1 个密文 | $\mathbf{2\times}$ |

在实际场景中（如 FedPHE 论文中的 MNIST，$N \approx 10^6$, $B=4096$, $K=0.1$）：

- Batch 总数：$M = \lceil 10^6 / 4096 \rceil \approx 244$
- TopK 后：$\lceil 244 \times 0.1 \rceil = 25$ 个 batch
- 压缩率：$244 / 25 \approx 9.76\times$

这与论文中报告的通信开销降低 $1.24 \sim 22.62\times$ 一致。

---

## 十二、CKKS 同态运算性质的数学解释

### 12.1 密文 × 明文（本例使用的加权方式）

CKKS 支持**密文与明文**之间的同态乘法：

$$
\text{Enc}(\mathbf{m}) \times \mathbf{p} = \text{Enc}(\mathbf{m} \odot \mathbf{p})
$$

其中 $\mathbf{p}$ 是明文向量，$\odot$ 是逐元素乘法。

在本例中，权重 $w_i$ 是一个标量，TenSEAL 将其广播为与密文相同长度的向量：

$$
\text{Enc}([0.1, 0.4, -0.6, 0.9]) \times [0.6, 0.6, 0.6, 0.6] = \text{Enc}([0.06, 0.24, -0.36, 0.54])
$$

### 12.2 密文 + 密文（聚合加法）

CKKS 支持密文之间的同态加法：

$$
\text{Enc}(\mathbf{a}) + \text{Enc}(\mathbf{b}) = \text{Enc}(\mathbf{a} + \mathbf{b})
$$

在本例中：

$$
\text{Enc}([0.06, 0.24, -0.36, 0.54]) + \text{Enc}([0.20, -0.08, 0.04, 0.12]) = \text{Enc}([0.26, 0.16, -0.32, 0.66])
$$

### 12.3 为什么不需要 $E(w_i)$（加密权重）

论文中 $C_t = \sum_i E(p_{t,i}) \cdot C_{t,i}$ 使用加密权重 $E(p_{t,i})$，是为了在**权重本身也是隐私信息**的场景下保护权重。但在联邦学习中：

- 客户端权重通常是**样本数占比**，属于半公开信息
- CKKS 的密文 × 明文运算已经保证了：服务器无法从结果反推出客户端的原始梯度（因为密文具有语义安全性）
- 使用明文权重可将计算复杂度从 $O(n)$ 次密文×密文乘法降为 $O(n)$ 次密文×明文乘法，效率提升显著

因此代码实现选择了更实用的方案。

---

## 十三、扩展到 RandK 稀疏化

RandK 与 TopK 的区别仅在于掩码生成方式：

| 特性 | TopK | RandK |
|------|------|-------|
| 掩码生成 | 按 avg(\|x\|) 排序选最大 | 随机选择 |
| 种子 | 无需种子 | 需要 `randk_seed` + `round` |
| 代码 | `avg_list = [np.average(np.abs(batch)) ...]` | `randk_list = pseudo_random(randk_seed, batch_num, randk, round)` |
| 客户端发送 | `[rank, mask, cipher]` | `[rank, cipher]`（randk_list 在服务器端重建）|

RandK 的聚合公式与 TopK 完全相同，解密时也使用 `sum_masks` 归一化，区别仅在于 mask 是随机生成的而非基于梯度重要性。

---

*文档结束*
