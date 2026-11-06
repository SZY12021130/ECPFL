"""Fig. 5 — 数据集 batch 划分与带宽分布（双栏合并图，多配色版）

把原先两张独立的图合并为一幅双栏图：

    (a) 竖向分组柱状图                  —— 各数据集 pack 数（左轴）与密文大小（右轴，MB，2^20 口径）
        （源：tools/plot_batches/script/plot_encrypted_batches.py::plot_batch_bar）
    (b) 带宽 CDF 曲线（无面积填充）      —— 客户端上/下行带宽累积分布
        （源：tools/plot_bandwidth/plot_bandwidth_area.py::plot_cdf_gradient）

设计要点
    • 两个子图等宽等高（gridspec width_ratios=[1, 1]）；
    • (a)/(b) 标号居中置于子图上方，子图下方不加说明文字（说明交给 Fig.5 caption）；
    • 字号按"正文一致"标定：图宽 = \\textwidth（默认 7.2 in），
      因此 axis label = 10 pt、刻度 = 9 pt、图例 = 9 pt，
      以 width=\\linewidth 插入时与原文字号 1:1 对应；
    • 内置 7 套配色：1 套原图基准 + 3 套亮色 + 3 套暗色。

配色一览
    nature_forest   原图基准（Nature 四色 + Forest 绿/棕，均已加深）
    ---- 亮色 Light ----
    coral_teal      珊瑚橙 + 湖蓝 + 青绿 + 雾蓝（暖冷均衡）
    lilac_sky       淡紫 + 天蓝 + 薄荷 + 蓝紫（冷调柔和）
    amber_olive     琥珀黄 + 油橄榄 + 青碧 + 陶土（暖调）
    ---- 暗色 Dark ----
    navy_brick      深砖红 + 深海军蓝 + 墨绿 + 藏青（NPG 暗色）
    graphite_rose   石墨灰 + 玫红 + 钢青 + 紫灰
    forest_umber    深林绿 + 赭石棕 + 深青 + 暗紫

用法
    python AAAAA_Rework/vis/plot_fig5_dataset_batches_bandwidth.py --theme all
    python AAAAA_Rework/vis/plot_fig5_dataset_batches_bandwidth.py --theme coral_teal
    python AAAAA_Rework/vis/plot_fig5_dataset_batches_bandwidth.py --theme all --font-scale 1.15
    python AAAAA_Rework/vis/plot_fig5_dataset_batches_bandwidth.py --list-themes
"""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

VIS_DIR = SCRIPT_DIR
PALETTE_DIR = VIS_DIR / "palettes"
PKL_PATH = PROJECT_ROOT / "fedfetch_bandwidth.pkl"

# ---------------------------------------------------------------------------
# 样式：scienceplots 若可用则沿用原脚本风格（serif，与正文一致）
# ---------------------------------------------------------------------------
try:
    import scienceplots  # noqa: F401

    _STYLE: List[str] = ["science", "no-latex"]
except ImportError:  # pragma: no cover
    _STYLE = []

# ---------------------------------------------------------------------------
# 字体：全图 Times 风格（与 Times 正文 / elsarticle 默认字体一致）
#   • 正文、刻度、图例、标注统一走 serif 链，首选 Times New Roman
#   • 数学文本（对数刻度的 10^{-2}）用 STIX，字形与 Times 同族
#   • pdf.fonttype=42：TrueType 内嵌，Elsevier/IEEE 投稿可编辑文本
# ---------------------------------------------------------------------------
FONT_FAMILY = "Times New Roman"
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
    "svg.fonttype": "none",
}

# ---------------------------------------------------------------------------
# 字号：默认按 \textwidth = 7.2 in 标定，插入论文后与 10 pt 正文 1:1 一致
# ---------------------------------------------------------------------------
FS_AXIS_LABEL = 10.0
FS_TICK = 9.0
FS_LEGEND = 9.0
FS_ANNOT = 9.0
FS_PANEL_TAG = 10.0
FS_STATS = 8.0

# 全局字重：'normal' 或 'bold'。Times New Roman 自带 Bold 字形，
# 因此 'bold' 走的是真 Times Bold，而非描边伪粗体。
FONT_WEIGHT = "bold"

LW_SPINE = 0.8
LW_CURVE = 1.3
LW_MARKER_EDGE = 0.6
MARKER_SIZE = 26

