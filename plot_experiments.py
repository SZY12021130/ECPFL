import json
import yaml
import numpy as np
import matplotlib.pyplot as plt
import scienceplots
from pathlib import Path
from collections import defaultdict

plt.style.use(['science', 'ieee', 'no-latex'])

results_dir = Path('results')
experiments = []

for exp_dir in sorted(results_dir.glob('experiment_*')):
    config_path = exp_dir / 'config.yaml'
    metrics_path = exp_dir / 'metrics.json'
    if not config_path.exists() or not metrics_path.exists():
        continue
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open(metrics_path, 'r', encoding='utf-8') as f:
            metrics = json.load(f)

        ckks = config.get('ckks', {})
        prefetch = config.get('prefetch', {})
        ptopk = ckks.get('ptopk', {})
        system = config.get('system', {})

        test_acc = metrics.get('test_acc', [])
        if not test_acc:
            continue

        exp_info = {
            'name': exp_dir.name,
            'num_rounds': system.get('num_rounds', 0),
            'num_clients': system.get('num_clients', 0),
            'dataset': config.get('data', {}).get('dataset', ''),
            'model': config.get('model', {}).get('name', ''),
            'poly_modulus_degree': ckks.get('poly_modulus_degree', 0),
            'coeff_mod_bit_sizes': str(ckks.get('coeff_mod_bit_sizes', [])),
            'global_scale': ckks.get('global_scale', 0),
            'packing_strategy': ckks.get('packing', {}).get('strategy', ''),
            'sparsification_strategy': ckks.get('sparsification', {}).get('strategy', 'none'),
            'sparsity_rate': ckks.get('sparsification', {}).get('sparsity_rate', 1.0),
            'enable_prefetch': prefetch.get('enable_prefetch', False),
            'use_sticky_sampling': prefetch.get('use_sticky_sampling', False),
            'ptopk_enable': ptopk.get('enable', False),
            'ptopk_server_mode': ptopk.get('server_mode', 'none'),
            'test_acc_last': test_acc[-1],
            'test_acc_max': max(test_acc),
            'test_acc_avg': sum(test_acc) / len(test_acc),
            'test_acc_all': test_acc,
            'total_round_time': sum(metrics.get('total_round_time', [0])),
            'total_comm_cost_mb': sum(metrics.get('total_communication_cost', [0])) / (1024 * 1024),
        }
        experiments.append(exp_info)
    except Exception as e:
        print(f'Skip {exp_dir.name}: {e}')

print(f'Total experiments loaded: {len(experiments)}')

# ==================== 过滤无用实验 ====================
filtered = [e for e in experiments if e['test_acc_max'] > 15.0]
removed = [e for e in experiments if e['test_acc_max'] <= 15.0]
if removed:
    print(f'\nFiltered {len(removed)} failed experiments (acc < 15%):')
    for e in removed:
        print(f'  {e["name"]}: last={e["test_acc_last"]:.2f}, sparse={e["sparsification_strategy"]}-{e["sparsity_rate"]}')

# 只保留相同基础配置
filtered = [e for e in filtered if (
    e['dataset'] == 'mnist' and
    e['model'] == 'lenet' and
    e['poly_modulus_degree'] == 8192 and
    e['coeff_mod_bit_sizes'] == '[60, 40, 40, 60]' and
    e['packing_strategy'] == 'merged'
)]

print(f'After filtering same-base-config: {len(filtered)} experiments')

# ==================== 构建对比数据集 ====================

# ---- Chart 1: Sparsity Rate vs Accuracy (Clients=10, Prefetch=True, no PTopk) ----
sparsity_data = defaultdict(list)
for e in filtered:
    if e['num_clients'] == 10 and e['enable_prefetch'] and not e['ptopk_enable']:
        if e['sparsification_strategy'] == 'none':
            sparsity_data['No Sparsification'].append(e['test_acc_last'])
        else:
            key = f'TopK {e["sparsity_rate"]:.0%}'
            sparsity_data[key].append(e['test_acc_last'])

# ---- Chart 2: PTopk Effect (Clients=30, topk=0.5, Prefetch=True) ----
ptopk_10r = defaultdict(list)
ptopk_15r = defaultdict(list)
for e in filtered:
    if e['num_clients'] == 30 and e['sparsification_strategy'] == 'topk' and abs(e['sparsity_rate'] - 0.5) < 0.01 and e['enable_prefetch']:
        if e['num_rounds'] == 10:
            label = 'Baseline'
            if e['ptopk_enable']:
                label = f'PTopk-{e["ptopk_server_mode"]}'
            ptopk_10r[label].append(e['test_acc_last'])
        elif e['num_rounds'] == 15:
            label = 'Baseline'
            if e['ptopk_enable']:
                label = f'PTopk-{e["ptopk_server_mode"]}'
            ptopk_15r[label].append(e['test_acc_last'])

# ---- Chart 3: Prefetch vs No-Prefetch (topk=1.0, no ptopk) ----
prefetch_data = {}
for e in filtered:
    if e['sparsification_strategy'] == 'topk' and abs(e['sparsity_rate'] - 1.0) < 0.01 and not e['ptopk_enable']:
        nc = e['num_clients']
        if nc not in prefetch_data:
            prefetch_data[nc] = {'prefetch': [], 'no_prefetch': []}
        if e['enable_prefetch']:
            prefetch_data[nc]['prefetch'].append(e['test_acc_last'])
        else:
            prefetch_data[nc]['no_prefetch'].append(e['test_acc_last'])

# 只保留两组都有数据的client数
prefetch_data = {k: v for k, v in prefetch_data.items() if v['prefetch'] and v['no_prefetch']}

