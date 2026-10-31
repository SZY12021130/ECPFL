#!/usr/bin/env python3
"""
全面检查并修正所有基线的通信量和通信时间计算。

原则：
- 所有方法都从 metrics.json 提取真实数据计算，不依赖 report.md 中的 Total Communication/TT。
- 上行：每个客户端上传 num_ciphertexts[r] 个密文块；下行：每个客户端下载 aggregated_ciphertexts[r] 个聚合密文块。
- 聚合密文大小 = 单个密文大小（single_ct）。
- MASER 额外包含：部分解密上传（同上行量）+ 全局明文下发（每个客户端 model_size）。
- TT = Σ_r [ max_c (upload_per_client / ul_bw_c) + max_c (download_per_client / dl_bw_c) ]

修正后同时更新 report.md 中相关字段。
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


def update_report_line(report_path, prefix, new_value):
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if prefix in line and "|" in line:
            # 定位数值单元格：prefix 后的第二个 |...| 单元格
            parts = line.split("|")
            if len(parts) >= 3:
                # 找 prefix 所在的索引
                for j, p in enumerate(parts):
                    if prefix.strip() in p.strip():
                        if j + 1 < len(parts):
                            # parts[j+1] 是 " value unit "
                            old = parts[j + 1]
                            # 保留单位：替换开头的数字
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


# 读取现有 communication.json
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
        with open(mpath, "r", encoding="utf-8") as f:
            d = json.load(f)

        n_rounds = len(d["num_ciphertexts"])

        # single_ct：用 upload_cost / num_clients_selected / num_ciphertexts
        # 取第2轮稳定值
        i = 2
        num_selected = len(d.get("selected_clients", [[]])[i]) if "selected_clients" in d else len(clients)
        if num_selected == 0:
            num_selected = len(clients)
        single_ct = d["upload_cost"][i] / num_selected / d["num_ciphertexts"][i]

        # MASER 的明文模型大小
        model_size = 0
        if method == "MASER" and "plaintext_upload" in d:
            model_size = d["plaintext_upload"][i] / num_selected

        total_ul = 0
        total_dl = 0
        total_tt = 0.0

        agg_cts = d.get("aggregated_ciphertexts")
        if agg_cts is None or len(agg_cts) != n_rounds:
            agg_cts = d["num_ciphertexts"]

        for r in range(n_rounds):
            nb_up = d["num_ciphertexts"][r]
            nb_down = agg_cts[r]

            # 每客户端每轮的上传量
            if method == "MASER":
                ul_per_client = nb_up * single_ct  # ① 加密上传
                dl_per_client = nb_down * single_ct + model_size  # ② 聚合密文 + ④ 明文
                total_ul += ul_per_client * num_selected
                total_dl += dl_per_client * num_selected
                # MASER 额外 ③ 部分解密上传
                total_ul += nb_down * single_ct * num_selected
            else:
                ul_per_client = nb_up * single_ct
                dl_per_client = nb_down * single_ct
                total_ul += ul_per_client * num_selected
                total_dl += dl_per_client * num_selected

            # TT
            max_ul_t = max(ul_per_client / c["ul_bw"] for c in clients)
            max_dl_t = max(dl_per_client / c["dl_bw"] for c in clients)
            total_tt += max_ul_t + max_dl_t

        ul_gb = total_ul / 1024**3
        dl_gb = total_dl / 1024**3
        tv_gb = (total_ul + total_dl) / 1024**3

        print(f"\n{'='*60}")
        print(f"{method} | {ds}:")
        print(f"  客户端数={len(clients)}, 每轮选中={num_selected}, 轮数={n_rounds}")
        print(f"  single_ct={single_ct:.0f} bytes, model_size={model_size:.0f} bytes")
        print(f"  新 UV={ul_gb:.2f} GB, 新 DV={dl_gb:.2f} GB, 新 TV={tv_gb:.2f} GB, 新 TT={total_tt:.2f} s")

        # 更新 communication.json
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
        update_report_line(report_path, "Avg Aggregated CT Size /", f"{single_ct:.0f}")

        if method == "MASER":
            agg_ct_broadcast = total_ul / 2  # ② = ①
            partial_dec = total_ul / 2       # ③ = ①
            plaintext_dl = total_dl - agg_ct_broadcast  # ④
            update_report_line(report_path, "MASER ①", f"{total_ul/2/1024**2:.2f}")
            update_report_line(report_path, "MASER ②", f"{agg_ct_broadcast/1024**2:.2f}")
            update_report_line(report_path, "MASER ③", f"{partial_dec/1024**2:.2f}")
            update_report_line(report_path, "MASER ④", f"{plaintext_dl/1024**2:.2f}")

# 保存 communication.json
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
