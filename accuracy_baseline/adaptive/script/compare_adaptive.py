#!/usr/bin/env python3
"""
Compare FMNIST 15-round and 50-round adaptive voting experiments.

Reads experiments_registry.json from accuracy_baseline/adaptive and optionally
an older 50-round baseline from accuracy_baseline/ours/result_fix_pro.
Outputs a Markdown table and bar plots to accuracy_baseline/adaptive/.
"""

import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"
RESULT_FIX_PRO = PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro"

# 15-round experiments (timestamp -> label)
EXPERIMENTS_15 = {
    "20260630_111040": "baseline (topk 0.3)",
    "20260630_114831": "adaptive_cosine",
    "20260630_120615": "adaptive_accuracy",
    "20260630_122306": "adaptive_consensus",
}

# 50-round experiments (timestamp -> label)
EXPERIMENTS_50 = {
    "20260630_131841": "baseline (topk 0.3)",
    "20260630_131847": "adaptive_cosine",
    "20260630_140229": "adaptive_accuracy",
    "20260630_140249": "adaptive_consensus",
}

OLD_BASELINE_DIR = RESULT_FIX_PRO / "20260610_fashion_mnist_sp0.3_topk0.3"

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]


def load_registry():
    registry_path = ADAPTIVE_DIR / "experiments_registry.json"
    with open(registry_path, "r", encoding="utf-8") as f:
        return {item["timestamp"]: item for item in json.load(f)}


def load_old_baseline():
    metrics_path = OLD_BASELINE_DIR / "metrics.json"
    if not metrics_path.exists():
        return None
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    return {
        "label": "ours (50r topk 0.3)",
        "final_test_acc": m["test_acc"][-1] if m.get("test_acc") else 0.0,
        "total_time_sec": sum(m.get("total_round_real_time", [])),
        "total_communication_mb": sum(m.get("total_communication_cost", [])) / (1024 * 1024),
        "avg_expansion_ratio": (
            sum(m.get("expansion_ratio", [])) / len(m["expansion_ratio"])
            if m.get("expansion_ratio") else 0.0
        ),
        "num_rounds": len(m.get("test_acc", [])),
    }


def load_rows(registry, mapping):
    rows = []
    for ts, label in mapping.items():
        item = registry.get(ts)
        if item is None:
            print(f"Warning: {ts} not found in registry", file=sys.stderr)
            continue
        s = item["metrics_summary"]
        rows.append({
            "label": label,
            "num_rounds": item["config_summary"]["num_rounds"],
            "final_test_acc": s["final_test_acc"],
            "total_time_sec": s["total_time_sec"],
            "total_communication_mb": s["total_communication_mb"],
            "avg_expansion_ratio": s["avg_expansion_ratio"],
        })
    return rows


def build_table(rows, title, baseline_label=None):
    lines = []
    lines.append(f"# {title}\n")
    lines.append("| Strategy | Rounds | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |")
    lines.append("|----------|--------|---------------|----------------|-----------|---------------|")
    for r in rows:
        lines.append(
            f"| {r['label']} | {r['num_rounds']} | "
            f"{r['final_test_acc']:.2f} | {r['total_time_sec']:.2f} | "
            f"{r['total_communication_mb']:.2f} | {r['avg_expansion_ratio']:.2f}x |"
        )
    lines.append("")

    baseline = None
    if baseline_label:
        baseline = next((r for r in rows if r["label"] == baseline_label), None)
    if baseline is None:
        baseline = next((r for r in rows if "baseline" in r["label"].lower()), None)

    if baseline:
        lines.append(f"## Relative to {baseline['label']} ({baseline['num_rounds']}-round baseline)\n")
        lines.append("| Strategy | Δ Acc (pp) | Time Ratio | Comm Ratio |")
        lines.append("|----------|------------|------------|------------|")
        for r in rows:
            if r is baseline:
                continue
            lines.append(
                f"| {r['label']} | "
                f"{r['final_test_acc'] - baseline['final_test_acc']:+.2f} | "
                f"{r['total_time_sec'] / baseline['total_time_sec']:.2f}x | "
                f"{r['total_communication_mb'] / baseline['total_communication_mb']:.2f}x |"
            )
        lines.append("")
    return "\n".join(lines)


