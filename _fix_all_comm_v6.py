#!/usr/bin/env python3
"""
全面检查并修正所有基线的通信量和通信时间计算。

核心修正：
- 所有方法：聚合密文大小 = 单个密文大小（single_ct）
- MASER：
  * ① 加密上传 = num_selected × num_ciphertexts[r] × single_ct
  * ② 聚合密文广播 = num_selected × aggregated_ciphertexts[r] × single_ct
  * ③ 部分解密上传 = ②（每个客户端上传 partial decrypt 份额 = 聚合密文大小）
  * ④ 明文模型下发 = num_selected × model_size
- 非 MASER：
  * 上行 = num_selected × num_ciphertexts[r] × single_ct
  * 下行 = num_selected × aggregated_ciphertexts[r] × single_ct
- TT = Σ_r [ max_c(upload_per_client / ul_bw_c) + max_c(download_per_client / dl_bw_c) ]

同时更新各 report.md 中的 Total Communication, Total Upload, Total Download, Total Simulated Comm Time, Avg Aggregated CT Size 等字段。
"""
import json
import re
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


def parse_clients(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*kbps\s*\|\s*(\d+)\s*kbps\s*\|'
    clients = []
    for m in re.findall(pattern, content):
        clients.append({
            "cid": int(m[0]),
            "dl_bw": int(m[3]) * 1000 / 8,
            "ul_bw": int(m[4]) * 1000 / 8,
        })
    return clients


def get_sampling_rate(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"Client Sampling Rate.*?\|\s*([\d.]+)\s*\|", content)
    return float(m.group(1)) if m else 1.0


def update_report_line(report_path, prefix, new_value):
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if prefix in line and "|" in line:
            parts = line.split("|")
            for j, p in enumerate(parts):
                if prefix.strip() in p.strip():
                    if j + 1 < len(parts):
                        old = parts[j + 1]
                        m = re.match(r'(\s*)([\d.eE+-]+)(\s+.*)', old)
                        if m:
                            parts[j + 1] = m.group(1) + new_value + m.group(3)
                        else:
                            parts[j + 1] = " " + new_value + " "
                        lines[i] = "|".join(parts)
                        if not lines[i].endswith("\n"):
                            lines[i] += "\n"
                    break
            break
    with open(report_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


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
        sampling_rate = get_sampling_rate(report_path)
        with open(mpath, "r", encoding="utf-8") as f:
            d = json.load(f)

        n_rounds = len(d["upload_cost"])
        num_clients = len(clients)
        expected_selected = max(1, round(num_clients * sampling_rate))

        if "selected_clients" in d and len(d["selected_clients"]) == n_rounds:
            num_selected_per_round = [len(sc) if sc else expected_selected for sc in d["selected_clients"]]
        else:
            num_selected_per_round = [expected_selected] * n_rounds

        stride = len(d["num_ciphertexts"]) // n_rounds
        i = 2
        nb_up_per_client = d["num_ciphertexts"][i * stride]
        if method == "MASER":
            single_ct = d["maser_ct_upload"][i] / num_selected_per_round[i] / nb_up_per_client
        else:
            single_ct = d["upload_cost"][i] / num_selected_per_round[i] / nb_up_per_client

        agg_cts_raw = d.get("aggregated_ciphertexts", [])
        if len(agg_cts_raw) == n_rounds * 2:
            agg_cts_per_round = agg_cts_raw[::2]
        elif len(agg_cts_raw) == n_rounds:
            agg_cts_per_round = agg_cts_raw
        else:
            agg_cts_per_round = [nb_up_per_client] * n_rounds

        model_size_per_client = 0
        if method == "MASER":
            if "plaintext_size" in d:
                model_size_per_client = d["plaintext_size"][i]
            elif "maser_plaintext_download" in d:
                model_size_per_client = d["maser_plaintext_download"][i] / num_selected_per_round[i]

        total_ul = 0
        total_dl = 0
        total_tt = 0.0
        total_ul_tt = 0.0
        total_dl_tt = 0.0
        total_1 = 0  # MASER ①
        total_2 = 0  # MASER ②
        total_3 = 0  # MASER ③
        total_4 = 0  # MASER ④

        for r in range(n_rounds):
            n_sel = num_selected_per_round[r]
            nb_up = d["num_ciphertexts"][r * stride]
            nb_down = agg_cts_per_round[r]

            ul_client = nb_up * single_ct
            dl_client = nb_down * single_ct

            if method == "MASER":
                # 模拟：聚合密文 = 单个密文
                # ① 加密上传：n_sel * nb_up * single_ct
                c1 = n_sel * ul_client
                # ② 聚合密文广播：n_sel * nb_down * single_ct
                c2 = n_sel * dl_client
                # ③ 部分解密上传 = ②（每个客户端对聚合密文做部分解密）
                c3 = c2
                # ④ 明文模型下发：n_sel * model_size
                c4 = n_sel * model_size_per_client

                ul_this_round = c1 + c3
                dl_this_round = c2 + c4

                total_1 += c1
                total_2 += c2
                total_3 += c3
                total_4 += c4
                
                # MASER TT 计算：4 个步骤分别计算
                max_c1_t = max(ul_client / c["ul_bw"] for c in clients)
                max_c2_t = max(dl_client / c["dl_bw"] for c in clients)
                max_c3_t = max(dl_client / c["ul_bw"] for c in clients)  # ③ = ②
                max_c4_t = max(model_size_per_client / c["dl_bw"] for c in clients)
                
                total_ul_tt += max_c1_t + max_c3_t
                total_dl_tt += max_c2_t + max_c4_t
                total_tt += max_c1_t + max_c2_t + max_c3_t + max_c4_t
            elif method == "FedPHE":
                # FedPHE 上行稀疏化，但下行广播完整模型密文
                ul_this_round = n_sel * ul_client
                dl_this_round = d["download_cost"][r]
                
                ul_per_client_for_tt = ul_this_round / n_sel
                dl_per_client_for_tt = dl_this_round / n_sel

                max_ul_t = max(ul_per_client_for_tt / c["ul_bw"] for c in clients)
                max_dl_t = max(dl_per_client_for_tt / c["dl_bw"] for c in clients)
                total_ul_tt += max_ul_t
                total_dl_tt += max_dl_t
                total_tt += max_ul_t + max_dl_t
            else:
                # FedAvg+CKKS, ESAFL: 下行 = 聚合密文 = 单个密文
                ul_this_round = n_sel * ul_client
                dl_this_round = n_sel * dl_client
                
                ul_per_client_for_tt = ul_this_round / n_sel
                dl_per_client_for_tt = dl_this_round / n_sel

                max_ul_t = max(ul_per_client_for_tt / c["ul_bw"] for c in clients)
                max_dl_t = max(dl_per_client_for_tt / c["dl_bw"] for c in clients)
                total_ul_tt += max_ul_t
                total_dl_tt += max_dl_t
                total_tt += max_ul_t + max_dl_t

            total_ul += ul_this_round
            total_dl += dl_this_round

        ul_gb = total_ul / 1024**3
        dl_gb = total_dl / 1024**3
        tv_gb = (total_ul + total_dl) / 1024**3

        print(f"\n{'='*60}")
        print(f"{method} | {ds}:")
        print(f"  客户端数={num_clients}, 采样率={sampling_rate}, 轮数={n_rounds}")
        print(f"  single_ct={single_ct:.0f} bytes, model_size={model_size_per_client:.0f} bytes")
        print(f"  新 UV={ul_gb:.2f} GB, 新 DV={dl_gb:.2f} GB, 新 TV={tv_gb:.2f} GB, 新 TT={total_tt:.2f} s")
        if method == "MASER":
            print(f"  MASER ①={total_1/1024**2:.2f} MB, ②={total_2/1024**2:.2f} MB, ③={total_3/1024**2:.2f} MB, ④={total_4/1024**2:.2f} MB")

        if method not in comm_data:
            comm_data[method] = {}
        if ds not in comm_data[method]:
            comm_data[method][ds] = {}
        comm_data[method][ds].update({
            "UV_GB": round(ul_gb, 2),
            "DV_GB": round(dl_gb, 2),
            "TV_GB": round(tv_gb, 2),
            "TT_S": round(total_tt, 2),
            "UV_bytes": total_ul,
            "DV_bytes": total_dl,
        })

        # 更新 report.md
        update_report_line(report_path, "Total Upload /", f"{total_ul/1024**2:.2f}")
        update_report_line(report_path, "Total Download /", f"{total_dl/1024**2:.2f}")
        update_report_line(report_path, "Total Communication /", f"{(total_ul+total_dl)/1024**2:.2f}")
        update_report_line(report_path, "Total Simulated Comm Time /", f"{total_tt:.2f}")
        update_report_line(report_path, "CT Upload Time /", f"{total_ul_tt:.2f}")
        update_report_line(report_path, "CT Download Time /", f"{total_dl_tt:.2f}")
        update_report_line(report_path, "Avg Aggregated CT Size /", f"{single_ct:.0f}")

        if method == "MASER":
            update_report_line(report_path, "MASER ①", f"{total_1/1024**2:.2f}")
            update_report_line(report_path, "MASER ②", f"{total_2/1024**2:.2f}")
            update_report_line(report_path, "MASER ③", f"{total_3/1024**2:.2f}")
            update_report_line(report_path, "MASER ④", f"{total_4/1024**2:.2f}")

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)
print(f"\n[OK] 已更新: {COMM_JSON}")

# 生成 LaTeX 表格
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
    if ri == 4: return UN_KEYS[ds]
    if ri == 5: return TH_ACC[ds]
    if ri == 6: return RK_ACC[ds]

def get_comm_key(ri, ds):
    if ri <= 3: return TABLE_ROWS[ri][2]
    if ri == 4: return UN_KEYS[ds]
    if ri == 5: return TH_COMM[ds]
    if ri == 6: return RK_COMM[ds]

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
