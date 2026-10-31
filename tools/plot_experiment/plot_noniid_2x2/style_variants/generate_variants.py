#!/usr/bin/env python3
"""
Non-IID 数据多风格可视化（SciencePlots）
==========================================
基于 ../script/noniid_data.json，为 FMNIST / CIFAR-10 生成多种类型、
多种 SciencePlots 风格的可视化图片，存放到本目录 pic/ 下。

要求：调用 scienceplots 包；风格 / 类型不少于 10 种；每张图同时展示两个数据集。
"""

import json
import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

matplotlib.use("Agg")
import scienceplots  # noqa: F401, E402

# ---------------------------------------------------------------------------
# 路径与数据
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PIC_DIR = SCRIPT_DIR / "pic"
PIC_DIR.mkdir(parents=True, exist_ok=True)

DATA_PATH = SCRIPT_DIR.parent / "script" / "noniid_data.json"
with open(DATA_PATH, encoding="utf-8") as f:
    RAW = json.load(f)

DATASETS = RAW["datasets"]          # ["FMNIST", "CIFAR-10"]
METHODS = RAW["methods"]            # ["Ours", "ESAFL", "MASER", "FedPHE", "FedAvg-CKKS"]
ALPHAS = RAW["alphas"]              # [0.1, 0.5, 1.0, 5.0, 10.0]
ACC = RAW["accuracy"]

COLORS = {
    "Ours": "#D62728",
    "ESAFL": "#1F77B4",
    "MASER": "#2CA02C",
    "FedPHE": "#FF7F0E",
    "FedAvg-CKKS": "#9467BD",
}
MARKERS = {"Ours": "o", "ESAFL": "s", "MASER": "^", "FedPHE": "D", "FedAvg-CKKS": "v"}


def get_values(dataset: str, method: str) -> np.ndarray:
    return np.array(ACC[dataset][method], dtype=float)


def save(fig, name: str):
    for fmt in ("png", "pdf"):
        fpath = PIC_DIR / f"{name}.{fmt}"
        fig.savefig(fpath, dpi=300, bbox_inches="tight")
        print(f"[Saved] {fpath}")
    plt.close(fig)


def style_context(style=None):
    """统一使用 SciencePlots + no-latex，避免缺少 LaTeX 环境。"""
    if style is None:
        style = ["science", "no-latex"]
    return plt.style.context(style)


def set_title_labels(ax, dataset: str):
    ax.set_title(dataset, fontweight="bold")
    ax.set_xlabel(r"Non-IID coefficient $\alpha$")
    ax.set_ylabel("Test Accuracy (%)")


# ---------------------------------------------------------------------------
# 01. 经典折线图（带标记）
# ---------------------------------------------------------------------------
def chart_line_markers():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, ds in zip(axes, DATASETS):
            for m in METHODS:
                ax.plot(ALPHAS, get_values(ds, m), marker=MARKERS[m], color=COLORS[m],
                        linewidth=2.2, markersize=8, label=m)
            ax.set_ylim(0, 100)
            ax.set_xticks(ALPHAS)
            ax.set_xticklabels([str(a) for a in ALPHAS])
            set_title_labels(ax, ds)
            ax.legend(loc="lower right", frameon=True)
            ax.grid(True, linestyle="--", alpha=0.35)
        fig.suptitle("Test Accuracy vs. Non-IID Coefficient", fontweight="bold", y=1.02)
        save(fig, "01_line_markers")


# ---------------------------------------------------------------------------
# 02. 分组柱状图
# ---------------------------------------------------------------------------
def chart_grouped_bar():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        x = np.arange(len(ALPHAS))
        width = 0.15
        for ax, ds in zip(axes, DATASETS):
            for i, m in enumerate(METHODS):
                offset = (i - 2) * width
                bars = ax.bar(x + offset, get_values(ds, m), width, label=m, color=COLORS[m])
                for bar in bars:
                    bar.set_edgecolor("black")
                    bar.set_linewidth(0.5)
            ax.set_ylim(0, 100)
            ax.set_xticks(x)
            ax.set_xticklabels([str(a) for a in ALPHAS])
            set_title_labels(ax, ds)
            ax.legend(loc="upper left", frameon=True, ncol=2)
            ax.grid(True, axis="y", linestyle="--", alpha=0.35)
        fig.suptitle("Grouped Bar Chart by Non-IID Coefficient", fontweight="bold", y=1.02)
        save(fig, "02_grouped_bar")


