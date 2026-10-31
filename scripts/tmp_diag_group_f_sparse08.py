"""
诊断脚本：Group F (TEE + Prefetch) quick，sparsity_rate=0.8
"""
import sys, os, yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CKKSFedPrefetchExperiment

with open('configs/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Group F: TEE + prefetch，使用 sparsity_rate=0.8
config['ckks']['sparsification'] = {
    'strategy': 'topk', 'sparsity_rate': 0.8, 'batch_size': 4096, 'seed': 42,
}
config['ckks']['ptopk'] = {
    'client_residual': {'enabled': True},
    'server_accumulator': {'enabled': False, 'mode': 'none'},
}
config['tee'] = {
    'enabled': True,
    'compression': {'enabled': True, 'sparsity_rate': 0.8},
}
config['prefetch'] = {'enable_prefetch': True}
config['system']['num_rounds'] = 5
config['system']['num_epochs'] = 2

import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, dir='.', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True)
    tmp_path = f.name

try:
    exp = CKKSFedPrefetchExperiment(tmp_path)
    results = exp.run_experiment_prefetch()
    accs = [r['test_acc'] for r in results['results']]
    print('ACC_TRAJECTORY:', accs)
    print('FINAL_ACC:', accs[-1] if accs else 0)
finally:
    os.unlink(tmp_path)
