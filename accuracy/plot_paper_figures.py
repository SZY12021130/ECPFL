#!/usr/bin/env python3
"""
论文级图表自动生成脚本 — 使用 tools/plotter.Plotter (SciencePlots 风格)

扫描 accuracy/ 目录下的实验结果，按数据集-模型分组绘制：
  1. Test Accuracy vs. Communication Rounds (不同稀疏率)
  2. Test Loss vs. Communication Rounds
  3. Cumulative Communication Cost vs. Rounds
  4. Final Accuracy Bar Chart (所有稀疏率对比)

用法:
  python scripts/plot_paper_figures.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # 无头后端，必须在 Plotter 导入前设置

import numpy as np

# 导入 Plotter
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.plotter import Plotter, COLOR_THEMES

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--input-dir", type=str, default=".", help="实验结果根目录 (默认: 当前目录)")
_parser.add_argument("--output-dir", type=str, default=None, help="图表输出目录 (默认: {input-dir}/plots)")
_args = _parser.parse_args()

ACCURACY_DIR = Path(_args.input_dir)
OUTPUT_DIR = Path(_args.output_dir) if _args.output_dir else ACCURACY_DIR / "plots"

# 颜色与线型映射
COLORS = COLOR_THEMES["paper"]
LINESTYLES = ["-", "--", "-.", ":", "-", "--"]
MARKERS = ["o", "s", "^", "D", "v", "p"]

# 初始化 Plotter（SciencePlots 风格）
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

def load_experiment(exp_dir: Path) -> Tuple[dict, dict]:
    """加载单个实验的 metrics.json 和 config.yaml"""
    metrics_path = exp_dir / "metrics.json"
    config_path = exp_dir / "config.yaml"

    if not metrics_path.exists():
        return None, None

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    config = {}
    if config_path.exists():
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    return metrics, config


def scan_experiments() -> Dict[str, List[Tuple[Path, dict, dict]]]:
    """
    扫描 accuracy/ 目录，按 category (dataset-model) 分组返回实验列表。
    返回: {category: [(exp_dir, metrics, config), ...]}
    """
    groups = {}
    if not ACCURACY_DIR.exists():
        print(f"Warning: {ACCURACY_DIR} does not exist")
        return groups

    for category_dir in ACCURACY_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        if category_dir.name == "plots":
            continue

        category = category_dir.name
        exps = []
        for exp_dir in category_dir.iterdir():
            if not exp_dir.is_dir():
                continue
            metrics, config = load_experiment(exp_dir)
            if metrics is not None:
                exps.append((exp_dir, metrics, config))

        if exps:
            # 去重：同一 sparsity 优先选择真正稀疏化的实验（num_ct 更低）
            best = {}
            for exp_dir, metrics, config in exps:
                label = get_sparsity_label(config)
                num_ct = metrics.get("num_ciphertexts", [])
                avg_num_ct = sum(num_ct) / len(num_ct) if num_ct else 0
                test_acc = metrics.get("test_acc", [])
                if not test_acc:
                    continue
                key = label
                if key not in best:
                    best[key] = (exp_dir, metrics, config, avg_num_ct)
                else:
                    prev = best[key]
                    if avg_num_ct < prev[3] * 0.5:
                        best[key] = (exp_dir, metrics, config, avg_num_ct)
                    elif abs(avg_num_ct - prev[3]) / max(prev[3], 1) < 0.3:
                        if test_acc[-1] > prev[1].get("test_acc", [0])[-1]:
                            best[key] = (exp_dir, metrics, config, avg_num_ct)
            exps = [(v[0], v[1], v[2]) for v in best.values()]
            exps.sort(key=lambda x: x[0].name)
            groups[category] = exps

    return groups


def get_sparsity_label(config: dict) -> str:
    """从配置中提取稀疏率标签"""
    sparsification = config.get("ckks", {}).get("sparsification", {})
    strategy = sparsification.get("strategy", "none")
    if strategy == "none":
        return "1"
    rate = sparsification.get("sparsity_rate", "?")
    return f"{rate}"


def _get_title(group_name: str, base_title: str) -> str:
    """生成图表标题"""
    if "fashion_mnist" in group_name:
        # 与另外三张敏感性分析图统一：数据集名写 FMNIST、分隔符统一用长破折号
        return "FMNIST — Local Sparsity"
    return f"{base_title} — {group_name}"


def _sort_sparsity(items):
    """按稀疏率排序：1 (none) 放最后，其余按数值排序"""
    def _key(item):
        label = item[0] if isinstance(item, (tuple, list)) else item
        if label == "1":
            return (1, 0)
        try:
            return (0, float(label))
        except ValueError:
            return (0, 0)
    return sorted(items, key=_key)


# ---------------------------------------------------------------------------
# 绘图函数（统一使用 Plotter）
# ---------------------------------------------------------------------------

def _prepare_line_data(exps: List[Tuple[Path, dict, dict]], metric_key: str, transform=None):
    """准备折线图数据、颜色、标记和线型"""
    data = {}
    colors = {}
    markers = {}
    linestyles = {}

    for idx, (exp_dir, metrics, config) in enumerate(exps):
        values = metrics.get(metric_key, [])
        if not values:
            continue

        label = get_sparsity_label(config)
        rounds = list(range(1, len(values) + 1))
        # 图例用 ζ 代替 "sparsity"（mathtext 渲染，不依赖 LaTeX）；
        # 无稀疏化那档标签是 "1"，图例里统一写成 1.0，与 0.1/0.3/... 位数对齐
        display = "1.0" if label == "1" else label
        series_label = rf"$\zeta={display}$"

        y_values = values if transform is None else transform(values)
        if hasattr(y_values, 'tolist'):
            y_values = y_values.tolist()

        data[series_label] = {"x": rounds, "y": y_values}
        colors[series_label] = COLORS[idx % len(COLORS)]
        markers[series_label] = MARKERS[idx % len(MARKERS)]
        linestyles[series_label] = LINESTYLES[idx % len(LINESTYLES)]

    return data, colors, markers, linestyles


# 鲜艳配色 + 线型（vibrant_clean 风格）
_VIBRANT_COLORS = ["#E31A1C", "#1F78B4", "#33A02C", "#FF7F00", "#6A3D9A", "#08519C"]
_VIBRANT_LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
_VIBRANT_MARKERS = ["o", "s", "^", "D", "v", "p"]


def plot_accuracy_curves(group_name: str, exps: List[Tuple[Path, dict, dict]], save_dir: Path):
    """绘制不同稀疏率下的测试准确率曲线（vibrant_clean 风格：无 marker + 鲜艳配色 + 小图例）"""
    data, _, _, _ = _prepare_line_data(exps, "test_acc")
    if not data:
        return

    title = _get_title(group_name, "Test Accuracy vs. Rounds")
    sorted_items = _sort_sparsity(list(data.items()))

    import matplotlib.pyplot as plt

    with plt.style.context(plotter.style):
        # 统一字体（与 generate_analysis_and_plots.py 一致）
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "legend.fontsize": plotter.font_size - 1,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)

        for idx, (label, series) in enumerate(sorted_items):
            x = np.array(series["x"])
            y = np.array(series["y"])
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

        ax.set_xlabel("Communication Round", fontsize=plotter.font_size + 2)
        ax.set_ylabel("Test Accuracy (%)", fontsize=plotter.font_size + 2)
        ax.set_title(title, pad=10, fontsize=plotter.font_size)
        ax.grid(True, linestyle="--", alpha=0.5)

        # 图例：右侧中间，单列，字体缩小到 8pt
        ax.legend(
            loc="lower right",
            ncol=1,
            frameon=True,
            fontsize=plotter.font_size - 1,
        )

        # 轴线加粗
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.tick_params(axis="both", width=1.2, length=4)

        fname = f"{group_name}_accuracy_curves"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


def plot_accuracy_curves_vibrant_marker(group_name: str, exps: List[Tuple[Path, dict, dict]], save_dir: Path):
    """绘制不同稀疏率下的测试准确率曲线（vibrant_marker 风格：带 marker + 鲜艳配色 + 图例外挂）"""
    data, _, _, _ = _prepare_line_data(exps, "test_acc")
    if not data:
        return

    title = _get_title(group_name, "Test Accuracy vs. Rounds")
    sorted_items = _sort_sparsity(list(data.items()))

    import matplotlib.pyplot as plt

    with plt.style.context(plotter.style):
        plt.rcParams.update({
            "font.size": plotter.font_size,
            "axes.labelsize": plotter.font_size,
            "legend.fontsize": 14,
            "xtick.labelsize": plotter.font_size - 1,
            "ytick.labelsize": plotter.font_size - 1,
        })
        fig, ax = plt.subplots(figsize=plotter.figsize, dpi=plotter.dpi)

        for idx, (label, series) in enumerate(sorted_items):
            x = np.array(series["x"])
            y = np.array(series["y"])
            color = _VIBRANT_COLORS[idx % len(_VIBRANT_COLORS)]
            ls = _VIBRANT_LINESTYLES[idx % len(_VIBRANT_LINESTYLES)]
            marker = _VIBRANT_MARKERS[idx % len(_VIBRANT_MARKERS)]

            ax.plot(
                x, y,
                color=color,
                linestyle=ls,
                linewidth=2.0,
                marker=marker,
                markersize=5,
                markevery=5,
                label=label,
                zorder=3,
            )

        ax.set_xlabel("Communication Round", fontsize=plotter.font_size)
        ax.set_ylabel("Test Accuracy (%)", fontsize=plotter.font_size)
        # 标题字号与 client_selection 系列保持一致（25.2/8.4in = 3.0 pt/in → 6in 画布对应 18pt）
        ax.set_title(title, pad=12, fontsize=18)
        ax.grid(True, linestyle="--", alpha=0.5)

        # 图例：右下角，单列，字体 13pt
        ax.legend(
            loc="lower right",
            ncol=1,
            frameon=True,
            fontsize=17,
        )

        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.tick_params(axis="both", width=1.2, length=4)

        fname = f"{group_name}_accuracy_curves_vibrant_marker"
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"{fname}.{fmt}"
            fig.savefig(fpath, dpi=plotter.dpi, bbox_inches="tight", format=fmt)
        plt.close(fig)
        print(f"  Saved: {save_dir / f'{fname}.png'}")


def plot_loss_curves(group_name: str, exps: List[Tuple[Path, dict, dict]], save_dir: Path):
    """绘制测试损失曲线"""
    data, colors, markers, linestyles = _prepare_line_data(exps, "test_loss")
    if not data:
        return

    title = _get_title(group_name, "Test Loss vs. Rounds")

    plotter.line(
        data=data,
        xlabel="Communication Round",
        ylabel="Test Loss",
        title=title,
        colors=colors,
        markers=markers,
        linestyles=linestyles,
        linewidth=1.8,
        marker_size=5,
        legend_loc="best",
        legend_fontsize=12,
        filename=f"{group_name}_loss_curves",
        formats=["png", "pdf"],
    )
    print(f"  Saved: {save_dir / f'{group_name}_loss_curves.png'}")


def plot_communication_cost(group_name: str, exps: List[Tuple[Path, dict, dict]], save_dir: Path):
    """绘制累积通信开销曲线"""
    def cumsum_mb(values):
        return np.cumsum(values) / (1024 ** 2)

    data, colors, markers, linestyles = _prepare_line_data(exps, "total_communication_cost", transform=cumsum_mb)
    if not data:
        return

    title = _get_title(group_name, "Communication Cost vs. Rounds")

    plotter.line(
        data=data,
        xlabel="Communication Round",
        ylabel="Cumulative Communication Cost (MB)",
        title=title,
        colors=colors,
        markers=markers,
        linestyles=linestyles,
        linewidth=1.8,
        marker_size=5,
        legend_loc="best",
        legend_fontsize=16,
        filename=f"{group_name}_communication_cost",
        formats=["png", "pdf"],
    )
    print(f"  Saved: {save_dir / f'{group_name}_communication_cost.png'}")


def plot_final_accuracy_bar(group_name: str, exps: List[Tuple[Path, dict, dict]], save_dir: Path):
    """绘制最终准确率柱状图"""
    labels = []
    final_accs = []

    for exp_dir, metrics, config in exps:
        test_acc = metrics.get("test_acc", [])
        if not test_acc:
            continue
        labels.append(get_sparsity_label(config))
        final_accs.append(test_acc[-1])

    if not labels:
        return

    # 排序
    sorted_pairs = _sort_sparsity(list(zip(labels, final_accs)))
    labels, final_accs = zip(*sorted_pairs)

    # 使用 Plotter.bar() — categories 为 sparsity labels，单 series
    bar_data = {
        "categories": list(labels),
        "series": {
            "Final Accuracy": list(final_accs)
        }
    }

    title = _get_title(group_name, "Final Accuracy Comparison")

    # 临时调整 figsize
    orig_figsize = plotter.figsize
    n_bars = len(labels)
    plotter.figsize = (max(6, n_bars * 1.2), 5)

    plotter.bar(
        data=bar_data,
        xlabel="Sparsity Rate",
        ylabel="Final Test Accuracy (%)",
        title=title,
        ylim=(0, 105),
        grid=True,
        filename=f"{group_name}_final_accuracy_bar",
        formats=["png", "pdf"],
    )

    plotter.figsize = orig_figsize
    print(f"  Saved: {save_dir / f'{group_name}_final_accuracy_bar.png'}")


def plot_combined_summary(all_groups: Dict[str, List[Tuple[Path, dict, dict]]], save_dir: Path):
    """跨数据集的最终准确率综合对比图"""
    # 收集每个 group 的数据
    group_data = {}
    for group_name, exps in all_groups.items():
        labels = []
        final_accs = []
        for exp_dir, metrics, config in exps:
            test_acc = metrics.get("test_acc", [])
            if not test_acc:
                continue
            labels.append(get_sparsity_label(config))
            final_accs.append(test_acc[-1])

        if labels:
            sorted_pairs = _sort_sparsity(list(zip(labels, final_accs)))
            group_data[group_name] = dict(sorted_pairs)

    if not group_data:
        return

    # 收集所有 group 共有的 sparsity labels
    all_labels_sets = [set(gd.keys()) for gd in group_data.values()]
    common_labels = set.intersection(*all_labels_sets) if len(all_labels_sets) > 1 else all_labels_sets[0]

    # 如果没有共有 labels，放宽到出现在至少一半 group 中的 labels
    if not common_labels:
        from collections import Counter
        label_counts = Counter()
        for gd in group_data.values():
            for label in gd:
                label_counts[label] += 1
        min_count = max(1, len(group_data) // 2)
        common_labels = {l for l, c in label_counts.items() if c >= min_count}

    if not common_labels:
        print("  Skipped: no common sparsity labels across groups")
        return

    sorted_labels = _sort_sparsity(list(common_labels))

    # 整理为 bar() 格式
    sorted_groups = sorted(group_data.keys())
    categories = [g.split("-")[0] for g in sorted_groups]  # 简化 group name

    series = {}
    for label in sorted_labels:
        values = []
        for g in sorted_groups:
            values.append(group_data[g].get(label, 0))
        series[f"s={label}"] = values

    bar_data = {
        "categories": categories,
        "series": series
    }

    # 临时调整 figsize
    orig_figsize = plotter.figsize
    n_cats = len(categories)
    n_series = len(series)
    plotter.figsize = (max(8, n_cats * n_series * 0.8), 6)

    plotter.bar(
        data=bar_data,
        xlabel="Dataset",
        ylabel="Final Test Accuracy (%)",
        title="Final Accuracy Across All Configurations",
        ylim=(0, 105),
        grid=True,
        filename="combined_final_accuracy",
        formats=["png", "pdf"],
    )

    plotter.figsize = orig_figsize
    print(f"  Saved: {save_dir / 'combined_final_accuracy.png'}")


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" 论文级图表自动生成 (Plotter + SciencePlots)")
    print("=" * 60)

    groups = scan_experiments()
    if not groups:
        print("No experiments found in accuracy/ directory.")
        print("Run scripts/run_experiments.py first.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nFound {len(groups)} experiment groups:")
    for name, exps in groups.items():
        print(f"  {name}: {len(exps)} experiments")

    print(f"\nGenerating plots to: {OUTPUT_DIR}\n")

    for group_name, exps in groups.items():
        print(f"[{group_name}] {len(exps)} experiments")
        plot_accuracy_curves(group_name, exps, OUTPUT_DIR)
        plot_accuracy_curves_vibrant_marker(group_name, exps, OUTPUT_DIR)
        plot_loss_curves(group_name, exps, OUTPUT_DIR)
        plot_communication_cost(group_name, exps, OUTPUT_DIR)
        plot_final_accuracy_bar(group_name, exps, OUTPUT_DIR)

    # 综合对比图
    print("\n[Combined] Cross-group summary")
    plot_combined_summary(groups, OUTPUT_DIR)

    print(f"\n{'=' * 60}")
    print(f" All plots saved to: {OUTPUT_DIR}")
    print(f"{'=' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
