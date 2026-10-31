#!/usr/bin/env python3
"""
Non-IID 实验 2×2 综合图（SciencePlots 风格）
============================================
生成 (a)(b) 折线图 + (c)(d) 热力图的 2×2 组合图。
支持多种 SCI 风格热力图配色。

数据来源：accuracy_baseline/{esafl,fedphe,maser,fedavg+ckks,ours}/noneiid_result
输出：tools/plot_experiment/plot_noniid_2x2/pic/
"""

import matplotlib.pyplot as plt

from noniid_common import (
    CUSTOM_RCPARAMS,
    HEATMAP_CMAPS,
    PLOTTER,
    load_data,
    save_dir,
    draw_line_subplot,
    draw_alpha_heatmap,
)


def draw_2x2(accuracy, alphas, cmap="YlGnBu", suffix=""):
    """绘制一张 2×2 组合图并保存。"""
    with plt.style.context(PLOTTER.style):
        plt.rcParams.update(CUSTOM_RCPARAMS)
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        axes = axes.flatten()

        draw_line_subplot(axes[0], "FMNIST", accuracy, alphas)
        axes[0].set_title("(a) FMNIST", fontsize=20, fontweight="bold", pad=10)

        draw_line_subplot(axes[1], "CIFAR-10", accuracy, alphas)
        axes[1].set_title("(b) CIFAR-10", fontsize=20, fontweight="bold", pad=10)

        draw_alpha_heatmap(axes[2], "FMNIST", accuracy, alphas, cmap=cmap)
        axes[2].set_title("(c) FMNIST", fontsize=20, fontweight="bold", pad=10)

        draw_alpha_heatmap(axes[3], "CIFAR-10", accuracy, alphas, cmap=cmap)
        axes[3].set_title("(d) CIFAR-10", fontsize=20, fontweight="bold", pad=10)

        plt.tight_layout()
        for ax in (axes[2], axes[3]):
            ax.grid(False)

        for fmt in ("png", "pdf"):
            fname = f"noniid_2x2{suffix}.{fmt}"
            fpath = save_dir / fname
            plt.savefig(fpath, dpi=300, bbox_inches="tight")
            print(f"[Saved] {fpath}")
        plt.close(fig)


def _format_axis_labels(ax):
    """将 X/Y 轴标签和刻度字设为 20，并加粗子图边框。"""
    ax.set_xlabel(ax.get_xlabel(), fontsize=20)
    ax.set_ylabel(ax.get_ylabel(), fontsize=20)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(20)
    for spine in ax.spines.values():
        spine.set_linewidth(2.5)


def draw_1x2(accuracy, alphas):
    """绘制 (a)(b) 两张折线图的 1×2 横向组合图并保存。"""
    with plt.style.context(PLOTTER.style):
        plt.rcParams.update(CUSTOM_RCPARAMS)
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        draw_line_subplot(axes[0], "FMNIST", accuracy, alphas)
        axes[0].set_title("(a) FMNIST", fontsize=20, fontweight="bold", pad=10)
        _format_axis_labels(axes[0])

        draw_line_subplot(axes[1], "CIFAR-10", accuracy, alphas)
        axes[1].set_title("(b) CIFAR-10", fontsize=20, fontweight="bold", pad=10)
        _format_axis_labels(axes[1])

        plt.tight_layout()
        for fmt in ("png", "pdf"):
            fpath = save_dir / f"noniid_1x2.{fmt}"
            plt.savefig(fpath, dpi=300, bbox_inches="tight")
            print(f"[Saved] {fpath}")
        plt.close(fig)


def main():
    accuracy, alphas = load_data()

    # 1×2 折线图（仅 (a)(b)）
    draw_1x2(accuracy, alphas)

    # 默认配色 2×2 组合图
    draw_2x2(accuracy, alphas, cmap="YlGnBu", suffix="")

    # 多种 SCI 风格配色 2×2 组合图
    for theme_name, cmap_name in HEATMAP_CMAPS:
        draw_2x2(accuracy, alphas, cmap=cmap_name, suffix=f"_{theme_name}")


if __name__ == "__main__":
    main()