FIG_W = 7.2
FIG_H = 3.05

KBPS_TO_MBPS = 1.0 / 1000.0

# ---------------------------------------------------------------------------
# 配色主题
#   group     : 分组（用于总览图排序）
#   bars      : (a) 4 个数据集的柱色
#   upload    : (b) 上行 (fill, line)
#   download  : (b) 下行 (fill, line)
#   fill_alpha: (b) 填充透明度，亮色略高、暗色略低以保持均衡
# ---------------------------------------------------------------------------
THEMES: Dict[str, Dict] = {
    # ============ 期刊标准配色（建议优先挑这里） ============
    "npg": {
        "group": "Journal standard",
        "label": "NPG — Nature Publishing Group",
        "bars": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488"],
        "upload": ("#00A087", "#00786A"),
        "download": ("#E64B35", "#B8382A"),
        "fill_alpha": 0.45,
    },
    "aaas": {
        "group": "Journal standard",
        "label": "AAAS — Science",
        "bars": ["#3B4992", "#EE0000", "#008B45", "#631879"],
        "upload": ("#008B45", "#005F2F"),
        "download": ("#3B4992", "#232D63"),
        "fill_alpha": 0.45,
    },
    "lancet": {
        "group": "Journal standard",
        "label": "Lancet",
        "bars": ["#00468B", "#ED0000", "#42B540", "#0099B4"],
        "upload": ("#0099B4", "#006D82"),
        "download": ("#ED0000", "#B00000"),
        "fill_alpha": 0.45,
    },
    "nejm": {
        "group": "Journal standard",
        "label": "NEJM",
        "bars": ["#BC3C29", "#0072B5", "#E18727", "#20854E"],
        "upload": ("#20854E", "#145737"),
        "download": ("#BC3C29", "#8A2B1D"),
        "fill_alpha": 0.45,
    },
    "okabe_ito": {
        "group": "Journal standard",
        "label": "Okabe-Ito — colour-blind safe",
        "bars": ["#E69F00", "#56B4E9", "#009E73", "#0072B2"],
        "upload": ("#56B4E9", "#2F7FAE"),
        "download": ("#E69F00", "#B87B00"),
        "fill_alpha": 0.50,
    },
    # ============ 原图基准 ============
    "nature_forest": {
        "group": "Baseline",
        "label": "Original — Nature + Forest (darkened)",
        "bars": ["#A63626", "#378799", "#007361", "#2B3C62"],
        "upload": ("#1E884B", "#176739"),
        "download": ("#6E564D", "#49322B"),
        "fill_alpha": 0.42,
    },
    # ============ 亮色 ============
    "coral_teal": {
        "group": "Light",
        "label": "Light — Coral / Teal / Mist Blue",
        "bars": ["#F2836B", "#57C4D8", "#4DBFA2", "#7C97CE"],
        "upload": ("#4DBFA2", "#2E8F76"),
        "download": ("#F2836B", "#C25A44"),
        "fill_alpha": 0.55,
    },
    "lilac_sky": {
        "group": "Light",
        "label": "Light — Lilac / Sky / Mint",
        "bars": ["#B490CA", "#79B8E8", "#8FD3C5", "#7E93C9"],
        "upload": ("#79B8E8", "#4A87BD"),
        "download": ("#B490CA", "#8560A8"),
        "fill_alpha": 0.55,
    },
    "amber_olive": {
        "group": "Light",
        "label": "Light — Amber / Olive / Terracotta",
        "bars": ["#F0B357", "#8FBF5F", "#5FBFB0", "#D98A6A"],
        "upload": ("#8FBF5F", "#5E8A34"),
        "download": ("#F0B357", "#C08A2E"),
        "fill_alpha": 0.55,
    },
    # ============ 暗色 ============
    "navy_brick": {
        "group": "Dark",
        "label": "Dark — Brick Red / Navy / Ink Green",
        "bars": ["#8C2F26", "#1F6F82", "#0F5F52", "#2A3D66"],
        "upload": ("#0F5F52", "#0A4038"),
        "download": ("#8C2F26", "#5E1D18"),
        "fill_alpha": 0.40,
    },
    "graphite_rose": {
        "group": "Dark",
        "label": "Dark — Graphite / Rose / Steel Blue",
        "bars": ["#3E3E4E", "#A64B5A", "#4B6C8A", "#6B5B7B"],
        "upload": ("#4B6C8A", "#2C465C"),
        "download": ("#A64B5A", "#722E3A"),
        "fill_alpha": 0.40,
    },
    "forest_umber": {
        "group": "Dark",
        "label": "Dark — Forest Green / Umber / Deep Teal",
        "bars": ["#1B5E3A", "#7A5230", "#2E6B70", "#4A3B52"],
        "upload": ("#1B5E3A", "#0F3A24"),
        "download": ("#7A5230", "#4E3319"),
        "fill_alpha": 0.40,
    },
    # ============ 低饱和 / 莫兰迪 ============
    "morandi": {
        "group": "Muted",
        "label": "Muted — Morandi grey-green / clay",
        "bars": ["#8FA69B", "#C2A08E", "#93A7BC", "#B5A0A8"],
        "upload": ("#8FA69B", "#66806F"),
        "download": ("#C2A08E", "#9A7565"),
        "fill_alpha": 0.55,
    },
    "dusty": {
        "group": "Muted",
        "label": "Muted — Dusty blue / brick / sage",
        "bars": ["#7D94A6", "#B0766B", "#96A87F", "#6E7A93"],
        "upload": ("#96A87F", "#6B7D57"),
        "download": ("#B0766B", "#875448"),
        "fill_alpha": 0.50,
    },
    # ============ 单色阶（最保守，黑白印刷也安全） ============
    "mono_blue": {
        "group": "Mono",
        "label": "Mono — Blue ramp",
        "bars": ["#0B2545", "#134074", "#3A6EA5", "#8AB0D0"],
        "upload": ("#134074", "#0B2545"),
        "download": ("#8AB0D0", "#5C86AC"),
        "fill_alpha": 0.50,
    },
    "mono_teal": {
        "group": "Mono",
        "label": "Mono — Teal ramp",
        "bars": ["#0B3D3B", "#16645F", "#35918A", "#8AC4BC"],
        "upload": ("#16645F", "#0B3D3B"),
        "download": ("#8AC4BC", "#5A9C93"),
        "fill_alpha": 0.50,
    },
    # ============ 高对比现代 ============
    "vivid_royal": {
        "group": "Vivid",
        "label": "Vivid — Royal blue / crimson / emerald",
        "bars": ["#2E3A8C", "#D7263D", "#1B998B", "#F4A259"],
        "upload": ("#1B998B", "#12695F"),
        "download": ("#D7263D", "#9A1829"),
        "fill_alpha": 0.45,
    },
    "teal_amber": {
        "group": "Vivid",
        "label": "Vivid — Deep teal / amber / slate",
        "bars": ["#0E6E6E", "#E0A33E", "#2F4858", "#C4643B"],
        "upload": ("#0E6E6E", "#084A4A"),
        "download": ("#E0A33E", "#A6742A"),
        "fill_alpha": 0.45,
    },
}

