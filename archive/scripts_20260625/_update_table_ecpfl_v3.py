#!/usr/bin/env python3
"""
重新生成 LaTeX 表格（ECPFL 预取模式）
"""
import json, os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

with open(ACCURACY_JSON, "r", encoding="utf-8") as f:
    accuracy_data = json.load(f)

TABLE_DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
TABLE_ROWS = [
    ("FedAvg+CKKS", "FedAvg+CKKS", "FedAvg+CKKS", False),
    ("FedPHE", "FedPHE", "FedPHE", False),
    ("ESAFL", "ESAFL", "ESAFL", False),
    ("MASER", "MASER", "MASER", False),
    ("ECPFL-UN (Ours)", None, "ECPFL-UN", True),
    ("ECPFL-TH-$\\theta$ (Ours)", None, None, True),
    ("ECPFL-RK-$\\theta$ (Ours)", None, None, True),
]
UN_KEYS = {d: "ECPFL-UN" for d in TABLE_DATASETS}
TH_ACC = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
TH_COMM = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
RK_ACC = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
RK_COMM = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}

def get_acc_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][1]
    if ri == 4: return UN_KEYS[ds]
    if ri == 5: return TH_ACC[ds]
    if ri == 6: return RK_ACC[ds]

def get_comm_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][2]
    if ri == 4: return UN_KEYS[ds]
    if ri == 5: return TH_COMM[ds]
    if ri == 6: return RK_COMM[ds]

def get_ac(ri, ds):
    vals = accuracy_data.get(ds, {}).get(get_acc_key(ri, ds), [])
    return round(vals[-1] * 100, 2) if vals else 0.0

def get_tv(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TV_GB", 0.0)

def get_tt(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TT_S", 0.0)

best_ac, best_tv, best_tt = {}, {}, {}
for ds in TABLE_DATASETS:
    best_ac[ds] = max(range(len(TABLE_ROWS)), key=lambda i: get_ac(i, ds))
    best_tv[ds] = min(range(len(TABLE_ROWS)), key=lambda i: get_tv(i, ds))
    best_tt[ds] = min(range(len(TABLE_ROWS)), key=lambda i: get_tt(i, ds))

def fmt(val, is_best=False):
    s = f"{val:.2f}"
    return f"\\textbf{{{s}}}" if is_best else s

lines = []
lines.append(r"\begin{table*}[t]")
lines.append(r" \centering")
lines.append(r" \caption{Comparison of Accuracy and Communication Cost Across Datasets}")
lines.append(r" \label{tab:comm-comparison}")
lines.append(r" \resizebox{\textwidth}{!}{")
lines.append(r" \begin{tabular}{l ccc ccc ccc ccc}")
lines.append(r" \toprule")
lines.append(r" \multirow{3}{*}{\textbf{Methods}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{MNIST}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{FMNIST}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{CIFAR-10}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{SVHN}} \\")
lines.append(r" \cmidrule(lr){2-4} \cmidrule(lr){5-7} \cmidrule(lr){8-10} \cmidrule(lr){11-13}")
lines.append(r" & \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.1)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.3)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.7)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.5)$} \\")
lines.append(r" \cmidrule(lr){2-4} \cmidrule(lr){5-7} \cmidrule(lr){8-10} \cmidrule(lr){11-13}")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S) \\")
lines.append(r" \midrule")

for row_idx in range(len(TABLE_ROWS)):
    row_label = TABLE_ROWS[row_idx][0]
    is_ours = TABLE_ROWS[row_idx][3]
    if is_ours:
        lines.append(r" \rowcolor{gray!10}")
    cells = [row_label]
    for d in TABLE_DATASETS:
        cells.append(fmt(get_ac(row_idx, d), best_ac[d] == row_idx))
        cells.append(fmt(get_tv(row_idx, d), best_tv[d] == row_idx))
        cells.append(fmt(get_tt(row_idx, d), best_tt[d] == row_idx))
    lines.append(" & ".join(cells) + r" \\")
    if row_idx == 3:
        lines.append(r" \midrule")

lines.append(r" \bottomrule")
lines.append(r" \end{tabular}")
lines.append(r" }")
lines.append(r" \end{table*}")

tex_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/comm_comparison_table.tex")
with open(tex_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"[OK] 已更新: {tex_path}")
print("\n" + "="*60)
print("LaTeX 表格:")
print("="*60)
print("\n".join(lines))
