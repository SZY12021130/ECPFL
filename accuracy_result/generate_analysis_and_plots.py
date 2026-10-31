#!/usr/bin/env python3
"""Generate summary analysis + draw accuracy curves with multiple elegant themes."""

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
with open("experiment_data.pkl", "rb") as f:
    experiments = pickle.load(f)

# ---------------------------------------------------------------------------
# Helper: normalize to [0, 1]
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
# Elegant Color Palettes & Line Styles
# ---------------------------------------------------------------------------

# ---- Client Selection (7 strategies) ----
CS_THEMES = {
    "classic": {
        "colors": {
            "random": "#1f77b4", "sticky": "#ff7f0e", "sketch_clustering": "#2ca02c",
            "poc": "#d62728", "tifl": "#9467bd", "haccs": "#8c564b", "oort": "#e377c2",
        },
        "linestyles": {
            "random": "-", "sticky": "-", "sketch_clustering": "-",
            "poc": "-", "tifl": "-", "haccs": "-", "oort": "-",
        },
        "linewidth": 1.8,
    },
    "vibrant": {
        "colors": {
            "random": "#E31A1C", "sticky": "#1F78B4", "sketch_clustering": "#33A02C",
            "poc": "#FF7F00", "tifl": "#6A3D9A", "haccs": "#08519C", "oort": "#FB9A99",
        },
        "linestyles": {
            "random": "-", "sticky": "--", "sketch_clustering": "-.",
            "poc": ":", "tifl": (0, (5, 1)), "haccs": (0, (3, 1, 1, 1)), "oort": "-",
        },
        "linewidth": 2.2,
    },
    "nature": {
        "colors": {
            "random": "#2E8B57", "sticky": "#4682B4", "sketch_clustering": "#DAA520",
            "poc": "#CD5C5C", "tifl": "#708090", "haccs": "#8B4513", "oort": "#9370DB",
        },
        "linestyles": {
            "random": "-", "sticky": "--", "sketch_clustering": "-.",
            "poc": ":", "tifl": (0, (5, 1)), "haccs": (0, (3, 1, 1, 1)), "oort": "-",
        },
        "linewidth": 2.0,
    },
    "cool_warm": {
        "colors": {
            "random": "#E63946", "sticky": "#457B9D", "sketch_clustering": "#2A9D8F",
            "poc": "#F4A261", "tifl": "#264653", "haccs": "#E76F51", "oort": "#A8DADC",
        },
        "linestyles": {
            "random": "-", "sticky": "--", "sketch_clustering": "-.",
            "poc": ":", "tifl": (0, (5, 1)), "haccs": (0, (3, 1, 1, 1)), "oort": "-",
        },
        "linewidth": 2.0,
    },
}

