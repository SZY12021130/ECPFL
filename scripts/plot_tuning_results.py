"""
绘制超参数调优实验结果
=====================
读取 tuning_results/*.json，生成损失-轮数图、准确率-轮数图、通信-准确率权衡图。

用法:
    python scripts/plot_tuning_results.py --input scripts/tuning_results/cifar10_resnet20_*.json
"""

import sys
import os
import json
import glob
import argparse
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_results(pattern: str):
    """加载匹配的 JSON 结果文件"""
    files = glob.glob(pattern)
    if not files:
        print(f"[Warning] 未找到匹配文件: {pattern}")
        return []

    all_summaries = []
    for f in sorted(files):
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
            if isinstance(data, list):
                all_summaries.extend(data)
            elif isinstance(data, dict) and 'groups' in data:
                all_summaries.extend(data['groups'])
    return all_summaries


def plot_loss_curves(summaries, out_dir):
    """绘制损失-轮数曲线"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    # 按投票方式分组
    vote_groups = defaultdict(list)
    strategy_groups = defaultdict(list)
    sparsity_groups = defaultdict(list)
    all_exps = []

    for s in summaries:
        if 'rounds_data' not in s or not s['rounds_data']:
            continue
        vote_mode = s.get('vote_mode', 'none')
        strategy = s.get('selection_strategy', 'unknown')
        sparsity = s.get('sparsity_rate', 1.0)

        vote_groups[vote_mode].append(s)
        strategy_groups[strategy].append(s)
        sparsity_groups[sparsity].append(s)
        all_exps.append(s)

    # Plot 1: 按投票方式分组
    ax = axes[0]
    for vote_mode, group in sorted(vote_groups.items()):
        for s in group[:3]:  # 每类最多3条，避免过乱
            rounds = [r['round'] for r in s['rounds_data']]
            losses = [r['test_loss'] for r in s['rounds_data']]
            label = f"{vote_mode} ({s['selection_strategy']}, s={s['sparsity_rate']})"
            ax.plot(rounds, losses, marker='o', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Loss')
    ax.set_title('Loss vs Round (by Vote Mode)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, alpha=0.3)

    # Plot 2: 按选择策略分组
    ax = axes[1]
    for strategy, group in sorted(strategy_groups.items()):
        for s in group[:3]:
            rounds = [r['round'] for r in s['rounds_data']]
            losses = [r['test_loss'] for r in s['rounds_data']]
            label = f"{strategy} ({s['vote_mode']}, s={s['sparsity_rate']})"
            ax.plot(rounds, losses, marker='s', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Loss')
    ax.set_title('Loss vs Round (by Selection Strategy)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, alpha=0.3)

    # Plot 3: 按稀疏率分组
    ax = axes[2]
    for sparsity, group in sorted(sparsity_groups.items()):
        for s in group[:3]:
            rounds = [r['round'] for r in s['rounds_data']]
            losses = [r['test_loss'] for r in s['rounds_data']]
            label = f"s={sparsity} ({s['selection_strategy']}, {s['vote_mode']})"
            ax.plot(rounds, losses, marker='^', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Loss')
    ax.set_title('Loss vs Round (by Sparsity Rate)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, alpha=0.3)

    # Plot 4: 所有实验的对比（仅最终准确率最高的5个）
    ax = axes[3]
    top5 = sorted(all_exps, key=lambda x: x.get('final_test_acc', 0), reverse=True)[:5]
    for s in top5:
        rounds = [r['round'] for r in s['rounds_data']]
        losses = [r['test_loss'] for r in s['rounds_data']]
        label = f"{s['exp_id'][:30]}... ({s['final_test_acc']:.1f}%)"
        ax.plot(rounds, losses, marker='D', markersize=3, label=label, linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Loss')
    ax.set_title('Top 5 Configurations by Accuracy')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(out_dir, 'loss_curves.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 损失曲线: {out_path}")


def plot_accuracy_curves(summaries, out_dir):
    """绘制准确率-轮数曲线"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    vote_groups = defaultdict(list)
    strategy_groups = defaultdict(list)
    sparsity_groups = defaultdict(list)
    all_exps = []

    for s in summaries:
        if 'rounds_data' not in s or not s['rounds_data']:
            continue
        vote_groups[s.get('vote_mode', 'none')].append(s)
        strategy_groups[s.get('selection_strategy', 'unknown')].append(s)
        sparsity_groups[s.get('sparsity_rate', 1.0)].append(s)
        all_exps.append(s)

    # Plot 1: 按投票方式
    ax = axes[0]
    for vote_mode, group in sorted(vote_groups.items()):
        for s in group[:3]:
            rounds = [r['round'] for r in s['rounds_data']]
            accs = [r['test_acc'] for r in s['rounds_data']]
            label = f"{vote_mode} ({s['selection_strategy']}, s={s['sparsity_rate']})"
            ax.plot(rounds, accs, marker='o', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('Accuracy vs Round (by Vote Mode)')
    ax.legend(fontsize=7, loc='lower right')
    ax.grid(True, alpha=0.3)

    # Plot 2: 按选择策略
    ax = axes[1]
    for strategy, group in sorted(strategy_groups.items()):
        for s in group[:3]:
            rounds = [r['round'] for r in s['rounds_data']]
            accs = [r['test_acc'] for r in s['rounds_data']]
            label = f"{strategy} ({s['vote_mode']}, s={s['sparsity_rate']})"
            ax.plot(rounds, accs, marker='s', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('Accuracy vs Round (by Selection Strategy)')
    ax.legend(fontsize=7, loc='lower right')
    ax.grid(True, alpha=0.3)

    # Plot 3: 按稀疏率
    ax = axes[2]
    for sparsity, group in sorted(sparsity_groups.items()):
        for s in group[:3]:
            rounds = [r['round'] for r in s['rounds_data']]
            accs = [r['test_acc'] for r in s['rounds_data']]
            label = f"s={sparsity} ({s['selection_strategy']}, {s['vote_mode']})"
            ax.plot(rounds, accs, marker='^', markersize=3, label=label, alpha=0.7)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('Accuracy vs Round (by Sparsity Rate)')
    ax.legend(fontsize=7, loc='lower right')
    ax.grid(True, alpha=0.3)

    # Plot 4: Top 5
    ax = axes[3]
    top5 = sorted(all_exps, key=lambda x: x.get('final_test_acc', 0), reverse=True)[:5]
    for s in top5:
        rounds = [r['round'] for r in s['rounds_data']]
        accs = [r['test_acc'] for r in s['rounds_data']]
        label = f"{s['exp_id'][:30]}... ({s['final_test_acc']:.1f}%)"
        ax.plot(rounds, accs, marker='D', markersize=3, label=label, linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('Top 5 Configurations by Accuracy')
    ax.legend(fontsize=7, loc='lower right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(out_dir, 'accuracy_curves.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 准确率曲线: {out_path}")


def plot_communication_tradeoff(summaries, out_dir):
    """绘制通信-准确率权衡图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]

    # Plot 1: 总通信量 vs 最终准确率
    ax = axes[0]
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    vote_modes = sorted(set(s.get('vote_mode', 'none') for s in valid))
    color_map = {vm: colors[i % len(colors)] for i, vm in enumerate(vote_modes)}

    for s in valid:
        vm = s.get('vote_mode', 'none')
        ax.scatter(s['total_comm_mb'], s['final_test_acc'],
                   c=[color_map[vm]], s=100, alpha=0.7, edgecolors='black', linewidth=0.5)

    # 添加标签（仅Top 5）
    top5 = sorted(valid, key=lambda x: x['final_test_acc'], reverse=True)[:5]
    for s in top5:
        ax.annotate(s['exp_id'][:25],
                    (s['total_comm_mb'], s['final_test_acc']),
                    fontsize=7, alpha=0.8)

    ax.set_xlabel('Total Communication (MB)')
    ax.set_ylabel('Final Test Accuracy (%)')
    ax.set_title('Communication vs Accuracy Tradeoff')
    ax.grid(True, alpha=0.3)

    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='w',
                              markerfacecolor=color_map[vm], markersize=10, label=vm)
                       for vm in vote_modes]
    ax.legend(handles=legend_elements, loc='lower right')

    # Plot 2: 平均轮次时间 vs 最终准确率
    ax = axes[1]
    strategies = sorted(set(s.get('selection_strategy', 'unknown') for s in valid))
    color_map2 = {st: colors[i % len(colors)] for i, st in enumerate(strategies)}

    for s in valid:
        st = s.get('selection_strategy', 'unknown')
        ax.scatter(s['avg_round_time_sec'], s['final_test_acc'],
                   c=[color_map2[st]], s=100, alpha=0.7, edgecolors='black', linewidth=0.5)

    for s in top5:
        ax.annotate(s['exp_id'][:25],
                    (s['avg_round_time_sec'], s['final_test_acc']),
                    fontsize=7, alpha=0.8)

    ax.set_xlabel('Average Round Time (s)')
    ax.set_ylabel('Final Test Accuracy (%)')
    ax.set_title('Time vs Accuracy Tradeoff')
    ax.grid(True, alpha=0.3)

    legend_elements = [Line2D([0], [0], marker='o', color='w',
                              markerfacecolor=color_map2[st], markersize=10, label=st)
                       for st in strategies]
    ax.legend(handles=legend_elements, loc='lower right')

    plt.tight_layout()
    out_path = os.path.join(out_dir, 'tradeoff.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 权衡图: {out_path}")


def generate_markdown_report(summaries, out_dir):
    """生成 Markdown 汇总报告"""
    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]
    valid.sort(key=lambda x: x['final_test_acc'], reverse=True)

    lines = [
        "# CKKS-Fed 超参数调优实验报告",
        f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"\n## 实验概览\n",
        f"总实验数: {len(summaries)} | 成功: {len(valid)}\n",
        "## 配置排名（按最终准确率）\n",
        "| 排名 | 实验ID | 选择策略 | 投票方式 | 稀疏率 | 预取 | 准确率 | 通信(MB) | 轮时(s) |",
        "|-----|--------|---------|---------|--------|------|--------|----------|--------|",
    ]

    for i, s in enumerate(valid[:20], 1):
        pf = "✓" if s.get('prefetch_enabled', True) else "✗"
        lines.append(
            f"| {i} | `{s['exp_id']}` | {s['selection_strategy']} | {s['vote_mode']} | "
            f"{s['sparsity_rate']} | {pf} | {s['final_test_acc']:.2f}% | "
            f"{s['total_comm_mb']:.2f} | {s['avg_round_time_sec']:.2f} |"
        )

    lines.extend([
        "\n## 图表\n",
        "- 损失曲线: `loss_curves.png`",
        "- 准确率曲线: `accuracy_curves.png`",
        "- 通信-准确率权衡: `tradeoff.png`",
    ])

    out_path = os.path.join(out_dir, 'report.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[Report] Markdown报告: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="绘制调优结果")
    parser.add_argument("--input", type=str, default="scripts/tuning_results/*.json",
                        help="结果文件 glob 模式")
    parser.add_argument("--out_dir", type=str, default="scripts/tuning_results/plots",
                        help="输出目录")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    summaries = load_results(args.input)
    if not summaries:
        print("[Error] 没有加载到任何结果")
        return

    print(f"[Info] 加载了 {len(summaries)} 个实验结果")
    plot_loss_curves(summaries, args.out_dir)
    plot_accuracy_curves(summaries, args.out_dir)
    plot_communication_tradeoff(summaries, args.out_dir)
    generate_markdown_report(summaries, args.out_dir)
    print(f"\n[Done] 所有图表已保存到: {args.out_dir}")


if __name__ == "__main__":
    from datetime import datetime
    main()
