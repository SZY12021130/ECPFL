# 累加器设计详解：明文累加器 vs 密文累加器

> 你的代码中设计了**两种累加器**：
> 1. **密文累加器** (`encrypted_global_state`)：用于加密联邦学习路径，服务器在密文域维护全局模型
> 2. **明文累加器** (`server_accumulator_plain`)：用于 PTopk 的 Error Feedback 机制，支持 `none` / `delayed` / `momentum` 三种模式

---

## 一、密文累加器（`encrypted_global_state`）

### 1.1 位置与代码

- **位置**：`server.py: AggregationServer.encrypted_global_state`
- **初始化**：`init_encrypted_global_state()`（用公钥加密当前明文模型）
- **更新**：`_update_encrypted_global_state()`（同态加法累加）

### 1.2 原理

服务器不下发明文模型，而是在**密文域**维护一个全局状态 $W_t^{(enc)}$。每轮收到客户端聚合后的密文更新 $\Delta_t^{(enc)}$，通过 CKKS 同态加法直接累加：

$$
W_{t+1}^{(enc)} = W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})
$$

其中：
- $\oplus$：CKKS 同态加法（`evaluator.add()`）
- $\odot$：CKKS 密文×明文标量乘法（`evaluator.multiply_scalar()`，当 $\eta \neq 1$ 时）
- $\eta$：学习率（learning rate）
- $t$：轮次索引

### 1.3 公式推导

设第 $t$ 轮有 $n_t$ 个客户端参与，每个客户端 $i$ 提交密文更新 $\delta_{t,i}^{(enc)}$（已加权归一化）。聚合后的密文更新为：

$$
\Delta_t^{(enc)} = \bigoplus_{i=1}^{n_t} \delta_{t,i}^{(enc)}
$$

密文累加器更新规则：

$$
W_{t+1}^{(enc)} =
\begin{cases}
W_t^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)}), & \text{if upload\_difference = true} \\[8pt]
\Delta_t^{(enc)}, & \text{if upload\_difference = false}
\end{cases}
$$

**按 batch 展开**（因为 `__sparse__` 格式下每个 batch 是一个独立密文）：

对第 $j$ 个 batch（$j = 0, 1, \dots, M-1$）：

$$
W_{t+1}^{(enc)}[j] =
\begin{cases}
W_t^{(enc)}[j] \oplus (\eta \odot \Delta_t^{(enc)}[j]), & \text{if } \Delta_t^{(enc)} \text{ 提交了 batch } j \\[8pt]
W_t^{(enc)}[j], & \text{otherwise}
\end{cases}
$$

### 1.4 密文累加器的特点

| 特性 | 说明 |
|------|------|
| **数据类型** | 密文（CKKS 加密后的 `ts.CKKSVector`） |
| **运算类型** | 同态加法（`+`）+ 密文×明文标量乘法（`* lr`） |
| **安全性** | 服务器始终看不到明文模型参数 |
| **同步方式** | 每轮都累加（无延迟） |
| **适用场景** | 加密联邦学习（服务器不下发明文） |

---

## 二、明文累加器（`server_accumulator_plain`）

### 2.1 位置与代码

- **位置**：`ptopk.py: PTopkModule.server_accumulator_plain`
- **调用**：`_update_plain_global_model()` 中，在应用聚合更新之前调用 `ptopk.server_update_plain()`
- **三种模式**：`none` / `delayed` / `momentum`

### 2.2 原理

PTopk（Packed TopK with Error Feedback）的服务器端累加器，用于**平滑稀疏化带来的噪声**或**延迟同步以减少通信**。它操作的是**明文张量**（`Dict[str, torch.Tensor]`），因为 PTopk 在明文路径上工作。

设第 $t$ 轮聚合后的明文更新为 $\Delta_t \in \mathbb{R}^d$（已解密并完成稀疏补全）。

#### 模式 1：`none`（无累加器）

直接应用更新，不累加：

$$
\text{update}_t = \eta \cdot \Delta_t
$$

#### 模式 2：`delayed`（延迟同步）

维护一个明文累加器 $A_t$，每 $K$ 轮才将累加值应用到全局模型：

**累加阶段**（每轮都执行）：

$$
A_t = A_{t-1} + \eta \cdot \Delta_t
$$

**释放阶段**（当 $t \mod K = 0$ 时）：

$$
\text{update}_t = A_t, \quad A_t \leftarrow \mathbf{0}
$$

**跳过阶段**（当 $t \mod K \neq 0$ 时）：

$$
\text{update}_t = \mathbf{0}
$$

