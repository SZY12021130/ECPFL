# CKKS-Fed 项目完成总结报告

## 项目概述

本项目完成了一个完整的研究型工程项目，涵盖三个阶段：
1. **阶段一**：深度分析16篇联邦学习+CKKS同态加密论文
2. **阶段二**：设计创新方案CKKS-Fed（含两个核心创新点）
3. **阶段三**：Python可运行原型系统实现

---

## 阶段一：论文分析成果

### 分析论文列表（16篇）

| 年份 | 论文 | 核心贡献 |
|------|------|----------|
| 2025 | Liu等 - Single-key HE | 单密钥分层聚合 |
| 2025 | Omar等 - Multi-key HE | 多密钥CKKS高效聚合 |
| 2025 | Li等 - FedPHE | 打包同态加密 |
| 2025 | Wu等 - ESAFL | 高效加法同态加密 |
| 2025 | Hu等 - MaskCrypt | 选择性同态加密 |
| 2025 | Passelègue等 - Low communication FHE | 低通信阈值FHE |
| 2025 | Zhang等 - Phalanx | FHE友好SNARK |
| 2025 | Yan等 - FedFetch | 预取调度优化 |
| 2025 | Korkmaz等 - Selective HE | 选择性HE+DP+scrambling |
| 2024 | Cai等 - SecFed | 多密钥+安全聚合混合 |
| 2024 | Jin等 - FedML-HE | 自适应敏感参数识别 |
| 2024 | Xie等 - Cloud Federation | 云联邦+ECC密钥保护 |
| 2020 | Zhang等 - BatchCrypt | 批量加密编码（经典） |
| 2017 | Bonawitz等 - Secure Aggregation | 实用安全聚合协议 |
| - | ResFed | 残差编码传输 |
| - | FetchSGD | Count Sketch压缩 |

### 关键洞察

**通病总结**：
1. CKKS乘法深度限制导致频繁bootstrapping
2. 密文膨胀问题（10-100倍）
3. 旋转密钥开销被忽视
4. 半诚实假设过于理想
5. 噪声泄露风险未充分考虑

**创新点总结**：
1. 单密钥分层聚合（Liu等2025）
2. 批量加密编码（BatchCrypt）
3. 多密钥高效聚合（Omar等2025）
4. 选择性加密（MaskCrypt）
5. 打包同态加密（FedPHE）

**研究空白**：
1. CKKS噪声精确分析缺失
2. 多密钥HE严格安全证明不足
3. 加密+压缩联合优化理论空白
4. 非IID数据下收敛性未研究

---

## 阶段二：方案设计成果

### 方案名称
**CKKS-Fed: Adaptive Noise Management for Single-Key Homomorphic Encryption in Federated Learning**

### 核心创新点

#### 创新点1：ANM噪声自适应管理
- **预热期**：使用较小模数链，激进乘法深度
- **稳定期**：使用标准模数链，保守乘法深度
- **精调期**：使用较大模数链，最小乘法深度

噪声预算公式：
```
Budget(ct) = log₂(q_l) - log₂(||e||_can · √N)
```

#### 创新点2：RKP旋转密钥预分配
- 基于梯度稀疏性模式预计算旋转密钥
- 在线时直接使用预计算密钥
- 减少密钥生成和交换开销

### 数学基础

从RLWE假设严格推导CKKS：

**RLWE问题**：区分 (a, b = a·s + e) 和 (a, u)

**CKKS核心算法**：
- 密钥生成: pk = (b, a), b = -a·s + e
- 加密: ct = (b·v + e₀ + m, a·v + e₁)
- 解密: m̃ = c₀ + c₁·s
- 同态加法: ct₁ + ct₂
- 同态乘法: ct₁ × ct₂（噪声增长：||e_mult|| ≤ C₁·||e₁||·||e₂|| + ...）

### 安全性分析

| 威胁模型 | 安全保证 |
|----------|----------|
| 半诚实 | IND-CPA语义安全（基于RLWE） |
| 恶意 | 可检测错误梯度/重复提交/权重操纵 |
| 共谋（t < n/2） | 诚实客户端梯度机密性保证 |

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        系统架构                              │
├─────────────────────────────────────────────────────────────┤
│  客户端层 (N个)                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       ┌─────────┐     │
│  │ Client 1│ │ Client 2│ │ Client 3│  ...  │ Client N│     │
│  │本地训练 │ │本地训练 │ │本地训练 │       │本地训练 │     │
│  │ANM加密 │ │ANM加密 │ │ANM加密 │       │ANM加密 │     │
│  └────┬────┘ └────┬────┘ └────┬────┘       └────┬────┘     │
│       │           │           │                 │           │
│       └───────────┴───────────┴─────────────────┘           │
│                   │                                         │
│                   ▼                                         │
│  ┌─────────────────────────────────────────────┐           │
│  │           聚合服务器 (AS)                    │           │
│  │  - 密文加权聚合                             │           │
│  │  - 参数更新                                 │           │
│  └─────────────────────┬───────────────────────┘           │
│                        │                                    │
│                        ▼                                    │
│  ┌─────────────────────────────────────────────┐           │
│  │           辅助节点 (TEE)                     │           │
│  │  - 安全聚合解密                             │           │
│  │  - 噪声监控                                 │           │
│  │  - 密钥托管                                 │           │
│  └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 阶段三：Python实现成果