# ---------------------------------------------------------------------------
# 03. 水平柱状图（平均准确率排序）
# ---------------------------------------------------------------------------
def chart_horizontal_bar():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
        for ax, ds in zip(axes, DATASETS):
            avgs = [(m, float(np.mean(get_values(ds, m)))) for m in METHODS]
            avgs.sort(key=lambda t: t[1])
            names, vals = zip(*avgs)
            colors = [COLORS[n] for n in names]
            bars = ax.barh(names, vals, color=colors, edgecolor="black", linewidth=0.5)
            ax.set_xlim(0, 100)
            ax.set_xlabel("Average Test Accuracy (%)")
            ax.set_title(ds, fontweight="bold")
            for bar, val in zip(bars, vals):
                ax.text(val + 1, bar.get_y() + bar.get_height() / 2,
                        f"{val:.1f}", va="center", fontsize=10)
            ax.grid(True, axis="x", linestyle="--", alpha=0.35)
        fig.suptitle("Average Accuracy Ranking", fontweight="bold", y=1.02)
        save(fig, "03_horizontal_bar")


# ---------------------------------------------------------------------------
# 04. 雷达图
# ---------------------------------------------------------------------------
def chart_radar():
    with style_context():
        angles = np.linspace(0, 2 * np.pi, len(ALPHAS), endpoint=False).tolist()
        angles += angles[:1]
        fig, axes = plt.subplots(1, 2, figsize=(12, 6), subplot_kw=dict(polar=True))
        for ax, ds in zip(axes, DATASETS):
            for m in METHODS:
                vals = get_values(ds, m).tolist()
                vals += vals[:1]
                ax.plot(angles, vals, marker=MARKERS[m], color=COLORS[m], linewidth=2, label=m)
                ax.fill(angles, vals, color=COLORS[m], alpha=0.08)
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([str(a) for a in ALPHAS])
            ax.set_ylim(0, 100)
            ax.set_title(ds, fontweight="bold", y=1.08)
            ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=True)
        fig.suptitle("Radar Chart of Accuracy Across Heterogeneity Levels", fontweight="bold", y=1.02)
        save(fig, "04_radar")


# ---------------------------------------------------------------------------
# 05. 棒棒糖图
# ---------------------------------------------------------------------------
def chart_lollipop():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        x = np.arange(len(ALPHAS))
        for ax, ds in zip(axes, DATASETS):
            for i, m in enumerate(METHODS):
                vals = get_values(ds, m)
                offset = (i - 2) * 0.12
                ax.hlines(y=vals, xmin=x + offset - 0.04, xmax=x + offset + 0.04,
                          color=COLORS[m], linewidth=2)
                ax.scatter(x + offset, vals, color=COLORS[m], marker=MARKERS[m], s=90, zorder=3)
            ax.set_ylim(0, 100)
            ax.set_xticks(x)
            ax.set_xticklabels([str(a) for a in ALPHAS])
            set_title_labels(ax, ds)
            # 自定义图例
            handles = [plt.Line2D([0], [0], color=COLORS[m], marker=MARKERS[m], linestyle="-",
                                  markersize=8, label=m) for m in METHODS]
            ax.legend(handles=handles, loc="lower right", frameon=True, ncol=2)
            ax.grid(True, axis="y", linestyle="--", alpha=0.35)
        fig.suptitle("Lollipop Chart of Accuracy", fontweight="bold", y=1.02)
        save(fig, "05_lollipop")