GROUP_ORDER = ["Journal standard", "Baseline", "Light", "Dark",
               "Muted", "Mono", "Vivid"]

# ---------------------------------------------------------------------------
# 数据 (a)：模型 batch 划分
#   与原脚本完全一致：单密文 = n·⌈log Q⌉ / 8 字节，n = 4096
# ---------------------------------------------------------------------------
MODELS_META = [
    {"dataset": "MNIST", "model": "LeNet", "params": 44426, "batches": 11},
    {"dataset": "FMNIST", "model": "CNN", "params": 39786, "batches": 10},
    {"dataset": "CIFAR-10", "model": "ResNet-20", "params": 272186, "batches": 67},
    {"dataset": "SVHN", "model": "ResNet-32", "params": 460618, "batches": 113},
]

SLOT_N = 4096


def per_batch_mb() -> Tuple[float, int]:
    """单密文 MB 与 log Q 位数（复用 ckks_fed.eshe.RingContext 的模数口径）。"""
    try:
        from ckks_fed.eshe import RingContext

        ring = RingContext(SLOT_N)
        q_bits = ring.Q.bit_length()
    except Exception:  # 兜底：n=4096 时 q1/q2 = 31/30 bit → log Q = 61
        q_bits = 61
    n_bytes = SLOT_N * q_bits // 8
    return n_bytes / (1024 * 1024), q_bits


