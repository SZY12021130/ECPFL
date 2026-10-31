#!/usr/bin/env python3
"""
从 metrics.json 计算纯通信时间
"""
import json
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")

EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST":    "20260605_mnist_union",
        "FMNIST":   "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
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
        "SVHN":     "20260622_svhn_sp0.5_topk0.7",
    },
}

def calc_comm_time(metrics_path):
    """从 metrics.json 计算纯通信时间"""
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    
    # 每轮的最慢客户端上传/下载时间
    upload_time = m.get("upload_time", [])
    download_time = m.get("download_time", [])
    
    total_ul_time = sum(upload_time)
    total_dl_time = sum(download_time)
    total_comm_time = total_ul_time + total_dl_time
    
    return {
        "upload_time": total_ul_time,
        "download_time": total_dl_time,
        "total_comm_time": total_comm_time,
        "num_rounds": len(upload_time),
    }

def main():
    print("="*80)
    print("ECPFL 纯通信时间计算")
    print("="*80)
    
    for method, datasets in EXPERIMENTS.items():
        print(f"\n{method}:")
        print("-"*80)
        
        for ds, exp_dir in datasets.items():
            metrics_path = os.path.join(OURS_DIR, exp_dir, "metrics.json")
            
            if not os.path.exists(metrics_path):
                print(f"  {ds:12s}: metrics.json 不存在")
                continue
            
            calc = calc_comm_time(metrics_path)
            
            print(f"  {ds:12s} ({exp_dir}):")
            print(f"    Upload Time:   {calc['upload_time']:.2f} s")
            print(f"    Download Time: {calc['download_time']:.2f} s")
            print(f"    Total Comm Time: {calc['total_comm_time']:.2f} s")
            print(f"    Num Rounds: {calc['num_rounds']}")

if __name__ == "__main__":
    main()
