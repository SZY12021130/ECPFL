#!/usr/bin/env python3
"""
跨数据集对比 adaptive voting 实验结果。

读取每个数据集子目录下的 experiments_registry.json：
  accuracy_baseline/adaptive/<dataset>/experiments_registry.json

汇总每个数据集下最新一次 baseline / cosine / accuracy / consensus 的 50 轮结果，
输出 Markdown 表格与对比图。
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"

DATASETS = ["fashion_mnist", "mnist", "cifar10", "svhn"]
STRATEGIES = ["baseline", "cosine", "accuracy", "consensus"]

COLORS = {
    "baseline": "#1f77b4",
    "cosine": "#ff7f0e",
    "accuracy": "#2ca02c",
    "consensus": "#d62728",
}


def load_registry(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


# 旧 FMNIST 实验的时间戳映射（config_summary 中缺少 adaptive_vote）
FMNIST_LEGACY_MAP = {
    "20260630_111040": "baseline",
    "20260630_112958": "cosine",
    "20260630_114831": "cosine",
    "20260630_120615": "accuracy",
    "20260630_122306": "consensus",
    "20260630_131841": "baseline",
    "20260630_131847": "cosine",
    "20260630_140229": "accuracy",
    "20260630_140249": "consensus",
}


def detect_strategy(e):
    """从 config_summary 或时间戳推断策略。"""
    cfg = e.get("config_summary", {})
    av = cfg.get("adaptive_vote")
    if isinstance(av, dict):
        return av.get("strategy", "baseline") if av.get("enabled") else "baseline"
    # 兼容旧注册表
    ts = e.get("timestamp", "")
    return FMNIST_LEGACY_MAP.get(ts, "baseline")


def pick_entries(registry):
    """为每个策略挑选时间戳最新的一条记录。"""
    picked = {}
    for e in registry:
        strat = detect_strategy(e)
        if strat not in STRATEGIES:
            continue
        ts = e.get("timestamp", "")
        if strat not in picked or ts > picked[strat]["timestamp"]:
            picked[strat] = e
    return picked


def build_rows(dataset):
    reg_path = ADAPTIVE_DIR / dataset / "experiments_registry.json"
    registry = load_registry(reg_path)
    picked = pick_entries(registry)
    rows = []
    for strat in STRATEGIES:
        e = picked.get(strat)
        if e is None:
            rows.append({
                "dataset": dataset,
                "strategy": strat,
                "acc": None,
                "time": None,
                "comm": None,
                "expansion": None,
            })
            continue
        s = e["metrics_summary"]
        rows.append({
            "dataset": dataset,
            "strategy": strat,
            "acc": s["final_test_acc"],
            "time": s["total_time_sec"],
            "comm": s["total_communication_mb"],
            "expansion": s["avg_expansion_ratio"],
        })
    return rows


def build_table(all_rows):
    lines = []
    lines.append("# Adaptive Voting 跨数据集 50 轮对比\n")
    lines.append("| Dataset | Strategy | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |")
    lines.append("|---------|----------|---------------|----------------|-----------|---------------|")
    for rows in all_rows:
        for r in rows:
            ds = r["dataset"]
            st = r["strategy"]
            acc = f"{r['acc']:.2f}" if r["acc"] is not None else "—"
            time = f"{r['time']:.2f}" if r["time"] is not None else "—"
            comm = f"{r['comm']:.2f}" if r["comm"] is not None else "—"
            exp = f"{r['expansion']:.2f}x" if r["expansion"] is not None else "—"
            lines.append(f"| {ds} | {st} | {acc} | {time} | {comm} | {exp} |")
    lines.append("")

    # Relative to baseline per dataset
    lines.append("## Relative to dataset baseline (topk)\n")
    lines.append("| Dataset | Strategy | Δ Acc (pp) | Time Ratio | Comm Ratio |")
    lines.append("|---------|----------|------------|------------|------------|")
    for rows in all_rows:
        baseline = next((r for r in rows if r["strategy"] == "baseline" and r["acc"] is not None), None)
        if baseline is None:
            continue
        ds = baseline["dataset"]
        for r in rows:
            if r["strategy"] == "baseline" or r["acc"] is None:
                continue
            lines.append(
                f"| {ds} | {r['strategy']} | "
                f"{r['acc'] - baseline['acc']:+.2f} | "
                f"{r['time'] / baseline['time']:.2f}x | "
                f"{r['comm'] / baseline['comm']:.2f}x |"
            )
    lines.append("")
    return "\n".join(lines)


def plot_dataset(rows, title, filename):
    strategies = [r["strategy"] for r in rows if r["acc"] is not None]
    accs = [r["acc"] for r in rows if r["acc"] is not None]
    comms = [r["comm"] for r in rows if r["comm"] is not None]
    if not strategies:
        return None

    x = np.arange(len(strategies))
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    ax = axes[0]
    bars = ax.bar(x, accs, color=[COLORS[s] for s in strategies])
    ax.set_ylabel("Final Test Accuracy (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=15, ha="right")
    ax.set_title("Accuracy")
    for bar, v in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{v:.2f}", ha="center", va="bottom", fontsize=9)

    ax = axes[1]
    bars = ax.bar(x, comms, color=[COLORS[s] for s in strategies])
    ax.set_ylabel("Total Communication (MB)")
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=15, ha="right")
    ax.set_title("Communication")
    for bar, v in zip(bars, comms):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(comms) * 0.01,
                f"{v:.0f}", ha="center", va="bottom", fontsize=9)

    fig.suptitle(title, fontsize=12)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plot_path = ADAPTIVE_DIR / filename
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plot_path


def plot_cross_dataset(all_rows):
    datasets = [rows[0]["dataset"] for rows in all_rows]
    strategies = STRATEGIES
    x = np.arange(len(datasets))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, strat in enumerate(strategies):
        vals = []
        for rows in all_rows:
            r = next((r for r in rows if r["strategy"] == strat and r["acc"] is not None), None)
            vals.append(r["acc"] if r else np.nan)
        ax.bar(x + i * width, vals, width, label=strat, color=COLORS[strat])

    ax.set_ylabel("Final Test Accuracy (%)")
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels(datasets, rotation=15, ha="right")
    ax.set_title("Adaptive Voting Across Datasets (50 rounds)")
    ax.legend()
    plt.tight_layout()
    plot_path = ADAPTIVE_DIR / "adaptive_cross_dataset_accuracy.png"
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plot_path


def main():
    all_rows = []
    for ds in DATASETS:
        rows = build_rows(ds)
        all_rows.append(rows)

    md = build_table(all_rows)
    md_path = ADAPTIVE_DIR / "adaptive_cross_dataset_comparison.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)

    plot_paths = []
    for rows in all_rows:
        ds = rows[0]["dataset"]
        p = plot_dataset(rows, f"{ds} - Adaptive Voting (50 rounds)",
                         f"adaptive_{ds}_comparison.png")
        if p:
            plot_paths.append(p)

    cross_plot = plot_cross_dataset(all_rows)
    plot_paths.append(cross_plot)

    print(f"\nSaved table to {md_path}")
    for p in plot_paths:
        print(f"Saved plot to {p}")


if __name__ == "__main__":
    main()
