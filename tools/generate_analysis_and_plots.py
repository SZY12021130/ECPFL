#!/usr/bin/env python3
"""Generate summary analysis + draw accuracy curves for all experiments."""

import os
import sys
import json
import pickle
import numpy as np
from pathlib import Path

# Add project root to path for importing tools.plotter
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.plotter import Plotter

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
with open("accuracy_result/experiment_data.pkl", "rb") as f:
    experiments = pickle.load(f)

# ---------------------------------------------------------------------------
# Helper: normalize to [0, 1] (higher is better for all metrics after inversion)
# ---------------------------------------------------------------------------
def normalize(values, higher_is_better=True):
    arr = np.array(values, dtype=float)
    min_v, max_v = arr.min(), arr.max()
    if max_v - min_v < 1e-9:
        return np.ones_like(arr)
    normed = (arr - min_v) / (max_v - min_v)
    if not higher_is_better:
        normed = 1 - normed
    return normed


# ---------------------------------------------------------------------------
# Step 2: Summary analysis
# ---------------------------------------------------------------------------
def generate_summary():
    datasets = ["mnist", "fashion_mnist", "cifar10"]
    ds_labels = {"mnist": "MNIST", "fashion_mnist": "Fashion-MNIST", "cifar10": "CIFAR-10"}

    lines = []
    lines.append("# 实验汇总分析与最平衡结果\n")
    lines.append("> 涵盖目录：`accuracy_client_selection`、`accuracy_threshold_v2`、`accuracy_topk_v2`、`accuracy_niid`、`accuracy_noprefetch`、`accuracy`\n")
    lines.append("\n## 分析维度\n")
    lines.append("- **准确率**：最终第 50 轮测试准确率")
    lines.append("- **通信量**：累计总通信量（上行 + 下行，单位 MB）")
    lines.append("- **通信时间**：累计模拟通信时间（单位 秒）")
    lines.append("- **平衡得分**：归一化后加权 `0.5×准确率 − 0.25×通信量 − 0.25×通信时间`，越高越平衡\n")

    for ds in datasets:
        ds_exps = [e for e in experiments if e["dataset"] == ds]
        if not ds_exps:
            continue

        lines.append(f"## {ds_labels[ds]}\n")

        # Collect metrics
        accs = [e["final_acc"] for e in ds_exps]
        comms = [e["total_comm"] for e in ds_exps]
        times = [e["total_sim_time"] for e in ds_exps]

        acc_norm = normalize(accs, higher_is_better=True)
        comm_norm = normalize(comms, higher_is_better=False)
        time_norm = normalize(times, higher_is_better=False)

        scores = 0.5 * acc_norm + 0.25 * comm_norm + 0.25 * time_norm

        # Attach scores
        for i, e in enumerate(ds_exps):
            e["score"] = scores[i]

        # Sort by score descending
        sorted_exps = sorted(ds_exps, key=lambda x: x["score"], reverse=True)

        # Full table
        lines.append("### 全部实验汇总\n")
        lines.append("| 实验目录 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |")
        lines.append("|----------|------|:---:|:---:|:---:|:---:|")
        for e in sorted_exps:
            lines.append(
                f"| {e['dir']} | {e['method']} | {e['final_acc']:.2f}% | {e['total_comm']:.2f} | {e['total_sim_time']:.2f} | {e['score']:.4f} |"
            )
        lines.append("")

        # Top-3 balanced
        lines.append("### 最平衡的 Top-3 配置\n")
        lines.append("| 排名 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |")
        lines.append("|------|------|:---:|:---:|:---:|:---:|")
        for rank, e in enumerate(sorted_exps[:3], 1):
            lines.append(
                f"| {rank} | {e['method']} | {e['final_acc']:.2f}% | {e['total_comm']:.2f} | {e['total_sim_time']:.2f} | {e['score']:.4f} |"
            )
        lines.append("")

    # Key findings
    lines.append("## 关键结论\n")
    for ds in datasets:
        ds_exps = [e for e in experiments if e["dataset"] == ds]
        if not ds_exps:
            continue
        best = max(ds_exps, key=lambda x: x["score"])
        lines.append(f"- **{ds_labels[ds]}**：最平衡配置为 `{best['method']}`（准确率 {best['final_acc']:.2f}%，通信 {best['total_comm']:.2f} MB，时间 {best['total_sim_time']:.2f} s）")
    lines.append("")

    output_path = Path("accuracy_result/experiment_summary_analysis.md")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary saved to: {output_path}")


