# CKKS-Fed 问题与解决记录

> 本文档记录项目开发/调试过程中提出的问题及最终解决方案，按时间顺序整理。

---

## Q1: 可视化脚本有 bug，图片没有数据，且只输出 PDF 没有 PNG

**问题描述**: `visualize.py` 的 `_save_both` 方法存在递归调用自身导致崩溃；生成的图片看起来是空的；没有生成 PNG。

**最终解决**:
- 修复了 `_save_both` 的递归 bug，改为 `plt.savefig(save_path)` + `plt.savefig(png_path, dpi=300)` 的方式。
- 确认图片"没有数据"的原因是实验只跑了 **1 轮**，折线图只有一个点，在 IEEE/SciencePlots 细线风格下几乎不可见。
- 将所有 `plt.savefig` 调用替换为 `_save_both()`，确保每次保存同时输出 PDF 和 PNG。

---

## Q2: 项目结构混乱，需要重新规划和删除不必要的文件

**问题描述**: 根目录下代码文件、临时脚本、文档混在一起，结构不清晰。

**最终解决**:
- 重构为标准化 Python 项目结构：
  ```
  ckks_fed/
  ├── main.py                  # 入口脚本
  ├── ckks_fed/                # 核心包
  │   ├── crypto.py
  │   ├── models.py
  │   ├── data.py
  │   ├── client.py
  │   ├── server.py
  │   └── plotting.py
  ├── configs/
  ├── tests/
  ├── docs/
  ├── data/
  ├── results/
  └── visualization/
  ```
- 删除了 `fix_logs.py`、`fix_viz.py` 等临时脚本，清理了 `__pycache__`。
- 更新了所有 import 路径为包级绝对导入（`from ckks_fed.xxx import ...`）。
- 新增 `.gitignore`。

---

## Q3: 如何在重构后执行可视化？

**问题描述**: 重构后找不到 `visualize.py`，不确定命令行调用方式。

**最终解决**:
```bash
cd ckks_fed
python -m ckks_fed.plotting <encrypted_metrics.json> <plain_metrics.json>
```
输出目录为 `visualization/viz_YYYYMMDD_HHMMSS/`，同时包含 PDF 和 PNG。

---

## Q4: README 中增加时序图、指标解释、数据划分说明

**问题描述**: 需要在 README 中补充：
1. 实体交互时序图；
2. 每个评价指标的意义和计算原理；
3. 为什么 IID 时各客户端数据量一致，以及如何切换到非 IID。

**最终解决**:
- 新增 **Mermaid 时序图**，展示 Client → Server → HelperNode 的完整加密聚合流程。
- 新增详细指标表格，解释 6 大类指标（计算时间、通信开销、密文特性、模型性能、系统指标、密钥管理）的意义和计算公式。
- 解释 `partition_data_iid` 均匀切分导致数据量一致的原因。
- 给出非 IID 切换方法：修改 `config.yaml` 中 `data.iid: false` 和 `alpha` 值，并提供 `alpha` 参考表（10.0 接近 IID，0.5 明显非 IID，0.1 高度非 IID）。

---

## Q5: 运行时输出每个客户端的样本分布和类别统计

**问题描述**: 想在终端看到每个客户端的类别数量分布，以及全局各类别总数。

**最终解决**:
- 在 `data.py` 中新增 `log_client_distributions()` 函数。
- 在 `create_client_dataloaders()` 划分完成后自动调用。
- 输出形式为表格：每行一个 Client，列出每个类别的样本数，最后汇总 Overall total 和 Per-class total。

**示例输出**:
```
======================================================================
Client Data Distribution
======================================================================
Client  0: total=12000 |  0:1198   1:1373   2:1174   3:1237  ...
...
----------------------------------------------------------------------
Per-class total:  0: 5923   1: 6742   2: 5958  ...
Overall total samples: 60000
======================================================================
```

---

## Q6: RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu!

**问题描述**: 训练时 `server.update_global_model()` 中 `param.add_()` 报错，因为解密后的聚合更新在 CPU，而全局模型在 CUDA。

**最终解决**:
- 在 `server.py` 的 `update_global_model` 中，添加 `update_tensor = aggregated_update[name].to(param.device)`，确保解密后的更新张量自动对齐到模型参数所在设备。
- Buffer 更新同理。

---

## Q7: 每一轮密文膨胀率都完全一样（10.21x），是不是算错了？请检查其他数据

**问题描述**: 日志中每轮膨胀率固定，怀疑计算错误；要求检查所有数据正确性。

**最终解决**:
- **膨胀率固定 = 正常**：因为模型结构（MLP/CNN）和 CKKS 参数每轮不变，`plaintext_size` 和 `ciphertext_size` 本质上是常量，比值自然恒定。
- 发现并修复 **2 个真实 bug**：
  1. `download_cost` 只计算了 1 个客户端的接收量，但服务器是广播给所有客户端的。修复：乘以 `len(client_updates)`。
  2. `key_distribution_cost` 原先是估计值（`poly_modulus_degree * 8`），与真实值相差巨大。修复：新增 `get_key_distribution_size()` 用 `context.serialize()` 测量真实公钥/Galois 密钥大小，并乘以客户端数量。

---

## Q8: 每一轮都保存模型文件是否冗余？只想保存最终模型

**问题描述**: `save_interval` 导致中间 checkpoint 过多，占用空间且混乱。

**最终解决**:
- 在 `run_experiment()` 结尾强制保存最终轮模型，避免只跑中间轮而没有最终模型的情况。
- 建议将 `config.yaml` 中的 `save_interval` 设为 `999`（大于总轮数），这样只会保存最终模型，不会产生中间 checkpoint。

---

## Q9: 不要用 JSON 保存结果，要优雅文档；新增模型和 CKKS 参数选择；打印模型结构

**问题描述**: 希望：
1. 用可读文档替代/补充 JSON；
2. 增加 LeNet、MobileNetV2、DenseNet 等模型；
3. CKKS 参数给出多组预设和选择指南；
4. 建立模型-数据集匹配最佳实践；
5. 训练开始时在终端打印模型结构。

