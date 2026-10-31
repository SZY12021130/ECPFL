#!/usr/bin/env python3
"""
更新 ECPFL 实验的 report.md 文件
将通信量和通信时间更新为对称模式（DV = UV）
"""
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"

# ECPFL 实验目录
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

OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")

def update_report(report_path, new_uv_gb, new_dv_gb, new_tv_gb, new_tt_s):
    """更新 report.md 中的通信数据"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 更新 Total Communication
    content = re.sub(
        r"Total Communication.*?\|\s*[\d.]+\s*MB",
        f"Total Communication / 总通信量 | {new_tv_gb * 1024:.2f} MB",
        content
    )
    
    # 更新 Total Upload
    content = re.sub(
        r"Total Upload.*?\|\s*[\d.]+\s*MB",
        f"Total Upload / 总上传量 | {new_uv_gb * 1024:.2f} MB",
        content
    )
    
    # 更新 Total Download (Fetch)
    content = re.sub(
        r"Total Download \(Fetch\).*?\|\s*[\d.]+\s*MB",
        f"Total Download (Fetch) / 实际补下载 | {new_dv_gb * 1024:.2f} MB",
        content
    )
    
    # 更新 Effective Download
    content = re.sub(
        r"Effective Download.*?\|\s*[\d.]+\s*MB",
        f"Effective Download / 理论下载责任 | {new_dv_gb * 1024:.2f} MB",
        content
    )
    
    # 更新 Total Simulated Time
    content = re.sub(
        r"Total Simulated Time.*?\|\s*[\d.]+\s*s",
        f"Total Simulated Time / 总模拟时间 | {new_tt_s:.2f} s",
        content
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    import json
    
    # 读取 communication.json
    comm_json_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
    with open(comm_json_path, "r", encoding="utf-8") as f:
        comm_data = json.load(f)
    
    # 更新各实验的 report
    for method, datasets in EXPERIMENTS.items():
        for ds, exp_dir in datasets.items():
            report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
            
            if not os.path.exists(report_path):
                print(f"[SKIP] {method} | {ds}: report.md 不存在")
                continue
            
            # 从 communication.json 读取数据
            method_key = method
            if method == "ECPFL-TH":
                theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
                method_key = f"ECPFL-TH-{theta_map[ds]}"
            elif method == "ECPFL-RK":
                theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
                method_key = f"ECPFL-RK-{theta_map[ds]}"
            
            if method_key not in comm_data or ds not in comm_data[method_key]:
                print(f"[SKIP] {method} | {ds}: communication.json 中无数据")
                continue
            
            data = comm_data[method_key][ds]
            uv_gb = data["UV_GB"]
            dv_gb = data["DV_GB"]
            tv_gb = data["TV_GB"]
            tt_s = data["TT_S"]
            
            print(f"[UPDATE] {method} | {ds}: UV={uv_gb:.2f}GB, DV={dv_gb:.2f}GB, TV={tv_gb:.2f}GB, TT={tt_s:.2f}s")
            update_report(report_path, uv_gb, dv_gb, tv_gb, tt_s)

if __name__ == "__main__":
    main()
