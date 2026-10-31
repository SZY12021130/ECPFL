#!/usr/bin/env python3
"""
Fashion-MNIST 预取窗口实验运行脚本

基于最优 Fashion-MNIST 配置，固定其他参数，只改变 prefetch.max_prefetch_round (R)。
预取窗口取值: 1, 3, 5, 7, 9

用法:
  python scripts/run_window_experiments.py [--dry-run]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# Fix: OpenMP duplicate library error on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
BASELINE_CONFIG = PROJECT_ROOT / "accuracy" / "fashion_mnist-cnn_fmnist" / "experiment_20260529_130043" / "config.yaml"
OUTPUT_ROOT = PROJECT_ROOT / "accuracy_window" / "fashion_mnist-cnn_fmnist"
TMP_CONFIG_DIR = PROJECT_ROOT / "tmp_configs"

# 预取窗口取值
WINDOW_VALUES = [1, 3, 5, 7, 9]

_parser = argparse.ArgumentParser()
_parser.add_argument("--dry-run", action="store_true", help="只生成配置文件，不运行实验")
_parser.add_argument("--skip-existing", action="store_true", help="跳过已存在的实验")
_args = _parser.parse_args()


def load_baseline_config() -> dict:
    """加载最优 Fashion-MNIST baseline 配置"""
    if not BASELINE_CONFIG.exists():
        print(f"Error: Baseline config not found: {BASELINE_CONFIG}")
        print("Please ensure the Fashion-MNIST optimal experiment exists.")
        sys.exit(1)

    with open(BASELINE_CONFIG, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def create_window_config(base_config: dict, window: int) -> dict:
    """基于 baseline 配置创建指定预取窗口的实验配置"""
    config = dict(base_config)
    # 修改预取窗口
    if "prefetch" not in config:
        config["prefetch"] = {}
    config["prefetch"]["max_prefetch_round"] = window
    return config


def run_experiment(config_path: Path, output_dir: Path) -> bool:
    """运行单个实验"""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--config", str(config_path),
        "--output-dir", str(output_dir),
    ]
    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, capture_output=False, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error: Experiment failed with exit code {e.returncode}")
        return False


def main():
    print("=" * 70)
    print(" Fashion-MNIST 预取窗口实验")
    print("=" * 70)
    print(f"\nBaseline config: {BASELINE_CONFIG}")
    print(f"Output root:     {OUTPUT_ROOT}")
    print(f"Window values:   {WINDOW_VALUES}")
    print(f"Dry run:         {_args.dry_run}")
    print(f"Skip existing:   {_args.skip_existing}")

    # 加载 baseline 配置
    base_config = load_baseline_config()
    print(f"\nLoaded baseline config:")
    print(f"  dataset:   {base_config.get('data', {}).get('dataset')}")
    print(f"  model:     {base_config.get('model', {}).get('name')}")
    print(f"  sparsity:  {base_config.get('ckks', {}).get('sparsification', {}).get('sparsity_rate')}")
    print(f"  prefetch:  max_prefetch_round={base_config.get('prefetch', {}).get('max_prefetch_round')}")

    # 确保目录存在
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    TMP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 运行每个窗口的实验
    for window in WINDOW_VALUES:
        exp_name = f"experiment_R{window}"
        exp_dir = OUTPUT_ROOT / exp_name
        config_path = TMP_CONFIG_DIR / f"window_fmnist_R{window}.yaml"

        print(f"\n[Window R={window}] {exp_name}")

        # 检查是否已存在
        if _args.skip_existing and (exp_dir / "metrics.json").exists():
            print(f"  Skipped: experiment already exists at {exp_dir}")
            continue

        # 生成配置
        config = create_window_config(base_config, window)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"  Config saved: {config_path}")

        if _args.dry_run:
            print(f"  (Dry run, skipping execution)")
            continue

        # 运行实验
        exp_dir.mkdir(parents=True, exist_ok=True)
        success = run_experiment(config_path, exp_dir)
        if not success:
            print(f"  Warning: R={window} experiment failed, continuing...")

    print(f"\n{'=' * 70}")
    print(" All experiments completed!")
    print(f" Results saved to: {OUTPUT_ROOT}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
