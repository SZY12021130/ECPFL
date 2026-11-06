#!/usr/bin/env python3
"""
Non-IID 阶梯图 1x2 组合版
=========================
把 noniid_line_FMNIST_step 与 noniid_line_CIFAR10_step 两张阶梯图合成
一行两列，顶部标题分别为 (a) FMNIST 与 (b) CIFAR-10。

尺寸：单个子图绘图区 3.4835 x 2.657 in，与 method_comparison_contrast
（tools/plot_experiment/plot_compare，一行 4 子图）的单面板实测尺寸一致。

刻度数字 15.5 pt（加粗）、轴标题 18 pt（常规粗细）、Times serif——
与 AAAAA_Rework/vis/comm_volume_clients 一致的排版规格。

数据来源：script/noniid_data.json（由 noniid_common.load_data 提供）
输出：    tools/plot_experiment/plot_noniid_2x2/pic/noniid_step_1x2[_palette].png|pdf

用法：
    python plot_noniid_step_1x2.py                     # 默认配色（noniid_common.COLORS）
    python plot_noniid_step_1x2.py --palette all       # 默认 + 5 组配色全部输出
    python plot_noniid_step_1x2.py --palette okabe_ito # 指定单组
"""

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from noniid_common import (
    ALPHAS,
    COLORS,
    LINESTYLES,
    MARKERS,
    METHOD_ORDER,
    PLOTTER,
    Y_LIM,
    Y_TICK_STEP,
    load_data,
    save_dir,
)

matplotlib.use("Agg")

# ---- 与 comm_volume_clients 一致的字号规格 ----
FS_TICK = 15.5        # 刻度数字（加粗）
FS_AXIS = 18.0        # 轴标题（常规粗细）
FS_TITLE = 18.0       # 子图顶部 (a)/(b) 标题
FS_LEGEND = 12.0      # 图例

# ---- 轴线与刻度线宽：与 method_comparison_contrast 完全一致 ----
SPINE_LW = 1.8
TICK_WIDTH = 1.5
TICK_LENGTH = 5

# 显示名（与 method_comparison_contrast 的写法一致：FedAvg+CKKS 用加号）
DISPLAY_LABELS = {m: ("FedAvg+CKKS" if m == "FedAvg-CKKS" else m)
                  for m in METHOD_ORDER}

# ---- 面板尺寸：与 method_comparison_contrast 单面板实测一致 ----
PANEL_W = 3.4835      # 绘图区宽（in）
PANEL_H = 2.657       # 绘图区高（in）
M_LEFT = 0.70         # 左边距：18pt 纵轴标题 + 刻度
M_RIGHT = 0.10        # 右边距：无右侧标签
M_GAP = 0.75          # 两面板间距：右面板纵轴标注区
M_BOTTOM = 0.59       # 下边距：横轴标题 + 刻度
M_TOP = 0.42          # 上边距：(a)/(b) 标题
FIG_W = M_LEFT + PANEL_W + M_GAP + PANEL_W + M_RIGHT      # = 8.517
FIG_H = M_TOP + PANEL_H + M_BOTTOM                        # = 3.667
LEFT_F = M_LEFT / FIG_W
RIGHT_F = 1.0 - M_RIGHT / FIG_W
BOTTOM_F = M_BOTTOM / FIG_H
TOP_F = (M_BOTTOM + PANEL_H) / FIG_H
WSPACE_F = M_GAP / PANEL_W        # wspace 是“间距 / 单面板宽”的比值

# ---- 拆分版（单面板）：绘图区尺寸不变，去掉顶部 (a)/(b) 标题 ----
M_TOP_SPLIT = 0.10    # 无标题，只留刻度呼吸位
SPLIT_W = M_LEFT + PANEL_W + M_RIGHT                      # = 4.2835
SPLIT_H = M_TOP_SPLIT + PANEL_H + M_BOTTOM                # = 3.347
S_LEFT_F = M_LEFT / SPLIT_W
S_RIGHT_F = 1.0 - M_RIGHT / SPLIT_W
S_BOTTOM_F = M_BOTTOM / SPLIT_H
S_TOP_F = (M_BOTTOM + PANEL_H) / SPLIT_H