其中：
- $A_t$：`server_accumulator_plain`，明文张量
- $K$：`sync_interval`，同步间隔
- $A_0 = \mathbf{0}$

#### 模式 3：`momentum`（动量更新）

维护一个动量累加器 $A_t$，每轮都应用到全局模型：

$$
A_t = \beta \cdot A_{t-1} + (1 - \beta) \cdot \eta \cdot \Delta_t
$$

$$
\text{update}_t = A_t
$$

其中：
- $\beta$：`momentum_beta`，动量系数（通常 0.9）
- $A_0 = \mathbf{0}$

### 2.3 三种模式对比

| 模式 | 累加器公式 | 何时应用到全局模型 | 用途 |
|------|-----------|-------------------|------|
| `none` | 无 | 每轮都应用 | 无平滑，直接更新 |
| `delayed` | $A_t = A_{t-1} + \eta \Delta_t$ | 每隔 $K$ 轮应用一次 | 平滑噪声，减少更新频率 |
| `momentum` | $A_t = \beta A_{t-1} + (1-\beta) \eta \Delta_t$ | 每轮都应用 | 动量加速，抑制震荡 |

### 2.4 明文累加器的特点

| 特性 | 说明 |
|------|------|
| **数据类型** | 明文（`torch.Tensor`） |
| **运算类型** | 普通张量加法和数乘 |
| **安全性** | 服务器能看到明文更新（前提是已经解密） |
| **适用场景** | 明文联邦学习路径，或加密路径中解密后的更新 |

---

## 三、完整数学例子

### 3.1 场景设定

- 单参数（标量）简化：$d = 1$
- 学习率：$\eta = 0.1$
- 共 5 轮（$t = 1, 2, 3, 4, 5$）
- 每轮聚合后的明文更新 $\Delta_t$：

| 轮次 $t$ | $\Delta_t$ |
|---------|-----------|
| 1 | 10 |
| 2 | 20 |
| 3 | 15 |
| 4 | 5 |
| 5 | 25 |

### 3.2 密文累加器例子

假设初始全局模型 $W_0^{(enc)} = \text{Enc}(100)$。

**每轮更新**（`upload_difference = true`）：

| 轮次 $t$ | 聚合密文更新 $\Delta_t^{(enc)}$ | 缩放后 $\eta \odot \Delta_t^{(enc)}$ | 同态累加 $W_t^{(enc)} = W_{t-1}^{(enc)} \oplus (\eta \odot \Delta_t^{(enc)})$ | 解密后 $W_t$ |
|---------|-------------------------------|-------------------------------------|--------------------------------------------------------------------------|-------------|
| 0 | — | — | $\text{Enc}(100)$ | 100 |
| 1 | $\text{Enc}(10)$ | $\text{Enc}(1.0)$ | $\text{Enc}(100) \oplus \text{Enc}(1.0) = \text{Enc}(101)$ | 101 |
| 2 | $\text{Enc}(20)$ | $\text{Enc}(2.0)$ | $\text{Enc}(101) \oplus \text{Enc}(2.0) = \text{Enc}(103)$ | 103 |
| 3 | $\text{Enc}(15)$ | $\text{Enc}(1.5)$ | $\text{Enc}(103) \oplus \text{Enc}(1.5) = \text{Enc}(104.5)$ | 104.5 |
| 4 | $\text{Enc}(5)$ | $\text{Enc}(0.5)$ | $\text{Enc}(104.5) \oplus \text{Enc}(0.5) = \text{Enc}(105)$ | 105 |
| 5 | $\text{Enc}(25)$ | $\text{Enc}(2.5)$ | $\text{Enc}(105) \oplus \text{Enc}(2.5) = \text{Enc}(107.5)$ | 107.5 |

**公式展开**（第 3 轮为例）：

$$
W_3^{(enc)} = W_2^{(enc)} \oplus (\eta \odot \Delta_3^{(enc)}) = \text{Enc}(103) \oplus \text{Enc}(1.5) = \text{Enc}(103 + 1.5) = \text{Enc}(104.5)
$$

### 3.3 明文累加器：`delayed` 模式例子

设同步间隔 $K = 3$（每 3 轮应用一次）。

初始累加器 $A_0 = 0$，初始模型 $W_0 = 100$。

