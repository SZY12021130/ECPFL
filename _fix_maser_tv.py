#!/usr/bin/env python3
"""
重新计算 MASER 的 TV (总通信量)
公式:
- Upload = ① + ③ = 2 × Σ(25 × num_batches × single_ct)
- Download = ② + ④ = Σ(25 × num_batches × single_ct) + Σ(model_size)
- TV = Upload + Download
"""
import json
import math
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

MASER_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
    "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
    "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
}

NUM_SELECTED = 25

# 读取现有 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

for ds, exp_dir in MASER_EXPERIMENTS.items():
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath, "r", encoding="utf-8") as f:
        d = json.load(f)

    # 从稳定轮次反推单个密文大小
    i = 2
    ct_upload_r = d.get("maser_ct_upload", [0] * 50)[i]
    n_cts = d.get("num_ciphertexts", [33] * 50)[i]
    
    # single_ct = maser_ct_upload / num_selected / num_ciphertexts
    single_ct_bytes = ct_upload_r / NUM_SELECTED / n_cts
    
    # 模型明文大小 (从 plaintext_upload 反推)
    # plaintext_upload 是每轮所有选中客户端的明文总大小
    # model_size = plaintext_upload / num_selected
    plaintext_r = d.get("plaintext_upload", [0] * 50)[i]
    model_size_bytes = plaintext_r / NUM_SELECTED

    # 重新计算 TV
    total_ul = 0
    total_dl = 0
    
    for j in range(50):
        nb = math.ceil(d["num_ciphertexts"][j])
        
        # ① 加密上传: 25 × batches × single_ct
        ct_upload = NUM_SELECTED * nb * single_ct_bytes
        
        # ② 聚合密文广播: 25 × batches × single_ct (聚合密文=单个密文)
        agg_ct_download = NUM_SELECTED * nb * single_ct_bytes
        
        # ③ 部分解密: 25 × batches × single_ct
        partial_dec_upload = NUM_SELECTED * nb * single_ct_bytes
        
        # ④ 明文下发: 25 × model_size
        plaintext_download = NUM_SELECTED * model_size_bytes
        
        total_ul += ct_upload + partial_dec_upload
        total_dl += agg_ct_download + plaintext_download
    
    tv_gb = (total_ul + total_dl) / 1024**3
    
    print(f"\n{'='*60}")
    print(f"MASER {ds}:")
    print(f"  single_ct = {single_ct_bytes:.0f} bytes ({single_ct_bytes/1024/1024:.2f} MB)")
    print(f"  model_size = {model_size_bytes:.0f} bytes ({model_size_bytes/1024/1024:.2f} MB)")
    print(f"  n_batches = {n_cts}")
    print(f"  Total Upload:   {total_ul/1024**3:.2f} GB")
    print(f"  Total Download: {total_dl/1024**3:.2f} GB")
    print(f"  TV (Total):     {tv_gb:.2f} GB")
    
    # 更新 communication.json
    if "MASER" not in comm_data:
        comm_data["MASER"] = {}
    if ds not in comm_data["MASER"]:
        comm_data["MASER"][ds] = {}
    
    comm_data["MASER"][ds]["TV_GB"] = round(tv_gb, 2)
    comm_data["MASER"][ds]["TV_bytes"] = total_ul + total_dl

# 保存
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
