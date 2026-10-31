#!/usr/bin/env python3
"""
Non-IID 绘图公共模块
====================
包含数据加载、保存以及折线图 / 热力图绘制函数。
被 plot_noniid_2x2.py 与 plot_noniid_single.py 共用。
"""

import json
import os
import re
import sys
from pathlib import Path

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import yaml

# ---------------------------------------------------------------------------
# 路径设置
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[3]
save_dir = script_dir.parent / "pic"
save_dir.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(project_root))
from tools.plotter import Plotter  # noqa: E402

# ---------------------------------------------------------------------------
# 全局可视化配置（SciencePlots + 自定义字号）
# ---------------------------------------------------------------------------
matplotlib.use("Agg")

PLOTTER = Plotter(style=["science", "grid"], use_latex=False, font_size=18)

CUSTOM_RCPARAMS = {
    "axes.titlesize": 20,
    "axes.labelsize": 20,
    "xtick.labelsize": 17,
    "ytick.labelsize": 17,
    "legend.fontsize": 18,
    "axes.linewidth": 1.8,
    "xtick.major.width": 1.5,
    "ytick.major.width": 1.5,
    "xtick.major.size": 5,
    "ytick.major.size": 5,
}

# ---------------------------------------------------------------------------
# 方法配置
# ---------------------------------------------------------------------------
METHOD_FOLDERS = {
    "ESAFL": "esafl",
    "FedPHE": "fedphe",
    "MASER": "maser",
    "FedAvg-CKKS": "fedavg+ckks",
    "ECPFL": "ours",
}

METHOD_ORDER = ["ECPFL", "ESAFL", "MASER", "FedPHE", "FedAvg-CKKS"]

COLORS = {
    "ECPFL": "#D62728",
    "ESAFL": "#1F77B4",
    "MASER": "#2CA02C",
    "FedPHE": "#FF7F0E",
    "FedAvg-CKKS": "#9467BD",
}

MARKERS = {"ECPFL": "o", "ESAFL": "s", "MASER": "^", "FedPHE": "D", "FedAvg-CKKS": "v"}
LINESTYLES = {
    "ECPFL": "-",
    "ESAFL": "--",
    "MASER": "-.",
    "FedPHE": ":",
    "FedAvg-CKKS": (0, (5, 1)),
}

ALPHAS = [0.1, 0.5, 1.0, 5.0, 10.0]

# 热力图配色方案（SCI 风格，可自由增删）
HEATMAP_CMAPS = [
    ("YlGnBu", "YlGnBu"),
    ("YlOrRd", "YlOrRd"),
    ("PuBuGn", "PuBuGn"),
    ("RdYlGn", "RdYlGn"),
    ("Viridis", "viridis"),
    ("Coolwarm", "coolwarm"),
]


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------
def _dataset_name(raw: str) -> str:
    if raw == "fashion_mnist":
        return "FMNIST"
    if raw == "cifar10":
        return "CIFAR-10"
    return raw


def save_data(accuracy: dict, alphas: list, methods: list):
    """将准确率数据保存为 JSON 与 Markdown 表格，方便直接编辑。"""
    datasets = ["FMNIST", "CIFAR-10"]
    data = {
        "datasets": datasets,
        "alphas": alphas,
        "methods": methods,
        "accuracy": {},
    }
    for ds in datasets:
        data["accuracy"][ds] = {}
        for method in methods:
            vals = [round(accuracy[method][ds].get(alpha, float("nan")), 2) for alpha in alphas]
            data["accuracy"][ds][method] = vals

    json_path = script_dir / "noniid_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Saved] {json_path}")

    md_path = script_dir / "noniid_data.md"
    lines = ["# Non-IID Accuracy Summary\n", "Source: `accuracy_baseline/{esafl,fedphe,maser,fedavg+ckks,ours}/noneiid_result`\n"]
    for ds in datasets:
        lines.append(f"\n## {ds}\n")
        lines.append("| Method | " + " | ".join(f"α={a}" for a in alphas) + " |")
        lines.append("|" + "|".join(["---"] * (len(alphas) + 1)) + "|")
        for method in methods:
            vals = data["accuracy"][ds][method]
            lines.append(f"| {method} | " + " | ".join(str(v) for v in vals) + " |")
    lines.append("\n")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[Saved] {md_path}")


