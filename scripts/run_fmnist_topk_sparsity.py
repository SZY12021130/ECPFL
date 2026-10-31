#!/usr/bin/env python3
"""
FMNIST TopK 模式稀疏率批量实验
=============================

基于 configs/config.yaml，对 FMNIST 数据集在 TopK 模式下（topk_pct=0.3）
运行 sparsity_rate ∈ {0.1, 0.3, 0.5, 0.7, 0.9} 的五组实验。

输出目录命名：accuracy_topk_v2/{date}_fashion_mnist_sp{sparsity}_topk0.3/

Usage:
    python scripts/run_fmnist_topk_sparsity.py
    python scripts/run_fmnist_topk_sparsity.py --sparsities 0.1 0.3 0.7 0.9  # 跳过已存在的
"""

import yaml
import subprocess
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# 实验配置
# ---------------------------------------------------------------------------
BASE_CONFIG = Path("configs/config.yaml")
TMP_CONFIG_DIR = Path("tmp_configs")
PYTHON = sys.executable

DATASET = "fashion_mnist"
MODEL = "cnn_fmnist"
TOPK_PCT = 0.3
VOTE_MODE = "topk"
OUTPUT_ROOT = Path("accuracy_topk_v2")

# 统一参数覆盖（与之前 union 实验保持一致，仅修改 vote 模式）
UNIFIED_OVERRIDES = {
    "system": {
        "num_rounds": 50,
        "num_epochs": 3,
        "num_clients": 50,
        "client_sampling_rate": 0.5,
        "run_plaintext_baseline": False,
    },
    "data": {
        "dataset": DATASET,
    },
    "model": {
        "name": MODEL,
    },
    "global_mask_vote": {
        "mode": VOTE_MODE,
        "topk_pct": TOPK_PCT,
    },
    "ckks": {
        "sparsification": {
            "strategy": "topk",
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
    """递归更新字典"""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d


def build_config(sparsity: float) -> dict:
    """读取基础配置并应用实验覆盖"""
    with open(BASE_CONFIG, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 应用统一覆盖
    deep_update(cfg, UNIFIED_OVERRIDES)

    # 设置稀疏率
    cfg["ckks"]["sparsification"]["sparsity_rate"] = sparsity

    return cfg


def run_single_experiment(sparsity: float, skip_existing: bool = True) -> bool:
    """运行单个实验配置，返回是否成功"""
    sparsity_label = f"{sparsity}"

    date_str = datetime.now().strftime("%Y%m%d")
    exp_dir_name = f"{date_str}_fashion_mnist_sp{sparsity_label}_topk0.3"
    output_dir = OUTPUT_ROOT / exp_dir_name

    # 检查是否已存在（metrics.json 说明实验已完成）
    if skip_existing and (output_dir / "metrics.json").exists():
        print(f"\n[SKIP] sparsity={sparsity_label} already exists at {output_dir}")
        return True

    exp_tag = f"[FMNIST/topk_pct={TOPK_PCT}] sparsity={sparsity_label}"
    print(f"\n{'=' * 70}")
    print(f"  STARTING {exp_tag}")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 70}")

    # 构建并保存临时配置
    cfg = build_config(sparsity)
    TMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = TMP_CONFIG_DIR / f"fmnist_topk_sp{sparsity_label}.yaml"
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

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
    parser = argparse.ArgumentParser(description="FMNIST TopK mode sparsity sweep")
    parser.add_argument(
        "--sparsities",
        nargs="+",
        type=float,
        default=[0.1, 0.3, 0.5, 0.7, 0.9],
        help="Sparsity rates to sweep (default: 0.1 0.3 0.5 0.7 0.9)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-run even if experiment already exists",
    )
    args = parser.parse_args()

    total = len(args.sparsities)
    completed = 0
    failed = 0
    skipped = 0

    print(f"\n{'=' * 70}")
    print(f"  FMNIST TopK (topk_pct={TOPK_PCT}) Sparsity Sweep")
    print(f"  Sparsities: {args.sparsities}")
    print(f"  Skip existing: {not args.no_skip}")
    print(f"{'=' * 70}")

    # Windows OpenMP fix
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    for sparsity in args.sparsities:
        success = run_single_experiment(sparsity, skip_existing=not args.no_skip)
        if success is True:
            # 检查是跳过还是成功
            output_dir = OUTPUT_ROOT / f"{datetime.now().strftime('%Y%m%d')}_fashion_mnist_sp{sparsity}_topk0.3"
            if (output_dir / "metrics.json").exists() and not args.no_skip:
                skipped += 1
            else:
                completed += 1
        elif success is False:
            failed += 1

        print(f"\n[PROGRESS] {completed + skipped + failed}/{total}  "
              f"(completed={completed}, skipped={skipped}, failed={failed})")

        # 冷却
        time.sleep(5)

    print(f"\n{'=' * 70}")
    print(f"  批量实验结束: {completed} 完成 / {skipped} 跳过 / {failed} 失败")
    print(f"{'=' * 70}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
