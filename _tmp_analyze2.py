import os, json, yaml

exps = [
    'experiment_20260510_142703', 'experiment_20260510_143013', 'experiment_20260510_143338',
    'experiment_20260510_143626', 'experiment_20260510_143951', 'experiment_20260510_144252',
    'experiment_20260510_144606', 'experiment_20260510_144904', 'experiment_20260510_145145',
    'experiment_20260510_145451', 'experiment_20260510_145810', 'experiment_20260510_150032',
    'experiment_20260510_150505'
]

for exp in exps:
    d = os.path.join('results', exp)
    cfg_path = os.path.join(d, 'config.yaml')
    met_path = os.path.join(d, 'metrics.json')
    log_path = os.path.join(d, 'experiment.log')
    if not os.path.exists(cfg_path):
        continue
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    
    sys = cfg.get('system', {})
    ckks = cfg.get('ckks', {})
    tee = cfg.get('tee', {})
    rs = tee.get('residual_strategy', {})
    
    print(f"\n{'='*80}")
    print(f"Exp: {exp}")
    print(f"  num_clients={sys.get('num_clients')}, num_rounds={sys.get('num_rounds')}, num_epochs={sys.get('num_epochs')}")
    print(f"  client_sampling={sys.get('client_sampling_rate')}, lr={sys.get('learning_rate')}")
    print(f"  client_sparsity={ckks.get('sparsification',{}).get('sparsity_rate')}")
    print(f"  tee_compression={tee.get('compression',{}).get('enabled')}, tee_sparsity={tee.get('compression',{}).get('sparsity_rate')}")
    print(f"  residual_mode={rs.get('mode')}, decay_gamma={rs.get('decay_gamma')}, clip_tau={rs.get('clip_tau')}, clip_window={rs.get('clip_window')}")
    print(f"  optimizer={sys.get('optimizer',{}).get('name','sgd')}, scheduler_enabled={sys.get('lr_scheduler',{}).get('enabled',False)}")
    
    if os.path.exists(met_path):
        with open(met_path, 'r', encoding='utf-8') as f:
            m = json.load(f)
        accs = m.get('test_acc', [])
        losses = m.get('test_loss', [])
        times = m.get('total_round_time', [])
        if accs:
            print(f"  Accuracy curve: {' -> '.join([f'{a:.1f}' for a in accs])}")
            print(f"  Final: acc={accs[-1]:.2f}%, loss={losses[-1]:.4f}, max={max(accs):.2f}%")
        if times:
            print(f"  Total time: {sum(times):.1f}s, avg/round: {sum(times)/len(times):.1f}s")
    
    # Read residual_norm from log
    if os.path.exists(log_path):
        res_norms = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'residual_norm=' in line:
                    try:
                        val = float(line.split('residual_norm=')[1].strip().split()[0])
                        res_norms.append(val)
                    except:
                        pass
        if res_norms:
            print(f"  Residual norms: min={min(res_norms):.4f}, max={max(res_norms):.4f}, final={res_norms[-1]:.4f}")
