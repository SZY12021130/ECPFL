#!/usr/bin/env python3
"""
重新计算 MASER 通信量：假设聚合密文大小 = 单个密文大小
然后更新 communication.json 和 LaTeX 表格
"""
import json
import math
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

MASER_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
    "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
    "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
}

NUM_SELECTED = 25

# 1. 重新计算 MASER 通信量
new_maser = {}

for ds, exp_dir in MASER_EXPERIMENTS.items():
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath) as f:
        d = json.load(f)

    total_ct_upload = sum(d["maser_ct_upload"])
    total_agg_orig = sum(d["maser_agg_ct_download"])
    total_pd_orig = sum(d["maser_partial_dec_upload"])
    total_plain = sum(d["maser_plaintext_download"])
    orig_ul = sum(d["upload_cost"])
    orig_dl = sum(d["download_cost"])

    # 反推单个密文大小 (取稳定轮次 i=2)
    i = 2
    ct_upload_r = d["maser_ct_upload"][i]
    n_batches = d["num_ciphertexts"][i]
    single_ct_bytes = ct_upload_r / NUM_SELECTED / n_batches

    # 重新计算: 聚合密文 = 单个密文, 每轮每客户端下载/上传 = ceil(n_batches) * single_ct
    new_total_agg = 0
    new_total_pd = 0
    for j in range(50):
        nb = math.ceil(d["num_ciphertexts"][j])  # 向上取整
        new_total_agg += NUM_SELECTED * nb * single_ct_bytes
        new_total_pd += NUM_SELECTED * nb * single_ct_bytes

    new_ul = total_ct_upload + new_total_pd
    new_dl = new_total_agg + total_plain

    print(f"\n{'='*60}")
    print(f"{ds}:")
    print(f"  single_ct = {single_ct_bytes:.0f} bytes ({single_ct_bytes/1024/1024:.2f} MB)")
    print(f"  n_batches = {n_batches}")
    print(f"  ① ct_upload:      {total_ct_upload/1024**3:.2f} GB (不变)")
    print(f"  ② agg_ct (原→新): {total_agg_orig/1024**3:.2f} → {new_total_agg/1024**3:.2f} GB")
    print(f"  ③ partial_dec (原→新): {total_pd_orig/1024**3:.2f} → {new_total_pd/1024**3:.2f} GB")
    print(f"  ④ plaintext:      {total_plain/1024**3:.2f} GB (不变)")
    print(f"  Upload  (原→新):  {orig_ul/1024**3:.2f} → {new_ul/1024**3:.2f} GB")
    print(f"  Download(原→新):  {orig_dl/1024**3:.2f} → {new_dl/1024**3:.2f} GB")

    new_maser[ds] = {
        "DV_GB": round(new_dl / 1024**3, 2),
        "UV_GB": round(new_ul / 1024**3, 2),
        "DV_bytes": new_dl,
        "UV_bytes": new_ul,
    }

# 2. 更新 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

comm_data["MASER"] = new_maser

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")

# 3. 重新生成 LaTeX 表格
with open(ACCURACY_JSON, "r", encoding="utf-8") as f:
    accuracy_data = json.load(f)

TABLE_DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]

TABLE_ROWS = [
    ("FedAvg+CKKS", "FedAvg+CKKS", "FedAvg+CKKS", False),
    ("FedPHE", "FedPHE", "FedPHE", False),
    ("ESAFL", "ESAFL", "ESAFL", False),
    ("MASER", "MASER", "MASER", False),
    ("ECPFL-UN (Ours)", None, "ECPFL-UN", True),
    ("ECPFL-TH-$\\theta$ (Ours)", None, None, True),
    ("ECPFL-RK-$\\theta$ (Ours)", None, None, True),
]

UN_ACC_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
UN_COMM_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
TH_ACC_KEYS = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
TH_COMM_KEYS = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
RK_ACC_KEYS = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
RK_COMM_KEYS = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}

def get_acc_key(row_idx, ds):
    if row_idx <= 3:
        return TABLE_ROWS[row_idx][1]
    elif row_idx == 4:
        return UN_ACC_KEYS[ds]
    elif row_idx == 5:
        return TH_ACC_KEYS[ds]
    elif row_idx == 6:
        return RK_ACC_KEYS[ds]