# ---- Vote Ratios (TH warm + RK cool + Union highlight) ----
VOTE_THEMES = {
    "grouped": {
        "colors": {
            "TH-0.1": "#FF4444", "TH-0.3": "#FF8800", "TH-0.5": "#FFAA00",
            "TH-0.7": "#CC6600", "TH-0.9": "#993300",
            "RK-0.1": "#0066FF", "RK-0.3": "#0088CC", "RK-0.5": "#00AAAA",
            "RK-0.7": "#3366CC", "RK-0.9": "#2244AA",
            "UN": "#111111",
        },
        "linestyles": {
            "TH-0.1": "-", "TH-0.3": "-", "TH-0.5": "-",
            "TH-0.7": "-", "TH-0.9": "-",
            "RK-0.1": "--", "RK-0.3": "--", "RK-0.5": "--",
            "RK-0.7": "--", "RK-0.9": "--",
            "UN": "-",
        },
        "linewidth": 2.0,
        "UN_linewidth": 2.8,
    },
    "vibrant": {
        "colors": {
            "TH-0.1": "#E31A1C", "TH-0.3": "#FF7F00", "TH-0.5": "#33A02C",
            "TH-0.7": "#1F78B4", "TH-0.9": "#6A3D9A",
            "RK-0.1": "#FB9A99", "RK-0.3": "#A6CEE3", "RK-0.5": "#B2DF8A",
            "RK-0.7": "#FDBF6F", "RK-0.9": "#CAB2D6",
            "UN": "#111111",
        },
        "linestyles": {
            "TH-0.1": "-", "TH-0.3": "-", "TH-0.5": "-",
            "TH-0.7": "-", "TH-0.9": "-",
            "RK-0.1": "--", "RK-0.3": "--", "RK-0.5": "--",
            "RK-0.7": "--", "RK-0.9": "--",
            "UN": "-",
        },
        "linewidth": 2.0,
        "UN_linewidth": 2.8,
    },
    "elegant": {
        "colors": {
            "TH-0.1": "#C0392B", "TH-0.3": "#E67E22", "TH-0.5": "#F1C40F",
            "TH-0.7": "#8E44AD", "TH-0.9": "#2C3E50",
            "RK-0.1": "#2980B9", "RK-0.3": "#16A085", "RK-0.5": "#27AE60",
            "RK-0.7": "#2980B9", "RK-0.9": "#8E44AD",
            "UN": "#000000",
        },
        "linestyles": {
            "TH-0.1": "-", "TH-0.3": "-", "TH-0.5": "-",
            "TH-0.7": "-", "TH-0.9": "-",
            "RK-0.1": "--", "RK-0.3": "--", "RK-0.5": "--",
            "RK-0.7": "--", "RK-0.9": "--",
            "UN": "-",
        },
        "linewidth": 2.0,
        "UN_linewidth": 2.8,
    },
}


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

        accs = [e["final_acc"] for e in ds_exps]
        comms = [e["total_comm"] for e in ds_exps]
        times = [e["total_sim_time"] for e in ds_exps]

        acc_norm = normalize(accs, higher_is_better=True)
        comm_norm = normalize(comms, higher_is_better=False)
        time_norm = normalize(times, higher_is_better=False)

        scores = 0.5 * acc_norm + 0.25 * comm_norm + 0.25 * time_norm

        for i, e in enumerate(ds_exps):
            e["score"] = scores[i]

        sorted_exps = sorted(ds_exps, key=lambda x: x["score"], reverse=True)

        lines.append("### 全部实验汇总\n")
        lines.append("| 实验目录 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |")
        lines.append("|----------|------|:---:|:---:|:---:|:---:|")
        for e in sorted_exps:
            lines.append(
                f"| {e['dir']} | {e['method']} | {e['final_acc']:.2f}% | {e['total_comm']:.2f} | {e['total_sim_time']:.2f} | {e['score']:.4f} |"
            )
        lines.append("")

        lines.append("### 最平衡的 Top-3 配置\n")
        lines.append("| 排名 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |")
        lines.append("|------|------|:---:|:---:|:---:|:---:|")
        for rank, e in enumerate(sorted_exps[:3], 1):
            lines.append(
                f"| {rank} | {e['method']} | {e['final_acc']:.2f}% | {e['total_comm']:.2f} | {e['total_sim_time']:.2f} | {e['score']:.4f} |"
            )
        lines.append("")

    lines.append("## 关键结论\n")
    for ds in datasets:
        ds_exps = [e for e in experiments if e["dataset"] == ds]
        if not ds_exps:
            continue
        best = max(ds_exps, key=lambda x: x["score"])
        lines.append(f"- **{ds_labels[ds]}**：最平衡配置为 `{best['method']}`（准确率 {best['final_acc']:.2f}%，通信 {best['total_comm']:.2f} MB，时间 {best['total_sim_time']:.2f} s）")
    lines.append("")

    output_path = Path("experiment_summary_analysis.md")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary saved to: {output_path}")


