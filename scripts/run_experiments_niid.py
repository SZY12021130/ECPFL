#!/usr/bin/env python3
"""
Non-IID 浓度参数 alpha 批量实验运行脚本

在预取策略下，固定稀疏率=0.5，遍历不同 Non-IID 强度 alpha：
  alpha ∈ {0.1, 0.3, 0.5, 0.7, 0.9, 1.0}
  • α=0.1  极端 Non-IID（每客户端几乎只有 1~2 个类别）
  • α=0.5  中度 Non-IID（默认推荐）
  • α=1.0  轻度 Non-IID

数据集-模型:
  - MNIST + LeNet
  - Fashion-MNIST + CNN_FMNIST
  - CIFAR-10 + ResNet20

统一配置:
  - 50 clients, 50 rounds, 3 epochs, sample=0.5
  - sparsity=0.5, vote=union, PTopk (decay=0.3, stale=0.5)
  - prefetch=enabled, OC=1.3
"""

import yaml
import subprocess
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 实验矩阵
# ---------------------------------------------------------------------------
EXPERIMENTS = [
    # (dataset, model_name, alpha_list)
    ("mnist", "lenet", [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]),
    ("fashion_mnist", "cnn_fmnist", [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]),
    ("cifar10", "resnet20", [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]),
]

BASE_CONFIG = Path("configs/config.yaml")
TMP_CONFIG_DIR = Path("tmp_configs")
PYTHON = sys.executable

# ---------------------------------------------------------------------------
# 统一实验参数覆盖
# ---------------------------------------------------------------------------
UNIFIED_OVERRIDES = {
    "system": {
        "num_rounds": 50,
        "num_epochs": 3,
        "num_clients": 50,
        "client_sampling_rate": 0.5,
        "run_plaintext_baseline": False,
    },
    "data": {
        "iid": False,
    },
    "global_mask_vote": {
        "mode": "union",
    },
    "ckks": {
        "sparsification": {
            "strategy": "topk",
            "sparsity_rate": 0.5,
            "batch_size": 4096,
            "scoring_method": "l2_norm",
            "use_warmup_skip_sparse": False,
            "warmup_rounds": 2,
            "local_completion": {
                "enabled": False,
            },
        },
    },
    "ptopk": {
        "enable": True,
        "client_residual": {
            "enabled": True,
            "stale_gamma": 0.5,
            "decay_gamma": 0.3,
            "clip_tau": 0.0,
        },
        "server_accumulator": {
            "enabled": False,
            "mode": "none",
        },
    },
    "prefetch": {
        "enable_prefetch": True,
        "max_prefetch_round": 3,
        "warmup_round": 1,
        "scheduler_beta": 1.0,
        "overcommitment": 1.3,
    },
    "bandwidth": {
        "filter_low_bandwidth": True,
        "min_dl_bw_kbps": 5120,
        "min_ul_bw_kbps": 5120,
    },
}


def deep_update(d: dict, u: dict) -> dict:
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d


def build_config(base_path: Path, dataset: str, model: str, alpha: float) -> dict:
    with open(base_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    deep_update(cfg, UNIFIED_OVERRIDES)
    cfg["data"]["dataset"] = dataset
    cfg["model"]["name"] = model
    cfg["data"]["alpha"] = alpha
    return cfg


def run_single_experiment(dataset: str, model: str, alpha: float) -> bool:
    exp_tag = f"[{dataset}/{model}] alpha={alpha}"
    print(f"\n{'=' * 70}")
    print(f"  STARTING {exp_tag}")
    print(f"{'=' * 70}")

    cfg = build_config(BASE_CONFIG, dataset, model, alpha)
    TMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    alpha_label = str(alpha).replace(".", "_")
    tmp_path = TMP_CONFIG_DIR / f"niid_{dataset}_{model}_a{alpha_label}.yaml"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    output_dir = Path("accuracy_niid") / f"{dataset}-{model}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [PYTHON, "main.py", "--config", str(tmp_path), "--output-dir", str(output_dir)]

    start = time.time()
    try:
        result = subprocess.run(cmd, check=False)
        elapsed = time.time() - start
        if result.returncode == 0:
            print(f"\n[SUCCESS] {exp_tag}  ({elapsed/60:.1f} min)")
            return True
        else:
            print(f"\n[FAILED] {exp_tag}  code={result.returncode}  ({elapsed/60:.1f} min)")
            return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n[EXCEPTION] {exp_tag}: {e}  ({elapsed/60:.1f} min)")
        return False


def main():
    total = sum(len(alphas) for _, _, alphas in EXPERIMENTS)
    completed = 0
    failed = 0

    print(f"\n[LAUNCH] Non-IID alpha sweep: {total} total experiments")
    print(f"   Datasets: MNIST/LeNet | FMNIST/CNN_FMNIST | CIFAR-10/ResNet20")
    print(f"   Alpha values: 0.1, 0.3, 0.5, 0.7, 0.9, 1.0")
    print(f"   Fixed sparsity=0.5 | Prefetch=enabled | 50 clients | 50 rounds")

    for dataset, model, alphas in EXPERIMENTS:
        for alpha in alphas:
            success = run_single_experiment(dataset, model, alpha)
            completed += 1
            if not success:
                failed += 1
            print(f"\n[PROGRESS] {completed}/{total} done  (failed {failed})")
            time.sleep(5)

    print(f"\n{'=' * 70}")
    print(f"  Batch done: {completed} complete / {failed} failed")
    print(f"{'=' * 70}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
