# 模型参数与 CKKS 密文大小对照表

**CKKS 配置**: `N=8192`, `slot_count=4096`, `coeff_mod=[60,40,40,60]`

**说明**: 每个 batch = 4096 个参数 = 1 个 CKKS 密文向量。密文大小按 ResNet20 实测数据估算（1 batch ≈ 290 KB）。

## 汇总表

| 模型名称 | 适用数据集 | 输入尺寸 | 类别数 | 总参数 | 明文大小 (MB) | Batch 数 | 每 Batch 密文 (KB) | 总密文大小 (MB) | 膨胀率 |
|---------|-----------|---------|-------|--------|--------------|---------|-------------------|----------------|--------|
| mlp | MNIST | 1x28x28 | 10 | 235,146 | 0.90 | 58 | 297.3 | 16.84 | 18.8x |
| cnn | MNIST | 1x28x28 | 10 | 130,890 | 0.50 | 32 | 297.3 | 9.29 | 18.6x |
| cnn | CIFAR-10 | 3x32x32 | 10 | 130,890 | 0.50 | 32 | 297.3 | 9.29 | 18.6x |
| lenet | MNIST | 1x28x28 | 10 | 44,426 | 0.17 | 11 | 297.3 | 3.19 | 18.8x |
| lenet | CIFAR-10 | 3x32x32 | 10 | 44,426 | 0.17 | 11 | 297.3 | 3.19 | 18.8x |
| deepcnn | MNIST | 1x28x28 | 10 | 79,722 | 0.30 | 20 | 297.3 | 5.81 | 19.1x |
| deepcnn | CIFAR-10 | 3x32x32 | 10 | 79,722 | 0.30 | 20 | 297.3 | 5.81 | 19.1x |
| vggnobn | MNIST | 1x28x28 | 10 | 9,749,770 | 37.19 | 2381 | 297.3 | 691.20 | 18.6x |
| vggnobn | CIFAR-10 | 3x32x32 | 10 | 9,749,770 | 37.19 | 2381 | 297.3 | 691.20 | 18.6x |
| mobilenetv2 | CIFAR-10 | 3x32x32 | 10 | 2,236,106 | 8.53 | 546 | 297.3 | 158.50 | 18.6x |
| densenet | CIFAR-10 | 3x32x32 | 10 | 175,738 | 0.67 | 43 | 297.3 | 12.48 | 18.6x |
| resnet18 | CIFAR-10 | 3x32x32 | 10 | 11,172,810 | 42.62 | 2728 | 297.3 | 791.93 | 18.6x |
| cnn_cifar | CIFAR-10 | 3x32x32 | 10 | 61,706 | 0.24 | 16 | 297.3 | 4.64 | 19.7x |
| cnn_fmnist | Fashion-MNIST | 1x28x28 | 10 | 39,786 | 0.15 | 10 | 297.3 | 2.90 | 19.1x |
| resnet20 | CIFAR-10 | 3x32x32 | 10 | 272,186 | 1.04 | 67 | 297.3 | 19.45 | 18.7x |
| resnet32 | CIFAR-10 | 3x32x32 | 10 | 466,618 | 1.78 | 114 | 297.3 | 33.09 | 18.6x |
| **mnist2nn** | **MNIST** | **1x28x28** | **10** | **159,010** | **0.61** | **39** | **297.3** | **11.32** | **18.6x** |
| **alexnet_cifar** | **CIFAR-10** | **3x32x32** | **10** | **23,272,266** | **88.78** | **5683** | **297.3** | **1647.60** | **18.6x** |
| **alexnet_mnist** | **MNIST** | **1x28x28** | **10** | **11,696,202** | **44.62** | **2857** | **297.3** | **828.55** | **18.6x** |
| **cryptonet** | **MNIST** | **1x28x28** | **10** | **99,270** | **0.38** | **25** | **297.3** | **7.25** | **19.1x** |
| **lstm** | **Shakespeare** | **seq_len=80** | **80** | **819,920** | **3.13** | **201** | **297.3** | **58.22** | **18.6x** |
| **shufflenet** | **CIFAR-10** | **3x32x32** | **10** | **914,338** | **3.49** | **224** | **297.3** | **64.90** | **18.6x** |

