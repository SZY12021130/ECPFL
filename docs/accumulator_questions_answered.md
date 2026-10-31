# 累加器六问六答：与 STC/PTopk 对比、upload_difference、学习率 $\eta$ 详解

---

## 问题①：STC 算法的累加器 vs 我的累加器

### STC 原始论文（Sattler et al., IEEE TNNLS 2020）

STC 的核心是 **Error Feedback（误差反馈）**，客户端和服务器都维护累加器：

**客户端误差累加器**（每个客户端 $i$ 独立维护）：

$$
A_i^{t+1} = A_i^t + \Delta_i^t - \text{TopK}(A_i^t + \Delta_i^t)
$$

其中：
- $A_i^t$：第 $t$ 轮客户端 $i$ 的误差累加器（残差）
- $\Delta_i^t = W_{t,i} - W_t$：本地模型与全局模型的差值
- $\text{TopK}(\cdot)$：只保留最大的 $K\%$ 元素，其余置零

**上传内容**：$\text{upload}_i^t = \text{TopK}(A_i^t + \Delta_i^t)$

**服务器累加器**（全局）：

STC 原始论文的服务器端非常简单——直接对所有客户端上传的稀疏更新做**简单平均**，没有额外的动量或延迟机制。部分后续工作（如你的 PTopk 参考的变体）扩展了服务器累加器。

### 我的算法中的累加器

| 累加器 | 位置 | 类型 | 对应公式 |
|--------|------|------|---------|
| `client_residual` | 客户端 | 明文残差 | $r_{t+1} = (\Delta_t + r_t) - \text{TopK}(\Delta_t + r_t)$ |
| `server_accumulator_plain` | 服务器 | 明文（PTopk） | `delayed`: $A_t = A_{t-1} + \eta \Delta_t$；`momentum`: $A_t = \beta A_{t-1} + (1-\beta)\eta \Delta_t$ |
| `encrypted_global_state` | 服务器 | 密文（CKKS） | $W_{t+1}^{(enc)} = W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})$ |

**与 STC 的核心差异**：

1. **客户端残差**：我的 PTopk 客户端残差和 STC 公式**完全一致**（`ptopk.py: apply_residual / update_residual`）
2. **服务器累加器**：STC 服务器通常没有累加器（直接平均），而我的 PTopk 服务器累加器是**额外扩展**，支持 `delayed` 和 `momentum` 两种模式
3. **密文累加器**：STC 完全不涉及密文，这是我的加密扩展

---

## 问题②：明文累加器和密文累加器各维护在哪一边？

### 密文累加器（`encrypted_global_state`）

| 属性 | 说明 |
|------|------|
| **维护方** | 服务器（`AggregationServer`） |
| **数据类型** | CKKS 密文（`ts.CKKSVector`） |
| **存储位置** | `server.py: self.encrypted_global_state` |
| **初始化** | `init_encrypted_global_state()` 用公钥加密当前明文模型 |
| **更新** | `_update_encrypted_global_state()` 同态加法累加 |
| **是否下发客户端** | ✅ 是（作为密文全局模型下发） |
| **客户端是否需要解密** | ❌ 不需要（客户端在同态域操作） |

**流程**：

```
服务器: 加密全局模型 W_t^(enc) ──下发──> 客户端
客户端: 解密训练 ──> 计算本地更新 ──> 加密上传 δ_i^(enc)
服务器: 聚合 δ_i^(enc) ──> 得到 Δ_t^(enc) ──> 同态累加到 W_t^(enc)
```

### 明文累加器（`server_accumulator_plain`）

| 属性 | 说明 |
|------|------|
| **维护方** | 服务器（`PTopkModule`） |
| **数据类型** | 明文（`Dict[str, torch.Tensor]`） |
| **存储位置** | `ptopk.py: self.server_accumulator_plain` |
| **触发条件** | `ptopk.enabled=true` 且 `server_mode != 'none'` 且 `sparsification_enabled` |
| **更新** | `server_update_plain()` 中累加 |
| **是否下发客户端** | ❌ 不下发（只用于服务器内部平滑） |
| **客户端是否需要解密** | ❌ 不涉及（因为操作的是明文） |

**流程**：

```
客户端: 本地训练 ──> 稀疏化上传 δ_i
服务器: 聚合 δ_i ──> 得到明文 Δ_t
        └──> PTopk 累加器处理（delayed/momentum）
        └──> 得到实际更新量 update_t
        └──> 应用到明文全局模型 W_t
```

### 客户端误差累加器（`client_residual`）

