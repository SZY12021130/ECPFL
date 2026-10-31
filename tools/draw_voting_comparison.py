#!/usr/bin/env python3
"""
三种投票机制综合对比分析：Union vs Threshold vs TopK
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PLOT_DIR = Path("communication")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

# 数据定义
DATA = {
    "mnist": {
        "union": {"acc": 98.83, "upload": 4240.1, "download": 72.7},
        "threshold": {
            0.1: {"acc": 98.80, "upload": 8161.3, "download": 2945.3},
            0.3: {"acc": 98.80, "upload": 6216.6, "download": 2246.4},
            0.5: {"acc": 98.65, "upload": 4383.5, "download": 1600.7},
            0.7: {"acc": 98.55, "upload": 2996.7, "download": 1097.4},
            0.9: {"acc": 98.21, "upload": 1673.7, "download": 613.8},
        },
        "topk": {
            0.1: {"acc": 98.15, "upload": 797.0, "download": 17.3},
            0.3: {"acc": 98.49, "upload": 1594.0, "download": 34.6},
            0.5: {"acc": 98.66, "upload": 2391.0, "download": 51.6},
            0.7: {"acc": 98.82, "upload": 3188.0, "download": 64.9},
            0.9: {"acc": 98.84, "upload": 3985.0, "download": 78.1},
        },
    },
    "fashion_mnist": {
        "union": {"acc": 90.20, "upload": 2853.3, "download": 76.3},
        "threshold": {
            0.1: {"acc": 90.01, "upload": 5148.6, "download": 1871.3},
            0.3: {"acc": 88.74, "upload": 4287.9, "download": 1568.4},
            0.5: {"acc": 88.03, "upload": 3985.0, "download": 1444.9},
            0.7: {"acc": 86.35, "upload": 2805.5, "download": 1022.2},
            0.9: {"acc": 84.59, "upload": 1689.6, "download": 617.8},
        },
        "topk": {
            0.1: {"acc": 18.53, "upload": 390.5, "download": 7.2},
            0.3: {"acc": 86.16, "upload": 1195.5, "download": 24.9},
            0.5: {"acc": 87.99, "upload": 1992.5, "download": 43.8},
            0.7: {"acc": 89.86, "upload": 2789.5, "download": 57.2},
            0.9: {"acc": 90.25, "upload": 3586.5, "download": 70.5},
        },
    },
    "cifar10": {
        "union": {"acc": 76.77, "upload": 20020.9, "download": 492.9},
        "threshold": {
            0.1: {"acc": 76.67, "upload": 37443.4, "download": 13667.2},
            0.3: {"acc": 74.99, "upload": 32231.2, "download": 11760.9},
            0.5: {"acc": 72.92, "upload": 25297.0, "download": 9192.2},
            0.7: {"acc": 65.58, "upload": 15175.1, "download": 5532.5},
            0.9: {"acc": 53.08, "upload": 8368.6, "download": 3056.0},
        },
        "topk": {
            0.1: {"acc": 36.70, "upload": 2789.5, "download": 55.4},
            0.3: {"acc": 67.92, "upload": 8368.6, "download": 182.0},
            0.5: {"acc": 73.43, "upload": 13549.2, "download": 283.7},
            0.7: {"acc": 76.24, "upload": 18729.7, "download": 382.9},
            0.9: {"acc": 77.80, "upload": 24308.9, "download": 476.3},
        },
    },
}

from tools.plotter import Plotter

# ============================================================
# 图1: 准确率 vs 参数（三数据集并排）
# ============================================================
colors = {
    "threshold": "#e74c3c",
    "topk": "#3498db",
    "union": "#2ecc71",
}

plot_configs = []
for ds_name, ds_key in [("MNIST", "mnist"), ("Fashion-MNIST", "fashion_mnist"), ("CIFAR-10", "cifar10")]:
    line_data = {}
    # Threshold
    th_x = [0.1, 0.3, 0.5, 0.7, 0.9]
    th_y = [DATA[ds_key]["threshold"][p]["acc"] for p in th_x]
    line_data["Threshold"] = {"x": th_x, "y": th_y}
    # TopK
    tk_x = [0.1, 0.3, 0.5, 0.7, 0.9]
    tk_y = [DATA[ds_key]["topk"][p]["acc"] for p in tk_x]
    line_data["TopK"] = {"x": tk_x, "y": tk_y}
    # Union reference line
    union_acc = DATA[ds_key]["union"]["acc"]
    line_data["Union (ref)"] = {"x": [0.1, 0.9], "y": [union_acc, union_acc]}
    
    plot_configs.append({
        "type": "line",
        "data": line_data,
        "xlabel": "Parameter (threshold_pct / topk_pct)",
        "ylabel": "Final Accuracy (%)",
        "title": ds_name,
        "colors": {"Threshold": colors["threshold"], "TopK": colors["topk"], "Union (ref)": colors["union"]},
        "markers": {"Threshold": "s", "TopK": "o", "Union (ref)": None},
        "legend_loc": "best",
    })

p1 = Plotter(use_latex=False, figsize=(15, 4))
p1.multi_subplot(
    plot_configs=plot_configs,
    nrows=1, ncols=3,
    filename=str(PLOT_DIR / "voting_comparison_accuracy"),
)

# ============================================================
# 图2: 上传量 vs 参数（三数据集并排）
# ============================================================
plot_configs2 = []
for ds_name, ds_key in [("MNIST", "mnist"), ("Fashion-MNIST", "fashion_mnist"), ("CIFAR-10", "cifar10")]:
    line_data = {}
    th_x = [0.1, 0.3, 0.5, 0.7, 0.9]
    th_y = [DATA[ds_key]["threshold"][p]["upload"] for p in th_x]
    line_data["Threshold"] = {"x": th_x, "y": th_y}
    tk_x = [0.1, 0.3, 0.5, 0.7, 0.9]
    tk_y = [DATA[ds_key]["topk"][p]["upload"] for p in tk_x]
    line_data["TopK"] = {"x": tk_x, "y": tk_y}
    union_up = DATA[ds_key]["union"]["upload"]
    line_data["Union (ref)"] = {"x": [0.1, 0.9], "y": [union_up, union_up]}
    
    plot_configs2.append({
        "type": "line",
        "data": line_data,
        "xlabel": "Parameter (threshold_pct / topk_pct)",
        "ylabel": "Total Upload (MB)",
        "title": ds_name,
        "colors": {"Threshold": colors["threshold"], "TopK": colors["topk"], "Union (ref)": colors["union"]},
        "markers": {"Threshold": "s", "TopK": "o", "Union (ref)": None},
        "legend_loc": "best",
    })

p2 = Plotter(use_latex=False, figsize=(15, 4))
p2.multi_subplot(
    plot_configs=plot_configs2,
    nrows=1, ncols=3,
    filename=str(PLOT_DIR / "voting_comparison_upload"),
)

# ============================================================
# 图3: 准确率 vs 上传量 Pareto 分析（每个数据集一张图）
# ============================================================
for ds_name, ds_key in [("MNIST", "mnist"), ("Fashion-MNIST", "fashion_mnist"), ("CIFAR-10", "cifar10")]:
    p3 = Plotter(use_latex=False, figsize=(8, 6))
    
    # Union point
    union_up = DATA[ds_key]["union"]["upload"]
    union_acc = DATA[ds_key]["union"]["acc"]
    
    # Threshold points
    th_x = [DATA[ds_key]["threshold"][p]["upload"] for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
    th_y = [DATA[ds_key]["threshold"][p]["acc"] for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
    
    # TopK points
    tk_x = [DATA[ds_key]["topk"][p]["upload"] for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
    tk_y = [DATA[ds_key]["topk"][p]["acc"] for p in [0.1, 0.3, 0.5, 0.7, 0.9]]
    
    line_data = {
        "Threshold": {"x": th_x, "y": th_y},
        "TopK": {"x": tk_x, "y": tk_y},
    }
    
    p3.line(
        data=line_data,
        xlabel="Total Upload (MB)",
        ylabel="Final Accuracy (%)",
        title=f"{ds_name}: Accuracy vs Upload Cost",
        colors={"Threshold": colors["threshold"], "TopK": colors["topk"]},
        markers={"Threshold": "s", "TopK": "o"},
        legend_loc="best",
        filename=str(PLOT_DIR / f"voting_comparison_pareto_{ds_key}"),
    )

# ============================================================
# 图4: 三种机制柱状图对比（取最佳平衡点）
# ============================================================
# 选择每个机制的最佳代表：
# - Union: 只有一个点
# - Threshold: 取 threshold=0.5（之前分析的最佳折中）
# - TopK: 取 topk=0.5（或每个数据集的最佳点）

bar_data = {
    "categories": ["MNIST", "Fashion-MNIST", "CIFAR-10"],
    "series": {}
}

for mechanism in ["Union", "Threshold(0.5)", "TopK(0.5)"]:
    accs = []
    for ds_key in ["mnist", "fashion_mnist", "cifar10"]:
        if mechanism == "Union":
            accs.append(DATA[ds_key]["union"]["acc"])
        elif mechanism == "Threshold(0.5)":
            accs.append(DATA[ds_key]["threshold"][0.5]["acc"])
        else:
            accs.append(DATA[ds_key]["topk"][0.5]["acc"])
    bar_data["series"][mechanism] = accs

p4 = Plotter(use_latex=False, figsize=(10, 6))
p4.bar(
    data=bar_data,
    xlabel="Dataset",
    ylabel="Final Accuracy (%)",
    title="Accuracy Comparison: Union vs Threshold(0.5) vs TopK(0.5)",
    colors={"Union": colors["union"], "Threshold(0.5)": colors["threshold"], "TopK(0.5)": colors["topk"]},
    legend_loc="best",
    filename=str(PLOT_DIR / "voting_comparison_bar_accuracy"),
)

# 上传量柱状图
bar_data2 = {
    "categories": ["MNIST", "Fashion-MNIST", "CIFAR-10"],
    "series": {}
}
for mechanism in ["Union", "Threshold(0.5)", "TopK(0.5)"]:
    ups = []
    for ds_key in ["mnist", "fashion_mnist", "cifar10"]:
        if mechanism == "Union":
            ups.append(DATA[ds_key]["union"]["upload"])
        elif mechanism == "Threshold(0.5)":
            ups.append(DATA[ds_key]["threshold"][0.5]["upload"])
        else:
            ups.append(DATA[ds_key]["topk"][0.5]["upload"])
    bar_data2["series"][mechanism] = ups

p5 = Plotter(use_latex=False, figsize=(10, 6))
p5.bar(
    data=bar_data2,
    xlabel="Dataset",
    ylabel="Total Upload (MB)",
    title="Upload Cost Comparison: Union vs Threshold(0.5) vs TopK(0.5)",
    colors={"Union": colors["union"], "Threshold(0.5)": colors["threshold"], "TopK(0.5)": colors["topk"]},
    legend_loc="best",
    filename=str(PLOT_DIR / "voting_comparison_bar_upload"),
)

print(f"\n图表已保存到 {PLOT_DIR}/")

# ============================================================
# 最佳平衡点分析
# ============================================================
print("\n" + "="*80)
print("最佳平衡点分析")
print("="*80)

for ds_name, ds_key in [("MNIST", "mnist"), ("Fashion-MNIST", "fashion_mnist"), ("CIFAR-10", "cifar10")]:
    print(f"\n=== {ds_name} ===")
    
    # 收集所有点
    points = []
    # Union
    u = DATA[ds_key]["union"]
    points.append(("Union", u["acc"], u["upload"], u["upload"] + u["download"]))
    # Threshold
    for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
        d = DATA[ds_key]["threshold"][p]
        points.append((f"Threshold({p})", d["acc"], d["upload"], d["upload"] + d["download"]))
    # TopK
    for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
        d = DATA[ds_key]["topk"][p]
        points.append((f"TopK({p})", d["acc"], d["upload"], d["upload"] + d["download"]))
    
    # 按准确率排序
    points.sort(key=lambda x: x[1], reverse=True)
    print(f"{'Config':<18} {'Acc':<8} {'Upload':<10} {'Total':<10} {'Score':<10}")
    print("-" * 60)
    
    # 计算 score = acc / log(total_comm + 1) 作为平衡指标
    best_score = -1
    best_cfg = None
    for cfg, acc, up, total in points:
        score = acc / (1 + 0.0001 * total)  # 简单平衡指标
        marker = ""
        if score > best_score and acc > 50:  # 排除完全失效的点
            best_score = score
            best_cfg = cfg
            marker = " ★BEST"
        print(f"{cfg:<18} {acc:<8.2f} {up:<10.1f} {total:<10.1f} {score:<10.4f}{marker}")
    
    print(f"\n  → 推荐: {best_cfg} (准确率={DATA[ds_key][best_cfg.split('(')[0].lower()][float(best_cfg.split('(')[1].rstrip(')')) if '(' in best_cfg else 'union']['acc' if '(' in best_cfg else 'acc']:.2f}%)")
