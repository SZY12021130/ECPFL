# ECPFL (V17) 实现与论文公式对应文档

本文档对应 `scheme/V17-ecpfl.md`（论文定稿），说明参考实现
`ckks_fed/ecpfl_crypto.py`（密码学核心）与 `main_ecpfl.py`（Phase A-D 编排）
的逐项对应关系、通信轮数、实现差异、参数推导与复现命令。

## 1. 公式 → 代码对应表

| 论文公式 | 内容 | 实现（文件:行） |
|---|---|---|
| 式 (9) | ESP-Vote 掩码投票 `v̂_i = [a_0·λ_i z_i + p̃e + v_i(X)]_q` | `ECPFLClient.esp_vote` — ckks_fed/ecpfl_crypto.py:220 |
| 式 (10) | ESP-Tally 计票 `Σv̂ → [[·]_q]_p → ν_j` | `ECPFLServer.esp_tally` — :315；共识规则 UN/RK-θ/TH-θ：`ECPFLServer.consensus` — :325 |
| 式 (11) | ESP-Enc 有效密钥 `s̃_{i,j} = s_i + λ_i·Σ_{k∉S}s_{k,i} + λ_i b_j z_i` 与加密 `ct = [a_j·s̃ + p̃e + pt]_q`，`pt = round(ω_i·x·Δ)` | `ECPFLClient.effective_key` — :238；`ECPFLClient.esp_enc` — :247 |
| 式 (12) | 双衰减残差 `r_i ← γ_d·γ_s^{ℓ-1}·(x_i ⊙ (1−k))`，`ℓ = t − t_last,i` | main_ecpfl.py `run_experiment` 残差更新段（γ_d/γ_s 可配，默认 1 退化 Phase B） |
| 式 (13) | 同步聚合 `C_j = Σ_{i∈S} ct_{i,j}` | `ECPFLServer.esp_agg(cts)` — :342 |
| 式 (14) | ESP-Comp 纯密钥补偿 `δ_{i,j} = [a_j·κ_{i,j} + p̃ê]_q` | `ECPFLClient.esp_comp` — :260 |
| 式 (15) | 掉线聚合 `C_j = Σ_{i∈Ŝ}(ct_{i,j} + δ_{i,j})` | `ECPFLServer.esp_agg(cts, comp_cts)` — :342 |
| 式 (16) | ECP 跨轮累加 `C_pre = Σ_r C^(r)`，`A_pre = Σ_r a_j^(r)` | `ECPFLServer.ecp_accumulate` — :355 |
| 式 (17) | ECP 一步解密 `[[C_pre − A_pre·S]_q]_p / Δ` | `ECPFLServer.decrypt_prefetched` — :366（底层 `decrypt_poly` — :275）；单轮解密 `decrypt_pack` — :290 |
| 式 (D2.2/D2.3) | 环上 Shamir 拉格朗日恒等式 | `lagrange_coeffs` — :52；KGC 份额生成 `KGC.__init__`/分发 `KGC.distribute` — :119 |
| 式 (D1.3/D3.2) | 无回绕参数断言 | `KGC.assert_bounds` — :148（启动时强制检查） |

Phase 0 域分离 PRPG：`a_j^(t)=PRPG(σ_a, t·10^6+j)`、`a_0^(t)=PRPG(σ_b, t·10^6)` 见
`KGC.prpg_a/prpg_b/prpg_a0` — ckks_fed/ecpfl_crypto.py:135-145。

## 2. 通信轮数（每轮 t）

| 阶段 | 上行 | 下行 | 说明 |
|---|---|---|---|
| Phase 1 投票 | 每活跃客户端 1 个投票密文 | 服务器广播共识包集 K^(t)（标量列表） | 掩码 λ_i z_i 自归零，服务器无需密钥 |
| Phase 2 上传 | 每活跃客户端 \|K^(t)\| 个包密文 | — | 仅入选包 |
| Phase 3 掉线补偿 | 掉线时：每存活客户端再传 \|K^(t)\| 个 δ 密文（3 次上行合计） | 服务器广播 Ŝ | 无掉线为 2 次上行 |
| Phase 3 下发 | — | 每活跃客户端 \|K^(t)\| 个聚合包密文（掉线时 δ 与 ct 同包计数，合计口径 3+3） | 无掉线为 2 次下行 |
| Phase 4 ECP | — | 预采样池后台下载缺失 (r, C_j^(r))（记入 PV，不占训练关键路径） | 缓存命中则活跃客户端本轮 0 下载 |

**全程无 P2P 交互、无解密份额上传**：one-shot 解密 `[[C − aS]_q]_p` 由客户端
本地用全局公钥 S 完成，S 由 KGC 直接分发（单机模拟）。

## 3. 实现差异（vs 论文）

1. **打包容量**：论文按 n/2 参数打包（共轭对称）；实现每密文直接承载 n=4096 个
   定点系数（J = ⌈d/n⌉ 包，LeNet d=44426 → J=11）。这是 packing 口径差异，
   密码学结构（单环元素密文）一致。
2. **掉线为仿真随机**：D^(t) 由 `dropout_rate` 按二项分布抽取并强制 |Ŝ|≥τ；
   论文假设真实异步网络。补偿密码学路径（式 14/15）完全一致。
3. **KGC 单机模拟**：可信中心直接生成并分发 (s_i, S, σ_a, σ_b, {s_{k,i}}, z_i)，
   未模拟多服务器密钥仪式；Shamir 多项式系数"生成后即弃"。
4. **ECP-Fetch 为同步仿真**：后台预取在仿真中直接顺序执行，带宽配置
   （`prefetch.bandwidth`）仅用于计时估计，字节数恒记录到 PV。