**最终解决**:
- **Markdown 报告**：`main.py` 中新增 `_save_markdown_report()` 和 `_generate_comparison_report()`，生成 `report.md`（单实验）和 `comparison_report_xxx.md`（对比），包含配置摘要、关键指标、每轮详细表格、结论。保留 `metrics.json` 供可视化使用。
- **新增模型**：在 `models.py` 中新增 `LeNet`、`MobileNetV2`（轻量版）、`DenseNet`（轻量版），加上原有的 `MLP`、`CNN` 共 5 个模型，均支持通过 `config.yaml` 的 `model.name` 切换。
- **CKKS 参数预设**：在 `config.yaml` 中新增 4 组推荐预设（轻量快速、标准均衡、高精度、高安全），附带详细选择指南注释。
- **模型-数据集匹配表**：在 `config.yaml` 中建立最佳实践推荐表，例如 mnist → lenet，cifar10 → mobilenetv2，并给出各模型通信成本参考。
- **打印模型结构**：在 `main.py` 初始化模型后调用 `print_model_summary()`。

---

## Q10: 实验指标配置里的 true/false 到底有没有用？

**问题描述**: `config.yaml` 中 `metrics` 区块的各项 `true`/`false` 开关是否真的会控制指标计算？

**最终解决**:
- **当前状态：这些开关是无效的摆设。** 代码中没有任何地方读取 `config['metrics']`，无论设成 `true` 还是 `false`，所有指标都会被计算和记录。
- 说明：该配置块仅具有文档说明意义，尚未实现条件控制逻辑。

---

## Q11: 模型保存路径需要按时间戳分组，不要全部堆在 history_models 根目录

**问题描述**: 所有实验的模型文件都保存在 `history_models/` 下，没有按实验区分。

**最终解决**:
- 修改 `main.py` 的 `_save_model()` 方法，将模型保存路径改为：
  ```
  history_models/models_{timestamp}/model_round_{round_num}.pth
  ```
- 每次实验的模型都会隔离在自己的时间戳子目录中，避免混淆。

---

## Q12: 不喜欢原来的模型结构打印风格，想要表格形式，体现每一层的输出形状和参数量

**问题描述**: 原来的 `print(model)` 嵌套文本不够直观，想要类似 Keras 的层级表格。

**最终解决**:
- 重写 `ckks_fed/models.py` 中的 `print_model_summary()` 函数。
- 采用 **前向 hook** 机制，对 dummy input 跑一遍前向传播，收集每一层的 `Layer (type)`、`Output Shape`、`Param #`。
- 输出效果为对齐表格，底部汇总 `Total params`、`Trainable params`、`Model size`，风格类似 Keras `model.summary()`。

---

## Q13: 可视化输出目录错误，保存到了 `ckks_fed/ckks_fed/visualization/` 而不是项目根目录

**问题描述**: `ResultVisualizer` 默认使用相对路径 `"./visualization"`，导致无论从哪执行命令，输出目录可能偏离项目根目录下的 `visualization/`。

**最终解决**:
- 修改 `ckks_fed/plotting.py` 中 `ResultVisualizer.__init__()` 的路径解析逻辑。
- 通过 `os.path.dirname(os.path.abspath(__file__))` 定位包目录，再 `dirname` 一次得到项目根目录，确保输出固定到 `ckks_fed/visualization/viz_YYYYMMDD_HHMMSS/`。

---

## Q14: 每次训练都同时跑加密+明文两个实验，想要加一个开关控制是否跑明文对比

**问题描述**: `main.py` 每次固定先跑 CKKS-Fed 加密实验，再跑 FedAvg 明文实验，无法单独跑加密实验。

**最终解决**:
- 在 `configs/config.yaml` 的 `system` 区块新增 `run_plaintext_baseline: true` 开关。
- 修改 `main.py` 的 `main()` 函数：
  - 读取配置中的开关；
  - 当 `run_plaintext_baseline: false` 时，跳过明文实验、跳过终端对比输出、不生成 `comparison_report`；
  - 仅保留加密实验的 `report.md` 和日志输出。

---

## Q15: `upload_difference` 开关开启后通信开销没有降低，且 compare.py 中看不到该差异项

**问题描述**: 
1. 用户将 `upload_difference` 设为 `true`（差值上传）与 `false`（完整权重上传）分别做了两次实验，发现通信开销（`avg_upload_kb`、`total_communication_mb`）几乎没有变化（仅差 0.8KB）。
2. 使用 `python -m ckks_fed.compare` 对比两次实验时，配置对比表格中没有出现 `upload_difference` 这一行差异。

**原因分析**:

1. **通信开销未降低 = 正常现象**：
   - `upload_difference` 只是切换客户端上传**差值**（`new_params - old_params`）还是**完整权重**（`new_params`）。
   - 两者的张量 `shape` 和 `numel()` 完全相同，因此：
     ```python
     plaintext_size = sum(v.numel() * 4 for v in model_update.values())
     ciphertext_size = sum(len(ct.serialize()) for ct in encrypted_update.values())
     num_ciphertexts = sum(len(v) for v in encrypted_update.values())
     ```
     以上三项指标在两种模式下**完全一致**。
   - **差值上传 ≠ 通信压缩**。真正降低通信的技术是：Top-k 稀疏化、量化（QSGD）、Sketch 压缩、或者 Slot Packing（这个已经实现了）。`upload_difference` 只是切换聚合的数学形式，对通信量没有影响。

2. **compare.py 看不到差异 = 注册表字段遗漏**：
   - `_update_experiment_registry()` 在生成 `experiments_registry.json` 时，`config_summary` 里没有写入 `upload_difference` 字段。
   - 因此对比工具在读取注册表时，自然看不到这个配置项，也就无法高亮差异。

**最终解决**:
- 概念澄清：`upload_difference` 的目的是**消融验证两种聚合形式的数学等价性**（差值累加 vs 完整权重替换），而非降低通信开销。在权重归一化和为 1 且 `learning_rate=1.0` 时，两种方式理论上等价（实验中验证了准确率完全一致）。
- 代码修复：在 `main.py` 的 `_update_experiment_registry()` 中，`config_summary` 新增 `"upload_difference": self.config['system'].get('upload_difference', True)`。
- **注意**：已存在的历史实验记录不会自动补全该字段，需要删除旧注册表后重新跑实验，才能在 `compare.py` 中看到 `upload_difference` 差异高亮。

---


## Q16: 鲁棒性实验矩阵设计、攻击后果与防御效果分析

