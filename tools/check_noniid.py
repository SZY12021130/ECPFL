# -*- coding: utf-8 -*-
"""核查 non-IID α 扫描实验完成度与 TV=UV+FV 口径。"""
import json, glob, os, sys, io
import yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r'E:\GithubProjects\ckks_fed_robustness\AAAAA_Rework'

print('===== ECPFL noniid (alpha sweep) =====')
for exp in sorted(glob.glob(BASE + r'\ECPFL\result\noniid\experiment_*')):
    d = json.load(open(glob.glob(exp + r'\*.json')[0], encoding='utf-8'))
    cfg = d['config']
    rounds = d['rounds']
    dl = sum(r['download_bytes'] for r in rounds) / 1e6
    pv = sum(r['prefetch_bytes'] for r in rounds) / 1e6
    hits = sum(r['cache_hits'] for r in rounds)
    dev = cfg['system'].get('device')
    print('%s | alpha=%-4s ds=%-12s rounds=%d acc=%6.2f | UV=%8.1f FV(syncDL)=%8.1f PV=%8.1f hits=%d | TT_sim=%s | dev=%s' % (
        os.path.basename(exp)[11:], cfg['data']['alpha'], cfg['data']['dataset'], len(rounds),
        d['final_test_acc'], d['total_upload_mb'], dl, pv, hits,
        ('%.1f' % d['total_tt_sim']) if 'total_tt_sim' in d else 'N/A(旧代码)', dev))

print()
print('===== ESAFL noniid (alpha sweep) =====')
for exp in sorted(glob.glob(BASE + r'\ESAFL\result\noniid\experiment_*')):
    m = json.load(open(glob.glob(exp + r'\metrics.json')[0], encoding='utf-8'))
    cfg = yaml.safe_load(open(glob.glob(exp + r'\config.yaml')[0], encoding='utf-8'))
    uv = sum(m['upload_cost']) / 1e6
    dv = sum(m['download_cost']) / 1e6
    tt = sum(m['total_round_time_simulated'])
    dev = cfg.get('system', {}).get('device')
    print('%s | alpha=%-4s ds=%-12s rounds=%d acc=%6.2f | UV=%8.1f FV=%8.1f TV=%8.1f | TT_sim=%7.1f | dev=%s' % (
        os.path.basename(exp)[11:], cfg['data']['alpha'], cfg['data']['dataset'],
        len(m['test_acc']), m['test_acc'][-1], uv, dv, uv + dv, tt, dev))
