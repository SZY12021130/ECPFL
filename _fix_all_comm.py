#!/usr/bin/env python3
"""
综合修正脚本：
1. 重新计算 FedAvg+CKKS, FedPHE, MASER, ESAFL 的 Total Communication 和 TT
2. 更新各实验的 report.md
3. 更新 communication.json
4. 更新 LaTeX 表格

核心修正：
- 所有方法：聚合密文 = 单个密文 (single_ct)
- Download = Upload (密文大小)
- TT = Σ max(client_upload_time) + Σ max(client_download_time)
"""
import json
import re
import math
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

EXPERIMENTS = {
    "FedAvg+CKKS": {
        "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
        "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_115455_svhn",
    },
    "FedPHE": {
        "MNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist",
        "FMNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10",
        "SVHN": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn",
    },
    "MASER": {
        "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
        "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
        "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
    },
    "ESAFL": {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn",
    },
}

NUM_ROUNDS = 50


def parse_clients(report_path):
    """从 report 解析客户端带宽"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*kbps\s*\|\s*(\d+)\s*kbps\s*\|'
    clients = []
    for m in re.findall(pattern, content):
        clients.append({
            "cid": int(m[0]), "dl_bw": int(m[3]) * 1000 / 8, "ul_bw": int(m[4]) * 1000 / 8
        })
    return clients


def get_orig_report_vals(report_path):
    """从 report 提取原始 Total Communication 和 TT"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    tv_m = re.search(r"Total Communication.*?\|\s*([\d.]+)\s*MB", content)
    tt_m = re.search(r"Total Simulated Comm Time.*?\|\s*([\d.-]+)\s*s", content)
    return (float(tv_m.group(1)) if tv_m else None, float(tt_m.group(1)) if tt_m else None)


def update_report_line(report_path, metric_prefix, new_value_str):
    """更新 report 中某指标行的数值"""
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if metric_prefix in line and "|" in line:
            # 匹配: | prefix | value unit | description |
            m = re.match(r'(\|\s*' + re.escape(metric_prefix) + r'\s*\|\s*)([\d.e+-]+)(\s*.+\|)', line)
            if m:
                lines[i] = m.group(1) + new_value_str + m.group(3)
                if not lines[i].endswith('\n'):
                    lines[i] += '\n'
                break
    with open(report_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# 读取 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

for method, datasets in EXPERIMENTS.items():
    for ds, exp_dir in datasets.items():
        report_path = os.path.join(PROJECT_ROOT, exp_dir, "report.md")
        mpath = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")

        if not os.path.exists(report_path) or not os.path.exists(mpath):
            print(f"[SKIP] {method} | {ds}: 文件不存在")
            continue

        clients = parse_clients(report_path)
        orig_tv_mb, orig_tt = get_orig_report_vals(report_path)

        with open(mpath, "r", encoding="utf-8") as f:
            d = json.load(f)

        # 获取 single_ct
        i = 2
        if "maser_ct_upload" in d:
            n_cts = d["num_ciphertexts"][i]
            single_ct = d["maser_ct_upload"][i] / len(clients) / n_cts
        else:
            n_cts = d["num_ciphertexts"][i]
            single_ct = d["upload_cost"][i] / len(clients) / n_cts

        # 获取明文模型大小 (用于 MASER ④)
        model_size = 0
        if method == "MASER" and "plaintext_upload" in d:
            model_size = d["plaintext_upload"][i] / len(clients)

        # 逐轮计算
        total_ul = 0
        total_dl = 0
        total_tt = 0.0

        for r in range(NUM_ROUNDS):
            nb = d["num_ciphertexts"][r]
            ct_per_client = nb * single_ct  # 每客户端每轮的密文量

            if method == "MASER":
                # ① 加密上传 + ③ 部分解密 = 2 × ct
                ul_per_client = 2 * ct_per_client
                # ② 聚合密文广播 + ④ 明文下发 = ct + model
                dl_per_client = ct_per_client + model_size
            else:
                # Upload = ct, Download = ct (聚合密文=单个密文)
                ul_per_client = ct_per_client
                dl_per_client = ct_per_client

            total_ul += ul_per_client * len(clients)
            total_dl += dl_per_client * len(clients)

            # TT: 每轮最慢客户端
            max_ul_t = max(ul_per_client / c["ul_bw"] for c in clients)
            max_dl_t = max(dl_per_client / c["dl_bw"] for c in clients)
            total_tt += max_ul_t + max_dl_t

        tv_gb = (total_ul + total_dl) / 1024**3
        ul_gb = total_ul / 1024**3
        dl_gb = total_dl / 1024**3

        print(f"\n{'='*60}")
        print(f"{method} | {ds}:")
        print(f"  single_ct = {single_ct:.0f} bytes ({single_ct/1024/1024:.2f} MB)")
        print(f"  原 TV = {orig_tv_mb:.2f} MB, 原 TT = {orig_tt:.2f} s")
        print(f"  新 TV = {tv_gb:.2f} GB ({tv_gb*1024:.2f} MB)")
        print(f"  新 UL = {ul_gb:.2f} GB, 新 DL = {dl_gb:.2f} GB")
        print(f"  新 TT = {total_tt:.2f} s")

        # 更新 communication.json
        if method not in comm_data:
            comm_data[method] = {}
        if ds not in comm_data[method]:
            comm_data[method][ds] = {}
        comm_data[method][ds]["TV_GB"] = round(tv_gb, 2)
        comm_data[method][ds]["TT_S"] = round(total_tt, 2)
        comm_data[method][ds]["DV_GB"] = round(dl_gb, 2)
        comm_data[method][ds]["UV_GB"] = round(ul_gb, 2)

        # 更新 report.md
        if method == "FedAvg+CKKS":
            update_report_line(report_path, "Total Download /", f"{total_dl/1024**2:.2f}")
            update_report_line(report_path, "Total Communication /", f"{(total_ul+total_dl)/1024**2:.2f}")
            update_report_line(report_path, "Total Simulated Comm Time /", f"{total_tt:.2f}")

        elif method == "FedPHE":
            update_report_line(report_path, "Total Download /", f"{total_dl/1024**2:.2f}")
            update_report_line(report_path, "Total Communication /", f"{(total_ul+total_dl)/1024**2:.2f}")
            update_report_line(report_path, "Total Simulated Comm Time /", f"{total_tt:.2f}")

        elif method == "MASER":
            agg_ct_broadcast = total_ul / 2  # ② = ①
            partial_dec = total_ul / 2  # ③ = ①
            plaintext_dl = total_dl - agg_ct_broadcast  # ④
            update_report_line(report_path, "MASER ②", f"{agg_ct_broadcast/1024**2:.2f}")
            update_report_line(report_path, "MASER ③", f"{partial_dec/1024**2:.2f}")
            update_report_line(report_path, "Total Upload /", f"{total_ul/1024**2:.2f}")
            update_report_line(report_path, "Total Download /", f"{total_dl/1024**2:.2f}")
            update_report_line(report_path, "Total Communication /", f"{(total_ul+total_dl)/1024**2:.2f}")
            update_report_line(report_path, "Avg Aggregated CT Size /", f"{single_ct:.0f}")
            update_report_line(report_path, "Total Simulated Comm Time /", f"{total_tt:.2f}")

        elif method == "ESAFL":
            update_report_line(report_path, "Avg Aggregated CT Size /", f"{single_ct:.0f}")
            update_report_line(report_path, "Total Download /", f"{total_dl/1024**2:.2f}")
            update_report_line(report_path, "Total Communication /", f"{(total_ul+total_dl)/1024**2:.2f}")

# 保存 communication.json
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)
print(f"\n[OK] 已更新: {COMM_JSON}")