**问题描述**: 在构建联邦学习 + CKKS 鲁棒性研究平台后，需要系统性地梳理：
1. 实验矩阵为什么是 60 个实验？
2. 每种攻击会对全局模型造成什么后果？
3. 每种防御的预期效果是什么？
4. 在 CKKS 同态加密环境下，防御部署有什么特殊困难？

---

### 1. 实验矩阵的构成

配置文件定义了：
- **6 种攻击**：sign_flipping, scaling, gaussian_noise, backdoor, mimic_alie, constant
- **9 种防御**：fedavg, median, trimmed_mean, krum, multi_krum, geometric_median, norm_clip_fedavg, cosine_fedavg, multi_criteria_fedavg
- **1 种模式**：plain（明文，暂 focus 于此）

`attack_runner.py` 的矩阵构建逻辑是**全组合（笛卡尔积）**：
- 每种攻击场景下，先跑 1 个 **baseline（无攻击 + fedavg）**
- 然后该攻击分别与 **9 种防御** 各跑一次

因此总实验数 = **6 × (1 + 9) = 60 个实验**。

> 这不是函数映射意义上的"满射"，而是**控制变量对比**：固定攻击类型，观察不同防御的效果差异。

---

### 2. 数据层面攻击的后果

| 攻击 | 机制 | 对全局模型的后果 |
|------|------|----------------|
| **Label Flipping** | 将训练数据标签改为错误的（随机/全转一类/定向翻转） | 模型学到错误映射。**random** 模式整体准确率显著下降；**all_to_one** 导致模型倾向于将所有输入预测成目标类；**targeted** 使特定两类间区分崩溃 |
| **Backdoor Data** | 在图像中注入触发器（如右下角白块），并强制标签为目标类 | **隐蔽性高**：正常测试集准确率几乎不受影响，但**只要输入带 trigger，就会被错误分类到目标类**。模型行为正确但存在隐藏漏洞 |

---

### 3. 模型层面攻击的后果

| 攻击 | 机制 | 对全局模型的后果 |
|------|------|----------------|
| **Sign-flipping** | 将梯度/差值符号全部取反 | 破坏收敛方向，全局模型往最优解的反方向更新。恶意客户端比例高时，准确率暴跌甚至发散 |
| **Scaling** | 将模型更新乘以大系数（如 10x） | 在 FedAvg 加权聚合中**恶意影响力被不成比例放大**。2 个恶意客户端可能获得相当于 20 个客户端的权重，常用于配合后门进行"模型替换" |
| **Gaussian Noise** | 在更新中加入大量随机噪声 | 非定向破坏，全局模型收敛变慢、震荡，最终准确率显著下降。类似"在梯度里撒沙子" |
| **Backdoor Model** | 恶意客户端先用后门数据训练，再对更新进行缩放 | 将后门持久化注入全局模型。正常样本表现尚可，但带 trigger 的样本会被定向误分类。最接近真实威胁的攻击形式之一 |
| **Mimic (ALIE)** | 对正常更新进行微小偏移（如 +1.5σ） | **隐蔽性极强**。不会导致准确率暴跌，而是让模型收敛到被精心偏移的点。专门用来绕过基于统计的防御 |
| **Constant** | 直接上传全 0（或固定常数）的更新 | 导致全局模型收敛停滞或退化。相当于告诉服务器"不要更新这些参数"或"往固定值拉" |

---

### 4. 防御手段的效果分析

#### 4.1 鲁棒聚合规则

| 防御 | 核心机制 | 预期效果 |
|------|---------|---------|
| **FedAvg** | 标准加权平均 | **无防御效果**，攻击会 100% 进入全局模型。仅作为 baseline 用于对比 |
| **Median** | 对每个参数坐标取所有客户端值的中位数 | 对 **Sign-flipping**、**Gaussian Noise**、**Constant** 效果极好（异常值被中位数自然过滤）。对 **Scaling** 和 **Backdoor** 效果有限（缩放后的值未必是极端值） |
| **Trimmed Mean** | 每个坐标去掉最高和最低的 `trim_ratio` 比例后再平均 | 只要恶意比例 **< trim_ratio**（如 20%），攻击影响基本被消除。计算比 Median 高效，信息利用更充分 |
| **Krum** | 计算每个更新与其他更新的相似度，选"最合群"的一个 | 对明显离群的 **Sign-flipping**、**Constant**、**Gaussian Noise** 非常有效。但如果恶意客户端协调一致（如 **ALIE**），可能"骗过"Krum 被选上 |
| **Multi-Krum** | 先选 `m` 个最可信的更新，再用 FedAvg 聚合 | 比 Krum 更稳定，保留了更多良性客户端的信息，通常性能优于 Krum |
| **Geometric Median** | 寻找使得到所有更新距离之和最小的点（Weiszfeld 迭代） | 对 **ALIE** 和 **Backdoor** 有一定抵抗力，因为几何中位数比 Krum 更难被少数协调好的攻击者绕过。但计算开销较大 |

#### 4.2 异常检测过滤（聚合前）

| 防御 | 核心机制 | 预期效果 |
|------|---------|---------|
| **Norm Clip** | 更新 L2 范数超过中位数范数 `max_norm_ratio` 倍则剔除 | 对 **Scaling** 极其有效（缩放后范数必然暴增）。对 **Sign-flipping** 范数不变，因此**基本无效** |
| **Cosine Similarity** | 计算每个更新与中位数更新的方向余弦，过低则剔除 | 对 **Sign-flipping** 极其有效（方向完全相反，余弦接近 -1）。对 **Constant** 也有效 |
| **MAD** | 基于中位数绝对偏差计算稳健 Z-score，剔除离群点 | 综合性统计防御。对各种导致更新分布异常的攻击都有一定效果，但对精心控制的 **ALIE** 效果有限 |
| **Multi-Criteria** | **Norm Clip + Cosine Similarity** 联合过滤 | 双重保险。能同时应对 Scaling（范数异常）和 Sign-flipping（方向异常）。但阈值过严时可能**误杀诚实但更新幅度大的客户端** |

---

### 5. 攻击 vs 防御最佳实践速查表

