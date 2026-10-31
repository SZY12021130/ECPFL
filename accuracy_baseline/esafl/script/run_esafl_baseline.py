#!/usr/bin/env python3
"""
ESAFL Baseline Experiment Runner
配置：50客户端，50轮，alpha=1（轻度Non-IID），每轮随机选25个客户端
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/esafl/config")
RESULT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/esafl/result")


def run_experiment(config_name, label):
    config_path = os.path.join(CONFIG_DIR, config_name)
    output_dir = RESULT_DIR
    
    print(f"\n{'='*70}")
    print(f"[START] Running ESAFL baseline: {label}")
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
    print("ESAFL Baseline Experiment Runner")
    print("Configuration: 50 clients, 50 rounds, alpha=1, random selection")
    print("=" * 70)
    
    os.makedirs(RESULT_DIR, exist_ok=True)
    
    # 运行MNIST实验（与fedphe对比）
    success = run_experiment("config_mnist.yaml", "mnist")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    status = "[OK]" if success else "[FAIL]"
    print(f"  {status} mnist")
    print("=" * 70)
    
    if success:
        print("[OK] Experiment completed successfully!")
        return 0
    else:
        print("[WARNING] Experiment failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())