# ---------------------------------------------------------------------------
# Step 3: Draw client selection accuracy curves (multi-theme)
# ---------------------------------------------------------------------------
def draw_client_selection():
    datasets = ["mnist", "fashion_mnist", "cifar10"]
    ds_labels = {"mnist": "MNIST", "fashion_mnist": "Fashion-MNIST", "cifar10": "CIFAR-10"}
    methods = ["random", "sticky", "sketch_clustering", "poc", "tifl", "haccs", "oort"]

    out_dir = Path("client_selection/pic")
    out_dir.mkdir(parents=True, exist_ok=True)

    for theme_name, theme_cfg in CS_THEMES.items():
        p = Plotter(
            style=["science", "grid"],
            use_latex=False,
            font_size=16,
            figsize=(6, 4),
            dpi=300,
            output_dir=out_dir,
        )

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
                title=f"{ds_labels[ds]} — Client Selection",
                colors=theme_cfg["colors"],
                linestyles=theme_cfg["linestyles"],
                linewidth=theme_cfg["linewidth"],
                legend_loc="best",
                legend_ncol=1,
                filename=f"{ds}_client_selection_accuracy_{theme_name}",
            )
            print(f"  Drawn: {ds}_client_selection_accuracy_{theme_name}")


# ---------------------------------------------------------------------------
# Step 4: Draw vote ratio accuracy curves (multi-theme)
# ---------------------------------------------------------------------------
def draw_vote_ratios():
    datasets = ["mnist", "fashion_mnist", "cifar10"]
    ds_labels = {"mnist": "MNIST", "fashion_mnist": "Fashion-MNIST", "cifar10": "CIFAR-10"}

    threshold_methods = [f"threshold_{x}" for x in [0.1, 0.3, 0.5, 0.7, 0.9]]
    topk_methods = [f"topk_{x}" for x in [0.1, 0.3, 0.5, 0.7, 0.9]]
    all_methods = threshold_methods + topk_methods + ["union"]

    label_map = {}
    for m in all_methods:
        if m.startswith("threshold_"):
            label_map[m] = "TH-" + m.split("_")[1]
        elif m.startswith("topk_"):
            label_map[m] = "RK-" + m.split("_")[1]
        elif m == "union":
            label_map[m] = "UN"

    out_dir = Path("vote/pic")
    out_dir.mkdir(parents=True, exist_ok=True)

    for theme_name, theme_cfg in VOTE_THEMES.items():
        p = Plotter(
            style=["science", "grid"],
            use_latex=False,
            font_size=16,
            figsize=(6, 4),
            dpi=300,
            output_dir=out_dir,
        )

        for ds in datasets:
            data_dict = {}
            linestyles_for_ds = {}
            colors_for_ds = {}

            for method in all_methods:
                if method == "topk_0.1" and ds != "mnist":
                    continue
                exps = [e for e in experiments if e["dataset"] == ds and e["method"] == method]
                if exps:
                    e = exps[0]
                    new_label = label_map.get(method, method)
                    data_dict[new_label] = {"x": e["rounds"], "y": e["acc"]}
                    colors_for_ds[new_label] = theme_cfg["colors"].get(new_label, "#333333")
                    linestyles_for_ds[new_label] = theme_cfg["linestyles"].get(new_label, "-")

            if not data_dict:
                continue

            p.line(
                data=data_dict,
                xlabel="Communication Round",
                ylabel="Test Accuracy (%)",
                title=f"{ds_labels[ds]} — Voting Mechanisms",
                colors=colors_for_ds,
                linestyles=linestyles_for_ds,
                linewidth=theme_cfg["linewidth"],
                legend_loc="lower right",
                legend_ncol=2,
                filename=f"{ds}_vote_accuracy_{theme_name}",
            )
            print(f"  Drawn: {ds}_vote_accuracy_{theme_name}")


if __name__ == "__main__":
    print("Step 2: Generating summary analysis...")
    generate_summary()

    print("\nStep 3: Drawing client selection accuracy curves...")
    draw_client_selection()

    print("\nStep 4: Drawing vote ratio accuracy curves...")
    draw_vote_ratios()

    print("\nAll done!")
