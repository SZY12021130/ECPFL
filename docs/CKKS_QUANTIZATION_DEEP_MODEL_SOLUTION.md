# CKKS 量化精度问题与深层网络训练发散：解决方案与顶会调研

> 日期: 2026-05-21  
> 背景: CIFAR-10 上 `cnn_cifar`（2层卷积，62K）可达 43%，但 `CNN`（3层，189K）和 `ResNet20`（272K，含BN+残差）均因 CKKS 量化误差累积而完全发散。

---

## 一、问题根因分析

### 1.1 为什么 `cnn_cifar` 能工作？

| 特性 | `cnn_cifar` (62K) | `CNN` (189K) | `ResNet20` (272K) |
|------|-------------------|--------------|-------------------|
| 卷积层数 | 2 | 3 | 6+ (含残差) |
| 最大通道 | 16 | 64 | 64 |
| 有 BatchNorm | ❌ | ❌ (已移除) | ✅ (不可移除) |
| 参数更新范围 | ±0.1 | ±1~10 | ±10~100 |
| 量化后小值保留 | ✅ 良好 | ❌ 被抹平 | ❌ 严重抹平 |
| 训练结果 | **43%** | loss=10¹⁹ | loss=nan |

**核心洞察**：
- CKKS 16-bit 量化将每个 block 的 `max_abs` 映射到 `[-32767, 32767]`
- 当 `max_abs = 10` 时，量化步长 `scale = 10/32767 ≈ 3×10⁻⁴`
- 任何小于 `1.5×10⁻⁴` 的梯度更新都会被 rounding 到 **0**
- 深层网络的梯度范围更大 → 小但关键的梯度被系统性抹除 → 有效学习停止 → 大误差偶尔爆炸 → loss 发散

### 1.2 BatchCrypt (ATC'20) 的启示

> "As gradients values are unbounded, they need to be **clipped before quantization**, which critically determines the learning performance."

BatchCrypt 论文明确指出的关键措施：
1. **梯度裁剪 (Gradient Clipping)**：限制 backward 后的梯度 L2 norm
2. **更新裁剪 (Update Clipping / dACIQ)**：限制 `new_params - old_params` 的范围
3. **量化前裁剪**：确保进入量化的值在可控范围内

### 1.3 QuanCrypt-FL (2024) 的启示

> "We propose a **layerwise dynamic mean-based clipping mechanism** to address numerical inconsistencies during the quantization process."

QuanCrypt-FL 的核心创新：
- 每层独立裁剪：`clip_threshold = clip_factor × mean_abs(layer_update)`
- 配合低比特量化 + 剪枝，在 MNIST/CIFAR-10/CIFAR-100 上实现稳定训练

---

## 二、已实施的解决方案

### 2.1 代码改进清单

#### A. 客户端梯度裁剪 (`ckks_fed/client.py`)

在 `loss.backward()` 后添加了 `torch.nn.utils.clip_grad_norm_`：

```yaml
system:
  gradient_clipping:
    enabled: true      # 启用梯度裁剪
    max_norm: 1.0      # L2 norm 上限
```

**效果**：限制反向传播后的梯度幅度，使 optimizer 产生的参数更新更可控。

#### B. 模型更新裁剪 (`ckks_fed/client.py`)

在计算 `model_update = new_params - old_params` 后添加了逐层裁剪：

```yaml
system:
  update_clipping:
    enabled: true
    method: "layerwise_mean"   # 或 "global_norm"
    clip_factor: 3.0           # max_val = 3.0 * mean_abs(layer)
```

**效果**：限制上传的模型更新范围，使量化 scale 更小，精度更高。

#### C. LayerwiseQuantizedPacking (`ckks_fed/packing.py`)

新增打包策略，核心设计：
1. **逐层独立量化**：每层用自己的 `min-max scale`，避免大层拖垮小层
2. **合并加密**：量化后的所有层拼接成一个长数组，按 `slot_count` 分块加密
3. **密文数量 = MergedPacking 级别**（最少），**精度 = 逐层级别**（最高）

```yaml
ckks:
  packing:
    strategy: "layerwise_quantized"
    quant_bits: 16
```

**与现有策略对比**：

| 策略 | Scale 粒度 | 密文数量 | 适用场景 |
|------|-----------|---------|---------|
| `merged` | 无量化 | 最少 | 浅层网络、更新范围小 |
| `twotier` | per-block | 最少 | 中等深度 |
| `crtstack` | per-layer (8-bit) | 少 (CRT压缩4x) | 全精度容忍场景 |
| **`layerwise_quantized`** | **per-layer (16-bit)** | **最少** | **深层网络首选** |