### 项目结构

```
ckks_fed/
├── config.yaml              # 实验参数配置
├── requirements.txt         # 依赖管理
├── README.md               # 项目文档
│
├── crypto_utils.py         # CKKS加密工具 (600+行)
│   ├── CKKSContext         # 上下文管理
│   ├── CKKSEncryptor       # 加密器
│   ├── CKKSDecryptor       # 解密器
│   ├── CKKSEvaluator       # 同态运算
│   ├── ANMManager          # 噪声自适应管理
│   ├── RKPManager          # 旋转密钥预分配
│   └── CKKSManager         # 整合管理器
│
├── models.py               # 神经网络模型
│   ├── MLP                 # 多层感知机
│   └── CNN                 # 卷积神经网络
│
├── train_utils.py          # 训练工具函数
│   ├── 数据加载与预处理
│   ├── 数据集划分 (IID/非IID)
│   └── 训练与评估函数
│
├── client.py               # 联邦学习客户端
│   ├── FederatedClient     # 完整客户端
│   └── SimpleClient        # 简化客户端
│
├── server.py               # 服务器端
│   ├── AggregationServer   # 聚合服务器
│   └── HelperNode          # 辅助节点(TEE)
│
├── main.py                 # 主程序入口
│   ├── MetricsCollector    # 指标收集器
│   └── CKKSFedExperiment   # 实验类
│
├── visualize.py            # 可视化模块
│   └── ResultVisualizer    # 结果可视化器
│
└── test_basic.py           # 基础测试脚本
```

### 核心功能验证

| 功能 | 状态 | 说明 |
|------|------|------|
| 配置加载 | ✅ | 成功加载YAML配置 |
| 模型创建 | ✅ | MLP/CNN模型测试通过 |
| CKKS加密 | ✅ | 加法误差 < 0.002, 标量乘法误差 < 0.16 |
| ANM管理器 | ✅ | 阶段参数切换正常 |

### 实验指标（9项）

| 指标类别 | 具体指标 |
|----------|----------|
| **计算时间** | 本地训练时间、加密时间、聚合时间、总轮次时间 |
| **通信开销** | 每轮通信开销、累积通信开销 |
| **模型性能** | 测试准确率、测试损失 |
| **系统指标** | CPU利用率、内存使用、噪声预算 |
| **密钥管理** | 密钥分发时间、密钥分发开销 |

### 可视化输出

运行实验后将生成6类图表：
1. `accuracy_comparison.png` - 准确率对比
2. `loss_comparison.png` - 损失对比
3. `computation_time.png` - 计算时间分析
4. `communication_cost.png` - 通信开销分析
5. `system_metrics.png` - 系统指标分析
6. `summary_table.png` - 结果汇总表格

---

## 使用说明

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行实验
```bash
python main.py
```

### 生成可视化
```bash
python visualize.py results/exp1/metrics.json results/exp2/metrics.json
```

### 运行测试
```bash
python test_basic.py
```

---

## 文件清单

### 文档文件
- `/mnt/okcomputer/output/phase1_paper_analysis.md` - 阶段一论文分析报告
- `/mnt/okcomputer/output/phase2_scheme_design.md` - 阶段二方案设计文档
- `/mnt/okcomputer/output/project_summary.md` - 项目总结报告（本文件）

### 代码文件
- `/mnt/okcomputer/output/ckks_fed/config.yaml` - 配置文件
- `/mnt/okcomputer/output/ckks_fed/requirements.txt` - 依赖文件
- `/mnt/okcomputer/output/ckks_fed/README.md` - 项目说明
- `/mnt/okcomputer/output/ckks_fed/crypto_utils.py` - CKKS加密工具
- `/mnt/okcomputer/output/ckks_fed/models.py` - 神经网络模型
- `/mnt/okcomputer/output/ckks_fed/train_utils.py` - 训练工具
- `/mnt/okcomputer/output/ckks_fed/client.py` - 客户端实现
- `/mnt/okcomputer/output/ckks_fed/server.py` - 服务器实现
- `/mnt/okcomputer/output/ckks_fed/main.py` - 主程序
- `/mnt/okcomputer/output/ckks_fed/visualize.py` - 可视化模块
- `/mnt/okcomputer/output/ckks_fed/test_basic.py` - 测试脚本

---

## 技术亮点

1. **严格的数学基础**：从RLWE假设出发，完整推导CKKS核心流程
2. **创新的ANM策略**：根据训练阶段动态调整CKKS参数
3. **实用的RKP优化**：预计算旋转密钥减少在线开销
4. **完整的安全性分析**：涵盖半诚实/恶意/共谋三种威胁模型
5. **可运行的原型系统**：基于TenSEAL实现，支持MNIST/Fashion-MNIST
6. **全面的实验指标**：9项指标采集与可视化

---

## 后续工作建议

1. 在真实数据集上运行完整实验
2. 对比更多baseline方案
3. 扩展支持CIFAR-10等复杂数据集
4. 实现多密钥CKKS扩展
5. 添加差分隐私保护
6. 进行更严格的安全性证明

---

*项目完成时间：2026年3月30日*