| 轮次 $t$ | $\Delta_t$ | 累加器更新 $A_t = A_{t-1} + \eta \Delta_t$ | $t \mod K = 0$? | 应用到模型? | 全局模型 $W_t$ | 累加器 $A_t$ 释放后 |
|---------|-----------|------------------------------------------|----------------|------------|--------------|------------------|
| 1 | 10 | $0 + 0.1 \times 10 = 1$ | $1 \mod 3 \neq 0$ | ❌ 跳过 | 100 | $1$ |
| 2 | 20 | $1 + 0.1 \times 20 = 3$ | $2 \mod 3 \neq 0$ | ❌ 跳过 | 100 | $3$ |
| 3 | 15 | $3 + 0.1 \times 15 = 4.5$ | $3 \mod 3 = 0$ ✓ | ✅ 应用 | $100 + 4.5 = 104.5$ | $0$（清零） |
| 4 | 5 | $0 + 0.1 \times 5 = 0.5$ | $4 \mod 3 \neq 0$ | ❌ 跳过 | 104.5 | $0.5$ |
| 5 | 25 | $0.5 + 0.1 \times 25 = 3$ | $5 \mod 3 \neq 0$ | ❌ 跳过 | 104.5 | $3$ |

**公式展开**（第 3 轮为例）：

**步骤 1：累加**

$$
A_3 = A_2 + \eta \cdot \Delta_3 = 3 + 0.1 \times 15 = 4.5
$$

**步骤 2：检查是否到达同步点**

$$
3 \mod 3 = 0 \quad \Rightarrow \quad \text{释放累加器}
$$

**步骤 3：应用到全局模型**

$$
W_3 = W_2 + A_3 = 100 + 4.5 = 104.5
$$

**步骤 4：清零累加器**

$$
A_3 \leftarrow 0
$$

### 3.4 明文累加器：`momentum` 模式例子

设动量系数 $\beta = 0.9$。

初始累加器 $A_0 = 0$，初始模型 $W_0 = 100$。

| 轮次 $t$ | $\Delta_t$ | $\eta \Delta_t$ | 动量累加 $A_t = 0.9 A_{t-1} + 0.1 \cdot \eta \Delta_t$ | 应用到模型 $W_t = W_{t-1} + A_t$ |
|---------|-----------|----------------|-----------------------------------------------------|--------------------------------|
| 1 | 10 | 1.0 | $0.9 \times 0 + 0.1 \times 1.0 = \mathbf{0.1}$ | $100 + 0.1 = 100.1$ |
| 2 | 20 | 2.0 | $0.9 \times 0.1 + 0.1 \times 2.0 = 0.09 + 0.2 = \mathbf{0.29}$ | $100.1 + 0.29 = 100.39$ |
| 3 | 15 | 1.5 | $0.9 \times 0.29 + 0.1 \times 1.5 = 0.261 + 0.15 = \mathbf{0.411}$ | $100.39 + 0.411 = 100.801$ |
| 4 | 5 | 0.5 | $0.9 \times 0.411 + 0.1 \times 0.5 = 0.3699 + 0.05 = \mathbf{0.4199}$ | $100.801 + 0.4199 = 101.2209$ |
| 5 | 25 | 2.5 | $0.9 \times 0.4199 + 0.1 \times 2.5 = 0.37791 + 0.25 = \mathbf{0.62791}$ | $101.2209 + 0.62791 = 101.84881$ |

**公式展开**（第 3 轮为例）：

**步骤 1：计算当前学习率缩放后的更新**

$$
\eta \cdot \Delta_3 = 0.1 \times 15 = 1.5
$$

**步骤 2：动量累加**

$$
A_3 = \beta \cdot A_2 + (1 - \beta) \cdot \eta \cdot \Delta_3 = 0.9 \times 0.29 + 0.1 \times 1.5 = 0.261 + 0.15 = 0.411
$$

**步骤 3：应用到全局模型**

$$
W_3 = W_2 + A_3 = 100.39 + 0.411 = 100.801
$$

### 3.5 三种明文模式 + 密文模式对比

| 轮次 | `none` | `delayed` ($K=3$) | `momentum` ($\beta=0.9$) | 密文累加器 |
|------|--------|-------------------|--------------------------|-----------|
| 0 | 100 | 100 | 100 | 100 (Enc) |
| 1 | 101 | **100** (跳过) | 100.1 | 101 (Enc) |
| 2 | 103 | **100** (跳过) | 100.39 | 103 (Enc) |
| 3 | 104.5 | **104.5** (释放) | 100.801 | 104.5 (Enc) |
| 4 | 105 | **104.5** (跳过) | 101.2209 | 105 (Enc) |
| 5 | 107.5 | **104.5** (跳过) | 101.84881 | 107.5 (Enc) |

> **观察**：
> - `none` 和密文累加器每轮都更新，结果完全一致
> - `delayed` 前 2 轮跳过，第 3 轮一次性释放累积值 $(1+2+1.5)=4.5$，模型从 100 跳到 104.5
> - `momentum` 早期更新小（受历史影响大），后期逐渐累积响应新信号

