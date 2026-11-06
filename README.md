# ECPFL：加密包级联邦学习基线平台（CKKS 鲁棒性基准）

本仓库实现并基准对比 **5 种加密联邦学习方案**：本文方案 **ECPFL**（Encrypted Ciphertext-voting Pack-level FL）与四个基线 **FedAvg+CKKS / FedPHE / MASER / ESAFL**。所有方案统一在相同实验环境（数据划分、模型、轮数、带宽模拟、统计口径）下运行，输出精度（AC）与通信/时间指标（UV/FV/PV/TV/UT/DT/TT）。

---

## 一、方案架构

### 1.1 目录结构

```
ckks_fed_robustness/
├── main.py                     # 基线入口（FedAvg+CKKS / FedPHE / MASER / ESAFL）
├── main_ecpfl.py               # ECPFL 入口（投票共识 + ECP 队列 + 预取）
├── ckks_fed/
│   ├── crypto.py               # CKKSManager：TenSEAL 加解密/同态聚合/上传尺寸统计
│   ├── eshe.py                 # PurePyESHE：ESHE 纯 Python 复现（NTT 加速 R_Q 运算，
│   │                           #   ct = ⌊aᵗ·sᵢ + p̃·e + m⌋_Q，mask 经 PRPG 再生不上线）
│   ├── packing.py              # 打包策略：ESHEEPPacking（ESAFL 论文 §V-B2 EP 位打包）、
│   │                           #   Merged/CRTStack（TenSEAL 侧）、ESHEFixedPacking
│   ├── esafl_crypto.py         # ESAFL 协议适配器（SIMULATION/NATIVE/PUREPY 三模式）
│   ├── xmkckks_manager.py      # MASER 官方 xMK-CKKS Go 库绑定（真实多密钥）
│   ├── maser_mask.py           # MASER 参数级掩码/恢复
│   ├── client.py / server.py   # FL 客户端/服务器
│   └── models.py               # LeNet / CNN-FMNIST / ResNet-20 / ResNet-32
├── AAAAA_Rework/
│   ├── ECPFL/config/           # ECPFL 重跑配置（rerun_tt/、ablation/、dropout/）
│   ├── ESAFL/config/rerun_q20/ # ESAFL 修复重跑配置（logq0=20 + quant_clip）
│   └── docs/                   # 公式推导、口径对齐文档
├── accuracy_baseline/          # 基线历史结果与配置
│   ├── fedavg+ckks/config/     # config_{mnist,fmnist,cifar10,svhn}.yaml
│   ├── fedphe/config/
│   ├── maser/config/ 与 maser/config_mk/   # 旧 SK 模拟 / 新真实 xMK
│   └── esafl/
├── tools/
│   ├── run_tt_rerun.py         # ECPFL 12 组串行队列（3 变体 × 4 数据集）
│   ├── run_esafl_q20.py        # ESAFL 12 组串行队列（表三 4 组 + noniid 8 组）
│   └── run_maser_mk.py         # MASER 真实 xMK 队列（smoke → 4 数据集）
├── paper_src_v32/              # 论文源码与汇总表
└── MASER-main/                 # MASER 原版源码 + xmkckks_go2py/xmkckks.dll
```

### 1.2 五方案协议流程

| 方案 | 上行 | 服务器 | 下行 | 关键机制 |
|---|---|---|---|---|
| **FedAvg+CKKS** | 每客户端加密全量模型差值（J 个密文包） | TenSEAL 同态求和 | 广播聚合密文，客户端解密 | 标准 SK-CKKS FL；N=25 全参与 |
| **FedPHE**（结构复刻） | 仅加密 top-ζ 参数（batch 级 top-k 稀疏） | 同态求和 | 广播 + 解密 | ζ 稀疏减少密文**个数**；未实现成对掩码 |
| **MASER** | 参数级 top-50% 剪枝后 xMK-CKKS 加密 | 多密钥同态聚合 | 聚合密文广播 + 客户端部分解密份额 + 服务器下发明文模型 | 真实多密钥（官方 Go 库）；通信 = ①密文+②聚合密文+③份额+④明文 |
| **ESAFL** | ESHE 多密钥加密，EP 位打包（每客户端 J=⌈d/4096⌉ 个密文） | 密文直接求和（无交互） | 聚合密文下发，one-shot 解密 | mask 不上线（PRPG 再生）；单多项式 coeffs-only |
| **ECPFL（本文）** | 投票密文（1/客户端）+ 共识入选包的加密 | 密文投票 → ECP 滑动队列 → 聚合 | 只同步缺失包（FV），空闲期预取历史包（PV，不计入 TV） | **包级投票共识稀疏化**（UN/TH/RK 三规则）+ 预取 |

