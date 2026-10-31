import os, re
base = r'E:\GithubProjects\ckks_fed_robustness\accuracy_baseline\esafl\test'
items = [d for d in os.listdir(base) if d.startswith('experiment_') and '_q' not in d and 'cifar10' in d]
items.sort()
item = items[-1]
log = os.path.join(base, item, 'experiment.log')
out = []
with open(log, 'r', encoding='utf-8', errors='ignore') as f:
    for l in f:
        if 'SERVER' in l or 'aggregate' in l.lower() or 'packing' in l.lower() or 'update' in l.lower() or 'eval' in l.lower() or '测试' in l:
            out.append(l.strip())
with open(r'E:\GithubProjects\ckks_fed_robustness\_tmp_server_log.txt', 'w', encoding='utf-8') as f:
    for o in out:
        f.write(o + '\n')
print(f'Wrote {len(out)} lines')
