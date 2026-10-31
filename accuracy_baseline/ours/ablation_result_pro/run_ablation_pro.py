#!/usr/bin/env python3
"""
串行执行 ESP 模块消融实验（SVHN, LS=0.1）。

6 组配置位于本目录的 configs/ 下，实验结果保存在本目录下。
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "configs"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
PYTHON = sys.executable

EXPERIMENTS = [
    {"name": "01_sparse_only",                "desc": "仅本地稀疏化 (sparsity=0.1) + union 投票"},
    {"name": "02_sparse_residual",            "desc": "稀疏化 + 残差补偿 + union 投票"},
    {"name": "03_sparse_residual_decay",      "desc": "稀疏化 + 残差补偿 + 单轮衰减 + union 投票"},
    {"name": "04_sparse_residual_decay_stale","desc": "稀疏化 + 残差补偿 + 单轮衰减 + 跨轮衰减 + union 投票"},
    {"name": "05_esp_full",                   "desc": "完整 ESP (含投票 RK=0.7)"},
    {"name": "06_no_sparse",                  "desc": "无稀疏化 baseline"},
]


def run_experiment(exp: dict) -> bool:
    config_path = CONFIG_DIR / f"config_{exp['name']}.yaml"
    output_dir = SCRIPT_DIR / exp["name"]
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"[START] {exp['name']}: {exp['desc']}")
    print(f"[CONFIG] {config_path}")
    print(f"[OUTPUT] {output_dir}")
    print("=" * 70)

    cmd = [
        PYTHON, str(MAIN_SCRIPT),
        "--config", str(config_path),
        "--output-dir", str(output_dir),
    ]
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print(f"[SUCCESS] {exp['name']} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {exp['name']} 失败: {e}")
        return False


def main():
    if not MAIN_SCRIPT.exists():
        raise FileNotFoundError(f"找不到主程序: {MAIN_SCRIPT}")

    results = []
    for exp in EXPERIMENTS:
        success = run_experiment(exp)
        results.append((exp["name"], success))

    print("\n" + "=" * 70)
    print("[SUMMARY] 消融实验执行汇总")
    print("=" * 70)
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {name:<35s} {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
