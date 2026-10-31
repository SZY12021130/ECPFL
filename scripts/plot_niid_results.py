#!/usr/bin/env python3
"""
Non-IID alpha 实验结果画图脚本
扫描 accuracy_niid/ 目录，按数据集分组绘制 alpha-准确率关系图
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    print("Error: matplotlib not installed. Run: pip install matplotlib")
    sys.exit(1)

import numpy as np

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
INPUT_DIR = Path("accuracy_niid")
OUTPUT_DIR = Path("accuracy_niid/plots")
DPI = 300
FIGSIZE = (8, 5)

COLORS = {
    "mnist-lenet": "#1f77b4",
    "fashion_mnist-cnn_fmnist": "#ff7f0e",
    "cifar10-resnet20": "#2ca02c",
}

LABELS = {
    "mnist-lenet": "MNIST + LeNet",
    "fashion_mnist-cnn_fmnist": "Fashion-MNIST + CNN",
    "cifar10-resnet20": "CIFAR-10 + ResNet20",
}

MARKERS = {"mnist-lenet": "o", "fashion_mnist-cnn_fmnist": "s", "cifar10-resnet20": "^"}

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def extract_alpha_from_log(log_path: Path) -> Optional[float]:
    """从 experiment.log 中提取 alpha 值"""
    if not log_path.exists():
        return None
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # 日志中使用希腊字母 alpha 或英文字母 alpha
            match = re.search(r"Non-IID partition \((?:\u03b1|alpha)=([0-9.]+)\)", line)
            if match:
                return float(match.group(1))
            match = re.search(r"alpha=([0-9.]+)", line)
            if match:
                return float(match.group(1))
    return None


def extract_final_acc_from_log(log_path: Path) -> Optional[float]:
    """从 experiment.log 中提取最终测试准确率"""
    if not log_path.exists():
        return None
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(r"最终测试准确率:\s+([0-9.]+)%", line)
            if match:
                return float(match.group(1))
            match = re.search(r"final test accuracy:\s+([0-9.]+)%", line, re.IGNORECASE)
            if match:
                return float(match.group(1))
    return None


def extract_acc_curve_from_log(log_path: Path) -> List[float]:
    """从 experiment.log 中提取每轮测试准确率"""
    accs = []
    if not log_path.exists():
        return accs
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(r"acc=([0-9.]+)%", line)
            if match:
                accs.append(float(match.group(1)))
    return accs


def extract_comm_from_log(log_path: Path) -> List[float]:
    """从 experiment.log 中提取每轮通信量 (MB)"""
    comms = []
    if not log_path.exists():
        return comms
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(r"comm=([0-9.]+)\s*MB", line)
            if match:
                comms.append(float(match.group(1)))
    return comms


def load_dataset_results(dataset_dir: Path) -> Dict[float, dict]:
    """
    加载某个数据集下所有实验的结果。
    返回: {alpha: {"acc_curve": [...], "final_acc": float, "comm_curve": [...], "rounds": int}}
    """
    results = {}
    if not dataset_dir.exists():
        return results

    for exp_dir in dataset_dir.iterdir():
        if not exp_dir.is_dir() or not exp_dir.name.startswith("experiment_"):
            continue

        log_path = exp_dir / "experiment.log"
        alpha = extract_alpha_from_log(log_path)
        if alpha is None:
            continue

        acc_curve = extract_acc_curve_from_log(log_path)
        final_acc = extract_final_acc_from_log(log_path)
        comm_curve = extract_comm_from_log(log_path)
        rounds = len(acc_curve)

        # 如果同一 alpha 有多个实验，保留轮数更多的
        if alpha in results:
            if rounds <= results[alpha]["rounds"]:
                continue

        results[alpha] = {
            "acc_curve": acc_curve,
            "final_acc": final_acc,
            "comm_curve": comm_curve,
            "rounds": rounds,
            "exp_dir": exp_dir.name,
        }

    return results


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------

def set_paper_style(ax):
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.tick_params(labelsize=11)
    ax.legend(fontsize=10, framealpha=0.9, edgecolor="gray")
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)


def plot_accuracy_curves(results_map: Dict[str, Dict[float, dict]], save_dir: Path):
    """绘制每个数据集在不同 alpha 下的测试准确率曲线"""
    for ds_key, results in results_map.items():
        if not results:
            continue

        fig, ax = plt.subplots(figsize=FIGSIZE)
        alphas = sorted(results.keys())

        for idx, alpha in enumerate(alphas):
            data = results[alpha]
            acc = data["acc_curve"]
            if not acc:
                continue
            rounds = list(range(1, len(acc) + 1))
            color = plt.cm.viridis(idx / max(len(alphas) - 1, 1))
            ls = "-" if data["rounds"] >= 45 else "--"
            marker = MARKERS.get(ds_key, "o")
            markevery = max(1, len(rounds) // 8)

            label = f"alpha={alpha}"
            if data["rounds"] < 45:
                label += f" ({data['rounds']}/50R)"

            ax.plot(rounds, acc, label=label, color=color, linestyle=ls,
                    marker=marker, markevery=markevery, linewidth=1.8,
                    markersize=4, markerfacecolor="white", markeredgewidth=1.0)

        ax.set_xlabel("Communication Round", fontsize=13)
        ax.set_ylabel("Test Accuracy (%)", fontsize=13)
        ax.set_title(f"Test Accuracy vs. Rounds — {LABELS.get(ds_key, ds_key)}",
                     fontsize=14, fontweight="bold")
        set_paper_style(ax)
        plt.tight_layout()
        save_path = save_dir / f"{ds_key}_accuracy_curves.png"
        plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
        plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        plt.close()
        print(f"  Saved: {save_path}")


def plot_final_accuracy_vs_alpha(results_map: Dict[str, Dict[float, dict]], save_dir: Path):
    """绘制最终准确率 vs alpha 的对比图"""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for ds_key, results in results_map.items():
        if not results:
            continue

        alphas = sorted(results.keys())
        accs = []
        valid_alphas = []
        for a in alphas:
            data = results[a]
            if data["final_acc"] is not None and data["rounds"] >= 45:
                accs.append(data["final_acc"])
                valid_alphas.append(a)
            elif data["final_acc"] is not None and data["rounds"] < 45:
                # 部分完成的实验用半透明的点
                accs.append(data["final_acc"])
                valid_alphas.append(a)

        if not valid_alphas:
            continue

        color = COLORS.get(ds_key, "#333333")
        marker = MARKERS.get(ds_key, "o")
        label = LABELS.get(ds_key, ds_key)

        # 区分完整和不完整的实验
        full_x, full_y = [], []
        partial_x, partial_y = [], []
        for a, acc in zip(valid_alphas, accs):
            if results[a]["rounds"] >= 45:
                full_x.append(a)
                full_y.append(acc)
            else:
                partial_x.append(a)
                partial_y.append(acc)

        if full_x:
            ax.plot(full_x, full_y, label=label, color=color, marker=marker,
                    linewidth=2.0, markersize=8, markerfacecolor="white",
                    markeredgewidth=1.5, zorder=5)
        if partial_x:
            ax.plot(partial_x, partial_y, color=color, marker=marker,
                    linewidth=1.5, markersize=8, markerfacecolor=color,
                    markeredgewidth=1.5, linestyle="--", alpha=0.6,
                    label=f"{label} (partial)", zorder=4)

    ax.set_xlabel("Non-IID Concentration Parameter alpha", fontsize=13)
    ax.set_ylabel("Final Test Accuracy (%)", fontsize=13)
    ax.set_title("Final Accuracy vs. Non-IID Strength", fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    ax.set_xticklabels(["0.1", "0.3", "0.5", "0.7", "0.9", "1.0"])
    set_paper_style(ax)
    plt.tight_layout()
    save_path = save_dir / "final_accuracy_vs_alpha.png"
    plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
    plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_communication_cost(results_map: Dict[str, Dict[float, dict]], save_dir: Path):
    """绘制累积通信量 vs alpha"""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for ds_key, results in results_map.items():
        if not results:
            continue

        alphas = sorted(results.keys())
        total_comms = []
        valid_alphas = []
        for a in alphas:
            data = results[a]
            if data["comm_curve"]:
                total_comms.append(sum(data["comm_curve"]) / 1024)  # GB
                valid_alphas.append(a)

        if not valid_alphas:
            continue

        color = COLORS.get(ds_key, "#333333")
        marker = MARKERS.get(ds_key, "o")
        label = LABELS.get(ds_key, ds_key)

        ax.plot(valid_alphas, total_comms, label=label, color=color, marker=marker,
                linewidth=2.0, markersize=8, markerfacecolor="white",
                markeredgewidth=1.5)

    ax.set_xlabel("Non-IID Concentration Parameter alpha", fontsize=13)
    ax.set_ylabel("Total Communication Cost (GB)", fontsize=13)
    ax.set_title("Cumulative Communication vs. Non-IID Strength", fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    ax.set_xticklabels(["0.1", "0.3", "0.5", "0.7", "0.9", "1.0"])
    set_paper_style(ax)
    plt.tight_layout()
    save_path = save_dir / "communication_vs_alpha.png"
    plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
    plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_summary_table(results_map: Dict[str, Dict[float, dict]], save_dir: Path):
    """生成文本汇总表"""
    lines = []
    lines.append("=" * 80)
    lines.append("Non-IID Alpha 实验结果汇总")
    lines.append("=" * 80)
    lines.append("")

    for ds_key in ["mnist-lenet", "fashion_mnist-cnn_fmnist", "cifar10-resnet20"]:
        results = results_map.get(ds_key, {})
        if not results:
            continue

        lines.append(f"--- {LABELS.get(ds_key, ds_key)} ---")
        lines.append(f"{'alpha':>6} | {'Rounds':>8} | {'Final Acc':>12} | {'Total Comm':>12} | Status")
        lines.append("-" * 70)

        for alpha in sorted(results.keys()):
            data = results[alpha]
            rounds = data["rounds"]
            acc = data["final_acc"]
            comm = sum(data["comm_curve"]) / 1024 if data["comm_curve"] else 0
            status = "OK" if rounds >= 45 else "PARTIAL"
            acc_str = f"{acc:.2f}%" if acc is not None else "N/A"
            comm_str = f"{comm:.2f} GB" if comm else "N/A"
            lines.append(f"{alpha:>6.1f} | {rounds:>8} | {acc_str:>12} | {comm_str:>12} | {status}")

        lines.append("")

    lines.append("=" * 80)

    table_path = save_dir / "niid_summary_table.txt"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Saved: {table_path}")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "mnist-lenet": INPUT_DIR / "mnist-lenet",
        "fashion_mnist-cnn_fmnist": INPUT_DIR / "fashion_mnist-cnn_fmnist",
        "cifar10-resnet20": INPUT_DIR / "cifar10-resnet20",
    }

    print("[LOAD] Scanning experiment results...")
    results_map = {}
    for ds_key, ds_path in datasets.items():
        results = load_dataset_results(ds_path)
        results_map[ds_key] = results
        print(f"  {LABELS.get(ds_key, ds_key)}: {len(results)} alpha values loaded")
        for alpha in sorted(results.keys()):
            r = results[alpha]
            status = "OK" if r["rounds"] >= 45 else f"PARTIAL-{r['rounds']}R"
            acc_str = f"{r['final_acc']:.2f}%" if r['final_acc'] is not None else "N/A"
            print(f"    alpha={alpha}: final_acc={acc_str} | {status}")

    print(f"\n[PLOT] Generating figures -> {OUTPUT_DIR}")
    plot_accuracy_curves(results_map, OUTPUT_DIR)
    plot_final_accuracy_vs_alpha(results_map, OUTPUT_DIR)
    plot_communication_cost(results_map, OUTPUT_DIR)
    plot_summary_table(results_map, OUTPUT_DIR)

    print(f"\n[DONE] All plots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