### 1.3 单密文线上大小（同机实测）

| 方案 | 密文结构 | 大小 | 计算 |
|---|---|---|---|
| FedAvg+CKKS / FedPHE | TenSEAL CKKS 双多项式 (c0,c1)，n=8192，模数链 [60,40,40,60] | **334,399 B** | `serialize()` 实测；理论 2×8192×200bit/8 |
| MASER (xMK) | 官方 Go 库双多项式+多密钥结构 | **1,795,776 B**（聚合密文/份额 13×） | `pickle.dumps()` 实测（N=25） |
| ESAFL / ECPFL | ESHE 单多项式 coeffs-only，n=4096，Q=61-bit | **31,232 B** | n×log₂Q/8 = 4096×61/8 |

---

## 二、运行操作

### 2.1 环境

```bash
# conda 环境（Windows + RTX 3050 验证通过）：Python + torch 2.9.1+cu126
pip install -r requirements.txt     # tenseal>=0.3.14, torch>=2.0, numpy, pyyaml ...
set KMP_DUPLICATE_LIB_OK=TRUE       # OpenMP 冲突规避（Windows 必需）
```

数据：`./data/` 下 MNIST / FashionMNIST / CIFAR-10 / SVHN（torchvision 自动下载）；非 IID 划分用 Dirichlet `data.alpha`。

### 2.2 运行单个方案

```bash
# ---- 四个基线（入口 main.py）----
python main.py --config accuracy_baseline/fedavg+ckks/config/config_mnist.yaml
python main.py --config accuracy_baseline/fedphe/config/config_mnist.yaml
python main.py --config accuracy_baseline/maser/config/config_mnist.yaml        # 旧 SK 模拟模式
python main.py --config accuracy_baseline/maser/config_mk/maser_mk_mnist.yaml   # 真实 xMK 多密钥
python main.py --config AAAAA_Rework/ESAFL/config/rerun_q20/esafl_mnist_a1.yaml # ESAFL (PUREPY ESHE)

# ---- ECPFL（入口 main_ecpfl.py）----
python main_ecpfl.py --config AAAAA_Rework/ECPFL/config/rerun_tt/ecpfl_mnist_un.yaml
# vote_rule: un(全票) / th(阈值 0.7) / rk(前 30%) → 对应 *_un/_th/_rk 配置
```

结果输出到配置 `output.results_dir`，含 `metrics.json`（通信/时间/精度逐轮明细）与 `report.md`（ECPFL 另有逐轮 K、掉线、预取明细）。

### 2.3 串行队列（推荐：实验必须逐个跑，避免 GPU/内存争用）

```bash
python tools/run_tt_rerun.py     # ECPFL 3 变体 × 4 数据集 → AAAAA_Rework/ECPFL/result/accuracy_diri1_tt
python tools/run_esafl_q20.py    # 等 ECPFL 队列完成后自动跑 ESAFL 12 组
python tools/run_maser_mk.py     # 等 ESAFL 完成后自动跑 MASER xMK（先 2 轮 smoke 验证）
```

队列脚本均带 `_progress.txt` 进度文件，支持链式等待（后者轮询前者的完成标记）。

---

## 三、每个基线的方案配置（关键参数）

以下均取自各方案**实际运行配置**（统一口径：N=25 客户端、T=50 轮、epochs=3、Adam lr=1e-3、batch=64、Dirichlet α=1、seed=42、MB=10⁶ 字节）。

### 3.1 FedAvg+CKKS（`accuracy_baseline/fedavg+ckks/config/`）

```yaml
ckks:
  poly_modulus_degree: 8192          # 环维度 → 4096 slots/密文
  coeff_mod_bit_sizes: [60, 40, 40, 60]   # 模数链 200-bit（SEAL λ=128 预算 218 内）
  global_scale: 1099511627776        # 2^40
  slot_packing: true                 # SIMD 打包
system: {num_clients: 25, client_sampling_rate: 1.0, upload_difference: true}
# 行为：全量上传差值 → 同态求和 → 广播 → 解密。单密文 334,399 B；J=⌈d/4096⌉
```

### 3.2 FedPHE（`accuracy_baseline/fedphe/config/`）

```yaml
ckks:                                # 同 FedAvg+CKKS 的 TenSEAL 参数
  poly_modulus_degree: 8192
  coeff_mod_bit_sizes: [60, 40, 40, 60]
  sparsification:
    strategy: topk                   # batch 级 top-k（l2_norm 打分，batch=4096）
    sparsity_rate: 0.1               # ζ：mnist=0.1 / fmnist=0.3 / cifar,svhn=0.5
system: {num_clients: 50, client_sampling_rate: 0.5}
# 行为：只加密被选中的 batch（密文个数 = ⌈ζJ⌉），加性聚合；未实现成对掩码（blinding_mask.enabled=false）
```

