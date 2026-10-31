#!/usr/bin/env python3
"""
分析人工带宽实验结果：提取带宽配置 + 通信量 + 生成面积图
"""
import json
import re
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------
# 1. 读取带宽配置
# ------------------------------------------------------------------
BW_CONFIG = Path("configs/bandwidth_config_50_25000_12000_0.2_uniform.json")
LOG_PATH = Path("results/experiment_20260603_004802/experiment.log")
OUT_DIR = Path("communication")
OUT_DIR.mkdir(exist_ok=True)

with open(BW_CONFIG, "r", encoding="utf-8") as f:
    bw = json.load(f)

dl = bw["dl_bandwidth"]
ul = bw["ul_bandwidth"]

# 统计
dl_vals = np.array(list(dl.values())) / 1000.0  # kbps -> Mbps
ul_vals = np.array(list(ul.values())) / 1000.0

print("=" * 70)
print("每个客户端的上下行带宽 (uniform, variance=0.2)")
print("=" * 70)
print(f"{'Client ID':<10} {'Downlink (Mbps)':<18} {'Uplink (Mbps)':<18}")
print("-" * 70)
for cid in sorted(dl.keys(), key=int):
    print(f"{cid:<10} {dl[cid]/1000.0:<18.2f} {ul[cid]/1000.0:<18.2f}")
print("-" * 70)
print(f"{'AVG':<10} {dl_vals.mean():<18.2f} {ul_vals.mean():<18.2f}")
print(f"{'MIN':<10} {dl_vals.min():<18.2f} {ul_vals.min():<18.2f}")
print(f"{'MAX':<10} {dl_vals.max():<18.2f} {ul_vals.max():<18.2f}")
print(f"{'STD':<10} {dl_vals.std():<18.2f} {ul_vals.std():<18.2f}")

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
prefetchs = []
rounds = []

with open(LOG_PATH, "r", encoding="utf-8") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            up = float(m.group(1))
            fv_str = m.group(2)
            # 处理 B -> MB
            if "B" in line.split("|")[1] and "MB" not in line.split("|")[1]:
                # 如果单位是 B
                pass
            fv = float(fv_str)
            # 判断单位：如果原始行里有 "B" 但没有 "MB"，则是字节
            if "=0 B" in line or ("MB" not in line.split("FV")[1].split("|")[0] and "B" in line.split("FV")[1].split("|")[0]):
                if fv > 0 and fv < 1:  # 很可能是字节，数值很小
                    fv = fv / (1024 * 1024)  # B -> MB
            effective = float(m.group(3))
            rounds.append(len(rounds) + 1)
            uploads.append(up)
            fetchs.append(fv)

print(f"\n提取到 {len(rounds)} 轮通信数据")
print(f"Upload 均值: {np.mean(uploads):.2f} MB")
print(f"Fetch  均值: {np.mean(fetchs):.2f} MB")
print(f"Fetch  总轮次: {sum(1 for f in fetchs if f > 0)}/{len(fetchs)}")
print(f"Fetch  占比: {np.mean(fetchs)/(np.mean(uploads)+np.mean(fetchs))*100:.1f}% (按均值)")

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
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
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
        title="MNIST (LeNet) with Prefetch — Artificial BW 25/12 Mbps",
        colors={"Upload": "#4472C4", "Fetch": "#ED7D31"},
        alpha=0.85,
        legend_loc="upper right",
        filename=str(OUT_DIR / "comm_artificial_bw_upload_fetch"),
    )

    # 图2: Upload + Download (effective) 作为对比
    p.stacked_area(
        data={
            "x": list(range(1, len(rounds) + 1)),
            "series": {
                "Upload": uploads,
                "Download (effective)": [float(re.search(r"effective[^=]+?=([\d.]+)\s*MB", line).group(1)) for line in open(LOG_PATH, "r", encoding="utf-8") if "通信汇总" in line],
            },
        },
        xlabel="Communication Round",
        ylabel="Communication Cost (MB)",
        title="MNIST (LeNet) — Upload + Effective Download",
        colors={"Upload": "#4472C4", "Download (effective)": "#70AD47"},
        alpha=0.85,
        legend_loc="upper right",
        filename=str(OUT_DIR / "comm_artificial_bw_upload_download"),
    )

    print(f"\n图表已保存到 {OUT_DIR}/")
except Exception as e:
    print(f"绘图失败: {e}")
    import traceback
    traceback.print_exc()
