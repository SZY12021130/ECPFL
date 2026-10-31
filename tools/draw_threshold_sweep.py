#!/usr/bin/env python3
"""
Threshold sweep 实验结果可视化：准确率曲线 + 上传量对比
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

OUT_DIR = Path("accuracy_threshold_v2")
PLOT_DIR = Path("communication")
PLOT_DIR.mkdir(exist_ok=True)

def extract_accuracy(log_path):
    """从日志提取每轮准确率"""
    # 两种日志格式: [轮次/ROUND] 和 [测试/TEST]
    pattern = re.compile(r"\[轮次/ROUND\].*?acc=([\d.]+)%")
    accs = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                accs.append(float(m.group(1)))
    return accs

def extract_comm(log_path):
    """从日志提取每轮 upload 和 download"""
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

# 数据集配置
datasets = {
    "MNIST": "mnist",
    "Fashion-MNIST": "fashion_mnist",
    "CIFAR-10": "cifar10",
}
thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]

# 收集数据
results = {}
for ds_name, ds_key in datasets.items():
    results[ds_name] = {}
    for pct in thresholds:
        dir_name = f"20260604_{ds_key}_threshold_pct_{pct}"
        log_path = OUT_DIR / dir_name / "run.log"
        if not log_path.exists():
            continue
        accs = extract_accuracy(str(log_path))
        uploads, downloads = extract_comm(str(log_path))
        results[ds_name][pct] = {
            "accuracy": accs,
            "upload": uploads,
            "download": downloads,
            "total_upload": sum(uploads),
            "total_download": sum(downloads),
            "final_acc": accs[-1] if accs else 0,
        }

# 打印汇总表
print("=" * 80)
print("Threshold Sweep 实验结果汇总")
print("=" * 80)
for ds_name in datasets:
    print(f"\n=== {ds_name} ===")
    print(f"{'threshold':<10} {'Final Acc':<12} {'Total Upload':<15} {'Total Download':<15} {'Rounds':<10}")
    print("-" * 70)
    for pct in thresholds:
        if pct in results[ds_name]:
            r = results[ds_name][pct]
            print(f"{pct:<10} {r['final_acc']:<12.2f} {r['total_upload']:<15.2f} {r['total_download']:<15.2f} {len(r['accuracy']):<10}")

from tools.plotter import Plotter

# ------------------------------------------------------------------
# 图1: 每个数据集一张图 — 不同 threshold 的准确率曲线
# ------------------------------------------------------------------
colors_map = {
    0.1: "#1f77b4",
    0.3: "#ff7f0e",
    0.5: "#2ca02c",
    0.7: "#d62728",
    0.9: "#9467bd",
}

for ds_name in datasets:
    p = Plotter(use_latex=False, figsize=(10, 6))
    line_data = {}
    for pct in thresholds:
        if pct in results[ds_name]:
            accs = results[ds_name][pct]["accuracy"]
            line_data[f"threshold={pct}"] = {
                "x": list(range(1, len(accs) + 1)),
                "y": accs,
            }
    p.line(
        data=line_data,
        xlabel="Communication Round",
        ylabel="Test Accuracy (%)",
        title=f"{ds_name}: Accuracy vs Threshold_pct",
        colors={f"threshold={pct}": colors_map[pct] for pct in thresholds},
        legend_loc="lower right",
        filename=str(PLOT_DIR / f"threshold_sweep_accuracy_{ds_name.lower().replace('-', '_')}"),
    )

# ------------------------------------------------------------------
# 图2: 三数据集并排 — 不同 threshold 的准确率曲线
# ------------------------------------------------------------------
plot_configs = []
for ds_name in datasets:
    line_data = {}
    for pct in thresholds:
        if pct in results[ds_name]:
            accs = results[ds_name][pct]["accuracy"]
            line_data[f"t={pct}"] = {"x": list(range(1, len(accs) + 1)), "y": accs}
    plot_configs.append({
        "type": "line",
        "data": line_data,
        "xlabel": "Round",
        "ylabel": "Accuracy (%)",
        "title": ds_name,
        "colors": {f"t={pct}": colors_map[pct] for pct in thresholds},
        "legend_loc": "lower right",
    })

p2 = Plotter(use_latex=False, figsize=(15, 4))
p2.multi_subplot(
    plot_configs=plot_configs,
    nrows=1, ncols=3,
    filename=str(PLOT_DIR / "threshold_sweep_accuracy_all"),
)

# ------------------------------------------------------------------
# 图3: 上传量随 threshold 变化（柱状图）
# ------------------------------------------------------------------
p3 = Plotter(use_latex=False, figsize=(10, 6))
bar_data = {"categories": list(datasets.keys())}
bar_series = {}
for pct in thresholds:
    bar_series[f"t={pct}"] = [
        results[ds].get(pct, {}).get("total_upload", 0) for ds in datasets
    ]
bar_data["series"] = bar_series

p3.bar(
    data=bar_data,
    xlabel="Dataset",
    ylabel="Total Upload (MB)",
    title="Total Upload Cost vs Threshold_pct",
    colors={f"t={pct}": colors_map[pct] for pct in thresholds},
    legend_loc="upper right",
    filename=str(PLOT_DIR / "threshold_sweep_upload_bar"),
)

# ------------------------------------------------------------------
# 图4: 最终准确率随 threshold 变化（折线图）
# ------------------------------------------------------------------
p4 = Plotter(use_latex=False, figsize=(10, 6))
line_data2 = {}
for ds_name in datasets:
    x_vals = []
    y_vals = []
    for pct in thresholds:
        if pct in results[ds_name]:
            x_vals.append(pct)
            y_vals.append(results[ds_name][pct]["final_acc"])
    line_data2[ds_name] = {"x": x_vals, "y": y_vals}

p4.line(
    data=line_data2,
    xlabel="Threshold_pct",
    ylabel="Final Test Accuracy (%)",
    title="Final Accuracy vs Threshold_pct",
    colors={"MNIST": "#1f77b4", "Fashion-MNIST": "#ff7f0e", "CIFAR-10": "#2ca02c"},
    markers={"MNIST": "o", "Fashion-MNIST": "s", "CIFAR-10": "^"},
    legend_loc="best",
    filename=str(PLOT_DIR / "threshold_sweep_final_accuracy"),
)

print(f"\n图表已保存到 {PLOT_DIR}/")