5. **候选池**：预采样池 P^(t+R) 大小 ⌈βK⌉，大 N 下与早期池不相交；小 N 耗尽时
   回退为"排除上一轮活跃"采样（允许跨轮复用）。

## 4. 参数推导（无回绕数值检查）

启动断言 `KGC.assert_bounds(K, max_abs_x)` 强制两项（式 D1.3/D3.2）：

- 外层 mod p 无损：`K·max|m| < p/2`
- 内层 mod q 无回绕：`p̃·K·eta + K·max|m| < Q/2`

正式配置（N=50、K=25、n=4096、η=4、p=2^50、Δ=2^20、Q≈2^61）代入：

```
max|m| = ceil(ω_max·max_abs_x·Δ)+1 = 2^20+1   (ω_max=1, max_abs_x=1)
K·max|m|            = 25·(2^20+1) ≈ 2^24.6  < p/2 = 2^49   ✓
p̃·K·η + K·max|m|   = 2^50·100 + 2^24.6
                    ≈ 2^56.64                < Q/2 ≈ 2^60  ✓
```

ECP 跨轮累加 R=3 轮时噪声项放大 ≤ R 倍：2^56.64·3 ≈ 2^58.2 < 2^60，仍有
~4× 余量（assert_bounds 按单轮 K 校验，跨轮场景测试
`test_ecp_cross_round_accumulation` 覆盖）。

## 5. 复现命令

```bash
# 单元 + 编排测试（38 passed, 2 skipped）
python -m pytest tests/test_ecpfl.py tests/test_eshe_purepy.py -q

# Phase C+D 冒烟（3 轮，N=8/K=4/R=2/dropout=0.3，预取开/关对照）
python main_ecpfl.py --config configs/test_ecpfl_phases_cd.yaml --output-dir out/cd_on
python main_ecpfl.py --config configs/test_ecpfl_phases_c.yaml  --output-dir out/c_only

# 正式实验（50 轮，MNIST+LeNet，N=50/K=25/TH-0.5/dropout=0.2/γ_d=0.9/γ_s=0.8）
python main_ecpfl.py --config configs/config_ecpfl.yaml \
    --output-dir accuracy_baseline/ours/ecpfl_v17/
```

输出：`ecpfl_results.json`（每轮 t/K/掉线数/精度/↑/↓/预取/缓存命中/sync 包数 +
TV=Σ(上行+预取)、PV=总预取、每客户端预取字节）与 `ecpfl_results.md`（表格）。

### 5.1 论文实验配置树（configs/ecpfl_v17/）

| 目录 | 对应论文 | 配置 |
|---|---|---|
| `table3/{mnist,fmnist,cifar10,svhn}_{un,th,rk}.yaml` | **Table III** 主对比（12 个） | MNIST(lenet,θ=0.1,ζ=0.1)、FMNIST(cnn_fmnist,θ=0.3,ζ=0.1)、CIFAR-10(resnet20,θ=0.7,ζ=0.5)、SVHN(resnet32,θ=0.7,ζ=0.5)；N=50/K=25/τ=3/R=3/β=1.5、dropout=0.2、γ_d=0.9/γ_s=0.8、50 轮、cuda |
| `table2/cifar10_N{100,500,1000}.yaml` | **Table II** 扩展性 | CIFAR-10(resnet20,TH-0.5,ζ=0.5)，N∈{100,500,1000}、K=N/2，其余同上（N=50 见 configs/config_ecpfl.yaml） |
| `ablation/svhn_step{0..5}.yaml` | **Table VI** ESP 组件消融（SVHN） | 逐级开启 LS→RF→PRD→CRD→RK；step0=全关（稠密上传/无残差/全参与/同步/TH），step5=完整版（RK 共识） |
| `sensitivity/mnist_dropout{0,0.1,0.3}.yaml` | dropout 敏感性（0.2 已在 table3） | MNIST(lenet,TH-0.1,ζ=0.1) |
| `sensitivity/noprefetch_mnist_th.yaml` | 预取开/关对照 | 同 MNIST-TH，prefetch.enabled=false |

消融开关（`ecpfl.ablation.*`，默认 true=论文完整版，均在 main_ecpfl.py `run_experiment` 内实现）：

| 键 | 组件 | 关闭时的对照路径 |
|---|---|---|
| `local_sparse` | LS 本地稀疏投票 | 跳过 ESP-Vote/Tally，K^(t)=全部 J 包稠密上传 |
| `residual_feedback` | RF 残差反馈 | x_i = Δw_i，残差不累积（式 12 不生效） |
| `partial_participation` | PRD 部分参与 | 全参与 S=[N]（K_active=N） |
| `dropout_comp` | CRD 掉线补偿 | 强制同步路径 D=∅（dropout_rate 置 0） |
| `vote_rule: "rk"` | RK 排序共识 | 关闭时用 TH-θ（steps 0-4） |

### 5.2 批量运行

```bash
python scripts/run_ecpfl_v17_experiments.py                # 全部 25 个实验顺序执行
python scripts/run_ecpfl_v17_experiments.py --only table3   # 只跑 Table III（可逗号分隔）
python scripts/run_ecpfl_v17_experiments.py --dry-run       # 只打印命令
```

每个实验独立 log（`results/ecpfl_v17/logs/<相对路径>.log`），失败继续下一个；
结束后汇总 `results/ecpfl_v17/summary.csv`
（config/dataset/model/variant/status/acc/TV_MB/PV_MB/TT_s）。

基线方法（FedAvg+CKKS、FedPHE、ESAFL、MASER）的配置在
`accuracy_baseline/{fedavg+ckks,fedphe,esafl,maser}/config/`，用 `main.py` 运行，不在本脚本范围。

