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
    PLOTTER,
    load_data,
    save_dir,
    draw_line_subplot,
    draw_line_elegant,
    draw_line_smooth_area,
    draw_line_step,
    draw_line_labeled,
    draw_alpha_heatmap,
)


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
                ax.set_title(f"{ds} ({desc})", fontsize=20, fontweight="bold", pad=10)
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


if __name__ == "__main__":
    main()
