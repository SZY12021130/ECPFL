#!/usr/bin/env python3
"""
Run remaining fedavg+ckks baseline experiments sequentially:
1. FMNIST (cnn_fmnist)
2. CIFAR-10 (resnet20)
3. SVHN (mobilenetv2)
"""
import os
import sys
import subprocess

# Fix OpenMP crash on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# Limit CPU threads to keep background worker heartbeat alive
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["NUMEXPR_MAX_THREADS"] = "4"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "fedavg+ckks", "config")
RESULT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "fedavg+ckks", "result_fix_pro")
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")

EXPERIMENTS = [
    ("config_svhn.yaml", "svhn"),
]

def run_experiment(config_name, label):
    config_path = os.path.join(CONFIG_DIR, config_name)
    output_dir = RESULT_DIR
    
    print(f"\n{'='*60}")
    print(f"Starting: {label} ({config_name})")
    print(f"{'='*60}")
    
    cmd = [
        sys.executable, "-u",
        MAIN_PY,
        "--config", config_path,
        "--output-dir", output_dir,
    ]
    
    print(f"Command: {' '.join(cmd)}", flush=True)
    print(f"Working directory: {PROJECT_ROOT}", flush=True)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode == 0:
        print(f"\n[OK] {label} completed successfully!")
    else:
        print(f"\n[FAIL] {label} failed with exit code {result.returncode}")
    
    return result.returncode

if __name__ == "__main__":
    print("Starting fedavg+ckks baseline experiment (SVHN with resnet32)")
    print(f"Project root: {PROJECT_ROOT}")
    
    for config_name, label in EXPERIMENTS:
        exit_code = run_experiment(config_name, label)
        if exit_code != 0:
            print(f"\n[WARNING] Experiment {label} failed. Stopping sequence.")
            sys.exit(exit_code)
    
    print(f"\n{'='*60}")
    print("All experiments completed!")
    print(f"{'='*60}")
