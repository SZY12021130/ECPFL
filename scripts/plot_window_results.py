#!/usr/bin/env python3
"""
预取窗口实验结果绘图脚本

读取 accuracy_window/fashion_mnist-cnn_fmnist/ 下的实验结果，绘制：
  1. 不同预取窗口 R 下的测试准确率曲线（x 轴为轮数）
  2. 总通信量随预取窗口 R 变化的柱状图

用法:
  python scripts/plot_window_results.py [--input-dir accuracy_window/fashion_mnist-cnn_fmnist]
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # 无头后端，必须在 pyplot 导入前设置

import matplotlib.pyplot as plt
import numpy as np

# 导入 Plotter
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.plotter import Plotter

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--input-dir", type=str, default="accuracy_window/fashion_mnist-cnn_fmnist",
                     help="实验结果根目录")
_parser.add_argument("--output-dir", type=str, default=None,
                     help="图表输出目录 (默认: {input-dir}/plots)")
_args = _parser.parse_args()

INPUT_DIR = Path(_args.input_dir)
OUTPUT_DIR = Path(_args.output_dir) if _args.output_dir else INPUT_DIR / "plots"

# 鲜艳配色 + 线型（与 accuracy/plot_paper_figures.py 保持一致）
_VIBRANT_COLORS = ["#E31A1C", "#1F78B4", "#33A02C", "#FF7F00", "#6A3D9A", "#08519C"]
_VIBRANT_LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]

# 初始化 Plotter（与 generate_analysis_and_plots.py / plot_paper_figures.py 保持一致）
plotter = Plotter(
    style=["science", "grid"],
    output_dir=OUTPUT_DIR,
    figsize=(6, 4),
    dpi=300,
    use_latex=False,
    font_size=16,
    theme="paper",
)

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def extract_window_from_dirname(dir_name: str) -> int:
    """从目录名中提取预取窗口 R 值"""
    if dir_name.startswith("experiment_R"):
        try:
            return int(dir_name.split("_R")[1])
        except (IndexError, ValueError):
            pass
    return None


def load_experiment(exp_dir: Path) -> Tuple[int, dict, dict]:
    """加载单个实验。返回: (window, metrics, config) 或 (None, None, None)"""
    metrics_path = exp_dir / "metrics.json"
    config_path = exp_dir / "config.yaml"

    if not metrics_path.exists():
        return None, None, None

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    config = {}
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    window = extract_window_from_dirname(exp_dir.name)
    if window is None and config:
        window = config.get("prefetch", {}).get("max_prefetch_round")

    return window, metrics, config


def scan_window_experiments() -> List[Tuple[int, dict, dict]]:
    """扫描预取窗口实验目录，返回按窗口排序的实验列表。"""
    exps = []
    if not INPUT_DIR.exists():
        print(f"Warning: {INPUT_DIR} does not exist")
        return exps

    for exp_dir in INPUT_DIR.iterdir():
        if not exp_dir.is_dir():
            continue
        window, metrics, config = load_experiment(exp_dir)
        if window is not None and metrics is not None:
            exps.append((window, metrics, config))

    exps.sort(key=lambda x: x[0])
    return exps


# ---------------------------------------------------------------------------
# 绘图函数
# ---------------------------------------------------------------------------

def _apply_vibrant_style(ax):
    """统一风格：轴线加粗、刻度加粗"""
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)
    ax.tick_params(axis="both", width=1.2, length=4)


def plot_accuracy_curves(exps: List[Tuple[int, dict, dict]], save_dir: Path):
    """绘制不同 R 下的测试准确率曲线（x 轴为轮数）"""
    if not exps:
        print("  No experiments to plot")
        return

    with plt.style.context(plotter.style):
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "legend.fontsize": plotter.font_size - 1,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)

        for idx, (window, metrics, _config) in enumerate(exps):
            test_acc = metrics.get("test_acc", [])
            if not test_acc:
                continue
            x = list(range(1, len(test_acc) + 1))
            y = test_acc
            label = f"R={window}"
            color = _VIBRANT_COLORS[idx % len(_VIBRANT_COLORS)]
            ls = _VIBRANT_LINESTYLES[idx % len(_VIBRANT_LINESTYLES)]

            ax.plot(
                x, y,
                color=color,
                linestyle=ls,
                linewidth=2.2,
                label=label,
                zorder=3,
            )

        ax.set_xlabel("Communication Round", fontsize=plotter.font_size)
        ax.set_ylabel("Test Accuracy (%)", fontsize=plotter.font_size)
        # 标题字号与 client_selection 系列保持一致（25.2/8.4in = 3.0 pt/in → 6in 画布对应 18pt）
        ax.set_title("FMNIST — Prefetch Windows", pad=12, fontsize=18)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(
            loc="lower right",
            ncol=1,
            frameon=True,
            fontsize=plotter.font_size - 1,
        )
        _apply_vibrant_style(ax)

        fname = "accuracy_curves_by_window"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


def plot_accuracy_vs_window(exps: List[Tuple[int, dict, dict]], save_dir: Path):
    """绘制最终准确率随预取窗口 R 变化的单曲线图（保留）"""
    if not exps:
        print("  No experiments to plot")
        return

    windows = [e[0] for e in exps]
    final_accs = [e[1].get("test_acc", [0])[-1] for e in exps]

    with plt.style.context(plotter.style):
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "legend.fontsize": plotter.font_size - 1,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)

        color = _VIBRANT_COLORS[0]
        ax.plot(
            windows, final_accs,
            color=color,
            linestyle="-",
            linewidth=2.2,
            marker="o",
            markersize=6,
            label="Final Accuracy",
            zorder=3,
        )

        ax.set_xlabel("Prefetch Window $R$", fontsize=plotter.font_size)
        ax.set_ylabel("Final Test Accuracy (%)", fontsize=plotter.font_size)
        ax.set_title("Fashion-MNIST — Accuracy vs. Prefetch Window", pad=10, fontsize=plotter.font_size)
        ax.grid(True, linestyle="--", alpha=0.5)
        _apply_vibrant_style(ax)

        fname = "accuracy_vs_window"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


def plot_comm_vs_window(exps: List[Tuple[int, dict, dict]], save_dir: Path):
    """绘制总通信量随预取窗口 R 变化的柱状图"""
    if not exps:
        print("  No experiments to plot")
        return

    windows = [str(e[0]) for e in exps]
    total_comm = []
    for e in exps:
        comm = e[1].get("total_communication_cost", [])
        total_mb = sum(comm) / (1024 ** 2) if comm else 0
        total_comm.append(total_mb)

    with plt.style.context(plotter.style):
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)

        x_pos = np.arange(len(windows))
        bars = ax.bar(x_pos, total_comm, color=_VIBRANT_COLORS[0], edgecolor="black", linewidth=0.8)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(windows)
        ax.set_xlabel("Prefetch Window $R$", fontsize=plotter.font_size)
        ax.set_ylabel("Total Communication Cost (MB)", fontsize=plotter.font_size)
        ax.set_title("Fashion-MNIST — Communication Cost vs. Prefetch Window", pad=10, fontsize=plotter.font_size)
        ax.grid(True, linestyle="--", alpha=0.5, axis="y")
        _apply_vibrant_style(ax)

        # 在柱顶标注数值
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=plotter.font_size - 2,
            )

        fname = "communication_vs_window"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


def plot_combined_window(exps: List[Tuple[int, dict, dict]], save_dir: Path):
    """双 Y 轴图：准确率 + 通信量 随 R 变化（保留）"""
    if not exps:
        return

    windows = [e[0] for e in exps]
    final_accs = [e[1].get("test_acc", [0])[-1] for e in exps]
    total_comm = []
    for e in exps:
        comm = e[1].get("total_communication_cost", [])
        total_mb = sum(comm) / (1024 ** 2) if comm else 0
        total_comm.append(total_mb)

    with plt.style.context(plotter.style):
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "legend.fontsize": plotter.font_size - 1,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax1 = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)
        ax2 = ax1.twinx()

        color1 = _VIBRANT_COLORS[0]
        color2 = _VIBRANT_COLORS[1]

        ax1.plot(
            windows, final_accs,
            color=color1,
            linestyle="-",
            linewidth=2.2,
            marker="o",
            markersize=6,
            label="Accuracy",
            zorder=3,
        )
        ax2.plot(
            windows, total_comm,
            color=color2,
            linestyle="--",
            linewidth=2.2,
            marker="s",
            markersize=6,
            label="Communication",
            zorder=3,
        )

        ax1.set_xlabel("Prefetch Window $R$", fontsize=plotter.font_size)
        ax1.set_ylabel("Final Test Accuracy (%)", color=color1, fontsize=plotter.font_size)
        ax2.set_ylabel("Total Communication Cost (MB)", color=color2, fontsize=plotter.font_size)
        ax1.set_title("Fashion-MNIST — Accuracy & Communication vs. Prefetch Window", pad=10, fontsize=plotter.font_size)
        ax1.grid(True, linestyle="--", alpha=0.5)

        ax1.tick_params(axis="y", labelcolor=color1)
        ax2.tick_params(axis="y", labelcolor=color2)
        _apply_vibrant_style(ax1)
        _apply_vibrant_style(ax2)

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=plotter.font_size - 1, frameon=True)

        fname = "combined_window_analysis"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" 预取窗口实验结果绘图")
    print("=" * 60)

    exps = scan_window_experiments()
    if not exps:
        print(f"\nNo experiments found in {INPUT_DIR}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nFound {len(exps)} window experiments:")
    for window, metrics, _config in exps:
        acc = metrics.get("test_acc", [0])[-1]
        comm = sum(metrics.get("total_communication_cost", [])) / (1024 ** 2)
        print(f"  R={window:2d}: acc={acc:.2f}%  comm={comm:.1f} MB")

    print(f"\nGenerating plots to: {OUTPUT_DIR}\n")

    # 新增：每条线代表一个 R 值的准确率曲线
    plot_accuracy_curves(exps, OUTPUT_DIR)
    # 保留：最终准确率 vs R
    plot_accuracy_vs_window(exps, OUTPUT_DIR)
    # 保留：通信量柱状图
    plot_comm_vs_window(exps, OUTPUT_DIR)
    # 保留：双 Y 轴图
    plot_combined_window(exps, OUTPUT_DIR)

    print(f"\n{'=' * 60}")
    print(f" All plots saved to: {OUTPUT_DIR}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
