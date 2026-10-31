#!/usr/bin/env python3
"""
重新计算 MASER 的 TT (通信时间)
根据修正后的 TV 和客户端带宽重新计算
"""
import json
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

MASER_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
    "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
    "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
}

# 读取现有 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

for ds, exp_dir in MASER_EXPERIMENTS.items():
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    # 从 metrics 读取带宽配置
    # bandwidths[cid] = {"download": kbps, "upload": kbps}
    bandwidths = d.get("bandwidths", {})
    
    if not bandwidths:
        print(f"[WARN] {ds}: 没有带宽数据，使用默认值")
        # 使用平均带宽 100 Mbps
        avg_dl_bw = 100 * 1024 * 1024 / 8  # bytes/s
        avg_ul_bw = 100 * 1024 * 1024 / 8  # bytes/s
    else:
        # 计算平均带宽
        dl_bws = [bw["download"] for bw in bandwidths.values()]
        ul_bws = [bw["upload"] for bw in bandwidths.values()]
        avg_dl_bw = sum(dl_bws) / len(dl_bws)
        avg_ul_bw = sum(ul_bws) / len(ul_bws)
    
    # 从 communication.json 读取修正后的 TV
    tv_gb = comm_data["MASER"][ds]["TV_GB"]
    tv_bytes = tv_gb * 1024**3
    
    # TV = Upload + Download
    # Upload = ① + ③ = 2 × Σ(25 × num_batches × single_ct)
    # Download = ② + ④ = Σ(25 × num_batches × single_ct) + Σ(model_size)
    # 所以 Upload = 2 × Download (近似)
    
    # 重新计算 Upload 和 Download
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
    # TT = Upload / avg_ul_bw + Download / avg_dl_bw
    tt_s = total_ul / avg_ul_bw + total_dl / avg_dl_bw
    
    print(f"\n{'='*60}")
    print(f"MASER {ds}:")
    print(f"  平均上行带宽: {avg_ul_bw / 1024 / 1024:.2f} MB/s")
    print(f"  平均下行带宽: {avg_dl_bw / 1024 / 1024:.2f} MB/s")
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
