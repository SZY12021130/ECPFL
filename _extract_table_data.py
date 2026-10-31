#!/usr/bin/env python3
"""提取所有方法的通信量数据（DV/UV），生成 communication.json 和 LaTeX 表格"""
import json
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
ACCURACY_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# 各方法各数据集的实验目录
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
    "ECPFL-UN": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260605_mnist_union",
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260605_fashion_mnist_union",
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260605_cifar10_union",
        "SVHN": "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7",
    },
    "ECPFL-TH-0.1": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260604_mnist_threshold_pct_0.1",
    },
    "ECPFL-TH-0.3": {
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260604_fashion_mnist_threshold_pct_0.3",
    },
    "ECPFL-TH-0.7": {
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260604_cifar10_threshold_pct_0.7",
        # SVHN 无 threshold 实验，使用 topk 实验的通信量
        "SVHN": "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7",
    },
    "ECPFL-RK-0.1": {
        "MNIST": "accuracy_baseline/ours/result_fix_pro/20260605_mnist_topk_pct_0.1",
    },
    "ECPFL-RK-0.3": {
        "FMNIST": "accuracy_baseline/ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3",
    },
    "ECPFL-RK-0.7": {
        "CIFAR-10": "accuracy_baseline/ours/result_fix_pro/20260605_cifar10_topk_pct_0.7",
        "SVHN": "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7",
    },
}


def extract_comm(metrics_path):
    """从 metrics.json 提取总 download 和 upload 通信量（字节）"""
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    dl_costs = data.get("download_cost", [])
    ul_costs = data.get("upload_cost", [])
    
    total_dl = sum(dl_costs)
    total_ul = sum(ul_costs)
    
    return total_dl, total_ul


def main():
    # 读取准确率
    with open(ACCURACY_JSON, "r", encoding="utf-8") as f:
        accuracy_data = json.load(f)
    
    comm_data = {}
    
    for method, datasets in EXPERIMENTS.items():
        comm_data[method] = {}
        for dataset, exp_dir in datasets.items():
            metrics_path = os.path.join(PROJECT_ROOT, exp_dir, "metrics.json")
            if not os.path.exists(metrics_path):
                print(f"[WARN] 文件不存在: {metrics_path}")
                continue
            try:
                total_dl, total_ul = extract_comm(metrics_path)
                dv_gb = total_dl / (1024**3)
                uv_gb = total_ul / (1024**3)
                comm_data[method][dataset] = {
                    "DV_GB": round(dv_gb, 2),
                    "UV_GB": round(uv_gb, 2),
                    "DV_bytes": total_dl,
                    "UV_bytes": total_ul,
                }
                print(f"[OK] {method} | {dataset}: DV={dv_gb:.2f} GB, UV={uv_gb:.2f} GB")
            except Exception as e:
                print(f"[ERR] {method} | {dataset}: {e}")
    
    # 保存 communication.json
    with open(COMM_JSON, "w", encoding="utf-8") as f:
        json.dump(comm_data, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] 已保存: {COMM_JSON}")
    
    # 构建表格数据
    # accuracy.json 中方法名 -> 数据集列
    # comm_data 中方法名 -> 数据集列
    TABLE_DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
    
    # 表格行定义: (显示名, accuracy_json中的方法名, comm_json中的方法名, 是否Ours)
    TABLE_ROWS = [
        ("FedAvg+CKKS", "FedAvg+CKKS", "FedAvg+CKKS", False),
        ("FedPHE", "FedPHE", "FedPHE", False),
        ("ESAFL", "ESAFL", "ESAFL", False),
        ("MASER", "MASER", "MASER", False),
        ("ECPFL-UN (Ours)", None, "ECPFL-UN", True),  # UN 在各数据集用不同 key
        ("ECPFL-TH-$\\theta$ (Ours)", None, None, True),  # TH 在各数据集用不同 key
        ("ECPFL-RK-$\\theta$ (Ours)", None, None, True),  # RK 在各数据集用不同 key
    ]
    
    # UN/TH/RK 在各数据集对应的 accuracy_json key 和 comm_json key
    UN_ACC_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
    UN_COMM_KEYS = {"MNIST": "ECPFL-UN", "FMNIST": "ECPFL-UN", "CIFAR-10": "ECPFL-UN", "SVHN": "ECPFL-UN"}
    
    TH_ACC_KEYS = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
    TH_COMM_KEYS = {"MNIST": "ECPFL-TH-0.1", "FMNIST": "ECPFL-TH-0.3", "CIFAR-10": "ECPFL-TH-0.7", "SVHN": "ECPFL-TH-0.7"}
    
    RK_ACC_KEYS = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
    RK_COMM_KEYS = {"MNIST": "ECPFL-RK-0.1", "FMNIST": "ECPFL-RK-0.3", "CIFAR-10": "ECPFL-RK-0.7", "SVHN": "ECPFL-RK-0.7"}
    
    def get_acc_key(row_idx, ds):
        if row_idx <= 3:
            return TABLE_ROWS[row_idx][1]  # baseline method name
        elif row_idx == 4:
            return UN_ACC_KEYS[ds]
        elif row_idx == 5:
            return TH_ACC_KEYS[ds]
        elif row_idx == 6:
            return RK_ACC_KEYS[ds]
    
    def get_comm_key(row_idx, ds):
        if row_idx <= 3:
            return TABLE_ROWS[row_idx][2]  # baseline method name
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
    
    # 找最佳值
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
    
    # 生成 LaTeX
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
    print("\n" + "=" * 80)
    print("LaTeX 表格:")
    print("=" * 80)
    print(latex)
    
    tex_path = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/comm_comparison_table.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"\n[OK] 已保存: {tex_path}")


if __name__ == "__main__":
    main()