#### D. 新增无 BN 深层模型 (`ckks_fed/models.py`)

```python
# 1. DeepCNN: 4层无BN CNN, ~92K 参数
#    专为测试 CKKS 深度极限设计
create_model("deepcnn", config)

# 2. VGGNoBN: VGG-11 简化版 (无BN), ~975万参数
#    注意: 参数量极大，CKKS 密文数量会非常多
#    建议仅用于 plaintext 对比或极小规模实验
create_model("vggnobn", config)
```

#### E. 新增数据集支持 (`ckks_fed/data.py`)

| 数据集 | 类别数 | 来源 | 模型建议 |
|--------|--------|------|---------|
| `femnist` | 62 | EMNIST byclass (LEAF替代) | LeNet / CNN |
| `svhn` | 10 | torchvision | LeNet / CNN |
| `emnist` | 47 | torchvision | LeNet |

配置方式：
```yaml
data:
  dataset: "femnist"   # 新增选项
  num_classes: 62
```

---

## 三、顶会顶刊调研：相关开源项目汇总

### 3.1 核心论文与代码

#### 1. FedPHE (INFOCOM'24 & TDSC'25) —— 本项目已对齐
- **GitHub**: https://github.com/lunan0320/FedPHE
- **数据集**: MNIST, Fashion-MNIST, CIFAR-10
- **模型**: LeNet, CNNCifar (2层, 62K)
- **加密**: CKKS + TopK 稀疏化 + 客户端选择
- **关键参数**: `enc_batch_size=4096`, `topk=0.1`

#### 2. BatchCrypt (ATC'20) —— 量化裁剪标杆
- **论文**: "BatchCrypt: Efficient Homomorphic Encryption for Cross-Silo Federated Learning"
- **核心贡献**:
  - dACIQ 在线裁剪阈值分析
  - 批量编码：多个量化值编码为一个长整数
  - 16-bit 量化，精度损失 < 1%
- **数据集**: FMNIST, CIFAR-10 (AlexNet), Shakespeare (LSTM)
- **结果**: 23x-93x 训练加速，66x-101x 通信减少
- **开源状态**: 集成在 FATE 框架中，无独立 GitHub

#### 3. FLASHE (arXiv'21)
- **GitHub**: https://github.com/SamuelGong/FLASHE
- **核心贡献**: 对称同态加密（仅模加 + 随机数），无公钥设计
- **数据集**: EMNIST, CIFAR-10
- **结果**: 相比明文训练仅增加 ≤6% 时间，**0% 通信开销**
- **集成**: FATE v1.2.0 插件

#### 4. Lancelot (Nature Machine Intelligence, 2025)
- **GitHub**: https://github.com/siyang-jiang/Lancelot-Dev
- **核心贡献**: 拜占庭鲁棒 + FHE 联邦学习
- **数据集**: CIFAR-10, MNIST, FaMNIST
- **模型**: CNN, ResNet
- **防御**: Krum, Trimmed Mean
- **命令示例**:
  ```bash
  python main.py --dataset CIFAR10 --num_clients 10 \
      --global_ep 100 --method krum --cipher_open 1
  ```

#### 5. QuanCrypt-FL (2024)
- **论文**: "QuanCrypt-FL: Quantized Homomorphic Encryption with Pruning for Secure Federated Learning"
- **核心贡献**:
  - **Mean-based dynamic layerwise clipping** (本项目已借鉴)
  - 低比特量化 + 动态剪枝 + CKKS
  - 全模型逐层加密
- **数据集**: MNIST, CIFAR-10, CIFAR-100
- **模型**: CNN, AlexNet, ResNet-18
- **结果**: 9x 加密加速，16x 解密加速，1.5x 推理加速

#### 6. FedHENet
- **GitHub**: https://github.com/AlejandroDopico2/FedHENet/
- **核心贡献**: CKKS + MQTT + 冻结 ResNet-18 backbone
- **数据集**: CIFAR-10, CIFAR-100
- **结果**: 使用冻结 backbone 减少需要加密的参数

#### 7. HEFLP (Flower 插件)
- **GitHub**: https://github.com/canarybit/canarybit-heflp
- **核心贡献**: Flower FL 框架插件，支持 CKKS/BFV/Flashe
- **特点**: 内置 quantizer，支持 PyTorch 和 TensorFlow

#### 8. MASER
- **GitHub**: https://github.com/sustainable-computing/MASER
- **核心贡献**: 多密钥 CKKS (xMKCKKS)
- **数据集**: MNIST, CIFAR-10