# ---------------------------------------------------------------------------
# 06. 斜率图（α=0.1 → α=10）
# ---------------------------------------------------------------------------
def chart_slope():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(11, 6))
        x = [0, 1]
        labels = ["0.1", "10"]
        for ax, ds in zip(axes, DATASETS):
            for m in METHODS:
                vals = [ACC[ds][m][0], ACC[ds][m][-1]]
                ax.plot(x, vals, marker=MARKERS[m], color=COLORS[m], linewidth=2.5,
                        markersize=10, label=m)
                # 右端标注
                ax.text(1.04, vals[1], m, color=COLORS[m], va="center", fontsize=10,
                        fontweight="bold" if m == "Ours" else "normal")
            ax.set_xticks(x)
            ax.set_xticklabels(labels)
            ax.set_ylim(0, 100)
            ax.set_xlim(-0.15, 1.25)
            ax.set_xlabel(r"Non-IID coefficient $\alpha$")
            ax.set_ylabel("Test Accuracy (%)")
            ax.set_title(ds, fontweight="bold")
            ax.grid(True, axis="y", linestyle="--", alpha=0.35)
        fig.suptitle(r"Slope Chart: Accuracy from $\alpha=0.1$ to $\alpha=10$", fontweight="bold", y=1.02)
        save(fig, "06_slope")


# ---------------------------------------------------------------------------
# 07. 热力图
# ---------------------------------------------------------------------------
def chart_heatmap():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, ds in zip(axes, DATASETS):
            data = np.array([get_values(ds, m) for m in METHODS])
            im = ax.imshow(data, cmap="YlGnBu", aspect="auto", vmin=0, vmax=100)
            for i, m in enumerate(METHODS):
                for j, a in enumerate(ALPHAS):
                    ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center",
                            color="black", fontsize=11)
            ax.set_xticks(np.arange(len(ALPHAS)))
            ax.set_xticklabels([str(a) for a in ALPHAS])
            ax.set_yticks(np.arange(len(METHODS)))
            ax.set_yticklabels(METHODS)
            ax.set_xlabel(r"Non-IID coefficient $\alpha$")
            ax.set_title(ds, fontweight="bold")
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label("Accuracy (%)")
        fig.suptitle("Heatmap of Test Accuracy", fontweight="bold", y=1.02)
        save(fig, "07_heatmap")


