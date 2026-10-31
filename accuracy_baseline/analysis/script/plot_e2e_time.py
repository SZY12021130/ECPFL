#!/usr/bin/env python3
"""
Generate three SCI-style figures for End-to-End Training Time analysis.
Output: accuracy_baseline/analysis/pic/
"""
import json, os, sys
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.plotter import COLOR_THEMES

plt.style.use(["science", "ieee"])

DATA_PATH = os.path.join(PROJECT_ROOT, "accuracy_baseline", "analysis", "time_data.json")
PIC_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "analysis", "pic")
os.makedirs(PIC_DIR, exist_ok=True)

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER", "ECPFL-UN", "ECPFL-TH", "ECPFL-RK"]

METHOD_COLORS = {
    "FedAvg+CKKS": "#4DBBD5",
    "FedPHE": "#E64B35",
    "ESAFL": "#00A087",
    "MASER": "#3C5488",
    "ECPFL-UN": "#F39B7F",
    "ECPFL-TH": "#8491B4",
    "ECPFL-RK": "#91D1C2",
}

DATASET_MARKERS = {
    "MNIST": "o",
    "FMNIST": "s",
    "CIFAR-10": "D",
    "SVHN": "^",
}


def extract(metric):
    out = {m: [] for m in METHODS}
    for ds in DATASETS:
        for m in METHODS:
            v = data[ds][m]
            out[m].append(v.get(metric, 0.0) if v else 0.0)
    return out


total = extract("total_time")
comm = extract("report_comm_time")
compute = extract("compute_time")


def savefig(fig, name):
    path_pdf = os.path.join(PIC_DIR, f"{name}.pdf")
    path_png = os.path.join(PIC_DIR, f"{name}.png")
    fig.savefig(path_pdf, bbox_inches="tight")
    fig.savefig(path_png, dpi=300, bbox_inches="tight")
    print(f"[Saved] {path_pdf}")
    print(f"[Saved] {path_png}")


# ------------------------------------------------------------------
# Figure 1: Total end-to-end time (grouped bar, log scale)
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(len(DATASETS))
width = 0.11
n_methods = len(METHODS)
for i, m in enumerate(METHODS):
    offset = width * (i - (n_methods - 1) / 2)
    ax.bar(x + offset, total[m], width, label=m, color=METHOD_COLORS[m], edgecolor="black", linewidth=0.5)

ax.set_xticks(x)
ax.set_xticklabels(DATASETS)
ax.set_xlabel("Dataset")
ax.set_ylabel("Total simulated time (s)")
ax.set_title("End-to-End Training Time")
ax.set_yscale("log")
ax.set_ylim(1, 200000)
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
ax.legend(loc="upper left", ncol=2, frameon=True)
plt.tight_layout()
savefig(fig, "e2e_total_time")
plt.close(fig)


# ------------------------------------------------------------------
# Figure 2: Serial communication time (grouped bar, log scale)
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
for i, m in enumerate(METHODS):
    offset = width * (i - (n_methods - 1) / 2)
    ax.bar(x + offset, comm[m], width, label=m, color=METHOD_COLORS[m], edgecolor="black", linewidth=0.5)

ax.set_xticks(x)
ax.set_xticklabels(DATASETS)
ax.set_xlabel("Dataset")
ax.set_ylabel("Serial communication time (s)")
ax.set_title("Communication Time (Serial Sum)")
ax.set_yscale("log")
ax.set_ylim(1, 10000)
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
ax.legend(loc="upper left", ncol=2, frameon=True)
plt.tight_layout()
savefig(fig, "e2e_comm_time")
plt.close(fig)


# ------------------------------------------------------------------
# Figure 3: Compute vs. Communication trade-off (scatter)
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 5))
# Plot per method, with dataset marker
for m in METHODS:
    for i, ds in enumerate(DATASETS):
        ax.scatter(
            comm[m][i],
            compute[m][i],
            color=METHOD_COLORS[m],
            marker=DATASET_MARKERS[ds],
            s=80,
            edgecolors="black",
            linewidth=0.5,
            alpha=0.85,
            label=m if i == 0 else "",
        )

# reference line y = x (comm == compute)
lims = [1, max(max(comm[m]) for m in METHODS) * 1.2]
ax.plot(lims, lims, "k--", linewidth=0.8, alpha=0.5, label="Comm = Compute")

ax.set_xlabel("Serial communication time (s)")
ax.set_ylabel("Compute time (s)")
ax.set_title("Compute vs. Communication Trade-off")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(lims)
ax.set_ylim(1, max(max(compute[m]) for m in METHODS) * 1.5)
ax.grid(True, linestyle="--", alpha=0.5)
# Dataset marker legend
from matplotlib.lines import Line2D
marker_legend = [Line2D([0], [0], marker=DATASET_MARKERS[ds], color="w", markeredgecolor="k", markersize=8, label=ds) for ds in DATASETS]
legend1 = ax.legend(handles=marker_legend, loc="lower right", title="Dataset", frameon=True)
ax.add_artist(legend1)
ax.legend(loc="upper right", ncol=2, frameon=True)
plt.tight_layout()
savefig(fig, "e2e_tradeoff")
plt.close(fig)

print("\n[OK] All figures saved to", PIC_DIR)
