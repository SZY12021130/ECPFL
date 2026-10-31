#!/usr/bin/env python3
"""
重新运行 ECPFL-TH 实验，将 sparsity_rate 从 0.5 收紧到 0.1，
以获得更合理的上传通信量。

模板配置：
  - MNIST: accuracy_baseline/ours/result_fix_pro/20260604_mnist_threshold_pct_0.1
  - FMNIST: accuracy_baseline/ours/result_fix_pro/20260604_fashion_mnist_threshold_pct_0.3

修改项：
  - ckks.sparsification.sparsity_rate = 0.1
  - ckks.ptopk.client_residual 保持 enabled=true, decay_gamma=0.3, stale_gamma=0.5
  - global_mask_vote 保持 threshold 模式及原有 threshold_pct
  - prefetch 保持启用

输出目录：
  - accuracy_baseline/ours/result_fix_pro/<原目录名>_sp0.1
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

import yaml

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MAIN_PY = PROJECT_ROOT / "main.py"
RESULT_DIR = PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro"

EXPERIMENTS = [
    {
        "name": "mnist_threshold_pct_0.1_sp0.1",
        "template": RESULT_DIR / "20260604_mnist_threshold_pct_0.1" / "config.yaml",
        "desc": "MNIST ECPFL-TH (sparsity=0.1, threshold=0.1)",
    },
    {
        "name": "fashion_mnist_threshold_pct_0.3_sp0.1",
        "template": RESULT_DIR / "20260604_fashion_mnist_threshold_pct_0.3" / "config.yaml",
        "desc": "FMNIST ECPFL-TH (sparsity=0.1, threshold=0.3)",
    },
    {
        "name": "mnist_threshold_pct_0.9_sp0.1",
        "template": RESULT_DIR / "20260604_mnist_threshold_pct_0.1" / "config.yaml",
        "desc": "MNIST ECPFL-TH (sparsity=0.1, threshold=0.9)",
        "override_threshold_pct": 0.9,
    },
]

NEW_SPARSITY = 0.1


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def run_single_experiment(exp: dict) -> bool:
    name = exp["name"]
    template_path = exp["template"]
    desc = exp["desc"]

    if not template_path.exists():
        print(f"[ERROR] 找不到模板配置: {template_path}")
        return False

    cfg = load_config(template_path)

    # 收紧本地稀疏率
    old_sparsity = cfg.get("ckks", {}).get("sparsification", {}).get("sparsity_rate", None)
    cfg["ckks"]["sparsification"]["sparsity_rate"] = NEW_SPARSITY

    # 可选：覆盖全局 threshold_pct
    old_threshold = cfg.get("global_mask_vote", {}).get("threshold_pct", None)
    new_threshold = exp.get("override_threshold_pct")
    if new_threshold is not None:
        cfg["global_mask_vote"]["threshold_pct"] = new_threshold

    # 保持 ckks.ptopk 与顶层 ptopk 同步（框架内部可能读取 ckks.ptopk）
    if "ptopk" in cfg.get("ckks", {}):
        cfg["ckks"]["ptopk"] = cfg.get("ptopk", cfg["ckks"]["ptopk"])

    # 固定输出目录
    output_subdir = RESULT_DIR / name
    cfg["output"]["results_dir"] = str(output_subdir.relative_to(PROJECT_ROOT).as_posix())

    # 保存修改后的配置
    output_subdir.mkdir(parents=True, exist_ok=True)
    config_path = output_subdir / "config.yaml"
    save_config(cfg, config_path)

    print("\n" + "=" * 70)
    print(f"[START] {name}")
    print(f"[DESC]  {desc}")
    print(f"[CONFIG] {config_path}")
    print(f"[CHANGE] sparsity_rate: {old_sparsity} -> {NEW_SPARSITY}")
    if new_threshold is not None:
        print(f"[CHANGE] threshold_pct: {old_threshold} -> {new_threshold}")
    print("=" * 70)

    cmd = [
        sys.executable, str(MAIN_PY),
        "--config", str(config_path),
        "--output-dir", str(output_subdir),
    ]

    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print(f"[SUCCESS] {name} 完成 -> {output_subdir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {name} 失败: {e}")
        return False


def main() -> int:
    if not MAIN_PY.exists():
        print(f"[ERROR] 找不到主程序: {MAIN_PY}")
        return 1

    print("=" * 70)
    print("ECPFL-TH 稀疏率收紧实验 (sparsity_rate=0.1)")
    print(f"结果目录: {RESULT_DIR}")
    print("=" * 70)

    results = []
    for exp in EXPERIMENTS:
        success = run_single_experiment(exp)
        results.append((exp["name"], success))

    print("\n" + "=" * 70)
    print("[SUMMARY]")
    print("=" * 70)
    for name, success in results:
        print(f"  {'[OK]' if success else '[FAIL]'} {name}")
    print("=" * 70)

    return 0 if all(s for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
