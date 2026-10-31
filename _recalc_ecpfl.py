#!/usr/bin/env python3
"""
重新计算 ECPFL 的通信量和通信时间
确保 Upload 和 Download 都是密文大小
"""
import json
import os
import re

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

def parse_client_bandwidth(report_path):
    """从 report.md 解析客户端带宽"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    clients = []
    for line in content.split("\n"):
        if re.match(r"\|\s*\d+\s*\|", line) and "CID" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                try:
                    cid = int(parts[1])
                    dl_bw_mbps = float(parts[4].replace("kbps", "").strip())
                    ul_bw_mbps = float(parts[5].replace("kbps", "").strip())
                    clients.append({
                        "cid": cid,
                        "dl_bw": dl_bw_mbps * 1024 * 1024 / 8,
                        "ul_bw": ul_bw_mbps * 1024 * 1024 / 8,
                    })
                except (ValueError, IndexError):
                    pass
    
    return clients

def calc_ecpfl_comm(metrics_path, report_path):
    """计算 ECPFL 的通信量和通信时间"""
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    
    upload_cost = m.get("upload_cost", [])
    download_cost = m.get("download_cost", [])
    num_rounds = len(upload_cost)
    
    if num_rounds == 0:
        return None
    
    # 解析客户端带宽
    clients = parse_client_bandwidth(report_path)
    if not clients:
        return None
    
    # 计算总上传量
    total_upload = sum(upload_cost)
    
    # 计算总下载量（Effective Download）
    total_download = sum(download_cost)
    
    # TV = Upload + Download
    tv = total_upload + total_download
    
    # 计算通信时间
    # 每轮最慢客户端的上传/下载时间
    total_ul_time = 0.0
    total_dl_time = 0.0
    
    for r in range(num_rounds):
        ul_this = upload_cost[r]
        dl_this = download_cost[r]
        
        # 假设每轮选中 25 个客户端（50 * 0.5）
        n_sel = 25
        
        # 每客户端上传/下载量
        ul_per_client = ul_this / n_sel if n_sel > 0 else ul_this
        dl_per_client = dl_this / n_sel if n_sel > 0 else dl_this
        
        # 每轮最慢客户端上传/下载时间
        max_ul_t = max(ul_per_client / c["ul_bw"] for c in clients)
        max_dl_t = max(dl_per_client / c["dl_bw"] for c in clients)
        
        total_ul_time += max_ul_t
        total_dl_time += max_dl_t
    
    total_tt = total_ul_time + total_dl_time
    
    return {
        "total_upload": total_upload,
        "total_download": total_download,
        "tv": tv,
        "tt": total_tt,
        "num_rounds": num_rounds,
    }

def main():
    print("="*80)
    print("ECPFL 通信量和通信时间重新计算")
    print("="*80)
    
    for method, datasets in EXPERIMENTS.items():
        print(f"\n{method}:")
        print("-"*80)
        
        for ds, exp_dir in datasets.items():
            metrics_path = os.path.join(OURS_DIR, exp_dir, "metrics.json")
            report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
            
            if not os.path.exists(metrics_path):
                print(f"  {ds:12s}: metrics.json 不存在")
                continue
            
            calc = calc_ecpfl_comm(metrics_path, report_path)
            
            if calc is None:
                print(f"  {ds:12s}: 无法计算")
                continue
            
            print(f"  {ds:12s} ({exp_dir}):")
            print(f"    Upload:   {calc['total_upload']/1024/1024/1024:.2f} GB")
            print(f"    Download: {calc['total_download']/1024/1024/1024:.2f} GB")
            print(f"    TV:       {calc['tv']/1024/1024/1024:.2f} GB")
            print(f"    TT:       {calc['tt']:.2f} s")
            print(f"    Rounds:   {calc['num_rounds']}")

if __name__ == "__main__":
    main()