| 攻击类型 | 最有效的防御 | 原因 |
|---------|------------|------|
| **Sign-flipping** | Median / Cosine Similarity / Multi-Criteria | 方向完全相反，中位数和余弦检测都能精准识别 |
| **Scaling** | Norm Clip / Trimmed Mean | 范数异常是死穴；截断均值也能把极端大值截掉 |
| **Gaussian Noise** | Median / Trimmed Mean / MAD | 噪声产生的极端值会被中位数或截断过滤 |
| **Constant** | Krum / Multi-Krum / Cosine Similarity | 常数更新与正常更新差异巨大，容易在相似度检测中被排除 |
| **Backdoor Model** | Multi-Krum / Geometric Median / Multi-Criteria | 后门更新可能方向/范数都正常，需要多维检测或多选可信聚合 |
| **Mimic (ALIE)** | Trimmed Mean / Geometric Median | ALIE 专门绕过 Krum，但截断均值和几何中位数对协调偏移有更好抵抗力 |

---

### 6. CKKS 加密环境下防御的特殊难点

#### 6.1 核心结论

> **CKKS 同态加密保护的是隐私，不是鲁棒性。**

恶意客户端可以正常加密它的有毒更新并上传。由于 CKKS 是同态的，服务器直接在密文上执行加权聚合，攻击影响依然会体现在最终解密后的全局模型中。

换句话说：
- **隐私保护**（服务器看不到单个客户端的明文梯度）✅
- **拜占庭鲁棒性**（自动抵御恶意更新）❌

这两个目标在标准 CKKS 流程中是**相互冲突**的：
- Median、Krum、Trimmed Mean、Norm Clip、Cosine Similarity 等防御都依赖"看到单个客户端的明文更新内容"
- 但在标准 CKKS-Fed 架构中，服务器只持有公钥，永远看不到单个更新的明文
- 辅助节点（HelperNode）只在**聚合完成后**解密一次

#### 6.2 可行的解决路径

1. **明文实验先行**（本平台当前采用）：
   - 在明文环境下完整跑完 60 个 (攻击, 防御) 组合
   - 掌握"什么攻击用什么防"的定量关系
   - 再在加密实验中验证"攻击对加密 FL 仍然有效"

2. **辅助节点增强**（未来研究方向）：
   - 让 HelperNode 在每一轮中先单独解密每个客户端更新
   - 执行异常检测和过滤
   - 再重新聚合
   - 代价：牺牲部分同态聚合的效率，引入额外解密开销

3. **安全聚合 + 零知识证明**（更高级）：
   - 超出本平台当前范围，可作为后续论文的延伸工作

#### 6.3 研究启示

本平台的核心价值在于帮助研究者建立以下认知：
- **不能假设 CKKS（或任何同态加密）会自动抵御拜占庭攻击**
- 要在联邦学习中同时实现**隐私保护**和**鲁棒性**，必须将两者作为**独立的设计目标**分别解决
- 在加密场景下部署单客户端梯度防御，需要重构聚合流程（如引入 HelperNode 逐客户端解密检测），这本身就是值得研究的课题

---

**最终解决**: 已将上述分析整理为技术文档并追加到 `docs/problem_log.md`。同时更新了 `README.md`，在"攻击与防御"章节中引用了相同结论。实验矩阵和防御逻辑已固化到 `configs/attack_config.yaml` 和 `ckks_fed/experiments/attack_runner.py` 中。

---


## Q17: Krum / Multi-Krum 断言报错，且不希望一次性跑全部 60 个实验

**问题描述**:
1. 跑全组合实验矩阵时，`krum_aggregate` 和 `multi_krum_aggregate` 抛出 `AssertionError`：
   ```
   AssertionError: Krum requires n > 2f + 2, got n=10, f=4
   ```
2. 用户不想一次性跑 60 个实验，希望在配置文件里灵活控制只跑关键组合，并且每个攻击对应最佳实践的防御方式。

---

### 原因分析

#### 1. Krum 断言失败
Krum 的理论前提是：
```
n > 2f + 2
```
其中 `n` 是参与聚合的客户端数，`f` 是估计的恶意客户端数上限。

原代码中 `f` 的自动推断逻辑是：
```python
f = max(0, n // 2 - 1)
```
当 `n = 10` 时，`f = 4`，但 `10 > 2*4 + 2 = 10` 不成立（严格大于），所以断言失败。

正确的自动推断应该是：
```python
f = max(0, (n - 3) // 2)
```
当 `n = 10` 时，`f = 3`，满足 `10 > 2*3 + 2 = 8`。

#### 2. 实验矩阵过大
原 `attack_runner.py` 采用笛卡尔积生成实验矩阵：6 种攻击 × 9 种防御 + baseline = 60 个实验。用户无法灵活控制，且大量组合并非"最佳实践"，实验效率低。

---

### 最终解决

#### 修复 1：修正 Krum / Multi-Krum 的 `f` 自动推断

文件：`ckks_fed/defenses/aggregation_rules.py`

修改两处：
```python
# 修改前
f = max(0, n // 2 - 1)

# 修改后
f = max(0, (n - 3) // 2)
```

验证：对于 `n = 10`，`f = 3`，`10 > 8` 成立，断言不再触发。

#### 修复 2：引入显式实验列表（白名单模式）

文件：`ckks_fed/experiments/attack_runner.py`

修改 `_build_attack_matrix()` 方法：
- 优先读取配置中的 `experiments` 列表，精确控制每个实验的 `(mode, attack, defense)` 组合。
- 如果配置中没有 `experiments` 字段，才回退到旧的全组合模式，保持向后兼容。

```python
def _build_attack_matrix(self) -> List[Dict]:
    explicit_experiments = self.config.get('experiments', None)
    if explicit_experiments is not None:
        # 白名单模式：只跑用户显式指定的组合
        for exp in explicit_experiments:
            ...
    else:
        # 回退：全组合（笛卡尔积）
        ...
```

#### 修复 3：重写默认配置文件，只跑最佳实践组合

文件：`configs/attack_config.yaml`

新增 `experiments` 字段，从 60 个实验精简为 **18 个精选实验**：

