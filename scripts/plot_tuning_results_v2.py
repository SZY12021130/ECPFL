"""
CKKS-Fed 超参数调优实验可视化 (增强版)
=====================================
支持:
  - 准确率/损失曲线 (对标论文风格)
  - 堆叠柱状图 (通信量分解)
  - 帕累托前沿 (准确率-通信权衡)
  - 热力图 (参数敏感性)
  - 时间分解图
  - 累积通信曲线

用法:
    python scripts/plot_tuning_results_v2.py \
        --input "scripts/tuning_results/*.json" \
        --out_dir "scripts/tuning_results/plots_v2"
"""

import sys
import os
import json
import glob
import argparse
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

# 设置中文字体和样式
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.dpi'] = 150

# 丰富配色方案 (ColorBrewer + 自定义)
COLORS = [
    '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00',
    '#FFFF33', '#A65628', '#F781BF', '#999999', '#66C2A5',
    '#FC8D62', '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F',
    '#E5C494', '#B3B3B3', '#1B9E77', '#D95F02', '#7570B3',
]

MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
LINESTYLES = ['-', '--', '-.', ':', (0, (5, 1)), (0, (3, 1, 1, 1))]


def load_results(pattern: str):
    """加载所有匹配的 JSON 结果"""
    files = glob.glob(pattern)
    all_data = []
    for f in sorted(files):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                if isinstance(data, list):
                    all_data.extend(data)
                elif isinstance(data, dict) and 'groups' in data:
                    all_data.extend(data['groups'])
        except Exception as e:
            print(f"[Warning] 加载 {f} 失败: {e}")
    return all_data


def extract_rounds_data(summary):
    """提取每轮数据为 numpy 数组"""
    rd = summary.get('rounds_data', [])
    if not rd:
        return None
    rounds = np.array([r['round'] for r in rd])
    acc = np.array([r['test_acc'] for r in rd])
    loss = np.array([r['test_loss'] for r in rd])
    times = np.array([r.get('round_time', 0) for r in rd])
    return {'rounds': rounds, 'acc': acc, 'loss': loss, 'times': times}


def get_display_label(s):
    """生成简洁的显示标签"""
    strategy = s.get('selection_strategy', '?')
    vote = s.get('vote_mode', '?')
    sparsity = s.get('sparsity_rate', 1.0)
    pf = 'PF' if s.get('prefetch_enabled', True) else 'NoPF'
    if sparsity >= 1.0:
        return f"{strategy} (no sparse, {pf})"
    return f"{strategy}+{vote} s={sparsity} ({pf})"


def get_group_key(s, group_by='vote_mode'):
    """按指定维度分组"""
    if group_by == 'vote_mode':
        return s.get('vote_mode', 'none')
    elif group_by == 'selection_strategy':
        return s.get('selection_strategy', 'unknown')
    elif group_by == 'sparsity_rate':
        return f"s={s.get('sparsity_rate', 1.0)}"
    elif group_by == 'prefetch':
        return 'Prefetch ON' if s.get('prefetch_enabled', True) else 'Prefetch OFF'
    return 'other'