## 详细说明

### Batch 计算公式
```
batch_num = ceil(total_params / slot_count)
batch_num = ceil(total_params / 4096)
```

### 密文大小计算公式
```
cipher_size_MB = batch_num × 290 KB / 1024
```
其中 **290 KB/batch** 是根据 ResNet20 (67 batches = 19.45 MB) 实测数据估算。
在 CKKS 中，每个 batch 对应 1 个密文向量，密文大小只与多项式次数 N 和模数链长度有关，与打包的参数数量无关。因此所有模型的「每 Batch 密文大小」基本相同（≈ 290 KB）。


## 不同稀疏率对应的客户端选择 Batch 数量

**说明**: 在 TopK 稀疏化策略下，客户端根据 `sparsity_rate` 选择最重要的 batch 上传。
`selected_batches = max(1, ceil(total_batches × sparsity_rate))`，即至少保留 1 个 batch。

| 模型 | 数据集 | 总 Batch 数 | 10% | 20% | 30% | 40% | 50% | 60% | 70% | 80% | 90% | 100% |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mlp | MNIST | 58 | 6 | 12 | 18 | 24 | 29 | 35 | 41 | 47 | 53 | 58 |
| cnn | MNIST | 32 | 4 | 7 | 10 | 13 | 16 | 20 | 23 | 26 | 29 | 32 |
| cnn | CIFAR-10 | 32 | 4 | 7 | 10 | 13 | 16 | 20 | 23 | 26 | 29 | 32 |
| lenet | MNIST | 11 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| lenet | CIFAR-10 | 11 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| deepcnn | MNIST | 20 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 |
| deepcnn | CIFAR-10 | 20 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 |
| vggnobn | MNIST | 2381 | 239 | 477 | 715 | 953 | 1191 | 1429 | 1667 | 1905 | 2143 | 2381 |
| vggnobn | CIFAR-10 | 2381 | 239 | 477 | 715 | 953 | 1191 | 1429 | 1667 | 1905 | 2143 | 2381 |
| mobilenetv2 | CIFAR-10 | 546 | 55 | 110 | 164 | 219 | 273 | 328 | 383 | 437 | 492 | 546 |
| densenet | CIFAR-10 | 43 | 5 | 9 | 13 | 18 | 22 | 26 | 31 | 35 | 39 | 43 |
| resnet18 | CIFAR-10 | 2728 | 273 | 546 | 819 | 1092 | 1364 | 1637 | 1910 | 2183 | 2456 | 2728 |
| cnn_cifar | CIFAR-10 | 16 | 2 | 4 | 5 | 7 | 8 | 10 | 12 | 13 | 15 | 16 |
| cnn_fmnist | Fashion-MNIST | 10 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| resnet20 | CIFAR-10 | 67 | 7 | 14 | 21 | 27 | 34 | 41 | 47 | 54 | 61 | 67 |
| resnet32 | CIFAR-10 | 114 | 12 | 23 | 35 | 46 | 57 | 69 | 80 | 92 | 103 | 114 |
| shufflenet | CIFAR-10 | 224 | 23 | 45 | 68 | 90 | 112 | 135 | 157 | 180 | 202 | 224 |

### 稀疏率与通信开销关系（以 ResNet20 为例）

| 稀疏率 | 选择 Batch 数 | 每客户端密文大小 | 相对全量比例 |
|-------|-------------|----------------|------------|
| 10% | 7 | 2.03 MB | 10.4% |
| 20% | 14 | 4.06 MB | 20.9% |
| 30% | 21 | 6.10 MB | 31.3% |
| 40% | 27 | 7.84 MB | 40.3% |
| 50% | 34 | 9.87 MB | 50.7% |
| 60% | 41 | 11.90 MB | 61.2% |
| 70% | 47 | 13.64 MB | 70.1% |
| 80% | 54 | 15.68 MB | 80.6% |
| 90% | 61 | 17.71 MB | 91.0% |
| 100% | 67 | 19.45 MB | 100.0% |

