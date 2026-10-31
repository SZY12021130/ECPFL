#!/usr/bin/env python3
"""
Extract end-to-end time metrics from accuracy_baseline/*/result_fix_pro.
Output: accuracy_baseline/analysis/time_data.json
"""
import json, os, re, sys

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OUT_PATH = os.path.join(PROJECT_ROOT, "accuracy_baseline", "analysis", "time_data.json")

DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER", "ECPFL-UN", "ECPFL-TH", "ECPFL-RK"]
ROUNDS = 50

BASELINE_DIRS = {
    ("MNIST", "FedAvg+CKKS"): "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
    ("FMNIST", "FedAvg+CKKS"): "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
    ("CIFAR-10", "FedAvg+CKKS"): "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
    ("SVHN", "FedAvg+CKKS"): "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn",
    ("MNIST", "FedPHE"): "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist",
    ("FMNIST", "FedPHE"): "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist",
    ("CIFAR-10", "FedPHE"): "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10",
    ("SVHN", "FedPHE"): "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn",
    ("MNIST", "ESAFL"): "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist",
    ("FMNIST", "ESAFL"): "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist",
    ("CIFAR-10", "ESAFL"): "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10",
    ("SVHN", "ESAFL"): "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn",
    ("MNIST", "MASER"): "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
    ("FMNIST", "MASER"): "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
    ("CIFAR-10", "MASER"): "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
    ("SVHN", "MASER"): "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
}

OURS_DIRS = {
    ("MNIST", "ECPFL-UN"): "accuracy_baseline/ours/result_fix_pro/20260605_mnist_union",
    ("MNIST", "ECPFL-TH"): "accuracy_baseline/ours/result_fix_pro/20260604_mnist_threshold_pct_0.1",
    ("MNIST", "ECPFL-RK"): "accuracy_baseline/ours/result/mnist_rk",
    ("FMNIST", "ECPFL-UN"): "accuracy_baseline/ours/result_fix_pro/20260605_fashion_mnist_union",
    ("FMNIST", "ECPFL-TH"): "accuracy_baseline/ours/result_fix_pro/20260604_fashion_mnist_threshold_pct_0.3",
    ("FMNIST", "ECPFL-RK"): "accuracy_baseline/ours/result/fashion_mnist_rk",
    ("CIFAR-10", "ECPFL-UN"): "accuracy_baseline/ours/result_fix_pro/20260605_cifar10_union",
    ("CIFAR-10", "ECPFL-TH"): "accuracy_baseline/ours/result_fix_pro/20260604_cifar10_threshold_pct_0.7",
    ("CIFAR-10", "ECPFL-RK"): "accuracy_baseline/ours/result/cifar10_rk",
    ("SVHN", "ECPFL-UN"): "accuracy_baseline/ours/result_fix_pro/experiment_20260624_194053_svhn_union",
    ("SVHN", "ECPFL-TH"): "accuracy_baseline/ours/result_fix_pro/experiment_20260624_204358_svhn_th",
    ("SVHN", "ECPFL-RK"): "accuracy_baseline/ours/result/svhn_rk",
}

def parse_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        text = f.read()

    def extract(pattern):
        m = re.search(pattern, text)
        return float(m.group(1)) if m else None

    total = extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s")
    comm = extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s")
    return {"total_time": total, "comm_time": comm}