# ---- Chart 4: Client Scale Effect (topk=0.5, Prefetch=True, no ptopk) ----
scale_data = defaultdict(list)
for e in filtered:
    if e['sparsification_strategy'] == 'topk' and abs(e['sparsity_rate'] - 0.5) < 0.01 and e['enable_prefetch'] and not e['ptopk_enable']:
        scale_data[e['num_clients']].append(e['test_acc_last'])

# ==================== 绘图 ====================
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

def bar_with_std(ax, labels, values_list, title, ylabel, color_map=None, ylim_bottom=None):
    means = [np.mean(v) if v else 0 for v in values_list]
    stds = [np.std(v) if len(v) > 1 else 0 for v in values_list]
    x = np.arange(len(labels))
    width = 0.6
    colors = color_map if color_map else ['#4472C4'] * len(labels)
    bars = ax.bar(x, means, width, yerr=stds, capsize=3, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right', fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    if ylim_bottom is not None:
        ax.set_ylim(bottom=ylim_bottom)
    for bar, mean, std in zip(bars, means, stds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + std + 0.5,
                f'{mean:.1f}', ha='center', va='bottom', fontsize=8)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

# ---- Plot 1: Sparsity Rate ----
# 排序: No Sparse 在前，然后按 sparsity_rate 排序
sparsity_keys = sorted(sparsity_data.keys(),
                       key=lambda k: (0 if k == 'No Sparsification' else 1,
                                      float(k.split()[1].rstrip('%'))/100 if k != 'No Sparsification' else 0))
sparsity_values = [sparsity_data[k] for k in sparsity_keys]
colors_sparsity = ['#70AD47' if k == 'No Sparsification' else '#4472C4' for k in sparsity_keys]

bar_with_std(axes[0, 0], sparsity_keys, sparsity_values,
             'Effect of Sparsity Rate on Test Accuracy\n(Clients=10, Prefetch=On)',
             'Test Accuracy (%)', colors_sparsity, ylim_bottom=90)

# ---- Plot 2: PTopk 10-round ----
if ptopk_10r:
    ptopk_labels_10 = list(ptopk_10r.keys())
    ptopk_values_10 = [ptopk_10r[k] for k in ptopk_labels_10]
    colors_10 = ['#C5504B' if 'Baseline' in l else '#4472C4' for l in ptopk_labels_10]
    bar_with_std(axes[0, 1], ptopk_labels_10, ptopk_values_10,
                 'PTopk Error-Feedback Effect (10 Rounds)\n(Clients=30, TopK=50%, Prefetch=On)',
                 'Test Accuracy (%)', colors_10, ylim_bottom=88)

# ---- Plot 3: PTopk 15-round ----
if ptopk_15r:
    ptopk_labels_15 = list(ptopk_15r.keys())
    ptopk_values_15 = [ptopk_15r[k] for k in ptopk_labels_15]
    colors_15 = []
    for l in ptopk_labels_15:
        if 'Baseline' in l:
            colors_15.append('#C5504B')
        elif 'delayed' in l:
            colors_15.append('#4472C4')
        else:
            colors_15.append('#ED7D31')
    bar_with_std(axes[1, 0], ptopk_labels_15, ptopk_values_15,
                 'PTopk Error-Feedback Effect (15 Rounds)\n(Clients=30, TopK=50%, Prefetch=On)',
                 'Test Accuracy (%)', colors_15, ylim_bottom=90)

# ---- Plot 4: Prefetch vs No-Prefetch ----
if prefetch_data:
    nc_keys = sorted(prefetch_data.keys())
    prefetch_labels = [f'{k} Clients' for k in nc_keys]
    prefetch_on_vals = [prefetch_data[k]['prefetch'] for k in nc_keys]
    prefetch_off_vals = [prefetch_data[k]['no_prefetch'] for k in nc_keys]

    x = np.arange(len(nc_keys))
    width = 0.35
    means_on = [np.mean(v) for v in prefetch_on_vals]
    means_off = [np.mean(v) for v in prefetch_off_vals]
    stds_on = [np.std(v) if len(v) > 1 else 0 for v in prefetch_on_vals]
    stds_off = [np.std(v) if len(v) > 1 else 0 for v in prefetch_off_vals]

    bars1 = axes[1, 1].bar(x - width/2, means_on, width, yerr=stds_on, capsize=3,
                           label='Prefetch On', color='#4472C4', edgecolor='black', linewidth=0.5)
    bars2 = axes[1, 1].bar(x + width/2, means_off, width, yerr=stds_off, capsize=3,
                           label='Prefetch Off', color='#ED7D31', edgecolor='black', linewidth=0.5)

    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(prefetch_labels, fontsize=9)
    axes[1, 1].set_ylabel('Test Accuracy (%)', fontsize=9)
    axes[1, 1].set_title('Prefetch Effect (No Sparsification)\n(TopK=100%, Sticky Sampling)', fontsize=10)
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(axis='y', linestyle='--', alpha=0.5)
    axes[1, 1].set_ylim(bottom=90)

    for bars, means, stds in [(bars1, means_on, stds_on), (bars2, means_off, stds_off)]:
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + std + 0.5,
                            f'{mean:.1f}', ha='center', va='bottom', fontsize=7)
else:
    axes[1, 1].text(0.5, 0.5, 'Insufficient data\nfor prefetch comparison',
                    ha='center', va='center', transform=axes[1, 1].transAxes, fontsize=10)
    axes[1, 1].set_title('Prefetch Effect (No Sparsification)', fontsize=10)

plt.tight_layout()
output_path = results_dir / 'experiment_summary.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'\nPlot saved to: {output_path}')
plt.show()
