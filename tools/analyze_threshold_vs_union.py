#!/usr/bin/env python3
"""
Threshold vs Union mask vote 上传量对比
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

OUT_DIR = Path("communication")
OUT_DIR.mkdir(exist_ok=True)

def extract_comm(log_path):
    pattern = re.compile(
        r"通信汇总:\s*↑([\d.]+)\s*MB\s*\|"
        r".*?FV\(fetch[^)]*\)=([\d.]+)\s*(?:MB|B)\s*\|"
        r".*?effective[^=]+?=([\d.]+)\s*MB"
    )
    uploads = []
    downloads = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                uploads.append(float(m.group(1)))
                downloads.append(float(m.group(3)))
    return uploads, downloads

# Union 实验（之前的结果）
union_logs = {
    "MNIST": "results/experiment_20260603_101807/experiment.log",
    "Fashion-MNIST": "results/experiment_20260602_182454/experiment.log",
    "CIFAR-10": "results/experiment_20260603_115420/experiment.log",
}

# Threshold 实验
threshold_logs = {
    "MNIST": "results/experiment_mnist_threshold.log",
    "Fashion-MNIST": "results/experiment_fashion_threshold.log",
    "CIFAR-10": "results/experiment_cifar10_threshold.log",
}

# 不预取 baseline
noprefetch_logs = {
    "MNIST": "accuracy_noprefetch/mnist-lenet/experiment_20260530_155103/experiment.log",
    "Fashion-MNIST": "accuracy_noprefetch/fashion_mnist-cnn_fmnist/experiment_20260530_183600/experiment.log",
    "CIFAR-10": "accuracy_noprefetch/cifar10-resnet20/experiment_20260530_221101/experiment.log",
}

def extract_noprefetch_upload(log_path):
    pattern = re.compile(r"上传总量=([\d.]+)\s*MB")
    uploads = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                uploads.append(float(m.group(1)))
    return uploads

print("=" * 70)
print("Union vs Threshold vs No-Prefetch 上传量对比 (50轮总计)")
print("=" * 70)

data = {}
for ds in ["MNIST", "Fashion-MNIST", "CIFAR-10"]:
    # Union (prefetch)
    u_up, u_dl = extract_comm(union_logs[ds])
    # Threshold (prefetch)
    t_up, t_dl = extract_comm(threshold_logs[ds])
    # No-prefetch
    np_up = extract_noprefetch_upload(noprefetch_logs[ds])
    
    data[ds] = {
        "union": {"upload": sum(u_up), "download": sum(u_dl), "rounds": len(u_up)},
        "threshold": {"upload": sum(t_up), "download": sum(t_dl), "rounds": len(t_up)},
        "noprefetch": {"upload": sum(np_up), "rounds": len(np_up)},
    }
    
    print(f"\n=== {ds} ===")
    print(f"  No-Prefetch:  upload={sum(np_up):.2f} MB | rounds={len(np_up)}")
    print(f"  Union:        upload={sum(u_up):.2f} MB | download={sum(u_dl):.2f} MB | rounds={len(u_up)}")
    print(f"  Threshold:    upload={sum(t_up):.2f} MB | download={sum(t_dl):.2f} MB | rounds={len(t_up)}")
    if sum(u_up) > 0:
        print(f"  Threshold vs Union reduction: {(1 - sum(t_up)/sum(u_up))*100:.1f}%")
    if sum(np_up) > 0:
        print(f"  Threshold vs No-Prefetch reduction: {(1 - sum(t_up)/sum(np_up))*100:.1f}%")

# 画柱状图
from tools.plotter import Plotter

p = Plotter(use_latex=False)

datasets = ["MNIST", "Fashion-MNIST", "CIFAR-10"]
noprefetch_uploads = [data[ds]["noprefetch"]["upload"] for ds in datasets]
union_uploads = [data[ds]["union"]["upload"] for ds in datasets]
threshold_uploads = [data[ds]["threshold"]["upload"] for ds in datasets]

p.bar(
    data={
        "categories": datasets,
        "series": {
            "No Prefetch": noprefetch_uploads,
            "Union": union_uploads,
            "Threshold": threshold_uploads,
        },
    },
    xlabel="Dataset",
    ylabel="Total Upload Cost (MB)",
    title="Total Upload Cost: No-Prefetch vs Union vs Threshold (mask vote)",
    colors={"No Prefetch": "#ED7D31", "Union": "#4472C4", "Threshold": "#70AD47"},
    legend_loc="upper left",
    filename=str(OUT_DIR / "upload_union_vs_threshold"),
)

print(f"\n图表已保存到 {OUT_DIR}/")
