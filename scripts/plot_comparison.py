#!/usr/bin/env python3
"""
预取 vs 无预取 对比分析脚本

读取 accuracy/（预取）和 accuracy_noprefetch/（无预取）的实验结果，
生成通信量对比、准确率-通信权衡图。

用法:
  python scripts/plot_comparison.py
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    print("Error: matplotlib not installed")
    sys.exit(1)

import numpy as np

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PREFETCH_DIR = Path("accuracy")
NO_PREFETCH_DIR = Path("accuracy_noprefetch")
OUTPUT_DIR = Path("comparison_plots")
DPI = 300
FIGSIZE = (8, 5)

COLORS = {
    "prefetch": "#1f77b4",
    "no_prefetch": "#ff7f0e",
}

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def load_group(base_dir: Path):
    """加载某个目录下的所有实验，按 (dataset, model, sparsity) 分组，保留最佳结果"""
    results = {}
    if not base_dir.exists():
        return results
    for category_dir in base_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name == "plots":
            continue
        for exp_dir in category_dir.iterdir():
            if not exp_dir.is_dir():
                continue
            mpath = exp_dir / "metrics.json"
            cpath = exp_dir / "config.yaml"
            if not mpath.exists() or not cpath.exists():
                continue
            try:
                with open(mpath, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
                with open(cpath, "r", encoding="utf-8") as f:
                    import yaml
                    config = yaml.safe_load(f)
            except Exception:
                continue
            test_acc = metrics.get("test_acc", [])
            if not test_acc:
                continue
            dataset = config["data"]["dataset"]
            model = config["model"]["name"]
            strategy = config["ckks"]["sparsification"]["strategy"]
            sparsity = config["ckks"]["sparsification"].get("sparsity_rate", "none")
            key = (dataset, model, str(sparsity))
            final_acc = test_acc[-1]
            num_ct_list = metrics.get("num_ciphertexts", [])
            avg_num_ct = sum(num_ct_list) / len(num_ct_list) if num_ct_list else 0
            # 优先选择正确稀疏化的实验：num_ciphertexts 与 sparsity_rate 匹配的
            # 对相同 key 的多个实验，优先选择 num_ciphertexts 更低（更接近真实稀疏率）的
            is_better = False
            if key not in results:
                is_better = True
            else:
                prev = results[key]
                # 如果当前实验的 num_ct 显著低于已有实验，说明当前是真正稀疏化的
                if avg_num_ct < prev["avg_num_ct"] * 0.5:
                    is_better = True
                # 如果两者都正常（差距不大），保留准确率更高的
                elif abs(avg_num_ct - prev["avg_num_ct"]) / max(prev["avg_num_ct"], 1) < 0.3:
                    if final_acc > prev["final_acc"]:
                        is_better = True
            if is_better:
                results[key] = {
                    "dataset": dataset,
                    "model": model,
                    "sparsity": str(sparsity),
                    "rounds": len(test_acc),
                    "final_acc": final_acc,
                    "max_acc": max(test_acc),
                    "avg_num_ct": avg_num_ct,
                    "test_acc": test_acc,
                    "test_loss": metrics.get("test_loss", []),
                    "comm": metrics.get("total_communication_cost", []),
                    "source": base_dir.name,
                }
    return results


def align_data(prefetch_data: dict, no_prefetch_data: dict):
    """对齐两组数据，只保留两边都存在的 (dataset, model, sparsity) 组合"""
    common_keys = sorted(set(prefetch_data.keys()) & set(no_prefetch_data.keys()))
    aligned = []
    for key in common_keys:
        aligned.append({
            "key": key,
            "dataset": key[0],
            "model": key[1],
            "sparsity": key[2],
            "prefetch": prefetch_data[key],
            "no_prefetch": no_prefetch_data[key],
        })
    return aligned


# ---------------------------------------------------------------------------
# 绘图函数
# ---------------------------------------------------------------------------

def set_paper_style(ax):
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.tick_params(labelsize=11)
    ax.legend(fontsize=10, framealpha=0.9, edgecolor="gray")
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)


def plot_comm_comparison(aligned: list, save_dir: Path):
    """每组配置绘制累积通信开销对比曲线"""
    # 按 group_name 分组
    groups = defaultdict(list)
    for item in aligned:
        gname = f"{item['dataset']}-{item['model']}"
        groups[gname].append(item)

    for gname, items in sorted(groups.items()):
        fig, ax = plt.subplots(figsize=FIGSIZE)
        for item in sorted(items, key=lambda x: (x["sparsity"] != "none", float(x["sparsity"]) if x["sparsity"] != "none" else 999)):
            sp = item["sparsity"]
            for label, color, data_key in [("Prefetch", COLORS["prefetch"], "prefetch"), ("No Prefetch", COLORS["no_prefetch"], "no_prefetch")]:
                comm = item[data_key]["comm"]
                if not comm:
                    continue
                rounds = list(range(1, len(comm) + 1))
                cum = np.cumsum(comm) / (1024 ** 2)
                ls = "-" if data_key == "prefetch" else "--"
                ax.plot(rounds, cum, label=f"{label} sp={sp}",
                        color=color, linestyle=ls, linewidth=1.8, alpha=0.8)
        ax.set_xlabel("Communication Round", fontsize=13)
        ax.set_ylabel("Cumulative Communication Cost (MB)", fontsize=13)
        ax.set_title(f"Communication Cost: Prefetch vs No Prefetch — {gname}", fontsize=13, fontweight="bold")
        set_paper_style(ax)
        plt.tight_layout()
        save_path = save_dir / f"{gname}_comm_comparison.png"
        plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
        plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        plt.close()
        print(f"  Saved: {save_path}")


def plot_final_comm_bar(aligned: list, save_dir: Path):
    """最终通信量柱状图对比"""
    # 按 group_name 分组
    groups = defaultdict(list)
    for item in aligned:
        gname = f"{item['dataset']}-{item['model']}"
        groups[gname].append(item)

    for gname, items in sorted(groups.items()):
        fig, ax = plt.subplots(figsize=(max(7, len(items) * 1.0), 5))
        labels = []
        pf_comm = []
        np_comm = []
        x_pos = []
        bar_width = 0.35
        for i, item in enumerate(sorted(items, key=lambda x: (x["sparsity"] != "none", float(x["sparsity"]) if x["sparsity"] != "none" else 999))):
            labels.append(f"sp={item['sparsity']}")
            x_pos.append(i)
            pf_comm.append(sum(item["prefetch"]["comm"]) / (1024 ** 2) if item["prefetch"]["comm"] else 0)
            np_comm.append(sum(item["no_prefetch"]["comm"]) / (1024 ** 2) if item["no_prefetch"]["comm"] else 0)

        x = np.arange(len(labels))
        bars1 = ax.bar(x - bar_width / 2, pf_comm, bar_width, label="Prefetch", color=COLORS["prefetch"], edgecolor="black", linewidth=1.0)
        bars2 = ax.bar(x + bar_width / 2, np_comm, bar_width, label="No Prefetch", color=COLORS["no_prefetch"], edgecolor="black", linewidth=1.0)

        # 标注数值
        for bar, val in zip(bars1, pf_comm):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + max(pf_comm) * 0.01,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8, rotation=45)
        for bar, val in zip(bars2, np_comm):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + max(np_comm) * 0.01,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8, rotation=45)

        ax.set_xlabel("Sparsity Rate", fontsize=13)
        ax.set_ylabel("Total Communication Cost (MB)", fontsize=13)
        ax.set_title(f"Total Communication: Prefetch vs No Prefetch — {gname}", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.grid(True, axis="y", linestyle="--", alpha=0.6)
        ax.legend(fontsize=10)
        for spine in ax.spines.values():
            spine.set_linewidth(1.2)
        plt.tight_layout()
        save_path = save_dir / f"{gname}_final_comm_bar.png"
        plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
        plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        plt.close()
        print(f"  Saved: {save_path}")


def plot_acc_vs_comm_scatter(aligned: list, save_dir: Path):
    """准确率-通信量权衡散点图"""
    fig, ax = plt.subplots(figsize=FIGSIZE)
    markers = {"mnist": "o", "fashion_mnist": "s", "cifar10": "^"}
    for item in aligned:
        pf_comm = sum(item["prefetch"]["comm"]) / (1024 ** 2) if item["prefetch"]["comm"] else 0
        np_comm = sum(item["no_prefetch"]["comm"]) / (1024 ** 2) if item["no_prefetch"]["comm"] else 0
        pf_acc = item["prefetch"]["final_acc"]
        np_acc = item["no_prefetch"]["final_acc"]
        ds = item["dataset"]
        mk = markers.get(ds, "o")
        sp = item["sparsity"]
        color = COLORS["prefetch"]
        ax.scatter(pf_comm, pf_acc, marker=mk, s=120, c=color, edgecolors="black", linewidths=1.2, alpha=0.8, zorder=3)
        color = COLORS["no_prefetch"]
        ax.scatter(np_comm, np_acc, marker=mk, s=120, c=color, edgecolors="black", linewidths=1.2, alpha=0.8, zorder=3)
        # 连线
        ax.plot([pf_comm, np_comm], [pf_acc, np_acc], "k--", alpha=0.3, linewidth=0.8, zorder=1)

    # 图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["prefetch"], markeredgecolor="black", markersize=10, label="Prefetch"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["no_prefetch"], markeredgecolor="black", markersize=10, label="No Prefetch"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="gray", markeredgecolor="black", markersize=8, label="MNIST"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="gray", markeredgecolor="black", markersize=8, label="Fashion-MNIST"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="gray", markeredgecolor="black", markersize=8, label="CIFAR-10"),
    ]
    ax.legend(handles=legend_elements, fontsize=9, framealpha=0.9, edgecolor="gray")

    ax.set_xlabel("Total Communication Cost (MB)", fontsize=13)
    ax.set_ylabel("Final Test Accuracy (%)", fontsize=13)
    ax.set_title("Accuracy vs. Communication Trade-off", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.tick_params(labelsize=11)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    plt.tight_layout()
    save_path = save_dir / "acc_vs_comm_scatter.png"
    plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
    plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_acc_comparison_bar(aligned: list, save_dir: Path):
    """最终准确率对比柱状图（预取 vs 无预取）"""
    groups = defaultdict(list)
    for item in aligned:
        gname = f"{item['dataset']}-{item['model']}"
        groups[gname].append(item)

    for gname, items in sorted(groups.items()):
        fig, ax = plt.subplots(figsize=(max(7, len(items) * 1.0), 5))
        labels = []
        pf_acc = []
        np_acc = []
        for item in sorted(items, key=lambda x: (x["sparsity"] != "none", float(x["sparsity"]) if x["sparsity"] != "none" else 999)):
            labels.append(f"sp={item['sparsity']}")
            pf_acc.append(item["prefetch"]["final_acc"])
            np_acc.append(item["no_prefetch"]["final_acc"])

        x = np.arange(len(labels))
        bar_width = 0.35
        bars1 = ax.bar(x - bar_width / 2, pf_acc, bar_width, label="Prefetch", color=COLORS["prefetch"], edgecolor="black", linewidth=1.0)
        bars2 = ax.bar(x + bar_width / 2, np_acc, bar_width, label="No Prefetch", color=COLORS["no_prefetch"], edgecolor="black", linewidth=1.0)

        for bar, val in zip(bars1, pf_acc):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.3,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8)
        for bar, val in zip(bars2, np_acc):
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.3,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8)

        ax.set_xlabel("Sparsity Rate", fontsize=13)
        ax.set_ylabel("Final Test Accuracy (%)", fontsize=13)
        ax.set_title(f"Accuracy Comparison: Prefetch vs No Prefetch — {gname}", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylim(0, 105)
        ax.grid(True, axis="y", linestyle="--", alpha=0.6)
        ax.legend(fontsize=10)
        for spine in ax.spines.values():
            spine.set_linewidth(1.2)
        plt.tight_layout()
        save_path = save_dir / f"{gname}_acc_comparison_bar.png"
        plt.savefig(save_path, dpi=DPI, bbox_inches="tight")
        plt.savefig(save_path.with_suffix(".pdf"), bbox_inches="tight")
        plt.close()
        print(f"  Saved: {save_path}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" 预取 vs 无预取 对比分析")
    print("=" * 60)

    print("\nLoading prefetch experiments...")
    prefetch_data = load_group(PREFETCH_DIR)
    print(f"  Found {len(prefetch_data)} unique experiments")

    print("\nLoading no-prefetch experiments...")
    no_prefetch_data = load_group(NO_PREFETCH_DIR)
    print(f"  Found {len(no_prefetch_data)} unique experiments")

    aligned = align_data(prefetch_data, no_prefetch_data)
    print(f"\nAligned common experiments: {len(aligned)}")
    for item in aligned:
        print(f"  {item['dataset']}-{item['model']} sp={item['sparsity']}")

    if not aligned:
        print("No common experiments found for comparison.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating comparison plots to: {OUTPUT_DIR}\n")

    plot_comm_comparison(aligned, OUTPUT_DIR)
    plot_final_comm_bar(aligned, OUTPUT_DIR)
    plot_acc_comparison_bar(aligned, OUTPUT_DIR)
    plot_acc_vs_comm_scatter(aligned, OUTPUT_DIR)

    print(f"\n{'=' * 60}")
    print(f" All comparison plots saved to: {OUTPUT_DIR}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
