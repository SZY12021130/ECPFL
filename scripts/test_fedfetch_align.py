import os, sys, time, yaml
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from main import CKKSFedPrefetchExperiment

def create_config():
    base_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'config.yaml')
    with open(base_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    cfg['system']['num_clients'] = 10
    cfg['system']['num_rounds'] = 3
    cfg['system']['num_epochs'] = 2
    cfg['system']['batch_size'] = 64
    cfg['system']['client_sampling_rate'] = 0.5
    cfg['system']['device'] = 'cpu'
    cfg['system']['random_seed'] = 42
    cfg['system']['run_plaintext_baseline'] = False
    cfg['data']['dataset'] = 'mnist'
    cfg['data']['iid'] = False
    cfg['data']['alpha'] = 1.0
    cfg['model']['name'] = 'lenet'
    cfg['ckks']['poly_modulus_degree'] = 8192
    cfg['ckks']['coeff_mod_bit_sizes'] = [60, 40, 40, 60]
    cfg['ckks']['global_scale'] = 1099511627776
    cfg['ckks']['sparsification']['strategy'] = 'topk'
    cfg['ckks']['sparsification']['sparsity_rate'] = 0.1
    cfg['ckks']['ptopk']['enable'] = True
    cfg['ckks']['ptopk']['client_residual']['enabled'] = True
    cfg['ckks']['ptopk']['client_residual']['stale_gamma'] = 1.0
    cfg['ckks']['ptopk']['client_residual']['decay_gamma'] = 0.5
    cfg['prefetch']['enable_prefetch'] = True
    cfg['prefetch']['use_sticky_sampling'] = True
    cfg['prefetch']['overcommitment'] = 2.0
    cfg['client_selection']['strategy'] = 'sketch_clustering'
    cfg['client_selection']['sim_len'] = 64
    cfg['client_selection']['quan_threshold'] = 0.05
    cfg['client_selection']['selection_interval'] = 5
    out = os.path.join(os.path.dirname(__file__), '..', 'configs', 'test_fedfetch_align.yaml')
    with open(out, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True)
    return out

def main():
    print("=== FedFetch Align Test ===")
    print("strategy: sketch_clustering | interval=5 | 3 rounds")
    print()
    config_path = create_config()
    exp = CKKSFedPrefetchExperiment(config_path)
    results = exp.run_experiment_prefetch()
    pf = results.get('results', [])
    accs = [r['test_acc'] for r in pf if 'test_acc' in r]
    print()
    print(f"Final acc: {accs[-1]:.2f}%" if accs else "No results")
    print()
    print("Checking presample pool consistency...")
    pool = exp.pool_manager.presample_pool if hasattr(exp, 'pool_manager') else None
    if pool:
        for tr, ids in sorted(pool.items()):
            print(f"  target_round={tr}: presampled={ids}")
    else:
        print("  No pool")
    print()
    print("PASS" if (accs and accs[-1] > 80) else "CHECK NEEDED")

if __name__ == '__main__':
    main()
