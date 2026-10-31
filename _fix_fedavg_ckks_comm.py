#!/usr/bin/env python3
"""
重新计算 FedAvg+CKKS 通信量：
- Upload: 25客户端 × num_batches × single_ct_size (密文)
- Download: 25客户端 × num_batches × single_ct_size (聚合密文=单个密文)
然后更新 communication.json 和 LaTeX 表格
"""
import json
import math
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

FEDAVG_CKKS_EXPERIMENTS = {
    "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
    "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
    "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
    "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_115455_svhn",
}

NUM_SELECTED = 25

new_fedavg = {}

for ds, exp_dir in FEDAVG_CKKS_EXPERIMENTS.items():
    mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
    with open(mpath) as f:
        d = json.load(f)

    # 取稳定轮次 i=2 反推单个密文大小
    i = 2
    ct_upload_r = d["maser_ct_upload"][i] if "maser_ct_upload" in d else None
    upload_cost_r = d["upload_cost"][i]
    n_cts = d["num_ciphertexts"][i] if "num_ciphertexts" in d else None

    # FedAvg+CKKS: upload_cost = 所有选中客户端的密文总大小
    # single_ct = upload_cost / num_selected / num_ciphertexts
    if ct_upload_r is not None:
        single_ct_bytes = ct_upload_r / NUM_SELECTED / n_cts
    else:
        single_ct_bytes = upload_cost_r / NUM_SELECTED / n_cts

    # 重新计算: 聚合密文 = 单个密文
    # Upload = 25 × batches × single_ct
    # Download = 25 × batches × single_ct (聚合密文发给每个客户端)
    new_total_ul = 0
    new_total_dl = 0
    for j in range(50):
        nb = math.ceil(d["num_ciphertexts"][j]) if "num_ciphertexts" in d else math.ceil(d["num_ciphertexts"][j])
        ct_size = NUM_SELECTED * nb * single_ct_bytes
        new_total_ul += ct_size
        new_total_dl += ct_size  # 聚合密文 = 单个密文, 每个客户端下载一份

    print(f"\n{'='*60}")
    print(f"{ds}:")
    print(f"  single_ct = {single_ct_bytes:.0f} bytes ({single_ct_bytes/1024/1024:.2f} MB)")
    print(f"  n_batches = {n_cts}")
    print(f"  原 Upload:   {sum(d['upload_cost'])/1024**3:.2f} GB")
    print(f"  原 Download: {sum(d['download_cost'])/1024**3:.2f} GB")
    print(f"  新 Upload:   {new_total_ul/1024**3:.2f} GB")
    print(f"  新 Download: {new_total_dl/1024**3:.2f} GB")
    print(f"  (Upload = Download = 密文)")

    new_fedavg[ds] = {
        "DV_GB": round(new_total_dl / 1024**3, 2),
        "UV_GB": round(new_total_ul / 1024**3, 2),
        "DV_bytes": new_total_dl,
        "UV_bytes": new_total_ul,
        "TV_GB": round((new_total_dl + new_total_ul) / 1024**3, 2),  # TV = DV + UV
    }

# 更新 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

comm_data["FedAvg+CKKS"] = new_fedavg

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")

# 重新生成 LaTeX 表格
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

UN_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
TH_ACC = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
TH_COMM = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
RK_ACC = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
RK_COMM = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}

def get_acc_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][1]
    elif ri == 4: return UN_KEYS[ds]
    elif ri == 5: return TH_ACC[ds]
    elif ri == 6: return RK_ACC[ds]

def get_comm_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][2]
    elif ri == 4: return UN_KEYS[ds]
    elif ri == 5: return TH_COMM[ds]
    elif ri == 6: return RK_COMM[ds]

def get_ac(ri, ds):
    vals = accuracy_data.get(ds, {}).get(get_acc_key(ri, ds), [])
    return round(vals[-1] * 100, 2) if vals else 0.0

def get_dv(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("DV_GB", 0.0)

def get_uv(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("UV_GB", 0.0)

best_ac, best_dv, best_uv = {}, {}, {}
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
