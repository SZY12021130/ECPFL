"""客户端数量 vs 时间/存储开销 —— 5 种不同风格的画法

数据与 plot_cost_scaling.py 完全一致（MNIST, RK-0.1, zeta=1.0, T=50）：

    N      TT (s)    Setup (s)   Storage (MB)
    50      843.4       0.60         3.47
    100    1525.2       2.51         6.75
    500    3386.3      70.28        32.97
    1000  10071.4     241.85        65.73

风格（同一数据，五种表达，供排版时挑选）：
    a_fit_line  双对数 + 幂律拟合虚线 + 指数徽标      1x3
    b_bar       线性纵轴柱状图 + 柱顶数值              1x3
    c_lollipop  棒棒糖图（细杆 + 圆点），双对数        1x3
    d_area      渐变面积图（曲线下方填充），双对数     1x3
    e_heatmap   3x4 热力图，行内按对数归一化并标原值   单图

用法
    python AAAAA_Rework/vis/comm_volume_clients/cost_scaling/plot_cost_scaling_styles.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

from plot_cost_scaling import (
    CLIENTS,
    FS_ANNOT,
    FS_LABEL,
    FS_TICK,
    FS_TITLE,
    LW_CURVE,
    LW_SPINE,
    MARKER_SIZE,
    SERIES,
    X_TICKS,
    apply_style,
    fit_power_law,
    plain_num,
)

OUT_DIR = Path(__file__).resolve().parent / "styles"

# 5 套配色：每套风格配一套，避免五张图长得一样
PALETTES: Dict[str, Dict[str, str]] = {
    "navy_red_green": {"TT": "#1F4E79", "KGC": "#C62828", "STORAGE": "#2E7D32"},
    "okabe_ito": {"TT": "#0072B2", "KGC": "#D55E00", "STORAGE": "#009E73"},
    "morandi": {"TT": "#4C6A92", "KGC": "#A85751", "STORAGE": "#6E8B74"},
    "vivid": {"TT": "#0D2A4A", "KGC": "#E4572E", "STORAGE": "#17BEBB"},
    "deep_teal": {"TT": "#08313A", "KGC": "#1B7A85", "STORAGE": "#8FBFBF"},
}

KEYS = ("KGC", "STORAGE")
# 去掉 TT 后只剩两栏：画布同步收窄，保持单栏宽度与主图一致
FIG_3UP = (4.95, 2.55)
MARGINS_3UP = dict(left=0.105, right=0.985, bottom=0.185, top=0.855, wspace=0.335)

PANEL_TITLES = {
    "KGC": "(a) KGC key initialization",
    "STORAGE": "(b) Storage overhead",
}
ROW_LABELS = {"TT": "$TT$ (s)", "KGC": "KGC setup (s)", "STORAGE": "Storage (MB)"}


# ---------------------------------------------------------------------------
# 公共小工具
# ---------------------------------------------------------------------------
def _log_axes(ax, cfg, xticks=X_TICKS):
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator(xticks))
    ax.xaxis.set_major_formatter(FuncFormatter(plain_num))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_locator(FixedLocator(cfg["yticks"]))
    ax.yaxis.set_major_formatter(FuncFormatter(plain_num))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(*cfg["ylim"])
    # 两端留白，避免 50/100 与 500/1000 的刻度文字挤在一起
    ax.set_xlim(38, 1400)
    ax.tick_params(axis="both", which="major", labelsize=FS_TICK,
                   width=LW_SPINE, length=3.0, pad=3.0)
    for s in ax.spines.values():
        s.set_linewidth(LW_SPINE)
        s.set_color("black")


def _finish(ax, cfg, ylabel: bool = True):
    if ylabel:
        ax.set_ylabel(cfg["ylabel"], fontsize=FS_LABEL, labelpad=2)
    ax.set_xlabel("Number of clients", fontsize=FS_LABEL, labelpad=2)
    ax.set_title(cfg["title"], fontsize=FS_TITLE, pad=5)


def _grid(ax):
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.35,
            zorder=0)
    ax.set_axisbelow(True)


def _label(ax, x, y, text, color, dx=7, dy=6, ha="left", fs=None):
    ax.annotate(text, (x, y), textcoords="offset points", xytext=(dx, dy),
                fontsize=fs if fs is not None else FS_ANNOT - 0.6, color=color,
                ha=ha, zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                          edgecolor="none", alpha=0.85))


def _three_up(title_font=None):
    fig, axes = plt.subplots(1, len(KEYS), figsize=FIG_3UP)
    fig.subplots_adjust(**MARGINS_3UP)
    return fig, axes


# ---------------------------------------------------------------------------
# A. 双对数 + 幂律拟合
# ---------------------------------------------------------------------------
def style_fit_line(palette="navy_red_green"):
    apply_style()
    colors = PALETTES[palette]
    fig, axes = _three_up()
    x = np.asarray(CLIENTS, float)

    for ax, key in zip(axes, KEYS):
        cfg = dict(SERIES[key], color=colors[key], title=PANEL_TITLES[key])
        y = np.asarray(cfg["values"], float)
        p, a, _ = fit_power_law(CLIENTS, cfg["values"])
        _log_axes(ax, cfg)

        xf = np.geomspace(40, 1250, 120)
        ax.plot(xf, a * xf ** p, color=cfg["color"], linewidth=1.1,
                linestyle=(0, (4, 2)), alpha=0.85, zorder=2)
        ax.plot(x, y, color=cfg["color"], marker=cfg["marker"],
                markersize=MARKER_SIZE, linewidth=LW_CURVE,
                markerfacecolor="white", markeredgecolor=cfg["color"],
                markeredgewidth=1.2, zorder=3)

        for i, (xi, yi) in enumerate(zip(x, y)):
            if i == len(x) - 1:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"], dx=-8, dy=7,
                       ha="right")
            else:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"])

        ax.text(0.96, 0.06, rf"$\propto N^{{{p:.2f}}}$", transform=ax.transAxes,
                fontsize=FS_ANNOT + 1.0, color=cfg["color"], va="bottom",
                ha="right", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor=cfg["color"], linewidth=0.6, alpha=0.9))
        _finish(ax, cfg)
        _grid(ax)
    return fig


# ---------------------------------------------------------------------------
# B. 柱状图（线性纵轴，柱顶标值）
# ---------------------------------------------------------------------------
def style_bar(palette="okabe_ito"):
    apply_style()
    colors = PALETTES[palette]
    fig, axes = _three_up()
    x = np.arange(len(CLIENTS))

    linear_ylim = {"TT": (0, 11500), "KGC": (0, 275), "STORAGE": (0, 76)}
    linear_ticks = {
        "TT": [0, 2500, 5000, 7500, 10000],
        "KGC": [0, 50, 100, 150, 200, 250],
        "STORAGE": [0, 20, 40, 60],
    }

    for ax, key in zip(axes, KEYS):
        cfg = dict(SERIES[key], color=colors[key], title=PANEL_TITLES[key])
        y = np.asarray(cfg["values"], float)
        ax.bar(x, y, 0.56, color=cfg["color"], edgecolor="#333333",
               linewidth=0.5, zorder=3)
        for xi, yi in zip(x, y):
            ax.text(xi, yi, f"{yi:g}", ha="center", va="bottom",
                    fontsize=FS_ANNOT - 0.2, color="#111111", zorder=4)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{n:g}" for n in CLIENTS])
        ax.set_ylim(*linear_ylim[key])
        ax.set_yticks(linear_ticks[key])
        ax.set_yticklabels([f"{t:g}" for t in linear_ticks[key]])
        ax.tick_params(axis="both", which="major", labelsize=FS_TICK,
                       width=LW_SPINE, length=3.0, pad=3.0)
        for s in ax.spines.values():
            s.set_linewidth(LW_SPINE)
            s.set_color("black")
        _finish(ax, cfg)
        _grid(ax)
    return fig


# ---------------------------------------------------------------------------
# C. 棒棒糖图（双对数）
# ---------------------------------------------------------------------------
def style_lollipop(palette="morandi"):
    apply_style()
    colors = PALETTES[palette]
    fig, axes = _three_up()
    x = np.asarray(CLIENTS, float)

    for ax, key in zip(axes, KEYS):
        cfg = dict(SERIES[key], color=colors[key], title=PANEL_TITLES[key])
        y = np.asarray(cfg["values"], float)
        _log_axes(ax, cfg)
        y0 = cfg["ylim"][0] * 1.15
        ax.vlines(x, y0, y, color=cfg["color"], linewidth=1.3, alpha=0.55,
                  zorder=2)
        ax.scatter(x, y, s=(MARKER_SIZE * 2.6) ** 2 / 4, facecolor="white",
                   edgecolor=cfg["color"], linewidth=1.4, zorder=4)
        ax.scatter(x, y, s=10, color=cfg["color"], zorder=5)
        for i, (xi, yi) in enumerate(zip(x, y)):
            if i == len(x) - 1:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"], dx=-8, dy=8,
                       ha="right")
            else:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"], dx=6, dy=8)
        _finish(ax, cfg)
        _grid(ax)
    return fig


# ---------------------------------------------------------------------------
# D. 渐变面积图（双对数）
# ---------------------------------------------------------------------------
def style_area(palette="vivid"):
    apply_style()
    colors = PALETTES[palette]
    fig, axes = _three_up()
    x = np.asarray(CLIENTS, float)

    for ax, key in zip(axes, KEYS):
        cfg = dict(SERIES[key], color=colors[key], title=PANEL_TITLES[key])
        y = np.asarray(cfg["values"], float)
        _log_axes(ax, cfg)
        base = cfg["ylim"][0] * 1.02
        ax.fill_between(x, base, y, color=cfg["color"], alpha=0.22, zorder=1,
                        linewidth=0)
        ax.plot(x, y, color=cfg["color"], linewidth=LW_CURVE + 0.3, zorder=3,
                marker=cfg["marker"], markersize=MARKER_SIZE - 0.5,
                markerfacecolor="white", markeredgecolor=cfg["color"],
                markeredgewidth=1.2)
        for i, (xi, yi) in enumerate(zip(x, y)):
            if i == len(x) - 1:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"], dx=-8, dy=8,
                       ha="right")
            else:
                _label(ax, xi, yi, f"{yi:g}", cfg["color"], dx=6, dy=8)
        _finish(ax, cfg)
        _grid(ax)
    return fig


# ---------------------------------------------------------------------------
# E. 热力图（行内对数归一化，格子标原值）
# ---------------------------------------------------------------------------
def style_heatmap(palette="deep_teal"):
    apply_style()
    fig, ax = plt.subplots(figsize=(3.55, 1.85))
    fig.subplots_adjust(left=0.235, right=0.845, bottom=0.225, top=0.945)

    data = np.array([SERIES[k]["values"] for k in KEYS], float)   # 3 x 4
    # 行内对数归一化：同一行里最小的=0、最大的=1，跨量级也能看出趋势
    logv = np.log10(data)
    norm = (logv - logv.min(axis=1, keepdims=True)) / (
        logv.max(axis=1, keepdims=True) - logv.min(axis=1, keepdims=True))

    cmap = plt.get_cmap("YlGnBu")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            shade = cmap(0.12 + 0.76 * norm[i, j])
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor=shade, edgecolor="white",
                                       linewidth=1.4, zorder=2))
            r, g, b = shade[:3]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            ax.text(j, i, f"{data[i, j]:g}", ha="center", va="center",
                    fontsize=FS_ANNOT + 0.4, color="white" if lum < 0.55
                    else "#111111", zorder=4)

    ax.set_xlim(-0.5, len(CLIENTS) - 0.5)
    ax.set_ylim(len(KEYS) - 0.5, -0.5)
    ax.set_xticks(np.arange(len(CLIENTS)))
    ax.set_xticklabels([f"{n:g}" for n in CLIENTS], fontsize=FS_TICK)
    ax.set_yticks(np.arange(len(KEYS)))
    ax.set_yticklabels([ROW_LABELS[k] for k in KEYS], fontsize=FS_TICK)
    ax.tick_params(axis="both", which="major", width=LW_SPINE, length=0,
                   pad=3.0)
    ax.set_xlabel("Number of clients", fontsize=FS_LABEL, labelpad=3)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_linewidth(LW_SPINE)
        s.set_color("black")

    # 右侧标出 50→1000 的增长倍数（用坐标轴外坐标，避免压到边框）
    text_colors = {"KGC": "#1B7A85", "STORAGE": "#2F6B6B"}
    n_row = len(KEYS)
    for i, key in enumerate(KEYS):
        grow = SERIES[key]["values"][-1] / SERIES[key]["values"][0]
        ax.text(1.035, 1.0 - (i + 0.5) / n_row, f"$\\times${grow:.0f}",
                transform=ax.transAxes, va="center", ha="left",
                fontsize=FS_ANNOT, color=text_colors[key], fontweight="bold")
    return fig


# ---------------------------------------------------------------------------
# F. 复杂度表（3 行 x 3 列，booktabs 三线表）
# ---------------------------------------------------------------------------
def style_table():
    apply_style()
    fig, ax = plt.subplots(figsize=(4.9, 1.30))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # 指数与倍数全部由拟合实时算出，保证与图一致
    p_kgc, _, _ = fit_power_law(CLIENTS, SERIES["KGC"]["values"])
    p_sto, _, _ = fit_power_law(CLIENTS, SERIES["STORAGE"]["values"])
    g_kgc = SERIES["KGC"]["values"][-1] / SERIES["KGC"]["values"][0]
    g_sto = SERIES["STORAGE"]["values"][-1] / SERIES["STORAGE"]["values"][0]

    header = ("Component", "Complexity", "Measured cost (N: 50 → 1000)")
    rows = [
        ("KGC key initialization", r"$O(N^2)$",
         rf"0.60 s $\rightarrow$ 241.85 s  ($\times{g_kgc:.0f}$, "
         rf"$\propto N^{{{p_kgc:.2f}}}$)"),
        ("Storage overhead", r"$O(N)$",
         rf"3.47 MB $\rightarrow$ 65.73 MB  ($\times{g_sto:.0f}$, "
         rf"$\propto N^{{{p_sto:.2f}}}$)"),
    ]

    # 列位置：第 1 列左对齐、第 2 列居中、第 3 列左对齐
    x1, x2, x3 = 0.015, 0.360, 0.520
    y_head, y_r1, y_r2 = 0.775, 0.455, 0.135

    for x, txt in ((x1, header[0]), (x3, header[2])):
        ax.text(x, y_head, txt, transform=ax.transAxes, ha="left",
                va="center", fontsize=FS_TICK + 0.4, fontweight="bold")
    ax.text(x2, y_head, header[1], transform=ax.transAxes, ha="center",
            va="center", fontsize=FS_TICK + 0.4, fontweight="bold")

    for y, (c1, c2, c3) in ((y_r1, rows[0]), (y_r2, rows[1])):
        ax.text(x1, y, c1, transform=ax.transAxes, ha="left", va="center",
                fontsize=FS_TICK)
        ax.text(x2, y, c2, transform=ax.transAxes, ha="center", va="center",
                fontsize=FS_TICK)
        ax.text(x3, y, c3, transform=ax.transAxes, ha="left", va="center",
                fontsize=FS_TICK)

    # booktabs 三线表：顶线/底线粗，表头下细线，无竖线
    for y, lw in ((0.965, 1.1), (0.615, 0.55), (0.020, 1.1)):
        ax.plot([0.0, 1.0], [y, y], color="black", linewidth=lw,
                transform=ax.transAxes, clip_on=False, zorder=3)
    return fig


# ---------------------------------------------------------------------------
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("a_fit_line", style_fit_line),
        ("b_bar", style_bar),
        ("c_lollipop", style_lollipop),
        ("d_area", style_area),
        ("e_heatmap", style_heatmap),
        ("f_complexity_table", style_table),
    ]
    for stem, func in jobs:
        fig = func()
        for ext in ("png", "pdf"):
            p = OUT_DIR / f"{stem}.{ext}"
            fig.savefig(p, dpi=600, bbox_inches="tight", facecolor="white")
            print(f"[SAVE]  {p}")
        plt.close(fig)


if __name__ == "__main__":
    main()