# ---------------------------------------------------------------------------
# 数据 (b)：FedFetch 真实带宽 trace
# ---------------------------------------------------------------------------
def load_bandwidth(pkl_path: Path = PKL_PATH) -> Tuple[np.ndarray, np.ndarray]:
    with open(pkl_path, "rb") as f:
        raw = pickle.load(f)
    ul = np.array([float(v["ul_kbps"]) * KBPS_TO_MBPS for v in raw.values()])
    dl = np.array([float(v["dl_kbps"]) * KBPS_TO_MBPS for v in raw.values()])
    return ul, dl


def darken(hex_color: str, factor: float) -> str:
    """把十六进制颜色按比例压暗（factor < 1 表示加深）。"""
    r, g, b = mcolors.to_rgb(hex_color)
    return mcolors.to_hex((r * factor, g * factor, b * factor))


# ---------------------------------------------------------------------------
# 子图 (a)：竖向分组柱状图 —— Pack Count（左轴）+ Ciphertext（右轴，MB，2^20 口径）
#   ciphertext = batches × per-batch size，右轴范围取左轴 × per_mb 后，
#   每组两根柱严格等高，正好体现"包数 ↔ 密文体积"的一一对应。
# ---------------------------------------------------------------------------
def draw_panel_a(ax, per_mb: float, theme: Dict, fs: float = 1.0) -> None:
    colors = theme["bars"]
    c_batch, c_cipher = colors[3], colors[2]

    n = len(MODELS_META)
    x = np.arange(n)
    bar_w = 0.30
    x_off = 0.17                      # 两根柱的中心距 0.34，中间留一道细缝
    batches = [m["batches"] for m in MODELS_META]
    sizes_mib = [m["batches"] * per_mb for m in MODELS_META]  # per_mb 实为 MiB

    y_max = 130.0                                   # 左轴：Number of Packs
    ax.bar(x - x_off, batches, bar_w, color=c_batch,
           edgecolor="#333333", linewidth=0.5, zorder=3,
           label=r"Pack Count ($J$)")
    ax.set_ylabel(r"Number of packs ($J$)", fontsize=FS_AXIS_LABEL * fs)
    ax.set_ylim(0, y_max)
    ax.set_yticks(np.arange(0, y_max + 1e-9, 20))

    # 右轴与左轴共享柱高比例：ciphertext(MiB) = batches × per_mb
    ax2 = ax.twinx()
    ax2.bar(x + x_off, sizes_mib, bar_w, color=c_cipher,
            edgecolor="#333333", linewidth=0.5, zorder=3,
            label="Ciphertext (MB)")
    ax2.set_ylabel("Encrypted Size (MB)", fontsize=FS_AXIS_LABEL * fs)
    y2_max = y_max * per_mb
    ax2.set_ylim(0, y2_max)
    y2_step = 0.5
    ax2.set_yticks(np.arange(0, y2_max + 1e-9, y2_step))

    # 柱顶标数值（与 backup 水平条形图的标注一致：包数 + MiB），各自居中于本柱
    for xi, b in zip(x - x_off, batches):
        ax.text(xi, b + y_max * 0.018, f"{b:d}", ha="center", va="bottom",
                fontsize=(FS_ANNOT - 1.0) * fs, fontweight="bold",
                color="#111111", zorder=6)
    for xi, s in zip(x + x_off, sizes_mib):
        ax2.text(xi, s + y2_max * 0.018, f"{s:.2f}", ha="center", va="bottom",
                 fontsize=(FS_ANNOT - 1.0) * fs, fontweight="bold",
                 color="#111111", zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{m['dataset']}\n({m['model']})" for m in MODELS_META],
                       fontsize=FS_TICK * fs, linespacing=1.15)
    ax.tick_params(axis="both", labelsize=FS_TICK * fs, width=LW_SPINE, length=3)
    ax2.tick_params(axis="y", labelsize=FS_TICK * fs, width=LW_SPINE, length=3)
    ax.grid(False)
    ax2.grid(False)

    for spine in ax.spines.values():
        spine.set_linewidth(LW_SPINE)
    for spine in ax2.spines.values():
        spine.set_linewidth(LW_SPINE)

    # 图例：两根柱各取一色，放在左上（MNIST/FMNIST 柱矮，左上是空白区）
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=c_batch, edgecolor="#333333",
                      linewidth=0.5),
        plt.Rectangle((0, 0), 1, 1, facecolor=c_cipher, edgecolor="#333333",
                      linewidth=0.5),
    ]
    leg = ax.legend(handles, [r"Pack Count ($J$)", "Ciphertext (MB)"],
                    loc="upper left", fontsize=FS_LEGEND * fs,
                    frameon=True, fancybox=False, framealpha=0.95,
                    edgecolor="#888888", facecolor="white",
                    borderpad=0.30, labelspacing=0.30,
                    handlelength=1.15, handletextpad=0.50,
                    borderaxespad=0.35)
    leg.get_frame().set_linewidth(0.7)


