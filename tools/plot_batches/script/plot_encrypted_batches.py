"""
加密 Batch 大小可视化工具集 (v2 — 优雅重设计)
================================================

三种图表类型 × 多种 SCI 配色方案

图表类型:
    batch_bar       水平条形图 + batch 分隔线：纯色 SCI 配色，白色细线标注 batch 边界
    scaling         参数-通信量散点图：展示线性缩放关系，点大小 ∝ batch 数
    step_cumulative 阶梯累积曲线：离散 batch 增长的阶梯面积图

配色方案:
    nature    Nature 期刊配色 (NPG)
    lancet    Lancet 期刊配色
    jama      JAMA 期刊配色
    nejm      NEJM 期刊配色
    science   Science 期刊配色
    all       生成所有配色方案

用法:
    python tools/plot_batches/script/plot_encrypted_batches.py --type all --palette all
    python tools/plot_batches/script/plot_encrypted_batches.py --type batch_bar --palette nature
    python tools/plot_batches/script/plot_encrypted_batches.py --type batch_bar,scaling,step_cumulative --palette lancet
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.plotter import Plotter

# ---------------------------------------------------------------------------
# 输出目录
# ---------------------------------------------------------------------------
PIC_DIR = PROJECT_ROOT / "tools" / "plot_batches" / "pic"

# ---------------------------------------------------------------------------
# 模型数据
# ---------------------------------------------------------------------------
MODELS = [
    {
        "dataset": "MNIST",
        "model": "LeNet",
        "params": 44426,
        "batches": 11,
    },
    {
        "dataset": "FMNIST",
        "model": "CNN",
        "params": 39786,
        "batches": 10,
    },
    {
        "dataset": "CIFAR-10",
        "model": "ResNet-20",
        "params": 272186,
        "batches": 67,
    },
    {
        "dataset": "SVHN",
        "model": "ResNet-32",
        "params": 460618,
        "batches": 114,
    },
]

# 统一 per-batch ciphertext 大小（0.319 MB = 334,289 bytes / 1024^2）
PER_BATCH_MB = 0.319

for m in MODELS:
    m["total_mb"] = m["batches"] * PER_BATCH_MB
    m["per_batch_mb"] = PER_BATCH_MB

ALL_TYPES = ["batch_bar", "scaling", "step_cumulative"]

# ---------------------------------------------------------------------------
# SCI 配色方案
# ---------------------------------------------------------------------------
SCI_PALETTES: Dict[str, Dict] = {
    "nature": {
        "colors": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488"],
        "label": "Nature (NPG)",
    },
    "lancet": {
        "colors": ["#00468B", "#ED0000", "#42B540", "#0099B4"],
        "label": "Lancet",
    },
    "jama": {
        "colors": ["#374E55", "#DF8F44", "#00A1D5", "#B24745"],
        "label": "JAMA",
    },
    "nejm": {
        "colors": ["#BC3C29", "#0072B5", "#E18727", "#20854E"],
        "label": "NEJM",
    },
    "science": {
        "colors": ["#0C5DA5", "#00B945", "#FF9500", "#FF2C00"],
        "label": "Science",
    },
}


# ===================================================================
#  1. 水平条形图 + batch 分隔线
# ===================================================================

def plot_batch_bar(p, palette_name: str):
    """
    水平条形图 — 纯色 SCI 配色，白色细线标注每个 batch 边界。
    右侧标注总 MB 和 batch 数，左侧 y 轴标签三行显示。
    """
    pal = SCI_PALETTES[palette_name]
    colors = pal["colors"]
    n_models = len(MODELS)

    with plt.style.context(p.style):
        # 与 bandwidth_cdf_gradient_contrast 保持一致 (6, 4)
        fig, ax = plt.subplots(figsize=(6.0, 4.0))

        bar_height = 0.5
        y_positions = np.arange(n_models)[::-1]  # 从上到下: MNIST → SVHN
        xlim_max = max(m["total_mb"] for m in MODELS) * 1.45

        for i, (model, y_pos) in enumerate(zip(MODELS, y_positions)):
            n_batches = model["batches"]
            per_batch = model["per_batch_mb"]
            total = model["total_mb"]
            color = colors[i]

            # 纯色填充条 + 白色带状 hatch 纹理
            ax.barh(y_pos, total, height=bar_height, color=color, alpha=0.85,
                    edgecolor=color, linewidth=0.5, hatch="|||", zorder=3)

            # 标签文字统一放在条形右侧，分两行：总大小 + batch 数
            label_text = f"{total:.2f} MB\n({n_batches} batches)"
            ax.text(total + 0.3, y_pos,
                    label_text,
                    va="center", ha="left", fontsize=13, fontweight="bold",
                    color="black", zorder=5)

        # Y 轴标签：三行显示
        y_labels = [f"{m['dataset']}\n{m['model']}\n({m['params']:,})" for m in MODELS]
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels, fontsize=16, linespacing=1.15)

        ax.set_xlabel("Encrypted Size (MB)", fontsize=20)
        ax.set_xlim(0, xlim_max)
        ax.tick_params(axis="both", labelsize=16)

        ax.grid(True, linestyle="--", alpha=0.3, which="major", axis="x")
        ax.grid(False, which="minor")
        ax.grid(False, axis="y")

        for spine in ax.spines.values():
            spine.set_linewidth(1.5)

        # 右上方图例式标注：per-batch ciphertext
        per_batch_val = MODELS[0]["per_batch_mb"]
        legend_text = f"Per-batch ciphertext:\n{per_batch_val:.3f} MB (4096 slots)"
        ax.text(0.98, 0.98,
                legend_text,
                transform=ax.transAxes, fontsize=14, va="top", ha="right",
                color="#333333",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor="#CCCCCC", alpha=0.95, linewidth=1))

        fig.tight_layout()
        p._save(f"encrypted_batch_bar_{palette_name}", formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  2. 参数-通信量散点图（线性缩放关系）
# ===================================================================

def plot_scaling(p, palette_name: str):
    """
    散点图 — 横轴为模型参数量，纵轴为总加密通信量。
    点大小 ∝ batch 数量，虚线为过原点线性拟合，展示完美线性缩放。
    """
    pal = SCI_PALETTES[palette_name]
    colors = pal["colors"]

    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(8, 5))

    # 每个模型一个散点
    for i, model in enumerate(MODELS):
        color = colors[i]
        n_batches = model["batches"]

        ax.scatter(model["params"], model["total_mb"],
                   s=n_batches * 10, color=color, alpha=0.85,
                   edgecolors="white", linewidth=1.5, zorder=5)

        # 智能偏移避免重叠
        offsets = [(15, 12), (15, -18), (12, 10), (-15, -15)]
        ox, oy = offsets[i]
        ha = "left" if ox > 0 else "right"
        ax.annotate(
            f"{model['dataset']}\n{model['model']}\n({n_batches} batches)",
            xy=(model["params"], model["total_mb"]),
            xytext=(ox, oy), textcoords="offset points",
            fontsize=11, color=color, fontweight="bold",
            va="center", ha=ha,
            zorder=6,
        )

    # 过原点线性拟合: total = k * params
    params_arr = np.array([m["params"] for m in MODELS])
    totals_arr = np.array([m["total_mb"] for m in MODELS])
    k = np.sum(params_arr * totals_arr) / np.sum(params_arr ** 2)
    r_squared = np.corrcoef(params_arr, totals_arr)[0, 1] ** 2

    x_fit = np.linspace(0, max(params_arr) * 1.12, 100)
    ax.plot(x_fit, k * x_fit, "--", color="gray", linewidth=1.2, alpha=0.5,
            label=f"Linear fit  ($R^2$={r_squared:.4f})", zorder=2)

    ax.set_xlabel("Model Parameters", fontsize=18)
    ax.set_ylabel("Total Encrypted Size (MB)", fontsize=18)
    ax.set_xlim(-max(params_arr) * 0.05, max(params_arr) * 1.12)
    ax.set_ylim(-max(totals_arr) * 0.05, max(totals_arr) * 1.12)
    ax.tick_params(axis="both", labelsize=14)

    # X 轴科学计数法
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))

    ax.grid(True, linestyle="--", alpha=0.3, which="major")
    ax.grid(False, which="minor")

    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    ax.legend(loc="upper left", fontsize=13, frameon=True, fancybox=True,
              framealpha=0.85, edgecolor="gray", facecolor="white")

    # 右下角 per-batch 标注
    ax.text(0.98, 0.03,
            f"Per-batch (SIMD): {MODELS[0]['per_batch_mb']:.3f} MB",
            transform=ax.transAxes, fontsize=11, va="bottom", ha="right",
            color="gray", style="italic")

    fig.tight_layout()
    p._save(f"encrypted_scaling_{palette_name}", formats=["png", "pdf"])
    plt.close(fig)


# ===================================================================
#  3. 阶梯累积曲线
# ===================================================================

def plot_step_cumulative(p, palette_name: str):
    """
    阶梯累积曲线 — 离散 batch 增长的阶梯面积图。
    每个 batch 对应一个阶梯，展示加密通信量的离散累积过程。
    """
    pal = SCI_PALETTES[palette_name]
    colors = pal["colors"]

    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(8, 5))

    max_batches = max(m["batches"] for m in MODELS)

    for i, model in enumerate(MODELS):
        n = model["batches"]
        per_batch = model["per_batch_mb"]
        total = model["total_mb"]
        color = colors[i]

        # 阶梯数据
        x = np.arange(0, n + 1)
        y = x * per_batch

        # 阶梯线
        ax.step(x, y, where="post", color=color, linewidth=2.0,
                label=f"{model['dataset']} ({model['model']})", zorder=3)

        # 半透明填充
        ax.fill_between(x, 0, y, step="post", color=color, alpha=0.10, zorder=2)

        # 终点标记
        ax.scatter([n], [total], color=color, s=60, zorder=5,
                   edgecolors="white", linewidths=1.0)

        # 终点标注（靠近终点右侧，最后一个模型放左侧避免出界）
        if n >= max_batches - 15:
            ox, ha = -10, "right"
        else:
            ox, ha = 10, "left"
        ax.annotate(
            f"{total:.2f} MB",
            xy=(n, total),
            xytext=(ox, 0), textcoords="offset points",
            fontsize=12, color=color, fontweight="bold",
            va="center", ha=ha, zorder=6,
        )

    ax.set_xlabel("Batch Index", fontsize=18)
    ax.set_ylabel("Cumulative Encrypted Size (MB)", fontsize=18)
    ax.set_xlim(0, max_batches + 8)
    ax.set_ylim(0, max(m["total_mb"] for m in MODELS) * 1.12)
    ax.tick_params(axis="both", labelsize=14)

    ax.legend(loc="upper left", fontsize=13, frameon=True, fancybox=True,
              framealpha=0.85, edgecolor="gray", facecolor="white")

    ax.grid(True, linestyle="--", alpha=0.3, which="major")
    ax.grid(False, which="minor")

    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    # 右下角 per-batch 标注
    ax.text(0.98, 0.03,
            f"Per-batch (SIMD): {MODELS[0]['per_batch_mb']:.3f} MB",
            transform=ax.transAxes, fontsize=11, va="bottom", ha="right",
            color="gray", style="italic")

    fig.tight_layout()
    p._save(f"encrypted_step_cumulative_{palette_name}", formats=["png", "pdf"])
    plt.close(fig)


# ===================================================================
# 主入口
# ===================================================================

def generate_plots(
    types: Optional[List[str]] = None,
    palette_name: str = "nature",
    output_dir: Path = PIC_DIR,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if types is None or "all" in types:
        types = list(ALL_TYPES)

    if palette_name == "all":
        palettes = list(SCI_PALETTES.keys())
    else:
        palettes = [palette_name]

    # 打印数据摘要
    print(f"\n{'=' * 60}")
    print("[DATA] Model encrypted batch summary:")
    print(f"{'Model':<12} {'Dataset':<10} {'Params':>8} {'Batches':>8} {'Total MB':>10} {'Per-Batch':>10}")
    print(f"{'-' * 60}")
    for m in MODELS:
        print(f"{m['model']:<12} {m['dataset']:<10} {m['params']:>8,} {m['batches']:>8} {m['total_mb']:>10.2f} {m['per_batch_mb']:>10.4f}")
    print(f"{'=' * 60}")

    saved_all = []

    for pname in palettes:
        pal = SCI_PALETTES[pname]
        print(f"\n[PALETTE] {pal['label']}")

        if len(palettes) > 1:
            sub_dir = output_dir / f"palette_{pname}"
            sub_dir.mkdir(parents=True, exist_ok=True)
        else:
            sub_dir = output_dir

        p = Plotter(
            style=["science", "grid"],
            figsize=(8, 5),
            dpi=300,
            output_dir=sub_dir,
            use_latex=False,
            font_size=12,
            theme="contrast",
        )

        for plot_type in types:
            print(f"  [PLOT]  {plot_type:<20s}")
            try:
                if plot_type == "batch_bar":
                    plot_batch_bar(p, pname)
                elif plot_type == "scaling":
                    plot_scaling(p, pname)
                elif plot_type == "step_cumulative":
                    plot_step_cumulative(p, pname)
                else:
                    print(f"  [SKIP] unknown type: {plot_type}")
                    continue
                saved_all.append(plot_type)
            except Exception as e:
                print(f"  [ERROR] {plot_type}: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"[DONE] {len(saved_all)} chart sets generated")
    print(f"       Output: {output_dir}")
    print(f"{'=' * 60}")
    return saved_all


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Encrypted batch visualization — 3 chart types x SCI palettes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/plot_batches/script/plot_encrypted_batches.py --type all --palette all
  python tools/plot_batches/script/plot_encrypted_batches.py --type batch_bar --palette nature
  python tools/plot_batches/script/plot_encrypted_batches.py --type batch_bar,scaling,step_cumulative --palette lancet

Chart types: {types}
Palettes:    {palettes}
        """.format(
            types=", ".join(ALL_TYPES),
            palettes=", ".join(SCI_PALETTES.keys()),
        ),
    )
    parser.add_argument("--type", type=str, default="all",
                        help=f"chart types, comma-separated or 'all'")
    parser.add_argument("--palette", type=str, default="all",
                        help=f"palette name or 'all'")
    parser.add_argument("--output-dir", type=str, default=None,
                        help=f"output directory (default: {PIC_DIR})")
    args = parser.parse_args()

    types = [t.strip() for t in args.type.split(",")]
    output_dir = Path(args.output_dir) if args.output_dir else PIC_DIR

    generate_plots(
        types=types,
        palette_name=args.palette,
        output_dir=output_dir,
    )
