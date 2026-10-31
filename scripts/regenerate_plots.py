#!/usr/bin/env python3
"""
Regenerate summary plots with white background, dual-axis accuracy+loss,
stacked communication charts, and CRTStack naming.
Reads from compare_analysis/all_results.json and per-experiment metrics.json.
"""

import os
import sys
import json
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── Style: clean white academic theme ──────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#333333',
    'axes.labelcolor': '#333333',
    'xtick.color': '#333333',
    'ytick.color': '#333333',
    'text.color': '#333333',
    'grid.color': '#CCCCCC',
    'grid.alpha': 0.6,
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,
    'legend.frameon': True,
    'legend.edgecolor': '#CCCCCC',
    'legend.facecolor': 'white',
    'legend.fontsize': 9,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'font.family': 'sans-serif',
    'font.size': 10,
})

COLORS = [
    '#1f77b4',  # Merged None     – blue
    '#ff7f0e',  # Merged Union    – orange
    '#2ca02c',  # Merged Threshold– green
    '#d62728',  # CRTStack None   – red
    '#9467bd',  # CRTStack Union  – purple
    '#8c564b',  # CRTStack Threshold– brown
]

MARKERS = ['o', 's', '^', 'D', 'v', 'p']


def format_label(tag: str) -> str:
    """Rename crtstack → CRTStack; drop 'None' suffix for cleaner labels."""
    parts = tag.replace('_', ' ').split()
    packing = 'CRTStack' if parts[0].lower() == 'crtstack' else parts[0].capitalize()
    vote = parts[1].capitalize() if len(parts) > 1 else ''
    if vote == 'None':
        return packing
    return f"{packing} {vote}"


def load_per_round(output_dir: str):
    path = os.path.join(output_dir, 'metrics.json')
    with open(path, 'r') as f:
        m = json.load(f)

    upload = [x / (1024 * 1024) for x in m.get('upload_cost', [])]
    download = [x / (1024 * 1024) for x in m.get('download_cost', [])]
    train_loss = m.get('train_loss', [])
    test_acc = m.get('test_acc', [])

    # time vectors
    local_train = m.get('local_train_time', [])
    encrypt = m.get('encryption_time', [])
    agg = m.get('aggregation_time', [])

    n_rounds = max(len(train_loss), 30)
    avg_train = []
    avg_enc = []
    for i in range(n_rounds):
        if len(local_train) >= (i + 1) * 30:
            avg_train.append(np.mean(local_train[i * 30:(i + 1) * 30]))
        else:
            avg_train.append(0.0)
        if len(encrypt) >= (i + 1) * 30:
            avg_enc.append(np.mean(encrypt[i * 30:(i + 1) * 30]))
        else:
            avg_enc.append(0.0)

    return {
        'upload': upload,
        'download': download,
        'train_loss': train_loss,
        'test_acc': test_acc,
        'avg_train_time': avg_train,
        'avg_encrypt_time': avg_enc,
        'agg_time': agg if len(agg) == n_rounds else [0.0] * n_rounds,
        'num_ciphertexts': m.get('num_ciphertexts', []),
    }


def plot_accuracy_comparison(all_results, per_round, out_dir):
    """Figure 1a: Test Accuracy over rounds."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlabel('Communication Round')
    ax.set_ylabel('Test Accuracy (%)')

    for i, res in enumerate(all_results):
        tag = res['tag']
        data = per_round[tag]
        rounds = np.arange(1, len(data['test_acc']) + 1)
        ax.plot(rounds, data['test_acc'], '-', color=COLORS[i],
                linewidth=2.0, alpha=0.9,
                marker=MARKERS[i], markersize=4.5, markevery=5,
                label=format_label(tag))

    ax.set_ylim(0, 100)
    ax.set_xlim(1, 30)
    ax.grid(True, alpha=0.4)
    ax.legend(loc='lower right', ncol=2, framealpha=0.95, fontsize=11)
    ax.tick_params(axis='both', labelsize=12)
    ax.xaxis.label.set_size(13)
    ax.yaxis.label.set_size(13)

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'accuracy_comparison.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] accuracy_comparison")


def plot_train_loss_comparison(all_results, per_round, out_dir):
    """Figure 1b: Training Loss over rounds."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlabel('Communication Round')
    ax.set_ylabel('Training Loss')

    for i, res in enumerate(all_results):
        tag = res['tag']
        data = per_round[tag]
        rounds = np.arange(1, len(data['train_loss']) + 1)
        ax.plot(rounds, data['train_loss'], '-', color=COLORS[i],
                linewidth=2.0, alpha=0.9,
                marker=MARKERS[i], markersize=4.5, markevery=5,
                label=format_label(tag))

    max_loss = max(max(d['train_loss']) for d in per_round.values())
    ax.set_ylim(0, max_loss * 1.15)
    ax.set_xlim(1, 30)
    ax.grid(True, alpha=0.4)
    ax.legend(loc='upper right', ncol=2, framealpha=0.95, fontsize=11)
    ax.tick_params(axis='both', labelsize=12)
    ax.xaxis.label.set_size(13)
    ax.yaxis.label.set_size(13)

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'train_loss_comparison.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] train_loss_comparison")