# 面板标识：文件名后缀 / 数据集 / （组合图用的）标题
PANELS = [
    ("a_fmnist", "FMNIST", "(a) FMNIST"),
    ("b_cifar10", "CIFAR-10", "(b) CIFAR-10"),
]

FONT_FALLBACKS = [
    "Times New Roman", "Times", "Nimbus Roman", "Nimbus Roman No9 L",
    "TeX Gyre Termes", "Liberation Serif", "FreeSerif", "DejaVu Serif",
]

# ---- 5 组扩展配色（默认配色为 noniid_common.COLORS）----
# 每组的 ECPFL（我们的方法）都用最醒目的暖色高亮
PALETTES = {
    "okabe_ito": {  # Okabe-Ito 色盲友好
        "ECPFL": "#D55E00", "ESAFL": "#0072B2", "MASER": "#009E73",
        "FedPHE": "#E69F00", "FedAvg-CKKS": "#CC79A7",
    },
    "npg": {        # Nature Publishing Group
        "ECPFL": "#E64B35", "ESAFL": "#4DBBD5", "MASER": "#00A087",
        "FedPHE": "#3C5488", "FedAvg-CKKS": "#7E6148",
    },
    "set1": {       # ColorBrewer Set1 高饱和
        "ECPFL": "#E41A1C", "ESAFL": "#377EB8", "MASER": "#4DAF4A",
        "FedPHE": "#984EA3", "FedAvg-CKKS": "#FF7F00",
    },
    "dark2": {      # ColorBrewer Dark2
        "ECPFL": "#D95F02", "ESAFL": "#1B9E77", "MASER": "#7570B3",
        "FedPHE": "#E7298A", "FedAvg-CKKS": "#666666",
    },
    "muted": {      # 低饱和沉稳色（与默认 tab10 风明显区分）
        "ECPFL": "#A63603", "ESAFL": "#08519C", "MASER": "#238B45",
        "FedPHE": "#54278F", "FedAvg-CKKS": "#252525",
    },
}


def apply_style() -> None:
    """science + grid 样式 + Times 字体；font.weight=bold 让刻度加粗，
    轴标题单独用 fontweight='normal' 压回常规粗细。"""
    plt.rcdefaults()
    for s in PLOTTER.style:
        plt.style.use(s)
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": FONT_FALLBACKS,
        "mathtext.fontset": "stix",
        "font.weight": "bold",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "xtick.labelsize": FS_TICK,
        "ytick.labelsize": FS_TICK,
        "xtick.top": True,
        "ytick.right": True,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,
        "savefig.bbox": "standard",
    })


def draw_step_panel(ax, dataset: str, accuracy: dict, alphas: list,
                    colors: dict) -> None:
    """阶梯折线 + 空心标记点，画法与 noniid_line_*_step 完全一致。"""
    x = np.arange(len(alphas))
    for method in METHOD_ORDER:
        accs = [accuracy[method][dataset].get(a, np.nan) for a in alphas]
        is_ours = method == "ECPFL"
        ax.step(
            x, accs, where="mid",
            color=colors[method], linestyle=LINESTYLES[method],
            linewidth=2.4 if is_ours else 1.6,
            alpha=1.0 if is_ours else 0.8,
            label=DISPLAY_LABELS[method], zorder=3,
        )
        ax.scatter(
            x, accs,
            color=colors[method], marker=MARKERS[method],
            s=85 if is_ours else 60,
            edgecolors="white", linewidths=0.9,
            zorder=5 if is_ours else 4,
        )

    lo, hi = Y_LIM[dataset]
    ax.set_ylim(lo, hi)
    ax.set_yticks(np.arange(lo, hi + 1e-9, Y_TICK_STEP))
    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas])
    ax.set_xlim(-0.35, len(alphas) - 0.65)

    # 浅色虚线网格 + 四边向内刻度（线宽与 method_comparison_contrast 一致）
    ax.grid(True, axis="y", linestyle="--", linewidth=0.55, alpha=0.40)
    ax.set_axisbelow(True)
    ax.tick_params(width=TICK_WIDTH, length=TICK_LENGTH)

    # 轴标题：18 pt、常规粗细（font.weight=bold 会被这里压回）
    ax.set_xlabel(r"Non-IID $\alpha$", fontsize=FS_AXIS,
                  fontweight="normal", labelpad=5)
    ax.set_ylabel("Test Accuracy (%)", fontsize=FS_AXIS, fontweight="normal",
                  labelpad=4)

    for s_ in ax.spines.values():
        s_.set_linewidth(SPINE_LW)