### 3.3 MASER（`accuracy_baseline/maser/config/` 旧 SK 模拟；`config_mk/` 真实 xMK）

```yaml
maser:
  enable: true
  mode: compressed                   # 服务器维护明文全局模型（multi-key 仅支持此模式）
  multi_key: true                    # ★ 真实 xMK-CKKS（旧跑为 false，仅协议级模拟）
  topk_ratio: 0.5                    # 参数级 top-50% 剪枝
  use_server_threshold: true
  voting_threshold: 0.5
# 真实 xMK 路径（main.py _ensure_xmkckks_manager + ckks_fed/xmkckks_manager.py）：
#   联合公钥聚合 → encrypt_for_client → 同态加法聚合 → 各客户端 partialDecrypt
#   → aggregate_pds 解码 → 明文模型下发
# 单密文 1,795,776 B；聚合密文/份额 = 13×（=(N+1)/2，N=25）；公钥分发一次性 16.3 MB
```

### 3.4 ESAFL（`AAAAA_Rework/ESAFL/config/rerun_q20/`，PUREPY 模式）

```yaml
esafl:
  enabled: true
  mode: PUREPY                       # 纯 Python ESHE 复现（ckks_fed/eshe.py）
  encoding: ep                       # 论文 §V-B2 EP 消息编码+多项式打包
  prpg_seed: 42                      # aᵗ 由 PRPG(t,B) 再生，mask 不上线
  logp: 56                           # 明文模数 p=2^56
  eta: 4                             # 噪声：中心二项分布参数
  num_clients: 25
  quant_clip: 1.0                    # ★ 全客户端共享量化 scale（密文求和语义必需）
packing:
  quant_bits: 20                     # logq0=20（20-bit 量化；旧 10-bit 导致 ResNet 精度崩坏）
# 打包推导：pad=⌈log₂25⌉+1=6 → slot_bits=26 → T=⌊56/26⌋=2（1 数据 slot）
#   → 单密文 4096 值、31,232 B；J=⌈d/4096⌉（mnist 11 / fmnist 10 / cifar 67 / svhn 115）
```

### 3.5 ECPFL（`AAAAA_Rework/ECPFL/config/rerun_tt/`，入口 `main_ecpfl.py`）

```yaml
ecpfl:
  n: 4096                            # 环维度（与 ESAFL 同环，Q=61-bit 双 NTT 素数）
  tau: 3                             # Lite 门限（F_S 为 τ 阶多项式）
  sparsity_rate: 0.5                 # ζ：mnist=0.1 / fmnist=0.3 / cifar,svhn=0.5
  vote_rule: un                      # un(≥1 票) / th(≥θ·|S|) / rk(前 ⌈θJ⌉ 名)
  vote_threshold: 0.7
  logp: 50
  delta_scale: 1048576
  eta: 4
  max_abs_x: 1.0                     # 量化：Δ=2^20，clip=1.0（与 ESAFL quant_clip 对齐）
  sampling:
    active_count: 25                 # 每轮 25/50 客户端活跃
    prefetch_rounds: 3               # 预采样提前 R 轮
    overcommit: 1.5                  # 候选池 ⌈βK⌉
  dropout_rate: 0                    # 掉线率（ablation 可调）
  gamma_d: 0.9                       # 式 12 残差双衰减
  gamma_s: 0.8
  prefetch:
    enabled: true                    # ECP 队列预取（PV 单独统计，不计入 TV）
# 单密文 31,232 B（= n×log₂Q/8）；每轮 UV = 25 投票密文 + 25×K 入选包
```

---

## 四、统计口径（表三/表四）

- **TV = UV + FV**（同步下行）；预取 PV 单列、不计入 TV
- UV/FV/PV/TV（MB=10⁶ 字节）与 UT/DT/TT（秒）均为 **50 轮累计**
- TT = Σₜ maxᵢ(本地训练 + 投票 + 加密 + UT + DT)，每轮取最慢客户端
- 详细的逐列计算方法与五方案实现保真度审计见 `paper_src_v32/汇总表_四数据集五方案.md`

---

## 附：历史模块

`main_robustness.py`（CKKS 攻击×防御鲁棒性平台，`configs/attack_config.yaml`）与 `main_samk.py`（SAMK 方案）为本仓库早期模块，保持可用但不在五方案基准流程内。
