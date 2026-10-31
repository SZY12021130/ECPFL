"""
比较 adaptive 投票实验与原始 ECPFL FMNIST 结果。

原始结果：accuracy_baseline/ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3
          （50 轮，取前 15 轮对比）
新结果：accuracy_baseline/adaptive/experiment_*_fashion_mnist* （15 轮）
"""
import json
import re
import os
from pathlib import Path
from collections import OrderedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"
BASELINE_DIR = PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260610_fashion_mnist_sp0.3_topk0.3"


def parse_report(report_path: Path):
    text = report_path.read_text(encoding="utf-8")

    def fpat(pattern, default=None):
        m = re.search(pattern, text)
        return float(m.group(1).replace(",", "")) if m else default

    def ipat(pattern, default=None):
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else default

    data = {}
    data["final_acc"] = fpat(r"Final Test Accuracy.*?\*\*([\d.]+)%")
    data["total_sim_time"] = fpat(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s")
    data["total_sim_comm_time"] = fpat(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s")

    up_m = re.search(r"Total Upload / 总上传量\s*\|\s*([\d.]+)\s*MB", text)
    data["up_mb"] = float(up_m.group(1)) if up_m else 0.0

    down_m = re.search(r"Total Download / 总下载量\s*\|\s*([\d.]+)\s*MB", text)
    data["down_mb"] = float(down_m.group(1)) if down_m else 0.0

    eff_m = re.search(r"Effective Download / 理论下载责任\s*\|\s*([\d.]+)\s*MB", text)
    data["effective_down_mb"] = float(eff_m.group(1)) if eff_m else data["down_mb"]

    return data


def parse_metrics_first_n(metrics_path: Path, n: int):
    """从 metrics.json 提取前 n 轮的 per-round 数据。"""
    if not metrics_path.exists():
        return None
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return {
        "test_acc": metrics.get("test_acc", [])[:n],
        "test_loss": metrics.get("test_loss", [])[:n],
        "upload_cost": metrics.get("upload_cost", [])[:n],
        "download_cost": metrics.get("download_cost", [])[:n],
        "total_round_time": metrics.get("total_round_time", [])[:n],
        "total_round_time_simulated": metrics.get("total_round_time_simulated", [])[:n],
    }


def find_adaptive_experiments():
    """查找 adaptive 目录下所有 FMNIST 实验。"""
    exps = OrderedDict()
    if not ADAPTIVE_DIR.exists():
        return exps
    for d in sorted(ADAPTIVE_DIR.iterdir()):
        if d.is_dir() and "fashion_mnist" in d.name:
            name = d.name
            exps[name] = d
    return exps


def summarize(exp_dir: Path, n: int = 15):
    report = parse_report(exp_dir / "report.md")
    metrics = parse_metrics_first_n(exp_dir / "metrics.json", n)
    if metrics is None:
        return None

    final_acc = metrics["test_acc"][-1] if metrics["test_acc"] else report["final_acc"]
    total_up = sum(metrics.get("upload_cost", [])) / (1024 ** 2)
    total_down = sum(metrics.get("download_cost", [])) / (1024 ** 2)
    total_time = sum(metrics.get("total_round_time_simulated", []) or metrics.get("total_round_time", []))

    return {
        "final_acc": final_acc,
        "avg_acc": sum(metrics["test_acc"]) / len(metrics["test_acc"]) if metrics["test_acc"] else 0.0,
        "up_mb": total_up,
        "down_mb": total_down,
        "total_mb": total_up + total_down,
        "total_time": total_time,
        "n_rounds": len(metrics["test_acc"]),
    }


def main():
    print("=" * 80)
    print("FMNIST 自适应投票实验结果对比（15 轮）")
    print("=" * 80)

    # 原始 ECPFL 基线（前 15 轮）
    baseline_metrics = parse_metrics_first_n(BASELINE_DIR / "metrics.json", 15)
    baseline_report = parse_report(BASELINE_DIR / "report.md")

    if baseline_metrics:
        baseline = {
            "final_acc": baseline_metrics["test_acc"][-1],
            "avg_acc": sum(baseline_metrics["test_acc"]) / len(baseline_metrics["test_acc"]),
            "up_mb": sum(baseline_metrics["upload_cost"]) / (1024 ** 2),
            "down_mb": sum(baseline_metrics["download_cost"]) / (1024 ** 2),
            "total_mb": (sum(baseline_metrics["upload_cost"]) + sum(baseline_metrics["download_cost"])) / (1024 ** 2),
            "total_time": sum(baseline_metrics.get("total_round_time_simulated", []) or baseline_metrics.get("total_round_time", [])),
            "n_rounds": 15,
        }
    else:
        # fallback 用 report 总量按比例估算
        baseline = {
            "final_acc": baseline_report["final_acc"],
            "avg_acc": baseline_report["final_acc"],
            "up_mb": baseline_report["up_mb"] * 15 / 50,
            "down_mb": baseline_report["down_mb"] * 15 / 50,
            "total_mb": (baseline_report["up_mb"] + baseline_report["down_mb"]) * 15 / 50,
            "total_time": baseline_report["total_sim_time"] * 15 / 50,
            "n_rounds": 15,
        }

    print(f"\n[Baseline] ECPFL-RK topk=0.3 (前 15 轮):")
    print(f"  Final Acc: {baseline['final_acc']:.2f}%")
    print(f"  Avg Acc:   {baseline['avg_acc']:.2f}%")
    print(f"  Upload:    {baseline['up_mb']:.2f} MB")
    print(f"  Download:  {baseline['down_mb']:.2f} MB")
    print(f"  Total:     {baseline['total_mb']:.2f} MB")
    print(f"  Total Time:{baseline['total_time']:.2f} s")

    # 自适应实验
    exps = find_adaptive_experiments()
    if not exps:
        print("\n[Warning] 未找到 adaptive 实验结果。")
        return

    print("\n" + "-" * 80)
    print("[Adaptive] 实验结果")
    print("-" * 80)

    for name, exp_dir in exps.items():
        summary = summarize(exp_dir, n=15)
        if summary is None:
            print(f"\n{name}: 无法解析 metrics.json")
            continue

        print(f"\n{name}:")
        print(f"  Final Acc: {summary['final_acc']:.2f}%  (Δ {summary['final_acc'] - baseline['final_acc']:+.2f}%)")
        print(f"  Avg Acc:   {summary['avg_acc']:.2f}%  (Δ {summary['avg_acc'] - baseline['avg_acc']:+.2f}%)")
        print(f"  Upload:    {summary['up_mb']:.2f} MB  ({summary['up_mb'] / baseline['up_mb']:.2f}x)")
        print(f"  Download:  {summary['down_mb']:.2f} MB  ({summary['down_mb'] / baseline['down_mb']:.2f}x)")
        print(f"  Total:     {summary['total_mb']:.2f} MB  ({summary['total_mb'] / baseline['total_mb']:.2f}x)")
        print(f"  Total Time:{summary['total_time']:.2f} s  ({summary['total_time'] / baseline['total_time']:.2f}x)")


if __name__ == "__main__":
    main()
