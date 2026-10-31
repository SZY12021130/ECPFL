#!/usr/bin/env python3
"""
回退 ECPFL 通信量到预取模式：
- UV = Total Upload（选中客户端上传总量）
- DV = Total Fetch（选中客户端实际 fetch 下载量，不含预取）
- TV = UV + DV
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

def parse_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    def extract(pattern):
        m = re.search(pattern, content)
        return float(m.group(1)) if m else None
    
    return {
        "total_upload_mb": extract(r"Total Upload.*?\|\s*([\d.]+)\s*MB"),
        "total_fetch_mb": extract(r"Total Download \(Fetch\).*?\|\s*([\d.]+)\s*MB"),
        "total_comm_mb": extract(r"Total Communication.*?\|\s*([\d.]+)\s*MB"),
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
    }

# 读取当前 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("回退 ECPFL 通信量到预取模式")
print("TV = Upload + Fetch, DV = Fetch")
print("=" * 80)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
        if not os.path.exists(report_path):
            print(f"  [SKIP] {method} | {ds}")
            continue
        
        data = parse_report(report_path)
        
        # 确定 method_key
        if method == "ECPFL-UN":
            mk = "ECPFL-UN"
        elif method == "ECPFL-TH":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-TH-{theta_map[ds]}"
        elif method == "ECPFL-RK":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-RK-{theta_map[ds]}"
        
        uv_mb = data["total_upload_mb"]
        dv_mb = data["total_fetch_mb"]  # 实际 fetch 下载量
        tv_mb = data["total_comm_mb"]  # UV + DV
        tt = data["sim_time_s"]
        
        print(f"\n  {method} | {ds}:")
        print(f"    UV (Upload)  = {uv_mb:.2f} MB = {uv_mb/1024:.2f} GB")
        print(f"    DV (Fetch)   = {dv_mb:.2f} MB = {dv_mb/1024:.2f} GB")
        print(f"    TV (UV+DV)   = {tv_mb:.2f} MB = {tv_mb/1024:.2f} GB")
        print(f"    TT           = {tt:.2f} s")
        
        if mk not in comm_data:
            comm_data[mk] = {}
        comm_data[mk][ds] = {
            "UV_GB": round(uv_mb / 1024, 2),
            "DV_GB": round(dv_mb / 1024, 2),
            "TV_GB": round(tv_mb / 1024, 2),
            "TT_S": round(tt, 2),
        }

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
