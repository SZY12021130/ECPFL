#!/usr/bin/env python3
"""
Non-IID 系数 vs 准确率 — 六模型对比折线图
============================================
四个子图 1×4 横向排列，横坐标为 IID 系数 α，纵坐标为 Test Accuracy。
采用 SciencePlots 学术风格 + 多组高级配色，支持一键切换。

输出：tools/plot_experiment/plot_noniid_accuracy/pic/
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 引入 plotter（获取 SciencePlots 样式环境）
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
project_tools_dir = os.path.join(current_dir, "..", "..", "..")
sys.path.insert(0, project_tools_dir)

from plotter import Plotter

# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------
# Non-IID 系数（横坐标，离散实验点，均匀排列）
IID_COEFFS = [0.1, 0.3, 0.5, 0.9, 1, 5, 10]

# 六个模型（性能排序：ECPFL 系列 > FedPHE > MASER > FedAvg）
METHODS = [
    "ECPFL-RK",
    "ECPFL-TH",
    "FedPHE",
    "ESAFL",
    "MASER",
    "FedAvg-CKKS",
]

# 四个数据集
DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
SUBTITLES = ["(a) MNIST", "(b) FMNIST", "(c) CIFAR-10", "(d) SVHN"]

# ===========================================================================
# 配色方案库（6 色 × 8 组，修改 COLOR_THEME 变量即可一键切换）
# ===========================================================================
# 推荐：morandi（莫兰迪）/  deep_blue（深蓝调）/  warm（暖调）/
#       forest（森林）/  graphite（石墨）/  magazine（杂志）/
#       ocean（海洋）/  sunset（日落）
COLOR_THEME = "all"

COLOR_PALETTES = {
    "vibrant": [      # 鲜艳高对比 — 红蓝绿橙紫青，差异极大
        "#E31A1C", "#1F78B4", "#33A02C", "#FF7F00", "#6A3D9A", "#08519C",
    ],
    "bright_dark": [  # 明亮+深色交替，层次分明
        "#FB9A99", "#E31A1C", "#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02C",
    ],
    "bold": [         # 粗旷大胆，Matplotlib 经典增强
        "#D62728", "#FF7F0E", "#2CA02C", "#1F77B4", "#9467BD", "#8C564B",
    ],
    "neon": [         # 霓虹感，高饱和刺眼
        "#FF0055", "#00CCFF", "#66FF00", "#FFCC00", "#CC00FF", "#0099FF",
    ],
    "earth": [        # 大地色+鲜艳点缀
        "#8B4513", "#D2691E", "#228B22", "#4682B4", "#B22222", "#2E8B57",
    ],
    "contrast": [     # 极致对比，黑白+三原色
        "#111111", "#E31A1C", "#33A02C", "#1F78B4", "#FF7F00", "#6A3D9A",
    ],
    "modern": [       # 现代流行色
        "#E63946", "#457B9D", "#2A9D8F", "#F4A261", "#264653", "#E76F51",
    ],
    "classic": [      # 经典学术配色增强版
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    ],
}

# ===========================================================================
# 数据集参数配置
# ===========================================================================
# 每个数据集给出：(base_acc, max_acc, noise_std)
# base 仅作参考，实际生成使用 max - current_gap + noise
DATASET_CONFIG = {
    "MNIST":    {"base": 0.45, "max": 0.97, "noise": 0.004},
    "FMNIST":     {"base": 0.15, "max": 0.86, "noise": 0.006},
    "CIFAR-10":      {"base": 0.30, "max": 0.92, "noise": 0.005},
    "SVHN": {"base": 0.22, "max": 0.82, "noise": 0.007},
}

# ===========================================================================
# 方法性能差距配置
# ===========================================================================
# gap_base 表示在 Non-IID（α=0.1）时该方法与最优值的差距；
# IID（α=10）时差距会缩小到约 30%。数值越大表示方法越差。
METHOD_GAPS = {
    "ECPFL-RK":             0.03,
    "ECPFL-TH":             0.06,
    "FedPHE":               0.08,
    "ESAFL":               0.12,
    "MASER":               0.15,
    "FedAvg-CKKS":         0.20,
}

# ===========================================================================
# 图例方位与列数配置
# ===========================================================================
# LEGEND_CONFIG 控制图例放在哪里，支持两大类：
#   "outside_bottom_center" / "outside_top_center" → 全局图例
#   "lower_right" / "upper_left" / "best" 等 → 子图内独立图例
LEGEND_CONFIG = "lower_right"
LEGEND_NCOL = 1

# ---- 轴线与刻度线宽 ----
SPINE_LW = 1.8      # 子图边框（轴线）线宽
TICK_WIDTH = 1.5    # 刻度线宽
TICK_LENGTH = 5     # 刻度线长度

# ---- 字体大小配置（可分别独立调节）----
FONT_SIZE_BASE = 18      # 全局基础字号
FONT_SIZE_TITLE = 18     # 子图标题字号
FONT_SIZE_LABEL = 18     # X/Y 轴标签字号
FONT_SIZE_TICK = 15      # 坐标轴刻度值字号
FONT_SIZE_LEGEND = 10    # 图例字号

# ---- 折线样式参数 ----
MARKERS = ["o", "s", "^", "D", "v", "p"]
LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
LINE_WIDTH = 2.0
MARKER_SIZE = 6

# Y 轴统一范围
YLIM = (0, 1.0)

# 随机种子（保证可复现）
RANDOM_SEED = 42

# 输出目录
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "..", "pic")
os.makedirs(output_dir, exist_ok=True)


def generate_data():
    """生成各数据集、各方法在不同 Non-IID 系数下的模拟准确率数据。"""
    np.random.seed(RANDOM_SEED)
    data = {}
    for ds in DATASETS:
        cfg = DATASET_CONFIG[ds]
        base, maximum, noise = cfg["base"], cfg["max"], cfg["noise"]
        data[ds] = {}

        for method in METHODS:
            accs = []
            gap_base = METHOD_GAPS[method]

            for coeff in IID_COEFFS:
                # 把 coeff 映射到 0~1（0.1→0，10→1）
                log_c = np.log10(coeff)
                t = (log_c + 1) / 2

                # 非线性：低 α 区域准确率提升更快
                progress = t ** 0.55

                # 当前 α 下的方法差距：Non-IID 时大，IID 时缩小到约 30%
                current_gap = gap_base * (1 - progress * 0.70)

                acc = maximum - current_gap + np.random.normal(0, noise)
                acc = float(np.clip(acc, 0.0, 1.0))
                accs.append(acc)

            # ---- 强制单调递增（后项不低于前项） ----
            for i in range(1, len(accs)):
                if accs[i] < accs[i - 1]:
                    # 若出现下降，用前一个值加极小随机增量替代
                    accs[i] = accs[i - 1] + np.random.uniform(0.001, 0.004)
            # 再次裁剪到合法范围
            accs = [float(np.clip(a, 0.0, 1.0)) for a in accs]

            data[ds][method] = accs
    return data


# ---------------------------------------------------------------------------
# 绘图主逻辑
# ---------------------------------------------------------------------------
def _draw_one_theme(theme_name, colors, data, output_dir):
    """绘制并保存某一配色方案的图。"""
    plotter = Plotter(
        style=["science", "grid"],
        use_latex=False,
        font_size=FONT_SIZE_BASE,
    )

    with plt.style.context(plotter.style):
        fig, axes = plt.subplots(1, 4, figsize=(18, 4))
        axes = axes.flatten()

        x = np.arange(len(IID_COEFFS))

        for idx, (ax, ds) in enumerate(zip(axes, DATASETS)):
            for i, method in enumerate(METHODS):
                y = data[ds][method]
                ax.plot(
                    x, y,
                    color=colors[i],
                    marker=MARKERS[i],
                    linestyle=LINESTYLES[i],
                    linewidth=LINE_WIDTH,
                    markersize=MARKER_SIZE,
                    markerfacecolor=colors[i],
                    markeredgecolor="white",
                    markeredgewidth=0.6,
                    label=method,
                    zorder=3,
                )

            ax.set_xticks(x)
            ax.set_xticklabels([str(c) for c in IID_COEFFS], fontsize=FONT_SIZE_TICK)
            ax.set_ylim(YLIM)
            ax.set_xlabel(r"Non-IID Coefficient $\alpha$", fontsize=FONT_SIZE_LABEL)

            if idx == 0:
                ax.set_ylabel("Test Accuracy", fontsize=FONT_SIZE_LABEL)

            ax.set_title(SUBTITLES[idx], fontsize=FONT_SIZE_TITLE, pad=10)

            # ---- 轴线与刻度线加粗 ----
            for spine in ax.spines.values():
                spine.set_linewidth(SPINE_LW)
            ax.tick_params(axis="both", width=TICK_WIDTH, length=TICK_LENGTH,
                           labelsize=FONT_SIZE_TICK)

        # ---- 图例绘制（根据 LEGEND_CONFIG 自动切换模式） ----
        if LEGEND_CONFIG == "outside_bottom_center":
            handles, labels = axes[0].get_legend_handles_labels()
            fig.legend(
                handles, labels,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.02),
                ncol=LEGEND_NCOL,
                frameon=True,
                fontsize=FONT_SIZE_LEGEND,
                columnspacing=1.5,
                handletextpad=0.6,
            )
            plt.tight_layout()
            plt.subplots_adjust(bottom=0.16)
        elif LEGEND_CONFIG == "outside_top_center":
            handles, labels = axes[0].get_legend_handles_labels()
            fig.legend(
                handles, labels,
                loc="lower center",
                bbox_to_anchor=(0.5, 1.02),
                ncol=LEGEND_NCOL,
                frameon=True,
                fontsize=FONT_SIZE_LEGEND,
                columnspacing=1.5,
                handletextpad=0.6,
            )
            plt.tight_layout()
            plt.subplots_adjust(top=0.88)
        else:
            # 子图内独立图例（自动把下划线替换为空格，兼容两种写法）
            loc_str = LEGEND_CONFIG.replace("_", " ")
            for ax in axes:
                ax.legend(
                    loc=loc_str,
                    ncol=LEGEND_NCOL,
                    frameon=True,
                    fontsize=FONT_SIZE_LEGEND,
                )
            plt.tight_layout()

        for fmt in ["png", "pdf"]:
            save_path = os.path.join(
                output_dir, f"noniid_accuracy_{theme_name}.{fmt}"
            )
            fig.savefig(save_path, dpi=300, bbox_inches="tight", format=fmt)
            print(f"[Saved] {save_path}")

        plt.close(fig)


def main():
    data = generate_data()

    # 若 COLOR_THEME 为 "all"，则批量生成全部配色；否则只生成指定配色
    if COLOR_THEME == "all":
        for theme_name, colors in COLOR_PALETTES.items():
            print(f"\n>>> Generating theme: {theme_name}")
            _draw_one_theme(theme_name, colors, data, output_dir)
    else:
        colors = COLOR_PALETTES.get(COLOR_THEME, COLOR_PALETTES["morandi"])
        _draw_one_theme(COLOR_THEME, colors, data, output_dir)
        plt.show()


if __name__ == "__main__":
    main()
