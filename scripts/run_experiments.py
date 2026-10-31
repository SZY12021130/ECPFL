#!/usr/bin/env python3
"""
大规模批量实验运行脚本

按数据集-模型分类组织结果到 accuracy/ 目录：
  accuracy/{dataset}-{model}/experiment_{timestamp}/

实验矩阵:
  - MNIST + LeNet       : sparsity ∈ {0.1, 0.3, 0.5, 0.7, 0.9, none}
  - FMNIST + CNN_FMNIST : sparsity ∈ {0.1, 0.3, 0.5, 0.7, 0.9, none}
  - CIFAR-10 + ResNet20 : sparsity ∈ {0.5, 0.7, 0.9, none}

统一配置:
  - 50 clients, 50 rounds, 3 local epochs, sample rate 0.5
  - vote=union, local_completion=false
  - ptopk=true, decay_gamma=0.3, stale_gamma=0.5
  - OC=1.3, filter_low_bandwidth=true, min_bw=5120 kbps

Windows WDDM TDR 规避:
  - 串行执行，避免同时创建过多 CUDA 上下文
  - 50 clients（而非100）
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
    # (dataset, model_name, sparsity_list)
    ("mnist", "lenet", [0.1, 0.3, 0.5, 0.7, 0.9, None]),
    ("fashion_mnist", "cnn_fmnist", [0.1, 0.3, 0.5, 0.7, 0.9, None]),
    ("cifar10", "resnet20", [0.5, 0.7, 0.9, None]),
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
    "global_mask_vote": {
        "mode": "union",
    },
    "ckks": {
        "sparsification": {
            "strategy": "topk",      # 会被覆盖为 none 当 sparsity=None
            "sparsity_rate": 0.1,    # 会被覆盖
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
        "enable_prefetch": False,
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
    """递归更新字典"""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d


def build_config(base_path: Path, dataset: str, model: str, sparsity) -> dict:
    """读取基础配置并应用实验覆盖"""
    with open(base_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 应用统一覆盖
    deep_update(cfg, UNIFIED_OVERRIDES)

    # 数据集与模型
    cfg["data"]["dataset"] = dataset
    cfg["model"]["name"] = model

    # 稀疏率设置
    if sparsity is None:
        cfg["ckks"]["sparsification"]["strategy"] = "none"
        # PTopk 在 strategy=none 时自动不生效，无需显式关闭
    else:
        cfg["ckks"]["sparsification"]["strategy"] = "topk"
        cfg["ckks"]["sparsification"]["sparsity_rate"] = sparsity

    return cfg


def run_single_experiment(dataset: str, model: str, sparsity) -> bool:
    """运行单个实验配置，返回是否成功"""
    sparsity_label = "none" if sparsity is None else f"{sparsity}"
    exp_tag = f"[{dataset}/{model}] sparsity={sparsity_label}"

    print(f"\n{'=' * 70}")
    print(f"  STARTING {exp_tag}")
    print(f"{'=' * 70}")

    # 构建并保存临时配置
    cfg = build_config(BASE_CONFIG, dataset, model, sparsity)
    TMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = TMP_CONFIG_DIR / f"batch_{dataset}_{model}_sp{sparsity_label}.yaml"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # 输出目录：accuracy/{dataset}-{model}/
    # main.py 会在其下再创建 experiment_{timestamp}/
    output_dir = Path("accuracy_noprefetch") / f"{dataset}-{model}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        PYTHON, "main.py",
        "--config", str(tmp_path),
        "--output-dir", str(output_dir),
    ]

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
    total = sum(len(sparsities) for _, _, sparsities in EXPERIMENTS)
    completed = 0
    failed = 0

    print(f"\n[LAUNCH] Batch experiments start: {total} total")
    print(f"   Unified: 50 clients | 50 rounds | 3 epochs | sample=0.5 | OC=1.3")
    print(f"   Sparse: union vote | PTopk (decay=0.3, stale=0.5) | LC=off")

    for dataset, model, sparsities in EXPERIMENTS:
        for sparsity in sparsities:
            success = run_single_experiment(dataset, model, sparsity)
            completed += 1
            if not success:
                failed += 1
            print(f"\n[PROGRESS] {completed}/{total} done  (failed {failed})")
            # 短暂冷却，降低 GPU 连续负载
            time.sleep(5)

    print(f"\n{'=' * 70}")
    print(f"  批量实验结束: {completed} 完成 / {failed} 失败")
    print(f"{'=' * 70}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
