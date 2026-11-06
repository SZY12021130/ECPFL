"""掉线率 vs 上传量（VOTE / PACK / COMP 堆叠柱）+ 测试准确率（折线）

数据（ECPFL，50 轮累计）：

    Dropout  Survivors  UV_vote  UV_pack  UV_comp   UV      AC
      0%       25       39.04     78.08     0.00   117.12  98.16
     10%       23       39.04     71.83    62.46   173.34  98.72
     20%       20       39.04     62.65    62.65   164.34  98.44
     30%       18       39.04     55.47    55.47   149.98  98.23
     40%       15       39.04     49.22    49.22   137.48  97.93

版面：宽高比 ≈ 1.2:1（横轴略长）；四边框齐全（top spine 打开）；
      堆叠三段之间无白边；配色参考 tools/plot_experiment/plot_grouped_bar，
      一半主题带条纹填充（hatch），一半纯色。
脚本自带 VERIFY 段：Vote+Pack+Comp 必须等于表中 UV（±0.02）。

用法
    python AAAAA_Rework/vis/upload_volume_dropout/plot_upload_volume_accuracy.py
    python AAAAA_Rework/vis/upload_volume_dropout/plot_upload_volume_accuracy.py --theme coral_teal
    python AAAAA_Rework/vis/upload_volume_dropout/plot_upload_volume_accuracy.py --list-themes
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

FS_AXIS_LABEL = 18.0      # 轴标题：与 method_comparison_contrast 子图一致（18 pt）
FS_TICK = 15.5            # 刻度值 12.5 + 3
FS_LEGEND = 11.8          # 图例 9.8 + 2
FS_BAR_LABEL = 13.5       # 柱顶数字 9.5 + 4

FONT_WEIGHT = "bold"
LW_SPINE = 1.0
LW_CURVE = 1.7
MARKER_SIZE = 4.8

# 布局改为“边距(英寸) + 绘图区(英寸)”双向固定：
# 绘图区 4.6667 x 3.0967 in 不变（与 accuracy_curves 系列相同）；
# 右轴标题改横排置于轴上方，右边距 0.72 -> 0.38 in，
# 画布 6.08x3.75 -> 5.67x3.99，轴框占画布宽 76.8% -> 82.3%
# （目标单轴图 88.5%；双轴 + 18pt 粗体刻度的物理下限约 83%）
AX_W = 4.6667
AX_H = 3.0967
M_LEFT, M_RIGHT = 0.62, 0.38
M_BOTTOM, M_TOP = 0.55, 0.34
FIG_W = M_LEFT + AX_W + M_RIGHT          # 5.6667
FIG_H = M_TOP + AX_H + M_BOTTOM          # 3.9867
BAR_W = 0.60

# 条纹描边（参考 plot_grouped_bar 的 EDGE_COLOR / EDGE_WIDTH）
EDGE_COLOR = "#555555"
EDGE_WIDTH = 0.45
HATCH_LW = 0.55

# ---------------------------------------------------------------------------
# 数据
# ---------------------------------------------------------------------------
DROPOUT = [0, 10, 20, 30, 40]
SURVIVORS = [25, 23, 20, 18, 15]
UV_VOTE = [39.04, 39.04, 39.04, 39.04, 39.04]
UV_PACK = [78.08, 71.83, 62.65, 55.47, 49.22]
UV_COMP = [0.00, 62.46, 62.65, 55.47, 49.22]
UV_TOTAL = [117.12, 173.34, 164.34, 149.98, 137.48]
AC = [98.16, 98.72, 98.44, 98.23, 97.93]

TOL_UV = 0.02

# ---------------------------------------------------------------------------
# 配色：高明度 / 高饱和，参考 plot_grouped_bar 的色彩体系
#   vote / pack / comp = 堆叠三段（浅 → 深 → 中调暖）
#   line              = 准确率折线
#   hatch             = 三段各自的条纹（"" 表示纯色，便于两版对照）
# ---------------------------------------------------------------------------
THEMES: Dict[str, Dict] = {
    # ---------------- 纯色（无条纹） ----------------
    "sky_navy_amber": {
        "group": "Solid",
        "label": "Solid — sky / navy / amber",
        "colors": {"vote": "#6EC6F0", "pack": "#1F3F73",
                   "comp": "#F5A03C", "line": "#D64045"},
        "hatch": {"vote": "", "pack": "", "comp": ""},
    },
    "ocean_lime": {
        "group": "Solid",
        "label": "Solid — turquoise / deep ocean / lime",
        "colors": {"vote": "#7BE0C8", "pack": "#0B6E99",
                   "comp": "#FFD166", "line": "#EF476F"},
        "hatch": {"vote": "", "pack": "", "comp": ""},
    },
    "royal_gold": {
        "group": "Solid",
        "label": "Solid — royal blue / gold",
        "colors": {"vote": "#9DB4FF", "pack": "#2B2D91",
                   "comp": "#FFC845", "line": "#E23E57"},
        "hatch": {"vote": "", "pack": "", "comp": ""},
    },
    "magenta_steel": {
        "group": "Solid",
        "label": "Solid — magenta / steel / sand",
        "colors": {"vote": "#F49AC1", "pack": "#3D5A80",
                   "comp": "#F4C27A", "line": "#B5175C"},
        "hatch": {"vote": "", "pack": "", "comp": ""},
    },
    # ---------------- 条纹 ----------------
    "coral_teal_hatch": {
        "group": "Hatched",
        "label": "Hatch — coral / teal",
        "colors": {"vote": "#72D6C9", "pack": "#12675E",
                   "comp": "#F78154", "line": "#C1292E"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "emerald_tangerine_hatch": {
        "group": "Hatched",
        "label": "Hatch — emerald / tangerine",
        "colors": {"vote": "#7BE0AD", "pack": "#12664F",
                   "comp": "#FF9F1C", "line": "#C1121F"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "violet_lime_hatch": {
        "group": "Hatched",
        "label": "Hatch — violet / lime",
        "colors": {"vote": "#A98CE8", "pack": "#4B2E83",
                   "comp": "#8BD450", "line": "#D7263D"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "okabe_ito_hatch": {
        "group": "Hatched",
        "label": "Hatch — Okabe-Ito (colour-blind safe)",
        "colors": {"vote": "#56B4E9", "pack": "#0072B2",
                   "comp": "#E69F00", "line": "#D55E00"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    # ---------------- 高饱和红蓝系（新增 5 套，全部带条纹） ----------------
    "crimson_cobalt_hatch": {
        "group": "Hatched",
        "label": "Hatch — crimson / cobalt (red+blue)",
        "colors": {"vote": "#7EC0F2", "pack": "#14418F",
                   "comp": "#EF3B2C", "line": "#0E7C42"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "scarlet_azure_hatch": {
        "group": "Hatched",
        "label": "Hatch — scarlet / azure",
        "colors": {"vote": "#5CC8F5", "pack": "#0A4C8C",
                   "comp": "#FF4757", "line": "#8E24AA"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "ruby_royal_hatch": {
        "group": "Hatched",
        "label": "Hatch — ruby / royal blue (red-dominant)",
        "colors": {"vote": "#F58A8A", "pack": "#A3122B",
                   "comp": "#3E7BC8", "line": "#D97706"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "cobalt_orange_hatch": {
        "group": "Hatched",
        "label": "Hatch — cobalt / orange",
        "colors": {"vote": "#58A8E8", "pack": "#123E7C",
                   "comp": "#FF8C1A", "line": "#B8001F"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
    "magenta_teal_hatch": {
        "group": "Hatched",
        "label": "Hatch — magenta / teal / yellow",
        "colors": {"vote": "#FF7EB0", "pack": "#0F6B5F",
                   "comp": "#FFD93D", "line": "#6A1B9A"},
        "hatch": {"vote": "..", "pack": "///", "comp": "\\\\"},
    },
}

GROUP_ORDER = ["Solid", "Hatched"]


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------
def verify() -> None:
    print("=" * 74)
    print("VERIFY — Vote + Pack + Comp ?= UV (table)")
    print("=" * 74)
    bad = 0
    for i, dp in enumerate(DROPOUT):
        s = UV_VOTE[i] + UV_PACK[i] + UV_COMP[i]
        ok = abs(s - UV_TOTAL[i]) <= TOL_UV
        bad += 0 if ok else 1
        print(f"  [{'OK ' if ok else 'DIFF'}] dropout={dp:>2d}%  "
              f"{UV_VOTE[i]:6.2f} + {UV_PACK[i]:6.2f} + {UV_COMP[i]:6.2f} "
              f"= {s:7.2f}  (table {UV_TOTAL[i]:7.2f})   AC={AC[i]:.2f}%")
    print("-" * 74)
    print(f"  survivors strictly decreasing: "
          f"{all(a > b for a, b in zip(SURVIVORS, SURVIVORS[1:]))}")
    print(f"  vote constant 39.04: {max(UV_VOTE) - min(UV_VOTE) < 1e-9}")
    print("=" * 74)
    if bad:
        print(f"!! {bad} row(s) mismatch the table — fix data before plotting")


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = FONT_WEIGHT) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    plt.rcParams["font.weight"] = font_weight
    # scienceplots 会打开顶部刻度与次刻度；本图只要有框无多余刻度
    plt.rcParams["xtick.top"] = False
    plt.rcParams["ytick.right"] = False
    plt.rcParams["xtick.minor.visible"] = False
    plt.rcParams["ytick.minor.visible"] = False
    # SciencePlots 默认 savefig.bbox=tight，会按内容裁切画布；
    # 这里改回 standard，保证输出严格等于 FIG_W x FIG_H（与 comm_volume 图一致）
    plt.rcParams["savefig.bbox"] = "standard"
    plt.rcParams["hatch.linewidth"] = HATCH_LW


def build_figure(theme: str = "sky_navy_amber"):
    th = THEMES[theme]
    c, h = th["colors"], th["hatch"]
    hatched = any(h.values())
    apply_style()

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    # 绘图区 4.6667 x 3.0967 in 不变；边距按 M_*（英寸）换算，右轴标题已移到轴上方
    fig.subplots_adjust(left=M_LEFT / FIG_W, right=1 - M_RIGHT / FIG_W,
                        bottom=M_BOTTOM / FIG_H, top=1 - M_TOP / FIG_H)

    x = np.arange(len(DROPOUT))
    vote = np.array(UV_VOTE)
    pack = np.array(UV_PACK)
    comp = np.array(UV_COMP)

    # 有 hatch 时必须留描边才能看见条纹；纯色版保持无缝
    stack_kw = (dict(edgecolor=EDGE_COLOR, linewidth=EDGE_WIDTH)
                if hatched else dict(edgecolor="none", linewidth=0.0))
    stack_kw["zorder"] = 3

    ax.bar(x, vote, BAR_W, color=c["vote"], hatch=h["vote"],
           label=r"Vote CT ($\mathrm{UV}_{\mathrm{vote}}$)", **stack_kw)
    ax.bar(x, pack, BAR_W, bottom=vote, color=c["pack"], hatch=h["pack"],
           label=r"Pack CT ($\mathrm{UV}_{\mathrm{pack}}$)", **stack_kw)
    ax.bar(x, comp, BAR_W, bottom=vote + pack, color=c["comp"], hatch=h["comp"],
           label=r"Comp CT ($\mathrm{UV}_{\mathrm{comp}}$)", **stack_kw)

    # ---- 柱顶总量 ----
    for i, tot in enumerate(UV_TOTAL):
        ax.text(x[i], tot + 4.0, f"{tot:.2f}", ha="center", va="bottom",
                fontsize=FS_BAR_LABEL, fontweight="bold", color="#111111",
                zorder=7)

    # ---- 左轴 ----
    # 轴标题沿用参考图样式：18 pt、常规粗细（不加粗）、Times serif
    ax.set_ylabel("Upload Volume (MB)", fontsize=FS_AXIS_LABEL,
                  fontweight="normal")
    ax.set_xlabel("Dropout Rate (%)", fontsize=FS_AXIS_LABEL,
                  fontweight="normal", labelpad=5)
    ax.set_ylim(0, 285)
    ax.set_yticks(np.arange(0, 251, 50))
    ax.set_xlim(-0.55, len(x) - 0.45)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{dp:g}" for dp in DROPOUT], fontsize=FS_TICK)
    ax.tick_params(axis="y", labelsize=FS_TICK, width=LW_SPINE, length=3.2,
                   right=False)
    ax.tick_params(axis="x", labelsize=FS_TICK, width=LW_SPINE, length=3.2, pad=4)
    ax.grid(True, axis="y", linestyle="--", linewidth=0.55, alpha=0.40, zorder=0)
    ax.set_axisbelow(True)
    for s in ("left", "bottom", "top"):          # 上方封框
        ax.spines[s].set_linewidth(LW_SPINE)
        ax.spines[s].set_visible(True)
    ax.spines["right"].set_visible(False)        # 右边由 twinx 提供

    # ---- 右轴：准确率 ----
    ax2 = ax.twinx()
    ax2.plot(x, AC, color=c["line"], linewidth=LW_CURVE, marker="o",
             markersize=MARKER_SIZE, markerfacecolor=c["line"],
             markeredgecolor="white", markeredgewidth=0.8,
             label="Test Accuracy", zorder=6, clip_on=False)
    # 右轴标题横排放在右上轴外（竖排需 0.72 in 右边距，横排只要 0.38 in），
    # 这是把轴框占画布比例从 76.8% 提到 82.3% 的关键
    ax2.text(1.0, 1.02, "Test Accuracy (%)", transform=ax2.transAxes,
             ha="right", va="bottom", fontsize=FS_AXIS_LABEL - 2,
             fontweight="normal", color="black")
    # 上限抬到 100.6（刻度仍 92-100）：曲线整体下移，避免峰值点碰到图例底边
    ax2.set_ylim(92, 100.6)
    ax2.set_yticks(np.arange(92, 101, 2))
    ax2.tick_params(axis="y", labelsize=FS_TICK, colors="black",
                    width=LW_SPINE, length=3.2, top=False)
    ax2.tick_params(axis="x", top=False, bottom=False, labelbottom=False)
    ax2.spines["right"].set_linewidth(LW_SPINE)
    ax2.spines["right"].set_color("black")
    # 上边框与 ax 的黑色顶线重合，这里透明，避免压住黑框
    ax2.spines["top"].set_visible(False)
    for s in ("left", "bottom"):
        ax2.spines[s].set_visible(False)

    # ---- 图例：两列，贴顶框内侧 ----
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    leg = ax.legend(h1 + h2, l1 + l2, loc="upper center",
                    bbox_to_anchor=(0.48, 0.995), ncol=2,
                    fontsize=FS_LEGEND, frameon=True, fancybox=False,
                    framealpha=0.96, edgecolor="#808080", facecolor="white",
                    borderpad=0.32, labelspacing=0.28, handlelength=1.25,
                    handletextpad=0.45, columnspacing=0.9,
                    borderaxespad=0.30)
    leg.get_frame().set_linewidth(0.55)
    return fig


def build_overview(out_root: Path) -> None:
    """配色总览：一行一套，四色（vote / pack / comp / line）。"""
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

    x0, w, gap = 0.585, 0.048, 0.008
    hh, top = 0.62, 0.19

    for i, (kind, key) in enumerate(rows):
        cy = i + 0.5
        if kind == "cols":
            ax.text(0.010, cy, "theme", fontsize=7, va="center", color="#444444")
            ax.text(x0, cy, "vote / pack / comp / accuracy-line",
                    fontsize=7, va="center", color="#444444")
            continue
        if kind == "header":
            ax.text(0.005, cy, f"— {key} —", fontsize=7.5, va="center",
                    fontweight="bold", color="#111111")
            continue
        th = THEMES[key]
        ax.text(0.010, cy, key, fontsize=6.6, va="center", color="black")
        ax.text(0.255, cy, th["label"], fontsize=6.2, va="center", color="#555555")
        for j, k in enumerate(("vote", "pack", "comp", "line")):
            ax.add_patch(Rectangle((x0 + j * (w + gap), i + top), w, hh,
                                   facecolor=th["colors"][k],
                                   hatch=th["hatch"].get(k, ""),
                                   edgecolor=EDGE_COLOR if th["hatch"].get(k) else "none",
                                   linewidth=EDGE_WIDTH))

    for ext in ("png", "pdf"):
        p = out_root / f"_overview_themes.{ext}"
        fig.savefig(p, dpi=400, bbox_inches="tight", facecolor="white")
        print(f"[SAVE]  {p}")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="上传量堆叠柱 + 准确率折线")
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
            p = sub / f"upload_volume_accuracy.{ext}"
            # 不做 tight 裁切：输出固定为 FIG_W x FIG_H（与 comm_volume 图严格一致）
            fig.savefig(p, dpi=args.dpi, facecolor="white")
            print(f"[SAVE]  {p}")
        plt.close(fig)


if __name__ == "__main__":
    main()