# 更新 LaTeX 表格
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

UN_KEYS = {d: "ECPFL-UN" for d in TABLE_DATASETS}
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

def get_tv(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TV_GB", 0.0)

def get_tt(ri, ds):
    return comm_data.get(get_comm_key(ri, ds), {}).get(ds, {}).get("TT_S", 0.0)

best_ac, best_tv, best_tt = {}, {}, {}
for ds in TABLE_DATASETS:
    best_ac[ds] = max(range(len(TABLE_ROWS)), key=lambda i: get_ac(i, ds))
    best_tv[ds] = min(range(len(TABLE_ROWS)), key=lambda i: get_tv(i, ds))
    best_tt[ds] = min(range(len(TABLE_ROWS)), key=lambda i: get_tt(i, ds))

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
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S)")
lines.append(r" & \scriptsize AC (\%) & \scriptsize TV (GB) & \scriptsize TT (S) \\")
lines.append(r" \midrule")

for row_idx in range(len(TABLE_ROWS)):
    row_label = TABLE_ROWS[row_idx][0]
    is_ours = TABLE_ROWS[row_idx][3]
    if is_ours:
        lines.append(r" \rowcolor{gray!10}")
    cells = [row_label]
    for d in TABLE_DATASETS:
        cells.append(fmt(get_ac(row_idx, d), best_ac[d] == row_idx))
        cells.append(fmt(get_tv(row_idx, d), best_tv[d] == row_idx))
        cells.append(fmt(get_tt(row_idx, d), best_tt[d] == row_idx))
    lines.append(" & ".join(cells) + r" \\")
    if row_idx == 3:
        lines.append(r" \midrule")

lines.append(r" \bottomrule")
lines.append(r" \end{tabular}")
lines.append(r" }")
lines.append(r" \end{table*}")

tex_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/comm_comparison_table.tex")
with open(tex_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n[OK] 已更新: {tex_path}")
print("\n" + "="*60)
print("LaTeX 表格:")
print("="*60)
print("\n".join(lines))
