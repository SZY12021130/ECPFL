#!/usr/bin/env python3
"""
从 report 解析每个客户端的带宽，按轮次计算 MASER 的 TT
TT = Σ max(client_upload_time) + Σ max(client_download_time)  per round
"""
import json
import re
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

MASER_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
    "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
    "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
}

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

for ds, exp_dir in MASER_EXPERIMENTS.items():
    report_path = os.path.join(PROJECT_ROOT, exp_dir, "report.md")
    clients = parse_client_bandwidths(report_path)
    
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    # 反推 single_ct 和 model_size
    i = 2
    ct_upload_r = d.get("maser_ct_upload", [0]*50)[i]
    n_cts = d.get("num_ciphertexts", [33]*50)[i]
    single_ct_bytes = ct_upload_r / 25 / n_cts
    
    plaintext_r = d.get("plaintext_upload", [0]*50)[i]
    model_size_bytes = plaintext_r / 25
    
    # 每轮的通信流程 (MASER):
    # ① 上传: 每个选中客户端上传 num_batches × single_ct (加密密文)
    # ② 下载: 每个选中客户端下载 num_batches × single_ct (聚合密文=单个密文)
    # ③ 上传: 每个选中客户端上传 num_batches × single_ct (部分解密)
    # ④ 下载: 每个选中客户端下载 model_size (明文模型)
    
    # 每客户端每轮:
    #   upload = ① + ③ = 2 × num_batches × single_ct
    #   download = ② + ④ = num_batches × single_ct + model_size
    
    # TT = Σ_r [ max_c(upload_c,r / ul_bw_c) + max_c(download_c,r / dl_bw_c) ]
    
    # 获取每轮选中的客户端 (从 metrics 的 selected_clients)
    selected_per_round = d.get("selected_clients", None)
    
    total_tt = 0.0
    
    for r in range(50):
        nb = d["num_ciphertexts"][r]
        
        if selected_per_round and r < len(selected_per_round):
            selected_cids = selected_per_round[r]
        else:
            # 如果没有 selected_clients，使用所有客户端
            selected_cids = [c["cid"] for c in clients]
        
        # 构建 cid -> bandwidth 映射
        cid_bw = {c["cid"]: c for c in clients}
        
        max_ul_time = 0
        max_dl_time = 0
        
        for cid in selected_cids:
            if cid not in cid_bw:
                continue
            bw = cid_bw[cid]
            
            # 每客户端的上传量 = ① + ③ = 2 × nb × single_ct
            ul_bytes = 2 * nb * single_ct_bytes
            # 每客户端的下载量 = ② + ④ = nb × single_ct + model_size
            dl_bytes = nb * single_ct_bytes + model_size_bytes
            
            ul_time = ul_bytes / bw["ul_bw"]
            dl_time = dl_bytes / bw["dl_bw"]
            
            max_ul_time = max(max_ul_time, ul_time)
            max_dl_time = max(max_dl_time, dl_time)
        
        total_tt += max_ul_time + max_dl_time
    
    print(f"\n{'='*60}")
    print(f"MASER {ds}:")
    print(f"  single_ct = {single_ct_bytes:.0f} bytes ({single_ct_bytes/1024/1024:.2f} MB)")
    print(f"  model_size = {model_size_bytes:.0f} bytes ({model_size_bytes/1024/1024:.2f} MB)")
    print(f"  客户端数: {len(clients)}")
    print(f"  TT (slowest client per round): {total_tt:.2f} s")
    
    comm_data["MASER"][ds]["TT_S"] = round(total_tt, 2)

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
