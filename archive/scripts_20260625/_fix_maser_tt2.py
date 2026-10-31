#!/usr/bin/env python3
"""
从 report 解析带宽数据，重新计算 MASER 的 TT
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

def parse_bandwidths(report_path):
    """从 report 解析客户端带宽"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 匹配表格行: | CID | Part | CTs | DL BW | UL BW |
    # 例如: | 0 | 50 | 347 | 31013 kbps | 30222 kbps |
    pattern = r'\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*kbps\s*\|\s*(\d+)\s*kbps\s*\|'
    matches = re.findall(pattern, content)
    
    dl_bws = []
    ul_bws = []
    for dl, ul in matches:
        dl_bws.append(int(dl) * 1000 / 8)  # kbps -> bytes/s
        ul_bws.append(int(ul) * 1000 / 8)
    
    return dl_bws, ul_bws

# 读取现有 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

for ds, exp_dir in MASER_EXPERIMENTS.items():
    report_path = os.path.join(PROJECT_ROOT, exp_dir, "report.md")
    dl_bws, ul_bws = parse_bandwidths(report_path)
    
    if not dl_bws:
        print(f"[WARN] {ds}: 没有解析到带宽数据")
        continue
    
    avg_dl_bw = sum(dl_bws) / len(dl_bws)
    avg_ul_bw = sum(ul_bws) / len(ul_bws)
    
    # 从 communication.json 读取 TV
    tv_gb = comm_data["MASER"][ds]["TV_GB"]
    
    # 重新计算 Upload 和 Download
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    i = 2
    ct_upload_r = d.get("maser_ct_upload", [0] * 50)[i]
    n_cts = d.get("num_ciphertexts", [33] * 50)[i]
    single_ct_bytes = ct_upload_r / 25 / n_cts
    
    plaintext_r = d.get("plaintext_upload", [0] * 50)[i]
    model_size_bytes = plaintext_r / 25
    
    total_ul = 0
    total_dl = 0
    
    for j in range(50):
        nb = d["num_ciphertexts"][j]
        ct_upload = 25 * nb * single_ct_bytes
        agg_ct_download = 25 * nb * single_ct_bytes
        partial_dec_upload = 25 * nb * single_ct_bytes
        plaintext_download = 25 * model_size_bytes
        
        total_ul += ct_upload + partial_dec_upload
        total_dl += agg_ct_download + plaintext_download
    
    # 计算 TT
    tt_s = total_ul / avg_ul_bw + total_dl / avg_dl_bw
    
    print(f"\n{'='*60}")
    print(f"MASER {ds}:")
    print(f"  客户端数: {len(dl_bws)}")
    print(f"  平均上行带宽: {avg_ul_bw / 1024 / 1024:.2f} MB/s ({avg_ul_bw * 8 / 1000:.0f} kbps)")
    print(f"  平均下行带宽: {avg_dl_bw / 1024 / 1024:.2f} MB/s ({avg_dl_bw * 8 / 1000:.0f} kbps)")
    print(f"  Upload:   {total_ul/1024**3:.2f} GB")
    print(f"  Download: {total_dl/1024**3:.2f} GB")
    print(f"  TV (Total): {tv_gb:.2f} GB")
    print(f"  TT (Time): {tt_s:.2f} s")
    
    # 更新 communication.json
    comm_data["MASER"][ds]["TT_S"] = round(tt_s, 2)

# 保存
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
