#!/usr/bin/env python3
"""
分析带上下限带宽实验结果
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

BW_CONFIG = Path("configs/bandwidth_config_50_8192_4096_0.2_uniform.json")
LOG_PATH = Path("results/experiment_20260603_101807/experiment.log")
OUT_DIR = Path("communication")
OUT_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# 1. 读取带宽配置
# ------------------------------------------------------------------
with open(BW_CONFIG, "r", encoding="utf-8") as f:
    bw = json.load(f)

dl = bw["dl_bandwidth"]
ul = bw["ul_bandwidth"]

dl_vals = np.array(list(dl.values())) / 1000.0
ul_vals = np.array(list(ul.values())) / 1000.0

print("=" * 70)
print("每个客户端的上下行带宽 (capped: DL≤8Mbps, UL≤4Mbps)")
print("=" * 70)
print(f"{'Client ID':<10} {'Downlink (Mbps)':<18} {'Uplink (Mbps)':<18}")
print("-" * 70)
for cid in sorted(dl.keys(), key=int):
    print(f"{cid:<10} {dl[cid]/1000.0:<18.2f} {ul[cid]/1000.0:<18.2f}")
print("-" * 70)
print(f"{'AVG':<10} {dl_vals.mean():<18.2f} {ul_vals.mean():<18.2f}")
print(f"{'MIN':<10} {dl_vals.min():<18.2f} {ul_vals.min():<18.2f}")
print(f"{'MAX':<10} {dl_vals.max():<18.2f} {ul_vals.max():<18.2f}")

# ------------------------------------------------------------------
# 2. 解析日志提取通信量
# ------------------------------------------------------------------
pattern = re.compile(
    r"通信汇总:\s*↑([\d.]+)\s*MB\s*\|"
    r".*?FV\(fetch[^)]*\)=([\d.]+)\s*(?:MB|B)\s*\|"
    r".*?effective[^=]+?=([\d.]+)\s*MB"
)

uploads = []
fetchs = []
rounds = []

with open(LOG_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            up = float(m.group(1))
            fv = float(m.group(2))
            rounds.append(len(rounds) + 1)
            uploads.append(up)
            fetchs.append(fv)

print(f"\n提取到 {len(rounds)} 轮通信数据")
print(f"Upload 均值: {np.mean(uploads):.2f} MB")
print(f"Fetch  均值: {np.mean(fetchs):.2f} MB")
fetch_nonzero = sum(1 for f in fetchs if f > 0)
print(f"Fetch  非零轮次: {fetch_nonzero}/{len(fetchs)}")
total_comm = np.mean(uploads) + np.mean(fetchs)
print(f"Fetch  占比: {np.mean(fetchs)/total_comm*100:.1f}% (按均值)")

# 详细每轮数据
print("\n" + "=" * 70)
print("每轮通信量明细")
print("=" * 70)
print(f"{'Round':<8} {'Upload (MB)':<14} {'Fetch (MB)':<14} {'Total (MB)':<14} {'Fetch%':<10}")
print("-" * 70)
for i, (u, f) in enumerate(zip(uploads, fetchs), 1):
    total = u + f
    pct = f / total * 100 if total > 0 else 0
    print(f"{i:<8} {u:<14.2f} {f:<14.2f} {total:<14.2f} {pct:<10.1f}")

# ------------------------------------------------------------------
# 3. 生成堆叠面积图
# ------------------------------------------------------------------
from tools.plotter import Plotter

p = Plotter(use_latex=False)

# 图1: Upload + Fetch
p.stacked_area(
    data={
        "x": list(range(1, len(rounds) + 1)),
        "series": {
            "Upload": uploads,
            "Fetch": fetchs,
        },
    },
    xlabel="Communication Round",
    ylabel="Communication Cost (MB)",
    title="MNIST (LeNet) — Capped BW: DL≤8 Mbps, UL≤4 Mbps, Prefetch Window=3",
    colors={"Upload": "#4472C4", "Fetch": "#ED7D31"},
    alpha=0.85,
    legend_loc="upper right",
    filename=str(OUT_DIR / "comm_capped_bw_upload_fetch"),
)

# 图2: 对比图 (无上限 vs 有上限)
# 先读取无上限的数据
LOG_PATH2 = Path("results/experiment_20260603_004802/experiment.log")
uploads2 = []
fetchs2 = []
with open(LOG_PATH2, "r", encoding="utf-8") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            uploads2.append(float(m.group(1)))
            fetchs2.append(float(m.group(2)))

# 截取相同轮数
n = min(len(uploads), len(uploads2))

from tools.plotter import Plotter
p2 = Plotter(use_latex=False)

# 用 multi_subplot 或分别保存
p2.stacked_area(
    data={
        "x": list(range(1, n + 1)),
        "series": {
            "Upload": uploads2[:n],
            "Fetch": fetchs2[:n],
        },
    },
    xlabel="Communication Round",
    ylabel="Communication Cost (MB)",
    title="MNIST (LeNet) — Uncapped BW: DL~25 Mbps, Prefetch Window=3",
    colors={"Upload": "#4472C4", "Fetch": "#ED7D31"},
    alpha=0.85,
    legend_loc="upper right",
    filename=str(OUT_DIR / "comm_uncapped_bw_upload_fetch"),
)

print(f"\n图表已保存到 {OUT_DIR}/")