def load_data():
    """从脚本目录下的 noniid_data.json 读取绘图数据；若不存在则从实验目录生成。"""
    json_path = script_dir / "noniid_data.json"
    if not json_path.exists():
        print("[Info] 未找到 noniid_data.json，正在从实验目录重新生成...")
        accuracy = load_experiments()
        save_data(accuracy, ALPHAS, METHOD_ORDER)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    accuracy = {
        method: {ds: {} for ds in data["datasets"]} for method in data["methods"]
    }
    for ds in data["datasets"]:
        for method in data["methods"]:
            for alpha, acc in zip(data["alphas"], data["accuracy"][ds][method]):
                accuracy[method][ds][alpha] = float(acc)
    return accuracy, data["alphas"]


def load_experiments():
    """扫描所有 baseline 的 noneiid_result，返回结构化的准确率数据。"""
    accuracy = {method: {"FMNIST": {}, "CIFAR-10": {}} for method in METHOD_ORDER}

    for method, folder in METHOD_FOLDERS.items():
        result_dir = project_root / "accuracy_baseline" / folder / "noneiid_result"
        if not result_dir.exists():
            continue

        for exp_dir in result_dir.iterdir():
            if not exp_dir.is_dir():
                continue

            cfg_path = exp_dir / "config.yaml"
            metrics_path = exp_dir / "metrics.json"
            if not cfg_path.exists() or not metrics_path.exists():
                continue

            with open(cfg_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            with open(metrics_path, encoding="utf-8") as f:
                metrics = json.load(f)

            ds_raw = cfg.get("data", {}).get("dataset") or cfg.get("dataset")
            ds = _dataset_name(ds_raw)
            if ds not in ("FMNIST", "CIFAR-10"):
                continue

            # 优先从目录名解析 alpha（OURS 的 alpha_1 目录配置中 alpha 可能不一致）
            m = re.search(r"alpha[_-]?([0-9.]+)", exp_dir.name)
            if m:
                alpha = float(m.group(1))
            else:
                alpha = cfg.get("data", {}).get("alpha")
            if alpha is None:
                continue
            alpha = float(alpha)

            acc = metrics.get("test_acc", [None])[-1]
            if acc is None and metrics.get("metrics_summary"):
                acc = metrics["metrics_summary"].get("final_test_acc")
            if acc is None:
                continue
            accuracy[method][ds][alpha] = float(acc)

    return accuracy


# ---------------------------------------------------------------------------
# 绘图函数
# ---------------------------------------------------------------------------
def draw_line_subplot(ax, dataset: str, accuracy: dict, alphas: list = None):
    """绘制单个数据集的 Non-IID 准确率折线图，图例在右下角。"""
    if alphas is None:
        alphas = ALPHAS
    x = np.arange(len(alphas))

    for method in METHOD_ORDER:
        accs = [accuracy[method][dataset].get(alpha, np.nan) for alpha in alphas]
        ax.plot(
            x,
            accs,
            color=COLORS[method],
            marker=MARKERS[method],
            linestyle=LINESTYLES[method],
            linewidth=5.0,
            markersize=10,
            markerfacecolor=COLORS[method],
            markeredgecolor="white",
            markeredgewidth=1.0,
            label=method,
            zorder=3,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas], fontsize=17)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.tick_params(axis="y", labelsize=17)
    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=20)
    ax.set_ylabel("Test Accuracy (%)", fontsize=20)
    ax.grid(True, linestyle="--", alpha=0.4, zorder=1)
    ax.set_axisbelow(True)

    # 加粗子图边框
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    ax.legend(
        loc="lower right",
        fontsize=18,
        frameon=True,
        ncol=1,
        handletextpad=0.4,
        columnspacing=1.0,
    )