# ============================================================================
# 1. 主图：准确率-轮数曲线 (对标论文风格)
# ============================================================================
def plot_accuracy_curves(summaries, out_dir):
    """准确率-轮数曲线，参考用户提供的图片风格"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    valid = [s for s in summaries if extract_rounds_data(s) is not None]
    if not valid:
        print("[Plot] 无有效数据，跳过 accuracy_curves")
        return

    # ---- 左图：按投票方式分组 ----
    ax = axes[0]
    groups = defaultdict(list)
    for s in valid:
        groups[get_group_key(s, 'vote_mode')].append(s)

    for i, (gname, group) in enumerate(sorted(groups.items())):
        for j, s in enumerate(group):
            d = extract_rounds_data(s)
            label = get_display_label(s) if j == 0 else None
            ax.plot(d['rounds'], d['acc'],
                    color=COLORS[i % len(COLORS)],
                    marker=MARKERS[j % len(MARKERS)],
                    markersize=3,
                    markevery=max(1, len(d['rounds'])//10),
                    linewidth=1.8,
                    alpha=0.75,
                    label=label)

    ax.set_xlabel('Rounds', fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('Test Accuracy vs. Rounds (by Vote Mode)', fontweight='bold')
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', framealpha=0.9, edgecolor='gray')
    ax.set_ylim(bottom=0)

    # ---- 右图：Top-K 最佳配置 ----
    ax = axes[1]
    top_configs = sorted(valid,
                         key=lambda x: x.get('final_test_acc', 0),
                         reverse=True)[:6]

    for i, s in enumerate(top_configs):
        d = extract_rounds_data(s)
        label = f"{get_display_label(s)} ({s['final_test_acc']:.1f}%)"
        ax.plot(d['rounds'], d['acc'],
                color=COLORS[i % len(COLORS)],
                marker=MARKERS[i % len(MARKERS)],
                markersize=4,
                markevery=max(1, len(d['rounds'])//10),
                linewidth=2.2,
                alpha=0.85,
                label=label)

    ax.set_xlabel('Rounds', fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontweight='bold')
    ax.set_title('Top-6 Configurations by Final Accuracy', fontweight='bold')
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', framealpha=0.9, edgecolor='gray')
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    out_path = os.path.join(out_dir, '01_accuracy_curves.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 准确率曲线: {out_path}")


# ============================================================================
# 2. 损失-轮数曲线
# ============================================================================
def plot_loss_curves(summaries, out_dir):
    """损失-轮数曲线"""
    fig, ax = plt.subplots(figsize=(10, 6))

    valid = [s for s in summaries if extract_rounds_data(s) is not None]
    if not valid:
        return

    top_configs = sorted(valid,
                         key=lambda x: x.get('final_test_acc', 0),
                         reverse=True)[:8]

    for i, s in enumerate(top_configs):
        d = extract_rounds_data(s)
        label = f"{get_display_label(s)}"
        ax.semilogy(d['rounds'], d['loss'],
                    color=COLORS[i % len(COLORS)],
                    marker=MARKERS[i % len(MARKERS)],
                    markersize=3,
                    markevery=max(1, len(d['rounds'])//10),
                    linewidth=1.8,
                    alpha=0.75,
                    label=label)

    ax.set_xlabel('Rounds', fontweight='bold')
    ax.set_ylabel('Test Loss (log scale)', fontweight='bold')
    ax.set_title('Test Loss vs. Rounds (Top-8 Configurations)', fontweight='bold')
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', framealpha=0.9, edgecolor='gray')

    plt.tight_layout()
    out_path = os.path.join(out_dir, '02_loss_curves.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 损失曲线: {out_path}")


# ============================================================================
# 3. 堆叠柱状图：通信量分解
# ============================================================================
def plot_communication_stacked(summaries, out_dir):
    """堆叠柱状图：每轮通信量分解 (Upload + Fetch + Prefetch)"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]
    top5 = sorted(valid, key=lambda x: x['final_test_acc'], reverse=True)[:5]

    # ---- 左图：Top 5 配置的每轮通信分解 ----
    ax = axes[0]
    x = np.arange(len(top5))
    width = 0.6

    upload_vals = [s.get('total_comm_mb', 0) * 0.6 for s in top5]  # 估算上传占比
    # 实际metrics中没有细分，用总通信量
    comm_vals = [s.get('total_comm_mb', 0) for s in top5]
    # 由于我们没有每轮细分的通信量，用总通信量/轮数作为平均每轮
    avg_comm = [s.get('total_comm_mb', 0) / max(1, len(s.get('rounds_data', []))) for s in top5]

    bars = ax.bar(x, avg_comm, width,
                   color=[COLORS[i % len(COLORS)] for i in range(len(top5))],
                   edgecolor='black', linewidth=0.5, alpha=0.85)

    # 在柱子上标注数值
    for bar, val in zip(bars, avg_comm):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.1f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    labels = [get_display_label(s)[:25] for s in top5]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('Avg Communication per Round (MB)', fontweight='bold')
    ax.set_title('Average Communication per Round (Top-5)', fontweight='bold')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    # ---- 右图：总通信量堆叠柱状图 ----
    ax = axes[1]

    # 按投票方式分组，计算组内平均
    groups = defaultdict(list)
    for s in valid:
        groups[get_group_key(s, 'vote_mode')].append(s)

    group_names = []
    group_comm = []
    group_colors = []
    for i, (gname, group) in enumerate(sorted(groups.items())):
        avg_comm = sum(s.get('total_comm_mb', 0) for s in group) / len(group)
        group_names.append(gname)
        group_comm.append(avg_comm)
        group_colors.append(COLORS[i % len(COLORS)])

    bars = ax.barh(group_names, group_comm, color=group_colors,
                   edgecolor='black', linewidth=0.5, alpha=0.85)

    for bar, val in zip(bars, group_comm):
        ax.text(val + 1, bar.get_y() + bar.get_height()/2,
                f'{val:.1f} MB',
                ha='left', va='center', fontsize=9, fontweight='bold')

    ax.set_xlabel('Total Communication (MB)', fontweight='bold')
    ax.set_title('Total Communication by Vote Mode (Average)', fontweight='bold')
    ax.grid(True, axis='x', linestyle='--', alpha=0.5)

    plt.tight_layout()
    out_path = os.path.join(out_dir, '03_communication_stacked.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 通信量堆叠图: {out_path}")


# ============================================================================
# 4. 时间分析图
# ============================================================================
def plot_time_analysis(summaries, out_dir):
    """时间分析：轮次时间和累积时间"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    valid = [s for s in summaries
             if extract_rounds_data(s) is not None and s.get('final_test_acc', 0) > 0]
    if not valid:
        return

    top5 = sorted(valid, key=lambda x: x['final_test_acc'], reverse=True)[:5]

    # ---- 左图：每轮时间曲线 ----
    ax = axes[0]
    for i, s in enumerate(top5):
        d = extract_rounds_data(s)
        label = f"{get_display_label(s)}"
        ax.plot(d['rounds'], d['times'],
                color=COLORS[i % len(COLORS)],
                marker=MARKERS[i % len(MARKERS)],
                markersize=3,
                markevery=max(1, len(d['rounds'])//8),
                linewidth=1.8,
                alpha=0.75,
                label=label)

    ax.set_xlabel('Rounds', fontweight='bold')
    ax.set_ylabel('Round Duration (s)', fontweight='bold')
    ax.set_title('Per-Round Duration (Top-5)', fontweight='bold')
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', framealpha=0.9, edgecolor='gray')

    # ---- 右图：平均轮次时间柱状图 ----
    ax = axes[1]

    # 按选择策略分组
    groups = defaultdict(list)
    for s in valid:
        groups[get_group_key(s, 'selection_strategy')].append(s)

    group_names = []
    group_time = []
    group_colors = []
    for i, (gname, group) in enumerate(sorted(groups.items())):
        avg_time = sum(s.get('avg_round_time_sec', 0) for s in group) / len(group)
        group_names.append(gname)
        group_time.append(avg_time)
        group_colors.append(COLORS[i % len(COLORS)])

    bars = ax.bar(range(len(group_names)), group_time, color=group_colors,
                  edgecolor='black', linewidth=0.5, alpha=0.85, width=0.6)

    for bar, val in zip(bars, group_time):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.0f}s',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xticks(range(len(group_names)))
    ax.set_xticklabels(group_names, rotation=0)
    ax.set_ylabel('Avg Round Time (s)', fontweight='bold')
    ax.set_title('Average Round Time by Selection Strategy', fontweight='bold')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    out_path = os.path.join(out_dir, '04_time_analysis.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 时间分析图: {out_path}")


# ============================================================================
# 5. 帕累托前沿：准确率-通信权衡
# ============================================================================
def plot_pareto_frontier(summaries, out_dir):
    """帕累托前沿：准确率 vs 通信量 + 时间"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]

    # ---- 左图：准确率 vs 总通信量 ----
    ax = axes[0]

    # 按投票方式着色，按选择策略标记形状
    vote_groups = sorted(set(s.get('vote_mode', 'none') for s in valid))
    strat_groups = sorted(set(s.get('selection_strategy', '?') for s in valid))

    vote_colors = {vm: COLORS[i % len(COLORS)] for i, vm in enumerate(vote_groups)}
    strat_markers = {st: MARKERS[i % len(MARKERS)] for i, st in enumerate(strat_groups)}

    for s in valid:
        vm = s.get('vote_mode', 'none')
        st = s.get('selection_strategy', '?')
        ax.scatter(s['total_comm_mb'], s['final_test_acc'],
                   c=vote_colors[vm],
                   marker=strat_markers[st],
                   s=150,
                   alpha=0.75,
                   edgecolors='black',
                   linewidth=0.8,
                   zorder=3)

    # 标注帕累托前沿点
    # 帕累托前沿：高准确率 + 低通信
    pareto = []
    for s in valid:
        dominated = False
        for other in valid:
            if (other['final_test_acc'] >= s['final_test_acc'] and
                other['total_comm_mb'] <= s['total_comm_mb'] and
                (other['final_test_acc'] > s['final_test_acc'] or
                 other['total_comm_mb'] < s['total_comm_mb'])):
                dominated = True
                break
        if not dominated:
            pareto.append(s)

    pareto.sort(key=lambda x: x['total_comm_mb'])
    if len(pareto) >= 2:
        px = [p['total_comm_mb'] for p in pareto]
        py = [p['final_test_acc'] for p in pareto]
        ax.plot(px, py, 'k--', linewidth=1.5, alpha=0.5, label='Pareto frontier')

    for p in pareto:
        ax.annotate(get_display_label(p)[:20],
                    (p['total_comm_mb'], p['final_test_acc']),
                    textcoords="offset points", xytext=(8, 5),
                    fontsize=7, alpha=0.85)

    ax.set_xlabel('Total Communication (MB)', fontweight='bold')
    ax.set_ylabel('Final Test Accuracy (%)', fontweight='bold')
    ax.set_title('Accuracy vs. Communication (Pareto Frontier)', fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)

    # 图例
    legend_elements = [Line2D([0], [0], marker='o', color='w',
                              markerfacecolor=vote_colors[vm], markersize=10,
                              label=vm, markeredgecolor='black')
                       for vm in vote_groups]
    legend_elements.append(Line2D([0], [0], linestyle='--', color='k',
                                   linewidth=1.5, label='Pareto frontier'))
    ax.legend(handles=legend_elements, loc='lower right',
              framealpha=0.9, edgecolor='gray')

    # ---- 右图：准确率 vs 平均轮次时间 ----
    ax = axes[1]
    for s in valid:
        vm = s.get('vote_mode', 'none')
        st = s.get('selection_strategy', '?')
        ax.scatter(s['avg_round_time_sec'], s['final_test_acc'],
                   c=vote_colors[vm],
                   marker=strat_markers[st],
                   s=150,
                   alpha=0.75,
                   edgecolors='black',
                   linewidth=0.8,
                   zorder=3)

    ax.set_xlabel('Average Round Time (s)', fontweight='bold')
    ax.set_ylabel('Final Test Accuracy (%)', fontweight='bold')
    ax.set_title('Accuracy vs. Round Time', fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(handles=legend_elements[:-1], loc='lower right',
              framealpha=0.9, edgecolor='gray')

    plt.tight_layout()
    out_path = os.path.join(out_dir, '05_pareto_frontier.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 帕累托前沿: {out_path}")


# ============================================================================
# 6. 热力图：参数敏感性
# ============================================================================
def plot_heatmap(summaries, out_dir):
    """热力图：不同参数组合的准确率/通信量"""
    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]
    if len(valid) < 4:
        print("[Plot] 实验数量不足，跳过热力图")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # 收集 (selection_strategy, vote_mode) -> 平均准确率
    acc_matrix = defaultdict(lambda: defaultdict(list))
    comm_matrix = defaultdict(lambda: defaultdict(list))

    for s in valid:
        st = s.get('selection_strategy', '?')
        vm = s.get('vote_mode', '?')
        acc_matrix[st][vm].append(s['final_test_acc'])
        comm_matrix[st][vm].append(s['total_comm_mb'])

    strategies = sorted(acc_matrix.keys())
    votes = sorted(set(vm for d in acc_matrix.values() for vm in d.keys()))

    acc_grid = np.zeros((len(strategies), len(votes)))
    comm_grid = np.zeros((len(strategies), len(votes)))

    for i, st in enumerate(strategies):
        for j, vm in enumerate(votes):
            vals = acc_matrix[st].get(vm, [0])
            acc_grid[i, j] = sum(vals) / len(vals)
            vals_c = comm_matrix[st].get(vm, [0])
            comm_grid[i, j] = sum(vals_c) / len(vals_c)

    # ---- 左图：准确率热力图 ----
    ax = axes[0]
    im = ax.imshow(acc_grid, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks(range(len(votes)))
    ax.set_yticks(range(len(strategies)))
    ax.set_xticklabels(votes, rotation=45, ha='right')
    ax.set_yticklabels(strategies)
    ax.set_title('Accuracy Heatmap (%)', fontweight='bold')

    # 标注数值
    for i in range(len(strategies)):
        for j in range(len(votes)):
            text = ax.text(j, i, f'{acc_grid[i, j]:.1f}',
                          ha="center", va="center", color="black",
                          fontsize=10, fontweight='bold')
    plt.colorbar(im, ax=ax, label='Accuracy (%)')

    # ---- 右图：通信量热力图 ----
    ax = axes[1]
    im = ax.imshow(comm_grid, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(votes)))
    ax.set_yticks(range(len(strategies)))
    ax.set_xticklabels(votes, rotation=45, ha='right')
    ax.set_yticklabels(strategies)
    ax.set_title('Communication Heatmap (MB)', fontweight='bold')

    for i in range(len(strategies)):
        for j in range(len(votes)):
            text = ax.text(j, i, f'{comm_grid[i, j]:.0f}',
                          ha="center", va="center", color="white",
                          fontsize=10, fontweight='bold')
    plt.colorbar(im, ax=ax, label='Total Communication (MB)')

    plt.tight_layout()
    out_path = os.path.join(out_dir, '06_heatmap.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 热力图: {out_path}")


# ============================================================================
# 7. 综合仪表盘 (Dashboard)
# ============================================================================
def plot_dashboard(summaries, out_dir):
    """综合仪表盘：所有关键指标一览"""
    valid = [s for s in summaries if s.get('final_test_acc', 0) > 0]
    if not valid:
        return

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    top6 = sorted(valid, key=lambda x: x['final_test_acc'], reverse=True)[:6]

    # ---- (0,0) 准确率曲线 ----
    ax1 = fig.add_subplot(gs[0, :2])
    for i, s in enumerate(top6):
        d = extract_rounds_data(s)
        ax1.plot(d['rounds'], d['acc'],
                 color=COLORS[i], marker=MARKERS[i], markersize=3,
                 markevery=max(1, len(d['rounds'])//10),
                 linewidth=2, alpha=0.8,
                 label=f"{get_display_label(s)[:30]}")
    ax1.set_xlabel('Rounds')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_title('Test Accuracy Curves', fontweight='bold', fontsize=14)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='lower right', fontsize=8)

    # ---- (0,2) 最终准确率排名 ----
    ax2 = fig.add_subplot(gs[0, 2])
    labels = [get_display_label(s)[:20] for s in top6]
    values = [s['final_test_acc'] for s in top6]
    colors = [COLORS[i] for i in range(len(top6))]
    bars = ax2.barh(range(len(top6)), values, color=colors,
                    edgecolor='black', linewidth=0.5, alpha=0.85)
    ax2.set_yticks(range(len(top6)))
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel('Accuracy (%)')
    ax2.set_title('Final Accuracy Ranking', fontweight='bold', fontsize=12)
    ax2.grid(True, axis='x', linestyle='--', alpha=0.5)
    for bar, val in zip(bars, values):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}%', va='center', fontsize=8, fontweight='bold')

    # ---- (1,0) 通信量对比 ----
    ax3 = fig.add_subplot(gs[1, 0])
    comm_vals = [s['total_comm_mb'] for s in top6]
    bars = ax3.bar(range(len(top6)), comm_vals, color=colors,
                   edgecolor='black', linewidth=0.5, alpha=0.85)
    ax3.set_xticks(range(len(top6)))
    ax3.set_xticklabels([f"#{i+1}" for i in range(len(top6))], fontsize=9)
    ax3.set_ylabel('Total Communication (MB)')
    ax3.set_title('Total Communication', fontweight='bold', fontsize=12)
    ax3.grid(True, axis='y', linestyle='--', alpha=0.5)

    # ---- (1,1) 时间对比 ----
    ax4 = fig.add_subplot(gs[1, 1])
    time_vals = [s['avg_round_time_sec'] for s in top6]
    bars = ax4.bar(range(len(top6)), time_vals, color=colors,
                   edgecolor='black', linewidth=0.5, alpha=0.85)
    ax4.set_xticks(range(len(top6)))
    ax4.set_xticklabels([f"#{i+1}" for i in range(len(top6))], fontsize=9)
    ax4.set_ylabel('Avg Round Time (s)')
    ax4.set_title('Average Round Time', fontweight='bold', fontsize=12)
    ax4.grid(True, axis='y', linestyle='--', alpha=0.5)

    # ---- (1,2) 准确率-通信散点 ----
    ax5 = fig.add_subplot(gs[1, 2])
    for s in valid:
        vm = s.get('vote_mode', 'none')
        idx = list(sorted(set(x.get('vote_mode', 'none') for x in valid))).index(vm)
        ax5.scatter(s['total_comm_mb'], s['final_test_acc'],
                   c=COLORS[idx % len(COLORS)], s=80, alpha=0.7,
                   edgecolors='black', linewidth=0.5)
    ax5.set_xlabel('Total Communication (MB)')
    ax5.set_ylabel('Accuracy (%)')
    ax5.set_title('Accuracy vs. Communication', fontweight='bold', fontsize=12)
    ax5.grid(True, linestyle='--', alpha=0.5)

    # ---- (2,:) 损失曲线 ----
    ax6 = fig.add_subplot(gs[2, :])
    for i, s in enumerate(top6):
        d = extract_rounds_data(s)
        ax6.semilogy(d['rounds'], d['loss'],
                     color=COLORS[i], marker=MARKERS[i], markersize=3,
                     markevery=max(1, len(d['rounds'])//10),
                     linewidth=1.8, alpha=0.8,
                     label=f"{get_display_label(s)[:35]}")
    ax6.set_xlabel('Rounds')
    ax6.set_ylabel('Test Loss (log scale)')
    ax6.set_title('Test Loss Curves', fontweight='bold', fontsize=14)
    ax6.grid(True, which='both', linestyle='--', alpha=0.5)
    ax6.legend(loc='upper right', fontsize=8, ncol=2)

    plt.suptitle('CKKS-Fed Hyperparameter Tuning Dashboard',
                 fontsize=16, fontweight='bold', y=0.995)

    out_path = os.path.join(out_dir, '07_dashboard.png')
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[Plot] 综合仪表盘: {out_path}")


# ============================================================================
# 主函数
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="CKKS-Fed 增强版可视化")
    parser.add_argument("--input", type=str,
                        default="scripts/tuning_results/*.json",
                        help="结果文件 glob 模式")
    parser.add_argument("--out_dir", type=str,
                        default=None,
                        help="输出目录 (默认: compare_analysis/{dataset}/plots)")
    parser.add_argument("--dataset", type=str,
                        default=None,
                        help="数据集名称 (用于自动推断输出目录)")
    args = parser.parse_args()

    summaries = load_results(args.input)
    if not summaries:
        print("[Error] 没有加载到任何结果")
        return

    # 自动推断数据集名称
    dataset = args.dataset
    if dataset is None and summaries:
        dataset = summaries[0].get('dataset', 'unknown')

    # 设置输出目录
    if args.out_dir is None:
        out_dir = os.path.join(PROJECT_ROOT, "compare_analysis", dataset, "plots")
    else:
        out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    print(f"[Info] 加载了 {len(summaries)} 个实验结果 (dataset={dataset})")
    print(f"[Info] 输出目录: {out_dir}")

    plot_accuracy_curves(summaries, out_dir)
    plot_loss_curves(summaries, out_dir)
    plot_communication_stacked(summaries, out_dir)
    plot_time_analysis(summaries, out_dir)
    plot_pareto_frontier(summaries, out_dir)
    plot_heatmap(summaries, out_dir)
    plot_dashboard(summaries, out_dir)

    print(f"\n[Done] 所有图表已保存到: {out_dir}")
    print("生成文件:")
    for f in sorted(os.listdir(out_dir)):
        if f.endswith('.png'):
            print(f"  - {f}")


if __name__ == "__main__":
    main()