def add_legend(ax) -> None:
    """右下角图例：顺序反转（FedAvg+CKKS 最上）；全局 bold，这里压回常规。"""
    handles, labels = ax.get_legend_handles_labels()
    leg = ax.legend(handles=handles[::-1], labels=labels[::-1],
                    loc="lower right", fontsize=FS_LEGEND,
                    frameon=True, fancybox=False, framealpha=0.95,
                    edgecolor="#888888", facecolor="white",
                    borderpad=0.30, labelspacing=0.28,
                    handlelength=1.9, handletextpad=0.55,
                    borderaxespad=0.35)
    leg.get_frame().set_linewidth(0.7)
    for t in leg.get_texts():
        t.set_fontweight("normal")


def build_figure(accuracy: dict, alphas: list, colors: dict):
    fig, axes = plt.subplots(1, 2, figsize=(FIG_W, FIG_H))
    fig.subplots_adjust(left=LEFT_F, right=RIGHT_F, bottom=BOTTOM_F,
                        top=TOP_F, wspace=WSPACE_F)

    for ax, (_suffix, ds, title) in zip(axes, PANELS):
        draw_step_panel(ax, ds, accuracy, alphas, colors)
        ax.set_title(title, fontsize=FS_TITLE, fontweight="normal", pad=8)
        add_legend(ax)
    return fig


def build_panel(dataset: str, accuracy: dict, alphas: list, colors: dict):
    """拆分的单面板：绘图区仍是 3.4835 x 2.657 in，但不画顶部 (a)/(b) 标题。"""
    fig, ax = plt.subplots(figsize=(SPLIT_W, SPLIT_H))
    fig.subplots_adjust(left=S_LEFT_F, right=S_RIGHT_F, bottom=S_BOTTOM_F,
                        top=S_TOP_F)
    draw_step_panel(ax, dataset, accuracy, alphas, colors)
    add_legend(ax)
    return fig


def save_figure(fig, name: str) -> None:
    out = save_dir / name
    for fmt in ("png", "pdf"):
        p = out.with_suffix(f".{fmt}")
        fig.savefig(p, dpi=600, facecolor="white")
        print(f"[Saved] {p}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Non-IID 阶梯图 1x2 组合图")
    parser.add_argument("--palette", type=str, default="default",
                        choices=["default", "all", *PALETTES],
                        help="配色：default=noniid_common.COLORS；all=默认+5 组")
    parser.add_argument("--split", action="store_true",
                        help="额外输出拆分的单面板（去掉 (a)/(b) 标题），文件名加 _a_fmnist/_b_cifar10")
    args = parser.parse_args()

    accuracy, alphas = load_data()
    apply_style()

    jobs = [("noniid_step_1x2", COLORS)]
    if args.palette == "all":
        jobs += [(f"noniid_step_1x2_{name}", pal) for name, pal in PALETTES.items()]
    elif args.palette != "default":
        jobs = [(f"noniid_step_1x2_{args.palette}", PALETTES[args.palette])]

    for name, colors in jobs:
        save_figure(build_figure(accuracy, alphas, colors), name)
        if args.split:
            for suffix, ds, _title in PANELS:
                save_figure(build_panel(ds, accuracy, alphas, colors),
                            f"{name}_{suffix}")


if __name__ == "__main__":
    main()
