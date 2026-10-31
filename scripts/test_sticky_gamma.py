"""只验证 sticky 策略下 stale_gamma 的效果（decay_gamma=0.5 保证收敛）。"""
import os, sys, time, json, yaml, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import PrefetchExperiment

def create_config(stale_gamma: float, decay_gamma: float, tag: str) -> str:
    base_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'config.yaml')
    with open(base_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

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

    cfg['ckks']['poly_modulus_degree'] = 4096
    cfg['ckks']['coeff_mod_bit_sizes'] = [40, 20, 40]
    cfg['ckks']['global_scale'] = 1048576
    cfg['ckks']['slot_packing'] = True
    cfg['ckks']['packing']['strategy'] = 'layerwise'

    cfg['ckks']['sparsification']['strategy'] = 'topk'
    cfg['ckks']['sparsification']['sparsity_rate'] = 0.1

    cfg['ckks']['ptopk']['enable'] = True
    cfg['ckks']['ptopk']['client_residual']['enabled'] = True
    cfg['ckks']['ptopk']['client_residual']['stale_gamma'] = stale_gamma
    cfg['ckks']['ptopk']['client_residual']['decay_gamma'] = decay_gamma
    cfg['ckks']['ptopk']['client_residual']['clip_tau'] = 0.0
    cfg['ckks']['ptopk']['server_accumulator']['enabled'] = False

    cfg['blinding_mask']['enabled'] = False
    cfg['tee']['enabled'] = False

    cfg['prefetch']['enable_prefetch'] = True
    cfg['prefetch']['use_sticky_sampling'] = True

    cfg['client_selection']['strategy'] = 'sticky'
    cfg['client_selection']['sticky']['enabled'] = True
    cfg['client_selection']['sticky']['decay'] = 0.9
    cfg['client_selection']['sticky']['group_size'] = 8
    cfg['client_selection']['sticky']['change_num'] = 1

    out_name = f"sticky_{tag}_s{stale_gamma}_d{decay_gamma}.yaml"
    out_path = os.path.join(os.path.dirname(__file__), '..', 'configs', out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)
    return out_path

def run_single(config_path: str, label: str):
    print(f"\n{'='*70}")
    print(f"▶ {label}")
    print(f"{'='*70}")
    start = time.time()
    exp = PrefetchExperiment(config_path)
    results = exp.run_experiment_prefetch()
    pf_results = results.get('results', [])
    accs = [r['test_acc'] for r in pf_results if 'test_acc' in r]
    losses = [r['test_loss'] for r in pf_results if 'test_loss' in r]
    elapsed = time.time() - start

    summary = {
        'label': label,
        'config': config_path,
        'final_acc': accs[-1] if accs else None,
        'max_acc': max(accs) if accs else None,
        'final_loss': losses[-1] if losses else None,
        'avg_round_time': elapsed / len(pf_results) if pf_results else 0,
        'total_time': elapsed,
    }
    print(f"\n✓ {label} | final={summary['final_acc']:.2f}% | max={summary['max_acc']:.2f}% | time={elapsed:.0f}s")
    return summary

def main():
    combos = [
        (1.0, 0.5, "decay_only"),   # 无陈旧衰减，只有每轮衰减
        (0.9, 0.5, "both"),          # 有陈旧衰减 + 每轮衰减
    ]
    all_results = []
    for stale_g, decay_g, tag in combos:
        label = f"sticky-{tag}(stale={stale_g},decay={decay_g})"
        config_path = create_config(stale_g, decay_g, tag)
        summary = run_single(config_path, label)
        summary['stale_gamma'] = stale_g
        summary['decay_gamma'] = decay_g
        summary['tag'] = tag
        all_results.append(summary)

    # 对比输出
    print("\n" + "="*70)
    print("stale_gamma 验证对比（sticky 策略，decay_gamma=0.5 固定）")
    print("="*70)
    for r in all_results:
        print(f"  {r['tag']:12s} | stale={r['stale_gamma']} | final={r['final_acc']:.2f}% | max={r['max_acc']:.2f}%")

    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'sticky_stale_gamma_comparison.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {out_path}")

if __name__ == '__main__':
    main()
