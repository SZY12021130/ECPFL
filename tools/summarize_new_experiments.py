# -*- coding: utf-8 -*-
"""Step1 数据汇总：扫描 ECPFL / ESAFL 新实验，输出论文 Table III / IV / VII / VIII 所需指标。"""
import json, glob, os, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r'E:\GithubProjects\ckks_fed_robustness\AAAAA_Rework'


def yml(path):
    import yaml
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def mb(x):
    return x / 2 ** 20 if x else 0.0


def esafl_summary(exp):
    mf = glob.glob(os.path.join(exp, 'metrics.json'))
    cf = glob.glob(os.path.join(exp, 'config.yaml'))
    if not mf:
        return None
    m = json.load(open(mf[0], encoding='utf-8'))
    cfg = yml(cf[0]) if cf else {}
    sysc, datac = cfg.get('system', {}), cfg.get('data', {})
    # 兼容两种 metrics 结构；逐轮列表字段求和，标量直取
    def g(k, default=0.0):
        if k in m:
            v = m[k]
        else:
            v = m.get('metrics_summary', {}).get(k, default)
        if isinstance(v, list):
            try:
                return sum(v)
            except TypeError:
                return default
        return v if v is not None else default
    acc_v = m.get('final_test_acc') or (m.get('metrics_summary', {}) or {}).get('final_test_acc')
    if acc_v is None:
        accs = m.get('test_acc') or m.get('round_test_acc') or []
        acc_v = accs[-1] if accs else None
    return dict(
        src=os.path.relpath(exp, BASE), ds=datac.get('dataset'), alpha=datac.get('alpha'),
        iid=datac.get('iid'), n=sysc.get('num_clients'), rounds=sysc.get('num_rounds'),
        acc=acc_v, tt=g('total_real_time') or g('total_round_real_time'),
        uv=mb(g('upload_cost')), dv=mb(g('download_cost')),
        ut=g('upload_time'), dt=g('download_time'),
        ct_up=g('num_ciphertexts'), ct_agg=g('aggregated_ciphertexts'),
    )


def ecpfl_summary(exp):
    jf = glob.glob(os.path.join(exp, '*.json'))
    cf = glob.glob(os.path.join(exp, 'config.yaml'))
    if not jf:
        return None
    d = json.load(open(jf[0], encoding='utf-8'))
    cfg = d.get('config', {})
    datac, ecp = cfg.get('data', {}), cfg.get('ecpfl', {})
    rounds = d.get('rounds', [])
    return dict(
        src=os.path.relpath(exp, BASE), ds=datac.get('dataset'), alpha=datac.get('alpha'),
        n=cfg.get('system', {}).get('num_clients'), rounds=cfg.get('system', {}).get('num_rounds'),
        rule=ecp.get('vote_rule'), thr=ecp.get('vote_threshold'), zeta=ecp.get('sparsity_rate'),
        abl=ecp.get('ablation', {}), pf=ecp.get('prefetch', {}).get('enabled'),
        acc=d.get('final_test_acc'), J=d.get('pack_count'), d_params=d.get('model_params'),
        uv=mb(sum(r.get('upload_bytes', 0) for r in rounds)),
        dl=mb(sum(r.get('download_bytes', 0) for r in rounds)),
        pv=mb(sum(r.get('prefetch_bytes', 0) for r in rounds)),
        tt=sum(r.get('round_time', 0) for r in rounds),
        enc=sum(r.get('enc_time', 0) for r in rounds),
        dec=sum(r.get('dec_time', 0) for r in rounds),
        vote=sum(r.get('vote_time', 0) for r in rounds),
        pf_t=sum(r.get('prefetch_time', 0) for r in rounds),
        ct_up=sum(len(r.get('active_set', [])) * d.get('pack_count', 0) for r in rounds),
    )


def main():
    print('================ ECPFL (json) ================')
    for sub in ['accuracy_diri1', 'accuracy', 'ablation', 'noniid']:
        for exp in sorted(glob.glob(os.path.join(BASE, 'ECPFL', 'result', sub, 'experiment_*'))):
            s = ecpfl_summary(exp)
            if s:
                print('%-46s ds=%-13s alpha=%-4s rule=%-2s thr=%-4s zeta=%-4s abl=%-60s acc=%-6.2f J=%-4s UV=%-8.1f DL=%-8.1f PV=%-8.1f TV=%-8.1f TT=%-8.1f enc=%-7.1f dec=%-5.1f vote=%-5.1f pfT=%-6.1f' % (
                    s['src'].split('result' + os.sep)[1], s['ds'], s['alpha'], s['rule'], s['thr'], s['zeta'],
                    json.dumps(s['abl']), s['acc'], s['J'], s['uv'], s['dl'], s['pv'], s['uv'] + s['pv'], s['tt'], s['enc'], s['dec'], s['vote'], s['pf_t']))
    print()
    print('================ ESAFL (metrics.json) ================')
    for sub in ['accuracy_diri1', 'accuracy', 'accuracy_n25_c1', 'accuracy_n8192', 'noniid']:
        for exp in sorted(glob.glob(os.path.join(BASE, 'ESAFL', 'result', sub, 'experiment_*'))):
            s = esafl_summary(exp)
            if s:
                print('%-46s ds=%-13s alpha=%-4s iid=%-5s N=%-3s rounds=%-3s acc=%-6s TT=%-9s UV=%-9.1f DV=%-9.1f UT=%-8s DT=%-8s' % (
                    s['src'].split('result' + os.sep)[1], s['ds'], s['alpha'], s['iid'], s['n'], s['rounds'],
                    s['acc'], s['tt'], s['uv'], s['dv'], s['ut'], s['dt']))
            else:
                # 尝试 report.md
                rm = glob.glob(os.path.join(exp, 'report.md'))
                cf = glob.glob(os.path.join(exp, 'config.yaml'))
                if rm and cf:
                    cfg = yml(cf[0])
                    txt = open(rm[0], encoding='utf-8', errors='replace').read()
                    acc = None
                    for line in txt.splitlines():
                        if 'Final Test Accuracy' in line and '**' in line:
                            acc = line.split('**')[1]
                            break
                    print('%-46s ds=%-13s alpha=%-4s (report.md acc=%s, metrics 字段不兼容)' % (
                        os.path.relpath(exp, BASE).split('result' + os.sep)[1],
                        cfg.get('data', {}).get('dataset'), cfg.get('data', {}).get('alpha'), acc))


if __name__ == '__main__':
    main()
