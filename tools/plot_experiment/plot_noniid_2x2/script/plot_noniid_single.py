#!/usr/bin/env python3
"""
Non-IID 实验单张图生成（SciencePlots 风格）
==========================================
生成 4 张带 (a)-(d) 标签的独立子图，以及每种配色下的单张热力图。

数据来源：accuracy_baseline/{esafl,fedphe,maser,fedavg+ckks,ours}/noneiid_result
输出：tools/plot_experiment/plot_noniid_2x2/pic/
"""

import matplotlib.pyplot as plt

from noniid_common import (
    CUSTOM_RCPARAMS,
    HEATMAP_CMAPS,
    HEATMAP_PANEL_STYLES,
    PLOTTER,
    load_data,
    save_dir,
    draw_line_subplot,
    draw_line_elegant,
    draw_line_smooth_area,
    draw_line_step,
    draw_line_labeled,
    draw_alpha_heatmap,
    draw_heatmap_panel,
)

# 与 Fig.6 单栏面板 (a)(b) 完全一致的画布与边距，保证可以直接并排成一行
PANEL_SIZE = (3.55, 2.95)
PANEL_TITLE_FS = 12.5
PANEL_RCPARAMS = {
    "axes.titlesize": PANEL_TITLE_FS,
    "axes.labelsize": 10.0,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,
    "axes.linewidth": 0.9,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
}
# 面板模式的热力图不画标题以外的角标、不留 (a)/(b)
PANEL_DIR = save_dir / "heatmap_panels"


def main():
    accuracy, alphas = load_data()
    single_size = (7, 5)

    # ------------------------------------------------------------------
    # 4 张独立同尺寸子图（方便 LaTeX 自行组合）
    # ------------------------------------------------------------------
    plot_funcs = [
        ("FMNIST", "line"),
        ("CIFAR-10", "line"),
        ("FMNIST", "heatmap"),
        ("CIFAR-10", "heatmap"),
    ]
    for idx, (ds, kind) in enumerate(plot_funcs):
        with plt.style.context(PLOTTER.style):
            plt.rcParams.update(CUSTOM_RCPARAMS)
            fig_single, ax_single = plt.subplots(figsize=single_size)

            if kind == "line":
                draw_line_subplot(ax_single, ds, accuracy, alphas)
            else:
                draw_alpha_heatmap(ax_single, ds, accuracy, alphas)

            ax_single.set_title(
                f"({chr(97 + idx)}) {ds}",
                fontsize=20,
                fontweight="bold",
                pad=10,
            )

            plt.tight_layout()
            if kind == "heatmap":
                ax_single.grid(False)
            for fmt in ("png", "pdf"):
                fpath = save_dir / f"noniid_2x2_{chr(97 + idx)}.{fmt}"
                plt.savefig(fpath, dpi=300, bbox_inches="tight")
                print(f"[Saved] {fpath}")
            plt.close(fig_single)

    # ------------------------------------------------------------------
    # 多种折线图变体（更具特色、优雅、清晰）
    # ------------------------------------------------------------------
    line_variants = [
        ("elegant",     draw_line_elegant,     "Elegant Open Markers"),
        ("smooth_area", draw_line_smooth_area, "Smooth Area Filled"),
        ("step",        draw_line_step,        "Step Emphasis"),
        ("labeled",     draw_line_labeled,     "Right-End Labels"),
    ]
    for ds in ("FMNIST", "CIFAR-10"):
        for suffix, draw_func, desc in line_variants:
            with plt.style.context(PLOTTER.style):
                plt.rcParams.update(CUSTOM_RCPARAMS)
                fig, ax = plt.subplots(figsize=single_size)
                draw_func(ax, ds, accuracy, alphas)
                # 标题只保留数据集名，风格描述（desc）只用于文件名
                ax.set_title(ds, fontsize=20, fontweight="bold", pad=10)
                plt.tight_layout()
                ds_safe = ds.replace("-", "")
                for fmt in ("png", "pdf"):
                    fpath = save_dir / f"noniid_line_{ds_safe}_{suffix}.{fmt}"
                    plt.savefig(fpath, dpi=300, bbox_inches="tight")
                    print(f"[Saved] {fpath}")
                plt.close(fig)

    # ------------------------------------------------------------------
    # 默认配色单张热力图
    # ------------------------------------------------------------------
    for ds in ("FMNIST", "CIFAR-10"):
        with plt.style.context(PLOTTER.style):
            plt.rcParams.update(CUSTOM_RCPARAMS)
            fig_hm, ax_hm = plt.subplots(figsize=single_size)
            draw_alpha_heatmap(ax_hm, ds, accuracy, alphas)
            ax_hm.set_title(ds, fontsize=20, fontweight="bold", pad=10)
            plt.tight_layout()
            ax_hm.grid(False)
            ds_safe = ds.replace("-", "")
            for fmt in ("png", "pdf"):
                fpath = save_dir / f"noniid_heatmap_{ds_safe}.{fmt}"
                plt.savefig(fpath, dpi=300, bbox_inches="tight")
                print(f"[Saved] {fpath}")
            plt.close(fig_hm)

    # ------------------------------------------------------------------
    # 多种配色方案下的单张热力图
    # ------------------------------------------------------------------
    for theme_name, cmap_name in HEATMAP_CMAPS:
        for ds in ("FMNIST", "CIFAR-10"):
            with plt.style.context(PLOTTER.style):
                plt.rcParams.update(CUSTOM_RCPARAMS)
                fig_hm, ax_hm = plt.subplots(figsize=single_size)
                draw_alpha_heatmap(ax_hm, ds, accuracy, alphas, cmap=cmap_name)
                ax_hm.set_title(ds, fontsize=20, fontweight="bold", pad=10)
                plt.tight_layout()
                ax_hm.grid(False)
                ds_safe = ds.replace("-", "")
                for fmt in ("png", "pdf"):
                    fpath = save_dir / f"noniid_heatmap_{ds_safe}_{theme_name}.{fmt}"
                    plt.savefig(fpath, dpi=300, bbox_inches="tight")
                    print(f"[Saved] {fpath}")
                plt.close(fig_hm)

    # ------------------------------------------------------------------
    # 紧凑热力图面板：尺寸与 Fig.6 的 (a)(b) 单栏图一致，
    # 标题只有数据集名，不带 (a)/(b)/(style) 任何描述，可直接作第 4 个面板
    # ------------------------------------------------------------------
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    for style in HEATMAP_PANEL_STYLES:
        for ds in ("CIFAR-10", "FMNIST"):
            with plt.style.context(PLOTTER.style):
                plt.rcParams.update(PANEL_RCPARAMS)
                fig_p, ax_p = plt.subplots(figsize=PANEL_SIZE)
                fig_p.subplots_adjust(left=0.255, right=0.995,
                                      bottom=0.190, top=0.900)
                draw_heatmap_panel(ax_p, ds, accuracy, alphas, style=style)
                ax_p.set_title(ds, fontsize=PANEL_TITLE_FS,
                               fontweight="bold", pad=5)
                ax_p.grid(False)
                ds_safe = ds.replace("-", "")
                for fmt in ("png", "pdf"):
                    fpath = PANEL_DIR / f"noniid_heatmap_{ds_safe}_{style}.{fmt}"
                    plt.savefig(fpath, dpi=600, bbox_inches="tight",
                                facecolor="white")
                    print(f"[Saved] {fpath}")
                plt.close(fig_p)


if __name__ == "__main__":
    main()
