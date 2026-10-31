#!/usr/bin/env python3
"""
计算 ECPFL 的正确 TT 值
TT = Σ (max(upload_time_per_client) + max(download_time_per_client)) for each round
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
                    dl_bw_str = parts[4].replace("kbps", "").strip()
                    ul_bw_str = parts[5].replace("kbps", "").strip()
                    dl_bw_kbps = float(dl_bw_str)
                    ul_bw_kbps = float(ul_bw_str)
                    clients.append({
                        "cid": cid,
                        "dl_bw": dl_bw_kbps * 1024 / 8,  # bytes/s
                        "ul_bw": ul_bw_kbps * 1024 / 8,  # bytes/s
                    })
                except (ValueError, IndexError):
                    pass
    
    return clients

def parse_num_clients_and_sample_rate(report_path):
    """从 report.md 解析客户端数和采样率"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    num_clients = 50
    sample_rate = 0.5
    
    m = re.search(r"Num Clients.*?\|\s*(\d+)", content)
    if m:
        num_clients = int(m.group(1))
    
    m = re.search(r"Client Sampling Rate.*?\|\s*([\d.]+)", content)
    if m:
        sample_rate = float(m.group(1))
    
    return num_clients, sample_rate

def calc_comm_time(metrics_path, report_path):
    """计算纯通信时间
    TT = Σ max_client(upload_time + download_time) per round
    即每轮最慢客户端的上传时间+下载时间，然后累加所有轮次
    """
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    
    upload_cost = m.get("upload_cost", [])      # 每轮总上传字节数（所有选中客户端）
    download_cost = m.get("download_cost", [])   # 每轮总下载字节数（所有选中客户端）
    num_rounds = len(upload_cost)
    
    if num_rounds == 0:
        return None
    
    clients = parse_client_bandwidth(report_path)
    if not clients:
        return None
    
    num_clients, sample_rate = parse_num_clients_and_sample_rate(report_path)
    n_sel = int(num_clients * sample_rate)
    
    # 计算每轮最慢客户端的通信时间，然后累加
    total_comm_time = 0.0
    
    for r in range(num_rounds):
        ul_this = upload_cost[r] if r < len(upload_cost) else 0
        dl_this = download_cost[r] if r < len(download_cost) else 0
        
        if ul_this > 0 or dl_this > 0:
            # upload_cost[r] 是第 r 轮所有选中客户端的总上传字节数
            # 需要除以 n_sel 得到每客户端的值
            ul_per_client = ul_this / n_sel if n_sel > 0 else ul_this
            dl_per_client = dl_this / n_sel if n_sel > 0 else dl_this
            
            # 计算每个客户端的通信时间（上传+下载），找最慢的
            client_times = [
                ul_per_client / c["ul_bw"] + dl_per_client / c["dl_bw"]
                for c in clients
            ]
            max_client_time = max(client_times)
            
            total_comm_time += max_client_time
    
    return {
        "total_comm_time": total_comm_time,
        "num_rounds": num_rounds,
    }

# 读取当前 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("计算 ECPFL 正确的 TT 值")
print("TT = Σ (max(upload_time) + max(download_time)) per round")
print("=" * 80)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        metrics_path = os.path.join(OURS_DIR, exp_dir, "metrics.json")
        report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
        
        if not os.path.exists(metrics_path) or not os.path.exists(report_path):
            print(f"  [SKIP] {method} | {ds}")
            continue
        
        calc = calc_comm_time(metrics_path, report_path)
        if calc is None:
            print(f"  [SKIP] {method} | {ds}")
            continue
        
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
        new_tt = calc["total_comm_time"]
        
        print(f"\n  {method} | {ds}:")
        print(f"    Total Comm Time: {calc['total_comm_time']:.2f} s")
        print(f"    Old TT:          {old_tt:.2f} s")
        print(f"    New TT:          {calc['total_comm_time']:.2f} s")
        
        # 更新 communication.json
        if mk not in comm_data:
            comm_data[mk] = {}
        if ds not in comm_data[mk]:
            comm_data[mk][ds] = {}
        comm_data[mk][ds]["TT_S"] = round(new_tt, 2)

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
