#!/usr/bin/env python3
"""
Baseline 对比自动绘图脚本
- accuracy_vs_rounds
- communication_total_bar
- cumulative_comm_vs_rounds
- baseline_report.md
"""

import json
import os
import sys
from pathlib import Path
import numpy as np

# Matplotlib 中文支持
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON_JSON = PROJECT_ROOT / "results" / "baseline_comparison" / "comparison_results.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "baseline_comparison"

# 配色方案
COLORS = {
    "fedavg_ckks": "#1f77b4",
    "fedphe_internal": "#ff7f0e",
    "fedphe_standalone": "#2ca02c",
    "esafl": "#d62728",
    "cipherfetch": "#9467bd",
}


def fmt_size(bytes_val: int) -> str:
    """将字节数格式化为人类可读字符串。"""
    if bytes_val >= 1024**3:
        return f"{bytes_val / 1024**3:.2f} GB"
    if bytes_val >= 1024**2:
        return f"{bytes_val / 1024**2:.2f} MB"
    if bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} KB"
    return f"{bytes_val} B"


def plot_accuracy(results: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    for key, data in results.items():
        rounds = data.get("rounds", [])
        acc = data.get("test_acc", [])
        if not rounds or not acc:
            continue
        label = data.get("name", key)
        color = COLORS.get(key, None)
        ax.plot(rounds, acc, marker="o", markersize=3, label=label, color=color, linewidth=1.5)

    ax.set_xlabel("Global Round", fontsize=12)
    ax.set_ylabel("Test Accuracy", fontsize=12)
    ax.set_title("Test Accuracy vs. Rounds", fontsize=14)
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "accuracy_vs_rounds.png", dpi=300)
    fig.savefig(OUTPUT_DIR / "accuracy_vs_rounds.pdf")
    plt.close(fig)
    print("[OK] 保存 accuracy_vs_rounds.png/pdf")


def plot_comm_bar(results: dict):
    labels = []
    uplink = []
    downlink = []
    total = []
    colors_list = []

    for key, data in results.items():
        labels.append(data.get("name", key))
        uplink.append(data.get("total_upload", 0))
        downlink.append(data.get("total_download", 0))
        total.append(data.get("total_comm", 0))
        colors_list.append(COLORS.get(key, "#333333"))

    if not labels:
        print("[WARN] 无数据，跳过通信量柱状图")
        return

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.5), 5))
    bars1 = ax.bar(x - width, [u / 1024**2 for u in uplink], width, label="Uplink", color="#4c78a8")
    bars2 = ax.bar(x, [d / 1024**2 for d in downlink], width, label="Downlink", color="#f58518")
    bars3 = ax.bar(x + width, [t / 1024**2 for t in total], width, label="Total", color="#54a24b")

    ax.set_ylabel("Communication (MB)", fontsize=12)
    ax.set_title("Total Communication Comparison", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "communication_total_bar.png", dpi=300)
    fig.savefig(OUTPUT_DIR / "communication_total_bar.pdf")
    plt.close(fig)
    print("[OK] 保存 communication_total_bar.png/pdf")


def plot_cumulative_comm(results: dict):
    fig, ax = plt.subplots(figsize=(8, 5))
    for key, data in results.items():
        rounds = data.get("rounds", [])
        ul = data.get("upload_cost", [])
        dl = data.get("download_cost", [])
        if not rounds or not ul:
            continue
        cum_ul = np.cumsum(ul)
        cum_dl = np.cumsum(dl)
        cum_total = cum_ul + cum_dl
        label = data.get("name", key)
        color = COLORS.get(key, None)
        ax.plot(rounds, cum_total / 1024**2, label=label, color=color, linewidth=1.5)

    ax.set_xlabel("Global Round", fontsize=12)
    ax.set_ylabel("Cumulative Communication (MB)", fontsize=12)
    ax.set_title("Cumulative Communication vs. Rounds", fontsize=14)
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "cumulative_comm_vs_rounds.png", dpi=300)
    fig.savefig(OUTPUT_DIR / "cumulative_comm_vs_rounds.pdf")
    plt.close(fig)
    print("[OK] 保存 cumulative_comm_vs_rounds.png/pdf")


def generate_report(results: dict):
    lines = [
        "# Baseline 对比实验报告",
        "",
        "| Baseline | Final Acc | Final Loss | Total Uplink | Total Downlink | Total Comm | Avg Round Time |",
        "|----------|-----------|------------|--------------|----------------|------------|----------------|",
    ]
    for key, data in results.items():
        name = data.get("name", key)
        acc = data.get("final_acc", 0.0)
        loss = data.get("final_loss", 0.0)
        ul = data.get("total_upload", 0)
        dl = data.get("total_download", 0)
        total = data.get("total_comm", 0)
        times = data.get("time_cost", [])
        avg_time = sum(times) / len(times) if times else 0.0
        lines.append(
            f"| {name} | {acc:.4f} | {loss:.4f} | {fmt_size(ul)} | {fmt_size(dl)} | {fmt_size(total)} | {avg_time:.2f}s |"
        )

    lines += ["", "## 说明", "", "- 所有实验在统一参数下运行（数据集、模型、客户端数、轮次、学习率等一致）。", "- 通信量统计单位为字节（Bytes），图表中转换为 MB。", ""]

    report_path = OUTPUT_DIR / "baseline_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] 保存报告: {report_path}")


def main():
    if not COMPARISON_JSON.exists():
        print(f"[ERROR] 未找到对比结果文件: {COMPARISON_JSON}")
        print("请先运行 collect_results.py")
        return 1

    with open(COMPARISON_JSON, "r", encoding="utf-8") as f:
        results = json.load(f)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plot_accuracy(results)
    plot_comm_bar(results)
    plot_cumulative_comm(results)
    generate_report(results)

    print("[DONE] 所有图表和报告已生成到 results/baseline_comparison/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
