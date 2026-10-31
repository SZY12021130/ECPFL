"""
生成 IEEE 双栏格式的多数据集对比表格（LaTeX + 4 种风格）
=========================================================

核心输出：可直接编译的 LaTeX 代码 + PDF
风格切换：修改脚本顶部 TABLE_STYLE 变量

使用方式:
    python table_experiment/script/generate_table.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ---------------------------------------------------------------------------
# 0. 路径
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
TABLE_DIR = SCRIPT_DIR.parent
TEX_DIR = TABLE_DIR / "tex"
PIC_DIR = TABLE_DIR / "pic"
TEX_DIR.mkdir(parents=True, exist_ok=True)
PIC_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. 用户配置
# ---------------------------------------------------------------------------
TABLE_STYLE = "classic_bars"   # classic_bars / booktabs_only / modern_minimal / color_groups

METHODS = [
    "FedAvg", "FedProx", "SCAFFOLD", "FedNova",
    "FedOpt", "MOON", "FedDyn", "Per-FedAvg",
    "pFedMe", "Ditto", "APFL", "FedRep",
    "FedPer", "LG-FedAvg", "FedBABU", "kNN-Per",
]

DATASETS = [
    ("FEMNIST", "75%"),
    ("Google Speech", "61%"),
    ("OpenImage", "68%"),
]

METRICS = ["FT", "TT", "FV", "TV"]

RAW_DATA = {
    "FedAvg":     [[0.64,2.56,1.56,2.76],[5.54,21.7,12.2,21.6],[1.14,5.40,10.8,19.1]],
    "FedProx":    [[0.85,2.46,2.58,3.07],[9.96,25.0,13.7,18.0],[0.97,4.47,11.5,15.0]],
    "SCAFFOLD":   [[0.21,1.67,1.31,3.14],[2.71,13.4,10.4,21.6],[0.44,4.00,8.85,18.1]],
    "FedNova":    [[0.30,2.11,2.58,3.32],[2.28,16.7,12.9,18.9],[0.38,2.55,14.0,20.7]],
    "FedOpt":     [[0.18,1.84,1.49,4.01],[1.26,14.3,11.2,25.0],[0.23,2.36,8.84,24.6]],
    "MOON":       [[0.46,1.35,1.56,1.73],[3.41,8.62,10.49,11.6],[0.72,3.68,10.8,12.0]],
    "FedDyn":     [[0.06,0.90,0.58,1.83],[0.84,6.26,4.87,14.3],[0.13,3.07,4.45,13.7]],
    "Per-FedAvg": [[0.43,1.27,1.45,1.60],[3.03,10.9,10.78,11.9],[0.67,3.55,10.4,11.6]],
    "pFedMe":     [[0.06,0.90,0.58,1.83],[0.58,8.88,4.70,14.7],[0.12,3.09,4.34,13.7]],
    "Ditto":      [[0.42,1.26,1.43,1.60],[4.02,12.7,11.7,13.7],[0.74,3.54,10.2,11.7]],
    "APFL":       [[0.06,0.89,0.60,1.75],[1.12,10.1,6.92,16.5],[0.16,3.12,5.48,14.1]],
    "FedRep":     [[1.49,4.23,5.25,5.62],[6.87,26.7,28.1,29.8],[0.58,2.81,8.01,9.24]],
    "FedPer":     [[0.14,3.02,1.47,6.54],[0.67,21.0,6.89,35.5],[0.11,2.43,4.28,11.0]],
    "LG-FedAvg":  [[0.04,0.96,0.13,0.72],[0.48,8.79,1.45,6.97],[0.12,3.26,1.15,5.52]],
    "FedBABU":    [[0.04,0.93,0.28,0.56],[0.50,8.47,2.95,6.02],[0.12,2.87,2.50,5.38]],
    "kNN-Per":    [[0.03,0.85,0.20,0.65],[0.42,7.80,1.30,6.20],[0.10,2.60,1.00,5.00]],
}

# ---------------------------------------------------------------------------
# 2. 最佳值自动标记
# ---------------------------------------------------------------------------
def find_best_values():
    n_datasets = len(DATASETS)
    n_metrics = len(METRICS)
    best = {m: [[False]*n_metrics for _ in range(n_datasets)] for m in METHODS}
    for di in range(n_datasets):
        for ci in range(n_metrics):
            col_vals = [RAW_DATA[m][di][ci] for m in METHODS]
            min_val = min(col_vals)
            for method in METHODS:
                if abs(RAW_DATA[method][di][ci] - min_val) < 1e-6:
                    best[method][di][ci] = True
    return best


BEST_MASK = find_best_values()


# ---------------------------------------------------------------------------
# 3. LaTeX 源码生成（同时输出片段 + 完整可编译文档）
# ---------------------------------------------------------------------------
def generate_latex():
    n_ds = len(DATASETS)
    n_met = len(METRICS)

    # ---- 列格式 ----
    if TABLE_STYLE in ("classic_bars", "color_groups"):
        col_spec = "l|" + "|".join(["r" * n_met for _ in range(n_ds)]) + "|"
    else:
        col_spec = "l" + "r" * (n_ds * n_met)

    # ---- 表格内容 ----
    table_lines = []
    table_lines.append(r"\begin{table}[t]")
    table_lines.append(r"\centering")
    table_lines.append(r"\caption{Performance Comparison on Three Datasets}")
    table_lines.append(r"\label{tab:main-result}")
    table_lines.append(r"\footnotesize")
    table_lines.append("")

    table_lines.append(r"\begin{tabular}{" + col_spec + "}")
    table_lines.append(r"\toprule")

    # 第一层分组表头
    header1_parts = []
    for ds_name, trg in DATASETS:
        header1_parts.append(
            r"\multicolumn{4}{c}{\textit{" + ds_name + r"} Trg " + trg.replace("%", r"\%") + r"}"
        )
    table_lines.append(" & ".join([""] + header1_parts) + r" \\")

    # 分组表头下方 \cmidrule
    cmidrule_parts = []
    for di in range(n_ds):
        start_col = 2 + di * n_met
        end_col = start_col + n_met - 1
        cmidrule_parts.append(r"\cmidrule(lr){" + f"{start_col}-{end_col}" + r"}")
    table_lines.append(" ".join(cmidrule_parts))

    # 第二层指标表头
    header2 = [""] + METRICS * n_ds
    table_lines.append(" & ".join(header2) + r" \\")

    # 指标表头下方 \cmidrule
    cmidrule_parts2 = []
    for di in range(n_ds):
        start_col = 2 + di * n_met
        end_col = start_col + n_met - 1
        cmidrule_parts2.append(r"\cmidrule(lr){" + f"{start_col}-{end_col}" + r"}")
    table_lines.append(" ".join(cmidrule_parts2))

    # 数据行
    for ri, method in enumerate(METHODS):
        row_parts = [method]
        for di in range(n_ds):
            for ci in range(n_met):
                val = RAW_DATA[method][di][ci]
                if BEST_MASK[method][di][ci]:
                    row_parts.append(r"\textbf{" + f"{val:.2f}" + r"}")
                else:
                    row_parts.append(f"{val:.2f}")

        if TABLE_STYLE == "modern_minimal" and ri % 2 == 1:
            table_lines.append(r"\rowcolor{gray!10} " + " & ".join(row_parts) + r" \\")
        else:
            table_lines.append(" & ".join(row_parts) + r" \\")

    table_lines.append(r"\bottomrule")
    table_lines.append(r"\end{tabular}")
    table_lines.append(r"\end{table}")

    # ---- 保存片段版（插入论文用）----
    snippet_lines = [
        r"% 请将以下代码放入 IEEEtran 文档的 table 环境中",
        r"% \usepackage{booktabs}  % 需要 booktabs 宏包",
        "",
    ] + table_lines
    snippet_path = TEX_DIR / "table_main.tex"
    snippet_path.write_text("\n".join(snippet_lines), encoding="utf-8")
    print(f"[LaTeX 片段] 已生成: {snippet_path}")

    # ---- 保存完整版（可直接编译预览）----
    full_lines = []
    full_lines.append(r"\documentclass[conference]{IEEEtran}")
    full_lines.append(r"\usepackage{booktabs}")
    if TABLE_STYLE in ("modern_minimal", "color_groups"):
        full_lines.append(r"\usepackage[table]{xcolor}")
    full_lines.append(r"\usepackage{caption}")
    full_lines.append(r"\usepackage{graphicx}")
    full_lines.append(r"\begin{document}")
    full_lines.append(r"\onecolumn")
    full_lines.append(r"\begin{center}")
    full_lines.append(r"\Large\textbf{Table Preview -- Style: " + TABLE_STYLE.replace("_", " ").title() + r"}")
    full_lines.append(r"\end{center}")
    full_lines.append(r"\vspace{1em}")

    if TABLE_STYLE == "modern_minimal":
        full_lines.append(r"\rowcolors{2}{gray!10}{white}")

    full_lines.extend(table_lines)
    full_lines.append(r"\end{document}")

    full_path = TEX_DIR / "table_full.tex"
    full_path.write_text("\n".join(full_lines), encoding="utf-8")
    print(f"[LaTeX 完整版] 已生成: {full_path}")

    return snippet_path, full_path


# ---------------------------------------------------------------------------
# 4. matplotlib 图片版（4 种风格统一入口）
# ---------------------------------------------------------------------------
def generate_image():
    n_rows = len(METHODS)
    n_ds = len(DATASETS)
    n_met = len(METRICS)
    n_data_cols = n_ds * n_met

    cell_w_method = 2.2
    cell_w_data = 1.1
    cell_h = 0.55
    header_h = 0.55
    group_header_h = 0.55
    top_margin = 0.3
    bottom_margin = 0.3
    left_margin = 0.5
    right_margin = 0.5

    fig_w = left_margin + cell_w_method + n_data_cols * cell_w_data + right_margin
    fig_h = top_margin + group_header_h + header_h + n_rows * cell_h + bottom_margin

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    def draw_line(x1, y1, x2, y2, lw=1.0, color="black"):
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, solid_capstyle="butt")

    def draw_text(x, y, text, ha="center", va="center", fontsize=9, weight="normal",
                  style="normal", color="black"):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fontsize, weight=weight,
                style=style, color=color)

    y_top = fig_h - top_margin
    y_group_bottom = y_top - group_header_h
    y_header_bottom = y_group_bottom - header_h
    y_data_top = y_header_bottom
    y_data_bottom = y_data_top - n_rows * cell_h

    x_start = left_margin
    x_method_right = x_start + cell_w_method
    x_col_rights = [x_method_right + i * cell_w_data for i in range(n_data_cols + 1)]
    x_group_bounds = [x_method_right + di * n_met * cell_w_data for di in range(n_ds + 1)]

    if TABLE_STYLE == "classic_bars":
        _draw_classic(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                      x_start, x_method_right, x_col_rights, x_group_bounds,
                      y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                      cell_w_method, cell_w_data, cell_h)
    elif TABLE_STYLE == "booktabs_only":
        _draw_booktabs(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                       x_start, x_method_right, x_col_rights,
                       y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                       cell_w_method, cell_w_data, cell_h)
    elif TABLE_STYLE == "modern_minimal":
        _draw_minimal(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                      x_start, x_method_right, x_col_rights,
                      y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                      cell_w_method, cell_w_data, cell_h)
    elif TABLE_STYLE == "color_groups":
        _draw_color_groups(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                           x_start, x_method_right, x_col_rights, x_group_bounds,
                           y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                           cell_w_method, cell_w_data, cell_h)

    plt.tight_layout(pad=0.2)
    for fmt in ["pdf", "png"]:
        fpath = PIC_DIR / f"table_{TABLE_STYLE}.{fmt}"
        kwargs = {"bbox_inches": "tight", "pad_inches": 0.05}
        if fmt == "png":
            kwargs["dpi"] = 300
        plt.savefig(fpath, **kwargs)
        print(f"[Image] 已生成: {fpath}")
    plt.close(fig)


def _draw_classic(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                  x_start, x_method_right, x_col_rights, x_group_bounds,
                  y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                  cell_w_method, cell_w_data, cell_h):
    rect = Rectangle((x_start, y_group_bottom), x_col_rights[-1] - x_start,
                     y_top - y_group_bottom, facecolor="#FDF5E6", edgecolor="none", zorder=0)
    ax.add_patch(rect)
    rect = Rectangle((x_start, y_header_bottom), x_col_rights[-1] - x_start,
                     y_group_bottom - y_header_bottom, facecolor="#F0F0F0", edgecolor="none", zorder=0)
    ax.add_patch(rect)

    for di, (ds_name, trg) in enumerate(DATASETS):
        x_left, x_right = x_group_bounds[di], x_group_bounds[di + 1]
        draw_text((x_left + x_right) / 2, (y_top + y_group_bottom) / 2,
                  f"{ds_name} Trg {trg}", fontsize=10, weight="bold", style="italic")

    for ci in range(n_ds * n_met):
        x_left, x_right = x_col_rights[ci], x_col_rights[ci + 1]
        draw_text((x_left + x_right) / 2, (y_group_bottom + y_header_bottom) / 2,
                  METRICS[ci % n_met], fontsize=9, weight="bold")

    for ri, method in enumerate(METHODS):
        y_center = y_data_top - (ri + 0.5) * cell_h
        draw_text(x_start + 0.1, y_center, method, ha="left", va="center", fontsize=9, weight="bold")
        for di in range(n_ds):
            for ci in range(n_met):
                col_idx = di * n_met + ci
                x_center = (x_col_rights[col_idx] + x_col_rights[col_idx + 1]) / 2
                val = RAW_DATA[method][di][ci]
                is_best = BEST_MASK[method][di][ci]
                draw_text(x_center, y_center, f"{val:.2f}", fontsize=9,
                          weight="bold" if is_best else "normal",
                          color="black" if is_best else "#333333")

    # 横线
    draw_line(x_start, y_top, x_col_rights[-1], y_top, lw=2.0)
    draw_line(x_start, y_data_bottom, x_col_rights[-1], y_data_bottom, lw=2.0)
    for di in range(n_ds):
        draw_line(x_group_bounds[di], y_group_bottom, x_group_bounds[di + 1], y_group_bottom, lw=1.2)
        draw_line(x_group_bounds[di], y_header_bottom, x_group_bounds[di + 1], y_header_bottom, lw=1.2)

    # 连贯竖线
    draw_line(x_start, y_top, x_start, y_data_bottom, lw=1.0)
    draw_line(x_method_right, y_top, x_method_right, y_data_bottom, lw=1.0)
    for ci in range(1, n_ds * n_met):
        draw_line(x_col_rights[ci], y_top, x_col_rights[ci], y_data_bottom, lw=0.6)
    draw_line(x_col_rights[-1], y_top, x_col_rights[-1], y_data_bottom, lw=1.0)
    for di in range(1, n_ds):
        draw_line(x_group_bounds[di], y_top, x_group_bounds[di], y_data_bottom, lw=1.5)


def _draw_booktabs(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                   x_start, x_method_right, x_col_rights,
                   y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                   cell_w_method, cell_w_data, cell_h):
    for di, (ds_name, trg) in enumerate(DATASETS):
        x_left = x_method_right + di * n_met * cell_w_data
        x_right = x_left + n_met * cell_w_data
        draw_text((x_left + x_right) / 2, (y_top + y_group_bottom) / 2,
                  f"{ds_name} Trg {trg}", fontsize=10, weight="bold", style="italic")

    for ci in range(n_ds * n_met):
        x_left, x_right = x_col_rights[ci], x_col_rights[ci + 1]
        draw_text((x_left + x_right) / 2, (y_group_bottom + y_header_bottom) / 2,
                  METRICS[ci % n_met], fontsize=9, weight="bold")

    for ri, method in enumerate(METHODS):
        y_center = y_data_top - (ri + 0.5) * cell_h
        draw_text(x_start + 0.1, y_center, method, ha="left", va="center", fontsize=9, weight="bold")
        for di in range(n_ds):
            for ci in range(n_met):
                col_idx = di * n_met + ci
                x_center = (x_col_rights[col_idx] + x_col_rights[col_idx + 1]) / 2
                val = RAW_DATA[method][di][ci]
                is_best = BEST_MASK[method][di][ci]
                draw_text(x_center, y_center, f"{val:.2f}", fontsize=9,
                          weight="bold" if is_best else "normal",
                          color="black" if is_best else "#333333")

    draw_line(x_start, y_top, x_col_rights[-1], y_top, lw=2.0)
    draw_line(x_start, y_group_bottom, x_col_rights[-1], y_group_bottom, lw=1.2)
    draw_line(x_start, y_header_bottom, x_col_rights[-1], y_header_bottom, lw=1.2)
    draw_line(x_start, y_data_bottom, x_col_rights[-1], y_data_bottom, lw=2.0)


def _draw_minimal(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                  x_start, x_method_right, x_col_rights,
                  y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                  cell_w_method, cell_w_data, cell_h):
    rect = Rectangle((x_start, y_header_bottom), x_col_rights[-1] - x_start,
                     y_top - y_header_bottom, facecolor="#F5F5F5", edgecolor="none", zorder=0)
    ax.add_patch(rect)

    for di, (ds_name, trg) in enumerate(DATASETS):
        x_left = x_method_right + di * n_met * cell_w_data
        x_right = x_left + n_met * cell_w_data
        draw_text((x_left + x_right) / 2, (y_top + y_group_bottom) / 2,
                  f"{ds_name} Trg {trg}", fontsize=10, weight="bold", style="italic")

    for ci in range(n_ds * n_met):
        x_left, x_right = x_col_rights[ci], x_col_rights[ci + 1]
        draw_text((x_left + x_right) / 2, (y_group_bottom + y_header_bottom) / 2,
                  METRICS[ci % n_met], fontsize=9, weight="bold")

    for ri, method in enumerate(METHODS):
        y_bottom = y_data_top - (ri + 1) * cell_h
        y_center = y_data_top - (ri + 0.5) * cell_h
        if ri % 2 == 1:
            rect = Rectangle((x_start, y_bottom), x_col_rights[-1] - x_start,
                             cell_h, facecolor="#FAFAFA", edgecolor="none", zorder=0)
            ax.add_patch(rect)
        draw_text(x_start + 0.1, y_center, method, ha="left", va="center", fontsize=9, weight="bold")
        for di in range(n_ds):
            for ci in range(n_met):
                col_idx = di * n_met + ci
                x_center = (x_col_rights[col_idx] + x_col_rights[col_idx + 1]) / 2
                val = RAW_DATA[method][di][ci]
                is_best = BEST_MASK[method][di][ci]
                draw_text(x_center, y_center, f"{val:.2f}", fontsize=9,
                          weight="bold" if is_best else "normal",
                          color="black" if is_best else "#333333")

    draw_line(x_start, y_top, x_col_rights[-1], y_top, lw=2.0)
    draw_line(x_start, y_data_bottom, x_col_rights[-1], y_data_bottom, lw=2.0)


def _draw_color_groups(ax, draw_line, draw_text, n_rows, n_ds, n_met,
                       x_start, x_method_right, x_col_rights, x_group_bounds,
                       y_top, y_group_bottom, y_header_bottom, y_data_top, y_data_bottom,
                       cell_w_method, cell_w_data, cell_h):
    group_colors = ["#FFF8E1", "#E8F5E9", "#E3F2FD"]
    for di in range(n_ds):
        x_left, x_right = x_group_bounds[di], x_group_bounds[di + 1]
        rect = Rectangle((x_left, y_data_bottom), x_right - x_left,
                         y_top - y_data_bottom, facecolor=group_colors[di % len(group_colors)],
                         edgecolor="none", zorder=0, alpha=0.35)
        ax.add_patch(rect)

    for di, (ds_name, trg) in enumerate(DATASETS):
        x_left, x_right = x_group_bounds[di], x_group_bounds[di + 1]
        draw_text((x_left + x_right) / 2, (y_top + y_group_bottom) / 2,
                  f"{ds_name} Trg {trg}", fontsize=10, weight="bold", style="italic")

    for ci in range(n_ds * n_met):
        x_left, x_right = x_col_rights[ci], x_col_rights[ci + 1]
        draw_text((x_left + x_right) / 2, (y_group_bottom + y_header_bottom) / 2,
                  METRICS[ci % n_met], fontsize=9, weight="bold")

    for ri, method in enumerate(METHODS):
        y_center = y_data_top - (ri + 0.5) * cell_h
        draw_text(x_start + 0.1, y_center, method, ha="left", va="center", fontsize=9, weight="bold")
        for di in range(n_ds):
            for ci in range(n_met):
                col_idx = di * n_met + ci
                x_center = (x_col_rights[col_idx] + x_col_rights[col_idx + 1]) / 2
                val = RAW_DATA[method][di][ci]
                is_best = BEST_MASK[method][di][ci]
                draw_text(x_center, y_center, f"{val:.2f}", fontsize=9,
                          weight="bold" if is_best else "normal",
                          color="black" if is_best else "#333333")

    draw_line(x_start, y_top, x_col_rights[-1], y_top, lw=2.0)
    draw_line(x_start, y_data_bottom, x_col_rights[-1], y_data_bottom, lw=2.0)
    for di in range(n_ds):
        draw_line(x_group_bounds[di], y_group_bottom, x_group_bounds[di + 1], y_group_bottom, lw=1.2)
        draw_line(x_group_bounds[di], y_header_bottom, x_group_bounds[di + 1], y_header_bottom, lw=1.2)

    draw_line(x_start, y_top, x_start, y_data_bottom, lw=1.0)
    draw_line(x_method_right, y_top, x_method_right, y_data_bottom, lw=1.0)
    draw_line(x_col_rights[-1], y_top, x_col_rights[-1], y_data_bottom, lw=1.0)
    for di in range(1, n_ds):
        draw_line(x_group_bounds[di], y_top, x_group_bounds[di], y_data_bottom, lw=1.2)


# ---------------------------------------------------------------------------
# 5. 编译 LaTeX
# ---------------------------------------------------------------------------
def compile_tex_to_pdf(tex_path: Path) -> bool:
    import shutil, subprocess
    if shutil.which("pdflatex") is None:
        print("[警告] 系统未找到 pdflatex，跳过编译。")
        return False
    try:
        # 编译两次确保引用正确
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", str(tex_path.name)],
                cwd=str(tex_path.parent), capture_output=True, text=True, timeout=60,
            )
        if result.returncode == 0:
            print(f"[PDF] 已编译: {tex_path.with_suffix('.pdf')}")
            # 清理 LaTeX 编译中间文件，只保留 .tex 和 .pdf
            _cleanup_latex_artifacts(tex_path)
            return True
        else:
            print(f"[警告] pdflatex 编译失败，返回码: {result.returncode}")
            return False
    except Exception as e:
        print(f"[警告] 编译异常: {e}")
        return False


def _cleanup_latex_artifacts(tex_path: Path):
    """删除 pdflatex 编译产生的中间文件，只保留 .tex 和 .pdf。"""
    base = tex_path.stem
    artifact_exts = [".aux", ".log", ".out", ".toc", ".lof", ".lot",
                     ".fls", ".fdb_latexmk", ".synctex.gz"]
    for ext in artifact_exts:
        artifact = tex_path.parent / (base + ext)
        if artifact.exists():
            try:
                artifact.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 6. 主入口
# ---------------------------------------------------------------------------
def main():
    print(f">>> 正在生成表格，风格: {TABLE_STYLE}\n")
    snippet_path, full_path = generate_latex()
    generate_image()

    print("\n>>> 正在编译 LaTeX ...")
    compile_tex_to_pdf(full_path)

    print("\n全部完成！")
    print(f"  LaTeX 片段（插入论文）: {TEX_DIR}/table_main.tex")
    print(f"  LaTeX 完整版（可编译）: {TEX_DIR}/table_full.tex")
    print(f"  编译 PDF 预览:          {TEX_DIR}/table_full.pdf")
    print("\n提示: 修改脚本顶部 TABLE_STYLE 变量可切换 4 种风格")


if __name__ == "__main__":
    main()
