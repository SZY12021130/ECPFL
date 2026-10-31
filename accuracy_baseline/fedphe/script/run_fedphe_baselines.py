#!/usr/bin/env python3
"""
Batch runner for FedPHE baselines across 4 datasets.
Sequential execution: MNIST -> FMNIST -> CIFAR-10 -> SVHN
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/fedphe/config")
RESULT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/fedphe/result")

EXPERIMENTS = [
    ("config_mnist.yaml", "mnist"),
    ("config_fmnist.yaml", "fmnist"),
    ("config_cifar10.yaml", "cifar10"),
    ("config_svhn.yaml", "svhn"),
]


def run_experiment(config_name, label):
    config_path = os.path.join(CONFIG_DIR, config_name)
    output_dir = RESULT_DIR
    
    print(f"\n{'='*70}")
    print(f"[START] Running FedPHE baseline: {label}")
    print(f"{'='*70}")
    
    cmd = [
        sys.executable, MAIN_PY,
        "--config", config_path,
        "--output-dir", output_dir
    ]
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print(f"\n[OK] {label} completed successfully!")
        # Move results to timestamped subdir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        subdir = os.path.join(RESULT_DIR, f"experiment_{timestamp}_{label}")
        os.makedirs(subdir, exist_ok=True)
        for fname in ["config.yaml", "metrics.json", "experiment.log", "report.md"]:
            src = os.path.join(RESULT_DIR, fname)
            if os.path.exists(src):
                shutil.move(src, os.path.join(subdir, fname))
        print(f"[OK] Results moved to {subdir}")
        return True
    else:
        print(f"\n[FAIL] {label} failed with exit code {result.returncode}")
        return False


def main():
    print("=" * 70)
    print("FedPHE Baseline Batch Runner")
    print("Datasets: MNIST -> FMNIST -> CIFAR-10 -> SVHN")
    print("=" * 70)
    
    os.makedirs(RESULT_DIR, exist_ok=True)
    
    results = []
    for config_name, label in EXPERIMENTS:
        success = run_experiment(config_name, label)
        results.append((label, success))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for label, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {label}")
    
    all_ok = all(s for _, s in results)
    print("=" * 70)
    if all_ok:
        print("[OK] All experiments completed successfully!")
    else:
        print("[WARNING] Some experiments failed. Check logs above.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