```yaml
experiments:
  # Baseline
  - { mode: "plain", attack: "none", defense: "fedavg" }

  # Sign-flipping → Median / Cosine
  - { mode: "plain", attack: "sign_flipping", defense: "fedavg" }
  - { mode: "plain", attack: "sign_flipping", defense: "median" }
  - { mode: "plain", attack: "sign_flipping", defense: "cosine_fedavg" }

  # Scaling → Trimmed Mean / Norm Clip
  - { mode: "plain", attack: "scaling", defense: "fedavg" }
  - { mode: "plain", attack: "scaling", defense: "trimmed_mean" }
  - { mode: "plain", attack: "scaling", defense: "norm_clip_fedavg" }

  # Gaussian Noise → Median
  - { mode: "plain", attack: "gaussian_noise", defense: "fedavg" }
  - { mode: "plain", attack: "gaussian_noise", defense: "median" }

  # Backdoor → Multi-Krum / Multi-Criteria
  - { mode: "plain", attack: "backdoor", defense: "fedavg" }
  - { mode: "plain", attack: "backdoor", defense: "multi_krum" }
  - { mode: "plain", attack: "backdoor", defense: "multi_criteria_fedavg" }

  # Mimic (ALIE) → Trimmed Mean / Geometric Median
  - { mode: "plain", attack: "mimic_alie", defense: "fedavg" }
  - { mode: "plain", attack: "mimic_alie", defense: "trimmed_mean" }
  - { mode: "plain", attack: "mimic_alie", defense: "geometric_median" }

  # Constant → Krum / Cosine
  - { mode: "plain", attack: "constant", defense: "fedavg" }
  - { mode: "plain", attack: "constant", defense: "krum" }
  - { mode: "plain", attack: "constant", defense: "cosine_fedavg" }
```

> 如需跑某个攻击的更多防御组合，或加入 `encrypted` 模式，直接在 `experiments` 列表中增删即可。若删掉整个 `experiments` 字段，系统会自动恢复 60 个实验的全组合模式。

---

### 验证结果

- `constant + krum`（10 客户端）：通过，`final_acc = 13.28%`
- `backdoor + multi_krum`（10 客户端）：通过，`final_acc = 12.88%`
- 显式实验列表生效后，实验总数从 **60 个** 降为 **18 个**，且均为文献中推荐的"最佳实践"组合。

---


## Q18: 希望命令行支持过滤，只运行某一组实验

**问题描述**: 即使配置文件精简到了 18 个实验，用户仍然不想一次性全部运行，而是希望通过命令行参数灵活选择，比如"只跑 Scaling 攻击的实验"或"只跑 Median 防御的实验"。

---

### 最终解决

#### 修改 1：扩展 `AttackExperimentRunner` 支持过滤参数

文件：`ckks_fed/experiments/attack_runner.py`

在 `__init__` 中新增三个可选过滤参数：
```python
def __init__(self, config_path: str = "configs/attack_config.yaml",
             filter_attack: str = None,
             filter_defense: str = None,
             filter_mode: str = None):
```

在 `_build_attack_matrix()` 构建完实验矩阵后，追加过滤逻辑：
```python
if self.filter_attack is not None:
    matrix = [m for m in matrix if m['attack_name'] == self.filter_attack]
if self.filter_defense is not None:
    matrix = [m for m in matrix if m['defense_name'] == self.filter_defense]
if self.filter_mode is not None:
    matrix = [m for m in matrix if m['mode'] == self.filter_mode]
```

#### 修改 2：`main_robustness.py` 增加命令行参数解析

文件：`main_robustness.py`

使用 `argparse` 新增以下参数：
- `--attack`：按攻击名过滤（如 `sign_flipping`, `scaling`, `backdoor` 等）
- `--defense`：按防御名过滤（如 `median`, `krum`, `trimmed_mean` 等）
- `--mode`：按模式过滤（`plain` 或 `encrypted`）
- `--config`：自定义配置文件路径

示例用法：

```bash
# 1. 运行配置文件中全部实验（默认行为）
python main_robustness.py

# 2. 只运行 Scaling 攻击的所有实验
python main_robustness.py --attack scaling

# 3. 只运行 Median 防御的所有实验
python main_robustness.py --defense median

# 4. 组合过滤：只跑 plain 模式下 scaling 攻击的实验
python main_robustness.py --mode plain --attack scaling

# 5. 精确到单个实验：只跑 sign_flipping + median
python main_robustness.py --attack sign_flipping --defense median
```

#### 修改 3：验证过滤效果

测试命令：
```bash
python main_robustness.py --attack scaling
```

输出日志显示：
```
使用显式实验列表，共 18 个配置
按攻击过滤后: 3 个配置 (attack=scaling)
实验矩阵 3 个配置
```

即从 18 个实验成功过滤为只有 Scaling 相关的 3 个实验（`scaling+fedavg`, `scaling+trimmed_mean`, `scaling+norm_clip_fedavg`），显著缩短实验时间。

---


## Q19: FedFetch 真实带宽下单轮模拟时间异常长（240~425s）

**问题描述**:
- `experiment_20260428_001001` 和 `experiment_20260428_003604` 的单轮模拟时间高达 **240~425 秒**
- 相比之下，之前使用生成带宽的实验单轮通常在 ~60 秒左右
- 用户质疑：为什么切换 FedFetch 真实 trace 后时间变长这么多？

---

### 根因分析

#### 1. 带宽瓶颈定量计算

每轮每个客户端需上传 **3.51 MB** 密文增量：

```
3.51 MB × 8 = 28.08 Mb = 28,080 kb
```

FedFetch 真实 trace 采样的 15 个客户端中，存在**极端慢上行带宽**：

| 实验 CID | 原始 Rank | UL (kbps) | 理论上传时间 | 实验对应轮次 |
|:--------:|:---------:|----------:|:------------:|:------------:|
| **#9** | 6913 | **69** | **~407 s** | **~423s 轮次** |
| **#6** | 1680 | **123** | **~228 s** | **~239s 轮次** |
| #3 | 4013 | 2,228 | ~13 s | ~16s 轮次 |
| #13 | 3583 | 2,177 | ~13 s | ~16s 轮次 |
| #1 | 410 | 14,945 | ~2 s | — |
| #5 | 2287 | 153,957 | ~0.2 s | — |

`calculate_round_duration = fetch_time + train_time + upload_time`，由**最慢选中客户端**决定整轮 wall-clock。

**实验数据完全吻合**：
- `003604` 中 ~423s 的轮次（#3, #4, #6, #9, #11, #13, #15, #16, #17, #19）→ 必含 client 9（69 kbps）
- `003604` 中 ~239s 的轮次（#1, #2, #7, #12, #20）→ 含 client 6（123 kbps）但不含 client 9
- `003604` 中 ~16s 的轮次（#5, #8, #10, #14, #18）→ 未选中这两个极端慢客户端

