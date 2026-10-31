#!/usr/bin/env python3
"""
生成 perf_evaluation 表格，Ours 使用 ECPFL-RK-θ。
所有数值均为 50 轮累计总量，与 comm_comparison_table.tex 的 TT 保持一致。
"""
import json, os, re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

ROUNDS = 50

def parse_report(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    def e(pat):
        m = re.search(pat, content)
        return float(m.group(1)) if m else None
    return {
        "n_up": e(r"Total CT Blocks \(Upload\).*?\|\s*([\d.]+)\s*blocks"),
        "n_agg": e(r"Total Aggregated CTs \(Download\).*?\|\s*([\d.]+)\s*blocks"),
        "ct_up_time": e(r"CT Upload Time.*?\|\s*([\d.]+)\s*s"),
        "ct_down_time": e(r"CT Download Time.*?\|\s*([\d.]+)\s*s"),
    }

def num_ciphertexts_from_metrics(exp_dir):
    p = os.path.join(exp_dir, "metrics.json")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    vals = d.get("num_ciphertexts")
    return sum(vals) if isinstance(vals, list) else None

BASELINES = {
    "FedAvg+CKKS": {
        "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
        "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_115455_svhn",
    },
    "FedPHE": {
        "MNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist",
        "FMNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10",
        "SVHN": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn",
    },
    "ESAFL": {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn",
    },
    "MASER": {
        "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
        "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
        "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
    },
}

OURS = {
    "MNIST": ("accuracy_baseline/ours/result_fix_pro/20260605_mnist_topk_pct_0.1", "ECPFL-RK-0.1"),
    "FMNIST": ("accuracy_baseline/ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3", "ECPFL-RK-0.3"),
    "CIFAR-10": ("accuracy_baseline/ours/result_fix_pro/20260605_cifar10_topk_pct_0.7", "ECPFL-RK-0.7"),
    "SVHN": ("accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7", "ECPFL-RK-0.7"),
}

DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]

def get_baseline_row(method, ds):
    exp_dir = os.path.join(PROJECT_ROOT, BASELINES[method][ds])
    rpt = parse_report(os.path.join(exp_dir, "report.md"))
    comm = comm_data[method][ds]
    uv_mb = comm["UV_GB"] * 1024
    dv_mb = comm["DV_GB"] * 1024
    tt = comm["TT_S"]
    up_time = rpt["ct_up_time"] if rpt["ct_up_time"] is not None else 0.0
    down_time = rpt["ct_down_time"] if rpt["ct_down_time"] is not None else 0.0
    # 若 report 的 up+down 与 comm TT 有小偏差，按比例缩放使 up+down = tt
    s = up_time + down_time
    if s > 0 and abs(s - tt) > 1e-3:
        up_time = up_time / s * tt
        down_time = down_time / s * tt
    return {
        "n_up": int(round(rpt["n_up"])) if rpt["n_up"] else 0,
        "n_agg": int(round(rpt["n_agg"])) if rpt["n_agg"] else 0,
        "uv_mb": uv_mb,
        "dv_mb": dv_mb,
        "up_time": up_time,
        "down_time": down_time,
        "tt": tt,
    }

def get_ours_row(ds):
    exp_dir, comm_key = OURS[ds]
    exp_dir = os.path.join(PROJECT_ROOT, exp_dir)
    rpt = parse_report(os.path.join(exp_dir, "report.md"))
    comm = comm_data[comm_key][ds]
    uv_mb = comm["UV_GB"] * 1024
    dv_mb = comm["DV_GB"] * 1024
    tt = comm["TT_S"]
    if rpt["ct_up_time"] is not None and rpt["ct_down_time"] is not None:
        up_time = rpt["ct_up_time"]
        down_time = rpt["ct_down_time"]
    else:
        # 按通信量比例拆分 TT
        total_v = uv_mb + dv_mb
        if total_v > 0:
            up_time = tt * uv_mb / total_v
            down_time = tt * dv_mb / total_v
        else:
            up_time = tt
            down_time = 0.0
    n_up = int(round(rpt["n_up"])) if rpt["n_up"] else 0
    if n_up == 0:
        n_up = num_ciphertexts_from_metrics(exp_dir) or 0
    return {
        "n_up": n_up,
        "n_agg": 50,  # 50 轮，每轮 1 次聚合/全局模型下发
        "uv_mb": uv_mb,
        "dv_mb": dv_mb,
        "up_time": up_time,
        "down_time": down_time,
        "tt": tt,
    }