# ---------------------------------------------------------------------------
# 折线图变体（additive，优雅 / 清晰 / 与默认样式不同）
# ---------------------------------------------------------------------------
def draw_line_elegant(ax, dataset: str, accuracy: dict, alphas: list = None):
    """优雅开放标记折线图：ECPFL 加粗高亮，其余半透明细线。"""
    if alphas is None:
        alphas = ALPHAS
    x = np.arange(len(alphas))

    for method in METHOD_ORDER:
        accs = [accuracy[method][dataset].get(alpha, np.nan) for alpha in alphas]
        is_ours = method == "ECPFL"
        ax.plot(
            x,
            accs,
            color=COLORS[method],
            marker=MARKERS[method],
            linestyle=LINESTYLES[method],
            linewidth=3.6 if is_ours else 2.0,
            alpha=1.0 if is_ours else 0.75,
            markersize=12 if is_ours else 8,
            markerfacecolor="white",
            markeredgecolor=COLORS[method],
            markeredgewidth=2.0 if is_ours else 1.4,
            label=method,
            zorder=5 if is_ours else 3,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas], fontsize=15)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=20)
    ax.set_ylabel("Test Accuracy (%)", fontsize=18)
    ax.grid(True, linestyle=":", alpha=0.35, zorder=1)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)
    ax.legend(
        loc="lower right",
        fontsize=15,
        frameon=True,
        fancybox=True,
        shadow=False,
        ncol=1,
        handletextpad=0.3,
        columnspacing=0.8,
    )


def _smooth_xy(x, y, num=200):
    """使用 CubicSpline 生成平滑曲线；若 scipy 不可用则线性插值。"""
    try:
        from scipy.interpolate import make_interp_spline
        spl = make_interp_spline(x, y, k=3)
        x_fine = np.linspace(x.min(), x.max(), num)
        y_fine = spl(x_fine)
        y_fine = np.clip(y_fine, 0, 100)
        return x_fine, y_fine
    except Exception:
        x_fine = np.linspace(x.min(), x.max(), num)
        y_fine = np.interp(x_fine, x, y)
        return x_fine, y_fine


def draw_line_smooth_area(ax, dataset: str, accuracy: dict, alphas: list = None):
    """平滑曲线 + 半透明面积填充，强调变化趋势。"""
    if alphas is None:
        alphas = ALPHAS
    x = np.arange(len(alphas))

    for method in METHOD_ORDER:
        accs = np.array([accuracy[method][dataset].get(alpha, np.nan) for alpha in alphas])
        if np.any(np.isnan(accs)):
            continue
        x_fine, y_fine = _smooth_xy(x, accs)
        is_ours = method == "ECPFL"
        ax.fill_between(
            x_fine,
            y_fine,
            alpha=0.18 if is_ours else 0.10,
            color=COLORS[method],
            zorder=2 if is_ours else 1,
        )
        ax.plot(
            x_fine,
            y_fine,
            color=COLORS[method],
            linestyle=LINESTYLES[method],
            linewidth=3.4 if is_ours else 2.2,
            alpha=1.0 if is_ours else 0.85,
            label=method,
            zorder=4 if is_ours else 3,
        )
        ax.scatter(
            x,
            accs,
            color=COLORS[method],
            marker=MARKERS[method],
            s=110 if is_ours else 70,
            edgecolors="white",
            linewidths=1.0,
            zorder=6 if is_ours else 5,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas], fontsize=15)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=18)
    ax.set_ylabel("Test Accuracy (%)", fontsize=18)
    ax.grid(True, linestyle="--", alpha=0.3, zorder=1)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)
    ax.legend(
        loc="lower right",
        fontsize=15,
        frameon=True,
        fancybox=True,
        ncol=1,
        handletextpad=0.3,
        columnspacing=0.8,
    )


def draw_line_step(ax, dataset: str, accuracy: dict, alphas: list = None):
    """阶梯折线图，强调每个 α 是独立实验点。"""
    if alphas is None:
        alphas = ALPHAS
    x = np.arange(len(alphas))

    for method in METHOD_ORDER:
        accs = [accuracy[method][dataset].get(alpha, np.nan) for alpha in alphas]
        is_ours = method == "ECPFL"
        ax.step(
            x,
            accs,
            where="mid",
            color=COLORS[method],
            linestyle=LINESTYLES[method],
            linewidth=3.0 if is_ours else 2.0,
            alpha=1.0 if is_ours else 0.8,
            label=method,
            zorder=3,
        )
        ax.scatter(
            x,
            accs,
            color=COLORS[method],
            marker=MARKERS[method],
            s=130 if is_ours else 90,
            edgecolors="white",
            linewidths=1.2,
            zorder=5 if is_ours else 4,
        )

    # 添加横向参考线帮助读数
    for y in np.arange(20, 101, 20):
        ax.axhline(y, color="gray", linestyle="-", linewidth=0.5, alpha=0.2, zorder=1)

    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas], fontsize=15)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=18)
    ax.set_ylabel("Test Accuracy (%)", fontsize=18)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)
    ax.legend(
        loc="lower right",
        fontsize=15,
        frameon=True,
        fancybox=True,
        ncol=1,
        handletextpad=0.3,
        columnspacing=0.8,
    )