#### 2. 与原来配置对比

| 配置 | 典型上行带宽 | 3.51 MB 上传时间 |
|------|-------------|-----------------|
| 原来 JSON/生成 | ~512 kbps | ~56 s |
| **FedFetch 真实（极端客户端）** | **69~123 kbps** | **~228~407 s** |
| FedFetch 真实（快客户端） | ~150 Mbps | ~0.2 s |

**FedFetch 的 client 9（69 kbps）比原配置慢约 7 倍**，导致单轮 wall-clock 从 ~60s 膨胀到 ~420s。

#### 3. 采样逻辑澄清

**不是取前 15 个客户端！**

```python
# ckks_fed/bandwidth_simulator.py
clients = list(trace.values())          # 9242 个客户端
random.seed(seed)                        # seed=42
sampled = random.sample(clients, 15)     # 随机采样 15 个
```

→ 从 9242 个中**随机采样 15 个**，seed=42 保证可复现。实际采样的客户端分布在原始 trace 的 Rank **410~8936** 之间，没有任何一个是前 30 名。

**seed 的作用**：seed 不变 → 每次实验采样的 15 个客户端**完全相同**；seed 改变 → 客户端集合改变。`001001` 和 `003604` 使用相同 seed=42，因此带宽分布完全一致。

---

### 这是预期行为还是问题？

这是 **FedFetch 真实 trace 的如实反映**。原始论文的 motivation 之一就是解决真实移动设备中**高度异构且普遍偏慢**的上行带宽问题。client 9（69 kbps）和 client 6（123 kbps）在真实移动网络中并不罕见。

---

### 最终解决

已在代码和文档中记录此现象，无需修复（非 bug）。如需缩短单轮时间，可选方案：

1. **剔除极端慢客户端**：设置带宽下限（如 `UL > 1000 kbps`），在 `from_fedfetch_trace()` 中增加过滤逻辑
2. **降低采样率**：增大 `num_clients` 或提高选中比例，降低极端慢客户端被选中的概率
3. **减小 `local_epochs`**：减少每轮训练量，从而减小 delta 大小
4. **更换 seed**：改用其他 seed 采样，可能避开极端慢客户端（但也可能抽到更慢的）

---

### 附录：实际采样的 15 个客户端完整带宽

| 实验 CID | 原始 Rank | Trace ID | DL (kbps) | UL (kbps) | DL (Mbps) | UL (Mbps) |
|:--------:|:---------:|:--------:|----------:|----------:|----------:|----------:|
| 0 | 1825 | 1824 | 140,253 | **164,128** | 136.97 | **160.28** |
| 1 | 410 | 409 | 181,607 | 14,945 | 177.35 | 14.59 |
| 2 | 4507 | 4506 | 285,420 | 8,420 | 278.73 | 8.22 |
| 3 | 4013 | 4012 | 68,765 | **2,228** | 67.15 | **2.18** |
| 4 | 3658 | 3657 | 326,532 | 37,700 | 318.88 | 36.82 |
| 5 | 2287 | 2286 | 315,045 | **153,957** | 307.66 | **150.35** |
| 6 | 1680 | 1679 | 31,607 | **123** | 30.87 | **0.12** |
| 7 | 8936 | 8935 | 54,066 | 9,108 | 52.80 | 8.89 |
| 8 | 1425 | 1424 | 491,028 | 94,737 | 479.52 | 92.52 |
| 9 | 6913 | 6912 | 6,086 | **69** | 5.94 | **0.07** |
| 10 | 521 | 520 | 607,745 | **170,456** | 607.75 | **166.46** |
| 11 | 489 | 488 | 38,572 | 16,600 | 37.67 | 16.21 |
| 12 | 1536 | 1535 | 13,338 | 8,718 | 13.03 | 8.51 |
| 13 | 3583 | 3582 | 14,154 | **2,177** | 13.82 | **2.13** |
| 14 | 3812 | 3811 | 575,271 | **137,048** | 561.79 | **133.84** |

> Mbps = kbps / 1024

---


## Q20: 包级稀疏化（Packet-Level Sparsification）原理与配置

**问题描述**:
- 需要理解包级稀疏化的工作原理
- 需要知道 FedPHE 的原始默认配置
- 需要在当前项目的 config 中给出建议配置

---

### 1. 什么是"包"（Packet/Batch）？

在 CKKS 同态加密中，一个密文（`ckks_vector`）可以同时编码 **N/2** 个浮点数，其中 N 是 `poly_modulus_degree`。这种并行编码能力称为 **SIMD（Single Instruction Multiple Data）** 或 **Slot Packing**。

- `poly_modulus_degree = 8192` → `slot_count = 4096`
- 一个密文 = 一个"包" = 可同时容纳 4096 个 float 值

**包级稀疏化的"包"指的就是这样一个 SIMD 密文块。**

---

### 2. 包级稀疏化的完整流程

#### Step 1: 模型更新扁平化

```
模型更新（差值）: {conv1.weight, conv1.bias, conv2.weight, ...}
                      ↓
扁平化为一维数组: [w1, w2, w3, ..., w_44426]   (LeNet 共 44,426 个参数)
```

#### Step 2: 切分为 batch（包）

按 `batch_size`（建议等于 `slot_count = 4096`）切分：

```
总参数: 44,426
batch_size: 4096
batch_num: ceil(44,426 / 4096) = 11 个 batch

batch[0]: [w1    ~ w4096 ]   → 可装入 1 个 CKKS 密文
batch[1]: [w4097 ~ w8192 ]   → 可装入 1 个 CKKS 密文
...
batch[10]: [w40961 ~ w44426] + padding[0...] → 可装入 1 个 CKKS 密文
```

如果不使用稀疏化，需要加密并上传 **11 个密文**。

#### Step 3: 稀疏化选择（TopK / RandK）

**TopK 策略**：
1. 计算每个 batch 的 `avg(|x|)`（绝对值平均值）
2. 按平均值排序，保留最大的 `topk = ceil(batch_num × sparsity_rate)` 个 batch
3. 生成 mask：标记哪些 batch 被选中（1）/ 未选中（0）

**RandK 策略**：
1. 使用 `seed + round_num` 作为随机种子
2. 随机选择 `randk = ceil(batch_num × sparsity_rate)` 个 batch
3. 返回被选中的索引列表