def fmt_count(n):
    return f"{n}"

def fmt_mb(v):
    return f"{v:.1f}"

def fmt_time(v):
    return f"{v:.1f}"

def fmt_tt(v):
    return f"{v:.2f}"

# 生成 LaTeX 表格
lines = []
lines.append(r"\begin{table}[t]")
lines.append(r"\centering")
lines.append(r"\caption{End-to-End Performance Breakdown Across Baseline Algorithms and Datasets}")
lines.append(r"\label{tab:perf_evaluation}")
lines.append(r"\resizebox{\linewidth}{!}{")
lines.append(r"\begin{tabular}{ll c c c}")
lines.append(r"\toprule")
lines.append(r"\multirow{2}{*}{\textbf{Dataset}} & \multirow{2}{*}{\textbf{Algorithm}} & \textbf{Counts} & \textbf{Comm. Vol. (MB)} & \textbf{Latency (s)} \\")
lines.append(r"\cmidrule(lr){3-3} \cmidrule(lr){4-4} \cmidrule(lr){5-5}")
lines.append(r"& & \scriptsize $N_{\mathrm{up}} \,/\, N_{\mathrm{agg}}$ & \scriptsize Up $\,/\,$ Down & \scriptsize Up $\,/\,$ Down $\,/\,$ \textbf{TT} \\")
lines.append(r"\midrule")

for ds in DATASETS:
    lines.append("")
    lines.append(f"% ---------------- {ds} ----------------")
    lines.append(r"\multirow{5}{*}{\textbf{" + ds + r"}} ")
    for method in ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER"]:
        row = get_baseline_row(method, ds)
        cells = (
            f"& {method} & ${fmt_count(row['n_up'])} \\,/\\, {fmt_count(row['n_agg'])}$ "
            f"& ${fmt_mb(row['uv_mb'])} \\,/\\, {fmt_mb(row['dv_mb'])}$ "
            f"& ${fmt_time(row['up_time'])} \\,/\\, {fmt_time(row['down_time'])} \\,/\\, {fmt_tt(row['tt'])}$ \\\\"
        )
        lines.append(cells)
    row = get_ours_row(ds)
    lines.append(r"\rowcolor{gray!15}")
    cells = (
        f"& \\textbf{{ECPFL-RK-$\\theta$ (Ours)}} & $\\mathbf{{{fmt_count(row['n_up'])}}} \\,/\\, \\mathbf{{{fmt_count(row['n_agg'])}}}$ "
        f"& $\\mathbf{{{fmt_mb(row['uv_mb'])}}} \\,/\\, \\mathbf{{{fmt_mb(row['dv_mb'])}}}$ "
        f"& $\\mathbf{{{fmt_time(row['up_time'])}}} \\,/\\, \\mathbf{{{fmt_time(row['down_time'])}}} \\,/\\, \\mathbf{{{fmt_tt(row['tt'])}}}$ \\\\"
    )
    lines.append(cells)
    if ds != DATASETS[-1]:
        lines.append(r"\midrule")

lines.append("")
lines.append(r"\bottomrule")
lines.append(r"\multicolumn{5}{l}{\scriptsize \textit{Note:} All values are totals over 50 communication rounds. $N_{\mathrm{up}}$ = upload ciphertext batches; $N_{\mathrm{agg}}$ = aggregated model/ciphertext batches. ECPFL-RK uses plaintext model broadcast (1 per round).}")
lines.append(r"\end{tabular}")
lines.append(r"}")
lines.append(r"\end{table}")

latex = "\n".join(lines)
OUT_PATH = os.path.join(PROJECT_ROOT, "accuracy_baseline/perf_table_rk.tex")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(latex)

print(f"[OK] 已生成: {OUT_PATH}")
print("\n" + "="*80)
print(latex)
