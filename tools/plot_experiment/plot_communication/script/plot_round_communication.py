"""
通信量堆叠面积图: 展示 Union / Threshold-0.5 / Top-0.5 三种策略的上传与下载成本
输出: plot_experiment/plot_communication/pic/

使用方式:
    1. 修改下方 【用户配置区】 的 COLOR_THEME、LEGEND_CONFIG、LEGEND_NCOL 等。
    2. 运行: python plot_experiment/plot_communication/script/plot_round_communication.py
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# 路径设置
script_dir = os.path.dirname(os.path.abspath(__file__))
project_tools_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_tools_dir)

from plotter import Plotter

# ---------------------------------------------------------------------------
# 1. 用户配置区（只需改这里）
# ---------------------------------------------------------------------------
ROUNDS = np.arange(1, 51)
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# 三种策略的配置 (Upload 基线, Download 基线, 噪声)
# 通信量大小: Union > Threshold-0.5 > Top-0.5
STRATEGIES = {
    "Union": {
        "upload_base": 15.0,
        "download_base": 12.0,
        "noise": 0.6,
        "title": "(a) Union",
    },
    "Threshold-0.5": {
        "upload_base": 10.0,
        "download_base": 7.0,
        "noise": 0.5,
        "title": "(b) Threshold-0.5",
    },
    "Top-0.5": {
        "upload_base": 8.0,
        "download_base": 6.0,
        "noise": 0.4,
        "title": "(c) Top-0.5",
    },
}

# ===========================================================================
# 配色方案库（修改 COLOR_THEME 变量即可一键切换）
# ===========================================================================
# 可选值:
#   "blue_red"      → 经典蓝红
#   "green_orange"  → 清新绿橙
#   "purple_cyan"   → 优雅紫青
#   "green_yellow"  → 薄荷绿 + 淡黄
#   "all"           → 批量生成全部 4 组配色
COLOR_THEME = "all"

COLOR_THEMES = [
    ("#E31A1C", "#1F78B4", "vibrant_red_blue"),      # 鲜红 + 亮蓝
    ("#33A02C", "#FF7F00", "green_orange"),           # 明绿 + 橙色
    ("#6A3D9A", "#2CA02C", "purple_green"),           # 深紫 + 翠绿
    ("#D62728", "#08519C", "red_cyan"),               # 大红 + 深青
    ("#FF7F0E", "#9467BD", "orange_purple"),          # 橙 + 紫
    ("#E63946", "#2A9D8F", "coral_teal"),             # 珊瑚红 + 青绿
    ("#F4A261", "#264653", "sand_navy"),              # 沙橙 + 海军蓝
    ("#1F77B4", "#D62728", "blue_red"),               # 蓝 + 红
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

# ---- 轴线与刻度线宽 ----
SPINE_LW = 1.8      # 子图边框（轴线）线宽
TICK_WIDTH = 1.5    # 刻度线宽
TICK_LENGTH = 5     # 刻度线长度

# ---- 字体大小配置（可分别独立调节）----
FONT_SIZE_BASE = 16      # 全局基础字号，影响 Plotter 默认
FONT_SIZE_TITLE = 16     # 子图标题字号
FONT_SIZE_LABEL = 16     # X/Y 轴标签字号
FONT_SIZE_TICK = 14      # 坐标轴刻度值字号
FONT_SIZE_LEGEND = 10    # 图例字号

# ---------------------------------------------------------------------------
# 2. 数据生成
# ---------------------------------------------------------------------------

def make_comm_series(upload_base, download_base, noise, n=50):
    """生成带轻微抖动的 Upload / Download 序列。"""
    upload = upload_base + np.random.normal(0, noise, size=n)
    download = download_base + np.random.normal(0, noise, size=n)
    upload = np.clip(upload, 0.5, None)
    download = np.clip(download, 0.5, None)
    return upload, download


data = {}
for name, cfg in STRATEGIES.items():
    up, down = make_comm_series(cfg["upload_base"], cfg["download_base"], cfg["noise"])
    data[name] = {
        "x": ROUNDS.tolist(),
        "Upload": up.tolist(),
        "Download": down.tolist(),
    }


# ---------------------------------------------------------------------------
# 3. 绘图函数
# ---------------------------------------------------------------------------
def _draw_one_theme(upload_color, download_color, theme_name, plotter):
    """绘制并保存某一配色方案的通信量堆叠面积图。"""
    with plt.style.context(plotter.style):
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))

        use_outside = LEGEND_CONFIG.startswith("outside")
        legend_handles = []
        legend_labels = []

        for ax, (name, series) in zip(axes, data.items()):
            x = np.array(series["x"])
            upload = np.array(series["Upload"])
            download = np.array(series["Download"])

            # stackplot 返回的是 PolyCollection 列表，无法直接做 legend handle
            # 所以我们手动创建 proxy artists
            from matplotlib.patches import Patch
            handle_upload = Patch(facecolor=upload_color, edgecolor="black", linewidth=0.3, label="Upload")
            handle_download = Patch(facecolor=download_color, edgecolor="black", linewidth=0.3, label="Download")

            ax.stackplot(
                x,
                upload,
                download,
                labels=["Upload", "Download"],
                colors=[upload_color, download_color],
                alpha=0.9,
                edgecolor="black",
                linewidth=0.3,
            )

            ax.set_xlabel("Round", fontsize=FONT_SIZE_LABEL)
            ax.set_ylabel("Cost (MB)", fontsize=FONT_SIZE_LABEL)
            ax.set_title(STRATEGIES[name]["title"], fontsize=FONT_SIZE_TITLE)
            ax.set_xlim(0, 50)
            ax.set_ylim(0, 35)
            ax.grid(True, linestyle="--", alpha=0.5)

            # 轴线与刻度线加粗
            for spine in ax.spines.values():
                spine.set_linewidth(SPINE_LW)
            ax.tick_params(axis="both", width=TICK_WIDTH, length=TICK_LENGTH,
                           labelsize=FONT_SIZE_TICK)

            # 收集全局图例句柄（仅需一次）
            if use_outside and ax == axes[0]:
                legend_handles = [handle_upload, handle_download]
                legend_labels = ["Upload", "Download"]

            # 子图内部图例
            if not use_outside:
                loc_str = LEGEND_CONFIG.replace("_", " ")
                ax.legend(loc=loc_str, fontsize=FONT_SIZE_LEGEND, frameon=True, ncol=LEGEND_NCOL)

        # 全局图例（图外）
        if use_outside:
            if LEGEND_CONFIG == "outside_bottom_center":
                fig.legend(
                    legend_handles, legend_labels,
                    loc="lower center",
                    ncol=LEGEND_NCOL,
                    bbox_to_anchor=(0.5, -0.02),
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
                plt.tight_layout(rect=[0, 0.06, 1, 1])
            elif LEGEND_CONFIG == "outside_top_center":
                fig.legend(
                    legend_handles, legend_labels,
                    loc="lower center",
                    ncol=LEGEND_NCOL,
                    bbox_to_anchor=(0.5, 1.02),
                    fontsize=FONT_SIZE_LEGEND,
                    frameon=True,
                )
                plt.tight_layout(rect=[0, 0, 1, 0.94])
            else:
                raise ValueError(f"暂不支持的图外位置: {LEGEND_CONFIG}")
        else:
            plt.tight_layout()

        # 保存
        save_dir = plotter.output_dir
        for fmt in ["png", "pdf"]:
            fpath = save_dir / f"round_communication_{theme_name}.{fmt}"
            kwargs = {"bbox_inches": "tight"}
            if fmt == "png":
                kwargs["dpi"] = plotter.dpi
            plt.savefig(fpath, **kwargs)
            print(f"[Saved] {fpath}")

        plt.close(fig)


# ---------------------------------------------------------------------------
# 4. 主入口
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
        for upload_color, download_color, theme_name in COLOR_THEMES:
            print(f"\n>>> Generating theme: {theme_name}")
            _draw_one_theme(upload_color, download_color, theme_name, p)
    else:
        # 查找指定主题
        found = False
        for upload_color, download_color, theme_name in COLOR_THEMES:
            if theme_name == COLOR_THEME:
                _draw_one_theme(upload_color, download_color, theme_name, p)
                found = True
                break
        if not found:
            raise ValueError(f"未知配色主题: {COLOR_THEME}，可选: {[t[2] for t in COLOR_THEMES] + ['all']}")

    print("\n绘图完成！图片保存在: plot_communication/pic/")


if __name__ == "__main__":
    main()
