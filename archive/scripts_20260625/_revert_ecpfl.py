#!/usr/bin/env python3
"""
回退 ECPFL 通信量到原始预取模式：
TV = Upload + Fetch（不是 Upload + Upload）
TT = report 中的 Total Simulated Time（含计算+通信）
"""
import json, os, re

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
        "accuracy": extract(r"Final Test Accuracy.*?\*\*([\d.]+)%\*\*"),
        "total_comm_mb": extract(r"Total Communication.*?\|\s*([\d.]+)\s*MB"),
        "total_upload_mb": extract(r"Total Upload.*?\|\s*([\d.]+)\s*MB"),
        "effective_download_mb": extract(r"Effective Download.*?\|\s*([\d.]+)\s*MB"),
        "total_fetch_mb": extract(r"Total Download \(Fetch\).*?\|\s*([\d.]+)\s*MB"),
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
        "sim_comm_time_s": extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s"),
    }

with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("回退 ECPFL 通信量到预取模式")
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
        # DV = Effective Download（理论下载责任）
        dv_mb = data["effective_download_mb"]
        # TV = Upload + Effective Download
        tv_mb = data["total_comm_mb"]
        
        # TT: 优先用 Sim Comm Time，否则用 Sim Time
        tt = data["sim_comm_time_s"] if data["sim_comm_time_s"] else data["sim_time_s"]
        
        print(f"\n  {method} | {ds}:")
        print(f"    UV = {uv_mb:.2f} MB = {uv_mb/1024:.2f} GB")
        print(f"    DV = {dv_mb:.2f} MB = {dv_mb/1024:.2f} GB")
        print(f"    TV = {tv_mb:.2f} MB = {tv_mb/1024:.2f} GB")
        print(f"    TT = {tt:.2f} s")
        
        if mk not in comm_data:
            comm_data[mk] = {}
        comm_data[mk][ds] = {
            "UV_GB": round(uv_mb / 1024, 2),
            "DV_GB": round(dv_mb / 1024, 2),
            "TV_GB": round(tv_mb / 1024, 2),
            "TT_S": round(tt, 2),
        }

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)
print(f"\n[OK] 已更新: {COMM_JSON}")
