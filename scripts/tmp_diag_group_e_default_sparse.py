"""
诊断脚本：Group E (non-TEE + Prefetch) quick，使用默认 sparsity_rate=0.8
"""
import sys, os, yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import CKKSFedPrefetchExperiment

with open('configs/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Group E: non-TEE + prefetch，使用默认配置（sparsity_rate=0.8）
config['tee'] = {'enabled': False}
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
