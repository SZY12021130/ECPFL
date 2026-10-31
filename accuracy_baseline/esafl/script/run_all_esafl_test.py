"""Run all ESAFL baseline experiments sequentially (one dataset at a time) in GPU conda env.

配置：四个数据集（MNIST / FashionMNIST / CIFAR10 / SVHN）各跑 50 轮，
      正式实验，结果保存至 accuracy_baseline/esafl/result_fix_pro。

说明：main.py 会自动在 results_dir 下按时间戳创建 experiment_YYYYMMDD_HHMMSS_<dataset> 子目录，
      本脚本只负责按顺序调用，不再额外移动文件，避免产生空记录。
"""

import os
import sys
import subprocess

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# GPU conda environment Python (concrete-env)
PYTHON = [r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "esafl", "config")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "esafl", "result_fix_pro")

baselines = [
    {"name": "ESAFL-Sim", "config": "config_mnist.yaml", "dataset": "mnist"},
    {"name": "ESAFL-Sim", "config": "config_fashionmnist.yaml", "dataset": "fashionmnist"},
    {"name": "ESAFL-Sim", "config": "config_cifar10.yaml", "dataset": "cifar10"},
    {"name": "ESAFL-Sim", "config": "config_svhn.yaml", "dataset": "svhn"},
]


def run_experiment(config_name, label):
    config_path = os.path.join(CONFIG_DIR, config_name)

    print("\n" + "=" * 70)
    print(f"[START] Running ESAFL baseline: {label}")
    print(f"[CONFIG] {config_path}")
    print(f"[OUTPUT] {OUTPUT_DIR}")
    print("=" * 70)

    cmd = PYTHON + [
        MAIN_PY,
        "--config", config_path,
        "--output-dir", OUTPUT_DIR,
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print(f"\n[OK] {label} completed successfully!")
        return True
    else:
        print(f"\n[FAIL] {label} failed with exit code {result.returncode}")
        return False


def main():
    print("=" * 70)
    print("ESAFL Multi-Dataset Formal Runner (50 rounds each)")
    print("Output: accuracy_baseline/esafl/result_fix_pro")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    status_list = []

    for item in baselines:
        success = run_experiment(item["config"], item["dataset"])
        status_list.append((item["dataset"], success))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for dataset, success in status_list:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {dataset}")
    print("=" * 70)

    all_ok = all(success for _, success in status_list)
    if all_ok:
        print("[OK] All experiments completed successfully!")
        return 0
    else:
        print("[WARNING] Some experiments failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
