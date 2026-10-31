#!/usr/bin/env python3
"""
提取 TV (总通信量) 和 TT (总模拟时间)
更新 communication.json 和 LaTeX 表格
"""
import json
import re
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

# 所有实验目录
EXPERIMENTS = {
    "FedAvg+CKKS": {
        "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
        "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn",
    },
    "FedPHE": {
        "MNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist",
        "FMNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10",
        "SVHN": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn",
    },
    "MASER": {
        "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
        "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
        "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
    },
    "ESAFL": {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn",
    },
    "ECPFL-UN": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260605_mnist_union",
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260605_fashion_mnist_union",
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260605_cifar10_union",
        "SVHN": "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7",
    },
    "ECPFL-TH-0.1": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260604_mnist_threshold_pct_0.1",
    },
    "ECPFL-TH-0.3": {
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260604_fashion_mnist_threshold_pct_0.3",
    },
    "ECPFL-TH-0.7": {
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260604_cifar10_threshold_pct_0.7",
        "SVHN": "accuracy_baseline/ours/result_fix_pro/experiment_20260624_204358_svhn_th",
    },
    "ECPFL-RK-0.1": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260605_mnist_topk_pct_0.1",
    },
    "ECPFL-RK-0.3": {
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3",
    },
    "ECPFL-RK-0.7": {
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260605_cifar10_topk_pct_0.7",
        "SVHN": "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7",
    },
}


def extract_tv_tt(report_path):
    """从 report.md 提取 TV 和 TT"""
    if not os.path.exists(report_path):
        return None, None
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取 Total Communication (MB)
    tv_match = re.search(r"Total Communication.*?\|\s*([\d.]+)\s*MB", content)
    tv_gb = float(tv_match.group(1)) / 1024 if tv_match else None
    
    # TT 使用 Total Simulated Time (s)，表示每轮最慢客户端 wall-clock 之和
    tt_match = re.search(r"Total Simulated Time.*?\|\s*([\d.-]+)\s*s", content)
    tt_s = float(tt_match.group(1)) if tt_match else None
    
    return tv_gb, tt_s


# 读取现有 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

# 提取所有实验的 TV 和 TT
for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(PROJECT_ROOT, exp_dir, "report.md")
        tv_gb, tt_s = extract_tv_tt(report_path)
        
        if tv_gb is not None and tt_s is not None:
            if method not in comm_data:
                comm_data[method] = {}
            if ds not in comm_data[method]:
                comm_data[method][ds] = {}
            
            comm_data[method][ds]["TV_GB"] = round(tv_gb, 2)
            comm_data[method][ds]["TT_S"] = round(tt_s, 2)
            
            print(f"[OK] {method} | {ds}: TV={tv_gb:.2f} GB, TT={tt_s:.2f} s")
        else:
            print(f"[WARN] {method} | {ds}: 无法提取 TV/TT")

# 保存 communication.json
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")

# 生成 LaTeX 表格
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

UN_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
TH_ACC = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
TH_COMM = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
RK_ACC = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
RK_COMM = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}

def get_acc_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][1]
    elif ri == 4: return UN_KEYS[ds]
    elif ri == 5: return TH_ACC[ds]
    elif ri == 6: return RK_ACC[ds]

def get_comm_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][2]
    elif ri == 4: return UN_KEYS[ds]
    elif ri == 5: return TH_COMM[ds]
    elif ri == 6: return RK_COMM[ds]

def get_ac(ri, ds):
    vals = accuracy_data.get(ds, {}).get(get_acc_key(ri, ds), [])
    return round(vals[-1] * 100, 2) if vals else 0.0

def get_tv(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TV_GB", 0.0)

def get_tt(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TT_S", 0.0)

best_ac, best_tv, best_tt = {}, {}, {}
for ds in TABLE_DATASETS:
    acs = [(i, get_ac(i, ds)) for i in range(len(TABLE_ROWS))]
    tvs = [(i, get_tv(i, ds)) for i in range(len(TABLE_ROWS))]
    tts = [(i, get_tt(i, ds)) for i in range(len(TABLE_ROWS))]
    best_ac[ds] = max(acs, key=lambda x: x[1])[0]
    best_tv[ds] = min(tvs, key=lambda x: x[1])[0]
    best_tt[ds] = min(tts, key=lambda x: x[1])[0]

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
    for ds in TABLE_DATASETS:
        ac = get_ac(row_idx, ds)
        tv = get_tv(row_idx, ds)
        tt = get_tt(row_idx, ds)
        cells.append(fmt(ac, best_ac[ds] == row_idx))
        cells.append(fmt(tv, best_tv[ds] == row_idx))
        cells.append(fmt(tt, best_tt[ds] == row_idx))
    lines.append(" & ".join(cells) + r" \\")
    if row_idx == 3:
        lines.append(r" \midrule")

lines.append(r" \bottomrule")
lines.append(r" \end{tabular}")
lines.append(r" }")
lines.append(r" \end{table*}")

latex = "\n".join(lines)

tex_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/comm_comparison_table.tex")
with open(tex_path, "w", encoding="utf-8") as f:
    f.write(latex)

print(f"\n[OK] 已更新: {tex_path}")
print("\n" + "="*60)
print("LaTeX 表格:")
print("="*60)
print(latex)