# ---------------------------------------------------------------------------
# 08. 气泡图
# ---------------------------------------------------------------------------
def chart_bubble():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
        for ax, ds in zip(axes, DATASETS):
            for i, m in enumerate(METHODS):
                vals = get_values(ds, m)
                sizes = (vals / 100) * 400 + 50
                ax.scatter(ALPHAS, [i] * len(ALPHAS), s=sizes, c=COLORS[m],
                           marker=MARKERS[m], edgecolors="black", linewidths=0.5, label=m)
                for a, v in zip(ALPHAS, vals):
                    ax.text(a, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white")
            ax.set_yticks(np.arange(len(METHODS)))
            ax.set_yticklabels(METHODS)
            ax.set_xticks(ALPHAS)
            ax.set_xticklabels([str(a) for a in ALPHAS])
            ax.set_xlabel(r"Non-IID coefficient $\alpha$")
            ax.set_title(ds, fontweight="bold")
            ax.set_ylim(-0.5, len(METHODS) - 0.5)
            ax.grid(True, axis="x", linestyle="--", alpha=0.35)
        fig.suptitle("Bubble Chart: Accuracy Encoded by Marker Size", fontweight="bold", y=1.02)
        save(fig, "08_bubble")


# ---------------------------------------------------------------------------
# 09. Cleveland 点图
# ---------------------------------------------------------------------------
def chart_dot_plot():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
        for ax, ds in zip(axes, DATASETS):
            for i, m in enumerate(METHODS):
                vals = get_values(ds, m)
                y = np.full_like(vals, i) + np.linspace(-0.25, 0.25, len(vals))
                ax.scatter(vals, y, color=COLORS[m], marker=MARKERS[m], s=100, zorder=3)
                for v, yy, a in zip(vals, y, ALPHAS):
                    ax.text(v + 1.5, yy, f"{a}", va="center", fontsize=8)
            ax.set_yticks(np.arange(len(METHODS)))
            ax.set_yticklabels(METHODS)
            ax.set_xlim(0, 105)
            ax.set_xlabel("Test Accuracy (%)")
            ax.set_title(ds, fontweight="bold")
            ax.grid(True, axis="x", linestyle="--", alpha=0.35)
        fig.suptitle("Cleveland Dot Plot", fontweight="bold", y=1.02)
        save(fig, "09_dot_plot")


# ---------------------------------------------------------------------------
# 10. 小多图（每个方法一个子图）
# ---------------------------------------------------------------------------
def chart_small_multiples():
    with style_context():
        fig, axes = plt.subplots(2, len(METHODS), figsize=(16, 7))
        for row, ds in enumerate(DATASETS):
            for col, m in enumerate(METHODS):
                ax = axes[row, col]
                vals = get_values(ds, m)
                ax.plot(ALPHAS, vals, marker=MARKERS[m], color=COLORS[m], linewidth=2.5,
                        markersize=8)
                ax.set_ylim(0, 100)
                ax.set_xticks(ALPHAS)
                ax.set_xticklabels([str(a) for a in ALPHAS], fontsize=8)
                ax.set_title(f"{m}\n({ds})", fontsize=10, fontweight="bold")
                ax.grid(True, linestyle="--", alpha=0.35)
                if col == 0:
                    ax.set_ylabel("Accuracy (%)")
        fig.suptitle("Small Multiples: One Panel Per Method", fontweight="bold", y=1.01)
        save(fig, "10_small_multiples")


# ---------------------------------------------------------------------------
# 11. 哑铃图（α=0.1 与 α=10 范围）
# ---------------------------------------------------------------------------
def chart_dumbbell():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
        for ax, ds in zip(axes, DATASETS):
            y = np.arange(len(METHODS))
            start = [ACC[ds][m][0] for m in METHODS]
            end = [ACC[ds][m][-1] for m in METHODS]
            for i, m in enumerate(METHODS):
                ax.plot([start[i], end[i]], [y[i], y[i]], color="gray", linewidth=2, zorder=1)
                ax.scatter(start[i], y[i], color=COLORS[m], marker=MARKERS[m], s=120,
                           edgecolors="black", linewidths=0.5, zorder=3)
                ax.scatter(end[i], y[i], color=COLORS[m], marker=MARKERS[m], s=120,
                           edgecolors="black", linewidths=0.5, zorder=3)
                ax.text(start[i] - 2, y[i], f"{start[i]:.1f}", ha="right", va="center", fontsize=9)
                ax.text(end[i] + 2, y[i], f"{end[i]:.1f}", ha="left", va="center", fontsize=9)
            ax.set_yticks(y)
            ax.set_yticklabels(METHODS)
            ax.set_xlim(0, 100)
            ax.set_xlabel("Test Accuracy (%)")
            ax.set_title(ds, fontweight="bold")
            ax.grid(True, axis="x", linestyle="--", alpha=0.35)
        fig.suptitle(r"Dumbbell Chart: Accuracy Range from $\alpha=0.1$ to $\alpha=10$", fontweight="bold", y=1.02)
        save(fig, "11_dumbbell")


# ---------------------------------------------------------------------------
# 12. 折线 + 面积填充（强调变化幅度）
# ---------------------------------------------------------------------------
def chart_area_line():
    with style_context():
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for ax, ds in zip(axes, DATASETS):
            for m in METHODS:
                vals = get_values(ds, m)
                ax.fill_between(ALPHAS, vals, alpha=0.15, color=COLORS[m])
                ax.plot(ALPHAS, vals, marker=MARKERS[m], color=COLORS[m], linewidth=2.2,
                        markersize=8, label=m)
            ax.set_ylim(0, 100)
            ax.set_xticks(ALPHAS)
            ax.set_xticklabels([str(a) for a in ALPHAS])
            set_title_labels(ax, ds)
            ax.legend(loc="lower right", frameon=True)
            ax.grid(True, linestyle="--", alpha=0.35)
        fig.suptitle("Line Chart with Area Filling", fontweight="bold", y=1.02)
        save(fig, "12_area_line")


CHARTS = [
    chart_line_markers,
    chart_grouped_bar,
    chart_horizontal_bar,
    chart_radar,
    chart_lollipop,
    chart_slope,
    chart_heatmap,
    chart_bubble,
    chart_dot_plot,
    chart_small_multiples,
    chart_dumbbell,
    chart_area_line,
]


def main():
    # 清空旧图
    for old in PIC_DIR.glob("*"):
        old.unlink()
    print(f"[Cleaned] {PIC_DIR}")

    for fn in CHARTS:
        try:
            fn()
        except Exception as e:
            print(f"[ERROR] {fn.__name__}: {e}")

    print(f"\n[DONE] 共生成 {len(CHARTS)} 种风格、{len(CHARTS) * 2} 张图 -> {PIC_DIR}")


if __name__ == "__main__":
    main()
