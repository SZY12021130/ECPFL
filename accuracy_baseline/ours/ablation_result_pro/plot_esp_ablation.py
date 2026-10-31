#!/usr/bin/env python3
"""
ESP 模块消融实验绘图脚本
=========================
读取 esp_ablation_data.json，生成 ESP 消融实验的柱状图。

输出：accuracy_baseline/ours/ablation_result/pic/esp_ablation.{png,pdf}
"""

import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# 路径设置
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[2]
pic_dir = script_dir / "pic"
pic_dir.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(project_root))
from tools.plotter import Plotter  # noqa: E402

# ---------------------------------------------------------------------------
# 可视化配置
# ---------------------------------------------------------------------------
matplotlib.use("Agg")
PLOTTER = Plotter(style=["science", "grid"], use_latex=False, font_size=14)

CUSTOM_RCPARAMS = {
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "axes.linewidth": 1.5,
    "xtick.major.width": 1.2,
    "ytick.major.width": 1.2,
    "xtick.major.size": 5,
    "ytick.major.size": 5,
}


def main():
    data_path = script_dir / "esp_ablation_data.json"
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    experiments = data["experiments"]
    labels = [exp["label"] for exp in experiments]
    ac = [exp["AC"] for exp in experiments]
    uv = [exp["UV_MB"] for exp in experiments]
    tt = [exp["TT_H"] for exp in experiments]

    x = np.arange(len(labels))
    width = 0.6

    # 默认颜色，最后一根柱子（完整 ESP）使用高亮色
    bar_colors = ["#4C78A8"] * (len(labels) - 1) + ["#E45756"]

    with plt.style.context(PLOTTER.style):
        plt.rcParams.update(CUSTOM_RCPARAMS)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

        # (1) 测试准确率
        ax = axes[0]
        bars = ax.bar(x, ac, width, color=bar_colors, edgecolor="black", linewidth=1.0)
        ax.set_ylabel("Test Accuracy (%)")
        ax.set_title("(a) Accuracy")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, ac):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.5,
                f"{val:.1f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        # (2) 上传通信量
        ax = axes[1]
        bars = ax.bar(x, uv, width, color=bar_colors, edgecolor="black", linewidth=1.0)
        ax.set_ylabel("Upload Volume (MB)")
        ax.set_title("(b) Communication Cost")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, uv):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(uv) * 0.02,
                f"{val:.0f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=0,
            )

        # (3) 总训练时间
        ax = axes[2]
        bars = ax.bar(x, tt, width, color=bar_colors, edgecolor="black", linewidth=1.0)
        ax.set_ylabel("Total Time (h)")
        ax.set_title("(c) Training Time")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, tt):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(tt) * 0.02,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        fig.suptitle(
            f"ESP Module Ablation on {data['dataset']} ({data['model']}, {data['note']})",
            fontsize=18,
            fontweight="bold",
            y=1.02,
        )

        plt.tight_layout()
        for fmt in ("png", "pdf"):
            fpath = pic_dir / f"esp_ablation.{fmt}"
            plt.savefig(fpath, dpi=300, bbox_inches="tight")
            print(f"[Saved] {fpath}")
        plt.close(fig)


if __name__ == "__main__":
    main()
