#!/usr/bin/env python3
"""
验证所有 result_fix_pro 实验的 report.md 都有 Total Simulated Comm Time 字段，
且与 communication.json 中的 TT_S 一致。
"""
import json
import os
import re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

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

BASELINE_METHODS = {
    "fedavg+ckks": "FedAvg+CKKS",
    "fedphe": "FedPHE",
    "maser": "MASER",
    "esafl": "ESAFL",
}


def dataset_from_dirname(dirname):
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


def extract_report_tt(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s", content)
    return float(match.group(1)) if match else None


def main():
    with open(COMM_JSON, "r", encoding="utf-8") as f:
        comm_data = json.load(f)

    print("=" * 90)
    print("验证所有 result_fix_pro 实验的 Total Simulated Comm Time")
    print("=" * 90)

    all_ok = True

    # 验证 ECPFL
    for rel_path, (method, dataset) in ECPFL_EXPERIMENTS.items():
        report_path = os.path.join(PROJECT_ROOT, "accuracy_baseline", rel_path, "report.md")
        report_tt = extract_report_tt(report_path)
        comm_tt = comm_data.get(method, {}).get(dataset, {}).get("TT_S")
        status = "OK" if report_tt == comm_tt else "MISMATCH"
        if status == "MISMATCH":
            all_ok = False
        print(f"  {method} | {dataset}: report={report_tt}, comm={comm_tt} [{status}]")

    # 验证其他 baseline
    for baseline_dir, method_name in BASELINE_METHODS.items():
        base = os.path.join(PROJECT_ROOT, "accuracy_baseline", baseline_dir, "result_fix_pro")
        if not os.path.exists(base):
            continue
        for exp_dir in sorted(os.listdir(base)):
            full_path = os.path.join(base, exp_dir)
            if not os.path.isdir(full_path):
                continue
            dataset = dataset_from_dirname(exp_dir)
            if dataset is None:
                continue
            report_path = os.path.join(full_path, "report.md")
            report_tt = extract_report_tt(report_path)
            comm_tt = comm_data.get(method_name, {}).get(dataset, {}).get("TT_S")
            status = "OK" if report_tt == comm_tt else "MISMATCH"
            if status == "MISMATCH":
                all_ok = False
            print(f"  {method_name} | {dataset}: report={report_tt}, comm={comm_tt} [{status}]")

    print("\n" + "=" * 90)
    if all_ok:
        print("[PASS] 所有报告和 communication.json 一致")
    else:
        print("[FAIL] 存在不一致")


if __name__ == "__main__":
    main()