def plot_section(rows, title, filename):
    labels = [r["label"] for r in rows]
    x = np.arange(len(labels))
    width = 0.25

    accs = [r["final_test_acc"] for r in rows]
    times = [r["total_time_sec"] for r in rows]
    comms = [r["total_communication_mb"] for r in rows]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

    ax = axes[0]
    bars = ax.bar(x, accs, color=COLORS[:len(labels)])
    ax.set_ylabel("Final Test Accuracy (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylim([min(accs) - 2, max(accs) + 2])
    ax.axhline(y=accs[0], color="gray", linestyle="--", linewidth=0.8)
    ax.set_title("Accuracy")
    for bar, v in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3, f"{v:.2f}",
                ha="center", va="bottom", fontsize=8)

    ax = axes[1]
    bars = ax.bar(x, times, color=COLORS[:len(labels)])
    ax.set_ylabel("Total Time (s)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_title("Total Training Time")
    for bar, v in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(times) * 0.01,
                f"{v:.1f}", ha="center", va="bottom", fontsize=8)

    ax = axes[2]
    bars = ax.bar(x, comms, color=COLORS[:len(labels)])
    ax.set_ylabel("Total Communication (MB)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_title("Total Communication")
    for bar, v in zip(bars, comms):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(comms) * 0.01,
                f"{v:.1f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle(title, fontsize=13)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plot_path = ADAPTIVE_DIR / filename
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plot_path


def build_cross_round_table(rows_15, rows_50):
    lines = []
    lines.append("# 15-round vs. 50-round Summary\n")
    lines.append("| Strategy | 15r Acc (%) | 15r Comm (MB) | 50r Acc (%) | 50r Comm (MB) | Δ Acc (pp) | Comm Ratio (50r/15r) |")
    lines.append("|----------|-------------|---------------|-------------|---------------|------------|----------------------|")

    map15 = {r["label"]: r for r in rows_15}
    map50 = {r["label"]: r for r in rows_50}

    for label in map15:
        if label not in map50:
            continue
        r15 = map15[label]
        r50 = map50[label]
        lines.append(
            f"| {label} | {r15['final_test_acc']:.2f} | {r15['total_communication_mb']:.2f} | "
            f"{r50['final_test_acc']:.2f} | {r50['total_communication_mb']:.2f} | "
            f"{r50['final_test_acc'] - r15['final_test_acc']:+.2f} | "
            f"{r50['total_communication_mb'] / r15['total_communication_mb']:.2f}x |"
        )
    lines.append("")
    return "\n".join(lines)


def plot_cross_round(rows_15, rows_50):
    strategies = [r["label"] for r in rows_15]
    x = np.arange(len(strategies))
    width = 0.35

    acc15 = [r["final_test_acc"] for r in rows_15]
    acc50 = [next(r for r in rows_50 if r["label"] == label)["final_test_acc"]
             for label in strategies]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars1 = ax.bar(x - width / 2, acc15, width, label="15 rounds", color="#1f77b4")
    bars2 = ax.bar(x + width / 2, acc50, width, label="50 rounds", color="#ff7f0e")

    ax.set_ylabel("Final Test Accuracy (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=15, ha="right")
    ax.set_title("FMNIST Adaptive Strategies: 15-round vs. 50-round Accuracy")
    ax.legend()

    for bars in (bars1, bars2):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, height + 0.2, f"{height:.2f}",
                    ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plot_path = ADAPTIVE_DIR / "adaptive_15v50_accuracy.png"
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plot_path


def main():
    registry = load_registry()

    rows_15 = load_rows(registry, EXPERIMENTS_15)
    rows_50 = load_rows(registry, EXPERIMENTS_50)

    old = load_old_baseline()

    md_parts = []
    md_parts.append(build_table(rows_15, "FMNIST 15-round Adaptive Voting Comparison"))
    md_parts.append(build_table(rows_50, "FMNIST 50-round Adaptive Voting Comparison"))
    if old:
        md_parts.append(build_table([old], "Older 50-round Baseline (accuracy_baseline/ours)"))
    md_parts.append(build_cross_round_table(rows_15, rows_50))
    md = "\n".join(md_parts)

    md_path = ADAPTIVE_DIR / "adaptive_comparison.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)

    plot_15 = plot_section(rows_15, "FMNIST 15-round Adaptive Voting Strategies",
                           "adaptive_comparison_15r.png")
    plot_50 = plot_section(rows_50, "FMNIST 50-round Adaptive Voting Strategies",
                           "adaptive_comparison_50r.png")
    plot_cross = plot_cross_round(rows_15, rows_50)

    print(f"\nSaved comparison table to {md_path}")
    print(f"Saved 15-round plot to {plot_15}")
    print(f"Saved 50-round plot to {plot_50}")
    print(f"Saved 15 vs 50 accuracy plot to {plot_cross}")


if __name__ == "__main__":
    main()
