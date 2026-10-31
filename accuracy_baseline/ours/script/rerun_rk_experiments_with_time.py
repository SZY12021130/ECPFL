#!/usr/bin/env python3
"""
重新运行 4 个 ECPFL-RK 实验，使用当前代码生成带完整 UT/DT/TT 字段的 report。

原实验目录（仅复用其 config.yaml）:
    - accuracy_baseline/ours/result_fix_pro/20260605_mnist_topk_pct_0.1
    - accuracy_baseline/ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3
    - accuracy_baseline/ours/result_fix_pro/20260605_cifar10_topk_pct_0.7
    - accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7

新结果保存到:
    - accuracy_baseline/ours/result/<target_name>/

脚本行为:
    1. 读取原实验的 config.yaml。
    2. 调用 main.py --config <config> --output-dir <result_parent> 重新运行。
    3. 找到运行生成的 experiment_YYYYMMDD_HHMMSS_<dataset> 目录，
       重命名为固定的 target_name，便于后续脚本定位。
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
MAIN_PY = PROJECT_ROOT / "main.py"
RESULT_PARENT = PROJECT_ROOT / "accuracy_baseline" / "ours" / "result"

# 原实验目录 -> 新结果目录名
EXPERIMENTS = {
    "mnist_rk": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260605_mnist_topk_pct_0.1",
    "fashion_mnist_rk": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260610_fashion_mnist_sp0.3_topk0.3",
    "cifar10_rk": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260605_cifar10_topk_pct_0.7",
    "svhn_rk": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260622_svhn_sp0.5_topk0.7",
}

# 优先使用与原实验一致的 conda 环境；不存在则回退到当前 python
CONCRETE_ENV_PYTHON = Path(r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe")
if CONCRETE_ENV_PYTHON.exists():
    PYTHON_EXE = str(CONCRETE_ENV_PYTHON)
else:
    PYTHON_EXE = sys.executable


def find_generated_dir(parent: Path, dataset: str) -> Path:
    """main.py 会生成 experiment_YYYYMMDD_HHMMSS_<dataset> 目录，返回最新生成的那个。"""
    candidates = sorted(
        parent.glob(f"experiment_*_{dataset}"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"未在 {parent} 找到新生成的 experiment_*_{dataset} 目录")
    return candidates[0]


def run_one(target_name: str, src_dir: Path) -> dict:
    config_path = src_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml 不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        import yaml
        cfg = yaml.safe_load(f)
    dataset = cfg.get("data", {}).get("dataset", "unknown")

    out_dir = RESULT_PARENT / target_name
    if out_dir.exists():
        backup = RESULT_PARENT / f"{target_name}_backup_{int(os.path.getmtime(out_dir))}"
        print(f"[WARN] {out_dir} 已存在，备份到 {backup}")
        shutil.move(str(out_dir), str(backup))

    RESULT_PARENT.mkdir(parents=True, exist_ok=True)

    cmd = [
        PYTHON_EXE,
        str(MAIN_PY),
        "--config", str(config_path),
        "--output-dir", str(RESULT_PARENT),
    ]

    print("\n" + "=" * 80)
    print(f"[RUN] {target_name}")
    print(f"  config : {config_path}")
    print(f"  python : {PYTHON_EXE}")
    print(f"  cmd    : {' '.join(cmd)}")
    print("=" * 80)

    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"{target_name} 运行失败，返回码 {proc.returncode}")

    generated = find_generated_dir(RESULT_PARENT, dataset)
    print(f"[INFO] 生成目录: {generated.name} -> 重命名为 {target_name}")
    shutil.move(str(generated), str(out_dir))

    # 验证 report 中是否包含 UT/DT/TT
    report_path = out_dir / "report.md"
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    has_ut = "CT Upload Time" in report_text
    has_dt = "CT Download Time" in report_text
    has_tt = "Total Simulated Time" in report_text
    print(f"[VERIFY] UT={has_ut}, DT={has_dt}, TT={has_tt}")

    # 顺便把关键时间提取出来写入 summary
    summary = {
        "target_name": target_name,
        "source_dir": str(src_dir),
        "output_dir": str(out_dir),
        "has_ut": has_ut,
        "has_dt": has_dt,
        "has_tt": has_tt,
    }
    return summary


def main():
    print(f"[INFO] PROJECT_ROOT = {PROJECT_ROOT}")
    print(f"[INFO] RESULT_PARENT = {RESULT_PARENT}")
    print(f"[INFO] PYTHON_EXE = {PYTHON_EXE}")

    summaries = []
    for target_name, src_dir in EXPERIMENTS.items():
        try:
            summary = run_one(target_name, src_dir)
            summaries.append(summary)
        except Exception as e:
            print(f"[ERROR] {target_name} 失败: {e}", file=sys.stderr)
            summaries.append({
                "target_name": target_name,
                "source_dir": str(src_dir),
                "error": str(e),
            })
            # 继续下一个实验

    summary_path = RESULT_PARENT / "rerun_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] 汇总已保存: {summary_path}")

    all_ok = all(s.get("has_ut") and s.get("has_dt") and s.get("has_tt") for s in summaries)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