# ---------------------------------------------------------------------------
# Step 3: Draw client selection accuracy curves
# ---------------------------------------------------------------------------
def draw_client_selection():
    datasets = ["mnist", "fashion_mnist", "cifar10"]
    ds_labels = {"mnist": "MNIST", "fashion_mnist": "Fashion-MNIST", "cifar10": "CIFAR-10"}
    methods = ["random", "sticky", "sketch_clustering", "poc", "tifl", "haccs", "oort"]

    out_dir = Path("accuracy_result/client_selection/pic")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Custom colors for 7 strategies
    colors = {
        "random": "#1f77b4",
        "sticky": "#ff7f0e",
        "sketch_clustering": "#2ca02c",
        "poc": "#d62728",
        "tifl": "#9467bd",
        "haccs": "#8c564b",
        "oort": "#e377c2",
    }

    p = Plotter(style=["science", "grid"], use_latex=False)
    # Override output dir
    p.output_dir = out_dir

    for ds in datasets:
        data_dict = {}
        for method in methods:
            exps = [e for e in experiments if e["dataset"] == ds and e["method"] == method and e["dir"] == "accuracy_client_selection"]
            if exps:
                e = exps[0]
                data_dict[method] = {"x": e["rounds"], "y": e["acc"]}

        if not data_dict:
            continue

        p.line(
            data=data_dict,
            xlabel="Communication Round",
            ylabel="Test Accuracy (%)",
            title=f"{ds_labels[ds]} — Client Selection Strategies",
            colors=colors,
            legend_loc="best",
            legend_ncol=1,
            legend_fontsize=9,
            filename=f"{ds}_client_selection_accuracy",
        )
        print(f"  Drawn: {ds}_client_selection_accuracy")


# ---------------------------------------------------------------------------
# Step 4: Draw vote ratio accuracy curves
# ---------------------------------------------------------------------------
def draw_vote_ratios():
    datasets = ["mnist", "fashion_mnist", "cifar10"]
    ds_labels = {"mnist": "MNIST", "fashion_mnist": "Fashion-MNIST", "cifar10": "CIFAR-10"}

    # Methods to draw: threshold 0.1-0.9, topk 0.1-0.9, union
    threshold_methods = [f"threshold_{x}" for x in [0.1, 0.3, 0.5, 0.7, 0.9]]
    topk_methods = [f"topk_{x}" for x in [0.1, 0.3, 0.5, 0.7, 0.9]]
    all_methods = threshold_methods + topk_methods + ["union"]

    # Label mapping
    label_map = {}
    for m in all_methods:
        if m.startswith("threshold_"):
            label_map[m] = "TH-" + m.split("_")[1]
        elif m.startswith("topk_"):
            label_map[m] = "RK-" + m.split("_")[1]
        elif m == "union":
            label_map[m] = "Union"

    out_dir = Path("accuracy_result/vote/pic")
    out_dir.mkdir(parents=True, exist_ok=True)

    p = Plotter(style=["science", "grid"], use_latex=False)
    p.output_dir = out_dir

    for ds in datasets:
        data_dict = {}
        for method in all_methods:
            # Skip topk_0.1 for non-MNIST datasets
            if method == "topk_0.1" and ds != "mnist":
                continue
            exps = [e for e in experiments if e["dataset"] == ds and e["method"] == method]
            if exps:
                e = exps[0]
                new_label = label_map.get(method, method)
                data_dict[new_label] = {"x": e["rounds"], "y": e["acc"]}

        if not data_dict:
            continue

        p.line(
            data=data_dict,
            xlabel="Communication Round",
            ylabel="Test Accuracy (%)",
            title=f"{ds_labels[ds]} — Voting Mechanisms",
            legend_loc="lower right",
            legend_ncol=2,
            legend_fontsize=10,
            filename=f"{ds}_vote_accuracy",
        )
        print(f"  Drawn: {ds}_vote_accuracy")


if __name__ == "__main__":
    print("Step 2: Generating summary analysis...")
    generate_summary()

    print("\nStep 3: Drawing client selection accuracy curves...")
    draw_client_selection()

    print("\nStep 4: Drawing vote ratio accuracy curves...")
    draw_vote_ratios()

    print("\nAll done!")
