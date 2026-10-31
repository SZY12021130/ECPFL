"""
SVHN 补充实验运行脚本
串行执行两个实验：
1. ECPFL-UN (union 模式)
2. ECPFL-TH-0.7 (threshold 0.7 模式)
"""

import os
import sys
import subprocess

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PYTHON = [r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "ours", "result_fix_pro")

# 实验配置列表
EXPERIMENTS = [
    {
        "name": "ECPFL-UN (SVHN Union)",
        "config": os.path.join(PROJECT_ROOT, "accuracy_baseline", "ours", "config_svhn_union.yaml"),
        "output": "20260623_svhn_union",
    },
    {
        "name": "ECPFL-TH-0.7 (SVHN Threshold 0.7)",
        "config": os.path.join(PROJECT_ROOT, "accuracy_baseline", "ours", "config_svhn_threshold_pct_0.7.yaml"),
        "output": "20260623_svhn_threshold_pct_0.7",
    },
]


def run_experiment(exp):
    """运行单个实验"""
    print("\n" + "=" * 70)
    print(f"开始实验: {exp['name']}")
    print(f"Config: {exp['config']}")
    print(f"Output: {exp['output']}")
    print("=" * 70 + "\n")

    if not os.path.exists(exp['config']):
        print(f"[ERROR] 配置文件不存在: {exp['config']}")
        return False

    cmd = PYTHON + [
        MAIN_PY,
        "--config", exp['config'],
        "--output-dir", OUTPUT_DIR,
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print(f"\n[OK] {exp['name']} 实验完成!")
        return True
    else:
        print(f"\n[FAIL] {exp['name']} 实验失败，退出码: {result.returncode}")
        return False


def main():
    print("=" * 70)
    print("SVHN 补充实验运行脚本")
    print(f"共 {len(EXPERIMENTS)} 个实验将串行执行")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success_count = 0
    for i, exp in enumerate(EXPERIMENTS, 1):
        print(f"\n[{i}/{len(EXPERIMENTS)}] ", end="")
        if run_experiment(exp):
            success_count += 1

    print("\n" + "=" * 70)
    print(f"实验完成: {success_count}/{len(EXPERIMENTS)}")
    print("=" * 70)

    return 0 if success_count == len(EXPERIMENTS) else 1


if __name__ == "__main__":
    sys.exit(main())
