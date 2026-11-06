"""客户端数量 vs 时间与存储开销（TT / KGC Setup / Storage）

数据来源（MNIST, RK-0.1, zeta=1.0, T=50 实测汇总表）：

    N      K      AC(%)    TT (s)    Setup (s)   Storage (MB)
    50     25     91.30     843.4       0.60         3.47
    100    50     97.17    1525.2       2.51         6.75
    500    250    95.54    3386.3      70.28        32.97
    1000   500    90.84   10071.4     241.85        65.73

三张图：
  1) cost_scaling_panels.png     —— 1x3 双对数面板，每格一条实测曲线 + 幂律拟合
  2) cost_scaling_normalized.png —— 单图：三条曲线各自除以 N=50 的取值，
                                    直接对比"涨了多少倍"
脚本自带 VERIFY：重算每客户端存储占用、每轮耗时、幂律指数与 R2。

用法
    python AAAAA_Rework/vis/comm_volume_clients/cost_scaling/plot_cost_scaling.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR

# ---------------------------------------------------------------------------
# 字体：与 AAAAA_Rework/vis 下其它图一致（Times，bold）
# ---------------------------------------------------------------------------
try:
    import scienceplots  # noqa: F401

    _STYLE: List[str] = ["science", "no-latex"]
except ImportError:  # pragma: no cover
    _STYLE = []

FONT_FALLBACKS = [
    "Times New Roman", "Times", "Nimbus Roman", "Nimbus Roman No9 L",
    "TeX Gyre Termes", "Liberation Serif", "FreeSerif", "DejaVu Serif",
]
FONT_RC = {
    "font.family": "serif",
    "font.serif": FONT_FALLBACKS,
    "mathtext.fontset": "stix",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}

FONT_WEIGHT = "bold"
FS_LABEL = 10.5      # 轴标题
FS_TICK = 8.8        # 刻度
FS_TITLE = 10.5      # 子图标题
FS_ANNOT = 8.6       # 指数标注
FS_LEGEND = 9.0

LW_SPINE = 0.9
LW_CURVE = 1.4
LW_FIT = 1.1
MARKER_SIZE = 5.0

# ---------------------------------------------------------------------------
# 数据
# ---------------------------------------------------------------------------
CLIENTS = [50, 100, 500, 1000]
ROUNDS = 50

TT = [843.4, 1525.2, 3386.3, 10071.4]       # s，总训练时间
SETUP = [0.60, 2.51, 70.28, 241.85]         # s，KGC 初始化为客户端生成密钥
STORAGE = [3.47, 6.75, 32.97, 65.73]        # MB，客户端侧存储

SERIES: Dict[str, Dict] = {
    "TT": {
        "values": TT,
        "color": "#1F4E79",
        "marker": "o",
        "ylabel": "Total time $TT$ (s)",
        "title": "(a) Total training time",
        "yticks": [1000, 2000, 5000, 10000],
        "ylim": (700, 16000),
    },
    "KGC": {
        "values": SETUP,
        "color": "#C62828",
        "marker": "s",
        "ylabel": "KGC setup time (s)",
        "title": "(b) KGC key initialization",
        "yticks": [0.5, 1, 2, 5, 10, 50, 200],
        "ylim": (0.35, 780),
    },
    "STORAGE": {
        "values": STORAGE,
        "color": "#2E7D32",
        "marker": "D",
        "ylabel": "Client storage (MB)",
        "title": "(c) Storage overhead",
        "yticks": [3, 5, 10, 20, 50, 100],
        "ylim": (2.0, 170),
    },
}

X_TICKS = [50, 100, 500, 1000]


# ---------------------------------------------------------------------------
# 幂律拟合  y = a * N^p   （在 log-log 空间做最小二乘）
# ---------------------------------------------------------------------------
def fit_power_law(x: List[float], y: List[float]) -> Tuple[float, float, float]:
    """返回 (指数 p, 系数 a, R²)，拟合 log10(y) = log10(a) + p·log10(x)。"""
    lx, ly = np.log10(np.asarray(x, float)), np.log10(np.asarray(y, float))
    p, b = np.polyfit(lx, ly, 1)
    pred = p * lx + b
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(p), float(10 ** b), r2


def plain_num(v, _pos=None) -> str:
    """刻度标签：整数不带小数点，小数最多两位。"""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}"
    return f"{v:g}"


def verify() -> None:
    print("=" * 78)
    print("VERIFY — 由汇总表反算的派生量与幂律指数")
    print("=" * 78)
    print(f"  {'N':>5} {'TT(s)':>10} {'TT/round':>9} {'Setup(s)':>9} "
          f"{'Storage':>9} {'MB/client':>10} {'KB/client':>10}")
    for i, n in enumerate(CLIENTS):
        print(f"  {n:>5} {TT[i]:>10.1f} {TT[i] / ROUNDS:>9.2f} "
              f"{SETUP[i]:>9.2f} {STORAGE[i]:>9.2f} "
              f"{STORAGE[i] / n:>10.5f} {STORAGE[i] * 1024 / n:>10.1f}")
    print("-" * 78)
    for key, name in (("TT", "TT"), ("KGC", "KGC setup"), ("STORAGE", "Storage")):
        p, a, r2 = fit_power_law(CLIENTS, SERIES[key]["values"])
        grow = SERIES[key]["values"][-1] / SERIES[key]["values"][0]
        print(f"  {name:<10s} ~ N^{p:.2f}   (系数 {a:.4g}, R2 = {r2:.4f})   "
              f"N: 50-1000 增长 {grow:.1f}x")
    print("-" * 78)
    print("  单位存储 (Storage/N) 恒为 66-71 KB → Storage 与 N 呈正比")
    print("  Setup 指数 ≈ 2 → KGC 初始化是平方级瓶颈，N=1000 时单次 241.85 s")
    print("  TT 指数 < 1 → 总时间增长慢于客户端数（每轮并行度提升）")
    print("=" * 78)


# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = FONT_WEIGHT) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    plt.rcParams["font.weight"] = font_weight
    plt.rcParams["xtick.top"] = True
    plt.rcParams["ytick.right"] = True
    plt.rcParams["xtick.minor.visible"] = False
    plt.rcParams["ytick.minor.visible"] = False


def _setup_log_axis(ax, xticks: List[float], yticks: List[float],
                    ylim: Tuple[float, float]) -> None:
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(FixedLocator(xticks))
    ax.xaxis.set_major_formatter(FuncFormatter(plain_num))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_locator(FixedLocator(yticks))
    ax.yaxis.set_major_formatter(FuncFormatter(plain_num))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(*ylim)
    ax.tick_params(axis="both", which="major", labelsize=FS_TICK,
                   width=LW_SPINE, length=3.0, pad=3.0)


# ---------------------------------------------------------------------------
# 图 1：1x3 双对数面板
# ---------------------------------------------------------------------------
def build_panels():
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55))
    fig.subplots_adjust(left=0.068, right=0.992, bottom=0.185, top=0.855,
                        wspace=0.285)

    x = np.asarray(CLIENTS, float)
    for ax, key in zip(axes, ("TT", "KGC", "STORAGE")):
        cfg = SERIES[key]
        y = np.asarray(cfg["values"], float)
        p, a, r2 = fit_power_law(CLIENTS, cfg["values"])

        _setup_log_axis(ax, X_TICKS, cfg["yticks"], cfg["ylim"])

        # 幂律拟合线
        xf = np.geomspace(40, 1250, 120)
        ax.plot(xf, a * xf ** p, color=cfg["color"], linewidth=LW_FIT,
                linestyle=(0, (4, 2)), alpha=0.85, zorder=2)

        # 实测点
        ax.plot(x, y, color=cfg["color"], marker=cfg["marker"],
                markersize=MARKER_SIZE, linewidth=LW_CURVE,
                markerfacecolor="white", markeredgecolor=cfg["color"],
                markeredgewidth=1.2, zorder=3)

        # 数值标注：右对齐末点、其余右上，白色底衬避免与曲线重叠
        n_pts = len(x)
        for i, (xi, yi) in enumerate(zip(x, y)):
            if i == n_pts - 1:
                dx, dy, ha = -8, 7, "right"
            else:
                dx, dy, ha = 7, 6, "left"
            ax.annotate(f"{yi:g}", (xi, yi), textcoords="offset points",
                        xytext=(dx, dy), fontsize=FS_ANNOT - 0.6,
                        color=cfg["color"], ha=ha, zorder=4,
                        bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                                  edgecolor="none", alpha=0.85))

        # 幂律指数徽标（放右下角空白区，避开纵轴刻度与右上角数据点）
        ax.text(0.96, 0.06, rf"$\propto N^{{{p:.2f}}}$", transform=ax.transAxes,
                fontsize=FS_ANNOT + 1.0, color=cfg["color"], va="bottom",
                ha="right", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor=cfg["color"], linewidth=0.6, alpha=0.9))

        ax.set_title(cfg["title"], fontsize=FS_TITLE, pad=5)
        ax.set_ylabel(cfg["ylabel"], fontsize=FS_LABEL, labelpad=2)
        ax.set_xlabel("Number of clients", fontsize=FS_LABEL, labelpad=2)
        ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.35,
                zorder=0)
        ax.set_axisbelow(True)
        for s in ax.spines.values():
            s.set_linewidth(LW_SPINE)
            s.set_color("black")

    return fig


# ---------------------------------------------------------------------------
# 图 2：归一化增长（各自除以 N=50 的值）
# ---------------------------------------------------------------------------
def build_normalized():
    apply_style()
    fig, ax = plt.subplots(figsize=(3.55, 2.75))
    fig.subplots_adjust(left=0.150, right=0.985, bottom=0.195, top=0.930)

    x = np.asarray(CLIENTS, float)
    _setup_log_axis(ax, X_TICKS, [1, 2, 5, 10, 20, 50, 100, 400],
                    (0.85, 700))

    labels = {"TT": r"Total time $TT$", "KGC": "KGC setup",
              "STORAGE": "Storage"}
    markers = {"TT": "o", "KGC": "s", "STORAGE": "D"}
    for key in ("TT", "KGC", "STORAGE"):
        cfg = SERIES[key]
        y = np.asarray(cfg["values"], float)
        yn = y / y[0]
        ax.plot(x, yn, color=cfg["color"], marker=markers[key],
                markersize=MARKER_SIZE - 0.6, linewidth=LW_CURVE,
                markerfacecolor="white", markeredgecolor=cfg["color"],
                markeredgewidth=1.1, label=labels[key], zorder=3)
        ax.annotate(rf"$\times${yn[-1]:.0f}", (x[-1], yn[-1]),
                    textcoords="offset points", xytext=(6, 0),
                    fontsize=FS_ANNOT, color=cfg["color"],
                    va="center", ha="left", fontweight="bold")

    # 参考：与客户端数同比例的基准线（×N/50）
    ax.plot(x, x / x[0], color="#9E9E9E", linestyle=":", linewidth=1.0,
            zorder=1, label=r"linear in $N$")

    ax.set_xlabel("Number of clients", fontsize=FS_LABEL, labelpad=2)
    ax.set_ylabel(r"Growth relative to $N=50$", fontsize=FS_LABEL, labelpad=2)
    ax.set_xlim(40, 1900)
    ax.grid(True, which="major", linestyle="--", linewidth=0.5, alpha=0.35,
            zorder=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_linewidth(LW_SPINE)
        s.set_color("black")
    leg = ax.legend(loc="upper left", fontsize=FS_LEGEND - 0.8, frameon=True,
                    fancybox=False, framealpha=0.95, edgecolor="#808080",
                    borderpad=0.3, labelspacing=0.28, handlelength=1.4,
                    handletextpad=0.4, borderaxespad=0.35)
    leg.get_frame().set_linewidth(0.6)
    return fig


def main() -> None:
    verify()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for fig, stem in ((build_panels(), "cost_scaling_panels"),
                      (build_normalized(), "cost_scaling_normalized")):
        for ext in ("png", "pdf"):
            p = OUT_DIR / f"{stem}.{ext}"
            fig.savefig(p, dpi=600, bbox_inches="tight", facecolor="white")
            print(f"[SAVE]  {p}")
        plt.close(fig)


if __name__ == "__main__":
    main()
