"""
堆叠柱状图: 四种策略 × CT Upload / CT Fetch / CT Prefetch
模仿参考图风格，带纹理，6 组 SCI 级别配色
输出: plot_experiment/plot_stacked/pic/

使用方式:
    1. 修改下方 【用户配置区】 的 COLOR_THEME、LEGEND_CONFIG、LEGEND_NCOL 等。
    2. 运行: python plot_experiment/plot_stacked/script/plot_stacked_bar.py
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# 路径设置
script_dir = os.path.dirname(os.path.abspath(__file__))
project_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))  # .../tools
sys.path.insert(0, project_tools_dir)

from plotter import Plotter

# ---------------------------------------------------------------------------
# 1. 用户配置区（只需改这里）
# ---------------------------------------------------------------------------
CATEGORIES = ["No Prefetch", "Union", "Threshold-0.5", "Top-0.5"]
LAYERS = ["CT Upload", "CT Fetch", "CT Prefetch"]

# 模拟数据 (单位: 100GB)
# 顺序与 LAYERS 一致: [CT Upload, CT Fetch, CT Prefetch]
VALUES = {
    "No Prefetch":   [3.0, 2.0, 0.0],
    "Union":         [3.5, 2.5, 3.0],
    "Threshold-0.5": [2.5, 1.8, 1.5],
    "Top-0.5":       [2.0, 1.2, 0.8],
}

# 纹理配置（对应参考图风格，增强黑白打印可区分性）
HATCHES = ["", "//", "\\"]  # Upload纯色, Fetch斜线, Prefetch反斜线

# ===========================================================================
# 配色方案库（修改 COLOR_THEME 变量即可一键切换）
# ===========================================================================
# 可选值:
#   "nature"        → 红、青、绿（Nature 风格）
#   "science"       → 深蓝、橙、灰紫
#   "colorblind"    → 蓝、橙红、粉（色盲友好）
#   "highcontrast"  → 深紫蓝、深绿、深红（高对比）
#   "elegant"       → 绿、橙、紫
#   "solid"         → 经典蓝、橙、绿（纯色无纹理）
#   "all"           → 批量生成全部 6 组配色
COLOR_THEME = "all"

COLOR_THEMES = [
    {
        "name": "vibrant",
        "colors": ["#E31A1C", "#1F78B4", "#33A02C"],  # 红、蓝、绿 — 差异极大
        "hatches": ["", "//", "\\"],
    },
    {
        "name": "warm_cool",
        "colors": ["#FF7F00", "#6A3D9A", "#08519C"],  # 橙、紫、深青
        "hatches": ["", "//", "\\"],
    },
    {
        "name": "coral",
        "colors": ["#E63946", "#2A9D8F", "#F4A261"],  # 珊瑚红、青、沙橙
        "hatches": ["", "//", "\\"],
    },
    {
        "name": "bold",
        "colors": ["#D62728", "#1F77B4", "#2CA02C"],  # 大红、蓝、绿
        "hatches": ["", "//", "\\"],
    },
    {
        "name": "earth",
        "colors": ["#8B4513", "#228B22", "#4682B4"],  # 棕、绿、蓝
        "hatches": ["", "//", "\\"],
    },
    {
        "name": "neon",
        "colors": ["#FF0055", "#00CCFF", "#66FF00"],  # 霓虹红、青、绿
        "hatches": ["", "", ""],
    },
]

# ===========================================================================
# 图例方位与列数配置
# ===========================================================================
# LEGEND_CONFIG 控制图例放在哪里，支持两大类：
#
# 【A】全局图例（整幅图级别，所有子图共用同一个图例）
#   "outside_bottom_center"  → 图例放在整幅图正下方（横向排布）
#   "outside_top_center"     → 图例放在整幅图正上方（横向排布）
#
# 【B】子图内独立图例（每个子图各自显示一个图例）
#   "upper_left"   → 子图左上角
#   "upper_right"  → 子图右上角
#   "lower_left"   → 子图左下角
#   "lower_right"  → 子图右下角
#   "best"         → matplotlib 自动找不遮挡数据的最佳位置
#
# 提示：下划线写法与空格写法等价，如 "lower_right" == "lower right"
# ----------------------------------------------------------------------------
# LEGEND_NCOL 控制图例列数：
#   1  → 竖排一列
#   2  → 两列排列
#   3  → 三列排列
# ----------------------------------------------------------------------------
LEGEND_CONFIG = "upper_right"
LEGEND_NCOL = 1

# Y 轴上限（统一刻度，方便对比）
Y_MAX = 10.0

# ---- 轴线与刻度线宽 ----
SPINE_LW = 1.8      # 子图边框（轴线）线宽
TICK_WIDTH = 1.5    # 刻度线宽
TICK_LENGTH = 5     # 刻度线长度

# ---- 字体大小配置（可分别独立调节）----
FONT_SIZE_BASE = 16      # 全局基础字号，影响 Plotter 默认
FONT_SIZE_TITLE = 16     # 子图标题字号
FONT_SIZE_LABEL = 16     # X/Y 轴标签字号
FONT_SIZE_TICK = 14      # 坐标轴刻度值字号
FONT_SIZE_LEGEND = 13    # 图例字号

# ---------------------------------------------------------------------------
# 2. 绘图函数
# ---------------------------------------------------------------------------
def _draw_one_theme(theme, plotter):
    """绘制并保存某一配色方案的堆叠柱状图。"""
    with plt.style.context(plotter.style):
        fig, ax = plt.subplots(figsize=(7, 4.2))

        x = np.arange(len(CATEGORIES))
        width = 0.5
        bottom = np.zeros(len(CATEGORIES))

        for idx, layer in enumerate(LAYERS):
            vals = [VALUES[cat][idx] for cat in CATEGORIES]
            ax.bar(
                x,
                vals,
                width,
                bottom=bottom,
                label=layer,
                color=theme["colors"][idx],
                edgecolor="black",
                linewidth=0.6,
                hatch=theme["hatches"][idx],
                alpha=0.95,
            )
            bottom += np.array(vals)

        ax.set_xlabel("FL Techniques", fontsize=FONT_SIZE_LABEL)
        ax.set_ylabel("Transmission Volume (100GB)", fontsize=FONT_SIZE_LABEL)
        ax.set_xticks(x)
        ax.set_xticklabels(CATEGORIES, fontsize=FONT_SIZE_TICK)
        ax.set_ylim(0, Y_MAX)
        ax.grid(True, axis="y", linestyle="--", alpha=0.5)

        # 轴线与刻度线加粗
        for spine in ax.spines.values():
            spine.set_linewidth(SPINE_LW)
        ax.tick_params(axis="both", width=TICK_WIDTH, length=TICK_LENGTH,
                       labelsize=FONT_SIZE_TICK)

        # 图例
        use_outside = LEGEND_CONFIG.startswith("outside")
        if use_outside:
            if LEGEND_CONFIG == "outside_bottom_center":
                ax.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.12),
                    ncol=LEGEND_NCOL,
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
            elif LEGEND_CONFIG == "outside_top_center":
                ax.legend(
                    loc="lower center",
                    bbox_to_anchor=(0.5, 1.02),
                    ncol=LEGEND_NCOL,
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
            else:
                raise ValueError(f"暂不支持的图外位置: {LEGEND_CONFIG}")
        else:
            loc_str = LEGEND_CONFIG.replace("_", " ")
            ax.legend(loc=loc_str, fontsize=FONT_SIZE_LEGEND, frameon=True, ncol=LEGEND_NCOL)

        plt.tight_layout()

        # 保存
        save_dir = plotter.output_dir
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"stacked_bar_{theme['name']}.{fmt}"
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
        for theme in COLOR_THEMES:
            print(f"\n>>> Generating theme: {theme['name']}")
            _draw_one_theme(theme, p)
    else:
        found = False
        for theme in COLOR_THEMES:
            if theme["name"] == COLOR_THEME:
                _draw_one_theme(theme, p)
                found = True
                break
        if not found:
            raise ValueError(f"未知配色主题: {COLOR_THEME}，可选: {[t['name'] for t in COLOR_THEMES] + ['all']}")

    print("\n绘图完成！图片保存在: plot_experiment/plot_stacked/pic/")


if __name__ == "__main__":
    main()
