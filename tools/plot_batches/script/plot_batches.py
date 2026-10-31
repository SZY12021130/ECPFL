#!/usr/bin/env python3
r"""
plot_batches.py
===============
绘制 CKKS 加密后模型参数的 SIMD batch 结构可视化，
并与带宽异构性图组合展示，适合论文插图。

输出目录: E:\GithubProjects\ckks_fed_robustness\tools\plot_batches\pic
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import scienceplots  # noqa: F401

# -----------------------------------------------------------------------------
# 配置
# -----------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIC_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "pic")
os.makedirs(PIC_DIR, exist_ok=True)

plt.style.use(["science", "ieee"])

# 模型信息：总参数、batch 数、总大小 (MB)
MODELS = [
    {"name": "MNIST",     "model": "LeNet",       "params": 44426,  "batches": 11,  "total_mb": 3.19,  "color": "#3498DB"},
    {"name": "FMNIST",    "model": "CNN-FMNIST",  "params": 39786,  "batches": 10,  "total_mb": 2.90,  "color": "#2ECC71"},
    {"name": "CIFAR-10",  "model": "ResNet-20",   "params": 272186, "batches": 67,  "total_mb": 19.45, "color": "#E67E22"},
    {"name": "SVHN",      "model": "ResNet-32",   "params": 466618, "batches": 114, "total_mb": 33.09, "color": "#9B59B6"},
]

SLOT_CAPACITY = 4096  # CKKS SIMD slots (poly_modulus_degree=8192 -> N/2 slots)


def compute_batches(model):
    """计算每个 batch 的参数数和大小"""
    total = model["params"]
    n = model["batches"]
    batches = []
    remaining = total
    for i in range(n):
        cap = SLOT_CAPACITY if i < n - 1 else remaining
        cap = min(cap, remaining)
        mb = cap / total * model["total_mb"]
        batches.append({
            "idx": i + 1,
            "params": cap,
            "mb": mb,
            "full": cap == SLOT_CAPACITY,
        })
        remaining -= cap
    return batches


for m in MODELS:
    m["batch_list"] = compute_batches(m)


# -----------------------------------------------------------------------------
# 图 1: 水平堆叠条形图 —— 每个 batch 像一块积木
# -----------------------------------------------------------------------------
def plot_batch_structure():
    fig, ax = plt.subplots(figsize=(10, 4.5))

    y_pos = np.arange(len(MODELS))
    bar_height = 0.55

    for i, m in enumerate(MODELS):
        left = 0.0
        batches = m["batch_list"]
        # 颜色从浅到深
        cmap = LinearSegmentedColormap.from_list(
            "batch_cmap", ["#E8F6F3", m["color"]]
        )
        colors = cmap(np.linspace(0.35, 0.95, len(batches)))

        for j, b in enumerate(batches):
            ax.barh(
                i,
                b["mb"],
                left=left,
                height=bar_height,
                color=colors[j],
                edgecolor="white",
                linewidth=0.6,
            )
            left += b["mb"]

        # 模型总大小标注
        ax.text(
            left + 0.8,
            i,
            f"{m['total_mb']:.2f} MB",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
            color="#333333",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{m['name']}\n({m['model']})" for m in MODELS], fontsize=10)
    ax.set_xlabel("Ciphertext Size (MB)", fontsize=11)
    ax.set_title(
        "CKKS-SIMD Batch Decomposition of Encrypted Models",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )

    # 添加 batch 容量图例
    full_patch = mpatches.Patch(facecolor="#BDC3C7", edgecolor="white", label=f"Full batch ({SLOT_CAPACITY} slots)")
    partial_patch = mpatches.Patch(facecolor="#ECF0F1", edgecolor="white", label="Partial last batch")
    ax.legend(handles=[full_patch, partial_patch], loc="lower right", fontsize=8)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(m["total_mb"] for m in MODELS) * 1.22)

    plt.tight_layout()
    save(fig, "batch_structure_horizontal")


# -----------------------------------------------------------------------------
# 图 2: Treemap —— 用矩形面积表示 batch 大小
# -----------------------------------------------------------------------------
def plot_batch_treemap():
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    axes = axes.flatten()

    for idx, m in enumerate(MODELS):
        ax = axes[idx]
        batches = m["batch_list"]
        values = [b["mb"] for b in batches]
        total = sum(values)
        n_full = sum(1 for b in batches if b["full"])
        n_partial = len(batches) - n_full

        # 简单 treemap: 将 batch 按顺序排成网格
        n_cols = int(np.ceil(np.sqrt(len(batches))))
        n_rows = int(np.ceil(len(batches) / n_cols))

        cmap = LinearSegmentedColormap.from_list(
            "tm_cmap", ["#FFFFFF", m["color"]]
        )
        colors = cmap(np.array(values) / max(values) * 0.8 + 0.2)

        for k, (b, color) in enumerate(zip(batches, colors)):
            row = k // n_cols
            col = k % n_cols
            rect = mpatches.FancyBboxPatch(
                (col, n_rows - 1 - row),
                0.95,
                0.95,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                facecolor=color,
                edgecolor="white",
                linewidth=1.5,
            )
            ax.add_patch(rect)

        ax.set_xlim(-0.1, n_cols)
        ax.set_ylim(-0.1, n_rows)
        ax.set_aspect("equal")
        ax.axis("off")

        # 标题
        ax.set_title(
            f"{m['name']} ({m['model']})\n"
            f"{m['batches']} batches, {m['total_mb']:.2f} MB, {m['params']:,} params",
            fontsize=10,
            fontweight="bold",
            pad=8,
        )

        # 标注 batch 索引（小数字）
        for k, b in enumerate(batches):
            row = k // n_cols
            col = k % n_cols
            fontsize = 7 if len(batches) > 30 else 9
            ax.text(
                col + 0.48,
                n_rows - 1 - row + 0.48,
                f"{b['idx']}",
                ha="center",
                va="center",
                fontsize=fontsize,
                color="white" if b["full"] else "#333333",
                fontweight="bold",
            )

    plt.suptitle(
        "Treemap of CKKS Ciphertext Batches (area proportional to batch size)",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    save(fig, "batch_treemap")


# -----------------------------------------------------------------------------
# 图 3: Batch 数量 vs 平均 batch 大小对比
# -----------------------------------------------------------------------------
def plot_batch_size_comparison():
    fig, ax = plt.subplots(figsize=(8, 5))

    names = [m["name"] for m in MODELS]
    batch_counts = [m["batches"] for m in MODELS]
    avg_batch_params = [m["params"] / m["batches"] for m in MODELS]
    avg_batch_mb = [m["total_mb"] / m["batches"] for m in MODELS]

    x = np.arange(len(names))
    width = 0.35

    bars1 = ax.bar(x - width / 2, batch_counts, width, color="#3498DB", label="Number of Batches", edgecolor="white")
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width / 2, avg_batch_mb, width, color="#E67E22", label="Avg. Batch Size (MB)", edgecolor="white")

    # 数值标注
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(
            f"{int(height)}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    for bar in bars2:
        height = bar.get_height()
        ax2.annotate(
            f"{height:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_xlabel("Dataset", fontsize=11)
    ax.set_ylabel("Number of Batches", fontsize=11, color="#3498DB")
    ax2.set_ylabel("Average Batch Size (MB)", fontsize=11, color="#E67E22")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.tick_params(axis="y", labelcolor="#3498DB")
    ax2.tick_params(axis="y", labelcolor="#E67E22")

    ax.set_title("Batch Count vs. Average Batch Size", fontsize=12, fontweight="bold", pad=10)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    plt.tight_layout()
    save(fig, "batch_size_comparison")


# -----------------------------------------------------------------------------
# 图 4: 带宽 CDF + Batch 结构 组合图（和带宽图放一起展示）
# -----------------------------------------------------------------------------
def plot_bandwidth_and_batches():
    fig = plt.figure(figsize=(12, 4.2))

    # 左侧: 带宽 CDF（复刻 FedFetch 风格）
    ax1 = plt.subplot(1, 2, 1)
    np.random.seed(42)
    # 模拟 FedFetch-like 带宽（对数正态，Mbps）
    upload = np.random.lognormal(mean=2.8, sigma=1.2, size=5000)  # Mbps
    download = np.random.lognormal(mean=4.4, sigma=1.0, size=5000)
    upload = np.clip(upload, 0.01, 1000)
    download = np.clip(download, 0.01, 1000)

    for data, label, color in [(upload, "Upload", "#3498DB"), (download, "Download", "#E74C3C")]:
        sorted_data = np.sort(data)
        cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        ax1.plot(sorted_data, cdf, label=label, color=color, linewidth=2)
        ax1.fill_between(sorted_data, 0, cdf, color=color, alpha=0.15)

    ax1.set_xscale("log")
    ax1.set_xlim(0.01, 1000)
    ax1.set_ylim(0, 1)
    ax1.set_xlabel("Bandwidth (Mbps)", fontsize=11)
    ax1.set_ylabel("Cumulative Distribution", fontsize=11)
    ax1.set_title("Bandwidth Heterogeneity", fontsize=12, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=9)
    ax1.grid(True, which="both", linestyle="--", alpha=0.3)

    # 右侧: batch 结构
    ax2 = plt.subplot(1, 2, 2)
    y_pos = np.arange(len(MODELS))
    bar_height = 0.5

    for i, m in enumerate(MODELS):
        left = 0.0
        batches = m["batch_list"]
        cmap = LinearSegmentedColormap.from_list(
            "batch_cmap", ["#E8F6F3", m["color"]]
        )
        colors = cmap(np.linspace(0.35, 0.95, len(batches)))

        for j, b in enumerate(batches):
            ax2.barh(
                i,
                b["mb"],
                left=left,
                height=bar_height,
                color=colors[j],
                edgecolor="white",
                linewidth=0.5,
            )
            left += b["mb"]

        ax2.text(
            left + 0.8,
            i,
            f"{m['batches']} batches",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
        )

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{m['name']}" for m in MODELS], fontsize=10)
    ax2.set_xlabel("Encrypted Model Size (MB)", fontsize=11)
    ax2.set_title("CKKS-SIMD Batch Decomposition", fontsize=12, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.set_xlim(0, max(m["total_mb"] for m in MODELS) * 1.28)

    plt.tight_layout()
    save(fig, "bandwidth_and_batches")


# -----------------------------------------------------------------------------
# 图 5: Waffle Chart —— 用网格方块表示 batch 分布
# -----------------------------------------------------------------------------
def plot_batch_waffle():
    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    axes = axes.flatten()

    grid_size = 20  # 20x20 = 400 cells

    for idx, m in enumerate(MODELS):
        ax = axes[idx]
        batches = m["batch_list"]
        total_cells = grid_size * grid_size

        # 按 batch 大小分配 cell 数
        batch_cells = []
        allocated = 0
        for b in batches:
            cells = int(round(b["mb"] / m["total_mb"] * total_cells))
            batch_cells.append(cells)
            allocated += cells

        # 修正四舍五入误差
        diff = total_cells - allocated
        if diff != 0:
            batch_cells[-1] += diff

        cmap = LinearSegmentedColormap.from_list(
            "waffle_cmap", ["#FFFFFF", m["color"]]
        )
        colors = cmap(np.linspace(0.3, 0.95, len(batches)))

        cell_idx = 0
        for b_idx, (b, n_cells, color) in enumerate(zip(batches, batch_cells, colors)):
            for _ in range(n_cells):
                row = cell_idx // grid_size
                col = cell_idx % grid_size
                rect = mpatches.Rectangle(
                    (col, grid_size - 1 - row),
                    0.95,
                    0.95,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=0.5,
                )
                ax.add_patch(rect)
                cell_idx += 1

        ax.set_xlim(-0.5, grid_size - 0.5)
        ax.set_ylim(-0.5, grid_size - 0.5)
        ax.set_aspect("equal")
        ax.axis("off")

        # 中心文字
        ax.text(
            grid_size / 2 - 0.5,
            grid_size / 2 - 0.5,
            f"{m['batches']}\nbatches",
            ha="center",
            va="center",
            fontsize=18,
            fontweight="bold",
            color="#333333",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#CCCCCC", alpha=0.9),
        )

        ax.set_title(
            f"{m['name']} ({m['model']}) — {m['total_mb']:.2f} MB",
            fontsize=10,
            fontweight="bold",
            pad=8,
        )

    plt.suptitle(
        "Waffle Representation of CKKS Batch Proportions",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    plt.tight_layout()
    save(fig, "batch_waffle")


# -----------------------------------------------------------------------------
# 图 6: Slot Utilization —— 展示每个 batch 的 slot 使用比例
# -----------------------------------------------------------------------------
def plot_slot_utilization():
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes = axes.flatten()

    for idx, m in enumerate(MODELS):
        ax = axes[idx]
        batches = m["batch_list"]
        x = np.arange(len(batches))
        utilization = [b["params"] / SLOT_CAPACITY * 100 for b in batches]

        colors = [m["color"] if u >= 99 else "#E74C3C" for u in utilization]

        ax.bar(x, utilization, color=colors, edgecolor="white", linewidth=0.5)
        ax.axhline(y=100, color="#2C3E50", linestyle="--", linewidth=1.5, label="Full capacity")

        ax.set_xlabel("Batch Index", fontsize=10)
        ax.set_ylabel("Slot Utilization (%)", fontsize=10)
        ax.set_title(
            f"{m['name']} ({m['model']}) — {m['batches']} batches",
            fontsize=11,
            fontweight="bold",
        )
        ax.set_ylim(0, 110)
        ax.legend(loc="lower right", fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # 标注最后一个 batch 的利用率
        last_u = utilization[-1]
        if last_u < 100:
            ax.annotate(
                f"{last_u:.1f}%",
                xy=(len(batches) - 1, last_u),
                xytext=(len(batches) - 1, last_u + 15),
                ha="center",
                fontsize=8,
                fontweight="bold",
                color="#E74C3C",
                arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=1),
            )

    plt.suptitle(
        "CKKS SIMD Slot Utilization per Ciphertext Batch",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    plt.tight_layout()
    save(fig, "batch_slot_utilization")


# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------
def save(fig, name):
    """保存 PNG 和 PDF"""
    png_path = os.path.join(PIC_DIR, f"{name}.png")
    pdf_path = os.path.join(PIC_DIR, f"{name}.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {png_path}")
    print(f"[OK] {pdf_path}")


def main():
    print("=" * 60)
    print("Generating CKKS Batch Visualizations")
    print("=" * 60)
    plot_batch_structure()
    plot_batch_treemap()
    plot_batch_size_comparison()
    plot_bandwidth_and_batches()
    plot_batch_waffle()
    plot_slot_utilization()
    print("=" * 60)
    print(f"All plots saved to: {PIC_DIR}")


if __name__ == "__main__":
    main()
