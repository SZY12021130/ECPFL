"""Fig. 6 — 每轮包（密文块）数量与全模型密文大小（五基线对比）

数据来源：`AAAAA_Rework/docs/baseline_encryption_same_security.md`
          口径 = 同 logQ=61 安全级别下的"位紧凑"理论值

    CKKS (c0,c1) 单密文 = 2·N·61/8 = 124,928 B  （N=8192, 4096 值/密文）
    单环元素密文   单密文 = n·61/8   =  31,232 B  （n=4096）
        ECPFL  : 4,096 值/密文
        ESAFL  : 8,192 值/密文（EP 位打包，每系数 2 值）

    包数 = ⌈d / 值每密文⌉
    总大小 = 包数 × 单密文字节

脚本自带 VERIFY 段落，会把上表的每个数字重算一遍并与给定值比对，
不通过会显式报警，避免把错误数字画进论文。

用法
    python AAAAA_Rework/vis/plot_fig6_batches_ciphertext.py
    python AAAAA_Rework/vis/plot_fig6_batches_ciphertext.py --theme all
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = SCRIPT_DIR / "fig6"

# ---------------------------------------------------------------------------
# 字体 / 字号：与主图一致（Times，按 \textwidth = 7.2 in 标定）
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

FS_AXIS_LABEL = 12.0    # 横纵坐标标题（原 10.0，+2）
FS_TICK = 9.0
FS_LEGEND = 10.5        # 图例（原 8.5，+2）；(b) 用 FS_LEGEND-0.5 = 10.0
FS_LEGEND_NONIID = 12.0  # --legend-style noniid：与 noniid_step_1x2 系列图例同字号
FS_LEGEND_NONIID_B = 9.5  # (b) 放不下 12 pt（会压住 FMNIST→CIFAR-10 陡升段），只缩字号
FS_BAR_LABEL = 8.4      # 柱顶数字：加粗 + 放大，保证小尺寸下仍清晰可辨
FS_ANNOT = 9.0

# 全局字重：'normal'（细）或 'bold'（粗）。Times New Roman 自带 Bold 字形，
# 因此 'bold' 调用的是真 Times Bold，而不是描边加粗的伪粗体。
FONT_WEIGHT = "bold"

LW_SPINE = 0.8
LW_CURVE = 1.3
MARKER_SIZE = 3.6

FIG_W = 7.2
FIG_H = 2.95

MIB = 1024.0 * 1024.0

# ---------------------------------------------------------------------------
# 数据定义
# ---------------------------------------------------------------------------
DATASETS = [
    {"name": "MNIST", "model": "LeNet", "params": 44_426},
    {"name": "FMNIST", "model": "CNN", "params": 39_786},
    {"name": "CIFAR-10", "model": "ResNet-20", "params": 272_186},
    {"name": "SVHN", "model": "ResNet-32", "params": 460_618},
]

METHODS = ["FedAvg+CKKS", "FedPHE", "MASER", "ESAFL", "ECPFL"]

#    单密文字节            值/密文
CT_BYTES = {
    "FedAvg+CKKS": 124_928,   # 2 · 8192 · 61 / 8
    "FedPHE": 124_928,
    "MASER": 124_928,
    "ESAFL": 31_232,          # 1 · 4096 · 61 / 8，EP 打包后承载 8192 值
    "ECPFL": 31_232,
}
VALUES_PER_CT = {
    "FedAvg+CKKS": 4096,
    "FedPHE": 4096,
    "MASER": 4096,
    "ESAFL": 8192,
    "ECPFL": 4096,
}

# 论文表格中已给出的数字（用于校验），格式: (包数, 总大小 MiB)
GIVEN: Dict[str, List[Tuple[int, float]]] = {
    "FedAvg+CKKS": [(11, 1.311), (10, 1.191), (67, 7.982), (113, 13.463)],
    "FedPHE": [(11, 1.311), (10, 1.191), (67, 7.982), (113, 13.463)],
    "MASER": [(11, 1.311), (10, 1.191), (67, 7.982), (113, 13.463)],
    "ESAFL": [(6, 0.179), (5, 0.149), (34, 1.013), (57, 1.698)],
    "ECPFL": [(11, 0.328), (10, 0.298), (67, 1.996), (113, 3.366)],
}

# ---------------------------------------------------------------------------
# 五方法配色
# ---------------------------------------------------------------------------
METHOD_PALETTES: Dict[str, Dict] = {
    "fig6": {
        "group": "Baseline",
        "label": "Original Fig.6 — navy / green / teal / purple / red",
        "colors": ["#1F4E79", "#2E9E3E", "#17A2B8", "#8C6BB1", "#E31A1C"],
    },
    "npg": {
        "group": "Journal standard",
        "label": "NPG — Nature Publishing Group",
        "colors": ["#3C5488", "#00A087", "#4DBBD5", "#8491B4", "#E64B35"],
    },
    "aaas": {
        "group": "Journal standard",
        "label": "AAAS — Science",
        "colors": ["#3B4992", "#008B45", "#EE0000", "#631879", "#E69F00"],
    },
    "lancet": {
        "group": "Journal standard",
        "label": "Lancet",
        "colors": ["#00468B", "#42B540", "#ED0000", "#0099B4", "#925E9F"],
    },
    "nejm": {
        "group": "Journal standard",
        "label": "NEJM",
        "colors": ["#BC3C29", "#0072B5", "#E18727", "#20854E", "#6F99AD"],
    },
    "okabe_ito": {
        "group": "Journal standard",
        "label": "Okabe-Ito — colour-blind safe",
        "colors": ["#0072B2", "#009E73", "#E69F00", "#CC79A7", "#D55E00"],
    },
    "dark": {
        "group": "Dark",
        "label": "Dark — deep jewel tones",
        "colors": ["#1B3A5C", "#1B6B3A", "#0F5F6B", "#4A3B6B", "#8C2F26"],
    },
    "dark_earth": {
        "group": "Dark",
        "label": "Dark — earth & ink",
        "colors": ["#2F3E46", "#6B4226", "#0B525B", "#5A3E5C", "#8C3B2E"],
    },
    "muted": {
        "group": "Muted",
        "label": "Muted — Morandi",
        "colors": ["#7D94A6", "#8FA69B", "#C2A08E", "#B5A0A8", "#A8705F"],
    },
    "mono_blue": {
        "group": "Mono",
        "label": "Mono — blue ramp",
        "colors": ["#0B2545", "#134074", "#3A6EA5", "#6C93B8", "#A8C4DC"],
    },
}

METHOD_GROUP_ORDER = ["Baseline", "Journal standard", "Dark", "Muted", "Mono"]

# ---------------------------------------------------------------------------
# 计算与校验
# ---------------------------------------------------------------------------
def compute() -> Dict[str, List[Tuple[int, float]]]:
    out: Dict[str, List[Tuple[int, float]]] = {}
    for m in METHODS:
        rows = []
        for d in DATASETS:
            batches = math.ceil(d["params"] / VALUES_PER_CT[m])
            rows.append((batches, batches * CT_BYTES[m] / MIB))
        out[m] = rows
    return out


def verify() -> Dict[str, List[Tuple[int, float]]]:
    print("=" * 78)
    print("VERIFY — 逐格重算 baseline_encryption_same_security.md")
    print("=" * 78)
    calc = compute()
    bad = 0
    for m in METHODS:
        for i, d in enumerate(DATASETS):
            cb, cs = calc[m][i]
            gb, gs = GIVEN[m][i]
            ok_b = cb == gb
            ok_s = abs(cs - gs) <= 0.0006
            flag = "OK " if (ok_b and ok_s) else "DIFF"
            if not (ok_b and ok_s):
                bad += 1
            print(f"  [{flag}] {m:<12s} {d['name']:<9s} "
                  f"ct={CT_BYTES[m]:>7,}B  v/ct={VALUES_PER_CT[m]:>4d}  "
                  f"包数 {cb:>3d} (表 {gb:>3d})   "
                  f"MiB {cs:>6.3f} (表 {gs:>6.3f})")

    print("-" * 78)
    print("附加校验")
    for d in DATASETS:
        pass
    ratios = []
    for i, d in enumerate(DATASETS):
        r = calc["FedAvg+CKKS"][i][1] / calc["ECPFL"][i][1]
        ratios.append(r)
        print(f"  ratio FedAvg/ECPFL  {d['name']:<9s} = {r:.4f}")
    print(f"  → 四数据集比值一致: {max(ratios) - min(ratios) < 1e-3}")
    print(f"  → 结构因子 2·8192 / (1·4096) = {2 * 8192 / 4096:.1f}")
    print("-" * 78)

    # 单位核对：表头写 MB，实际按 2^20 计（MiB）
    ex_b = GIVEN["FedAvg+CKKS"][0][0] * CT_BYTES["FedAvg+CKKS"]
    print(f"  单位核对：11×124,928 = {ex_b:,} B "
          f"= {ex_b / MIB:.3f} MiB（表中值） / {ex_b / 1e6:.3f} MB（十进制）")
    print(f"  → 表中数值为 MiB，列名如写 'MB' 需在正文注明 1 MB = 2^20 B")
    print("=" * 78)
    if bad:
        print(f"!! 有 {bad} 个单元格与给定值不符，请先修正再出图")
    return calc


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = FONT_WEIGHT) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    # scienceplots 会重置 font.*，字重同样必须在 style 生效后再覆盖
    plt.rcParams["font.weight"] = font_weight


def noniid_legend(ax, **overrides):
    """与 noniid_step_1x2(_set1) 系列完全同规格的图例。

    12 pt、常规粗细（不继承全局 font.weight=bold）、Times serif、
    灰框 #888888 / 0.7 pt、borderpad 0.30、labelspacing 0.28、
    handlelength 1.9、handletextpad 0.55、borderaxespad 0.35。
    """
    kw = dict(loc="upper left", fontsize=FS_LEGEND_NONIID, frameon=True,
              fancybox=False, framealpha=0.95, edgecolor="#888888",
              facecolor="white", borderpad=0.30, labelspacing=0.28,
              handlelength=1.9, handletextpad=0.55, borderaxespad=0.35)
    kw.update(overrides)
    leg = ax.legend(**kw)
    leg.get_frame().set_linewidth(0.7)
    for t in leg.get_texts():          # 全局 font.weight=bold，这里压回常规
        t.set_fontweight("normal")
    return leg


def compact_legend(ax, style: str = "compact", **overrides):
    """(a)(b) 共用的紧凑图例（style="noniid" 时切到 noniid_step_1x2 规格）。

    字号比坐标轴刻度小一档，行距 / 手柄 / 内边距一并收紧。原规格在 (b) 里
    筑成约 0.8 个数量级高的方块（下沿压到 y≈3），右下角正好贴上
    FMNIST→CIFAR-10 的陡升段；收紧后高度降到约 0.6 个数量级，回到空白区。
    """
    if style == "noniid":
        return noniid_legend(ax, **overrides)

    kw = dict(loc="upper left", fontsize=FS_LEGEND - 1.4, frameon=True,
              fancybox=False, framealpha=0.95, edgecolor="#666666",
              facecolor="white", borderpad=0.24, labelspacing=0.10,
              handlelength=1.00, handletextpad=0.32, borderaxespad=0.32,
              markerscale=0.78)
    kw.update(overrides)
    leg = ax.legend(**kw)
    leg.get_frame().set_linewidth(0.6)
    return leg


def draw_panel_a(ax, data: Dict[str, List[Tuple[int, float]]], colors: List[str],
                 legend_style: str = "compact") -> None:
    n_ds, n_m = len(DATASETS), len(METHODS)
    x = np.arange(n_ds)
    total_w = 0.78
    w = total_w / n_m

    for j, m in enumerate(METHODS):
        vals = [data[m][i][0] for i in range(n_ds)]
        offs = x - total_w / 2 + w * (j + 0.5)
        ax.bar(offs, vals, width=w * 0.86, color=colors[j], alpha=0.92,
               edgecolor="white", linewidth=0.4, label=m, zorder=3)

    # 相邻同值柱只标一次，标签落在整段的中点，避免 "113 113 113" 挤在一起
    for i in range(n_ds):
        run_start = 0
        for j in range(1, n_m + 1):
            same = (j < n_m
                    and data[METHODS[j]][i][0] == data[METHODS[run_start]][i][0])
            if same:
                continue
            v = data[METHODS[run_start]][i][0]
            x_lo = x[i] - total_w / 2 + w * (run_start + 0.5)
            x_hi = x[i] - total_w / 2 + w * (j - 0.5)
            ax.text(0.5 * (x_lo + x_hi), v + 2.2, f"{v}", ha="center", va="bottom",
                    fontsize=FS_BAR_LABEL, fontweight="bold", color="#000000",
                    zorder=5)
            run_start = j

    ax.set_xticks(x)
    ax.set_xticklabels([f"{d['name']}\n{d['model']}" for d in DATASETS],
                       fontsize=FS_TICK, linespacing=1.15)
    ax.set_ylabel("Number of packs", fontsize=FS_AXIS_LABEL)
    ax.set_ylim(0, 130)
    ax.set_xlim(-0.6, n_ds - 0.4)
    ax.yaxis.set_major_locator(plt.MultipleLocator(25))
    ax.tick_params(axis="both", labelsize=FS_TICK, width=LW_SPINE, length=3)
    ax.grid(True, axis="y", linestyle="--", alpha=0.30, zorder=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_linewidth(LW_SPINE)
    compact_legend(ax, style=legend_style)

# (b) 逐方法微小平移：FedAvg / FedPHE / MASER 三者数值完全相同，
#     不平移会完全重叠、只剩最后画的一条可见。平移仅 ±0.07 个类目宽度，
#     属于纯视觉分离，不改变任何数值。
DODGE = {
    "FedAvg+CKKS": -0.140,
    "FedPHE": -0.070,
    "MASER": 0.0,
    "ESAFL": 0.070,
    "ECPFL": 0.140,
}

# 线型 / 标记再做一重区分，保证黑白打印与色弱读者也能分辨
MARK_STYLE = {
    "FedAvg+CKKS": dict(marker="o", ms=4.0, ls="-", hollow=False),
    "FedPHE": dict(marker="^", ms=4.4, ls=(0, (4.0, 1.8)), hollow=False),
    "MASER": dict(marker="o", ms=2.6, ls=(0, (1.0, 1.0)), hollow=False),
    "ESAFL": dict(marker="s", ms=3.8, ls=(0, (4.0, 2.0)), hollow=True),
    "ECPFL": dict(marker="D", ms=3.4, ls="-", hollow=False),
}


def draw_panel_b(ax, data: Dict[str, List[Tuple[int, float]]], colors: List[str],
                 legend_style: str = "compact") -> None:
    x = np.arange(len(DATASETS))

    for j, m in enumerate(METHODS):
        st = MARK_STYLE[m]
        xs = x + DODGE[m]
        ys = [data[m][i][1] for i in range(len(DATASETS))]
        ax.plot(xs, ys, color=colors[j], linewidth=LW_CURVE,
                linestyle=st["ls"], marker=st["marker"], markersize=st["ms"],
                markerfacecolor="white" if st["hollow"] else colors[j],
                markeredgecolor=colors[j], markeredgewidth=1.1 if st["hollow"] else 0.8,
                label=m, zorder=5 + j, clip_on=False)

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d['name']}\n{d['model']}" for d in DATASETS],
                       fontsize=FS_TICK, linespacing=1.15)
    ax.set_xlim(-0.42, len(DATASETS) - 0.42)
    ax.set_ylim(0.12, 18)
    # 单位写 MB（与论文表格口径一致：1 MB = 2^20 B，数值不变）
    ax.set_ylabel("Total ciphertext size (MB)", fontsize=FS_AXIS_LABEL)

    ticks = [0.1, 0.2, 0.5, 1, 2, 5, 10]
    ax.yaxis.set_major_locator(plt.FixedLocator(ticks))
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.tick_params(axis="both", labelsize=FS_TICK, width=LW_SPINE, length=3)
    ax.grid(True, axis="y", linestyle="--", alpha=0.30, which="major", zorder=0)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_linewidth(LW_SPINE)

    # 图例置于左上角空白区（x < 1.4 处曲线最高只到 2.4），用两栏共用的
    # 紧凑规格，避免盒体下沿压到 FMNIST→CIFAR-10 的陡升段。
    # noniid 规格下 12 pt 盒体（1.58×1.05 in）会盖住陡升段，本图字号降到 9.5 pt，
    # 并把手柄/间距微收（否则盒右边缘仍越过 x≈1.37 压住曲线）。
    # 字体族、字重、灰框 #888888 / 0.7 pt 与 noniid_step_1x2 保持一致。
    if legend_style == "noniid":
        compact_legend(ax, style="noniid", fontsize=FS_LEGEND_NONIID_B,
                       handlelength=1.30, handletextpad=0.45,
                       borderpad=0.26, labelspacing=0.22)
    else:
        compact_legend(ax, style=legend_style)


def build_overview(out_root: Path) -> None:
    """五方法配色总览：一行一套，一屏看完 10 套。"""
    from matplotlib.patches import Rectangle

    rows: List[Tuple[str, str]] = [("cols", "")]
    for g in METHOD_GROUP_ORDER:
        keys = [k for k, v in METHOD_PALETTES.items() if v.get("group") == g]
        if not keys:
            continue
        rows.append(("header", g))
        rows.extend(("theme", k) for k in keys)

    apply_style()
    n = len(rows)
    fig, ax = plt.subplots(figsize=(7.2, 0.235 * n + 0.28))
    ax.set_xlim(0, 1)
    ax.set_ylim(n, 0)
    ax.axis("off")

    x0, w, gap = 0.470, 0.052, 0.009
    h, top = 0.60, 0.20

    for i, (kind, key) in enumerate(rows):
        cy = i + 0.5
        if kind == "cols":
            ax.text(0.010, cy, "palette", fontsize=7, va="center", color="#444444")
            ax.text(x0, cy, "method colours (FedAvg / FedPHE / MASER / ESAFL / ECPFL)",
                    fontsize=7, va="center", color="#444444")
            continue
        if kind == "header":
            ax.text(0.005, cy, f"— {key} —", fontsize=7.5, va="center",
                    fontweight="bold", color="#111111")
            continue

        ax.text(0.010, cy, key, fontsize=7, va="center", color="black")
        ax.text(0.115, cy, METHOD_PALETTES[key]["label"], fontsize=6.0,
                va="center", color="#555555")
        for j, c in enumerate(METHOD_PALETTES[key]["colors"]):
            ax.add_patch(Rectangle((x0 + j * (w + gap), i + top), w, h,
                                   facecolor=c, edgecolor="none"))

    for ext in ("png", "pdf"):
        p = out_root / f"_overview_methods.{ext}"
        fig.savefig(p, dpi=400, bbox_inches="tight", facecolor="white")
        print(f"[SAVE]  {p}")
    plt.close(fig)


def build_figure(theme: str = "fig6",
                 figsize: Tuple[float, float] = (FIG_W, FIG_H),
                 font_scale: float = 1.0,
                 font_weight: str = FONT_WEIGHT):
    global FS_AXIS_LABEL, FS_TICK, FS_LEGEND, FS_BAR_LABEL, FS_ANNOT
    if font_scale != 1.0:
        FS_AXIS_LABEL *= font_scale
        FS_TICK *= font_scale
        FS_LEGEND *= font_scale
        FS_BAR_LABEL *= font_scale
        FS_ANNOT *= font_scale

    data = compute()
    colors = METHOD_PALETTES[theme]["colors"]

    apply_style(font_weight)
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=0.20,
                          left=0.075, right=0.99, bottom=0.155, top=0.905)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])

    draw_panel_a(ax_a, data, colors)
    draw_panel_b(ax_b, data, colors)

    for ax, tag in ((ax_a, "(a)"), (ax_b, "(b)")):
        ax.set_title(tag, fontsize=10.0 * font_scale, fontweight="bold", pad=4)
    return fig


def build_panel(which: str, theme: str = "fig6",
                figsize: Tuple[float, float] = (3.55, 2.95),
                font_weight: str = FONT_WEIGHT,
                legend_style: str = "compact"):
    """单面板图（which = "a" / "b"），不带 (a)(b) 角标。

    与 2x1 主图共用 draw_panel_*，只把画布缩到单栏宽，边距按单轴重设，
    字号、刻度、图例规格全部沿用主图（FS_AXIS_LABEL / FS_TICK / FS_LEGEND …）。
    legend_style="noniid" 时图例改用 noniid_step_1x2 系列规格。
    """
    data = compute()
    colors = METHOD_PALETTES[theme]["colors"]

    apply_style(font_weight)
    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(left=0.170, right=0.985, bottom=0.190, top=0.965)

    if which == "a":
        draw_panel_a(ax, data, colors, legend_style=legend_style)
    elif which == "b":
        draw_panel_b(ax, data, colors, legend_style=legend_style)
    else:
        raise ValueError(f"unknown panel: {which}")
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Fig. 6 — 包数量与密文大小")
    parser.add_argument("--theme", type=str, default="all",
                        help=f"{', '.join(METHOD_PALETTES)} 或 all")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--font-scale", type=float, default=1.0)
    parser.add_argument("--font-weight", type=str, default=FONT_WEIGHT,
                        choices=["normal", "bold"],
                        help="全局字重（默认 bold，调用 Times Bold 字形）")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--skip-panels", action="store_true",
                        help="只出 2x1 主图，不额外导出单面板")
    parser.add_argument("--legend-style", type=str, default="compact",
                        choices=["compact", "noniid"],
                        help="compact=原紧凑规格；noniid=与 noniid_step_1x2 系列一致")
    parser.add_argument("--panels-only", action="store_true",
                        help="只导出单面板（不动 2x1 主图与 overview）")
    args = parser.parse_args()

    if not args.skip_verify:
        verify()

    names = list(METHOD_PALETTES) if args.theme == "all" else [args.theme]
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    if len(names) > 1 and not args.panels_only:
        build_overview(out_root)

    # 图例规格切换时另存新文件，绝不覆盖已有图
    suffix = "" if args.legend_style == "compact" else f"_{args.legend_style}_legend"

    for name in names:
        sub = out_root / name if len(names) > 1 else out_root
        sub.mkdir(parents=True, exist_ok=True)

        if not args.panels_only:
            fig = build_figure(name, font_weight=args.font_weight)
            for ext in ("png", "pdf"):
                p = sub / f"fig6_batches_ciphertext{'' if not suffix else suffix}.{ext}"
                fig.savefig(p, dpi=args.dpi, bbox_inches="tight", facecolor="white")
                print(f"[SAVE]  {p}")
            plt.close(fig)

        # ---- 单独子图：与主图同目录下的 panels/，标题里不带 (a)(b) ----
        if args.skip_panels:
            continue
        panel_dir = sub / "panels"
        panel_dir.mkdir(parents=True, exist_ok=True)
        for which, fname in (("a", "batches"), ("b", "ciphertext_size")):
            pfig = build_panel(which, name, font_weight=args.font_weight,
                               legend_style=args.legend_style)
            for ext in ("png", "pdf"):
                p = panel_dir / f"{fname}{suffix}.{ext}"
                pfig.savefig(p, dpi=args.dpi, bbox_inches="tight",
                             facecolor="white")
                print(f"[SAVE]  {p}")
            plt.close(pfig)


if __name__ == "__main__":
    main()
