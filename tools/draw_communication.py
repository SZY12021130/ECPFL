#!/usr/bin/env python3
"""
Communication Cost Visualization — Prefetch vs No-Prefetch
===========================================================

从实验日志提取每轮通信量（Upload / Download / Fetch），
调用 tools.plotter 绘制堆叠面积图，输出到 communication/ 目录。

要求：
  - 不预取：Upload + Download（两层）
  - 预取：  Upload + Fetch（两层）

用法:
    python tools/draw_communication.py
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.plotter import Plotter

EXPERIMENTS = {
    "CIFAR-10": {
        "log": "results/experiment_20260602_154753/experiment.log",
        "label": "CIFAR-10",
    },
    "MNIST": {
        "log": "results/experiment_20260602_173955/experiment.log",
        "label": "MNIST",
    },
    "Fashion-MNIST": {
        "log": "results/experiment_20260602_180937/experiment.log",
        "label": "Fashion-MNIST",
    },
}

OUTPUT_DIR = PROJECT_ROOT / "communication"


def parse_comm_log(log_path: Path):
    """
    解析实验日志，提取每轮的 Upload、effective(Download 基线)、FV(fetch)。

    返回:
        {
            "rounds": [1, 2, 3, ...],
            "upload":   [502.13, 470.22, ...],   # MB
            "download": [353.52, 331.07, ...],   # effective，作为不预取基线
            "fetch":    [0.0,   353.52, 60.15, ...], # MB
        }
    """
    upload, download, fetch = [], [], []

    # 匹配：↑446.31 MB | ... effective↓=314.24 MB ... | FV(fetch↓)=60.15 MB ... | TV=506.47 MB
    # 注意日志中的 ↓ 是 UTF-8 特殊字符，用 [^=]+? 宽松匹配
    pattern = re.compile(
        r"通信汇总:\s*↑([\d.]+)\s*MB\s*\|"
        r".*?FV\(fetch[^)]+\)=([\d.]+)\s*(?:MB|B)\s*\|"
        r".*?effective[^=]+?=([\d.]+)\s*MB"
        r".*?PV\(prefetch[^)]+\)=([\d.]+)\s*(?:MB|B)"
    )

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                up = float(m.group(1))
                fv_raw = m.group(2)
                fv = float(fv_raw) if fv_raw != "0" else 0.0
                eff = float(m.group(3))

                upload.append(up)
                download.append(eff)
                fetch.append(fv)

    n = len(upload)
    return {
        "rounds": list(range(1, n + 1)),
        "upload": upload,
        "download": download,
        "fetch": fetch,
    }


def draw_no_prefetch(data_dict: dict):
    """
    不预取情况 —— Upload + Download 堆叠。
    Download 使用 effective 作为无预取基线的下载量。
    """
    p = Plotter(
        style=["science", "grid"],
        theme="paper",
        output_dir=OUTPUT_DIR,
        figsize=(5, 3.5),
        dpi=300,
        use_latex=False,
    )

    plot_configs = []
    for name in ["MNIST", "CIFAR-10", "Fashion-MNIST"]:
        d = data_dict[name]
        plot_configs.append({
            "type": "stacked_area",
            "data": {
                "x": d["rounds"],
                "series": {
                    "Upload":   d["upload"],
                    "Download": d["download"],
                },
            },
            "xlabel": "Round",
            "ylabel": "Cost (MB)",
            "title": f"({chr(97 + len(plot_configs))}) {name} (No Prefetch)",
            "colors": {"Upload": "#3498db", "Download": "#e74c3c"},
            "legend_loc": "upper right",
        })

    p.multi_subplot(
        plot_configs=plot_configs,
        nrows=1, ncols=3,
        figsize=(15, 4),
        filename="comm_no_prefetch",
    )
    print("[Done] Saved: communication/comm_no_prefetch.png")


def draw_with_prefetch(data_dict: dict):
    """
    预取情况 —— Upload + Fetch 堆叠（只展示实际发生的 fetch）。
    """
    p = Plotter(
        style=["science", "grid"],
        theme="paper",
        output_dir=OUTPUT_DIR,
        figsize=(5, 3.5),
        dpi=300,
        use_latex=False,
    )

    plot_configs = []
    for name in ["MNIST", "CIFAR-10", "Fashion-MNIST"]:
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
            "title": f"({chr(97 + len(plot_configs))}) {name} (With Prefetch)",
            "colors": {"Upload": "#3498db", "Fetch": "#e74c3c"},
            "legend_loc": "upper right",
        })

    p.multi_subplot(
        plot_configs=plot_configs,
        nrows=1, ncols=3,
        figsize=(15, 4),
        filename="comm_with_prefetch",
    )
    print("[Done] Saved: communication/comm_with_prefetch.png")


def main():
    print("=" * 60)
    print("Communication Cost Visualization")
    print("=" * 60)

    data_dict = {}
    for name, cfg in EXPERIMENTS.items():
        log_path = PROJECT_ROOT / cfg["log"]
        print(f"\n[Parsing] {name}: {log_path}")
        d = parse_comm_log(log_path)
        data_dict[name] = d
        print(f"  Rounds: {len(d['rounds'])}")
        print(f"  Upload   avg: {sum(d['upload'])/len(d['upload']):.2f} MB")
        print(f"  Download avg: {sum(d['download'])/len(d['download']):.2f} MB")
        print(f"  Fetch    avg: {sum(d['fetch'])/len(d['fetch']):.2f} MB")

    print("\n" + "=" * 60)
    print("Drawing charts ...")
    print("=" * 60)

    draw_no_prefetch(data_dict)
    draw_with_prefetch(data_dict)

    print("\n" + "=" * 60)
    print("All charts saved to communication/")
    print("=" * 60)


if __name__ == "__main__":
    main()
