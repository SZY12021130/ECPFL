#!/usr/bin/env python3
"""
从 ECPFL 实验数据中提取信息并更新表格
"""
import json
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

# 实验目录映射
EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST": "20260605_mnist_union",
        "FMNIST": "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
    },
    "ECPFL-TH": {
        "MNIST": "20260604_mnist_threshold_pct_0.1",
        "FMNIST": "20260604_fashion_mnist_threshold_pct_0.3",
        "CIFAR-10": "20260604_cifar10_threshold_pct_0.7",
    },
    "ECPFL-RK": {
        "MNIST": "20260605_mnist_topk_pct_0.1",
        "FMNIST": "20260610_fashion_mnist_sp0.3_topk0.3",
        "CIFAR-10": "20260605_cifar10_topk_pct_0.7",
    },
}

def extract_from_report(report_path):
    """从 report.md 提取关键指标"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取 Final Test Accuracy
    acc_match = re.search(r"Final Test Accuracy.*?\*\*([\d.]+)%\*\*", content)
    accuracy = float(acc_match.group(1)) if acc_match else 0.0
    
    # 提取 Total Communication (MB)
    comm_match = re.search(r"Total Communication.*?\|\s*([\d.]+)\s*MB", content)
    total_comm_mb = float(comm_match.group(1)) if comm_match else 0.0
    
    # 提取 Total Simulated Time (s)
    time_match = re.search(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s", content)
    total_time = float(time_match.group(1)) if time_match else 0.0
    
    # 提取 Total Upload (MB)
    upload_match = re.search(r"Total Upload.*?\|\s*([\d.]+)\s*MB", content)
    total_upload_mb = float(upload_match.group(1)) if upload_match else 0.0
    
    # 提取 Effective Download (MB)
    download_match = re.search(r"Effective Download.*?\|\s*([\d.]+)\s*MB", content)
    effective_download_mb = float(download_match.group(1)) if download_match else 0.0
    
    return {
        "accuracy": accuracy,
        "total_comm_mb": total_comm_mb,
        "total_time": total_time,
        "upload_mb": total_upload_mb,
        "download_mb": effective_download_mb,
    }

def main():
    # 读取现有 communication.json
    with open(COMM_JSON, "r", encoding="utf-8") as f:
        comm_data = json.load(f)
    
    # 读取现有 accuracy.json
    with open(ACCURACY_JSON, "r", encoding="utf-8") as f:
        accuracy_data = json.load(f)
    
    # 提取 ECPFL 数据
    for method, datasets in EXPERIMENTS.items():
        for ds, exp_dir in datasets.items():
            report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
            
            if not os.path.exists(report_path):
                print(f"[SKIP] {method} | {ds}: report.md 不存在")
                continue
            
            data = extract_from_report(report_path)
            
            print(f"\n{method} | {ds}:")
            print(f"  Accuracy: {data['accuracy']:.2f}%")
            print(f"  Total Communication: {data['total_comm_mb']:.2f} MB ({data['total_comm_mb']/1024:.2f} GB)")
            print(f"  Total Simulated Time: {data['total_time']:.2f} s")
            print(f"  Upload: {data['upload_mb']:.2f} MB, Download: {data['download_mb']:.2f} MB")
            
            # 更新 communication.json
            method_key = f"{method}-{ds.split('-')[0]}" if "-" in ds else method
            if method == "ECPFL-TH":
                method_key = f"ECPFL-TH-{ds.split('_')[-1]}" if "_" in exp_dir else f"ECPFL-TH-{ds}"
            elif method == "ECPFL-RK":
                method_key = f"ECPFL-RK-{ds.split('_')[-1]}" if "_" in exp_dir else f"ECPFL-RK-{ds}"
            
            # 根据实验目录确定 key
            if "union" in exp_dir:
                method_key = "ECPFL-UN"
            elif "threshold" in exp_dir:
                theta = exp_dir.split("_")[-1]
                method_key = f"ECPFL-TH-{theta}"
            elif "topk" in exp_dir:
                theta = exp_dir.split("_")[-1]
                method_key = f"ECPFL-RK-{theta}"
            
            if method_key not in comm_data:
                comm_data[method_key] = {}
            
            comm_data[method_key][ds] = {
                "UV_GB": round(data['upload_mb'] / 1024, 2),
                "DV_GB": round(data['download_mb'] / 1024, 2),
                "TV_GB": round(data['total_comm_mb'] / 1024, 2),
                "TT_S": round(data['total_time'], 2),
            }
            
            # 更新 accuracy.json
            if ds not in accuracy_data:
                accuracy_data[ds] = {}
            accuracy_data[ds][method_key] = [data['accuracy'] / 100]
    
    # 保存 communication.json
    with open(COMM_JSON, "w", encoding="utf-8") as f:
        json.dump(comm_data, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] 已更新: {COMM_JSON}")
    
    # 保存 accuracy.json
    with open(ACCURACY_JSON, "w", encoding="utf-8") as f:
        json.dump(accuracy_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] 已更新: {ACCURACY_JSON}")
    
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
    
    print(f"\n[OK] 已更新: {tex_path}")
    print("\n" + "="*60)
    print("LaTeX 表格:")
    print("="*60)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