| 属性 | 说明 |
|------|------|
| **维护方** | 客户端（`PTopkModule`） |
| **数据类型** | 明文（`List[np.ndarray]`，每个 batch 一个残差数组） |
| **存储位置** | `ptopk.py: self.client_residual` |
| **作用** | 补偿 TopK 压缩损失，把未上传的信息累积到下一轮 |

**总结**：

| 累加器 | 维护位置 | 数据类型 | 作用 |
|--------|---------|----------|------|
| 密文累加器 | 服务器 | 密文 | 加密联邦学习的全局状态 |
| 明文累加器 | 服务器 | 明文 | PTopk 的服务器端平滑/动量 |
| 误差累加器 | 客户端 | 明文 | PTopk 的误差反馈补偿 |

---

## 问题③：upload_difference = true/false 的区别与公式推导

### 3.1 标准 FedAvg 的两种形式

FedAvg 有两种等价写法，取决于客户端上传什么：

#### 形式 A：客户端上传完整模型（upload_difference = false）

客户端本地训练 $E$ 个 epoch，得到本地模型 $W_{t,i}$，**直接上传完整模型**。

服务器聚合（加权平均）：

$$
W_{t+1} = \sum_{i=1}^{n} \frac{n_i}{n} \cdot W_{t,i}
$$

其中 $n_i$ 是客户端 $i$ 的样本数，$n = \sum_i n_i$。

**等价变形**：令 $W_{t,i} = W_t + \delta_{t,i}$，其中 $\delta_{t,i} = W_{t,i} - W_t$ 是本地更新量：

$$
W_{t+1} = \sum_{i=1}^{n} \frac{n_i}{n} \cdot (W_t + \delta_{t,i}) = W_t \cdot \underbrace{\sum_{i=1}^{n} \frac{n_i}{n}}_{=1} + \sum_{i=1}^{n} \frac{n_i}{n} \cdot \delta_{t,i} = W_t + \sum_{i=1}^{n} \frac{n_i}{n} \cdot \delta_{t,i}
$$

#### 形式 B：客户端上传差值（upload_difference = true）

客户端本地训练后，**只上传差值** $\delta_{t,i} = W_{t,i} - W_t$。

服务器聚合：

$$
W_{t+1} = W_t + \sum_{i=1}^{n} \frac{n_i}{n} \cdot \delta_{t,i}
$$

### 3.2 两种形式在数学上完全等价

$$
\boxed{W_{t+1} = \sum_{i=1}^{n} \frac{n_i}{n} W_{t,i} \quad \Longleftrightarrow \quad W_{t+1} = W_t + \sum_{i=1}^{n} \frac{n_i}{n} (W_{t,i} - W_t)}
$$

**为什么代码中要区分？**

| 维度 | upload_difference = true | upload_difference = false |
|------|------------------------|--------------------------|
| **客户端上传内容** | 差值 $\delta_{t,i} = W_{t,i} - W_t$ | 完整模型 $W_{t,i}$ |
| **通信量** | 差值通常更稀疏（尤其配合 TopK） | 完整模型，无稀疏性 |
| **服务器操作** | $W_{t+1} = W_t + \text{agg}(\delta_{t,i})$ | $W_{t+1} = \text{agg}(W_{t,i})$ |
| **是否需要旧模型** | ✅ 需要（作为累加基础） | ❌ 不需要（直接替换） |
| **适用场景** | 差值稀疏、需要误差反馈 | 差值不稀疏、简单场景 |

### 3.3 在我的代码中的实现

**明文路径**（`server.py:99-145`）：

```python
if upload_difference:
    # W_{t+1} = W_t + η * Δ_t
    param.add_(update_tensor, alpha=actual_lr)
else:
    # W_{t+1} = Δ_t（聚合后的完整模型）
    param.copy_(update_tensor)
```

**密文路径**（`server.py:147-186`）：

```python
if upload_difference:
    # W_{t+1}^{(enc)} = W_t^{(enc)} ⊕ (η ⊙ Δ_t^{(enc)})
    global_cts[batch_idx] = evaluator.add(global_cts[batch_idx], ct)
else:
    # W_{t+1}^{(enc)} = Δ_t^{(enc)}（直接替换）
    global_cts[batch_idx] = agg_cts[ct_idx]
```

**客户端代码**（`client.py:115-121` 和 `234-246`）：

```python
if upload_difference:
    model_update = {name: new_params[name] - old_params[name] for name in old_params}
    # 上传的是 W_{t,i} - W_t
else:
    model_update = new_params
    # 上传的是完整 W_{t,i}
```

