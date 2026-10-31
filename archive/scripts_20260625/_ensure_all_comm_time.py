#!/usr/bin/env python3
"""
确保所有 result_fix_pro 实验的 report.md 都有正确的 Total Simulated Comm Time 字段，
并更新 communication.json 中的 TT_S。

TT = 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) per round

策略：
- 优先从 report.md 中提取 CT Upload Time + CT Download Time。
- 如果 report 中没有这些字段（旧 ECPFL），从 metrics.json 的 upload_cost/download_cost
  和 report.md 中解析的客户端带宽估算。
"""
import json
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# ECPFL 实验目录 -> (方法名, 数据集) 的硬编码映射
ECPFL_EXPERIMENTS = {
    "ours/result_fix_pro/20260605_mnist_union": ("ECPFL-UN", "MNIST"),
    "ours/result_fix_pro/20260605_fashion_mnist_union": ("ECPFL-UN", "FMNIST"),
    "ours/result_fix_pro/20260605_cifar10_union": ("ECPFL-UN", "CIFAR-10"),
    "ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7": ("ECPFL-UN", "SVHN"),
    "ours/result_fix_pro/20260604_mnist_threshold_pct_0.1": ("ECPFL-TH-0.1", "MNIST"),
    "ours/result_fix_pro/20260604_fashion_mnist_threshold_pct_0.3": ("ECPFL-TH-0.3", "FMNIST"),
    "ours/result_fix_pro/20260604_cifar10_threshold_pct_0.7": ("ECPFL-TH-0.7", "CIFAR-10"),
    "ours/result_fix_pro/20260605_mnist_topk_pct_0.1": ("ECPFL-RK-0.1", "MNIST"),
    "ours/result_fix_pro/20260610_fashion_mnist_sp0.3_topk0.3": ("ECPFL-RK-0.3", "FMNIST"),
    "ours/result_fix_pro/20260605_cifar10_topk_pct_0.7": ("ECPFL-RK-0.7", "CIFAR-10"),
}

# 其他 baseline 方法在 communication.json 中的名称
BASELINE_METHODS = {
    "fedavg+ckks": "FedAvg+CKKS",
    "fedphe": "FedPHE",
    "maser": "MASER",
    "esafl": "ESAFL",
}


def dataset_from_dirname(dirname):
    """从实验目录名提取数据集名称"""
    d = dirname.lower()
    if "fashion_mnist" in d or "fmnist" in d:
        return "FMNIST"
    if "cifar10" in d or "cifar-10" in d:
        return "CIFAR-10"
    if "svhn" in d:
        return "SVHN"
    if "mnist" in d:
        return "MNIST"
    return None


def parse_client_bandwidth(report_path):
    """从 report.md 解析客户端带宽 (bytes/s)"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    clients = []
    for line in content.split("\n"):
        if re.match(r"\|\s*\d+\s*\|", line) and "CID" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                try:
                    cid = int(parts[1])
                    dl_bw_str = parts[4].replace("kbps", "").strip()
                    ul_bw_str = parts[5].replace("kbps", "").strip()
                    dl_bw_kbps = float(dl_bw_str)
                    ul_bw_kbps = float(ul_bw_str)
                    clients.append({
                        "cid": cid,
                        "dl_bw": dl_bw_kbps * 1024 / 8,
                        "ul_bw": ul_bw_kbps * 1024 / 8,
                    })
                except (ValueError, IndexError):
                    pass
    return clients


def parse_num_clients_and_sample_rate(report_path):
    """从 report.md 解析客户端数和采样率"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    num_clients = 50
    sample_rate = 0.5
    m = re.search(r"Num Clients.*?\|\s*(\d+)", content)
    if m:
        num_clients = int(m.group(1))
    m = re.search(r"Client Sampling Rate.*?\|\s*([\d.]+)", content)
    if m:
        sample_rate = float(m.group(1))
    return num_clients, sample_rate


def calc_comm_time_from_costs(metrics, clients, n_sel):
    """从 upload_cost/download_cost 估算通信时间"""
    upload_cost = metrics.get("upload_cost", [])
    download_cost = metrics.get("download_cost", [])
    num_rounds = len(upload_cost)
    total = 0.0
    for r in range(num_rounds):
        ul = upload_cost[r] if r < len(upload_cost) else 0
        dl = download_cost[r] if r < len(download_cost) else 0
        if ul > 0 or dl > 0:
            ul_per = ul / n_sel if n_sel > 0 else ul
            dl_per = dl / n_sel if n_sel > 0 else dl
            max_ul = max(ul_per / c["ul_bw"] for c in clients)
            max_dl = max(dl_per / c["dl_bw"] for c in clients) if dl_per > 0 else 0.0
            total += max_ul + max_dl
    return total


