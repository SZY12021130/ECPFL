"""
生成三层表头对比表格：Methods × Datasets × (AC, DV, UV)
=========================================================
结构：
    - 第一列：Methods
    - 顶层：Datasets（跨 12 列）
    - 中层：MNIST / FMNIST / CIFAR-10 / SVHN（各跨 3 列）
    - 底层：AC (%) / DV (GB) / UV (GB)

输出：
    - tex/comm_table_main.tex      → 插入论文的 LaTeX 片段
    - tex/comm_table_full.tex      → 完整可编译文档
    - tex/comm_table_full.pdf      → 编译后的 PDF 预览

使用：
    python table_experiment/script/generate_comm_table.py
"""

import os
import sys
from pathlib import Path
import random
import subprocess
import shutil

# ---------------------------------------------------------------------------
# 0. 路径
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
TABLE_DIR = SCRIPT_DIR.parent
TEX_DIR = TABLE_DIR / "tex"
TEX_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. 配置
# ---------------------------------------------------------------------------
METHODS = [
    "FedAvg+Ckks",
    "FedPHE",
    "ESAFL",
    "MASER",
    "ECPFL-UN",
    "ECPFL-TO-0.3",
    "ECPFL-TO-0.5",
    "ECPFL-TH-0.3",
    "ECPFL-TH-0.5",
]

DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METRICS = ["AC (%)", "DV (GB)", "UV (GB)"]

# 固定随机种子，让模拟数据可复现
random.seed(42)


def generate_mock_data():
    """
    生成模拟数据。
    AC: 准确率，70~99%（越高越好）
    DV: 下载量，0.5~5.0 GB（越低越好）
    UV: 上传量，0.1~2.0 GB（越低越好）
    返回: {method: {dataset: [AC, DV, UV]}}
    """
    data = {}
    for method in METHODS:
        data[method] = {}
        for ds in DATASETS:
            ac = round(random.uniform(0.75, 0.99), 2)
            dv = round(random.uniform(0.5, 4.5), 2)
            uv = round(random.uniform(0.1, 2.0), 2)
            data[method][ds] = [ac, dv, uv]
    return data


RAW_DATA = generate_mock_data()


# ---------------------------------------------------------------------------
# 2. 最佳值标记
# ---------------------------------------------------------------------------
def find_best_values():
    """
    对每个数据集-指标组合标记最佳值：
      - AC: 最大值
      - DV/UV: 最小值
    """
    best = {m: {ds: [False, False, False] for ds in DATASETS} for m in METHODS}

    for ds in DATASETS:
        for mi in range(3):
            col_vals = [RAW_DATA[m][ds][mi] for m in METHODS]
            if mi == 0:  # AC 越大越好
                best_val = max(col_vals)
            else:        # DV/UV 越小越好
                best_val = min(col_vals)
            for method in METHODS:
                if abs(RAW_DATA[method][ds][mi] - best_val) < 1e-6:
                    best[method][ds][mi] = True
    return best


BEST_MASK = find_best_values()


