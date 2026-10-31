import json, yaml, os
from pathlib import Path
from collections import defaultdict

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
        
        exp_info = {
            'name': exp_dir.name,
            'num_rounds': system.get('num_rounds', 0),
            'num_clients': system.get('num_clients', 0),
            'client_sampling_rate': system.get('client_sampling_rate', 0),
            'upload_difference': system.get('upload_difference', True),
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
            'ptopk_sync_interval': ptopk.get('sync_interval', 1),
            'test_acc_last': metrics.get('test_acc', [0])[-1] if metrics.get('test_acc') else 0,
            'test_acc_max': max(metrics.get('test_acc', [0])) if metrics.get('test_acc') else 0,
            'test_acc_avg': sum(metrics.get('test_acc', [0]))/len(metrics.get('test_acc', [1])) if metrics.get('test_acc') else 0,
            'total_round_time': sum(metrics.get('total_round_time', [0])) if metrics.get('total_round_time') else 0,
            'total_comm_cost_mb': sum(metrics.get('total_communication_cost', [0])) / (1024*1024) if metrics.get('total_communication_cost') else 0,
        }
        experiments.append(exp_info)
    except Exception as e:
        print(f'Skip {exp_dir.name}: {e}')

print(f'Total valid experiments: {len(experiments)}')
print()

# 按关键配置分组
groups = defaultdict(list)
for e in experiments:
    key = (e['dataset'], e['model'], e['poly_modulus_degree'], e['coeff_mod_bit_sizes'], 
           e['global_scale'], e['packing_strategy'], e['sparsification_strategy'], 
           e['sparsity_rate'], e['enable_prefetch'], e['use_sticky_sampling'],
           e['ptopk_enable'], e['ptopk_server_mode'], e['num_rounds'], e['num_clients'])
    groups[key].append(e)

print('=== Experiment Groups ===')
for i, (key, exps) in enumerate(groups.items()):
    ds, model, poly, coeff, scale, pack, sparse, sr, prefetch, sticky, ptopk_en, ptopk_mode, nr, nc = key
    print(f'\nGroup {i+1}: {len(exps)} runs')
    print(f'  Dataset={ds}, Model={model}, N={poly}, coeff={coeff}, scale={scale}')
    print(f'  Packing={pack}, Sparse={sparse}({sr}), Prefetch={prefetch}, Sticky={sticky}')
    print(f'  PTopk={ptopk_en}({ptopk_mode}), Rounds={nr}, Clients={nc}')
    for e in exps:
        print(f'    {e["name"]}: last_acc={e["test_acc_last"]:.2f}, max_acc={e["test_acc_max"]:.2f}')
