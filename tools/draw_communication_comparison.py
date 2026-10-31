#!/usr/bin/env python3
"""
Communication Cost Comparison — High BW vs Low BW (filter_low_bandwidth)
=======================================================================

对比两个 MNIST 实验的通信量：
  - 高带宽 (filter_low_bandwidth=true): experiment_20260602_173955
  - 低带宽 (filter_low_bandwidth=false): experiment_20260602_221009

用法:
    python tools/draw_communication_comparison.py
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.plotter import Plotter

OUTPUT_DIR = PROJECT_ROOT / "communication"

EXPERIMENTS = {
    "high_bw": {
        "log": "results/experiment_20260602_173955/experiment.log",
        "label": "MNIST (High BW, filter=True)",
    },
    "low_bw": {
        "log": "results/experiment_20260602_221009/experiment.log",
        "label": "MNIST (Low BW, filter=False)",
    },
}


def parse_comm_log(log_path: Path):
    upload, fetch = [], []
    pattern = re.compile(
        r"通信汇总:\s*↑([\d.]+)\s*MB\s*\|"
        r".*?FV\(fetch[^)]+\)=([\d.]+)\s*(?:MB|B)\s*\|"
    )
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                up = float(m.group(1))
                fv_raw = m.group(2)
                fv = float(fv_raw) if fv_raw != "0" else 0.0
                upload.append(up)
                fetch.append(fv)
    n = len(upload)
    return {
        "rounds": list(range(1, n + 1)),
        "upload": upload,
        "fetch": fetch,
    }


def draw_comparison(data_dict: dict):
    p = Plotter(
        style=["science", "grid"],
        theme="paper",
        output_dir=OUTPUT_DIR,
        figsize=(6, 4),
        dpi=300,
        use_latex=False,
    )

    plot_configs = []
    for name, label in [("high_bw", "(a) High BW"), ("low_bw", "(b) Low BW")]:
        d = data_dict[name]
        plot_configs.append({
            "type": "stacked_area",
            "data": {
                "x": d["rounds"],
                "series": {
                    "Upload": d["upload"],
                    "Fetch":  d["fetch"],
                },
            },
            "xlabel": "Round",
            "ylabel": "Cost (MB)",
            "title": f"{label}",
            "colors": {"Upload": "#3498db", "Fetch": "#e74c3c"},
            "legend_loc": "upper right",
        })

    p.multi_subplot(
        plot_configs=plot_configs,
        nrows=1, ncols=2,
        figsize=(12, 4.5),
        filename="comm_mnist_bw_comparison",
    )
    print("[Done] Saved: communication/comm_mnist_bw_comparison.png")


def print_stats(data_dict: dict):
    print("\n" + "=" * 60)
    print("COMMUNICATION STATISTICS")
    print("=" * 60)
    for name, cfg in EXPERIMENTS.items():
        d = data_dict[name]
        up_avg = sum(d["upload"]) / len(d["upload"])
        fv_avg = sum(d["fetch"]) / len(d["fetch"])
        fv_max = max(d["fetch"])
        fv_nonzero = sum(1 for v in d["fetch"] if v > 0)
        print(f"\n{cfg['label']}:")
        print(f"  Upload avg:  {up_avg:.2f} MB")
        print(f"  Fetch avg:   {fv_avg:.2f} MB")
        print(f"  Fetch max:   {fv_max:.2f} MB")
        print(f"  Fetch >0:    {fv_nonzero}/{len(d['fetch'])} rounds ({fv_nonzero/len(d['fetch'])*100:.1f}%)")
        print(f"  Fetch ratio: {fv_avg/(up_avg+fv_avg)*100:.1f}% of total")


def main():
    print("=" * 60)
    print("Communication Cost Comparison")
    print("=" * 60)

    data_dict = {}
    for name, cfg in EXPERIMENTS.items():
        log_path = PROJECT_ROOT / cfg["log"]
        print(f"\n[Parsing] {cfg['label']}: {log_path}")
        d = parse_comm_log(log_path)
        data_dict[name] = d
        print(f"  Rounds: {len(d['rounds'])}")

    print_stats(data_dict)

    print("\n" + "=" * 60)
    print("Drawing comparison chart ...")
    print("=" * 60)
    draw_comparison(data_dict)

    print("\n[Done] All saved to communication/")


if __name__ == "__main__":
    main()