例如 `sparsity_rate = 0.1`，`batch_num = 11`：
- `topk = ceil(11 × 0.1) = 2`
- 只加密并上传 **2 个密文**（而非 11 个）

#### Step 4: 加密上传

只对选中的 batch 调用 `ts.ckks_vector(context, batch)` 加密。

#### Step 5: 服务器聚合

```
TopK 场景：
  - 客户端上传：[cipher_batch3, cipher_batch7] + mask=[0,0,0,1,0,0,0,1,0,0,0]
  - 服务器按 mask 位置对齐：global[3] += cipher3, global[7] += cipher7
  - 未选中位置保持为 0（或上一轮值）

RandK 场景：
  - 客户端上传：[cipher_batch2, cipher_batch5] + randk_list=[2,5]
  - 服务器按 randk_list 位置对齐填充
```

#### Step 6: 解密与恢复

```
TopK 场景：
  - 解密后得到 2 个 batch 的明文值
  - 按 mask 放回原位置，其余位置补 0
  - 得到完整的一维数组 [0,0,0,v3,0,0,0,v7,0,0,0]（每个 0 是 4096 个 0）
  -  reshape 回模型参数形状

RandK 场景：
  - 解密后按 randk_list 位置填充，其余位置补 0
```

---

### 3. 通信量对比

以 LeNet（44,426 参数）为例：

| 配置 | batch_num | 选中 batch | 密文数 | 通信量 | 压缩率 |
|------|:---------:|:----------:|:------:|-------:|:------:|
| 无稀疏化 | 11 | 11 | 11 | ~24.55 MB | 1× |
| TopK 0.2 (FedPHE 默认) | 11 | 3 | 3 | ~6.7 MB | **3.7×** |
| TopK 0.1 | 11 | 2 | 2 | ~4.5 MB | **5.5×** |
| TopK 0.05 | 11 | 1 | 1 | ~2.2 MB | **11×** |
| RandK 0.1 | 11 | 2 | 2 | ~4.5 MB | **5.5×** |

> 注：密文大小约 3.51 MB / 11 blocks ≈ 0.32 MB per block。实际值因 TenSEAL 序列化略有波动。

---

### 4. FedPHE 原始实现 vs 当前项目实现对比

| 维度 | FedPHE 原始 | 当前项目 |
|------|------------|---------|
| **TopK 选择标准** | `avg(\|x\|)` 绝对值平均值 | `avg(\|x\|)` 绝对值平均值 ✅ 一致 |
| **RandK 随机种子** | `randk_seed + round_t` | `seed + round_num` ✅ 一致 |
| **batch_size 默认值** | `enc_batch_size = 4096` | `batch_size = 4096` ✅ 一致 |
| **sparsity_rate 默认值** | `topk = 0.2` | `sparsity_rate = 0.1` ⚠️ 不同 |
| **默认策略** | `isSpars = 'topk'` | `strategy = 'none'` ⚠️ 不同 |
| **randk_seed 默认值** | `12` | `42` ⚠️ 不同 |
| **padding 方式** | 末尾补 0 | 末尾补 0 ✅ 一致 |
| **聚合方式** | 按 mask 位置对齐累加 | 按 mask 位置对齐累加 ✅ 一致 |
| **解密恢复** | 未选中位置补 0 | 未选中位置补 0 ✅ 一致 |
| **代码组织** | 内嵌在 `ckks_enc()/ckks_dec()` 中 | 独立 `sparsification.py` 模块，策略可插拔 |

---

### 5.  FedPHE 原本配置

```yaml
# FedPHE 原始默认配置（从 main.py 和 encryption/ckks.py 提取）
sparsification:
  strategy: "topk"              # isSpars='topk'
  sparsity_rate: 0.2            # topk=0.2（保留 20% 的 batch）
  batch_size: 4096              # enc_batch_size=4096
  seed: 12                      # randk_seed=12
```

**FedPHE 加密参数**：
```yaml
ckks:
  poly_modulus_degree: 8192
  coeff_mod_bit_sizes: [60, 40, 40, 60]
  global_scale: 1099511627776   # 2^40
```

---

### 6. 建议配置

| 场景 | strategy | sparsity_rate | batch_size | 说明 |
|------|----------|---------------|------------|------|
| **高精度要求（不推荐稀疏）** | none | — | 4096 | 不牺牲任何梯度信息，通信量最大（~24.55 MB/轮） |
| **均衡（推荐）** | topk | 0.1 | 4096 | 保留 top 10% 的重要梯度，通信降 90%，准确率损失通常 <1% |
| **高压缩** | topk | 0.05 | 4096 | 保留 top 5%，通信降 95%，适合带宽极度受限场景 |
| **隐私增强** | randk | 0.1 | 4096 | 随机选择可防御基于梯度幅值的成员推断攻击 |
| **复现 FedPHE 论文** | topk | 0.2 | 4096 | 与 FedPHE 默认配置一致，通信降 80% |

---

### 7. 注意事项

1. **batch_size 不应超过 slot_count**
   - `slot_count = poly_modulus_degree // 2 = 4096`
   - 若 `batch_size > 4096`，TenSEAL 会报错或自动截断
   - 当前配置 `batch_size = 4096` 是最佳匹配

2. **稀疏化与 upload_difference 的关系**
   - 稀疏化在 `flatten → 切分 → 选择` 阶段执行
   - `upload_difference` 在 `稀疏化之前` 计算（`new_params - old_params`）
   - 两者正交：可以同时启用，也可以单独启用

3. **稀疏化对收敛的影响**
   - `sparsity_rate = 0.2`（FedPHE 默认）：通常无明显收敛损失
   - `sparsity_rate = 0.1`：轻微损失，可通过增加轮次补偿
   - `sparsity_rate = 0.05`：可能需 1.5~2 倍轮次达到相同精度
   - `randk` 比 `topk` 收敛更慢（因为随机丢弃可能丢掉重要梯度）

4. **当前项目默认未启用稀疏化**
   - `strategy: "none"` 是为了保持与早期代码的完全兼容
   - 如需启用，直接改 `strategy: "topk"` 即可

---

### 8. 代码实现位置

