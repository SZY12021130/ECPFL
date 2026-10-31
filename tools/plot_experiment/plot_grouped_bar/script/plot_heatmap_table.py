"""
通信量表格+热力图可视化
使用精美表格展示数据，颜色深浅编码数值大小
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# 路径设置
script_dir = os.path.dirname(os.path.abspath(__file__))
project_tools_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_tools_dir)

from plotter import Plotter

# ---------------------------------------------------------------------------
# 1. 数据配置
# ---------------------------------------------------------------------------
DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = [
    "ECPFL-TH",
    "FedPHE",
    "ESAFL",
    "MASER",
    "FedAvg-CKKS",
]

# 真实实验数据 (单位: MB)
# 格式: {dataset: {method: [CT-Upload, CT-Fetch]}}
DATA = {
    "MNIST": {
        "ECPFL-TH":     [2183.81, 35.46],
        "FedPHE":       [797.03, 3133.42],
        "ESAFL":        [2390.93, 2390.93],
        "MASER":        [5531.23, 2977.45],
        "FedAvg-CKKS":  [4383.87, 4383.87],
    },
    "FMNIST": {
        "ECPFL-TH":     [414.45, 9.65],
        "FedPHE":       [398.55, 3645.94],
        "ESAFL":        [1992.65, 1992.65],
        "MASER":        [4766.15, 2573.86],
        "FedAvg-CKKS":  [3985.09, 3985.09],
    },
    "CIFAR-10": {
        "ECPFL-TH":     [7587.58, 190.34],
        "FedPHE":       [13548.73, 18960.94],
        "ESAFL":        [13549.24, 13549.24],
        "MASER":        [27066.40, 14839.93],
        "FedAvg-CKKS":  [26699.46, 26699.46],
    },
    "SVHN": {
        "ECPFL-TH":     [19263.73, 298.54],
        "FedPHE":       [23112.74, 32567.46],
        "ESAFL":        [23113.26, 23113.26],
        "MASER":        [46991.57, 25733.91],
        "FedAvg-CKKS":  [45828.08, 45828.08],
    },
}

# 配色方案
UPLOAD_CMAP = "Reds"      # Upload 用红色系
FETCH_CMAP = "Blues"      # Fetch 用蓝色系
TOTAL_CMAP = "YlOrRd"     # Total 用黄橙红系

# 字体大小
FONT_SIZE_TITLE = 16
FONT_SIZE_HEADER = 12
FONT_SIZE_CELL = 11
FONT_SIZE_UNIT = 10

# ---------------------------------------------------------------------------
# 2. 绘图函数
# ---------------------------------------------------------------------------
def format_value(val):
    """格式化数值显示"""
    if val >= 10000:
        return f"{val/1024:.1f} GB"
    elif val >= 1000:
        return f"{val/1024:.2f} GB"
    else:
        return f"{val:.1f} MB"

def draw_heatmap_table():
    """绘制表格+热力图"""
    
    # 准备数据矩阵
    n_datasets = len(DATASETS)
    n_methods = len(METHODS)
    
    # 提取 Upload, Fetch, Total 数据
    upload_data = np.zeros((n_datasets, n_methods))
    fetch_data = np.zeros((n_datasets, n_methods))
    total_data = np.zeros((n_datasets, n_methods))
    
    for i, ds in enumerate(DATASETS):
        for j, method in enumerate(METHODS):
            upload_data[i, j] = DATA[ds][method][0]
            fetch_data[i, j] = DATA[ds][method][1]
            total_data[i, j] = upload_data[i, j] + fetch_data[i, j]
    
    # 创建图形：三个子图（Upload, Fetch, Total）
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 配置每个子图
    configs = [
        (upload_data, "CT-Upload", UPLOAD_CMAP),
        (fetch_data, "CT-Fetch", FETCH_CMAP),
        (total_data, "Total Communication", TOTAL_CMAP),
    ]
    
    for ax, (data, title, cmap) in zip(axes, configs):
        # 使用对数归一化来更好地展示数据差异
        vmin = data[data > 0].min()
        vmax = data.max()
        norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
        
        # 绘制热力图
        im = ax.imshow(data, cmap=cmap, norm=norm, aspect='auto')
        
        # 设置刻度
        ax.set_xticks(np.arange(n_methods))
        ax.set_yticks(np.arange(n_datasets))
        ax.set_xticklabels(METHODS, rotation=35, ha='right', fontsize=FONT_SIZE_HEADER)
        ax.set_yticklabels(DATASETS, fontsize=FONT_SIZE_HEADER)
        
        # 标题
        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight='bold', pad=10)
        
        # 在每个单元格中添加数值
        for i in range(n_datasets):
            for j in range(n_methods):
                val = data[i, j]
                # 根据背景颜色选择文字颜色
                bg_color = im.norm(val)
                text_color = 'white' if bg_color > 0.5 else 'black'
                
                text = ax.text(j, i, format_value(val),
                              ha="center", va="center",
                              color=text_color, fontsize=FONT_SIZE_CELL)
        
        # 添加网格线
        ax.set_xticks(np.arange(-0.5, n_methods, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_datasets, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1)
        ax.tick_params(which="minor", bottom=False, left=False)
    
    # 添加颜色条
    for ax, (_, _, cmap) in zip(axes, configs):
        pass  # 颜色条已在 imshow 中自动添加
    
    # 调整布局
    plt.tight_layout()
    
    # 保存
    save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pic")
    os.makedirs(save_dir, exist_ok=True)
    
    for fmt in ["png", "pdf"]:
        fpath = os.path.join(save_dir, f"communication_heatmap.{fmt}")
        plt.savefig(fpath, dpi=300, bbox_inches="tight")
        print(f"[Saved] {fpath}")
    
    plt.close()

# ---------------------------------------------------------------------------
# 3. 主入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n>>> Generating heatmap table...")
    draw_heatmap_table()
    print("\n绘图完成！图片保存在: plot_experiment/plot_grouped_bar/pic/")