# ---------------------------------------------------------------------------
# 3. 生成 LaTeX
# ---------------------------------------------------------------------------
def generate_latex():
    n_ds = len(DATASETS)
    n_met = len(METRICS)
    n_data_cols = n_ds * n_met

    # 列格式：左右外侧加竖线，所有数据列之间也有竖线
    col_spec = "|l|" + "|".join(["c"] * n_data_cols) + "|"

    table_lines = []
    table_lines.append(r"\begin{table}[t]")
    table_lines.append(r"\centering")
    table_lines.append(r"\caption{Comparison of Accuracy and Communication Cost}")
    table_lines.append(r"\label{tab:comm-comparison}")
    table_lines.append(r"\footnotesize")
    table_lines.append("")

    table_lines.append(r"\begin{tabular}{" + col_spec + "}")
    table_lines.append(r"\hline")

    # 第一层：Datasets（跨 12 列数据）
    table_lines.append(
        r" & \multicolumn{" + str(n_data_cols) + r"}{c|}{Datasets} \\"
    )
    table_lines.append(r"\hline")

    # 第二层：数据集名（各跨 3 列）
    ds_header_parts = []
    for ds in DATASETS:
        ds_header_parts.append(r"\multicolumn{3}{c|}{" + ds + r"}")
    table_lines.append(" & ".join([""] + ds_header_parts) + r" \\")
    table_lines.append(r"\hline")

    # 第三层：指标名（对 % 进行 LaTeX 转义）
    escaped_metrics = [m.replace("%", r"\%") for m in METRICS]
    metric_header = ["Methods"] + escaped_metrics * n_ds
    table_lines.append(" & ".join(metric_header) + r" \\")
    table_lines.append(r"\hline")

    # 数据行
    for method in METHODS:
        row_parts = [method]
        for ds in DATASETS:
            for mi in range(n_met):
                val = RAW_DATA[method][ds][mi]
                is_best = BEST_MASK[method][ds][mi]
                # AC 显示为 95.20%，DV/UV 显示为数值
                if mi == 0:
                    txt = f"{val * 100:.2f}"
                else:
                    txt = f"{val:.2f}"
                if is_best:
                    row_parts.append(r"\textbf{" + txt + r"}")
                else:
                    row_parts.append(txt)
        table_lines.append(" & ".join(row_parts) + r" \\")
        table_lines.append(r"\hline")

    table_lines.append(r"\end{tabular}")
    table_lines.append(r"\end{table}")

    # ---- 片段版 ----
    snippet_lines = [
        r"% 将以下代码放入 IEEEtran 文档中",
        r"% 无需额外宏包，使用标准 tabular 环境",
        "",
    ] + table_lines
    snippet_path = TEX_DIR / "comm_table_main.tex"
    snippet_path.write_text("\n".join(snippet_lines), encoding="utf-8")
    print(f"[LaTeX 片段] 已生成: {snippet_path}")

    # ---- 完整版 ----
    full_lines = [
        r"\documentclass[conference]{IEEEtran}",
        r"\usepackage{caption}",
        r"\usepackage{graphicx}",
        r"\begin{document}",
        r"\onecolumn",
        r"\begin{center}",
        r"\Large\textbf{Table Preview -- Communication Cost Comparison}",
        r"\end{center}",
        r"\vspace{1em}",
    ]
    full_lines.extend(table_lines)
    full_lines.append(r"\end{document}")

    full_path = TEX_DIR / "comm_table_full.tex"
    full_path.write_text("\n".join(full_lines), encoding="utf-8")
    print(f"[LaTeX 完整版] 已生成: {full_path}")

    return snippet_path, full_path


# ---------------------------------------------------------------------------
# 4. 编译 PDF
# ---------------------------------------------------------------------------
def compile_tex_to_pdf(tex_path: Path) -> bool:
    if shutil.which("pdflatex") is None:
        print("[警告] 系统未找到 pdflatex，跳过编译。")
        return False
    try:
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", str(tex_path.name)],
                cwd=str(tex_path.parent),
                capture_output=True,
                text=True,
                timeout=60,
            )
        if result.returncode == 0:
            pdf_path = tex_path.with_suffix(".pdf")
            print(f"[PDF] 已编译: {pdf_path}")
            # 清理 LaTeX 编译中间文件，只保留 .tex 和 .pdf
            _cleanup_latex_artifacts(tex_path)
            return True
        else:
            print(f"[警告] pdflatex 编译失败，返回码: {result.returncode}")
            print(result.stderr[-500:])  # 打印最后 500 字符错误信息
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
# 5. 主入口
# ---------------------------------------------------------------------------
def main():
    print(">>> 正在生成通信开销对比表格...\n")
    snippet_path, full_path = generate_latex()

    print("\n>>> 正在编译 LaTeX ...")
    compile_tex_to_pdf(full_path)

    print("\n全部完成！")
    print(f"  LaTeX 片段:  {TEX_DIR}/comm_table_main.tex")
    print(f"  LaTeX 完整版: {TEX_DIR}/comm_table_full.tex")
    print(f"  PDF 预览:     {TEX_DIR}/comm_table_full.pdf")


if __name__ == "__main__":
    main()
