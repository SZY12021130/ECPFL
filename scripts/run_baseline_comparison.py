#!/usr/bin/env python3
"""
Baseline 对比实验一键总入口
Usage:
    python scripts/run_baseline_comparison.py --all
    python scripts/run_baseline_comparison.py --step generate
    python scripts/run_baseline_comparison.py --step run_ckks
    python scripts/run_baseline_comparison.py --step run_fedphe
    python scripts/run_baseline_comparison.py --step collect
    python scripts/run_baseline_comparison.py --step plot
"""

import argparse
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "baseline_comparison"
PYTHON = sys.executable


def run_cmd(cmd: list, cwd=None, desc: str = ""):
    print(f"\n{'='*60}")
    print(f"[STEP] {desc}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        print(f"[ERROR] 步骤失败: {desc}")
        return False
    print(f"[OK] 步骤完成: {desc}")
    return True


def step_generate():
    return run_cmd(
        [PYTHON, str(SCRIPTS_DIR / "generate_configs.py")],
        cwd=PROJECT_ROOT,
        desc="生成所有 baseline 配置文件"
    )


def step_run_ckks():
    config = PROJECT_ROOT / "tmp_configs" / "baseline_fedavg_ckks.yaml"
    return run_cmd(
        [PYTHON, str(PROJECT_ROOT / "main.py"), "--config", str(config)],
        cwd=PROJECT_ROOT,
        desc="运行 FedAvg+CKKS 实验"
    )


def step_run_fedphe():
    return run_cmd(
        [PYTHON, str(SCRIPTS_DIR / "run_fedphe_standalone.py")],
        cwd=PROJECT_ROOT,
        desc="运行 FedPHE standalone 实验"
    )


def step_collect():
    return run_cmd(
        [PYTHON, str(SCRIPTS_DIR / "collect_results.py")],
        cwd=PROJECT_ROOT,
        desc="收集跨项目结果"
    )


def step_plot():
    return run_cmd(
        [PYTHON, str(SCRIPTS_DIR / "plot_baselines.py")],
        cwd=PROJECT_ROOT,
        desc="绘制对比图表"
    )


def main():
    parser = argparse.ArgumentParser(description="Baseline 对比实验一键入口")
    parser.add_argument("--all", action="store_true", help="执行完整流程（生成配置→运行实验→收集→绘图）")
    parser.add_argument("--step", choices=["generate", "run_ckks", "run_fedphe", "collect", "plot"],
                        help="执行单个步骤")
    args = parser.parse_args()

    if not args.all and not args.step:
        parser.print_help()
        return 0

    steps = []
    if args.all:
        steps = ["generate", "run_ckks", "run_fedphe", "collect", "plot"]
    else:
        steps = [args.step]

    success = True
    for s in steps:
        if s == "generate":
            success = step_generate()
        elif s == "run_ckks":
            success = step_run_ckks()
        elif s == "run_fedphe":
            success = step_run_fedphe()
        elif s == "collect":
            success = step_collect()
        elif s == "plot":
            success = step_plot()

        if not success:
            print("\n[ABORT] 流程中断，请检查上方错误信息。")
            return 1

    print("\n[DONE] 全部完成！结果请查看 results/baseline_comparison/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