def get_comm_key(row_idx, ds):
    if row_idx <= 3:
        return TABLE_ROWS[row_idx][2]
    elif row_idx == 4:
        return UN_COMM_KEYS[ds]
    elif row_idx == 5:
        return TH_COMM_KEYS[ds]
    elif row_idx == 6:
        return RK_COMM_KEYS[ds]

def get_ac(row_idx, ds):
    acc_key = get_acc_key(row_idx, ds)
    vals = accuracy_data.get(ds, {}).get(acc_key, [])
    return round(vals[-1] * 100, 2) if vals else 0.0

def get_dv(row_idx, ds):
    comm_key = get_comm_key(row_idx, ds)
    return comm_data.get(comm_key, {}).get(ds, {}).get("DV_GB", 0.0)

def get_uv(row_idx, ds):
    comm_key = get_comm_key(row_idx, ds)
    return comm_data.get(comm_key, {}).get(ds, {}).get("UV_GB", 0.0)

best_ac = {}
best_dv = {}
best_uv = {}
for ds in TABLE_DATASETS:
    acs = [(i, get_ac(i, ds)) for i in range(len(TABLE_ROWS))]
    dvs = [(i, get_dv(i, ds)) for i in range(len(TABLE_ROWS))]
    uvs = [(i, get_uv(i, ds)) for i in range(len(TABLE_ROWS))]
    best_ac[ds] = max(acs, key=lambda x: x[1])[0]
    best_dv[ds] = min(dvs, key=lambda x: x[1])[0]
    best_uv[ds] = min(uvs, key=lambda x: x[1])[0]

def fmt(val, is_best=False):
    s = f"{val:.2f}"
    return f"\\textbf{{{s}}}" if is_best else s

lines = []
lines.append(r"\begin{table*}[t]")
lines.append(r" \centering")
lines.append(r" \caption{Comparison of Accuracy and Communication Cost Across Datasets}")
lines.append(r" \label{tab:comm-comparison}")
lines.append(r" \resizebox{\textwidth}{!}{")
lines.append(r" \begin{tabular}{l ccc ccc ccc ccc}")
lines.append(r" \toprule")
lines.append(r" \multirow{3}{*}{\textbf{Methods}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{MNIST}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{FMNIST}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{CIFAR-10}} &")
lines.append(r" \multicolumn{3}{c}{\textbf{SVHN}} \\")
lines.append(r" \cmidrule(lr){2-4} \cmidrule(lr){5-7} \cmidrule(lr){8-10} \cmidrule(lr){11-13}")
lines.append(r" & \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.1)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.3)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.7)$} &")
lines.append(r" \multicolumn{3}{c}{\scriptsize $(\alpha=1.0, \theta=0.5)$} \\")
lines.append(r" \cmidrule(lr){2-4} \cmidrule(lr){5-7} \cmidrule(lr){8-10} \cmidrule(lr){11-13}")
lines.append(r" & \scriptsize AC (\%) & \scriptsize DV (GB) & \scriptsize UV (GB)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize DV (GB) & \scriptsize UV (GB)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize DV (GB) & \scriptsize UV (GB)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize DV (GB) & \scriptsize UV (GB) \\")
lines.append(r" \midrule")

for row_idx in range(len(TABLE_ROWS)):
    row_label = TABLE_ROWS[row_idx][0]
    is_ours = TABLE_ROWS[row_idx][3]
    if is_ours:
        lines.append(r" \rowcolor{gray!10}")
    cells = [row_label]
    for ds in TABLE_DATASETS:
        ac = get_ac(row_idx, ds)
        dv = get_dv(row_idx, ds)
        uv = get_uv(row_idx, ds)
        cells.append(fmt(ac, best_ac[ds] == row_idx))
        cells.append(fmt(dv, best_dv[ds] == row_idx))
        cells.append(fmt(uv, best_uv[ds] == row_idx))
    lines.append(" & ".join(cells) + r" \\")
    if row_idx == 3:
        lines.append(r" \midrule")

lines.append(r" \bottomrule")
lines.append(r" \end{tabular}")
lines.append(r" }")
lines.append(r" \end{table*}")

latex = "\n".join(lines)

tex_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/comm_comparison_table.tex")
with open(tex_path, "w", encoding="utf-8") as f:
    f.write(latex)

print(f"\n[OK] 已更新: {tex_path}")
print("\n" + "="*60)
print("LaTeX 表格:")
print("="*60)
print(latex)
