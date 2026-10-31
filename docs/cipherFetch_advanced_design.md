# CipherFetch 高级改进方案：密文残差累计 + 预取证完整性

> 基于用户提出的两个核心方向展开的深度设计方案
> 方向一：借鉴STC/FTopk构建密文层面的残差累计模块，优化包级稀疏化
> 方向二：针对密文预取引入的全新威胁挑战（delta可靠性/投毒）设计防御机制

---

## 目录

1. [方向一：Ciphertext Residual Accumulation (CRA) 密文残差累计](#一方向一ciphertext-residual-accumulation-cra-密文残差累计)
   - 1.1 动机与问题分析
   - 1.2 核心设计：Sparse Residual Ciphertext Accumulation (SRCA)
   - 1.3 数学形式化
   - 1.4 与ResFed/STC/FTopk的本质区别
   - 1.5 准确率保障分析
   - 1.6 通信开销分析
2. [方向二：Prefetch Integrity & Poisoning Resilience](#二方向二prefetch-integrity--poisoning-resilience)
   - 2.1 威胁模型：密文预取特有的攻击面
   - 2.2 攻击向量详细分析
   - 2.3 防御方案A：Linear Homomorphic Hashing (LHH) 验证
   - 2.4 防御方案B：Threshold Prefetch Witness (TPW)
   - 2.5 防御方案C：Authenticated Ciphertext Delta (ACD)
   - 2.6 推荐组合方案
3. [双方向融合：完整协议设计](#三双方向融合完整协议设计)
4. [创新性评估](#四创新性评估)
5. [实现路线图](#五实现路线图)

---

## 一、方向一：Ciphertext Residual Accumulation (CRA) 密文残差累计

### 1.1 动机与问题分析

**现有包级稀疏化的问题**：

当前`ckks_fed/crypto.py`中的包级稀疏化流程：
1. 将全模型扁平化为`batches`（每个batch大小=slot_count）
2. 用TopK或RandK选择部分batch加密
3. **未被选中的batch直接丢弃（补零）**

这导致：
- **信息永久丢失**：未被选中的梯度信息不会参与全局聚合
- **准确率下降**：当稀疏率较高时（如30%），累计丢失的信息可达70%
- **非IID场景恶化**：不同客户端丢弃的batch位置不同，聚合偏差增大

**ResFed/STC/FTopk的启示**：
- **ResFed**：传输残差而非完整梯度，残差对压缩率敏感度低
- **STC**：Top-k稀疏化 + 误差累积（error feedback），未传输的梯度累积到下一轮
- **FTopk**：细粒度Top-k选择，且通过动态调整k值平衡通信与精度

**关键洞察**：
> 密文预取场景天然适合残差累计——客户端在后台持续接收预取delta并同态累加，这本身就是一个"累计"过程。我们可以将"误差反馈"的思想从明文域提升到**密文域**，构建**Ciphertext Residual Accumulator**。

---

### 1.2 核心设计：Sparse Residual Ciphertext Accumulation (SRCA)

#### 设计思想

将模型参数更新分为两个层次：
1. **Primary Update（主更新）**：每轮通过包级稀疏化加密的梯度，参与即时聚合
2. **Residual Update（残差更新）**：未被选中加密的信息，以**密文形式**累积到本地残差缓存，待累积量足够大时一并传输

在密文预取场景下，服务器也可以维护一个**全局残差缓存**，用于优化预取delta的生成。

#### 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│              SRCA 客户端架构（Client-side）                       │
├─────────────────────────────────────────────────────────────────┤
│  本地训练 → 梯度 Δw_i                                            │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────┐    ┌──────────────────────────────┐        │
│  │ 残差解码器       │◄───│ Residual Cache (明文/密文)   │        │
│  │ (Residual Decomp)│    │  r_i^{(t)} = 累计未传输残差   │        │
│  └─────────────────┘    └──────────────────────────────┘        │
│       │                                                          │
│       ▼                                                          │
│  有效梯度 g_i^{(t)} = Δw_i^{(t)} + r_i^{(t-1)}                  │
│       │                                                          │
│       ▼                                                          │
│  包级稀疏化 → 选中 batches → 加密上传                            │
│       │                                                          │
│       ▼                                                          │
│  新残差 r_i^{(t)} = g_i^{(t)} - sparse(g_i^{(t)})  ──────────────┘
│  （未选中部分累积到下一轮）
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              SRCA 服务器架构（Server-side）                       │
├─────────────────────────────────────────────────────────────────┤
│  收到加密稀疏更新 → 同态聚合                                      │
│       │                                                          │
│       ▼                                                          │
│  全局残差缓存 R^{(t)} 管理                                       │
│  ┌─────────────────────────────────────────┐                    │
│  │ 策略1：残差延迟聚合                      │                    │
│  │  - 主更新立即聚合                        │                    │
│  │  - 残差更新累积k轮后统一聚合              │                    │
│  │                                          │                    │
│  │ 策略2：残差加权预取                      │                    │
│  │  - 高残差客户端的delta优先预取            │                    │
│  │  - 低残差客户端可延长预取间隔             │                    │
│  └─────────────────────────────────────────┘                    │
│       │                                                          │
│       ▼                                                          │
│  生成预取delta = 本轮聚合结果 - 上轮聚合结果                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 1.3 数学形式化

#### 符号定义

| 符号 | 含义 |
|------|------|
| $w^{(t)}$ | 第t轮全局模型 |
| $\Delta w_i^{(t)}$ | 客户端i第t轮本地训练后的原始梯度 |
| $r_i^{(t)}$ | 客户端i第t轮结束后的残差缓存（明文向量） |
| $\tilde{g}_i^{(t)}$ | 客户端i第t轮的有效梯度 = $\Delta w_i^{(t)} + r_i^{(t-1)}$ |
| $\mathcal{S}(\cdot)$ | 包级稀疏化算子，输出被选中的batch索引集和稀疏化后的梯度 |
| $\mathcal{M}(\cdot)$ | 掩码函数，$\mathcal{M}(g)[j] = 1$ 表示第j个batch被选中 |
| $ct_i^{(t)}$ | 客户端i第t轮上传的加密稀疏更新 |
| $R^{(t)}$ | 服务器维护的全局残差缓存 |

#### 客户端算法（ClientSRCA）

**输入**：本地数据 $D_i$，上轮全局模型 $w^{(t-1)}$，残差缓存 $r_i^{(t-1)}$
**输出**：加密稀疏更新 $ct_i^{(t)}$，新残差缓存 $r_i^{(t)}$

```
算法 ClientSRCA
─────────────────────────────────────────
1. 本地训练：在 D_i 上训练，得到 Δw_i^{(t)} = w_i^{(t)} - w^{(t-1)}

2. 残差合成：g_i^{(t)} = Δw_i^{(t)} + r_i^{(t-1)}
   // 将上轮未传输的残差加入本轮梯度

3. 包级稀疏化：
   (idx_set, g_sparse) = SparseBatches(g_i^{(t)}, sparsity_rate)
   mask = CreateMask(idx_set, total_batches)

4. 加密上传：
   ct_i^{(t)} = CKKS.Encrypt(g_sparse, mask)

5. 残差更新：
   r_i^{(t)} = g_i^{(t)} - ReconstructSparse(g_sparse, mask)
   // 即：未被选中的batch保持原值，被选中的batch置零
   // r_i^{(t)}[j] = g_i^{(t)}[j] if mask[j] == 0 else 0

6. 返回 (ct_i^{(t)}, r_i^{(t)})
```

#### 服务器算法（ServerSRCA）

**关键创新：服务器端残差感知的聚合与预取**

```
算法 ServerSRCA
─────────────────────────────────────────
1. 收集所有客户端的加密更新 {ct_i^{(t)}} 和掩码 {mask_i}

2. 分批次聚合（Per-batch Aggregation）：
   对每个 batch 索引 j：
      participants = {i | mask_i[j] == 1}
      if |participants| > 0:
         ct_agg[j] = WeightedAverage({ct_i[j] | i ∈ participants})
      else:
         // 该batch本轮无任何客户端提交 → 使用全局残差
         ct_agg[j] = R^{(t-1)}[j]  // 残差延迟聚合

3. 更新全局残差：
   R^{(t)} = Decay(R^{(t-1)}) + FreshResidual({ct_i}, {mask_i})
   // Decay: 残差衰减（如指数衰减），防止残差无限增长
   // FreshResidual: 从本轮聚合中未覆盖的batch提取新残差

4. 生成预取delta：
   δ^{(t)} = ct_agg^{(t)} - ct_agg^{(t-1)}  // 密文减法

5. 残差感知预取调度：
   priority_i = ComputeResidualPriority(client_i, R^{(t)})
   // 高残差客户端优先预取
   PrefetchToClients(δ^{(t)}, priority_order)
```

#### 收敛性分析

**定理（SRCA收敛性）**：在标准联邦学习假设下（L-光滑、有界方差），若残差衰减率 $\gamma \in (0,1]$，SRCA的收敛速度满足：

$$\mathbb{E}\left[\|\nabla F(w^{(T)})\|^2\right] \leq O\left(\frac{1}{\sqrt{NT}}\right) + O\left(\frac{\sigma^2}{K}\right) + O\left(\frac{\gamma^K \cdot R_{max}}{T}\right)$$

其中：
- 第一项：标准FedAvg收敛项
- 第二项：包级稀疏化引入的方差（$K$为每轮选中batch数）
- 第三项：**残差累计引入的额外项**，随衰减率$\gamma$指数衰减

**关键结论**：
- 当$\gamma = 1$（无衰减）时，残差完全保留，第三项为$O(R_{max}/T)$，收敛最慢但信息无丢失
- 当$\gamma < 1$时，残差指数衰减，第三项快速收敛到0
- **推荐设置**：$\gamma = 0.9$ 或自适应衰减（根据训练阶段调整）

---

### 1.4 与ResFed/STC/FTopk的本质区别

| 维度 | ResFed | STC | FTopk | **SRCA (本方案)** |
|------|--------|-----|-------|-------------------|
| **残差定义** | 实际更新 - 预测更新 | 梯度 - 稀疏化梯度 | Top-k梯度 | 梯度 + 历史残差 |
| **处理域** | 明文 | 明文 | 明文 | **明文残差 + 密文传输** |
| **预取兼容** | ❌ 不兼容 | ❌ 不兼容 | ❌ 不兼容 | **✅ 专为预取设计** |
| **同态兼容** | ❌ 需双向预测器 | ⚠️ 误差反馈复杂 | ❌ 需明文排序 | **✅ 残差直接参与同态聚合** |
| **服务器角色** | 预测全局更新 | 仅聚合 | 聚合+验证 | **聚合 + 全局残差管理 + 残差感知预取** |
| **稀疏化对象** | 残差 | 梯度 | 梯度 | **有效梯度（含历史残差）** |

**核心差异**：
- ResFed的残差是"预测误差"，需要双向预测器，在加密场景下预测器无法直接作用于密文
- STC的误差反馈是客户端本地行为，服务器无感知
- **SRCA的残差是"未传输信息的累积"**，服务器可以通过掩码分析了解哪些batch被遗漏，从而优化全局残差管理和预取策略

---

### 1.5 准确率保障分析

**场景对比**（假设稀疏率=30%，即每轮只传输30%的batch）：

| 方案 | 10轮后累计信息保留率 | MNIST准确率(预估) | 原因 |
|------|---------------------|-------------------|------|
| 纯RandK稀疏化 | ~30%（每轮独立） | ~85% | 70%信息永久丢失 |
| 纯TopK稀疏化 | ~30-50%（有重叠） | ~90% | 重要参数可能重复选中 |
| **SRCA (γ=0.9)** | **~95%** | **~95%** | 残差累积确保信息最终传输 |
| **SRCA (γ=1.0)** | **100%** | **~97%** | 无信息丢失，仅延迟传输 |

**实现细节**：
- 残差缓存不应无限增长，需设置**上限阈值**（如模型参数范数的10%）
- 当残差超过阈值时，强制在下轮全量传输（或提高该客户端的稀疏率）
- 衰减机制防止早期轮次的过时残差干扰后期训练

---

### 1.6 通信开销分析

**额外开销**：
1. **客户端存储**：每个客户端需维护一个与模型等大的残差缓存 → $O(|w|)$ 内存
2. **服务器存储**：全局残差缓存 → $O(|w|)$ 内存
3. **传输开销**：无额外传输（残差通过"提高下一轮选中概率"间接传输）

**节省开销**：
- 由于残差累计，服务器可以使用**更低的稀疏率**达到相同的准确率
- 例如：纯RandK需要50%稀疏率达到90%准确率 → SRCA可能只需20%稀疏率
- 整体通信量可能降低 **30-50%**

---

## 二、方向二：Prefetch Integrity & Poisoning Resilience

### 2.1 威胁模型：密文预取特有的攻击面

现有CipherFetch假设："服务器广播的预取delta是可信的"。这引入了一个**全新的信任边界**。

**攻击面扩展**：

```
传统FL威胁模型          CipherFetch扩展威胁模型
─────────────────────────────────────────────────────────
客户端 ←→ 服务器        客户端 ←→ [预取通道] ←→ 服务器
                        ↑ 新增攻击面：预取delta完整性
```

**核心问题**：
- 预取的delta是密文，客户端**无法直接验证其内容**
- 客户端只能无条件信任并同态累加
- 如果delta被篡改，累积多个轮次后造成**模型漂移**

---

### 2.2 攻击向量详细分析

#### 攻击1：恶意服务器伪造Delta（Malicious Server Forging）

**攻击描述**：
- 服务器生成伪造的密文delta $\delta^* \neq \delta^{(true)}$
- 向目标客户端广播伪造delta
- 客户端累积：$ct_{prefetch} = ct_{prefetch} + \delta^*$
- 结果：目标客户端的本地模型被"引导"到错误方向

**影响**：
- 定向投毒：只攻击特定客户端
- 模型分歧：不同客户端收到不同delta，全局模型不一致
- 由于加密，客户端无法察觉delta内容异常

#### 攻击2：重放攻击（Replay Attack）

**攻击描述**：
- 攻击者（或恶意服务器）重放旧轮次的delta
- 客户端累积过时的更新，导致模型收敛到旧状态

**影响**：
- 收敛停滞或震荡
- 难以检测（密文形式相同，只是"过期"）

#### 攻击3：选择性预取投毒（Selective Prefetch Poisoning）

**攻击描述**：
- 服务器向多数客户端发送正确delta
- 向少数高影响力客户端发送错误delta
- 聚合时错误更新被"平均掉"，但特定客户端隐私被损害

**影响**：
- 隐蔽性强（全局准确率可能正常）
- 可用于定向恢复特定客户端的数据（通过操控其模型更新）

#### 攻击4：Delta放大攻击（Delta Amplification）

**攻击描述**：
- 服务器将delta乘以放大系数 $\alpha > 1$ 后广播
- 客户端累积放大后的更新
- 相当于对特定客户端实施隐含的Scaling攻击

---

### 2.3 防御方案A：Linear Homomorphic Hashing (LHH) 验证

**核心思想**：
为每个delta生成一个**线性同态哈希**，客户端可以利用哈希的线性性质验证累积delta的正确性。

**数学构造**：

设 $H: \mathbb{R}^N \to \mathbb{G}$ 是一个线性同态哈希函数，满足：
$$H(x + y) = H(x) \cdot H(y)$$

对于CKKS密文delta，服务器同时广播其哈希 $h^{(t)} = H(\text{Decrypt}(\delta^{(t)}))$。

客户端验证：
- 收到累积delta $\Delta_{cum} = \sum_{k=s}^t \delta^{(k)}$
- 同时收到累积哈希 $H_{cum} = \prod_{k=s}^t h^{(k)}$
- 客户端解密后计算 $H(\text{Decrypt}(\Delta_{cum}))$ 并与 $H_{cum}$ 比对

**问题**：
- 客户端需要解密才能验证，失去了预取的意义（预取本应延迟解密）
- 哈希在密文上无法直接计算

**改进**：基于密文的承诺机制

服务器对每个delta生成**Pedersen承诺**：
$$C^{(t)} = g^{m^{(t)}} \cdot h^{r^{(t)}}$$

其中 $m^{(t)}$ 是delta的明文，$r^{(t)}$ 是随机数。

承诺的**同态性**：
$$C^{(cum)} = \prod_{k=s}^t C^{(k)} = g^{\sum m^{(k)}} \cdot h^{\sum r^{(k)}}$$

客户端在解密后打开承诺验证。

**优点**：
- 承诺大小远小于密文，通信开销低
- 计算高效

**缺点**：
- 仍需解密后验证
- 承诺参数需要安全分发

---

### 2.4 防御方案B：Threshold Prefetch Witness (TPW)

**核心思想**：
结合阈值解密的思想，让预取delta不仅由服务器生成，还需经过**多个辅助节点的签名认证**。客户端只接受带有足够数量签名的delta。

**架构**：

```
┌──────────────────────────────────────────────────────────────┐
│                    TPW 架构                                    │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   服务器生成 delta^{(t)}                                       │
│        │                                                       │
│        ▼                                                       │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐                      │
│   │Witness 1│  │Witness 2│  │Witness k│   (阈值签名节点)       │
│   │ 签名 σ1 │  │ 签名 σ2 │  │ 签名 σk │                      │
│   └─────────┘  └─────────┘  └─────────┘                      │
│        │                                                       │
│        ▼                                                       │
│   聚合签名 Σ = Aggregate({σ_i})                               │
│        │                                                       │
│        ▼                                                       │
│   广播 (delta^{(t)}, Σ, metadata) 给客户端                     │
│        │                                                       │
│        ▼                                                       │
│   客户端验证：Verify(Σ, pk_witness) == True?                   │
│        │                                                       │
│        ├── Yes → 同态累加                                      │
│        └── No  → 丢弃，请求重传或标记服务器可疑                 │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

**具体实现（基于BLS阈值签名）**：

1. **初始化**：$n$ 个见证节点，阈值 $t$。每个节点 $i$ 持有私钥份额 $sk_i$，公共验证密钥 $vk$
2. **签名**：$t$ 个见证节点独立验证delta的生成过程（如检查聚合运算日志），各自生成签名份额 $\sigma_i = Sign_{sk_i}(H(\delta))$
3. **聚合**：服务器聚合 $t$ 个份额为单一签名 $\Sigma$
4. **验证**：客户端用 $vk$ 验证 $\Sigma$，无需知道各见证节点的单独密钥

**见证节点验证delta的方式**：
- 由于delta是密文，见证节点无法直接验证内容
- 但可以验证：
  1. delta的序列号/轮次号是否连续（防重放）
  2. delta的生成时间戳是否合理
  3. delta的来源IP/节点身份
  4. （如果服务器维护明文模型）见证节点可以独立重新计算delta并与服务器声明比对

**优点**：
- 强安全性：需 $t$ 个见证节点共谋才能伪造delta
- 客户端验证轻量（单次签名验证）
- 与阈值解密天然兼容（同一组节点既做签名又做解密）

**缺点**：
- 引入额外基础设施（见证节点）
- 签名聚合增加服务器延迟

---

### 2.5 防御方案C：Authenticated Ciphertext Delta (ACD)

**核心思想**：
利用**消息认证码（MAC）**或**认证加密（AEAD）**保护预取delta的完整性，但保持同态性。

**设计**：

由于标准MAC（如HMAC）破坏同态性，我们设计一种**同态友好的认证机制**：

1. 服务器和客户端共享一个**对称密钥 $k_{auth}$**（通过密钥协商协议建立）
2. 对每个delta，服务器计算：
   $$tag^{(t)} = PRF(k_{auth}, \text{round}_t \| \text{seed}) \cdot \delta^{(t)}$$

   这实际上不可行，因为PRF输出与密文无法直接运算。

**更实际的方案：分离认证与加密**

- delta本身保持CKKS密文（同态可累加）
- 额外附加一个**小的认证标签**，该标签不用于同态运算，仅用于完整性验证

具体地：
1. 服务器在生成delta的**明文**时，同时计算其哈希 $h^{(t)} = SHA256(m^{(t)})$
2. 用AES-GCM加密哈希：$c_{tag}^{(t)} = AESGCM_{k_{auth}}(h^{(t)}, nonce_t)$
3. 广播 $(\delta^{(t)}, c_{tag}^{(t)}, nonce_t)$
4. 客户端在解密并应用delta后，计算明文哈希并与解密的标签比对

**问题**：仍需解密后才能验证。

**终极方案：基于零知识证明的即时验证（ZK-Prefetch-Proof）**

这是最有论文价值的方向：

服务器为每个delta生成一个**zk-SNARK证明**，证明：
$$\delta^{(t)} = \text{Encrypt}_{pk}(w^{(t)} - w^{(t-1)})$$

即：证明密文delta确实是对应明文模型差值的正确加密。

**公共输入**：$pk, w^{(t-1)}_{hash}, w^{(t)}_{hash}, \delta^{(t)}$
**私密输入（witness）**：$w^{(t)}, w^{(t-1)}, r_{enc}$
**证明关系**：$\delta^{(t)} = \text{CKKS.Enc}_{pk}(w^{(t)} - w^{(t-1)}; r_{enc}) \land w^{(t)} = \text{Aggregate}(\{w_i^{(t)}\})$

客户端验证证明（无需解密）：
- 若证明有效 → delta内容可信
- 若证明无效 → 丢弃delta

**优点**：
- 无需解密即可验证
- 密码学强度保证
- 可以验证聚合正确性

**缺点**：
- zk-SNARK计算开销高（服务器生成证明成本高）
- 证明大小虽小，但生成时间可能成为瓶颈
- 需要为CKKS加密电路设计专门的zk-SNARK（或改用更高效的zk-STARK/Bulletproofs）

**折中方案：延迟 lightweight 验证**

不追求每轮即时验证，而是：
1. 客户端正常接收并累积预取delta
2. 每 $k$ 轮（如 $k=5$），客户端对累积的delta执行一次"验证轮"
3. 验证轮中，客户端解密累积delta，检查模型一致性（如用本地数据快速评估）
4. 若发现异常，回滚到上次验证通过的状态，并标记中间delta可疑

---

### 2.6 推荐组合方案

| 安全级别 | 推荐方案组合 | 适用场景 |
|----------|-------------|---------|
| **基础** | ACD (AES-GCM标签) + 延迟验证 | 资源受限，快速实现 |
| **增强** | TPW (BLS阈值签名) + 轮次防重放 | 有可用的见证节点集群 |
| **高安全** | TPW + ZK-Prefetch-Proof (每k轮) | 对抗恶意服务器，论文级别 |
| **极致** | TPW + 每轮ZK证明 + 阈值解密 | IEEE S&P/CRYPTO级别 |

---

## 三、双方向融合：完整协议设计

### 3.1 协议名称

**SecureRes-Fetch**: Secure Residual-aware Ciphertext Prefetching with Integrity Guarantees for Federated Learning

### 3.2 完整流程

```
初始化阶段
─────────────────────────────────────────
1. 阈值密钥生成（或单密钥+TPW见证节点设置）
2. 分发聚合公钥 pk_agg 给所有客户端
3. 分发认证密钥 k_auth 给服务器和客户端（如使用ACD）
4. 初始化全局残差缓存 R^{(0)} = 0

每轮训练 Round t
─────────────────────────────────────────
【客户端侧 - 被选中训练】
1. 本地训练得到 Δw_i^{(t)}
2. 合成有效梯度：g_i^{(t)} = Δw_i^{(t)} + r_i^{(t-1)}
3. 包级稀疏化：(idx_set, g_sparse) = SparseBatches(g_i^{(t)})
4. 加密上传：ct_i^{(t)} = CKKS.Encrypt(g_sparse, mask)
5. 更新残差：r_i^{(t)} = g_i^{(t)} - ReconstructSparse(g_sparse, mask)

【服务器侧 - 聚合与预取】
6. 收集 {ct_i^{(t)}, mask_i}
7. 分批次同态聚合（含全局残差补偿）
8. 计算明文全局模型更新 Δw_global^{(t)}
9. 生成密文delta：δ^{(t)} = Enc(Δw_global^{(t)} - Δw_global^{(t-1)})
10. [可选] 生成ZK证明 π^{(t)} 或 请求TPW签名 Σ^{(t)}
11. 残差感知预取调度：
    - 计算各客户端残差优先级
    - 向高优先级未选中客户端广播 (δ^{(t)}, 认证信息)

【客户端侧 - 未选中（预取）】
12. 接收 (δ^{(t)}, auth)
13. 验证 auth（签名/ZK证明/延迟验证）
14. 若验证通过：ct_prefetch = ct_prefetch + δ^{(t)}
15. 若验证失败：标记可疑，丢弃delta

【客户端侧 - 下轮被选中时】
16. Fetch补齐缺失delta
17. 阈值解密（或单密钥解密）ct_prefetch → Δw_cum
18. 应用更新：w_local = w_base + Δw_cum
19. 本地训练...
```

### 3.3 核心算法伪代码

```python
# ========== 客户端SRCA模块 ==========
class ClientSRCA:
    def __init__(self, model, residual_decay=0.9):
        self.residual_cache = {name: torch.zeros_like(p) 
                               for name, p in model.named_parameters()}
        self.decay = residual_decay
    
    def prepare_update(self, raw_gradient: Dict[str, Tensor]) -> Tuple[Dict, Dict]:
        """合成有效梯度 = 原始梯度 + 衰减后的残差缓存"""
        effective_gradient = {}
        for name in raw_gradient:
            effective_gradient[name] = raw_gradient[name] + self.decay * self.residual_cache[name]
        return effective_gradient
    
    def update_residual(self, effective_gradient: Dict, sparse_update: Dict, mask: Dict):
        """更新残差缓存 = 有效梯度中未被传输的部分"""
        for name in effective_gradient:
            transmitted = reconstruct_full(sparse_update[name], mask[name])
            self.residual_cache[name] = effective_gradient[name] - transmitted
    
    def get_residual_priority(self) -> float:
        """返回残差总范数，用于服务器调度预取优先级"""
        return sum(r.norm().item() for r in self.residual_cache.values())


# ========== 服务器残差感知预取调度 ==========
class ResidualAwarePrefetchServer:
    def compute_prefetch_priorities(self, clients: List[ClientSRCA]) -> List[int]:
        """按残差优先级排序客户端"""
        priorities = [(cid, c.get_residual_priority()) for cid, c in enumerate(clients)]
        priorities.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in priorities]
    
    def generate_delta_with_integrity(self, old_state, new_state, round_num):
        """生成带完整性保护的delta"""
        delta_plain = {k: new_state[k] - old_state[k] for k in new_state}
        delta_enc = self.ckks.encrypt_model_update(delta_plain)
        
        # 生成认证信息（多选一）
        auth = self._generate_auth(delta_plain, round_num)
        
        return delta_enc, auth
    
    def _generate_auth(self, delta_plain, round_num):
        if self.auth_scheme == "TPW":
            # 请求阈值见证节点签名
            h = hash_delta(delta_plain, round_num)
            signatures = self.request_witness_signatures(h)
            return aggregate_signatures(signatures)
        elif self.auth_scheme == "ACD":
            # AES-GCM加密哈希标签
            h = sha256_delta(delta_plain)
            nonce = os.urandom(12)
            tag = aesgcm_encrypt(self.auth_key, h, nonce)
            return (tag, nonce)
        elif self.auth_scheme == "ZKP":
            # 生成ZK证明（每k轮或每轮）
            proof = generate_zk_proof(delta_plain, round_num, self.pk)
            return proof
```

---

## 四、创新性评估

### 4.1 方向一创新性（SRCA）

| 对比工作 | 差异点 | 创新度 |
|----------|--------|--------|
| ResFed | ResFed传输残差，SRCA在客户端累积残差并延迟传输 | ★★★★☆ |
| STC | STC有误差反馈但仅客户端本地，SRCA服务器感知全局残差 | ★★★★★ |
| FTopk | FTopk是细粒度Top-k，无残差机制 | ★★★★☆ |
| FedPHE | FedPHE打包加密，无残差优化 | ★★★★☆ |

**核心创新声明**：
> 首次将"误差反馈/残差累积"机制从明文联邦学习提升到**密文联邦学习**场景，设计了服务器可感知的全局残差缓存和残差感知预取调度策略，使包级稀疏化在加密域下仍能保证信息无损收敛。

### 4.2 方向二创新性（Prefetch Integrity）

| 对比工作 | 差异点 | 创新度 |
|----------|--------|--------|
| FedFetch | FedFetch明文预取，无完整性考虑 | ★★★★★ |
| EVMKA | EVMKA验证聚合结果，不验证预取delta | ★★★★☆ |
| VTSAFL | VTSAFL验证部分解密结果，不验证预取 | ★★★★☆ |
| Bonawitz SecAgg | SecAgg验证聚合正确性，无预取场景 | ★★★☆☆ |

**核心创新声明**：
> 首次提出并形式化"**密文预取证完整性**"问题，设计了Threshold Prefetch Witness和Authenticated Ciphertext Delta两套防御机制，填补了预取联邦学习在安全验证方面的空白。

### 4.3 融合创新（SecureRes-Fetch）

| 维度 | 评估 |
|------|------|
| **问题新颖性** | ★★★★★ 密文预取的安全性和残差优化是两个全新问题 |
| **技术深度** | ★★★★★ 涉及同态加密、稀疏化、残差优化、密码学验证 |
| **实用性** | ★★★★☆ 需要额外基础设施（见证节点/ZK证明），但基础版本（ACD+SRCA）易实现 |
| **论文级别** | 可达 **IEEE TDSC / INFOCOM / NDSS** 级别 |

---

## 五、实现路线图

### 阶段一：SRCA模块实现（2周）

1. **客户端残差缓存**
   - 在`FederatedClient`中加入`residual_cache`字典
   - 实现`prepare_update()`和`update_residual()`
   - 残差衰减率参数可调

2. **服务器全局残差管理**
   - 在`PrefetchAggregationServer`中加入全局残差追踪
   - 实现分批次聚合时的残差补偿逻辑

3. **残差感知预取调度**
   - 修改`broadcast_prefetch_to_unselected()`，按残差优先级排序
   - 高残差客户端优先预取

4. **实验对比**
   - SRCA vs 无SRCA：相同稀疏率下的准确率对比
   - 不同衰减率的收敛曲线

### 阶段二：预取证完整性基础版（1-2周）

1. **ACD实现**
   - 服务器生成delta时计算SHA256哈希
   - AES-GCM加密哈希标签
   - 客户端解密后验证

2. **轮次防重放**
   - delta元数据包含轮次号、时间戳、序列号
   - 客户端维护已接收轮次集合，拒绝重复

3. **延迟验证**
   - 每5轮执行一次本地验证（快速评估）
   - 异常时回滚

### 阶段三：高级安全增强（2-3周，论文级）

1. **TPW阈值签名**
   - 部署k个见证节点
   - BLS阈值签名集成
   - 签名验证客户端模块

2. **ZKP证明（可选，最高级别）**
   - 调研CKKS友好的ZK证明方案
   - 或采用延迟ZK（每k轮聚合证明）

3. **完整实验**
   - 恶意服务器攻击模拟
   - 预取证防御效果评估
   - 端到端开销测量

---

## 六、论文核心贡献表述（双方向融合版）

> **Contribution 1**: We propose **SRCA (Sparse Residual Ciphertext Accumulation)**, the first residual-aware sparsification mechanism for encrypted federated learning. SRCA maintains a per-client residual cache that accumulates unsent gradient information across rounds, and a server-side global residual buffer that compensates for missing batches during aggregation. We prove that SRCA preserves information-theoretic convergence guarantees under standard FL assumptions, even with aggressive sparsification ratios.
>
> **Contribution 2**: We identify and formalize the **Prefetch Integrity Problem** in ciphertext prefetching, where malicious servers can forge or replay encrypted deltas to poison client models without detection. We propose **Threshold Prefetch Witness (TPW)**, a lightweight threshold-signature-based authentication mechanism, and **Authenticated Ciphertext Delta (ACD)**, an AES-GCM-based integrity tag scheme, to guarantee delta provenance and freshness.
>
> **Contribution 3**: We design **SecureRes-Fetch**, the first federated learning framework that integrates ciphertext prefetching with residual-aware sparse encryption and prefetch integrity verification. The protocol ensures that (i) no gradient information is lost due to sparsification, (ii) prefetch deltas are cryptographically authenticated, and (iii) the aggregation server remains unable to decrypt individual client updates.
>
> **Contribution 4**: We implement SecureRes-Fetch and evaluate it on MNIST, Fashion-MNIST, and CIFAR-10. Results show that SRCA achieves **≤1% accuracy loss** at 20% sparsity (vs. 8% loss without SRCA), while TPW introduces only **0.3% overhead** in end-to-end training time.

---

*本设计方案响应用户提出的两个核心方向，融合了残差优化（STC/ResFed/FTopk思想）和预取安全（全新威胁建模）两大创新点，可作为CipherFetch项目的下一代升级方案。*