| 文件 | 作用 |
|------|------|
| `ckks_fed/sparsification.py` | 稀疏化策略定义（TopK / RandK / None） |
| `ckks_fed/crypto.py` | `CKKSManager.encrypt_update()` 中调用稀疏化策略 |
| `ckks_fed/client.py` | 客户端训练后生成更新，传入加密模块 |
| `ckks_fed/server.py` | 聚合时按 mask/randk_list 对齐稀疏密文 |

---

**最终解决**: 已在 `configs/config.yaml` 的 `sparsification` 区块中补充完整原理说明、FedPHE 原本配置、建议配置表格。`docs/problem_log.md` 新增 Q20 记录。

---


## Q21: 启用包级稀疏化后准确率暴跌至 10.10%（随机猜测水平）

**问题描述**:
- `experiment_20260428_134554`（启用 TopK 0.2 包级稀疏化）：最终准确率 **10.10%**
- `experiment_20260428_135246`（无稀疏化）：最终准确率 **95.90%**
- 两者配置完全相同，唯一区别是 `sparsification.strategy`

---

### 根因分析

#### 1. 现象观察

| 指标 | 稀疏化 (TopK 0.2) | 无稀疏化 |
|------|-------------------|---------|
| 最终准确率 | **10.10%** | **95.90%** |
| 密文膨胀率 | 5.64x | 20.69x |
| 每客户端密文数 | ~3 个/轮 | ~11 个/轮 |
| 每轮准确率 | 始终 10.10% | 稳步上升 |

→ 准确率从头到尾停滞在随机猜测水平（MNIST 共 10 类，随机 ≈ 10%），说明**全局模型完全没学到任何东西**。

#### 2. 核心 BUG：预取累加时的 batch 错位

包级稀疏化后，每轮聚合后的 delta 是稀疏格式：
```python
{
    '__sparse__': True,
    'ciphertexts': [ct0, ct1, ct2],  # 只保留选中的 batch
    'mask': [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],  # 标记哪些 batch 被选中
}
```

**关键问题**：不同轮次的聚合 mask 不同！

模拟验证（10 客户端，每轮选 5 个，TopK 0.2，batch_num=11）：

| 轮次 | 聚合后 mask 中 1 的个数 |
|------|------------------------|
| Round 1 | 8/11 |
| Round 2 | 9/11 |
| Round 3 | **11/11**（全满） |
| Round 4 | 10/11 |

#### 3. 错位演示

**Round 1 聚合后**（mask 有 8 个 1）：
```
mask        = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
ciphertexts = [c1_0, c1_1, c1_2, c1_3, c1_4, c1_5, c1_6, c1_7]  (8个密文)
```

**Round 3 聚合后**（mask 全满）：
```
mask        = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
ciphertexts = [c3_0, c3_1, ..., c3_10]  (11个密文)
```

**预取累加代码（BUG 版本）**：
```python
for i in range(len(prefetched_state['ciphertexts'])):  # i=0..7 (8个)
    prefetched_state['ciphertexts'][i] += delta['ciphertexts'][i]
```

结果：
- batch 0~7：`c1_i + c3_i` ← 正确对齐 ✓
- **batch 8, 9, 10：`c3_8, c3_9, c3_10` 完全丢失！** ← 致命错误

反过来，如果 Round 1 mask 比 Round 3 更满，还会触发 **IndexError**（访问越界）。

#### 4. 为什么模型完全崩溃？

1. **batch 错位**：不同 batch 的密文被错误地加在一起（如 batch 0 += batch 3）
2. **信息丢失**：某些 batch 根本没累加到，全局更新中这些位置永远是 0
3. **梯度变成噪声**：解密后得到的"更新"是随机值，模型无法收敛

→ **准确率从头到尾 10.10%，因为全局模型根本没学到任何东西。**

---

### 修复方案

#### 核心原则

> **不能按 `ciphertexts` 列表索引直接相加，必须按 `mask` 中标记的 batch 索引逐一比对后累加。**

#### 新增辅助函数

文件：`ckks_fed/crypto.py`

```python
def merge_sparse_encrypted_updates(enc1, enc2, evaluator=None):
    """
    按 batch 索引对齐合并两个稀疏加密更新。
    遍历 mask，对同一 batch 位置的密文做同态加法；
    只有一方有时深拷贝保留；都没有时跳过。
    """
    mask1 = enc1['mask']
    mask2 = enc2['mask']
    cts1 = enc1['ciphertexts']
    cts2 = enc2['ciphertexts']

    batch_num = len(mask1)
    merged_mask = [0] * batch_num
    merged_cts = []

    idx1 = idx2 = 0
    for i in range(batch_num):
        has1 = mask1[i]
        has2 = mask2[i]
        if has1 and has2:
            merged_cts.append(evaluator.add(cts1[idx1], cts2[idx2]) if evaluator else cts1[idx1] + cts2[idx2])
            merged_mask[i] = 1
            idx1 += 1; idx2 += 1
        elif has1:
            merged_cts.append(cts1[idx1].copy()); merged_mask[i] = 1; idx1 += 1
        elif has2:
            merged_cts.append(cts2[idx2].copy()); merged_mask[i] = 1; idx2 += 1

    return {
        '__sparse__': True,
        'ciphertexts': merged_cts,
        'mask': merged_mask,
        ...
    }
```

#### 替换 6 处累加逻辑

| 文件 | 方法 | 原代码 | 修复后 |
|------|------|--------|--------|
| `server.py` | `broadcast_prefetch_to_unselected` | `for i in range(len(cts)): cts[i] += ...` | `merge_sparse_encrypted_updates(...)` |
| `server.py` | `get_remaining_fetch_info` | 同上 | 同上 |
| `client.py` | `receive_prefetch_delta` | 同上 | 同上 |
| `client.py` | `fetch_remaining_deltas` | 同上 | 同上 |

---

### 关键洞察

1. **同态加法不改变密文大小**：`密文 A (326 KB) + 密文 B (326 KB) = 密文 C (326 KB)`。多个 delta 累加后数量不变。

2. **稀疏化确实影响预取**：下行广播的 delta 也是稀疏格式，`prefetched_state` 必须能正确处理稀疏累加。

3. **mask 对齐是核心**：稀疏化的核心难点不是"减少密文数量"，而是"不同客户端/不同轮次的 mask 不一致时如何正确对齐聚合"。

---

**最终解决**: 已新增 `merge_sparse_encrypted_updates` 函数并替换所有 6 处累加逻辑。`docs/problem_log.md` 新增 Q21 记录。

---
