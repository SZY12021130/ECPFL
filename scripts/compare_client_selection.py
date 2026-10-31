"""
客户端选择策略对比实验脚本
================================
对比 random vs sketch_clustering 在 MNIST 上的 10 轮表现。
保持其他所有参数一致，仅切换策略。
"""

import os
import sys
import yaml
import json
import shutil
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CKKSFedPrefetchExperiment, _get_or_create_bandwidth_simulator


def create_mnist_config(strategy: str) -> str:
    """创建 MNIST 对比实验的临时配置文件。"""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'config.yaml')
    with open(base_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    # MNIST 最佳配置
    cfg['system']['num_clients'] = 10
    cfg['system']['num_rounds'] = 10
    cfg['system']['num_epochs'] = 3
    cfg['system']['batch_size'] = 64
    cfg['system']['client_sampling_rate'] = 0.5
    cfg['system']['device'] = 'cpu'
    cfg['system']['random_seed'] = 42
    cfg['system']['run_plaintext_baseline'] = False

    cfg['data']['dataset'] = 'mnist'
    cfg['data']['iid'] = False
    cfg['data']['alpha'] = 1.0
    cfg['data']['num_classes'] = 10

    cfg['model']['name'] = 'lenet'

    cfg['system']['optimizer']['name'] = 'adam'
    cfg['system']['optimizer']['lr'] = 0.001

    # CKKS 轻量快速配置
    cfg['ckks']['poly_modulus_degree'] = 4096
    cfg['ckks']['coeff_mod_bit_sizes'] = [40, 20, 40]
    cfg['ckks']['global_scale'] = 1048576
    cfg['ckks']['slot_packing'] = True
    cfg['ckks']['packing']['strategy'] = 'layerwise'

    # 关闭所有额外变量，纯对比策略
    cfg['ckks']['sparsification']['strategy'] = 'none'
    cfg['ckks']['ptopk']['enable'] = False
    cfg['blinding_mask']['enabled'] = False
    cfg['tee']['enabled'] = False

    # 预取开启（策略无关的公共配置）
    cfg['prefetch']['enable_prefetch'] = True
    cfg['prefetch']['use_sticky_sampling'] = True
    cfg['prefetch']['overcommitment'] = 2.0
    cfg['prefetch']['max_prefetch_round'] = 3
    cfg['prefetch']['warmup_round'] = 1

    # 客户端选择策略（唯一变量）
    cfg['client_selection']['strategy'] = strategy
    cfg['client_selection']['sim_len'] = 64
    cfg['client_selection']['quan_threshold'] = 0.05
    cfg['client_selection']['selection_interval'] = 10
    cfg['client_selection']['fairness']['enabled'] = False

    # 保存临时配置
    tmp_dir = os.path.join(os.path.dirname(__file__), '..', 'tmp_configs')
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f'config_mnist_{strategy}.yaml')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)

    return tmp_path


def run_experiment(config_path: str, strategy: str):
    """运行单个实验。"""
    print(f"\n{'='*60}")
    print(f"Strategy: {strategy}")
    print(f"Config: {config_path}")
    print('='*60)

    # 加载配置以获取带宽模拟器
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    bw_sim = _get_or_create_bandwidth_simulator(cfg)

    start = time.time()
    experiment = CKKSFedPrefetchExperiment(config_path, bandwidth_simulator=bw_sim)
    results = experiment.run_experiment_prefetch()
    elapsed = time.time() - start

    # 提取关键指标
    pf_results = results.get('results', [])
    metrics = results.get('metrics', {})

    accs = [r['test_acc'] for r in pf_results if 'test_acc' in r]
    losses = [r['test_loss'] for r in pf_results if 'test_loss' in r]
    rounds = [r['round'] for r in pf_results if 'round' in r]

    round_times = metrics.get('total_round_time', [])
    prefetch_costs = metrics.get('prefetch_download_cost', [])
    fetch_costs = metrics.get('fetch_download_cost', [])

    result_summary = {
        'strategy': strategy,
        'elapsed_seconds': elapsed,
        'output_dir': experiment.output_dir,
        'final_acc': accs[-1] if accs else 0.0,
        'final_loss': losses[-1] if losses else 0.0,
        'max_acc': max(accs) if accs else 0.0,
        'round_accuracies': accs,
        'round_losses': losses,
        'avg_round_time': sum(round_times) / max(1, len(round_times)),
        'total_prefetch_cost': sum(prefetch_costs),
        'total_fetch_cost': sum(fetch_costs),
    }

    print(f"\n[{strategy}] 实验完成 | 耗时: {elapsed:.1f}s")
    print(f"  最终准确率: {result_summary['final_acc']:.2f}%")
    print(f"  最高准确率: {result_summary['max_acc']:.2f}%")
    print(f"  平均轮耗时: {result_summary['avg_round_time']:.2f}s")
    print(f"  总预取通信: {result_summary['total_prefetch_cost'] / 1024 / 1024:.2f} MB")
    print(f"  总Fetch通信: {result_summary['total_fetch_cost'] / 1024 / 1024:.2f} MB")
    print(f"  结果目录: {experiment.output_dir}")

    return result_summary


def main():
    strategies = ['random', 'sketch_clustering', 'sticky']
    summaries = []

    for strategy in strategies:
        config_path = create_mnist_config(strategy)
        summary = run_experiment(config_path, strategy)
        summaries.append(summary)

    # 打印对比表
    print("\n" + "="*80)
    print("对比结果汇总")
    print("="*80)
    print(f"{'指标':<25} {'random':>15} {'sketch_clustering':>20} {'sticky':>15}")
    print("-"*80)

    keys = [
        ('最终准确率 (%)', 'final_acc', '{:.2f}'),
        ('最高准确率 (%)', 'max_acc', '{:.2f}'),
        ('总耗时 (s)', 'elapsed_seconds', '{:.1f}'),
        ('平均轮耗时 (s)', 'avg_round_time', '{:.2f}'),
        ('总预取通信 (MB)', 'total_prefetch_cost', '{:.2f}'),
        ('总Fetch通信 (MB)', 'total_fetch_cost', '{:.2f}'),
    ]

    for label, key, fmt in keys:
        values = []
        for s in summaries:
            v = s[key]
            if 'cost' in key:
                v = v / 1024 / 1024
            values.append(v)
        line = f"{label:<25}"
        for v in values:
            line += f" {fmt.format(v):>15}"
        # 对齐扩展列
        if len(values) == 2:
            line += f" {'--':>15}"
        print(line)

    # 打印逐轮准确率曲线
    print("\n逐轮准确率对比:")
    headers = ['Round'] + [s['strategy'][:10] for s in summaries]
    print(f"{headers[0]:>6} {headers[1]:>10} {headers[2]:>10} {headers[3]:>10}")
    print("-"*40)
    accs = [s['round_accuracies'] for s in summaries]
    for i in range(len(accs[0])):
        line = f"{i+1:>6}"
        for acc in accs:
            line += f" {acc[i]:>10.2f}"
        print(line)

    print("\n" + "="*70)


if __name__ == '__main__':
    main()
