"""Run SVHN experiment for Ours baseline (50 rounds).

配置：SVHN 数据集，ResNet32 模型，本地稀疏率 0.5，服务器 topk_pct 0.7，
      结果保存至 accuracy_baseline/ours/result_fix_pro。
"""

import os
import sys
import subprocess

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PYTHON = [r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "accuracy_baseline", "ours", "config_svhn_sp0.5_topk0.7.yaml")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "ours", "result_fix_pro")


def main():
    print("=" * 70)
    print("Ours SVHN Experiment Runner (50 rounds)")
    print(f"Config: {CONFIG_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = PYTHON + [
        MAIN_PY,
        "--config", CONFIG_PATH,
        "--output-dir", OUTPUT_DIR,
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print("\n[OK] SVHN experiment completed successfully!")
        return 0
    else:
        print(f"\n[FAIL] SVHN experiment failed with exit code {result.returncode}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
