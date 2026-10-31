#!/usr/bin/env python3
"""
预取 vs 不预取 下行通信量对比柱状图
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

OUT_DIR = Path("communication")
OUT_DIR.mkdir(exist_ok=True)


def extract_noprefetch_comm(log_path):
    """从不预取实验日志提取每轮 upload 和 download"""
    pattern = re.compile(
        r"上传总量=([\d.]+)\s*MB\s*\|\s*下载总量=([\d.]+)\s*MB"
    )
    uploads = []
    downloads = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                uploads.append(float(m.group(1)))
                downloads.append(float(m.group(2)))
    return uploads, downloads


def extract_prefetch_comm(log_path):
    """从预取实验日志提取每轮 upload 和 effective download"""
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
                # effective download = 实际下载量
                downloads.append(float(m.group(3)))
    return uploads, downloads


# ------------------------------------------------------------------
# 1. 不预取实验 (从 accuracy_noprefetch 目录)
# ------------------------------------------------------------------
noprefetch_dirs = {
    "MNIST": "accuracy_noprefetch/mnist-lenet/experiment_20260530_155103/experiment.log",
    "Fashion-MNIST": "accuracy_noprefetch/fashion_mnist-cnn_fmnist/experiment_20260530_183600/experiment.log",
    "CIFAR-10": "accuracy_noprefetch/cifar10-resnet20/experiment_20260530_221101/experiment.log",
}

# 如果上述文件不存在，尝试找其他实验目录
def find_noprefetch_log(base_dir):
    base = Path(base_dir)
    for exp_dir in sorted(base.glob("experiment_*")):
        log = exp_dir / "experiment.log"
        if log.exists():
            # 验证有通信数据
            with open(log, "r", encoding="utf-8") as f:
                content = f.read()
            if "下载总量=" in content:
                return str(log)
    return None

for ds, path in list(noprefetch_dirs.items()):
    if not Path(path).exists():
        base = Path(path).parent.parent
        found = find_noprefetch_log(base)
        if found:
            noprefetch_dirs[ds] = found

# ------------------------------------------------------------------
# 2. 预取实验 (从 results 目录)
# ------------------------------------------------------------------
prefetch_dirs = {
    "MNIST": "results/experiment_20260603_101807/experiment.log",
    "Fashion-MNIST": "results/experiment_20260602_182454/experiment.log",
    "CIFAR-10": "results/experiment_20260603_115420/experiment.log",
}

# ------------------------------------------------------------------
# 3. 提取数据并计算总通信量
# ------------------------------------------------------------------
data = {}

for ds in ["MNIST", "Fashion-MNIST", "CIFAR-10"]:
    np_log = noprefetch_dirs[ds]
    p_log = prefetch_dirs[ds]
    
    np_up, np_dl = extract_noprefetch_comm(np_log)
    p_up, p_dl = extract_prefetch_comm(p_log)
    
    data[ds] = {
        "noprefetch": {
            "upload": sum(np_up),
            "download": sum(np_dl),
            "rounds": len(np_up),
        },
        "prefetch": {
            "upload": sum(p_up),
            "download": sum(p_dl),
            "rounds": len(p_up),
        }
    }
    
    print(f"\n=== {ds} ===")
    print(f"  No-Prefetch: rounds={len(np_up)}, total_download={sum(np_dl):.2f} MB, total_upload={sum(np_up):.2f} MB")
    print(f"  Prefetch:    rounds={len(p_up)}, total_download={sum(p_dl):.2f} MB, total_upload={sum(p_up):.2f} MB")
    if sum(np_dl) > 0:
        print(f"  Download reduction: {(1 - sum(p_dl)/sum(np_dl))*100:.1f}%")

# ------------------------------------------------------------------
# 4. 画柱状图
# ------------------------------------------------------------------
from tools.plotter import Plotter

p = Plotter(use_latex=False)

datasets = ["MNIST", "Fashion-MNIST", "CIFAR-10"]
noprefetch_downloads = [data[ds]["noprefetch"]["download"] for ds in datasets]
prefetch_downloads = [data[ds]["prefetch"]["download"] for ds in datasets]

# 分组柱状图
p.bar(
    data={
        "categories": datasets,
        "series": {
            "No Prefetch": noprefetch_downloads,
            "Prefetch": prefetch_downloads,
        },
    },
    xlabel="Dataset",
    ylabel="Total Download Cost (MB)",
    title="Total Download Cost: Prefetch vs No-Prefetch",
    colors={"No Prefetch": "#ED7D31", "Prefetch": "#4472C4"},
    legend_loc="upper left",
    filename=str(OUT_DIR / "download_prefetch_vs_noprefetch_bar"),
)

# 再画一个堆叠柱状图（Upload + Download）
noprefetch_uploads = [data[ds]["noprefetch"]["upload"] for ds in datasets]
prefetch_uploads = [data[ds]["prefetch"]["upload"] for ds in datasets]

# 使用 stacked_bar
p.stacked_bar(
    data={
        "categories": datasets,
        "series": {
            "Upload": [data[ds]["noprefetch"]["upload"] for ds in datasets],
            "Download": noprefetch_downloads,
        },
    },
    xlabel="Dataset",
    ylabel="Total Communication Cost (MB)",
    title="No-Prefetch: Upload + Download Breakdown",
    colors={"Upload": "#4472C4", "Download": "#70AD47"},
    legend_loc="upper right",
    filename=str(OUT_DIR / "comm_noprefetch_breakdown"),
)

p.stacked_bar(
    data={
        "categories": datasets,
        "series": {
            "Upload": [data[ds]["prefetch"]["upload"] for ds in datasets],
            "Download": prefetch_downloads,
        },
    },
    xlabel="Dataset",
    ylabel="Total Communication Cost (MB)",
    title="Prefetch: Upload + Download Breakdown",
    colors={"Upload": "#4472C4", "Download": "#70AD47"},
    legend_loc="upper right",
    filename=str(OUT_DIR / "comm_prefetch_breakdown"),
)

print(f"\n图表已保存到 {OUT_DIR}/")
