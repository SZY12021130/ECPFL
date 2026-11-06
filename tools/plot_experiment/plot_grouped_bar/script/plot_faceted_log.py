"""
分面柱状图 + 对数刻度 (SciencePlots 风格)
每个数据集一个子图，Y轴对数刻度，所有数值清晰可见
支持多组配色主题，与 plot_grouped_bar.py 风格一致
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# 路径设置
script_dir = os.path.dirname(os.path.abspath(__file__))
project_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_tools_dir)

from plotter import Plotter

# ---------------------------------------------------------------------------
# 1. 数据配置
# ---------------------------------------------------------------------------
# 口径约定（2026-11-06 锁定）：
#   TV = UV + FV（同步下行），PV 预取单列不计入；MB = 10^6 字节；
#   ECPFL 下行柱只含同步 FV（预取 PV 由图十单独展示）。
#   基线三方案暂用论文旧数字（待基线核查/重跑后替换为自动读数）。
import json
import glob as _glob

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = [
    "ECPFL-TH",
    "FedPHE",
    "ESAFL",
    "MASER",
    "FedAvg+CKKS",
]


def _load_ecpfl_th(ds):
    """ECPFL-TH：自动读取重跑结果（TV=UV+FV 口径，MB=10^6）。"""
    name = {"MNIST": "mnist", "FMNIST": "fashion_mnist",
            "CIFAR-10": "cifar10", "SVHN": "svhn"}[ds]
    exps = [e for e in sorted(_glob.glob(
        ROOT + r"\AAAAA_Rework\ECPFL\result\accuracy_diri1_tt\experiment_*"))
            if os.path.basename(e).endswith("_" + name)]
    if not exps:
        return None
    d = json.load(open(_glob.glob(exps[-1] + r"\ecpfl_results.json")[0],
                       encoding="utf-8"))
    rounds = d["rounds"]
    uv = sum(r["upload_bytes"] for r in rounds) / 1e6
    fv = sum(r["download_bytes"] for r in rounds) / 1e6
    return [uv, fv]


def _load_esafl(ds):
    """ESAFL：自动读取 α=1 结果（当前指向旧 T=3/10-bit 运行；
    T=3 + 20-bit 修复重跑完成后，把目录换成新时间戳即可）。"""
    paths = {
        "MNIST": ROOT + r"\AAAAA_Rework\ESAFL\result\accuracy_diri1\experiment_20261105_121440_mnist",
        "SVHN": ROOT + r"\AAAAA_Rework\ESAFL\result\accuracy_diri1\experiment_20261105_122858_svhn",
        "FMNIST": ROOT + r"\AAAAA_Rework\ESAFL\result\noniid\experiment_20261104_214115_fashion_mnist",
        "CIFAR-10": ROOT + r"\AAAAA_Rework\ESAFL\result\noniid\experiment_20261105_000652_cifar10",
    }
    m = json.load(open(paths[ds] + r"\metrics.json", encoding="utf-8"))
    uv = sum(m["upload_cost"]) / 1e6
    fv = sum(m["download_cost"]) / 1e6
    return [uv, fv]


# 基线：论文旧数字（MB，2^20 口径），待基线重跑/核查后替换
_BASELINE_FIXED = {
    "FedPHE": {
        "MNIST": [797.03, 3133.42], "FMNIST": [398.55, 3645.94],
        "CIFAR-10": [13548.73, 18960.94], "SVHN": [23112.74, 32567.46]},
    "MASER": {
        "MNIST": [5531.23, 2977.45], "FMNIST": [4766.15, 2573.86],
        "CIFAR-10": [27066.40, 14839.93], "SVHN": [46991.57, 25733.91]},
    "FedAvg+CKKS": {
        "MNIST": [4383.87, 4383.87], "FMNIST": [3985.09, 3985.09],
        "CIFAR-10": [26699.46, 26699.46], "SVHN": [45828.08, 45828.08]},
}


def _build_data():
    data = {}
    for ds in DATASETS:
        row = {}
        e = _load_ecpfl_th(ds)
        row["ECPFL-TH"] = e if e else [0.0, 0.0]
        if e is None:
            print(f"[WARN] ECPFL-TH {ds} 结果缺失（SVHN 重跑未完成？），柱高置 0")
        row["ESAFL"] = _load_esafl(ds)
        for m in ("FedPHE", "MASER", "FedAvg+CKKS"):
            row[m] = _BASELINE_FIXED[m][ds]
        data[ds] = row
    return data


DATA = _build_data()

# ===========================================================================
# 配色方案库（8 组，与 plot_grouped_bar.py 一致）
# ===========================================================================
COLOR_THEME = "all"

# 每组: (upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name)
COLOR_THEMES = [
    ("#E31A1C", "///", "#1F78B4", "\\\\", "vibrant_red_blue"),
    ("#33A02C", "+++", "#FF7F00", "xxx", "green_orange"),
    ("#6A3D9A", "///", "#2CA02C", "---", "purple_green"),
    ("#D62728", "|||", "#08519C", "///", "red_cyan"),
    ("#FF7F0E", "", "#9467BD", "///", "orange_purple"),
    ("#E63946", "///", "#2A9D8F", "\\\\", "coral_teal"),
    ("#F4A261", "///", "#264653", "\\\\", "sand_navy"),
    ("#1F77B4", "xxx", "#D62728", "///", "blue_red"),
]

# ===========================================================================
# 样式参数（与 plot_grouped_bar.py 保持一致）
# ===========================================================================
EDGE_COLOR = "#555555"
EDGE_WIDTH = 0.4
BAR_ALPHA = 0.92

SPINE_LW = 1.8
TICK_WIDTH = 1.5
TICK_LENGTH = 5

FONT_SIZE_BASE = 18
FONT_SIZE_TITLE = 18
FONT_SIZE_LABEL = 18
FONT_SIZE_TICK = 15
FONT_SIZE_LEGEND = 12
FONT_SIZE_VALUE = 9

# ---------------------------------------------------------------------------
# 2. 绘图函数
# ---------------------------------------------------------------------------
def _draw_one_theme(upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name, plotter):
    """绘制并保存某一配色方案的分面对数柱状图。"""
    with plt.style.context(plotter.style):
        fig, axes = plt.subplots(1, 4, figsize=(18, 4.5))
        axes = axes.flatten()

        save_dir = plotter.output_dir
        x = np.arange(len(METHODS))
        width = 0.35

        for ax, ds in zip(axes, DATASETS):
            uploads = [DATA[ds][m][0] for m in METHODS]
            fetches = [DATA[ds][m][1] for m in METHODS]

            bar_up = ax.bar(
                x - width / 2, uploads, width,
                label="CT-Upstream",
                color=upload_color, edgecolor=EDGE_COLOR,
                linewidth=EDGE_WIDTH, hatch=upload_hatch, alpha=BAR_ALPHA,
            )
            bar_fetch = ax.bar(
                x + width / 2, fetches, width,
                label="CT-Downstream",
                color=fetch_color, edgecolor=EDGE_COLOR,
                linewidth=EDGE_WIDTH, hatch=fetch_hatch, alpha=BAR_ALPHA,
            )

            # 对数刻度
            ax.set_yscale("log")
            ax.set_ylim(5, 2000000)

            y_ticks = [10, 100, 1000, 10000, 100000, 1000000]
            y_labels = ["10", "100", "1K", "10K", "100K", "1M"]
            ax.set_yticks(y_ticks)
            ax.set_yticklabels(y_labels, fontsize=FONT_SIZE_TICK)

            # 柱子外部数值标签
            # 当上行/下行高度相近（比值 < 1.3）时合并为一个标签，避免互相遮挡
            for i, m in enumerate(METHODS):
                up_h = uploads[i]
                fetch_h = fetches[i]

                def _fmt_label(h):
                    # 与纵轴刻度（1K/10K/1M，单位 MB）保持同一单位体系
                    return f"{h/1e3:.1f}K" if h >= 1000 else f"{h:.0f}"

                min_h, max_h = min(up_h, fetch_h), max(up_h, fetch_h)
                if min_h > 0 and max_h / min_h < 1.3:
                    # 合并标签，放在两个柱子的中点上方
                    label = _fmt_label(max_h)
                    ax.text(
                        i, max_h * 1.15,
                        label,
                        ha='center', va='bottom',
                        fontsize=FONT_SIZE_VALUE,
                        color='black', fontweight='bold',
                    )
                else:
                    # 分别标注
                    for bar, h in [(bar_up[i], up_h), (bar_fetch[i], fetch_h)]:
                        label = _fmt_label(h)
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            h * 1.15,
                            label,
                            ha='center', va='bottom',
                            fontsize=FONT_SIZE_VALUE,
                            color='black', fontweight='bold',
                        )

            ax.set_xlabel("Algorithm", fontsize=FONT_SIZE_LABEL)
            ax.set_ylabel("Communication Volume (MB)", fontsize=FONT_SIZE_LABEL)
            ax.set_title(f"({chr(ord('a') + DATASETS.index(ds))}) {ds}",
                         fontsize=FONT_SIZE_TITLE)
            ax.set_xticks(x)
            ax.set_xticklabels(METHODS, rotation=30, ha="right", fontsize=FONT_SIZE_TICK)

            # 背景网格线
            ax.grid(True, axis="y", linestyle="--", alpha=0.5)

            # 外框加粗
            for spine in ax.spines.values():
                spine.set_linewidth(SPINE_LW)
            ax.tick_params(axis="both", width=TICK_WIDTH, length=TICK_LENGTH,
                           labelsize=FONT_SIZE_TICK)

            # 子图内部图例
            ax.legend(loc="upper left", fontsize=FONT_SIZE_LEGEND, frameon=True)

        plt.tight_layout()

        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"faceted_log_{theme_name}.{fmt}"
            kwargs = {"bbox_inches": "tight"}
            if fmt == "png":
                kwargs["dpi"] = plotter.dpi
            plt.savefig(fpath, **kwargs)
            print(f"[Saved] {fpath}")

        plt.close(fig)


# ---------------------------------------------------------------------------
# 3. 主入口
# ---------------------------------------------------------------------------
def main():
    p = Plotter(
        style=["science", "grid"],
        output_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "pic"),
        figsize=(6, 4),
        dpi=300,
        use_latex=False,
        font_size=FONT_SIZE_BASE,
    )

    if COLOR_THEME == "all":
        for upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name in COLOR_THEMES:
            print(f"\n>>> Generating theme: {theme_name}")
            _draw_one_theme(upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name, p)
    else:
        found = False
        for upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name in COLOR_THEMES:
            if theme_name == COLOR_THEME:
                _draw_one_theme(upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name, p)
                found = True
                break
        if not found:
            raise ValueError(f"未知配色主题: {COLOR_THEME}，可选: {[t[4] for t in COLOR_THEMES] + ['all']}")

    print("\n绘图完成！图片保存在: plot_experiment/plot_grouped_bar/pic/")


if __name__ == "__main__":
    main()
