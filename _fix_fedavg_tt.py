#!/usr/bin/env python3
"""
重新计算 FedAvg+CKKS 的 TT (通信时间)
公式: TT = Σ max(client_upload_time) + Σ max(client_download_time)
"""
import json
import re
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

FEDAVG_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
    "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
    "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_115455_svhn",
}

NUM_SELECTED = 25

def parse_client_bandwidths(report_path):
    """从 report 解析每个客户端的带宽 (kbps)"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*kbps\s*\|\s*(\d+)\s*kbps\s*\|'
    clients = []
    for m in re.findall(pattern, content):
        cid, part, cts, dl_kbps, ul_kbps = int(m[0]), int(m[1]), int(m[2]), int(m[3]), int(m[4])
        clients.append({
            "cid": cid,
            "part": part,
            "cts": cts,
            "dl_bw": dl_kbps * 1000 / 8,  # kbps -> bytes/s
            "ul_bw": ul_kbps * 1000 / 8,
        })
    return clients

# 读取 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

for ds, exp_dir in FEDAVG_EXPERIMENTS.items():
    report_path = os.path.join(PROJECT_ROOT, exp_dir, "report.md")
    clients = parse_client_bandwidths(report_path)
    
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    # 反推 single_ct
    # upload_cost = 所有选中客户端的密文总大小
    # single_ct = upload_cost / num_selected / num_ciphertexts
    i = 2
    upload_cost_r = d.get("upload_cost", [0]*50)[i]
    n_cts = d.get("num_ciphertexts", [33]*50)[i]
    single_ct_bytes = upload_cost_r / NUM_SELECTED / n_cts
    
    # FedAvg+CKKS 通信流程:
    # Upload: 25 × num_batches × single_ct (每个客户端上传密文)
    # Download: 25 × num_batches × single_ct (每个客户端下载聚合密文=单个密文)
    
    total_tt = 0.0
    
    for r in range(50):
        nb = d["num_ciphertexts"][r]
        
        # 每客户端的上传量 = num_batches × single_ct
        ul_bytes_per_client = nb * single_ct_bytes
        # 每客户端的下载量 = num_batches × single_ct (聚合密文=单个密文)
        dl_bytes_per_client = nb * single_ct_bytes
        
        max_ul_time = 0
        max_dl_time = 0
        
        for client in clients:
            ul_time = ul_bytes_per_client / client["ul_bw"]
            dl_time = dl_bytes_per_client / client["dl_bw"]
            
            max_ul_time = max(max_ul_time, ul_time)
            max_dl_time = max(max_dl_time, dl_time)
        
        total_tt += max_ul_time + max_dl_time
    
    print(f"\n{'='*60}")
    print(f"FedAvg+CKKS {ds}:")
    print(f"  single_ct = {single_ct_bytes:.0f} bytes ({single_ct_bytes/1024/1024:.2f} MB)")
    print(f"  客户端数: {len(clients)}")
    print(f"  TT (slowest client per round): {total_tt:.2f} s")
    
    comm_data["FedAvg+CKKS"][ds]["TT_S"] = round(total_tt, 2)

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
