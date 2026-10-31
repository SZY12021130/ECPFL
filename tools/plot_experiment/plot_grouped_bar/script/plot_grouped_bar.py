"""
分组柱状图: 四个数据集 × 五种算法 × CT-Upload / CT-Fetch
高级配色 + 条纹纹理，输出: plot_experiment/plot_grouped_bar/pic/

使用方式:
    1. 修改下方 【用户配置区】 的 COLOR_THEME、LEGEND_CONFIG、LEGEND_NCOL 等。
    2. 运行: python plot_experiment/plot_grouped_bar/script/plot_grouped_bar.py
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
# 1. 用户配置区（只需改这里）
# ---------------------------------------------------------------------------
DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = [
    "ECPFL-TH",
    "FedPHE",
    "ESAFL",
    "MASER",
    "FedAvg-CKKS",
]

# 真实实验数据 (单位: MB)
# 格式: {dataset: {method: [CT-Upload, CT-Fetch]}}
DATA = {
    "MNIST": {
        "ECPFL-TH":     [2183.81, 35.46],
        "FedPHE":       [797.03, 3133.42],
        "ESAFL":        [2390.93, 2390.93],
        "MASER":        [5531.23, 2977.45],
        "FedAvg-CKKS":  [4383.87, 4383.87],
    },
    "FMNIST": {
        "ECPFL-TH":     [414.45, 9.65],
        "FedPHE":       [398.55, 3645.94],
        "ESAFL":        [1992.65, 1992.65],
        "MASER":        [4766.15, 2573.86],
        "FedAvg-CKKS":  [3985.09, 3985.09],
    },
    "CIFAR-10": {
        "ECPFL-TH":     [7587.58, 190.34],
        "FedPHE":       [13548.73, 18960.94],
        "ESAFL":        [13549.24, 13549.24],
        "MASER":        [27066.40, 14839.93],
        "FedAvg-CKKS":  [26699.46, 26699.46],
    },
    "SVHN": {
        "ECPFL-TH":     [19263.73, 298.54],
        "FedPHE":       [23112.74, 32567.46],
        "ESAFL":        [23113.26, 23113.26],
        "MASER":        [46991.57, 25733.91],
        "FedAvg-CKKS":  [45828.08, 45828.08],
    },
}

# 每个子图的 Y 轴上限 (MB)，等差刻度
Y_MAX_PER_DS = {
    "MNIST": 6000,
    "FMNIST": 6000,
    "CIFAR-10": 28000,
    "SVHN": 50000,
}

# ===========================================================================
# 配色方案库（8 组高级配色 + 条纹纹理，修改 COLOR_THEME 即可一键切换）
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
# 图例方位与列数配置
# ===========================================================================
LEGEND_CONFIG = "upper_left"
LEGEND_NCOL = 1

# Y 轴使用线性等差刻度
USE_LOG_SCALE = False

# 高级感边框参数
EDGE_COLOR = "#555555"
EDGE_WIDTH = 0.4
BAR_ALPHA = 0.92

# ---- 轴线与刻度线宽 ----
SPINE_LW = 1.8
TICK_WIDTH = 1.5
TICK_LENGTH = 5

# ---- 字体大小配置 ----
FONT_SIZE_BASE = 18
FONT_SIZE_TITLE = 18
FONT_SIZE_LABEL = 18
FONT_SIZE_TICK = 15
FONT_SIZE_LEGEND = 12

# ---------------------------------------------------------------------------
# 2. 绘图函数
# ---------------------------------------------------------------------------
def _draw_one_theme(upload_color, upload_hatch, fetch_color, fetch_hatch, theme_name, plotter):
    """绘制并保存某一配色方案的分组柱状图。"""
    with plt.style.context(plotter.style):
        fig, axes = plt.subplots(1, 4, figsize=(18, 4.5))
        axes = axes.flatten()

        save_dir = plotter.output_dir
        x = np.arange(len(METHODS))
        width = 0.35

        use_outside = LEGEND_CONFIG.startswith("outside")
        legend_handles = []
        legend_labels = []

        for ax, ds in zip(axes, DATASETS):
            uploads = [DATA[ds][m][0] for m in METHODS]
            fetches = [DATA[ds][m][1] for m in METHODS]

            bar_up = ax.bar(
                x - width / 2,
                uploads,
                width,
                label="CT-Upstream",
                color=upload_color,
                edgecolor=EDGE_COLOR,
                linewidth=EDGE_WIDTH,
                hatch=upload_hatch,
                alpha=BAR_ALPHA,
            )
            bar_fetch = ax.bar(
                x + width / 2,
                fetches,
                width,
                label="CT-Downstream",
                color=fetch_color,
                edgecolor=EDGE_COLOR,
                linewidth=EDGE_WIDTH,
                hatch=fetch_hatch,
                alpha=BAR_ALPHA,
            )

            # 在柱子上方添加数值标签
            # 当上行/下行高度相近（比值 < 1.3）时合并为一个标签，避免互相遮挡
            for i, m in enumerate(METHODS):
                up_h = uploads[i]
                fetch_h = fetches[i]

                def _fmt_label(h):
                    return f"{h:.0f}" if h >= 100 else f"{h:.1f}"

                min_h, max_h = min(up_h, fetch_h), max(up_h, fetch_h)
                if min_h > 0 and max_h / min_h < 1.3:
                    # 合并标签，放在两个柱子的中点上方
                    label = _fmt_label(max_h)
                    ax.text(
                        i, max_h,
                        label,
                        ha='center', va='bottom',
                        fontsize=9, rotation=45,
                    )
                else:
                    # 分别标注
                    for bar, h in [(bar_up[i], up_h), (bar_fetch[i], fetch_h)]:
                        label = _fmt_label(h)
                        ax.text(
                            bar.get_x() + bar.get_width() / 2, h,
                            label,
                            ha='center', va='bottom',
                            fontsize=9, rotation=45,
                        )

            ax.set_xlabel("Algorithm", fontsize=FONT_SIZE_LABEL)
            ax.set_ylabel("Communication Volume (MB)", fontsize=FONT_SIZE_LABEL)
            ax.set_title(f"({chr(ord('a') + DATASETS.index(ds))}) {ds}", fontsize=FONT_SIZE_TITLE)
            ax.set_xticks(x)
            ax.set_xticklabels(METHODS, rotation=30, ha="right", fontsize=FONT_SIZE_TICK)

            if USE_LOG_SCALE:
                ax.set_yscale("log")
                ax.set_ylim(bottom=1, top=5e6)
                # 自定义 Y 轴刻度标签
                ax.set_yticks([1, 10, 100, 1000, 10000, 100000, 1000000])
                ax.set_yticklabels(["1", "10", "100", "1K", "10K", "100K", "1M"], fontsize=FONT_SIZE_TICK)
            else:
                # 使用每个数据集独立的上限，等差刻度
                y_max = Y_MAX_PER_DS.get(ds, 500)
                ax.set_ylim(0, y_max)
                # 等差刻度：0, y_max/4, y_max/2, 3*y_max/4, y_max
                y_ticks = [0, y_max/4, y_max/2, 3*y_max/4, y_max]
                ax.set_yticks(y_ticks)
                ax.set_yticklabels([f"{t:.0f}" for t in y_ticks], fontsize=FONT_SIZE_TICK)

            ax.grid(True, axis="y", linestyle="--", alpha=0.5)

            # 轴线与刻度线加粗
            for spine in ax.spines.values():
                spine.set_linewidth(SPINE_LW)
            ax.tick_params(axis="both", width=TICK_WIDTH, length=TICK_LENGTH,
                           labelsize=FONT_SIZE_TICK)

            # 收集全局图例句柄（仅需一次）
            if use_outside and ax == axes[0]:
                legend_handles = [bar_up, bar_fetch]
                legend_labels = ["CT-Upload", "CT-Fetch"]

            # 子图内部图例
            if not use_outside:
                loc_str = LEGEND_CONFIG.replace("_", " ")
                ax.legend(loc=loc_str, fontsize=FONT_SIZE_LEGEND, frameon=True, ncol=LEGEND_NCOL)

        # 全局图例（图外）
        if use_outside:
            if LEGEND_CONFIG == "outside_bottom_center":
                fig.legend(
                    legend_handles, legend_labels,
                    loc="upper center",
                    ncol=LEGEND_NCOL,
                    bbox_to_anchor=(0.5, -0.02),
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
                plt.tight_layout()
                plt.subplots_adjust(bottom=0.16)
            elif LEGEND_CONFIG == "outside_top_center":
                fig.legend(
                    legend_handles, legend_labels,
                    loc="lower center",
                    ncol=LEGEND_NCOL,
                    bbox_to_anchor=(0.5, 1.02),
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
                plt.tight_layout()
                plt.subplots_adjust(top=0.88)
            else:
                raise ValueError(f"暂不支持的图外位置: {LEGEND_CONFIG}")
        else:
            plt.tight_layout()

        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"grouped_bar_{theme_name}.{fmt}"
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