def extract_ct_times(report_path):
    """从 report.md 提取 CT Upload Time 和 CT Download Time"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    ul_match = re.search(r"CT Upload Time.*?\|\s*([\d.]+)\s*s", content)
    dl_match = re.search(r"CT Download Time.*?\|\s*([\d.]+)\s*s", content)
    if ul_match and dl_match:
        return float(ul_match.group(1)), float(dl_match.group(1))
    return None, None


def calc_comm_time(metrics_path, report_path):
    """计算纯通信时间 TT"""
    # 优先从 report.md 的 CT Upload/CT Download 提取
    ct_ul, ct_dl = extract_ct_times(report_path)
    if ct_ul is not None and ct_dl is not None:
        return ct_ul + ct_dl, "ct_times"

    # 否则从 metrics.json 的 upload_time/download_time 求和
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    upload_time = metrics.get("upload_time", [])
    download_time = metrics.get("download_time", [])
    if len(upload_time) > 0 or len(download_time) > 0:
        return sum(upload_time) + sum(download_time), "direct"

    # 最后从 upload_cost/download_cost + 带宽估算（旧 ECPFL）
    clients = parse_client_bandwidth(report_path)
    if not clients:
        return None, "no_clients"
    num_clients, sample_rate = parse_num_clients_and_sample_rate(report_path)
    n_sel = int(num_clients * sample_rate)
    tt = calc_comm_time_from_costs(metrics, clients, n_sel)
    return tt, "estimated"


def update_report_comm_time(report_path, tt_value):
    """在 report.md 中添加或更新 Total Simulated Comm Time 字段"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_line = f"| Total Simulated Comm Time / 总模拟通信时间 | {tt_value:.2f} s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |"

    # 检查是否已存在
    if re.search(r"Total Simulated Comm Time", content):
        # 替换已有行
        content_new = re.sub(
            r"\| Total Simulated Comm Time.*?\|\n",
            new_line + "\n",
            content,
        )
        updated = content_new != content
    else:
        # 在 Total Simulated Time 行之后插入
        pattern = r"(\| Total Simulated Time.*?\|\n)"
        if re.search(pattern, content):
            content_new = re.sub(pattern, r"\1" + new_line + "\n", content, count=1)
            updated = True
        else:
            content_new = content
            updated = False

    if updated:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content_new)
    return updated


def collect_all_experiments():
    """收集所有需要处理的实验"""
    experiments = []

    # ECPFL (ours)
    for rel_path, (method, dataset) in ECPFL_EXPERIMENTS.items():
        exp_dir = os.path.join(PROJECT_ROOT, "accuracy_baseline", rel_path)
        experiments.append({
            "method": method,
            "dataset": dataset,
            "path": exp_dir,
        })

    # 其他 baseline
    for baseline_dir, method_name in BASELINE_METHODS.items():
        base = os.path.join(PROJECT_ROOT, "accuracy_baseline", baseline_dir, "result_fix_pro")
        if not os.path.exists(base):
            continue
        for exp_dir in os.listdir(base):
            full_path = os.path.join(base, exp_dir)
            if not os.path.isdir(full_path):
                continue
            dataset = dataset_from_dirname(exp_dir)
            if dataset is None:
                continue
            experiments.append({
                "method": method_name,
                "dataset": dataset,
                "path": full_path,
            })

    return experiments


def main():
    with open(COMM_JSON, "r", encoding="utf-8") as f:
        comm_data = json.load(f)

    experiments = collect_all_experiments()

    print("=" * 90)
    print("确保所有 result_fix_pro 实验的 TT 正确")
    print("=" * 90)

    updated_methods = set()

    for exp in experiments:
        method = exp["method"]
        dataset = exp["dataset"]
        exp_dir = exp["path"]
        metrics_path = os.path.join(exp_dir, "metrics.json")
        report_path = os.path.join(exp_dir, "report.md")

        if not os.path.exists(metrics_path) or not os.path.exists(report_path):
            print(f"  [SKIP] {method} | {dataset} | missing files")
            continue

        tt_value, source = calc_comm_time(metrics_path, report_path)
        if tt_value is None:
            print(f"  [SKIP] {method} | {dataset} | cannot calculate")
            continue

        updated = update_report_comm_time(report_path, tt_value)

        print(f"\n  {method} | {dataset}:")
        print(f"    TT = {tt_value:.2f} s  (source: {source})")
        print(f"    Report updated: {updated}")

        # 更新 communication.json
        if method not in comm_data:
            comm_data[method] = {}
        if dataset not in comm_data[method]:
            comm_data[method][dataset] = {}
        comm_data[method][dataset]["TT_S"] = round(tt_value, 2)
        updated_methods.add(method)

    with open(COMM_JSON, "w", encoding="utf-8") as f:
        json.dump(comm_data, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] 已更新 {len(updated_methods)} 个方法的 TT_S: {COMM_JSON}")


if __name__ == "__main__":
    main()
