# AAAAA_Rework — 5 方案实验工作区

本目录是 5 个联邦学习隐私方案（ECPFL / ESAFL / FedAvg_CKKS / FedPHE / MASER）
统一实验工作区：**配置与结果都保存在各方案自己的目录下**。
另含 SAMK（TDSC 2025）复现实验（`main_samk.py`，多密钥 BFV + Paillier + 插值）。

```
AAAAA_Rework/
├── SAMK/                      # SAMK 复现（main_samk.py）
│   ├── config/{synthetic,fl,dropout}/
│   ├── result/{synthetic,fl,dropout}/   # 含 summary.md / dropout_summary.{md,csv}
│   └── summarize.py           # 汇总各 run 的 json -> 总览表
├── ECPFL/                     # 本文方案（main_ecpfl.py，V17 定稿）
│   ├── config/                # scalability/ dropout/ noniid/ accuracy/ ablation/
│   └── result/                # 对应子目录 + complexity/
├── ESAFL/                     # 基线（main.py，esafl.mode=PUREPY EP）
│   ├── config/{accuracy,noniid}/
│   └── result/{accuracy,noniid}/
├── FedAvg_CKKS/               # 基线（main.py，配置源自 accuracy_baseline/fedavg+ckks）
│   ├── config/  result/
├── FedPHE/                    # 基线（源自 accuracy_baseline/fedphe）
│   ├── config/  result/
├── MASER/                     # 基线（源自 accuracy_baseline/maser）
│   ├── config/  result/
└── docs/
    └── ciphertext_stats.md    # 密文大小/密度公式计算表
```

## 运行命令

### ECPFL（每个配置头部注释含完整命令）

```bash
python main_ecpfl.py --config AAAAA_Rework/ECPFL/config/scalability/scalability_N100.yaml \
    --output-dir AAAAA_Rework/ECPFL/result/scalability
# 配置树批量运行（configs/ecpfl_v17/，独立于本目录）：
python scripts/run_ecpfl_v17_experiments.py --only table3
```

### SAMK（多密钥 BFV + Paillier，`main_samk.py`）

```bash
# 密码学流程自检（Paillier/BFV/插值/掉线语义，9 用例）
python test_samk_scheme.py

# synthetic：只跑密码学流程（随机更新，秒级）
python main_samk.py --config AAAAA_Rework/SAMK/config/synthetic/samk_synthetic.yaml \
    --output-dir AAAAA_Rework/SAMK/result/synthetic
# fl：MNIST 真实训练 + SAMK 加密聚合（全量参数）
python main_samk.py --config AAAAA_Rework/SAMK/config/fl/samk_mnist.yaml \
    --output-dir AAAAA_Rework/SAMK/result/fl
# 掉线率消融（dropout∈{0,0.1,0.2,0.3,0.4}）
python main_samk.py --config AAAAA_Rework/SAMK/config/dropout/samk_dropout_d20.yaml \
    --output-dir AAAAA_Rework/SAMK/result/dropout --tag d20
# 汇总
python AAAAA_Rework/SAMK/summarize.py
```

### ESAFL / 三个 CKKS 基线（main.py）

```bash
python main.py --config AAAAA_Rework/ESAFL/config/accuracy/mnist.yaml
python main.py --config AAAAA_Rework/FedAvg_CKKS/config/mnist.yaml
python main.py --config AAAAA_Rework/FedPHE/config/mnist.yaml
python main.py --config AAAAA_Rework/MASER/config/mnist.yaml
```

ESAFL Non-IID 模板（cifar10/svhn 同理，改 dataset/model/θ/ζ 即可）：

```bash
python main.py --config AAAAA_Rework/ESAFL/config/noniid/noniist_fmnist_a0.1.yaml
# 生成 cifar/svhn noniid：复制 accuracy/{cifar10,svhn}.yaml 改 data.iid=false 与 alpha
```

结果通过各配置 `output.results_dir` 落到本目录对应 `result/` 下。

### 计算复杂度基准（ECPFL 组件）

```bash
python scripts/benchmark_complexity.py                     # 完整：N∈{50,100,500,1000} ×5 reps
python scripts/benchmark_complexity.py --sizes 50 --reps 1 # 快速验证
# 输出 AAAAA_Rework/ECPFL/result/complexity/complexity.{csv,md}
```

## ECPFL 配置说明（config/ 子目录）

| 子目录 | 实验 | 变量 |
|---|---|---|
| `scalability/` | 扩展性 | N∈{50,100,500,1000}，K=N/2（N=1000 仅 10 轮，单机成本注释） |
| `dropout/` | 掉线率 | K=25，dropout∈{0,0.08,0.2,0.28,0.4} → 存活 ≈{25,23,20,18,15} |
| `noniid/` | Non-IID | Dirichlet α∈{0.1,0.5,1,5,10}（FMNIST，iid: false） |
| `accuracy/` | IID 稠密参照 | iid: true + 关闭 LS（local_sparse=false） |
| `ablation/` | ESP 组件消融 | ls/rf/prd/crd/rk 各关闭一个 + 仅 ESP（prefetch 关） |

公共参数：FMNIST+cnn_fmnist、τ=3、R=3、β=1.5、TH-0.3、ζ=0.1、γ_d=0.9/γ_s=0.8、
n=4096、Δ=2^20、p=2^50、eta=4、50 轮、cuda。

ESAFL 安全参数与 ECPFL 控制变量：PMD=8192（n=4096 同维度）、PUREPY EP、
logp=56、quant_bits=10（→pad=6,T=3）、eta=4、prpg_seed=42、num_clients=50、
采样率 0.5（esafl.num_clients=25 全参与）。

## SAMK 配置说明（config/ 子目录）

| 子目录 | 实验 | 变量 |
|---|---|---|
| `synthetic/` | 密码学流程 | 固定集合 K=8、dropout=0.25、d=1024、3 轮 |
| `fl/` | MNIST 真实训练 | 全量 12730 维（13 个 BFV 密文块）、mlp[16]、3 轮 |
| `dropout/` | 上传阶段掉线率 | dropout∈{0,0.1,0.2,0.3,0.4}、5 轮 |

公共参数：n=1024（Q≈2^61，双素数 CRT+NTT）、t=2^40、φ=2^16、Paillier 512 bit
（槽宽 65 bit，每密文 7 个采样点）、预采样 OC=1.5 提前 R=2 轮、粘性采样 decay=0.9。
密码学侧**不依赖第三方密码学库**：BFV 复用 `ckks_fed/eshe.py:RingContext`，
Paillier 与拉格朗日插值均为纯 Python + NumPy 自研（`ckks_fed/samk_crypto.py`）。