---

## 四、两种累加器的关系与使用时机

### 4.1 架构位置

```
┌─────────────────────────────────────────────────────────────────────┐
│                         联邦学习服务器                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────┐    ┌───────────────────────────────┐  │
│  │   密文累加器             │    │   明文累加器 (PTopk)           │  │
│  │   encrypted_global_state │    │   server_accumulator_plain     │  │
│  ├─────────────────────────┤    ├───────────────────────────────┤  │
│  │  数据类型: CKKS 密文      │    │  数据类型: torch.Tensor        │  │
│  │  运算: 同态加法 + 标量乘   │    │  运算: 普通张量加法 + 数乘      │  │
│  │  触发: 每轮都累加         │    │  触发: none/delayed/momentum   │  │
│  │  路径: _update_encrypted_ │    │  路径: _update_plain_          │  │
│  │         global_state()    │    │         global_model()         │  │
│  └─────────────────────────┘    └───────────────────────────────┘  │
│                                                                     │
│  关系：互斥使用                                                      │
│  - 如果用加密路径 → 只用密文累加器                                    │
│  - 如果用明文路径 + PTopk → 可能用到明文累加器                        │
│  - PTopk 明文累加器只在 sparsification_enabled 时生效                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 使用时机

| 配置 | 使用的累加器 | 代码路径 |
|------|------------|---------|
| `enc=true`（加密模式） | **密文累加器** | `server._update_encrypted_global_state()` |
| `enc=false` + `ptopk.enable=false` | 无累加器 | `server._update_plain_global_model()` 直接应用更新 |
| `enc=false` + `ptopk.enable=true` + `server_mode=none` | 无累加器（PTopk 包装稀疏化策略，但服务器不累加） | `ptopk.server_update_plain()` 直接返回 $\Delta_t$ |
| `enc=false` + `ptopk.enable=true` + `server_mode=delayed` | **明文累加器**（delayed） | `ptopk.server_update_plain()` 累加并周期性释放 |
| `enc=false` + `ptopk.enable=true` + `server_mode=momentum` | **明文累加器**（momentum） | `ptopk.server_update_plain()` 动量更新 |

### 4.3 关键代码片段对照

**密文累加器**（`server.py:147-186`）：

```python
def _update_encrypted_global_state(self, encrypted_update, learning_rate):
    global_cts = self.encrypted_global_state['ciphertexts']
    for batch_idx, is_selected in enumerate(agg_mask):
        if is_selected:
            ct = agg_cts[ct_idx]
            if learning_rate != 1.0:
                ct = self.ckks_manager.evaluator.multiply_scalar(ct, learning_rate)
            global_cts[batch_idx] = self.ckks_manager.evaluator.add(
                global_cts[batch_idx], ct          # ← 同态加法累加
            )
```

**明文累加器**（`ptopk.py:103-149`）：

```python
def server_update_plain(self, aggregated_delta_plain, learning_rate):
    if self.server_mode == 'delayed':
        for k in aggregated_delta_plain:
            self.server_accumulator_plain[k] += aggregated_delta_plain[k] * learning_rate
        if self.round_counter % self.sync_interval == 0:
            update = {k: v.clone() for k, v in self.server_accumulator_plain.items()}
            for k in self.server_accumulator_plain:
                self.server_accumulator_plain[k].zero_()   # ← 清零
            return update
        else:
            return {k: torch.zeros_like(v) for k, v in aggregated_delta_plain.items()}  # ← 跳过
    
    elif self.server_mode == 'momentum':
        beta = self.momentum_beta
        for k in self.server_accumulator_plain:
            self.server_accumulator_plain[k] = (
                beta * self.server_accumulator_plain[k] + 
                (1 - beta) * aggregated_delta_plain[k] * learning_rate
            )
        return {k: v.clone() for k, v in self.server_accumulator_plain.items()}
```

---

## 五、公式汇总

### 密文累加器

$$
\boxed{W_{t+1}^{(enc)}[j] = W_t^{(enc)}[j] \oplus (\eta \odot \Delta_t^{(enc)}[j])}
$$

### 明文累加器：`delayed`

$$
\boxed{A_t = A_{t-1} + \eta \cdot \Delta_t, \quad \text{update}_t =
\begin{cases}
A_t, & t \mod K = 0 \\
\mathbf{0}, & \text{otherwise}
\end{cases}}
$$

### 明文累加器：`momentum`

$$
\boxed{A_t = \beta \cdot A_{t-1} + (1 - \beta) \cdot \eta \cdot \Delta_t, \quad \text{update}_t = A_t}
$$

---

*文档结束*
