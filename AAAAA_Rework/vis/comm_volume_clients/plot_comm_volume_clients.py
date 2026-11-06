"""客户端数量 vs 通信量（UV / FV / PV 堆叠柱，GB）

数据来源（AC / TV / PV / FV 表，GB）：

    N      K      AC(%)    TV      PV      FV
    50     25     91.30   0.500   0.383   0.002
    100    50     97.17   0.999   0.765   0.003
    500    250    95.54   4.997   3.826   0.016
    1000   500    90.84   9.994   7.652   0.031

说明
1. 表中只给了总量 TV 与 PV / FV 两个分量，UV 按 TV - PV - FV 反推（脚本内 VERIFY 会校验
   三段之和是否等于 TV）。
2. 原表 N=1000 行的 PV 写作 "7652"，与 0.383 → 0.765 → 3.826 的等比趋势不符（应为 7.652）；
   本脚本按 7.652 绘制，若原始数据确实是 7652 需要修正。
3. 不含准确率（AC）曲线，只画通信量。

版面：与 vis/upload_volume_dropout/upload_volume_accuracy.png 一致
      （5.15 x 4.30 in、1.20:1、Times、字号 14.5/12.5/9.8/9.5、四边框齐全）。
配色：全部为条纹（hatch）方案，UV 点、FV 左斜、PV 右斜。

用法
    python AAAAA_Rework/vis/comm_volume_clients/plot_comm_volume_clients.py
    python AAAAA_Rework/vis/comm_volume_clients/plot_comm_volume_clients.py --theme cobalt_orange_hatch
    python AAAAA_Rework/vis/comm_volume_clients/plot_comm_volume_clients.py --list-themes
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR

# ---------------------------------------------------------------------------
# 字体：与 vis/ 下其它图一致（Times）
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

# 与 upload_volume_accuracy.png 完全一致的字号
FS_AXIS_LABEL = 18.0      # 轴标题：与 method_comparison_contrast 子图一致（18 pt）
FS_TICK = 15.5            # 刻度值 12.5 + 3
FS_LEGEND = 11.8          # 图例 9.8 + 2
FS_BAR_LABEL = 13.5       # 柱顶数字 9.5 + 4

FONT_WEIGHT = "bold"
LW_SPINE = 1.0

# 横轴略长：1.20 : 1
# 画布与 upload_volume_accuracy 完全一致（5.67 x 3.99，绘图区 4.6667 x 3.0967 in）：
# 右边距虽无内容，仍与 (a) 保持同宽，保证两图按 \linewidth 插入时轴框同大
AX_W = 4.6667
AX_H = 3.0967
M_LEFT, M_RIGHT = 0.62, 0.38
M_BOTTOM, M_TOP = 0.55, 0.34
FIG_W = M_LEFT + AX_W + M_RIGHT          # 5.6667
FIG_H = M_TOP + AX_H + M_BOTTOM          # 3.9867
BAR_W = 0.56

EDGE_COLOR = "#555555"
EDGE_WIDTH = 0.45
HATCH_LW = 0.55

# FV 只有 0.002--0.031 GB，在 0--12.4 的主轴上不足 1.5 像素，必须单独给尺度：
# 左上角插入一个小图，把 FV 换算成 MB 单独画（主图几何完全不变，不引入任何失真）
SHOW_FV_INSET = True

# ---------------------------------------------------------------------------
# 数据（GB）
# ---------------------------------------------------------------------------
CLIENTS = [50, 100, 500, 1000]
AC = [91.30, 97.17, 95.54, 90.84]          # 仅作记录，本图不画

TV = [0.500, 0.999, 4.997, 9.994]
PV = [0.383, 0.765, 3.826, 7.652]
FV = [0.002, 0.003, 0.016, 0.031]
# UV = TV - PV - FV（上传量）
UV = [round(t - p - f, 4) for t, p, f in zip(TV, PV, FV)]

TOL_VOL = 0.002

# ---------------------------------------------------------------------------
# 配色（全部条纹）：
#   uv  = 底层（点），fv = 中层（左斜），pv = 顶层（右斜）
# ---------------------------------------------------------------------------
THEMES: Dict[str, Dict] = {
    "cobalt_orange_hatch": {
        "group": "Hatched",
        "label": "Hatch — cobalt / navy / orange",
        "colors": {"uv": "#58A8E8", "fv": "#123E7C", "pv": "#FF8C1A"},
    },
    "crimson_cobalt_hatch": {
        "group": "Hatched",
        "label": "Hatch — sky / cobalt / crimson",
        "colors": {"uv": "#7EC0F2", "fv": "#14418F", "pv": "#EF3B2C"},
    },
    "scarlet_azure_hatch": {
        "group": "Hatched",
        "label": "Hatch — azure / deep navy / scarlet",
        "colors": {"uv": "#5CC8F5", "fv": "#0A4C8C", "pv": "#FF4757"},
    },
    "coral_teal_hatch": {
        "group": "Hatched",
        "label": "Hatch — coral / teal",
        "colors": {"uv": "#72D6C9", "fv": "#12675E", "pv": "#F78154"},
    },
    "emerald_tangerine_hatch": {
        "group": "Hatched",
        "label": "Hatch — emerald / tangerine",
        "colors": {"uv": "#7BE0AD", "fv": "#12664F", "pv": "#FF9F1C"},
    },
    "violet_lime_hatch": {
        "group": "Hatched",
        "label": "Hatch — violet / lime",
        "colors": {"uv": "#A98CE8", "fv": "#4B2E83", "pv": "#8BD450"},
    },
    "okabe_ito_hatch": {
        "group": "Hatched",
        "label": "Hatch — Okabe-Ito (colour-blind safe)",
        "colors": {"uv": "#56B4E9", "fv": "#0072B2", "pv": "#E69F00"},
    },
    "magenta_teal_hatch": {
        "group": "Hatched",
        "label": "Hatch — magenta / teal / yellow",
        "colors": {"uv": "#FF7EB0", "fv": "#0F6B5F", "pv": "#FFD93D"},
    },
    # ---------------- 全斜线（三段都是斜条纹，方向/密度区分） ----------------
    "indigo_amber_diag": {
        "group": "Diagonal",
        "label": "Diag — amber / indigo / red",
        "colors": {"uv": "#FFC857", "fv": "#1F2A6B", "pv": "#E84855"},
        "hatch": {"uv": "/", "fv": "\\\\", "pv": "//"},
    },
    "teal_magenta_diag": {
        "group": "Diagonal",
        "label": "Diag — mint / slate / magenta",
        "colors": {"uv": "#7FD8BE", "fv": "#264653", "pv": "#C43E8B"},
        "hatch": {"uv": "\\\\", "fv": "//", "pv": "/"},
    },
    "slate_lime_diag": {
        "group": "Diagonal",
        "label": "Diag — lime / charcoal / pine",
        "colors": {"uv": "#A8E06E", "fv": "#2F3E46", "pv": "#52796F"},
        "hatch": {"uv": "//", "fv": "/", "pv": "\\\\"},
    },
    "rose_steel_diag": {
        "group": "Diagonal",
        "label": "Diag — rose / near-black / steel",
        "colors": {"uv": "#F7B2BD", "fv": "#2B2D42", "pv": "#577590"},
        "hatch": {"uv": "///", "fv": "\\\\", "pv": "/"},
    },
    "sun_clay_diag": {
        "group": "Diagonal",
        "label": "Diag — sun / clay / deep green",
        "colors": {"uv": "#FFB347", "fv": "#5C2E1A", "pv": "#0B6E4F"},
        "hatch": {"uv": "/", "fv": "///", "pv": "\\\\"},
    },
}

GROUP_ORDER = ["Hatched", "Diagonal"]

# 默认条纹（点 / 左斜 / 右斜）；带 "hatch" 字段的主题覆盖它
HATCH = {"uv": "..", "fv": "///", "pv": "\\\\"}

LEGEND_LABELS = {
    "uv": r"$\mathrm{UV}$",
    "fv": r"$\mathrm{FV}$",
    "pv": r"$\mathrm{PV}$",
}


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------
def verify() -> None:
    print("=" * 72)
    print("VERIFY — UV + FV + PV ?= TV (GB)")
    print("=" * 72)
    bad = 0
    for i, n in enumerate(CLIENTS):
        s = UV[i] + FV[i] + PV[i]
        ok = abs(s - TV[i]) <= TOL_VOL
        bad += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'DIFF'}] N={n:>4d}  "
              f"UV={UV[i]:6.3f} + FV={FV[i]:6.3f} + PV={PV[i]:6.3f} "
              f"= {s:7.3f}  (TV {TV[i]:7.3f})")
    print("-" * 72)
    print(f"  TV strictly increasing: {all(a < b for a, b in zip(TV, TV[1:]))}")
    print(f"  PV <= TV in every row:  {all(p <= t for p, t in zip(PV, TV))}")
    print("=" * 72)
    if bad:
        print(f"!! {bad} row(s) mismatch — fix data before plotting")


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = FONT_WEIGHT) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    plt.rcParams["font.weight"] = font_weight
    # SciencePlots 标准外观：上/右两条框线也带向内刻度（四边对称）
    plt.rcParams["xtick.top"] = True
    plt.rcParams["ytick.right"] = True
    # 次刻度保持关闭，避免 5 条 α 柱之间出现多余短线
    plt.rcParams["xtick.minor.visible"] = False
    plt.rcParams["ytick.minor.visible"] = False
    # SciencePlots 默认 savefig.bbox=tight，会按内容裁切画布；
    # 这里改回 standard，保证输出严格等于 FIG_W x FIG_H（与 upload_volume 图一致）
    plt.rcParams["savefig.bbox"] = "standard"
    plt.rcParams["hatch.linewidth"] = HATCH_LW


def build_figure(theme: str = "cobalt_orange_hatch"):
    th = THEMES[theme]
    c = th["colors"]
    h = th.get("hatch", HATCH)
    apply_style()

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    # 绘图区 4.6667 x 3.0967 in；边距与 upload_volume_accuracy 完全一致（M_* 英寸换算）
    fig.subplots_adjust(left=M_LEFT / FIG_W, right=1 - M_RIGHT / FIG_W,
                        bottom=M_BOTTOM / FIG_H, top=1 - M_TOP / FIG_H)

    x = np.arange(len(CLIENTS))
    uv = np.array(UV)
    fv = np.array(FV)
    pv = np.array(PV)

    stack_kw = dict(edgecolor=EDGE_COLOR, linewidth=EDGE_WIDTH, zorder=3)

    ax.bar(x, uv, BAR_W, color=c["uv"], hatch=h["uv"],
           label=LEGEND_LABELS["uv"], **stack_kw)
    ax.bar(x, fv, BAR_W, bottom=uv, color=c["fv"], hatch=h["fv"],
           label=LEGEND_LABELS["fv"], **stack_kw)
    ax.bar(x, pv, BAR_W, bottom=uv + fv, color=c["pv"], hatch=h["pv"],
           label=LEGEND_LABELS["pv"], **stack_kw)

    # ---- 柱顶总量 ----
    for i, tot in enumerate(TV):
        ax.text(x[i], tot + 0.18, f"{tot:.2f}", ha="center", va="bottom",
                fontsize=FS_BAR_LABEL, fontweight="bold", color="#111111",
                zorder=7)

    # ---- FV 放大插图：单独尺度（MB），主图几何不变（窗口加大便于阅读）----
    if SHOW_FV_INSET:
        fv_mb = np.array(FV) * 1000.0
        ins = ax.inset_axes([0.068, 0.500, 0.378, 0.290])
        ins.bar(x, fv_mb, BAR_W, color=c["fv"], hatch=h["fv"],
                edgecolor=EDGE_COLOR, linewidth=EDGE_WIDTH, zorder=3)
        for i, v in enumerate(fv_mb):
            ins.text(x[i], v + 0.9, f"{v:.0f}", ha="center", va="bottom",
                     fontsize=10.6, fontweight="bold", color="#111111", zorder=6)
        ins.set_ylim(0, 40)
        ins.set_yticks([])                     # 数值已标在柱顶，去掉纵轴刻度更干净
        ins.set_xlim(-0.60, len(x) - 0.40)
        ins.set_xticks(x)
        ins.set_xticklabels([f"{n:d}" for n in CLIENTS])
        ins.set_title(r"$\mathrm{FV}$ (MB)", fontsize=11.5, pad=2.5)
        ins.tick_params(axis="x", labelsize=10.6, width=0.6, length=2.0, pad=2)
        ins.tick_params(axis="y", width=0.6, length=0.0)
        ins.grid(False)
        for s in ins.spines.values():
            s.set_visible(True)
            s.set_color("black")
            s.set_linewidth(0.6)

    # ---- 轴 ----
    # 轴标题沿用参考图样式：18 pt、常规粗细（不加粗）、Times serif
    ax.set_ylabel("Communication Volume (GB)", fontsize=FS_AXIS_LABEL,
                  fontweight="normal")
    ax.set_xlabel("Number of Clients", fontsize=FS_AXIS_LABEL,
                  fontweight="normal", labelpad=5)
    ax.set_ylim(0, 12.4)
    ax.set_yticks(np.arange(0, 10.1, 2))
    ax.set_xlim(-0.55, len(x) - 0.45)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n:d}" for n in CLIENTS], fontsize=FS_TICK)
    ax.tick_params(axis="y", labelsize=FS_TICK, width=LW_SPINE, length=3.2)
    ax.tick_params(axis="x", labelsize=FS_TICK, width=LW_SPINE, length=3.2, pad=4)
    ax.grid(True, axis="y", linestyle="--", linewidth=0.55, alpha=0.40, zorder=0)
    ax.set_axisbelow(True)
    for s in ("left", "bottom", "top", "right"):     # 四边封框
        ax.spines[s].set_linewidth(LW_SPINE)
        ax.spines[s].set_visible(True)
        ax.spines[s].set_color("black")

    # ---- 图例：单行横向（UV / FV / PV 从右往左排一行），贴顶框内侧 ----
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=3,
                    fontsize=FS_LEGEND, frameon=True, fancybox=False,
                    framealpha=0.96, edgecolor="#808080", facecolor="white",
                    borderpad=0.32, labelspacing=0.28, handlelength=1.25,
                    handletextpad=0.45, columnspacing=1.1, borderaxespad=0.30)
    leg.get_frame().set_linewidth(0.55)
    return fig


def build_overview(out_root: Path) -> None:
    """配色总览：一行一套，三色（uv / fv / pv）。"""
    from matplotlib.patches import Rectangle

    rows: List[Tuple[str, str]] = [("cols", "")]
    for g in GROUP_ORDER:
        keys = [k for k, v in THEMES.items() if v.get("group") == g]
        if not keys:
            continue
        rows.append(("header", g))
        rows.extend(("theme", k) for k in keys)

    apply_style()
    n = len(rows)
    fig, ax = plt.subplots(figsize=(7.2, 0.26 * n + 0.30))
    ax.set_xlim(0, 1)
    ax.set_ylim(n, 0)
    ax.axis("off")

    x0, w, gap = 0.640, 0.048, 0.008
    hh, top = 0.62, 0.19

    for i, (kind, key) in enumerate(rows):
        cy = i + 0.5
        if kind == "cols":
            ax.text(0.010, cy, "theme", fontsize=7, va="center", color="#444444")
            ax.text(x0, cy, "UV / FV / PV",
                    fontsize=7, va="center", color="#444444")
            continue
        if kind == "header":
            ax.text(0.005, cy, f"— {key} —", fontsize=7.5, va="center",
                    fontweight="bold", color="#111111")
            continue
        th = THEMES[key]
        th_h = th.get("hatch", HATCH)
        ax.text(0.010, cy, key, fontsize=6.6, va="center", color="black")
        ax.text(0.255, cy, th["label"], fontsize=6.2, va="center", color="#555555")
        for j, k in enumerate(("uv", "fv", "pv")):
            ax.add_patch(Rectangle((x0 + j * (w + gap), i + top), w, hh,
                                   facecolor=th["colors"][k],
                                   hatch=th_h[k],
                                   edgecolor=EDGE_COLOR, linewidth=EDGE_WIDTH))

    for ext in ("png", "pdf"):
        p = out_root / f"_overview_themes.{ext}"
        fig.savefig(p, dpi=400, bbox_inches="tight", facecolor="white")
        print(f"[SAVE]  {p}")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="客户端数量 vs 通信量堆叠柱（UV/FV/PV）")
    parser.add_argument("--theme", type=str, default="all",
                        help=f"{', '.join(THEMES)} 或 all")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--list-themes", action="store_true")
    args = parser.parse_args()

    if args.list_themes:
        for g in GROUP_ORDER:
            keys = [k for k, v in THEMES.items() if v.get("group") == g]
            if keys:
                print(f"\n[{g}]")
                for k in keys:
                    print(f"  {k:<26s} {THEMES[k]['label']}")
        return

    if not args.skip_verify:
        verify()

    names = list(THEMES) if args.theme == "all" else [args.theme]
    out_root = Path(args.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    if len(names) > 1:
        build_overview(out_root)

    for name in names:
        fig = build_figure(name)
        sub = out_root / name if len(names) > 1 else out_root
        sub.mkdir(parents=True, exist_ok=True)
        for ext in ("png", "pdf"):
            p = sub / f"comm_volume_clients.{ext}"
            # 不做 tight 裁切：输出固定为 FIG_W x FIG_H（与 upload_volume 图严格一致）
            fig.savefig(p, dpi=args.dpi, facecolor="white")
            print(f"[SAVE]  {p}")
        plt.close(fig)


if __name__ == "__main__":
    main()