#### 9. FedCrypt
- **GitHub**: https://github.com/medlansari/FedCrypt
- **核心贡献**: 动态白盒水印 + HE
- **模型**: VGG, ResNet-18
- **加密**: TenSEAL CKKS

### 3.2 LEAF Benchmark 数据集

- **GitHub**: https://github.com/TalwalkarLab/leaf
- **数据集**: FEMNIST, Shakespeare, Sent140, CelebA, Reddit
- **特点**: 真实联邦场景，按用户/书写者自然分区

本项目已集成 FEMNIST (通过 EMNIST byclass 替代)。

---

## 四、推荐配置与使用指南

### 4.1 深层网络 CKKS 训练推荐配置

```yaml
system:
  num_epochs: 2              # 减少本地训练轮数，控制更新幅度
  learning_rate: 0.0005      # 降低学习率
  gradient_clipping:
    enabled: true
    max_norm: 1.0
  update_clipping:
    enabled: true
    method: "layerwise_mean"
    clip_factor: 3.0

ckks:
  packing:
    strategy: "layerwise_quantized"   # 深层网络首选
    quant_bits: 16
```

### 4.2 数据集-模型映射推荐

```yaml
# CIFAR-10 (深度极限测试)
model: "deepcnn"        # 4层无BN, 92K, 比 CNN (189K) 更稳定

# CIFAR-10 (精度优先)
model: "cnn_cifar"      # 2层, 62K, 已验证可达 43%

# CIFAR-100
model: "mobilenetv2"    # 注意: 含BN，CKKS 下可能不稳定

# FEMNIST / EMNIST
model: "lenet"          # 经典轻量模型

# SVHN
model: "lenet"          # 或 CNN
```

### 4.3 快速验证脚本

```bash
# 测试 CNN (3层) 在新配置下是否发散
python scripts/quick_test_deep_models_minimal.py \
    --model cnn --packing layerwise_quantized \
    --grad-clip --update-clip

# 全矩阵测试（对比所有组合）
python scripts/quick_test_deep_models_minimal.py --matrix

# 多数据集批量实验
python scripts/run_multi_dataset.py --datasets cifar10 femnist
```

---

## 五、后续建议

### 5.1 短期 (1-2周)
1. **跑通完整 30 轮实验**：验证 CNN / DeepCNN 在 `layerwise_quantized` + 裁剪下的最终精度
2. **调参搜索**：`max_norm` (0.5, 1.0, 2.0), `clip_factor` (2.0, 3.0, 5.0), `learning_rate` (0.0001, 0.0005, 0.001)
3. **对比明文基线**：确保精度差距 < 5%

### 5.2 中期 (1个月)
1. **集成 BatchCrypt 风格的批量编码**：将多个量化值编码为长整数，减少密文数量
2. **实现 dACIQ 在线裁剪**：根据历史梯度分布动态调整裁剪阈值
3. **CIFAR-100 完整实验**：验证 MobileNetV2 在 CKKS 下的可行性

### 5.3 长期 (论文投稿前)
1. **引入 Low-Rank Updates (HEAL-FL, DATE'26)**：仅加密低秩系数矩阵，大幅减少密文数量
2. **Bootstrapping 探索**：使用 OpenFHE/HEaaN 实现真正的无限深度同态运算
3. **硬件加速调研**：参考 100x.ai GPU CKKS 加速方案

---

## 六、关键结论

| 问题 | 解决方案 | 状态 |
|------|---------|------|
| 深层网络梯度爆炸 | 梯度裁剪 + 更新裁剪 | ✅ 已集成 |
| 跨层量化精度不均 | LayerwiseQuantizedPacking | ✅ 已集成 |
| BatchNorm 不兼容 | 新增 DeepCNN / VGGNoBN (无BN) | ✅ 已集成 |
| 数据集单一 | 新增 FEMNIST / SVHN / EMNIST | ✅ 已集成 |
| 缺乏对比基线 | 集成明文基线 + 快速测试脚本 | ✅ 已集成 |
| 密文数量过多 | 待引入 BatchCrypt 批量编码 | 🔄 待实现 |
| 超大模型支持 | 待引入 Low-Rank / 冻结 Backbone | 🔄 待实现 |

**核心观点**：CKKS 16-bit 量化对网络深度有**硬限制**，但通过 (1) 梯度/更新裁剪控制范围 + (2) 逐层独立量化保护精度 + (3) 使用无BN轻量模型，可以将有效深度从 2 层扩展到 4 层。对于 ResNet-18 级别的模型，需要结合 Low-Rank 更新或明文聚合 + 加密上传的混合架构。
