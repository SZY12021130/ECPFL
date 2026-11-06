#!/usr/bin/env python3
"""生成 Dirichlet(1) 准确率重跑配置（修正 IID 控制变量 bug）。
ESAFL: mnist/svhn（50x0.5，与基线一致；fmnist/cifar10 由 noniid sweep 的 a1 覆盖）
ECPFL: UN/TH/RK x mnist/svhn + UN/TH x fmnist/cifar10（RK fmnist/cifar10 由 sweep 覆盖）
"""
import re
from pathlib import Path

ROOT = Path("E:/GithubProjects/ckks_fed_robustness")

# ---------- ECPFL：复制 accuracy 配置，改 iid ----------
ECPFL_JOBS = ["mnist_un", "mnist_th", "mnist_rk",
              "svhn_un", "svhn_th", "svhn_rk",
              "fmnist_un", "fmnist_th",
              "cifar10_un", "cifar10_th"]
ecpfl_out = ROOT / "AAAAA_Rework/ECPFL/config/accuracy_diri1"
ecpfl_out.mkdir(parents=True, exist_ok=True)
for job in ECPFL_JOBS:
    src = ROOT / f"AAAAA_Rework/ECPFL/config/accuracy/{job}.yaml"
    text = src.read_text(encoding="utf-8")
    text = text.replace("  iid: true", "  iid: false   # Dirichlet(1) 与基线控制变量一致")
    dst = ecpfl_out / f"{job}.yaml"
    dst.write_text(text, encoding="utf-8")
    print(f"wrote {dst.name}")

# ---------- ESAFL：mnist/svhn，基于 noniid 模板（50x0.5） ----------
ESAFL_TMPL = """# ESAFL (PUREPY EP) Dirichlet(1) 准确率重跑：{dataset}、iid=false alpha=1
# 精度设置与 accuracy_n25_c1 一致（{model}、ζ={zeta}、TH-{theta}），参与 50x0.5=25（与基线一致）
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
  dataset: "{dataset}"
  data_dir: "./data"
  num_classes: 10
  iid: false
  alpha: 1

model:
  name: "{model}"
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
    sparsity_rate: {zeta}
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
  threshold_pct: {theta}
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
  results_dir: "AAAAA_Rework/ESAFL/result/accuracy_diri1"
  model_dir: "./models"
  save_interval: 5
"""

esafl_out = ROOT / "AAAAA_Rework/ESAFL/config/accuracy_diri1"
esafl_out.mkdir(parents=True, exist_ok=True)
for ds, model, zeta, theta in [("mnist", "lenet", 0.1, 0.1),
                               ("svhn", "resnet32", 0.5, 0.7)]:
    p = esafl_out / f"{ds}.yaml"
    p.write_text(ESAFL_TMPL.format(dataset=ds, model=model, zeta=zeta, theta=theta),
                 encoding="utf-8")
    print(f"wrote {p.name}")

print("done")
