#!/usr/bin/env python3
"""Non-IID 准确率 —— 替代可视化（解决折线重叠、看不出差别）

原始图 `pic/noniid_1x2.png` 用 0–100% 纵轴画 5 条折线，各方法差距只有
0.2–5 个百分点，几乎完全重叠。本脚本用四种论文常用形式重画同一份数据：

  zoom  截断纵轴的折线图（纵轴只覆盖数据区间，差异被放大）
  gap   相对 FedAvg-CKKS 的准确率差距 Δ（百分点），基线恒为 0
  bars  Δ 的分组柱状图（每个 α 一组，4 个加密方案）
  heat  方法 × α 的数值热力图（色块 + 数字，直接读差）

每个视图输出：
  single/<dataset>__<view>.png|pdf   两个数据集各自独立
  grid/<view>__2x1.png|pdf           2 行 1 列组合（上 FMNIST，下 CIFAR-10）

数据来源：../script/noniid_data.json（只读，不修改）
输出目录：本脚本同级的 single/ 与 grid/
原始图 pic/ 下的任何文件都不会被触碰。

用法
    python tools/plot_experiment/plot_noniid_2x2/alt_charts/plot_noniid_alt.py
    python .../plot_noniid_alt.py --view gap
    python .../plot_noniid_alt.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_JSON = SCRIPT_DIR.parent / "script" / "noniid_data.json"
OUT_SINGLE = SCRIPT_DIR / "single"
OUT_GRID = SCRIPT_DIR / "grid"

PROJECT_ROOT = SCRIPT_DIR.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import scienceplots  # noqa: F401

    _STYLE: List[str] = ["science", "grid", "no-latex"]
except ImportError:  # pragma: no cover
    _STYLE = ["ggplot"]

FONT_RC = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Nimbus Roman",
                   "TeX Gyre Termes", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}

# ---------------------------------------------------------------------------
# 方法与配色（与原图 / 全文其它图保持一致）
# ---------------------------------------------------------------------------
METHODS_FULL = ["ECPFL", "ESAFL", "MASER", "FedPHE", "FedAvg-CKKS"]
METHODS_GAP = ["ECPFL", "ESAFL", "MASER", "FedPHE"]          # Δ 视图不含基线
BASELINE = "FedAvg-CKKS"

COLORS = {
    "ECPFL": "#D62728",
    "ESAFL": "#1F77B4",
    "MASER": "#2CA02C",
    "FedPHE": "#FF7F0E",
    "FedAvg-CKKS": "#9467BD",
}
MARKERS = {"ECPFL": "o", "ESAFL": "s", "MASER": "^", "FedPHE": "D",
           "FedAvg-CKKS": "v"}
LINESTYLES = {"ECPFL": "-", "ESAFL": "--", "MASER": "-.", "FedPHE": ":",
              "FedAvg-CKKS": (0, (5, 1))}

DATASETS = ["FMNIST", "CIFAR-10"]
DS_TAG = {"FMNIST": "fmnist", "CIFAR-10": "cifar10"}

# 截断纵轴范围（zoom 视图）：覆盖数据并留呼吸空间
ZOOM_YLIM = {"FMNIST": (67, 94), "CIFAR-10": (32, 89)}

# 已知数据缺陷：CIFAR-10 / ESAFL 多出一个值 85.0（重复了 FedAvg 的 α=5.0 值）
# noniid_data.md（由实验目录自动导出）对应序列为 38.0 76.0 80.5 81.0 81.3
KNOWN_DEFECTS = {("CIFAR-10", "ESAFL"): 4}   # 需剔除的下标


# ---------------------------------------------------------------------------
# 数据
# ---------------------------------------------------------------------------
def load_data() -> Tuple[Dict[str, Dict[str, np.ndarray]], List[float]]:
    with open(DATA_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    alphas = [float(a) for a in raw["alphas"]]
    n = len(alphas)

    acc: Dict[str, Dict[str, np.ndarray]] = {m: {} for m in METHODS_FULL}
    for ds in DATASETS:
        for m in METHODS_FULL:
            vals = [float(v) for v in raw["accuracy"][ds][m]]
            key = (ds, m)
            if len(vals) > n:
                drop = KNOWN_DEFECTS.get(key, len(vals) - 1)
                print(f"[WARN] {ds}/{m}: {len(vals)} values for {n} alphas; "
                      f"dropping index {drop} (value {vals[drop]})")
                del vals[drop]
            elif len(vals) < n:
                raise ValueError(f"{ds}/{m}: only {len(vals)} values for {n} alphas")
            acc[m][ds] = np.asarray(vals, dtype=float)
    return acc, alphas


def gap_matrix(acc, ds) -> Dict[str, np.ndarray]:
    """各加密方案相对 FedAvg-CKKS 的准确率差（百分点，负值=更低）。"""
    base = acc[BASELINE][ds]
    return {m: acc[m][ds] - base for m in METHODS_GAP}


def gap_ylim(acc, ds) -> Tuple[float, float]:
    g = gap_matrix(acc, ds)
    lo = min(float(v.min()) for v in g.values()) - 0.7
    return (np.floor(lo * 2) / 2.0, 0.8)


# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = "bold", base: float = 1.0) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    plt.rcParams["font.weight"] = font_weight
    plt.rcParams["axes.labelweight"] = font_weight
    plt.rcParams["axes.titlesize"] = 12.5 * base
    plt.rcParams["axes.labelsize"] = 11.5 * base
    plt.rcParams["xtick.labelsize"] = 10.0 * base
    plt.rcParams["ytick.labelsize"] = 10.0 * base
    plt.rcParams["legend.fontsize"] = 9.0 * base
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["grid.alpha"] = 0.35
    plt.rcParams["xtick.top"] = False
    plt.rcParams["ytick.right"] = False
    plt.rcParams["xtick.minor.visible"] = False
    plt.rcParams["ytick.minor.visible"] = False


def _frame(ax) -> None:
    for s in ax.spines.values():
        s.set_linewidth(1.0)


def _xaxis(ax, alphas: List[float]) -> None:
    x = np.arange(len(alphas))
    ax.set_xticks(x)
    ax.set_xticklabels([f"{a:g}" for a in alphas])
    ax.set_xlim(-0.45, len(alphas) - 0.55)
    ax.set_xlabel(r"Non-IID coefficient $\alpha$")


# ---------------------------------------------------------------------------
# 视图 1：截断纵轴折线（zoom）
# ---------------------------------------------------------------------------
def draw_zoom(ax, ds: str, acc, alphas: List[float], legend: bool = True) -> None:
    x = np.arange(len(alphas))
    for m in METHODS_FULL:
        y = acc[m][ds]
        ours = m == "ECPFL"
        ax.plot(x, y, color=COLORS[m], marker=MARKERS[m],
                linestyle=LINESTYLES[m],
                linewidth=2.6 if ours else 1.7,
                markersize=7.0 if ours else 5.2,
                markerfacecolor=COLORS[m] if ours else "white",
                markeredgecolor=COLORS[m], markeredgewidth=1.1,
                label=m, zorder=6 if ours else 3, clip_on=False)

    _xaxis(ax, alphas)
    lo, hi = ZOOM_YLIM[ds]
    ax.set_ylim(lo, hi)
    ax.set_ylabel("Test Accuracy (%)")
    ax.grid(True, linestyle="--", linewidth=0.6)
    ax.set_axisbelow(True)
    _frame(ax)
    ax.text(0.015, 0.965, f"y-axis starts at {lo:.0f}%",
            transform=ax.transAxes, fontsize=7.2, va="top", ha="left",
            color="#666666", style="italic")
    if legend:
        ax.legend(loc="lower right", frameon=True, framealpha=0.95,
                  handlelength=2.0, labelspacing=0.28, borderpad=0.35)


# ---------------------------------------------------------------------------
# 视图 2：相对基线的准确率差距（gap，折线）
# ---------------------------------------------------------------------------
def draw_gap_line(ax, ds: str, acc, alphas: List[float], legend: bool = True) -> None:
    x = np.arange(len(alphas))
    g = gap_matrix(acc, ds)
    ax.axhline(0.0, color=COLORS[BASELINE], linewidth=1.6, zorder=2,
               label=BASELINE + " (reference)")
    for m in METHODS_GAP:
        y = g[m]
        ours = m == "ECPFL"
        ax.plot(x, y, color=COLORS[m], marker=MARKERS[m],
                linestyle=LINESTYLES[m],
                linewidth=2.6 if ours else 1.7,
                markersize=7.0 if ours else 5.2,
                markerfacecolor=COLORS[m] if ours else "white",
                markeredgecolor=COLORS[m], markeredgewidth=1.1,
                label=m, zorder=6 if ours else 3, clip_on=False)

    _xaxis(ax, alphas)
    ax.set_ylim(*gap_ylim(acc, ds))
    ax.set_ylabel(r"Accuracy gap vs %s (pp)" % BASELINE)
    ax.grid(True, linestyle="--", linewidth=0.6)
    ax.set_axisbelow(True)
    _frame(ax)
    if legend:
        ax.legend(loc="center right", bbox_to_anchor=(0.995, 0.45),
                  frameon=True, framealpha=0.95, ncol=1,
                  handlelength=2.0, labelspacing=0.25, borderpad=0.35)


# ---------------------------------------------------------------------------
# 视图 3：Δ 分组柱状图（bars）
# ---------------------------------------------------------------------------
def draw_gap_bars(ax, ds: str, acc, alphas: List[float], legend: bool = True) -> None:
    x = np.arange(len(alphas))
    g = gap_matrix(acc, ds)
    n_m = len(METHODS_GAP)
    total_w = 0.78
    w = total_w / n_m

    for j, m in enumerate(METHODS_GAP):
        vals = g[m]
        offs = x - total_w / 2 + w * (j + 0.5)
        ax.bar(offs, vals, width=w * 0.88, color=COLORS[m],
               edgecolor="white", linewidth=0.5, label=m, zorder=3)
        for xi, v in zip(offs, vals):
            ax.text(xi, v - 0.18, f"{v:.1f}", ha="center", va="top",
                    fontsize=6.4, color="#222222", zorder=5)

    ax.axhline(0.0, color="#333333", linewidth=1.0, zorder=4)
    _xaxis(ax, alphas)
    ax.set_ylim(*gap_ylim(acc, ds))
    ax.set_ylabel(r"Accuracy gap vs %s (pp)" % BASELINE)
    ax.grid(True, axis="y", linestyle="--", linewidth=0.6)
    ax.set_axisbelow(True)
    _frame(ax)
    # 图例统一交给整图级 figure legend（见 _figure_legend），避免压住标题


# ---------------------------------------------------------------------------
# 视图 4：数值热力图（heat）
# ---------------------------------------------------------------------------
def draw_heat(ax, ds: str, acc, alphas: List[float], cmap: str = "YlGnBu",
              colorbar: bool = True):
    methods = METHODS_FULL[::-1]
    data = np.array([[acc[m][ds][j] for j in range(len(alphas))] for m in methods])
    vmin, vmax = float(data.min()) - 2.0, float(data.max()) + 0.6

    im = ax.imshow(data, cmap=cmap, norm=Normalize(vmin=vmin, vmax=vmax),
                   aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            frac = (v - vmin) / max(vmax - vmin, 1e-9)
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    fontsize=8.4, color="white" if frac > 0.62 else "#111111",
                    fontweight="bold")

    ax.set_xticks(np.arange(len(alphas)))
    ax.set_xticklabels([f"{a:g}" for a in alphas])
    ax.set_yticks(np.arange(len(methods)))
    ax.set_yticklabels(methods)
    ax.set_xlabel(r"Non-IID coefficient $\alpha$")
    ax.set_xlim(-0.5, len(alphas) - 0.5)
    ax.set_ylim(-0.5, len(methods) - 0.5)
    ax.grid(False)
    _frame(ax)
    for xx in np.arange(-0.5, len(alphas), 1):
        ax.axvline(xx, color="white", linewidth=1.2, zorder=2)
    for yy in np.arange(-0.5, len(methods), 1):
        ax.axhline(yy, color="white", linewidth=1.2, zorder=2)

    if colorbar:
        cbar = plt.colorbar(im, ax=ax, fraction=0.042, pad=0.03)
        cbar.set_label("Accuracy (%)", fontsize=9.5)
        cbar.ax.tick_params(labelsize=8.0)
        cbar.outline.set_linewidth(0.8)
    return im


VIEWS = {
    "zoom": {"title": "Truncated axis (zoom)", "draw": draw_zoom},
    "gap": {"title": "Accuracy gap vs baseline", "draw": draw_gap_line},
    "bars": {"title": "Accuracy gap (grouped bars)", "draw": draw_gap_bars},
    "heat": {"title": "Value heatmap", "draw": draw_heat},
}


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def save(fig, path: Path, dpi: int = 400) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        p = path.with_suffix("." + ext)
        fig.savefig(p, dpi=dpi, bbox_inches="tight", facecolor="white")
        print(f"[SAVE]  {p}")
    plt.close(fig)


def _bottom_legend(fig, ax, anchor: float = -0.02, ncol: int = 4) -> None:
    """把柱状图的图例放到底部，避免压住标题/柱体。"""
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, anchor),
               ncol=ncol, frameon=False, handlelength=1.0,
               columnspacing=1.6, borderaxespad=0.0, fontsize=9.0)


def _draw(view: str, ax, ds: str, acc, alphas, legend: bool) -> None:
    if view in ("zoom", "gap"):
        VIEWS[view]["draw"](ax, ds, acc, alphas, legend=legend)
    else:
        VIEWS[view]["draw"](ax, ds, acc, alphas)


def render_single(view: str, acc, alphas, dpi: int) -> None:
    for ds in DATASETS:
        apply_style()
        fig, ax = plt.subplots(figsize=(5.8, 4.5 if view == "bars" else 4.3))
        _draw(view, ax, ds, acc, alphas, legend=(view != "bars"))
        name = "FMNIST" if ds == "FMNIST" else "CIFAR-10"
        ax.set_title(f"{name} — {VIEWS[view]['title']}", pad=6, fontsize=11.5)
        if view == "bars":
            _bottom_legend(fig, ax, anchor=-0.01)
        save(fig, OUT_SINGLE / f"{DS_TAG[ds]}__{view}", dpi)


def render_grid(view: str, acc, alphas, dpi: int) -> None:
    apply_style()
    if view == "heat":
        fig, axes = plt.subplots(2, 1, figsize=(6.0, 6.6))
    elif view == "bars":
        fig, axes = plt.subplots(2, 1, figsize=(6.2, 7.9))
    else:
        fig, axes = plt.subplots(2, 1, figsize=(6.2, 7.4))

    for k, ds in enumerate(DATASETS):
        _draw(view, axes[k], ds, acc, alphas, legend=(k == 0))
        axes[k].set_title(f"({chr(97 + k)}) {ds}", fontsize=11.5, pad=5)
        if view not in ("heat", "bars"):
            axes[k].set_xlabel("")            # 共享横轴标签

    if view not in ("heat", "bars"):
        fig.supxlabel(r"Non-IID coefficient $\alpha$", fontsize=11.5)
    fig.tight_layout()
    if view == "bars":
        _bottom_legend(fig, axes[0], anchor=0.005)
    save(fig, OUT_GRID / f"{view}__2x1", dpi)


def main() -> None:
    parser = argparse.ArgumentParser(description="Non-IID 准确率替代可视化")
    parser.add_argument("--view", default="all",
                        choices=list(VIEWS) + ["all"])
    parser.add_argument("--dpi", type=int, default=400)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for k, v in VIEWS.items():
            print(f"  {k:<6s} {v['title']}")
        return

    acc, alphas = load_data()
    print(f"[DATA] {len(alphas)} alphas, methods: {', '.join(METHODS_FULL)}")
    for ds in DATASETS:
        row = ", ".join(f"{m}={acc[m][ds][-1]:.1f}" for m in METHODS_FULL)
        print(f"[DATA] {ds:<9s} (alpha={alphas[-1]:g})  {row}")

    views = list(VIEWS) if args.view == "all" else [args.view]
    for v in views:
        render_single(v, acc, alphas, args.dpi)
    for v in views:
        render_grid(v, acc, alphas, args.dpi)


if __name__ == "__main__":
    main()
