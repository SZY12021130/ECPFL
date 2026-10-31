#!/usr/bin/env python3
"""
补跑提前终止的 Non-IID alpha 实验
针对 WDDM TDR 风险，加入串行冷却和轮数检查
"""

import yaml
import subprocess
import os
import sys
import time
from pathlib import Path

# 需要补跑的实验：(dataset, model, alpha, 原因)
RERUN_LIST = [
    ("fashion_mnist", "cnn_fmnist", 0.1, "FMNIST a=0.1 init failed"),
    ("cifar10", "resnet20", 0.3, "CIFAR-10 a=0.3 stopped at R23"),
    ("cifar10", "resnet20", 0.5, "CIFAR-10 a=0.5 stopped at R3"),
    ("cifar10", "resnet20", 0.7, "CIFAR-10 a=0.7 stopped at R21"),
    ("cifar10", "resnet20", 1.0, "CIFAR-10 a=1.0 stopped at R4"),
]

BASE_CONFIG = Path("configs/config.yaml")
TMP_CONFIG_DIR = Path("tmp_configs")
PYTHON = sys.executable

UNIFIED_OVERRIDES = {
    "system": {
        "num_rounds": 50,
        "num_epochs": 3,
        "num_clients": 50,
        "client_sampling_rate": 0.5,
        "run_plaintext_baseline": False,
    },
    "data": {"iid": False},
    "global_mask_vote": {"mode": "union"},
    "ckks": {
        "sparsification": {
            "strategy": "topk",
            "sparsity_rate": 0.5,
            "batch_size": 4096,
            "scoring_method": "l2_norm",
            "use_warmup_skip_sparse": False,
            "warmup_rounds": 2,
            "local_completion": {"enabled": False},
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
        "server_accumulator": {"enabled": False, "mode": "none"},
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


def count_rounds(log_path: Path) -> int:
    """从 experiment.log 统计已完成的轮数"""
    if not log_path.exists():
        return 0
    count = 0
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "轮次" in line and "done" in line:
                count += 1
    return count


def run_single(dataset: str, model: str, alpha: float, reason: str) -> bool:
    exp_tag = f"[{dataset}/{model}] alpha={alpha}"
    print(f"\n{'=' * 70}")
    print(f"  RERUN {exp_tag}")
    print(f"  Reason: {reason}")
    print(f"{'=' * 70}")

    cfg = build_config(BASE_CONFIG, dataset, model, alpha)
    TMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    alpha_label = str(alpha).replace(".", "_")
    tmp_path = TMP_CONFIG_DIR / f"niid_rerun_{dataset}_{model}_a{alpha_label}.yaml"
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
    total = len(RERUN_LIST)
    completed = 0
    failed = 0

    print(f"\n[LAUNCH] Rerun {total} failed/aborted Non-IID experiments")
    print(f"   Cooling: 10s between runs to mitigate WDDM TDR")
    print(f"   Max retries: 1 per experiment\n")

    for dataset, model, alpha, reason in RERUN_LIST:
        # 第一次尝试
        success = run_single(dataset, model, alpha, reason)
        if not success:
            # 检查是否因为轮数不足而需要重试
            log_dir = Path("accuracy_niid") / f"{dataset}-{model}"
            # 找最新生成的实验目录
            exp_dirs = sorted(log_dir.glob("experiment_*"), key=lambda p: p.stat().st_mtime)
            if exp_dirs:
                latest = exp_dirs[-1]
                rounds = count_rounds(latest / "experiment.log")
                print(f"   [CHECK] Latest experiment has {rounds}/50 rounds")
                if rounds < 50:
                    print(f"   [RETRY] Rerunning once more after 30s cooldown...")
                    time.sleep(30)
                    success = run_single(dataset, model, alpha, f"{reason} (retry)")

        completed += 1
        if not success:
            failed += 1
        print(f"\n[PROGRESS] {completed}/{total} done  (failed {failed})")

        # GPU 冷却
        if completed < total:
            print(f"   [COOLDOWN] GPU cooldown 10s...")
            time.sleep(10)

    print(f"\n{'=' * 70}")
    print(f"  Rerun done: {completed} complete / {failed} failed")
    print(f"{'=' * 70}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
