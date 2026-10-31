# 数据集与模型描述修正

## 原始描述 vs 代码实际结构

| 数据集 | 原始描述 | 代码实际模型 | 修正描述 |
|--------|---------|------------|---------|
| MNIST | LeNet with two convolutional layers followed by three fully connected layers | `LeNet` (LeNet-5 变体) | LeNet-5 变体，两个卷积层（6→16通道，5×5核）接三个全连接层（120→84→10），参数量约60K |
| FEMNIST | CNN with 2 convolutional layers and 2 fully-connected layers | `CNNFashion` | 三个卷积层（16→32→64通道，含BatchNorm）接全局平均池化和全连接层，参数量约39K |
| CIFAR-10 | ResNet-18 | `ResNetCifar` (ResNet20) | ResNet20（非标准ResNet-18），初始通道16，三个stage（16→32→64），每个stage含3个残差块，参数量约272K |

## 修改后的 LaTeX 段落

```latex
\begin{itemize}
    \item \textbf{MNIST}~\cite{lecun1998gradient}: Handwritten digit classification with 60,000 training and 10,000 test examples across 10 classes. We employ a LeNet-5 variant~\cite{lecun1998gradient} comprising two convolutional layers (6 and 16 channels, $5\times5$ kernels) with ReLU activations and max-pooling, followed by three fully connected layers (120$\to$84$\to$10). The model contains approximately 60K parameters, making it communication-efficient for federated training.
    \item \textbf{FEMNIST}~\cite{caldas2018leaf}: A federated extension of EMNIST containing 671,585 handwritten character images (62 classes) from 3,400 users. We use \texttt{CNNFashion}, a lightweight CNN tailored for $28\times28$ grayscale inputs with three convolutional stages (16$\to$32$\to$64 channels, each followed by BatchNorm and ReLU), two max-pooling layers, and a single fully connected output layer. This architecture contains approximately 39K parameters and aligns with the FedPHE baseline implementation.
    \item \textbf{CIFAR-10}~\cite{krizhevsky2009learning}: A 10-class color image classification dataset with 60,000 $32\times32$ images. We deploy \texttt{ResNetCifar} (ResNet20)~\cite{he2016deep}, a CIFAR-optimized residual network with an initial convolution of 16 channels, three stages (16$\to$32$\to$64 channels), and 3 basic residual blocks per stage (total 6n+2 layers where $n=3$). Unlike the standard ImageNet ResNet-18, this variant removes the early max-pooling and adapts the filter sizes for small inputs, containing approximately 272K parameters.
\end{itemize}
```

## 关键修改点

1. **MNIST**: 明确是 LeNet-5 variant，参数量约60K，强调通信效率
2. **FEMNIST**: 修正为 3 conv layers（不是2层），加入 BatchNorm 细节，参数量约39K，说明与 FedPHE 对齐
3. **CIFAR-10**: **最关键**：原文写 ResNet-18 是**错误的**。代码中使用的是 `ResNetCifar`（ResNet20/32），初始通道16，3个stage，无 bottleneck。必须与标准 ResNet-18 区分清楚，否则审稿人会质疑实验设置不一致。
