#!/usr/bin/env python3
"""
顺序运行 MNIST / CIFAR-10 / SVHN / Fashion-MNIST 的 50 轮 adaptive voting 实验。
每个数据集包含 4 个策略：baseline(topk)、cosine、accuracy、consensus。

环境变量：
  KMP_DUPLICATE_LIB_OK=TRUE（避免 Windows OpenMP 运行时冲突）
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"

DATASETS = ["mnist", "cifar10", "svhn"]
STRATEGIES = ["baseline", "cosine", "accuracy", "consensus"]

PYTHON = sys.executable
MAIN = PROJECT_ROOT / "main.py"

# Windows MSYS/Git Bash 下需要设置环境变量
ENV = os.environ.copy()
ENV["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def run_one(dataset, strategy):
    cfg_path = ADAPTIVE_DIR / dataset / "configs" / f"config_{strategy}_{dataset}_50r.yaml"
    if not cfg_path.exists():
        print(f"[SKIP] 配置文件不存在: {cfg_path}")
        return False

    print(f"\n{'='*60}")
    print(f"[{dataset}] {strategy} | {cfg_path.relative_to(PROJECT_ROOT)}")
    print(f"{'='*60}")

    cmd = [PYTHON, str(MAIN), "--config", str(cfg_path)]
    # 使用 Popen 实时打印输出
    proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=ENV)
    proc.wait()
    if proc.returncode != 0:
        print(f"[ERROR] {dataset}/{strategy} 退出码 {proc.returncode}", file=sys.stderr)
        return False
    return True


def main():
    total = len(DATASETS) * len(STRATEGIES)
    completed = 0
    failed = []
    for dataset in DATASETS:
        for strategy in STRATEGIES:
            ok = run_one(dataset, strategy)
            completed += 1
            if not ok:
                failed.append((dataset, strategy))
            print(f"\n进度: {completed}/{total} 完成 | 失败: {len(failed)}")

    print("\n" + "=" * 60)
    print("全部运行结束")
    if failed:
        print("失败任务:")
        for d, s in failed:
            print(f"  - {d}/{s}")
    else:
        print("无失败任务")


if __name__ == "__main__":
    main()