# ---------------------------------------------------------------------------
# 子图 (b)：CDF 曲线（无面积填充），图例自带中位数
# ---------------------------------------------------------------------------
def draw_panel_b(ax, ul: np.ndarray, dl: np.ndarray, theme: Dict, fs: float = 1.0,
                 mode: str = "plain") -> None:
    """mode: plain=纯曲线 | median=曲线+中位点 | area=中位点+曲线下面积填充"""
    c_dl = theme["bars"][3]     # 下行：主题第 4 色（深色，实线）
    c_ul = theme["bars"][0]     # 上行：主题第 1 色（亮色，虚线）

    configs = [
        (dl, c_dl, "-", f"Download (Med: {np.median(dl):.1f} Mbps)",
         theme["download"][0]),
        (ul, c_ul, (0, (5, 2.5)), f"Upload (Med: {np.median(ul):.1f} Mbps)",
         theme["upload"][0]),
    ]
    for arr, color, ls, label, fill_color in configs:
        s = np.sort(arr)
        cdf = np.arange(1, len(s) + 1) / len(s)
        if mode == "area":
            ax.fill_between(s, 0, cdf, color=fill_color,
                            alpha=theme["fill_alpha"], linewidth=0, zorder=2)
        ax.plot(s, cdf, color=color, linestyle=ls, linewidth=LW_CURVE + 0.3,
                label=label, zorder=3)

    # 中位点：虚线导引 + 圆点 + 数值标注，落在 CDF=0.5 处
    if mode in ("median", "area"):
        for arr, color, side in ((dl, c_dl, "right"), (ul, c_ul, "left")):
            med = float(np.median(arr))
            ax.plot([med, med], [0.0, 0.5], color=color, linestyle=":",
                    linewidth=0.7, alpha=0.6, zorder=4)
            ax.scatter([med], [0.5], s=MARKER_SIZE * 1.1, color=color,
                       edgecolors="white", linewidths=LW_MARKER_EDGE, zorder=6)
            # 数值标在点旁：Download（右侧点）向右伸、Upload（左侧点）向左伸
            ha = "left" if side == "right" else "right"
            dx = 6 if side == "right" else -6
            ax.annotate(f"{med:.1f} Mbps", xy=(med, 0.5),
                        xytext=(dx, 7), textcoords="offset points",
                        fontsize=FS_STATS * fs, color=color, ha=ha,
                        va="bottom", fontweight="bold", zorder=7,
                        bbox=dict(boxstyle="round,pad=0.14", facecolor="white",
                                  edgecolor="none", alpha=0.85))

    ax.set_xscale("log")
    ax.set_xlabel("Client Bandwidth (Mbps)", fontsize=FS_AXIS_LABEL * fs)
    ax.set_ylabel("Cumulative Distribution", fontsize=FS_AXIS_LABEL * fs)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlim(left=min(ul.min(), dl.min()) * 0.8,
                right=max(ul.max(), dl.max()) * 1.25)
    ax.yaxis.set_major_locator(plt.MultipleLocator(0.2))
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.tick_params(axis="both", labelsize=FS_TICK * fs, width=LW_SPINE, length=3)
    ax.grid(False)

    for spine in ax.spines.values():
        spine.set_linewidth(LW_SPINE)

    leg = ax.legend(loc="upper left", fontsize=(FS_LEGEND - 0.6) * fs,
                    frameon=True, fancybox=False, framealpha=0.95,
                    edgecolor="#888888", facecolor="white",
                    borderpad=0.30, labelspacing=0.28,
                    handlelength=1.55, handletextpad=0.45,
                    borderaxespad=0.35)
    leg.get_frame().set_linewidth(0.7)