def draw_line_labeled(ax, dataset: str, accuracy: dict, alphas: list = None):
    """极简风格：无网格、无图例，右侧直接标注方法名。"""
    if alphas is None:
        alphas = ALPHAS
    x = np.arange(len(alphas))

    labels_y = []
    for method in METHOD_ORDER:
        accs = np.array([accuracy[method][dataset].get(alpha, np.nan) for alpha in alphas])
        if np.any(np.isnan(accs)):
            continue
        is_ours = method == "ECPFL"
        ax.plot(
            x,
            accs,
            color=COLORS[method],
            marker=MARKERS[method],
            linestyle=LINESTYLES[method],
            linewidth=3.4 if is_ours else 2.2,
            markersize=10 if is_ours else 7,
            markerfacecolor=COLORS[method],
            markeredgecolor="white",
            markeredgewidth=0.9,
            label=method,
            zorder=3,
        )
        labels_y.append((method, accs[-1], COLORS[method], is_ours))

    # 右侧标注，按终点 y 排序后做最小防重叠
    labels_y.sort(key=lambda t: t[1])
    min_gap = 6.0
    for i in range(1, len(labels_y)):
        if labels_y[i][1] - labels_y[i - 1][1] < min_gap:
            labels_y[i] = (labels_y[i][0], labels_y[i - 1][1] + min_gap,
                           labels_y[i][2], labels_y[i][3])

    x_last = x[-1] + 0.18
    for method, y, color, is_ours in labels_y:
        ax.text(
            x_last,
            y,
            method,
            color=color,
            fontsize=14 if is_ours else 13,
            fontweight="bold" if is_ours else "normal",
            va="center",
            ha="left",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([str(a) for a in alphas], fontsize=15)
    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=18)
    ax.set_ylabel("Test Accuracy (%)", fontsize=18)
    ax.grid(False)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(2.2)


def draw_alpha_heatmap(ax, dataset: str, accuracy: dict, alphas: list = None,
                       add_colorbar: bool = True, cmap: str = "YlGnBu"):
    """绘制 α 动态变化热力图：行为方法，列为 α，颜色为准确率。"""
    if alphas is None:
        alphas = ALPHAS
    methods = METHOD_ORDER[::-1]
    data = np.array(
        [[accuracy[m][dataset].get(alpha, np.nan) for alpha in alphas] for m in methods],
        dtype=float,
    )

    vmin, vmax = 0, 100
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    im = ax.imshow(
        data,
        cmap=cmap,
        norm=norm,
        aspect="auto",
        extent=[-0.5, len(alphas) - 0.5, -0.5, len(methods) - 0.5],
        origin="lower",
    )

    # 单元格数值
    for i, m in enumerate(methods):
        for j, alpha in enumerate(alphas):
            val = data[i, j]
            if np.isnan(val):
                continue
            ax.text(
                j,
                i,
                f"{val:.1f}",
                ha="center",
                va="center",
                color="black",
                fontsize=18,
            )

    ax.set_xticks(np.arange(len(alphas)))
    ax.set_xticklabels([str(a) for a in alphas], fontsize=17)
    ax.set_yticks(np.arange(len(methods)))
    ax.set_yticklabels(methods, fontsize=17)
    ax.set_xlim(-0.5, len(alphas) - 0.5)
    ax.set_ylim(-0.5, len(methods) - 0.5)

    for spine in ax.spines.values():
        spine.set_linewidth(2.2)

    # 手动绘制白色单元格分隔线
    for x in np.arange(-0.5, len(alphas), 1):
        ax.axvline(x, color="white", linewidth=1.5, zorder=2)
    for y in np.arange(-0.5, len(methods), 1):
        ax.axhline(y, color="white", linewidth=1.5, zorder=2)
    ax.grid(False)

    ax.set_xlabel(r"Non-IID coefficient $\alpha$", fontsize=18)

    # 颜色条
    if add_colorbar:
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Accuracy (%)", fontsize=18)
        cbar.ax.tick_params(labelsize=16)

    return im
