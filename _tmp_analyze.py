import os, json, yaml

exps = [
    'experiment_20260510_142703', 'experiment_20260510_143013', 'experiment_20260510_143338',
    'experiment_20260510_143626', 'experiment_20260510_143951', 'experiment_20260510_144252',
    'experiment_20260510_144606', 'experiment_20260510_144904', 'experiment_20260510_145145',
    'experiment_20260510_145451', 'experiment_20260510_145810', 'experiment_20260510_150032',
    'experiment_20260510_150505'
]

print('ExpID                     mode     tau     win   gamma final_acc max_acc  total_time comm_time')
print('='*105)

for exp in exps:
    d = os.path.join('results', exp)
    cfg_path = os.path.join(d, 'config.yaml')
    met_path = os.path.join(d, 'metrics.json')
    if not os.path.exists(cfg_path):
        continue
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
    except:
        continue
    rs = cfg.get('tee', {}).get('residual_strategy', {})
    mode = rs.get('mode', 'N/A')
    tau = rs.get('clip_tau', 'N/A')
    win = rs.get('clip_window', 'N/A')
    gamma = rs.get('decay_gamma', 'N/A')
    fa, ma, tt, ct = 'N/A', 'N/A', 'N/A', 'N/A'
    if os.path.exists(met_path):
        try:
            with open(met_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            accs = m.get('test_acc', [])
            if accs:
                fa = f"{accs[-1]:.2f}%"
                ma = f"{max(accs):.2f}%"
            times = m.get('total_round_time', [])
            if times:
                tt = f"{sum(times):.1f}s"
            comms = m.get('total_communication_cost', [])
            if comms:
                ct = f"{sum(comms):.1f}"
        except:
            pass
    print(f"{exp:<25} {mode:<8} {str(tau):<6} {str(win):<5} {str(gamma):<5} {fa:<9} {ma:<8} {tt:<11} {ct}")