> 注：稀疏率越高（越接近 100%），上传的 batch 越多，通信开销越大。当稀疏率=100% 时等同于全量上传。

---

## 外部项目对齐模型详情

以下模型从其他开源联邦学习/同态加密项目中移植，用于跨项目公平对比实验。

### mnist2nn (来源: FedDMC-main / fedavgpy-master)

- **结构**: Flatten -> Linear(784, 200) -> ReLU -> Linear(200, num_classes)
- **特点**: 极简2层全连接，MNIST经典基线，无卷积层
- **参数量**: 159,010 (MNIST, 10 classes)
- **适用数据集**: MNIST, Fashion-MNIST, EMNIST
- **Batch数**: 39 batches (MNIST)
- **通信量**: 11.32 MB (全量密文)
- **使用场景**: 作为非CNN架构的对比基线；验证HE在纯全连接网络上的效率

### alexnet_cifar (来源: FedSHE)

- **结构**: Conv(3->64, 3x3, s2) -> MaxPool -> Conv(64->192, 3x3) -> MaxPool -> Conv(192->384, 3x3) -> Conv(384->256, 3x3) -> Conv(256->256, 3x3) -> MaxPool -> FC(256*2*2 -> 4096) -> ReLU -> Dropout -> FC(4096 -> 4096) -> ReLU -> Dropout -> FC(4096 -> num_classes)
- **特点**: ImageNet AlexNet的CIFAR适配版，缩小了卷积核和FC层以适应32x32输入
- **参数量**: 23,272,266 (CIFAR-10, 10 classes)
- **适用数据集**: CIFAR-10, CIFAR-100
- **Batch数**: 5683 batches (CIFAR-10)
- **通信量**: 1647.60 MB (全量密文)
- **⚠️ 注意**: 参数量极大，必须配合稀疏化或压缩策略使用
- **使用场景**: 中等深度CNN对比基线；测试HE在多层卷积+大FC网络上的精度损失

### alexnet_mnist (来源: FedSHE)

- **结构**: Conv(1->32, 5x5) -> Conv(32->64, 3x3) -> MaxPool -> Conv(64->96, 3x3) -> Conv(96->64, 3x3) -> Conv(64->32, 3x3) -> MaxPool -> FC(32*12*12 -> 2048) -> ReLU -> Dropout -> FC(2048 -> 1024) -> ReLU -> FC(1024 -> num_classes)
- **特点**: 专为28x28灰度图设计的AlexNet变体，通道数逐级递减
- **参数量**: 11,696,202 (MNIST, 10 classes)
- **适用数据集**: MNIST, Fashion-MNIST
- **Batch数**: 2857 batches (MNIST)
- **通信量**: 828.55 MB (全量密文)
- **⚠️ 注意**: 参数量极大，必须配合稀疏化或压缩策略使用
- **使用场景**: MNIST上的深度CNN对比；验证大容量模型在小图像上的过拟合/泛化

### cryptonet (来源: ckks_cryptonet)

- **结构**: Conv2D(5, 3x3, s2, padding=1) -> SquareActivation -> Flatten -> FC(5*14*14, 100) -> SquareActivation -> FC(100, 10) -> SquareActivation -> FC(10, num_classes)
- **特点**: **HE友好设计**，使用平方激活函数 (x²) 替代ReLU，避免同态加密中的非线性开销；原始为TensorFlow/Keras实现，此处移植为PyTorch
- **参数量**: 99,270 (MNIST, 10 classes)
- **适用数据集**: MNIST, Fashion-MNIST, CIFAR-10
- **Batch数**: 25 batches (MNIST)
- **通信量**: 7.25 MB (全量密文)
- **使用场景**: HE专用模型对比；验证平方激活在联邦学习中的精度与效率权衡

### lstm (来源: Federated-Learning-master)

