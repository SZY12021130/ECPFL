"""
stale_gamma / decay_gamma 在不同客户端选择策略下的验证实验
============================================================

实验矩阵（3 策略 × 4 种 gamma 组合 = 12 组）：
  策略: random | sketch_clustering | sticky
  gamma 组合:
    A) (1.0, 1.0) - 完全关闭（基准，残差不衰减）
    B) (0.5, 1.0) - 仅 stale_gamma（强跨轮衰减）
    C) (1.0, 0.5) - 仅 decay_gamma（强自然衰减）
    D) (0.9, 0.5) - 两者都开（默认配置）

预期验证点:
  1. sketch_clustering: 5 个客户端完全不被选中（gap 最大），stale_gamma 应显著影响
     其残差衰减，防止过时残差在偶尔参与时引发震荡。
  2. sticky: 边缘客户端 gap 中等，decay_gamma 应能抑制其长期未选中 batch 的残差膨胀。
  3. random: 所有客户端均匀参与，gap 较小，gamma 影响应最弱（作为对照）。
"""

import os
import sys
import yaml
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CKKSFedPrefetchExperiment, _get_or_create_bandwidth_simulator


def create_config(strategy: str, stale_gamma: float, decay_gamma: float) -> str:
    """生成实验配置。"""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'config.yaml')
    with open(base_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    # MNIST 轻量配置
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

    # CKKS
    cfg['ckks']['poly_modulus_degree'] = 4096
    cfg['ckks']['coeff_mod_bit_sizes'] = [40, 20, 40]
    cfg['ckks']['global_scale'] = 1048576
    cfg['ckks']['slot_packing'] = True
    cfg['ckks']['packing']['strategy'] = 'layerwise'

    # ★ 稀疏化: TopK 0.1
    cfg['ckks']['sparsification']['strategy'] = 'topk'
    cfg['ckks']['sparsification']['sparsity_rate'] = 0.1

    # ★ PTopk 开启 + gamma 配置（ptopk 在 ckks 段下）
    cfg['ckks']['ptopk']['enable'] = True
    cfg['ckks']['ptopk']['client_residual']['enabled'] = True
    cfg['ckks']['ptopk']['client_residual']['stale_gamma'] = stale_gamma
    cfg['ckks']['ptopk']['client_residual']['decay_gamma'] = decay_gamma
    cfg['ckks']['ptopk']['client_residual']['clip_tau'] = 0.0
    cfg['ckks']['ptopk']['server_accumulator']['enabled'] = False

    # 关闭其他变量
    cfg['blinding_mask']['enabled'] = False
    cfg['tee']['enabled'] = False

    # 预取
    cfg['prefetch']['enable_prefetch'] = True
    cfg['prefetch']['use_sticky_sampling'] = True
    cfg['prefetch']['overcommitment'] = 2.0
    cfg['prefetch']['max_prefetch_round'] = 3
    cfg['prefetch']['warmup_round'] = 1

    # 客户端选择策略
    cfg['client_selection']['strategy'] = strategy
    cfg['client_selection']['sim_len'] = 64
    cfg['client_selection']['quan_threshold'] = 0.05
    cfg['client_selection']['selection_interval'] = 10
    cfg['client_selection']['fairness']['enabled'] = False

    tmp_dir = os.path.join(os.path.dirname(__file__), '..', 'tmp_configs')
    os.makedirs(tmp_dir, exist_ok=True)
    tag = f"{strategy}_stale{stale_gamma}_decay{decay_gamma}"
    tmp_path = os.path.join(tmp_dir, f'config_gamma_{tag}.yaml')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    return tmp_path


def run_single(config_path: str, label: str):
    """运行单组实验。"""
    print(f"\n{'='*70}")
    print(f"[RUN] {label}")
    print(f"Config: {config_path}")
    print('='*70)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    bw_sim = _get_or_create_bandwidth_simulator(cfg)

    start = time.time()
    experiment = CKKSFedPrefetchExperiment(config_path, bandwidth_simulator=bw_sim)
    results = experiment.run_experiment_prefetch()
    elapsed = time.time() - start

    pf_results = results.get('results', [])
    accs = [r['test_acc'] for r in pf_results if 'test_acc' in r]
    losses = [r['test_loss'] for r in pf_results if 'test_loss' in r]

    summary = {
        'label': label,
        'elapsed': elapsed,
        'final_acc': accs[-1] if accs else 0.0,
        'final_loss': losses[-1] if losses else 0.0,
        'max_acc': max(accs) if accs else 0.0,
        'round_accuracies': accs,
        'round_losses': losses,
    }

    print(f"\n[{label}] Done | {elapsed:.1f}s | FinalAcc={summary['final_acc']:.2f}%")
    return summary


def main():
    strategies = ['random', 'sketch_clustering', 'sticky']
    gamma_combos = [
        (1.0, 1.0, "OFF"),
        (0.5, 1.0, "stale_only"),
        (1.0, 0.5, "decay_only"),
        (0.9, 0.5, "both"),
    ]

    all_results = []
    total_start = time.time()

    for strategy in strategies:
        for stale_g, decay_g, tag in gamma_combos:
            label = f"{strategy}-{tag}"
            config_path = create_config(strategy, stale_g, decay_g)
            summary = run_single(config_path, label)
            summary['strategy'] = strategy
            summary['stale_gamma'] = stale_g
            summary['decay_gamma'] = decay_g
            summary['tag'] = tag
            all_results.append(summary)

    total_elapsed = time.time() - total_start

    # =====================================================================
    # 汇总输出
    # =====================================================================
    print("\n\n" + "="*90)
    print(f"汇总结果 | TotalTime={total_elapsed/60:.1f}min")
    print("="*90)

    # 按策略分组打印
    for strategy in strategies:
        print(f"\n{'─'*90}")
        print(f"策略: {strategy}")
        print(f"{'Tag':<12} {'FinalAcc':>10} {'MaxAcc':>10} {'R1':>8} {'R2':>8} {'R3':>8} {'R5':>8} {'R10':>8} | Time")
        print("─"*90)
        for r in all_results:
            if r['strategy'] != strategy:
                continue
            accs = r['round_accuracies']
            r1 = accs[0] if len(accs) > 0 else 0
            r2 = accs[1] if len(accs) > 1 else 0
            r3 = accs[2] if len(accs) > 2 else 0
            r5 = accs[4] if len(accs) > 4 else 0
            r10 = accs[-1] if len(accs) > 0 else 0
            print(f"{r['tag']:<12} {r['final_acc']:>10.2f} {r['max_acc']:>10.2f} "
                  f"{r1:>8.2f} {r2:>8.2f} {r3:>8.2f} {r5:>8.2f} {r10:>8.2f} | {r['elapsed']:>5.0f}s")

    # 关键对比: gamma OFF vs gamma both（每策略）
    print(f"\n{'='*90}")
    print("关键对比: OFF vs both (验证 gamma 是否有净收益)")
    print(f"{'Strategy':<18} {'OFF_fin':>10} {'both_fin':>10} {'Δ':>8} {'OFF_max':>10} {'both_max':>10}")
    print("─"*90)
    for strategy in strategies:
        off = next(r for r in all_results if r['strategy'] == strategy and r['tag'] == 'OFF')
        both = next(r for r in all_results if r['strategy'] == strategy and r['tag'] == 'both')
        print(f"{strategy:<18} {off['final_acc']:>10.2f} {both['final_acc']:>10.2f} "
              f"{both['final_acc']-off['final_acc']:>+8.2f} {off['max_acc']:>10.2f} {both['max_acc']:>10.2f}")

    # 保存 JSON
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'gamma_strategy_comparison.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n详细结果已保存: {out_path}")
    print("="*90)


if __name__ == '__main__':
    main()