---

## 问题④：$\Delta_t^{(enc)}$ 指的是什么？

$\Delta_t^{(enc)}$ 是**第 $t$ 轮服务器聚合后的密文更新**，具体含义取决于 `upload_difference` 配置：

### 当 upload_difference = true 时

$$
\Delta_t^{(enc)} = \text{Enc}\left( \sum_{i=1}^{n_t} w_{t,i} \cdot (W_{t,i} - W_t) \right)
$$

即：所有客户端**本地差值**的**加权平均**的加密。

- $W_{t,i}$：客户端 $i$ 本地训练后的模型
- $W_t$：第 $t$ 轮全局模型
- $w_{t,i} = n_i / n$：客户端权重（样本数占比）
- $n_t$：第 $t$ 轮参与的客户端数

**密文累加器更新**：

$$
W_{t+1}^{(enc)} = W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})
$$

**解密后**：

$$
W_{t+1} = W_t + \eta \cdot \text{Dec}(\Delta_t^{(enc)})
$$

### 当 upload_difference = false 时

$$
\Delta_t^{(enc)} = \text{Enc}\left( \sum_{i=1}^{n_t} w_{t,i} \cdot W_{t,i} \right)
$$

即：所有客户端**完整本地模型**的**加权平均**的加密。

**密文累加器更新**：

$$
W_{t+1}^{(enc)} = \Delta_t^{(enc)}
$$

**解密后**：

$$
W_{t+1} = \text{Dec}(\Delta_t^{(enc)})
$$

### 图示

```
┌─────────────────────────────────────────────────────────────────────────┐
│  upload_difference = true                                               │
│                                                                         │
│  C1: Enc(W_{t,1} - W_t) ──┐                                             │
│  C2: Enc(W_{t,2} - W_t) ──┼──> 服务器聚合 ──> Δ_t^{(enc)} = Enc(Σ w_i δ_i) │
│  C3: Enc(W_{t,3} - W_t) ──┘                                             │
│                              ↓                                          │
│                    W_{t+1}^{(enc)} = W_t^{(enc)} ⊕ (η ⊙ Δ_t^{(enc)})     │
│                              ↓ 解密                                     │
│                    W_{t+1} = W_t + η · Dec(Δ_t^{(enc)})                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  upload_difference = false                                              │
│                                                                         │
│  C1: Enc(W_{t,1}) ──┐                                                   │
│  C2: Enc(W_{t,2}) ──┼──> 服务器聚合 ──> Δ_t^{(enc)} = Enc(Σ w_i W_{t,i})  │
│  C3: Enc(W_{t,3}) ──┘                                                   │
│                              ↓                                          │
│                    W_{t+1}^{(enc)} = Δ_t^{(enc)}  （直接替换）            │
│                              ↓ 解密                                     │
│                    W_{t+1} = Dec(Δ_t^{(enc)})                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 问题⑤：两个累加器为什么都有 $\eta$？STC/PTopk 中没有，这是新策略吗？

### 5.1 $\eta$ 是什么？

$\eta$ 是**服务器端学习率**（server learning rate），在代码中对应 `learning_rate` 参数。

### 5.2 标准 FedAvg 有没有 $\eta$？

**标准 FedAvg**（McMahan et al., 2017）的服务器端更新公式：

$$
W_{t+1} = \sum_{i=1}^{n} \frac{n_i}{n} W_{t,i}
$$

**没有额外的服务器端学习率**（等效于 $\eta = 1$）。

但如果客户端上传差值：

$$
W_{t+1} = W_t + \sum_{i=1}^{n} \frac{n_i}{n} (W_{t,i} - W_t)
$$

同样没有额外的 $\eta$。

### 5.3 STC/PTopk 原始论文有没有 $\eta$？

**STC 原始论文**（Sattler et al., 2020）：

服务器端就是简单平均，没有额外学习率：

$$
W_{t+1} = W_t + \frac{1}{n} \sum_{i=1}^{n} \text{sparse}(\delta_{t,i})
$$

**PTopk**（我的实现参考的扩展）：

原始 Error Feedback 论文中，服务器也是直接应用聚合更新，没有 $\eta$。

### 5.4 那我的代码为什么有 $\eta$？

这不是 STC/PTopk 的策略，而是 **FedAvg 的一种常见扩展**——**Server Learning Rate**。

在以下论文和框架中广泛使用：

| 来源 | 说明 |
|------|------|
| Reddi et al., "Adaptive Federated Optimization", ICLR 2021 | 系统讨论了服务器端优化器和学习率 |
| FedML / Flower / TFF | 主流 FL 框架都支持 `server_learning_rate` 参数 |
| 异步联邦学习 | 常用较小的服务器学习率来稳定收敛 |

**作用**：

服务器端学习率 $\eta$ 允许**独立于客户端本地训练步长**来控制全局更新幅度：

- 当客户端本地训练过度（本地模型偏离全局模型太远）时，较小的 $\eta$ 可以抑制更新幅度，防止发散
- 当需要加速收敛时，较大的 $\eta$ 可以加快全局模型移动
- 在加密场景下，由于量化/近似的存在，$\eta$ 可以补偿精度损失

**数学上**：

标准 FedAvg（无服务器学习率）：

$$
W_{t+1} = W_t + 1.0 \cdot \Delta_t
$$

带服务器学习率的 FedAvg：

$$
W_{t+1} = W_t + \eta \cdot \Delta_t
$$

当 $\eta = 1$ 时，两者等价。我的代码中 $\eta$ 默认通常为 1.0（配置文件中可调整）。

### 5.5 代码中的体现

```python
# server.py:169-172
if learning_rate != 1.0:
    ct = self.ckks_manager.evaluator.multiply_scalar(ct, learning_rate)
