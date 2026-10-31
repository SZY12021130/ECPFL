#!/usr/bin/env python3
"""
plot_bandwidth_heterogeneity.py
==============================
绘制异构跨设备客户端的带宽分布直方图，体现设备间带宽波动差异。
用于论文插图：展示联邦学习中不同设备类型（手机/手表/平板/IoT）的带宽异构性。

使用 scienceplots 生成 publication-ready 级别的图表。

输出：
    - bandwidth_heterogeneity.png （主图，300 DPI）
    - bandwidth_heterogeneity.svg （矢量图，适合论文插入）
    - bandwidth_heterogeneity_config.json （带宽统计配置，供实验使用）

Usage:
    python tools/plot_bandwidth_heterogeneity.py
"""

import numpy as np
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401
import os
import json

# ------------------------------------------------------------------------------
# 模拟不同设备类型的带宽分布（单位：Kbps）
# ------------------------------------------------------------------------------
np.random.seed(42)
n_samples = 3000

# 1. 智能手机 Smartphone: 中等带宽，双峰（WiFi / 蜂窝网络切换）
phone_wifi = np.random.normal(loc=8000, scale=1500, size=n_samples // 2)
phone_cell = np.random.normal(loc=2500, scale=800, size=n_samples // 2)
phone_bw = np.concatenate([phone_wifi, phone_cell])
phone_bw = np.clip(phone_bw, 500, 15000)

# 2. 智能手表 Smartwatch: 低带宽，窄分布（蓝牙/WiFi辅助）
watch_bw = np.random.normal(loc=800, scale=200, size=n_samples)
watch_bw = np.clip(watch_bw, 200, 2000)

# 3. 平板电脑 Tablet: 高带宽，较宽分布（稳定WiFi）
tablet_bw = np.random.normal(loc=10000, scale=2500, size=n_samples)
tablet_bw = np.clip(tablet_bw, 3000, 20000)

# 4. IoT/摄像头 IoT Camera: 很低带宽，右偏分布
camera_bw = np.random.lognormal(mean=6.2, sigma=0.5, size=n_samples)
camera_bw = np.clip(camera_bw, 100, 3000)

# 5. 笔记本电脑 Laptop: 高带宽，稳定分布（WiFi/Ethernet）
laptop_bw = np.random.normal(loc=25000, scale=8000, size=n_samples)
laptop_bw = np.clip(laptop_bw, 5000, 50000)

devices = [
    ("Smartphone", phone_bw, "#3498DB"),
    ("Smartwatch", watch_bw, "#2ECC71"),
    ("Tablet",     tablet_bw, "#E67E22"),
    ("IoT Camera", camera_bw, "#9B59B6"),
    ("Laptop",     laptop_bw, "#E74C3C"),
]

# ------------------------------------------------------------------------------
# 绘图 (scienceplots paper 级别样式)
# ------------------------------------------------------------------------------
plt.style.use(['science', 'ieee'])

fig, axes = plt.subplots(len(devices), 1, figsize=(10, 7), sharex=False)

for idx, (name, data, color) in enumerate(devices):
    ax = axes[idx]
    
    n_bins = 50
    # 填充柱形（无边框，避免重叠模糊）
    ax.hist(
        data, bins=n_bins, color=color, alpha=0.70,
        edgecolor='none', density=False,
        histtype='stepfilled'
    )
    # 叠加粗黑轮廓线，确保柱间竖线清晰锐利
    ax.hist(
        data, bins=n_bins, facecolor='none',
        edgecolor='black', linewidth=2.0, density=False,
        histtype='step'
    )
    
    # 保留 y 轴标签（仅第一个子图显示标题）和刻度（所有子图都显示）
    if idx == 0:
        ax.set_ylabel('Number of Clients', fontsize=10)
    ax.tick_params(axis='y', which='both', left=True, right=False, labelleft=True, labelright=False)
    
    ymax = ax.get_ylim()[1]
    ax.set_ylim(0, ymax * 1.25)
    
    # 设备名称放在子图内部右上角
    ax.text(
        0.98, 0.90, name,
        transform=ax.transAxes,
        fontsize=10, fontweight='bold', color='#333333',
        ha='right', va='top',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                  edgecolor='#CCCCCC', alpha=0.9)
    )
    
    # 保留 x 轴刻度、标签和轴线（连贯）
    ax.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True)
    ax.spines['bottom'].set_visible(True)
    
    # 去掉上边框和右边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 去掉所有网格线，保持背景纯白
    ax.grid(False)
    
    margin = (data.max() - data.min()) * 0.05
    ax.set_xlim(data.min() - margin, data.max() + margin)

# x轴标签（仅最底部）
axes[-1].set_xlabel('Downlink Bandwidth (Kbps)', fontsize=11)


plt.tight_layout(rect=[0.02, 0.05, 0.98, 0.98])

# ------------------------------------------------------------------------------
# 保存
# ------------------------------------------------------------------------------
output_dir = os.path.dirname(os.path.abspath(__file__))
png_path = os.path.join(output_dir, 'bandwidth_heterogeneity.png')
svg_path = os.path.join(output_dir, 'bandwidth_heterogeneity.svg')

plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(svg_path, format='svg', bbox_inches='tight', facecolor='white')
plt.close()

print(f"[OK] Saved: {png_path}")
print(f"[OK] Saved: {svg_path}")

# ------------------------------------------------------------------------------
# 附加：生成带宽配置 JSON（供实验使用）
# ------------------------------------------------------------------------------
bandwidth_config = {}
for name, data, color in devices:
    key = name.lower().replace(" ", "_")
    bandwidth_config[key] = {
        "mean_kbps": float(np.mean(data)),
        "std_kbps": float(np.std(data)),
        "min_kbps": float(np.min(data)),
        "max_kbps": float(np.max(data)),
        "median_kbps": float(np.median(data)),
        "p95_kbps": float(np.percentile(data, 95)),
        "color": color,
    }

json_path = os.path.join(output_dir, 'bandwidth_heterogeneity_config.json')
with open(json_path, 'w') as f:
    json.dump(bandwidth_config, f, indent=2)
print(f"[OK] Saved: {json_path}")

# 打印统计摘要
print("\n" + "="*60)
print("Bandwidth Statistics Summary")
print("="*60)
for name, data, color in devices:
    print(f"{name:12s}: mean={np.mean(data)/1000:5.1f} Mbps, "
          f"std={np.std(data)/1000:4.1f} Mbps, "
          f"range=[{np.min(data)/1000:.1f}, {np.max(data)/1000:.1f}] Mbps")
print("="*60)