# ---------------------------------------------------------------------------
# 字体解析报告
# ---------------------------------------------------------------------------
def report_font() -> None:
    """打印实际命中的 Times 系列字体文件，便于确认没有静默回退。"""
    from matplotlib import font_manager

    for name in FONT_FALLBACKS:
        try:
            path = font_manager.findfont(
                font_manager.FontProperties(family=name), fallback_to_default=False)
        except Exception:
            continue
        print(f"[FONT]  {name}  ->  {path}")
        return
    print("[FONT]  ! 未找到 Times 系列字体，已回退到 matplotlib 默认 serif")


# ---------------------------------------------------------------------------
# 样式应用
#   必须全局生效：Text 只保存 family="serif"，真正的 serif 候选表在 draw 时
#   从 rcParams 解析。若用 plt.style.context()，退出后 rcParams 复位，
#   随后 savefig 会退回 DejaVu Serif。
# ---------------------------------------------------------------------------
def apply_style(font_weight: str = FONT_WEIGHT) -> None:
    plt.rcdefaults()
    if _STYLE:
        plt.style.use(_STYLE)
    plt.rcParams.update(FONT_RC)
    # scienceplots 会重置 font.*，字重同样要在 style 生效后再覆盖
    plt.rcParams["font.weight"] = font_weight


# ---------------------------------------------------------------------------
# 主图
# ---------------------------------------------------------------------------
def build_figure(
    theme_name: str = "nature_forest",
    figsize: Tuple[float, float] = (FIG_W, FIG_H),
    font_scale: float = 1.0,
    font_weight: str = FONT_WEIGHT,
    panel_b_mode: str = "plain",
):
    if theme_name not in THEMES:
        raise KeyError(f"未知配色：{theme_name}（可选：{', '.join(THEMES)}）")
    theme = THEMES[theme_name]

    per_mb, q_bits = per_batch_mb()
    ul, dl = load_bandwidth()

    print(f"[THEME] {theme_name}  —  {theme['label']}")
    print(f"[DATA]  per-batch ciphertext = {per_mb:.4f} MB (n={SLOT_N}, logQ={q_bits})")
    print(f"[DATA]  clients={len(ul)}  upload P50={np.median(ul):.2f} Mbps  "
          f"download P50={np.median(dl):.2f} Mbps")

    apply_style(font_weight)
    fig = plt.figure(figsize=figsize)
    # 左右等宽 ⇒ 两个子图严格等大
    gs = fig.add_gridspec(
        1, 2, width_ratios=[1.0, 1.0], wspace=0.42,
        left=0.085, right=0.985, bottom=0.155, top=0.885,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])

    draw_panel_a(ax_a, per_mb, theme, font_scale)
    draw_panel_b(ax_b, ul, dl, theme, font_scale, mode=panel_b_mode)

    # (a)/(b) 标号：居中置于各自子图上方，不加子图说明文字
    for ax, tag in ((ax_a, "(a)"), (ax_b, "(b)")):
        ax.set_title(tag, fontsize=FS_PANEL_TAG * font_scale,
                     fontweight="bold", pad=4)

    return fig