global_cts[batch_idx] = self.ckks_manager.evaluator.add(global_cts[batch_idx], ct)
```

```python
# server.py:127-128
param.add_(update_tensor, alpha=actual_lr)  # alpha 就是 η
```

**如果 `learning_rate = 1.0`**：
- 密文路径：跳过 `multiply_scalar`，直接同态加法
- 明文路径：`alpha=1.0`，等价于标准 FedAvg

### 5.6 与 STC/PTopk 的对比总结

| | 标准 STC/PTopk | 我的代码（可配置） |
|---|---|---|
| 服务器端学习率 | 无（固定为 1） | 有（`learning_rate`，默认 1） |
| 目的 | 简单直接 | 增加灵活性，抑制发散 |
| 是否新策略 | 否 | 否（FedAvg 扩展，广泛使用） |
| 推荐设置 | — | 本地训练稳定时设 1.0；需要稳定时设 0.1~0.5 |

---

## 问题⑥：解密后是否还要加上上一轮全局模型？

### 6.1 核心结论

| upload_difference | 解密后是否需要加旧模型 | 原因 |
|------------------|---------------------|------|
| **true** | ✅ **需要** | 聚合的是差值 $\delta_i = W_{t,i} - W_t$，新模型 = 旧模型 + 聚合差值 |
| **false** | ❌ **不需要** | 聚合的是完整模型 $W_{t,i}$，新模型 = 聚合结果直接替换 |

### 6.2 upload_difference = true 的完整推导

**客户端**（第 $i$ 个）：

1. 接收全局模型 $W_t$
2. 本地训练：$W_{t,i} = \text{LocalTrain}(W_t, D_i)$
3. 计算差值：$\delta_{t,i} = W_{t,i} - W_t$
4. 加密上传：$\delta_{t,i}^{(enc)} = \text{Enc}(\delta_{t,i})$

**服务器**：

1. 聚合（加权平均）：

$$
\Delta_t^{(enc)} = \bigoplus_{i=1}^{n_t} w_{t,i} \odot \delta_{t,i}^{(enc)}
$$

2. 同态累加到全局状态：

$$
W_{t+1}^{(enc)} = W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})
$$

3. **解密后**：

$$
W_{t+1} = \text{Dec}(W_{t+1}^{(enc)}) = W_t + \eta \cdot \Delta_t
$$

**注意**：这里的服务器累加器 $W_t^{(enc)}$ 就是上一轮的全局模型加密，所以解密后自然包含了旧模型。

### 6.3 upload_difference = false 的完整推导

**客户端**（第 $i$ 个）：

1. 接收全局模型 $W_t$
2. 本地训练：$W_{t,i} = \text{LocalTrain}(W_t, D_i)$
3. **直接上传完整模型**：$W_{t,i}^{(enc)} = \text{Enc}(W_{t,i})$

**服务器**：

1. 聚合（加权平均）：

$$
\Delta_t^{(enc)} = \bigoplus_{i=1}^{n_t} w_{t,i} \odot W_{t,i}^{(enc)}
$$

2. **直接替换**全局状态：

$$
W_{t+1}^{(enc)} = \Delta_t^{(enc)}
$$

3. **解密后**：

$$
W_{t+1} = \text{Dec}(\Delta_t^{(enc)}) = \sum_{i=1}^{n_t} w_{t,i} \cdot W_{t,i}
$$

**注意**：这里没有 $W_t$ 的参与，因为聚合结果已经是加权平均后的完整模型。

### 6.4 两种模式的数值对比

**场景**：2 个客户端，权重各 0.5，$\eta = 1.0$，初始模型 $W_0 = 100$

| | C1 | C2 |
|---|---|---|
| 本地训练后 $W_{1,i}$ | 110 | 120 |
| 差值 $\delta_{1,i} = W_{1,i} - W_0$ | 10 | 20 |

#### upload_difference = true

**客户端上传**：$\delta_{1,1}=10$, $\delta_{1,2}=20$

**服务器聚合**：

$$
\Delta_1 = 0.5 \times 10 + 0.5 \times 20 = 15
$$

**全局更新**：

$$
W_1 = W_0 + \eta \cdot \Delta_1 = 100 + 1.0 \times 15 = 115
$$

**验证**：

$$
0.5 \times 110 + 0.5 \times 120 = 55 + 60 = 115 \; \checkmark
$$

#### upload_difference = false

**客户端上传**：$W_{1,1}=110$, $W_{1,2}=120$

**服务器聚合**：

$$
\Delta_1 = 0.5 \times 110 + 0.5 \times 120 = 55 + 60 = 115
$$

**全局更新**：

$$
W_1 = \Delta_1 = 115
$$

**两种模式结果相同**（当 $\eta=1$ 时）。

### 6.5 加密场景下的流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    upload_difference = true（差值上传）                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  客户端 i:                                                                  │
│    W_{t,i} = LocalTrain(W_t)                                                │
│    δ_{t,i} = W_{t,i} - W_t       ← 计算差值                                  │
│    upload = Enc(δ_{t,i})         ← 加密差值上传                               │
│                                                                             │
│  服务器:                                                                    │
│    Δ_t^{(enc)} = weighted_average(Enc(δ_{t,1}), Enc(δ_{t,2}), ...)         │
│    W_{t+1}^{(enc)} = W_t^{(enc)} ⊕ (η ⊙ Δ_t^{(enc)})   ← 累加！旧模型+新差值   │
│                                                                             │
│  解密后:                                                                    │
│    W_{t+1} = Dec(W_{t+1}^{(enc)}) = W_t + η·Δ_t   ← 包含旧模型                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    upload_difference = false（完整模型上传）                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  客户端 i:                                                                  │
│    W_{t,i} = LocalTrain(W_t)                                                │
│    upload = Enc(W_{t,i})         ← 加密完整模型上传                           │
│                                                                             │
│  服务器:                                                                    │
│    Δ_t^{(enc)} = weighted_average(Enc(W_{t,1}), Enc(W_{t,2}), ...)         │
│    W_{t+1}^{(enc)} = Δ_t^{(enc)}              ← 替换！直接覆盖               │
│                                                                             │
│  解密后:                                                                    │
│    W_{t+1} = Dec(Δ_t^{(enc)}) = Σ w_i W_{t,i}   ← 不需要加旧模型              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、全公式汇总

### FedAvg + upload_difference = true（差值上传）

**客户端**：

$$
W_{t,i} = \text{LocalTrain}(W_t, D_i), \quad \delta_{t,i} = W_{t,i} - W_t
$$

**服务器聚合**：

$$
\Delta_t = \sum_{i=1}^{n_t} w_{t,i} \cdot \delta_{t,i}
$$

**全局更新**：

$$
\boxed{W_{t+1} = W_t + \eta \cdot \Delta_t}
$$

**加密形式**：

$$
\Delta_t^{(enc)} = \bigoplus_{i=1}^{n_t} w_{t,i} \odot \text{Enc}(\delta_{t,i}), \quad W_{t+1}^{(enc)} = W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})
$$

### FedAvg + upload_difference = false（完整模型上传）

**客户端**：

$$
W_{t,i} = \text{LocalTrain}(W_t, D_i)
$$

**服务器聚合**：

$$
\Delta_t = \sum_{i=1}^{n_t} w_{t,i} \cdot W_{t,i}
$$

**全局更新**：

$$
\boxed{W_{t+1} = \Delta_t}
$$

**加密形式**：

$$
\Delta_t^{(enc)} = \bigoplus_{i=1}^{n_t} w_{t,i} \odot \text{Enc}(W_{t,i}), \quad W_{t+1}^{(enc)} = \Delta_t^{(enc)}
$$

---

*文档结束*