def compute_time_from_metrics(exp_dir):
    """
    Estimate the compute-only critical-path time from metrics.json.
    Per round: max(local_train) + max(encryption) + aggregation
    For ECPFL: additionally + max(apply) + max(fetch) + max(prefetch) + prefetch_server_encrypt.
    """
    metrics_path = os.path.join(exp_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        return None
    with open(metrics_path, "r", encoding="utf-8") as f:
        d = json.load(f)

    def per_round_max(arr):
        if not isinstance(arr, list) or len(arr) == 0:
            return [0.0] * ROUNDS
        n = len(arr)
        per_client = n // ROUNDS
        if per_client == 0:
            return [0.0] * ROUNDS
        return [max(arr[r * per_client:(r + 1) * per_client]) for r in range(ROUNDS)]

    local_train = per_round_max(d.get("local_train_time"))
    encryption = per_round_max(d.get("encryption_time"))
    aggregation = d.get("aggregation_time") or [0.0] * ROUNDS
    if not isinstance(aggregation, list) or len(aggregation) != ROUNDS:
        aggregation = [0.0] * ROUNDS

    apply_t = per_round_max(d.get("apply_time"))
    fetch_t = per_round_max(d.get("fetch_time"))
    prefetch_t = per_round_max(d.get("prefetch_time"))
    prefetch_server = d.get("prefetch_server_encrypt_time") or [0.0] * ROUNDS
    if not isinstance(prefetch_server, list) or len(prefetch_server) != ROUNDS:
        prefetch_server = [0.0] * ROUNDS

    total = 0.0
    for r in range(ROUNDS):
        total += (
            local_train[r] + encryption[r] + aggregation[r]
            + apply_t[r] + fetch_t[r] + prefetch_t[r] + prefetch_server[r]
        )
    return total


def fallback_from_metrics(exp_dir):
    """If report lacks total/comm time, try metrics.json."""
    metrics_path = os.path.join(exp_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        return {}
    with open(metrics_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    out = {}
    # total round time (per-round wall-clock)
    for key in ["total_round_time_simulated", "total_round_time", "total_round_real_time"]:
        vals = d.get(key)
        if isinstance(vals, list) and len(vals) > 0:
            out["total_time"] = sum(vals)
            break
    # comm time: upload + download (per-round max)
    up = d.get("upload_time")
    down = d.get("download_time")
    if isinstance(up, list) and isinstance(down, list) and len(up) > 0:
        out["comm_time"] = sum(up) + sum(down)
    return out


data = {ds: {m: None for m in METHODS} for ds in DATASETS}

for ds in DATASETS:
    for method in ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER"]:
        exp_dir = os.path.join(PROJECT_ROOT, BASELINE_DIRS[(ds, method)])
        rep = parse_report(os.path.join(exp_dir, "report.md"))
        if rep["total_time"] is None:
            rep.update(fallback_from_metrics(exp_dir))
        total = rep.get("total_time")
        report_comm = rep.get("comm_time")
        compute = compute_time_from_metrics(exp_dir)
        if total is None:
            total = compute + (report_comm or 0.0)
        if compute is None:
            compute = total - report_comm if report_comm is not None else None
        # ensure non-negative residual communication
        if compute is not None and total is not None:
            if compute > total:
                compute = total
            comm = total - compute
        else:
            comm = report_comm
        data[ds][method] = {
            "total_time": total,
            "comm_time": comm,
            "compute_time": compute,
            "report_comm_time": report_comm,
        }

for (ds, method), rel_dir in OURS_DIRS.items():
    exp_dir = os.path.join(PROJECT_ROOT, rel_dir)
    rep = parse_report(os.path.join(exp_dir, "report.md"))
    if rep["total_time"] is None:
        rep.update(fallback_from_metrics(exp_dir))
    total = rep.get("total_time")
    report_comm = rep.get("comm_time")
    compute = compute_time_from_metrics(exp_dir)
    if total is None:
        total = compute + (report_comm or 0.0)
    if compute is None:
        compute = total - report_comm if report_comm is not None else None
    if compute is not None and total is not None:
        if compute > total:
            compute = total
        comm = total - compute
    else:
        comm = report_comm
    data[ds][method] = {
        "total_time": total,
        "comm_time": comm,
        "compute_time": compute,
        "report_comm_time": report_comm,
    }

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[OK] Saved {OUT_PATH}")
# quick sanity print
for ds in DATASETS:
    print(f"\n{ds}")
    for m in METHODS:
        v = data[ds][m]
        if v:
            print(f"  {m:12s}: total={v['total_time']:10.2f}s  comm={v['comm_time']:10.2f}s  compute={v['compute_time']:10.2f}s")