def build_overview(out_root: Path) -> None:
    """色板总览：一屏看完所有配色的柱色 + 曲线色，便于快速挑选。"""
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
    fig, ax = plt.subplots(figsize=(7.2, 0.225 * n + 0.30))
    ax.set_xlim(0, 1)
    ax.set_ylim(n, 0)
    ax.axis("off")

    x_chip0, w_chip, gap = 0.440, 0.042, 0.008
    x_up, x_dl, w_pair = 0.660, 0.790, 0.088
    h, top = 0.60, 0.20

    for i, (kind, key) in enumerate(rows):
        cy = i + 0.5
        if kind == "cols":
            ax.text(0.010, cy, "palette", fontsize=7, va="center", color="#444444")
            ax.text(x_chip0, cy, "bars in (a)", fontsize=7, va="center", color="#444444")
            ax.text(x_up, cy, "upload", fontsize=7, va="center", color="#444444")
            ax.text(x_dl, cy, "download", fontsize=7, va="center", color="#444444")
            continue

        if kind == "header":
            ax.text(0.005, cy, f"— {key} —", fontsize=7.5, va="center",
                    fontweight="bold", color="#111111")
            continue

        th = THEMES[key]
        ax.text(0.010, cy, f"{key}", fontsize=7, va="center", color="black")
        ax.text(0.135, cy, th["label"], fontsize=6.2, va="center", color="#555555")

        for j, c in enumerate(th["bars"]):
            ax.add_patch(Rectangle((x_chip0 + j * (w_chip + gap), i + top), w_chip, h,
                                   facecolor=c, edgecolor="none"))

        for x, pair in ((x_up, th["upload"]), (x_dl, th["download"])):
            fill, line = pair
            ax.add_patch(Rectangle((x, i + top), w_pair, h, facecolor=fill,
                                   alpha=th["fill_alpha"], edgecolor="none"))
            ax.plot([x, x + w_pair], [i + top, i + top], color=line, lw=1.8,
                    solid_capstyle="butt")
            ax.plot([x, x + w_pair], [i + top + h, i + top + h], color=line, lw=0.8)

    out_root.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        p = out_root / f"_overview.{ext}"
        fig.savefig(p, dpi=400, bbox_inches="tight", facecolor="white")
        print(f"[SAVE]  {p}")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fig. 5 — 数据集 batch 划分 + 带宽 CDF 合并图（多配色）")
    parser.add_argument("--theme", type=str, default="all",
                        help=f"配色名，或 'all'（可选：{', '.join(THEMES)}）")
    parser.add_argument("--out-dir", type=str, default=str(PALETTE_DIR),
                        help=f"输出根目录（默认 {PALETTE_DIR}）")
    parser.add_argument("--name", type=str, default=None,
                        help="输出文件名（不含扩展名；默认 fig5_<theme>）")
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--font-scale", type=float, default=1.0,
                        help="正文字号倍数，1.0 = 与 10 pt 正文 1:1")
    parser.add_argument("--width-in", type=float, default=FIG_W,
                        help=f"图宽英寸（默认 {FIG_W} = \\textwidth）")
    parser.add_argument("--font", type=str, default=FONT_FAMILY,
                        help=f"首选字体（默认 {FONT_FAMILY}）")
    parser.add_argument("--font-weight", type=str, default=FONT_WEIGHT,
                        choices=["normal", "bold"],
                        help="全局字重（默认 bold，调用 Times Bold 字形）")
    parser.add_argument("--panel-b", type=str, default="plain",
                        choices=["plain", "median", "area"],
                        help="(b) 面板样式：plain=纯曲线；median=曲线+中位点；"
                             "area=中位点+面积填充")
    parser.add_argument("--list-themes", action="store_true")
    parser.add_argument("--no-overview", dest="overview", action="store_false",
                        help="不生成 _overview 色板总览图")
    args = parser.parse_args()

    # 允许用户指定其它 Times 变体（如 Nimbus Roman）
    if args.font != FONT_FAMILY:
        FONT_FALLBACKS.insert(0, args.font)
        FONT_RC["font.serif"] = FONT_FALLBACKS

    if args.list_themes:
        for g in GROUP_ORDER:
            keys = [k for k, v in THEMES.items() if v.get("group") == g]
            if keys:
                print(f"\n[{g}]")
            for k in keys:
                print(f"  {k:<16s} {THEMES[k]['label']}")
        return

    names = list(THEMES) if args.theme == "all" else [args.theme]
    out_root = Path(args.out_dir)
    height = args.width_in * FIG_H / FIG_W

    report_font()

    if args.overview and len(names) > 1:
        build_overview(out_root)

    for name in names:
        fig = build_figure(name, figsize=(args.width_in, height),
                           font_scale=args.font_scale,
                           font_weight=args.font_weight,
                           panel_b_mode=args.panel_b)
        # 单主题 → 直接放 out-dir；多主题 → 每套配色一个子目录
        sub = out_root if len(names) == 1 else out_root / name
        sub.mkdir(parents=True, exist_ok=True)
        base = args.name or (f"fig5_{name}" if len(names) > 1 else "fig5")
        for ext in ("png", "pdf"):
            path = sub / f"{base}.{ext}"
            fig.savefig(path, dpi=args.dpi, bbox_inches="tight", facecolor="white")
            print(f"[SAVE]  {path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
