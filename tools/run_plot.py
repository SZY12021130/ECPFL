"""
Experiment Plot Runner — 非交互式批量绘图
=============================================

根据 JSON 配置文件一键出图，无需编写 Python 代码。

用法:
    python tools/run_plot.py                    # 使用默认配置 tools/plot_config.json
    python tools/run_plot.py my_config.json     # 使用自定义配置

功能:
    • 支持 line / bar / stacked_bar / stacked_area / scatter / heatmap / multi_subplot
    • 每张图自动输出 PNG + PDF
    • 纯命令行运行，无需交互
"""

import argparse
import sys
from pathlib import Path

# 确保能 import 到 plotter
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.plotter import plot_from_config


def main():
    parser = argparse.ArgumentParser(description="根据 JSON 配置文件批量生成实验图表")
    parser.add_argument(
        "config",
        nargs="?",
        default="../tools/plot_config.json",
        help="JSON 配置文件路径 (默认: tools/plot_config.json)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[Error] 配置文件不存在: {config_path}")
        sys.exit(1)

    print(f"[Info] 读取配置: {config_path}")
    saved_files = plot_from_config(config_path)

    print(f"\n[Done] 共生成 {len(saved_files)} 个文件:")
    for f in saved_files:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
