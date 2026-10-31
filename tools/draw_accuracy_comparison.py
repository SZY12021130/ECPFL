#!/usr/bin/env python3
"""
对比 No-Prefetch vs Union vs Threshold 的准确率曲线
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

OUT_DIR = Path("communication")
OUT_DIR.mkdir(exist_ok=True)

def extract_accuracy(log_path):
    """从日志提取每轮准确率"""
    # 预取实验格式: acc=XX.XX%
    pattern_prefetch = re.compile(r"acc=([\d.]+)%")
    # 不预取实验格式: [轮次/ROUND] #X done | acc=XX.XX%
    pattern_noprefetch = re.compile(r"acc=([\d.]+)%")
    
    accs = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern_prefetch.search(line)
            if m:
                accs.append(float(m.group(1)))
    return accs

def extract_accuracy_from_metrics(metrics_path):
    """从 metrics.json 提取每轮准确率"""
    import json
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    rounds = metrics.get("rounds", [])
    return [r.get("accuracy", 0) * 100 for r in rounds if "accuracy" in r]

# 实验路径
experiments = {
    "MNIST": {
        "No-Prefetch": ("accuracy_noprefetch/mnist-lenet/experiment_20260530_155103/experiment.log", "log"),
        "Union": ("results/experiment_20260603_101807/experiment.log", "log"),
        "Threshold": ("results/experiment_mnist_threshold.log", "log"),
    },
    "Fashion-MNIST": {
        "No-Prefetch": ("accuracy_noprefetch/fashion_mnist-cnn_fmnist/experiment_20260530_183600/experiment.log", "log"),
        "Union": ("results/experiment_20260602_182454/experiment.log", "log"),
        "Threshold": ("results/experiment_fashion_threshold.log", "log"),
    },
    "CIFAR-10": {
        "No-Prefetch": ("accuracy_noprefetch/cifar10-resnet20/experiment_20260530_221101/experiment.log", "log"),
        "Union": ("results/experiment_20260603_115420/experiment.log", "log"),
        "Threshold": ("results/experiment_cifar10_threshold.log", "log"),
    },
}

from tools.plotter import Plotter

# 为每个数据集画一张图
for ds, exps in experiments.items():
    data = {"x": list(range(1, 51))}
    series = {}
    
    for mode, (path, ptype) in exps.items():
        accs = extract_accuracy(path)
        # 只取前50轮
        accs = accs[:50]
        if len(accs) < 50:
            # 补齐
            accs = accs + [accs[-1]] * (50 - len(accs))
        series[mode] = accs
        final_acc = accs[-1] if accs else 0
        print(f"{ds} - {mode}: rounds={len(accs)}, final_acc={final_acc:.2f}%")
    
    data["series"] = series
    
    p = Plotter(use_latex=False, figsize=(10, 6))
    line_data = {}
    for mode, accs in series.items():
        line_data[mode] = {"x": list(range(1, len(accs)+1)), "y": accs}
    p.line(
        data=line_data,
        xlabel="Communication Round",
        ylabel="Test Accuracy (%)",
        title=f"{ds}: Accuracy Comparison (No-Prefetch vs Union vs Threshold)",
        colors={"No-Prefetch": "#ED7D31", "Union": "#4472C4", "Threshold": "#70AD47"},
        legend_loc="lower right",
        filename=str(OUT_DIR / f"accuracy_{ds.lower().replace('-', '_')}"),
    )

# 再画一个三子图对比
plot_configs = []
for ds, exps in experiments.items():
    series = {}
    for mode, (path, ptype) in exps.items():
        accs = extract_accuracy(path)[:50]
        if len(accs) < 50:
            accs = accs + [accs[-1]] * (50 - len(accs))
        series[mode] = accs
    
    line_data = {}
    for mode, accs in series.items():
        line_data[mode] = {"x": list(range(1, len(accs)+1)), "y": accs}
    plot_configs.append({
        "type": "line",
        "data": line_data,
        "xlabel": "Round",
        "ylabel": "Accuracy (%)",
        "title": ds,
        "colors": {"No-Prefetch": "#ED7D31", "Union": "#4472C4", "Threshold": "#70AD47"},
        "legend_loc": "lower right",
    })

p2 = Plotter(use_latex=False, figsize=(14, 4))
p2.multi_subplot(
    plot_configs=plot_configs,
    nrows=1,
    ncols=3,
    filename=str(OUT_DIR / "accuracy_all_datasets"),
)

print(f"\n图表已保存到 {OUT_DIR}/")
