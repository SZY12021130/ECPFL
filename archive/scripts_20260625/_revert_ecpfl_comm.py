#!/usr/bin/env python3
"""
回退ECPFL通信量计算方式
ECPFL采用预取机制，需要将DV从仅Fetch改为Total Actual Download (Fetch + Prefetch)
"""
import json
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# ECPFL实验目录映射
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

def parse_report(report_path):
    """从report.md解析通信量数据"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    def extract(pattern):
        m = re.search(pattern, content)
        return float(m.group(1)) if m else None
    
    return {
        "total_upload_mb": extract(r"Total Upload.*?\|\s*([\d.]+)\s*MB"),
        "total_fetch_mb": extract(r"Total Download \(Fetch\).*?\|\s*([\d.]+)\s*MB"),
        "total_prefetch_mb": extract(r"Total Download \(Prefetch\).*?\|\s*([\d.]+)\s*MB"),
        "total_actual_download_mb": extract(r"Total Actual Download.*?\|\s*([\d.]+)\s*MB"),
    }

# 读取当前communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("回退ECPFL通信量计算方式")
print("DV = Total Actual Download (Fetch + Prefetch)")
print("=" * 80)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
        if not os.path.exists(report_path):
            print(f"  [SKIP] {method} | {ds}")
            continue
        
        data = parse_report(report_path)
        
        # 确定method_key
        if method == "ECPFL-UN":
            mk = "ECPFL-UN"
        elif method == "ECPFL-TH":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-TH-{theta_map[ds]}"
        elif method == "ECPFL-RK":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-RK-{theta_map[ds]}"
        
        uv_mb = data["total_upload_mb"]
        dv_mb = data["total_actual_download_mb"]  # 使用Total Actual Download
        tv_mb = uv_mb + dv_mb
        
        print(f"\n  {method} | {ds}:")
        print(f"    UV (Upload)              = {uv_mb:.2f} MB = {uv_mb/1024:.2f} GB")
        print(f"    DV (Actual Download)     = {dv_mb:.2f} MB = {dv_mb/1024:.2f} GB")
        print(f"    TV (UV+DV)               = {tv_mb:.2f} MB = {tv_mb/1024:.2f} GB")
        
        # 更新communication.json
        if mk not in comm_data:
            comm_data[mk] = {}
        comm_data[mk][ds] = {
            "UV_GB": round(uv_mb / 1024, 2),
            "DV_GB": round(dv_mb / 1024, 2),
            "TV_GB": round(tv_mb / 1024, 2),
        }

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
