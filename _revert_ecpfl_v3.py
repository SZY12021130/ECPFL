#!/usr/bin/env python3
"""
正确计算 ECPFL 通信量（预取模式）：
- UV = Total Upload（选中客户端上传总量）
- DV = Total Fetch（选中客户端实际 fetch 下载量，不含预取）
- TV = UV + DV
- TT = Total Simulated Time（含计算+通信）
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

def parse_metrics(metrics_path):
    """从 metrics.json 读取原始数据"""
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    
    upload_cost = m.get("upload_cost", [])
    download_cost = m.get("download_cost", [])  # 这是 fetch 下载量
    
    total_upload = sum(upload_cost)
    total_fetch = sum(download_cost)
    
    return {
        "total_upload_bytes": total_upload,
        "total_fetch_bytes": total_fetch,
    }

def parse_report_time(report_path):
    """从 report.md 读取时间"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    def extract(pattern):
        m = re.search(pattern, content)
        return float(m.group(1)) if m else None
    
    return {
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
        "sim_comm_time_s": extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s"),
    }

def update_report(report_path, uv_mb, dv_mb, tv_mb, tt_s):
    """更新 report.md 中的通信数据"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 更新 Total Communication
    content = re.sub(
        r"Total Communication.*?\|\s*[\d.]+\s*MB",
        f"Total Communication / 总通信量 | {tv_mb:.2f} MB",
        content
    )
    
    # 更新 Total Upload
    content = re.sub(
        r"Total Upload.*?\|\s*[\d.]+\s*MB",
        f"Total Upload / 总上传量 | {uv_mb:.2f} MB",
        content
    )
    
    # 更新 Total Download (Fetch)
    content = re.sub(
        r"Total Download \(Fetch\).*?\|\s*[\d.]+\s*MB",
        f"Total Download (Fetch) / 实际补下载 | {dv_mb:.2f} MB",
        content
    )
    
    # 更新 Effective Download
    content = re.sub(
        r"Effective Download.*?\|\s*[\d.]+\s*MB",
        f"Effective Download / 理论下载责任 | {dv_mb:.2f} MB",
        content
    )
    
    # 更新 Total Simulated Time
    content = re.sub(
        r"Total Simulated Time.*?\|\s*[\d.]+\s*s",
        f"Total Simulated Time / 总模拟时间 | {tt_s:.2f} s",
        content
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("正确计算 ECPFL 通信量（预取模式）")
print("TV = Upload + Fetch, DV = Fetch")
print("=" * 80)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
        metrics_path = os.path.join(OURS_DIR, exp_dir, "metrics.json")
        
        if not os.path.exists(report_path) or not os.path.exists(metrics_path):
            print(f"  [SKIP] {method} | {ds}")
            continue
        
        # 从 metrics.json 读取原始数据
        metrics_data = parse_metrics(metrics_path)
        time_data = parse_report_time(report_path)
        
        # 确定 method_key
        if method == "ECPFL-UN":
            mk = "ECPFL-UN"
        elif method == "ECPFL-TH":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-TH-{theta_map[ds]}"
        elif method == "ECPFL-RK":
            theta_map = {"MNIST": "0.1", "FMNIST": "0.3", "CIFAR-10": "0.7"}
            mk = f"ECPFL-RK-{theta_map[ds]}"
        
        uv_bytes = metrics_data["total_upload_bytes"]
        dv_bytes = metrics_data["total_fetch_bytes"]
        tv_bytes = uv_bytes + dv_bytes
        
        uv_mb = uv_bytes / 1024 / 1024
        dv_mb = dv_bytes / 1024 / 1024
        tv_mb = tv_bytes / 1024 / 1024
        
        # TT: 优先用 Sim Comm Time，否则用 Sim Time
        tt = time_data["sim_comm_time_s"] if time_data["sim_comm_time_s"] else time_data["sim_time_s"]
        
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
        
        # 更新 report.md
        update_report(report_path, uv_mb, dv_mb, tv_mb, tt)

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)
print(f"\n[OK] 已更新: {COMM_JSON}")