- **结构**: Embedding(vocab_size, embed_dim) -> 2-layer LSTM(hidden_dim, batch_first=True) -> Dropout -> FC(hidden_dim, num_classes)
- **特点**: 框架中**唯一的序列模型**，字符级LSTM，适合NLP联邦学习任务
- **参数量**: 819,920 (vocab=80, classes=80, hidden=256)
- **适用数据集**: Shakespeare, sent140 等文本/序列数据
- **Batch数**: 201 batches (vocab=80, classes=80)
- **通信量**: 58.22 MB (全量密文)
- **使用场景**: NLP联邦学习（如下一个字符预测、文本分类）；验证HE在序列模型上的可行性
- **关键配置**: `vocab_size` 需根据数据集调整（Shakespeare=80, sent140=2）

### shufflenet (来源: FedFetch-main)

- **结构**: InitBlock(Conv3x3, BN, ReLU, MaxPool) -> Stage1~3 (ShuffleUnit堆叠, 含ChannelShuffle+DepthwiseConv+PointwiseConv) -> AdaptiveAvgPool2d -> FC
- **特点**: **轻量级分组卷积+通道混洗**，专为移动设备设计的高效CNN；通过 `shufflenet_groups` 和 `shufflenet_width` 可灵活调节容量
- **参数量**: 914,338 (CIFAR-10, g3_w1, 10 classes)
- **适用数据集**: CIFAR-10, CIFAR-100, SVHN, MNIST, Fashion-MNIST
- **Batch数**: 224 batches (CIFAR-10)
- **通信量**: 64.90 MB (全量密文)
- **使用场景**: 移动/边缘设备联邦学习对比；验证分组卷积+ChannelShuffle在HE聚合中的效率
- **关键配置**: 
  - `shufflenet_groups`: 1/2/3/4/8，默认 3（g3_w1=1.87M on ImageNet-1000，此处因 10 类 FC 层大幅缩减故约 914K）
  - `shufflenet_width`: 1.0/0.75/0.5/0.25，默认 1.0；设为 0.5 时参数量降至约 534K (g1_wd2)

## 模型结构分类

#### 1. 轻量模型 (< 100K 参数, < 25 batches)
适合快速验证、CPU 环境、低带宽场景。

- **lenet** (MNIST): 44,426 参数, 11 batches, 3.19 MB
- **lenet** (CIFAR-10): 44,426 参数, 11 batches, 3.19 MB
- **deepcnn** (MNIST): 79,722 参数, 20 batches, 5.81 MB
- **deepcnn** (CIFAR-10): 79,722 参数, 20 batches, 5.81 MB
- **cnn_cifar** (CIFAR-10): 61,706 参数, 16 batches, 4.64 MB
- **cnn_fmnist** (Fashion-MNIST): 39,786 参数, 10 batches, 2.90 MB

#### 2. 中等模型 (100K - 500K 参数, 25-125 batches)
标准联邦学习场景的主力模型。

- **mlp** (MNIST): 235,146 参数, 58 batches, 16.84 MB
- **cnn** (MNIST): 130,890 参数, 32 batches, 9.29 MB
- **cnn** (CIFAR-10): 130,890 参数, 32 batches, 9.29 MB
- **densenet** (CIFAR-10): 175,738 参数, 43 batches, 12.48 MB
- **resnet20** (CIFAR-10): 272,186 参数, 67 batches, 19.45 MB
- **resnet32** (CIFAR-10): 466,618 参数, 114 batches, 33.09 MB

#### 3. 大型模型 (> 500K 参数, > 125 batches)
通信开销大，需要配合稀疏化或压缩策略使用。

- **vggnobn** (MNIST): 9,749,770 参数, 2381 batches, 691.20 MB
- **vggnobn** (CIFAR-10): 9,749,770 参数, 2381 batches, 691.20 MB
- **mobilenetv2** (CIFAR-10): 2,236,106 参数, 546 batches, 158.50 MB
- **resnet18** (CIFAR-10): 11,172,810 参数, 2728 batches, 791.93 MB
- **alexnet_cifar** (CIFAR-10): 23,272,266 参数, 5683 batches, 1647.60 MB
- **shufflenet** (CIFAR-10): 914,338 参数, 224 batches, 64.90 MB
- **alexnet_mnist** (MNIST): 11,696,202 参数, 2857 batches, 828.55 MB
