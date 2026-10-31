#!/usr/bin/env python3
"""
检查 ECPFL-UN/TH/RK 各数据集的通信量和通信时间
"""
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")

# 实验目录映射
EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST":    "20260605_mnist_union",
        "FMNIST":   "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
        "SVHN":     None,  # 没有 UN 实验
    },
    "ECPFL-TH": {
        "MNIST":    "20260604_mnist_threshold_pct_0.1",
        "FMNIST":   "20260604_fashion_mnist_threshold_pct_0.3",
        "CIFAR-10": "20260604_cifar10_threshold_pct_0.7",
        "SVHN":     None,  # 没有 TH 实验
    },
    "ECPFL-RK": {
        "MNIST":    "20260605_mnist_topk_pct_0.1",
        "FMNIST":   "20260610_fashion_mnist_sp0.3_topk0.3",
        "CIFAR-10": "20260605_cifar10_topk_pct_0.7",
        "SVHN":     "20260622_svhn_sp0.5_topk0.7",
    },
}

def parse_report(report_path):
    """从 report.md 提取关键指标"""
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
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
        "sim_comm_time_s": extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s"),
    }

def main():
    print("="*80)
    print("ECPFL 实验通信量和通信时间检查")
    print("="*80)
    
    for method, datasets in EXPERIMENTS.items():
        print(f"\n{method}:")
        print("-"*80)
        
        for ds, exp_dir in datasets.items():
            if exp_dir is None:
                print(f"  {ds:12s}: 无实验数据")
                continue
            
            report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
            
            if not os.path.exists(report_path):
                print(f"  {ds:12s}: report.md 不存在")
                continue
            
            data = parse_report(report_path)
            
            # 确定使用哪个时间字段
            if data['sim_comm_time_s'] is not None:
                tt = data['sim_comm_time_s']
                tt_label = "Comm Time"
            else:
                tt = data['sim_time_s']
                tt_label = "Sim Time"
            
            tv_gb = data['total_comm_mb'] / 1024 if data['total_comm_mb'] else 0
            
            print(f"  {ds:12s} ({exp_dir}):")
            print(f"    Accuracy: {data['accuracy']:.2f}%")
            print(f"    TV = {data['total_comm_mb']:.2f} MB = {tv_gb:.2f} GB")
            print(f"    Upload = {data['total_upload_mb']:.2f} MB")
            print(f"    Effective DL = {data['effective_download_mb']:.2f} MB")
            print(f"    TT ({tt_label}) = {tt:.2f} s")

if __name__ == "__main__":
    main()
