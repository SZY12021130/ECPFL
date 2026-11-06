# -*- coding: utf-8 -*-
"""
汇总 AAAAA_Rework/SAMK/result 下的所有 SAMK 实验结果（读取 samk_results.json）。

生成：
  result/summary.md                     所有运行的总览表
  result/dropout/dropout_summary.md     掉线率消融表
  result/dropout/dropout_summary.csv    同上（CSV，便于画图）

用法：
  python AAAAA_Rework/SAMK/summarize.py
"""

import glob
import json
import os
import statistics as st

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(ROOT, 'result')


def load_runs():
    runs = []
    for js in sorted(glob.glob(os.path.join(RESULT, '**', 'samk_results.json'),
                               recursive=True)):
        with open(js, 'r', encoding='utf-8') as f:
            runs.append((js, json.load(f)))
    return runs


def aggregate(d):
    rs = d['rounds']
    return dict(
        rounds=len(rs),
        online=st.mean(len(r['online']) for r in rs),
        up=st.mean(r['upload_bytes'] for r in rs) / 1e6,
        down=st.mean(r['download_bytes'] for r in rs) / 1e6,
        enc=st.mean(r['enc_time'] / max(1, len(r['online'])) for r in rs),
        agg=st.mean(r['agg_time'] for r in rs),
        dec=st.mean(r['dec_time'] for r in rs),
        rt=st.mean(r['round_time'] for r in rs),
        err=d['max_abs_err'],
        acc=d['final_test_acc'],
    )


def write_dropout(runs):
    sel = [(js, d) for js, d in runs if 'dropout' in js.replace('\\', '/')]
    if not sel:
        return
    sel.sort(key=lambda x: x[1]['config']['sampling']['dropout_rate'])
    md = ['# SAMK 掉线率消融（上传阶段掉线，固定集合 K=8，N=12，n=1024，d=1024）', '',
          '| dropout | 平均在线 | 上行/轮(MB) | 下行/轮(MB) | 加密/客户端(s) | 聚合(s) | '
          '解密(s) | 轮耗时(s) | 最大误差 | 重连可解 | 掉线者被拒 |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    csv = ['dropout_rate,avg_online,upload_mb_per_round,download_mb_per_round,'
           'enc_s_per_client,agg_s,dec_s,round_s,max_abs_err,late_fetch_ok,dropout_blocked']
    for _, d in sel:
        a = aggregate(d)
        r = d['config']['sampling']['dropout_rate']
        late = all(x['late_fetch_ok'] in (True, None) for x in d['rounds'])
        blk = all(x['preupload_dropout_blocked'] in (True, None) for x in d['rounds'])
        md.append(f"| {r:.1f} | {a['online']:.2f} | {a['up']:.3f} | {a['down']:.3f} | "
                  f"{a['enc']:.2f} | {a['agg']:.2f} | {a['dec']:.2f} | {a['rt']:.2f} | "
                  f"{a['err']:.2e} | {late} | {blk} |")
        csv.append(f"{r:.1f},{a['online']:.2f},{a['up']:.4f},{a['down']:.4f},"
                   f"{a['enc']:.3f},{a['agg']:.3f},{a['dec']:.3f},{a['rt']:.2f},"
                   f"{a['err']:.3e},{late},{blk}")
    out = os.path.join(RESULT, 'dropout')
    with open(os.path.join(out, 'dropout_summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    with open(os.path.join(out, 'dropout_summary.csv'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(csv) + '\n')


def write_summary(runs):
    md = ['# SAMK（TDSC 2025）复现实验结果总览', '',
          '密码学实现：**纯 Python + NumPy 自研**（BFV 复用项目 '
          '`ckks_fed/eshe.py:RingContext` 的双素数 CRT+negacyclic NTT；'
          'Paillier 为纯 Python 大整数实现；未使用 phe / tenseal / Pyfhel / sympy）。', '',
          '| 实验 | 模式 | 轮数 | 平均在线 | 上行/轮(MB) | 下行/轮(MB) | '
          '加密/客户端(s) | 聚合(s) | 解密(s) | 最大误差 | 最终精度 |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for js, d in runs:
        a = aggregate(d)
        name = os.path.basename(os.path.dirname(js))
        acc = f"{a['acc']:.2f}%" if a['acc'] is not None and a['acc'] == a['acc'] else '—'
        md.append(f"| {name} | {d['mode']} | {a['rounds']} | {a['online']:.2f} | "
                  f"{a['up']:.3f} | {a['down']:.3f} | {a['enc']:.2f} | {a['agg']:.2f} | "
                  f"{a['dec']:.2f} | {a['err']:.2e} | {acc} |")
    with open(os.path.join(RESULT, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')


def main():
    runs = load_runs()
    if not runs:
        raise SystemExit('未找到 samk_results.json，请先运行 main_samk.py')
    write_dropout(runs)
    write_summary(runs)
    print(f'汇总完成：{len(runs)} 个运行 -> result/summary.md, '
          f'result/dropout/dropout_summary.md|csv')


if __name__ == '__main__':
    main()