def plot_communication_stacked_bar(all_results, out_dir):
    """Figure 2: Horizontal stacked bar chart: Upload + Download per config."""
    fig, ax = plt.subplots(figsize=(9, 5))
    tags = [format_label(r['tag']) for r in all_results]
    upload = np.array([r['upload_mb'] for r in all_results])
    download = np.array([r['download_mb'] for r in all_results])

    y = np.arange(len(tags))
    bar_h = 0.55

    ax.barh(y, upload, height=bar_h, color='#3498DB', label='Upload', alpha=0.9)
    ax.barh(y, download, left=upload, height=bar_h, color='#E74C3C',
            label='Download', alpha=0.9)

    # Annotate total on the right
    for i in range(len(tags)):
        total = upload[i] + download[i]
        ax.text(total + 80, i, f'{total:,.0f} MB',
                va='center', ha='left', fontsize=9, color='#333333')

    ax.set_yticks(y)
    ax.set_yticklabels(tags)
    ax.set_xlabel('Total Communication (MB)')
    ax.set_title('Communication Breakdown by Configuration')
    ax.legend(loc='lower right')
    ax.grid(axis='x', alpha=0.4)
    ax.set_xlim(0, max(upload + download) * 1.25)

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'communication_stacked_bar.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] communication_stacked_bar")


def plot_communication_per_round(all_results, per_round, out_dir):
    """Figure 3: Per-round stacked area (Upload + Download) in 2×3 subplots."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
    axes = axes.flatten()

    max_total = 0
    for res in all_results:
        d = per_round[res['tag']]
        max_total = max(max_total, max(np.array(d['upload']) + np.array(d['download'])))

    for idx, (res, ax) in enumerate(zip(all_results, axes)):
        tag = res['tag']
        data = per_round[tag]
        rounds = np.arange(1, len(data['upload']) + 1)
        up = np.array(data['upload'])
        down = np.array(data['download'])

        ax.fill_between(rounds, 0, up, alpha=0.75, color='#3498DB', label='Upload')
        ax.fill_between(rounds, up, up + down, alpha=0.75, color='#E74C3C',
                        label='Download')

        ax.set_title(format_label(tag), fontsize=10.5)
        ax.set_xlabel('Round')
        if idx % 3 == 0:
            ax.set_ylabel('Communication (MB)')
        ax.set_xlim(1, 30)
        ax.set_ylim(0, max_total * 1.1)
        ax.grid(alpha=0.35)
        ax.tick_params(labelbottom=True)
        ax.legend(loc='upper right', fontsize=8)

    fig.suptitle('Per-Round Communication Breakdown', fontsize=13, y=1.02)
    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'communication_per_round.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] communication_per_round")


def plot_time_breakdown_per_round(all_results, per_round, out_dir):
    """Figure 4: Per-round time decomposition (Train + Encrypt + Aggregate).
    Note: Prefetch/Fetch not available in this experiment config."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
    axes = axes.flatten()

    max_total = 0
    for res in all_results:
        d = per_round[res['tag']]
        totals = np.array(d['avg_train_time']) + np.array(d['avg_encrypt_time']) + np.array(d['agg_time'])
        max_total = max(max_total, max(totals))

    for idx, (res, ax) in enumerate(zip(all_results, axes)):
        tag = res['tag']
        data = per_round[tag]
        rounds = np.arange(1, len(data['avg_train_time']) + 1)
        t = np.array(data['avg_train_time'])
        e = np.array(data['avg_encrypt_time'])
        a = np.array(data['agg_time'])

        b1 = t
        b2 = b1 + e

        ax.fill_between(rounds, 0, b1, alpha=0.75, color='#2ECC71', label='Train')
        ax.fill_between(rounds, b1, b2, alpha=0.75, color='#F39C12', label='Encrypt')
        ax.fill_between(rounds, b2, b2 + a, alpha=0.75, color='#9B59B6', label='Aggregate')

        ax.set_title(format_label(tag), fontsize=10.5)
        ax.set_xlabel('Round')
        if idx % 3 == 0:
            ax.set_ylabel('Time (s)')
        ax.set_xlim(1, 30)
        ax.set_ylim(0, max_total * 1.1)
        ax.grid(alpha=0.35)
        ax.tick_params(labelbottom=True)
        ax.legend(loc='upper right', fontsize=8)

    fig.suptitle('Per-Round Time Decomposition', fontsize=13, y=1.02)
    fig.text(0.5, -0.01,
             'Note: Prefetch/Fetch modules were not enabled in this experiment configuration.',
             ha='center', fontsize=9, style='italic', color='#666666')
    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'time_breakdown_per_round.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] time_breakdown_per_round")


