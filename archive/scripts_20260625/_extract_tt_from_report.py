#!/usr/bin/env python3
"""
从 report.md 提取 CT Upload Time 和 CT Download Time，计算 TT = CT Upload Time + CT Download Time
"""
import json
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST":    "20260605_mnist_union",
        "FMNIST":   "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
        "SVHN":     "20260622_svhn_sp0.5_topk0.7",
    },
    "ECPFL-TH": {
        "MNIST":    "20260604_mnist_threshold_pct_0.1",
        "FMNIST":   "20260604_fashion_mnist_threshold_pct_0.3",
        "CIFAR-10": "20260604_cifar10_threshold_pct_0.7",
    },
    "ECPFL-RK": {
        "MNIST":    "20260605_mnist_topk_pct_0.1",
        "FMNIST":   "20260610_fashion_mnist_sp0.3_topk0.3",
        "CIFAR-10": "20260605_cifar10_topk_pct_0.7",
    },
}

def extract_comm_time(report_path):
    """从 report.md 提取 CT Upload Time 和 CT Download Time"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取 CT Upload Time
    m_ul = re.search(r"CT Upload Time.*?\|\s*([\d.]+)\s*s", content)
    ul_time = float(m_ul.group(1)) if m_ul else 0
    
    # 提取 CT Download Time
    m_dl = re.search(r"CT Download Time.*?\|\s*([\d.]+)\s*s", content)
    dl_time = float(m_dl.group(1)) if m_dl else 0
    
    return ul_time, dl_time

# 读取当前 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("从 report.md 提取 CT Upload Time 和 CT Download Time")
print("TT = CT Upload Time + CT Download Time")
print("=" * 80)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
        
        if not os.path.exists(report_path):
            print(f"  [SKIP] {method} | {ds} - report.md not found")
            continue
        
        ul_time, dl_time = extract_comm_time(report_path)
        tt = ul_time + dl_time
        
        # 确定 method_key
        if method == "ECPFL-UN":
            mk = "ECPFL-UN"
        elif method == "ECPFL-TH":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-TH-{theta_map[ds]}"
        elif method == "ECPFL-RK":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-RK-{theta_map[ds]}"
        
        old_tt = comm_data.get(mk, {}).get(ds, {}).get("TT_S", 0)
        
        print(f"\n  {method} | {ds}:")
        print(f"    CT Upload Time:   {ul_time:.2f} s")
        print(f"    CT Download Time: {dl_time:.2f} s")
        print(f"    TT (UL+DL):       {tt:.2f} s")
        print(f"    Old TT:           {old_tt:.2f} s")
        
        # 更新 communication.json
        if mk not in comm_data:
            comm_data[mk] = {}
        if ds not in comm_data[mk]:
            comm_data[mk][ds] = {}
        comm_data[mk][ds]["TT_S"] = round(tt, 2)

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
