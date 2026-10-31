#!/usr/bin/env python
"""
绘制 FedPHE 实验结果的准确率曲线
调用 ckks_fed_robustness/tools/plotter.py
"""
import os
import sys
import json
import glob
from pathlib import Path

# 将 ckks_fed_robustness 加入路径以导入 plotter
CKKS_FED_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, CKKS_FED_ROOT)

try:
    from tools.plotter import Plotter
except ImportError as e:
    print(f"Failed to import plotter: {e}")
    print("Please ensure ckks_fed_robustness/tools/plotter.py exists.")
    sys.exit(1)


def find_experiment_dirs(result_dir="result"):
    """Find all experiment directories under result/."""
    if not os.path.exists(result_dir):
        return []
    dirs = [d for d in os.listdir(result_dir) if os.path.isdir(os.path.join(result_dir, d))]
    # Sort by name (which starts with date)
    dirs.sort()
    return [os.path.join(result_dir, d) for d in dirs]


def load_metrics(exp_dir):
    metrics_file = os.path.join(exp_dir, "metrics.json")
    if not os.path.exists(metrics_file):
        return None
    with open(metrics_file, "r") as f:
        return json.load(f)


def draw_accuracy_single(exp_dir, metrics):
    """Draw accuracy curve for a single experiment."""
    accuracy = metrics.get("accuracy", [])
    if not accuracy:
        print(f"No accuracy data in {exp_dir}")
        return

    rounds = list(range(1, len(accuracy) + 1))
    exp_name = os.path.basename(exp_dir)
    
    # Use plotter to draw
    p = Plotter(style=["science", "no-latex"], output_dir=os.path.join(exp_dir, "plots"), figsize=(8, 5))
    p.line(
        data={
            "FedPHE": {"x": rounds, "y": accuracy},
        },
        xlabel="Communication Round",
        ylabel="Test Accuracy (%)",
        title=f"Accuracy Curve — {exp_name}",
        filename="accuracy_curve",
    )
    print(f"Saved accuracy plot for {exp_name}")


def draw_accuracy_combined(result_dir="result"):
    """Draw combined accuracy curves for all experiments."""
    exp_dirs = find_experiment_dirs(result_dir)
    if not exp_dirs:
        print(f"No experiment directories found in {result_dir}")
        return

    data = {}
    for exp_dir in exp_dirs:
        metrics = load_metrics(exp_dir)
        if not metrics:
            continue
        accuracy = metrics.get("accuracy", [])
        if not accuracy:
            continue
        rounds = list(range(1, len(accuracy) + 1))
        exp_name = os.path.basename(exp_dir)
        data[exp_name] = {"x": rounds, "y": accuracy}

    if not data:
        print("No valid metrics found for combined plot.")
        return

    p = Plotter(style=["science", "no-latex"], output_dir=result_dir, figsize=(10, 6))
    p.line(
        data=data,
        xlabel="Communication Round",
        ylabel="Test Accuracy (%)",
        title="FedPHE Accuracy Comparison",
        filename="combined_accuracy",
    )
    print(f"Saved combined accuracy plot to {result_dir}/combined_accuracy.png")


def draw_communication(exp_dir, metrics):
    """Draw upload/download communication cost per round."""
    upload = metrics.get("upload_cost", [])
    download = metrics.get("download_cost", [])
    if not upload and not download:
        return

    rounds = list(range(1, len(upload) + 1))
    exp_name = os.path.basename(exp_dir)
    
    # Convert bytes to MB
    upload_mb = [x / (1024 * 1024) for x in upload]
    download_mb = [x / (1024 * 1024) for x in download]

    p = Plotter(style=["science", "no-latex"], output_dir=os.path.join(exp_dir, "plots"), figsize=(8, 5))
    p.line(
        data={
            "Upload": {"x": rounds, "y": upload_mb},
            "Download": {"x": rounds, "y": download_mb},
        },
        xlabel="Communication Round",
        ylabel="Communication Cost (MB)",
        title=f"Communication Cost — {exp_name}",
        filename="communication_cost",
    )
    print(f"Saved communication plot for {exp_name}")


def main():
    result_dir = "result"
    if len(sys.argv) > 1:
        result_dir = sys.argv[1]

    exp_dirs = find_experiment_dirs(result_dir)
    if not exp_dirs:
        print(f"No experiment directories found in {result_dir}")
        return

    print(f"Found {len(exp_dirs)} experiment(s):")
    for d in exp_dirs:
        print(f"  - {d}")

    for exp_dir in exp_dirs:
        metrics = load_metrics(exp_dir)
        if not metrics:
            continue
        draw_accuracy_single(exp_dir, metrics)
        draw_communication(exp_dir, metrics)

    draw_accuracy_combined(result_dir)
    print("\nAll plots generated!")


if __name__ == "__main__":
    main()