def plot_accuracy_vs_communication(all_results, per_round, out_dir):
    """Figure 5: Scatter + annotated trajectory: Accuracy vs Cumulative Communication."""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for i, res in enumerate(all_results):
        tag = res['tag']
        data = per_round[tag]
        acc = np.array(data['test_acc'])
        up = np.array(data['upload'])
        down = np.array(data['download'])
        cum = np.cumsum(up + down)
        color = COLORS[i]

        ax.scatter(cum, acc, c=color, s=35, alpha=0.6, edgecolors='none', zorder=2)
        ax.plot(cum, acc, '-', color=color, linewidth=1.5, alpha=0.8,
                label=format_label(tag), zorder=3)
        # Mark final point
        ax.scatter(cum[-1], acc[-1], c=color, s=120, marker=MARKERS[i],
                   edgecolors='white', linewidths=1.2, zorder=4)

    ax.set_xlabel('Cumulative Communication (MB)')
    ax.set_ylabel('Test Accuracy (%)')
    ax.set_title('Accuracy vs Cumulative Communication')
    ax.legend(loc='lower right', ncol=2, framealpha=0.95)
    ax.grid(True, alpha=0.4)
    ax.set_ylim(70, 100)

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'accuracy_vs_communication.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] accuracy_vs_communication")


def plot_ciphertext_count(all_results, out_dir):
    """Figure 6: Horizontal bar chart comparing total ciphertext counts."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    tags = [format_label(r['tag']) for r in all_results]
    counts = [r['num_ciphertexts'] for r in all_results]
    colors = COLORS

    bars = ax.barh(tags, counts, color=colors, alpha=0.85, height=0.55)

    for bar, count in zip(bars, counts):
        ax.text(count + 80, bar.get_y() + bar.get_height() / 2,
                f'{count:,}', va='center', ha='left', fontsize=9)

    ax.set_xlabel('Total Ciphertexts Transmitted')
    ax.set_title('Ciphertext Count Comparison')
    ax.grid(axis='x', alpha=0.4)
    ax.set_xlim(0, max(counts) * 1.2)

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'ciphertext_count_comparison.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] ciphertext_count_comparison")


def plot_summary_table_figure(all_results, out_dir):
    """Figure 7: A clean table summarising the 6 configs."""
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis('off')
    ax.axis('tight')

    headers = ['Config', 'Final Acc', 'Total Comm (MB)', 'Upload (MB)',
               'Download (MB)', 'Ciphertexts']
    rows = []
    for r in all_results:
        rows.append([
            format_label(r['tag']),
            f"{r['test_acc'][-1]:.2f}%" if r.get('test_acc') else 'N/A',
            f"{r['upload_mb'] + r['download_mb']:,.0f}",
            f"{r['upload_mb']:,.0f}",
            f"{r['download_mb']:,.0f}",
            f"{r['num_ciphertexts']:,}",
        ])

    table = ax.table(cellText=rows, colLabels=headers, loc='center',
                     cellLoc='center', colColours=['#E8E8E8'] * len(headers))
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.1, 1.8)

    # Color rows by config group
    for i in range(len(rows)):
        for j in range(len(headers)):
            table[(i + 1, j)].set_facecolor('#F8F8F8' if i % 2 == 0 else 'white')

    plt.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(os.path.join(out_dir, f'summary_table.{ext}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("[OK] summary_table")


def main():
    summary_path = os.path.join(project_root, 'compare_analysis', 'all_results.json')
    with open(summary_path, 'r') as f:
        all_results = json.load(f)

    out_dir = os.path.join(project_root, 'compare_analysis', 'summary_plots')
    os.makedirs(out_dir, exist_ok=True)

    print("Loading per-round metrics …")
    per_round = {}
    for res in all_results:
        per_round[res['tag']] = load_per_round(res['output_dir'])

    print("Generating plots …")
    plot_accuracy_comparison(all_results, per_round, out_dir)
    plot_train_loss_comparison(all_results, per_round, out_dir)
    plot_communication_stacked_bar(all_results, out_dir)
    plot_communication_per_round(all_results, per_round, out_dir)
    plot_time_breakdown_per_round(all_results, per_round, out_dir)
    plot_accuracy_vs_communication(all_results, per_round, out_dir)
    plot_ciphertext_count(all_results, out_dir)
    plot_summary_table_figure(all_results, out_dir)

    print(f"\nAll plots saved to: {out_dir}")


if __name__ == '__main__':
    main()
