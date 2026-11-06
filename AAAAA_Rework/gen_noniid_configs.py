#!/usr/bin/env python3
"""生成 Non-IID (Dirichlet alpha) 实验配置。
ESAFL: cifar10 x 5 alpha（fmnist 5 个已存在）
ECPFL: fmnist_rk + cifar10_rk 各 5 alpha（基于 accuracy 配置，仅改 iid/alpha）
"""
from pathlib import Path

ROOT = Path("E:/GithubProjects/ckks_fed_robustness")
ALPHAS = [0.1, 0.5, 1.0, 5.0, 10.0]


def a_name(a):
    return {0.1: "a0.1", 0.5: "a0.5", 1.0: "a1", 5.0: "a5", 10.0: "a10"}[a]


# ---------------- ESAFL cifar10 noniid（模板 = 现有 noniid_fmnist，换 cifar10 精度设置） ----------------
ESAFL_CIFAR_TMPL = """# ESAFL (PUREPY EP) Non-IID 实验：cifar10、Dirichlet alpha={alpha}
# 与 accuracy_n25_c1/cifar10 同精度设置（resnet20、ζ=0.5、TH-0.7），参与模式 50x0.5=25（与 ECPFL 控制变量）
client_selection:
  strategy: "random"

system:
  num_clients: 50
  num_rounds: 50
  num_epochs: 3
  batch_size: 64
  learning_rate: 0.001
  device: "cuda"
  random_seed: 42
  run_plaintext_baseline: false
  client_sampling_rate: 0.5
  upload_difference: true
  optimizer:
    name: "adam"
    lr: 0.001
    momentum: 0.9
  lr_scheduler:
    enabled: false

data:
  dataset: "cifar10"
  data_dir: "./data"
  num_classes: 10
  iid: false
  alpha: {alpha}

model:
  name: "resnet20"
  hidden_dims: [256, 128]
  dropout: 0.2

ckks:
  poly_modulus_degree: 8192
  coeff_mod_bit_sizes: [60, 40, 40, 60]
  global_scale: 1099511627776
  slot_packing: true
  packing:
    strategy: "esafl"
    logq0: 10
    slots2: 2
    quant_bits: 10
    pad_bits: 0
  sparsification:
    strategy: "topk"
    sparsity_rate: 0.5
    batch_size: 4096
    seed: 42
    scoring_method: "l2_norm"
    use_warmup_skip_sparse: false
    warmup_rounds: 0
    local_completion:
      enabled: false
  ptopk:
    enable: false
    client_residual:
      enabled: false
      stale_gamma: 0.5
      decay_gamma: 0.3
      clip_tau: 0.0
    server_accumulator:
      enabled: false
      mode: "none"
      sync_interval: 1
      momentum_beta: 0.9

blinding_mask:
  enabled: false
  mask_range: 1.0
  compensation_mode: "auto"
  apply_mode: "post_topk"

global_mask_vote:
  mode: "threshold"
  threshold_pct: 0.7
  topk_count_k: 20
  topk_pct: 0.1

esafl:
  enabled: true
  mode: "PUREPY"
  encoding: "ep"
  prpg_seed: 42
  logp: 56
  eta: 4
  num_clients: 25

prefetch:
  enable_prefetch: false
  max_prefetch_round: 3

tee:
  enabled: false

bandwidth:
  fedfetch_trace_path: "fedfetch_bandwidth.pkl"
  base_dl_bw: 10240.0
  base_ul_bw: 10240.0
  variance: 0.3
  distribution: "lognormal"
  filter_low_bandwidth: true
  min_dl_bw_kbps: 5120
  min_ul_bw_kbps: 5120

output:
  results_dir: "AAAAA_Rework/ESAFL/result/noniid"
  model_dir: "./models"
  save_interval: 5
"""

esafl_dir = ROOT / "AAAAA_Rework/ESAFL/config/noniid"
for a in ALPHAS:
    p = esafl_dir / f"noniid_cifar10_{a_name(a)}.yaml"
    p.write_text(ESAFL_CIFAR_TMPL.format(alpha=a), encoding="utf-8")
    print(f"wrote {p.name}")

# ---------------- ECPFL RK noniid（模板 = accuracy/{fmnist,cifar10}_rk.yaml，仅改 iid/alpha） ----------------
ECPFL_TMPL = """system:
  num_clients: 50
  num_rounds: 50
  num_epochs: 3
  batch_size: 64
  learning_rate: 0.001
  device: cuda
  random_seed: 42
data:
  dataset: {dataset}
  data_dir: ./data
  num_classes: 10
  iid: false
  alpha: {alpha}
model:
  name: {model}
ecpfl:
  n: 4096
  tau: 3
  sparsity_rate: {zeta}
  vote_rule: rk
  vote_threshold: {theta}
  logp: 50
  delta_scale: 1048576
  eta: 4
  max_abs_x: 1.0
  sampling:
    active_count: 25
    prefetch_rounds: 3
    overcommit: 1.5
  dropout_rate: 0
  gamma_d: 0.9
  gamma_s: 0.8
  ablation:
    local_sparse: true
    residual_feedback: true
  prefetch:
    enabled: true
    bandwidth:
      base_dl_bw: 8192.0
      base_ul_bw: 4096.0
      distribution: uniform
      filter_low_bandwidth: false
      max_dl_bw_kbps: 8192.0
      max_ul_bw_kbps: 4096.0
      min_dl_bw_kbps: 5120
      min_ul_bw_kbps: 5120
"""

ecpfl_dir = ROOT / "AAAAA_Rework/ECPFL/config/noniid"
jobs = [("fmnist", "cnn_fmnist", 0.3, 0.3), ("cifar10", "resnet20", 0.5, 0.7)]
for ds, model, zeta, theta in jobs:
    for a in ALPHAS:
        p = ecpfl_dir / f"noniid_{ds}_rk_{a_name(a)}.yaml"
        p.write_text(ECPFL_TMPL.format(dataset=ds, model=model, alpha=a,
                                       zeta=zeta, theta=theta), encoding="utf-8")
        print(f"wrote {p.name}")

print("done")
