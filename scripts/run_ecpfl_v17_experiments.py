# -*- coding: utf-8 -*-
"""
ECPFL (V17) 论文全套实验批量运行脚本
====================================

遍历 configs/ecpfl_v17/ 配置树，顺序执行
  python main_ecpfl.py --config <cfg> --output-dir results/ecpfl_v17/<相对路径>
每个实验独立 log（results/ecpfl_v17/logs/<相对路径>.log），失败继续下一个，
全部结束后汇总 results/ecpfl_v17/summary.csv（dataset/variant/acc/TV/PV/TT）。

用法：
  python scripts/run_ecpfl_v17_experiments.py                 # 全部
  python scripts/run_ecpfl_v17_experiments.py --only table3   # 只跑某子树（可逗号分隔）
  python scripts/run_ecpfl_v17_experiments.py --dry-run       # 只打印将执行的命令
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_TREE = ROOT / 'configs' / 'ecpfl_v17'
RESULTS_DIR = ROOT / 'results' / 'ecpfl_v17'
LOGS_DIR = RESULTS_DIR / 'logs'
SUMMARY_CSV = RESULTS_DIR / 'summary.csv'


def collect_configs(only: str = None):
    """返回 [(相对路径不含扩展名, config 路径)]，按相对路径排序。"""
    cfgs = sorted(CONFIG_TREE.rglob('*.yaml'))
    if only:
        groups = [g.strip() for g in only.split(',') if g.strip()]
        cfgs = [c for c in cfgs if any(
            c.relative_to(CONFIG_TREE).parts[0] == g or
            str(c.relative_to(CONFIG_TREE).with_suffix('')) == g
            for g in groups)]
    return [(str(c.relative_to(CONFIG_TREE).with_suffix('')), c) for c in cfgs]


def run_one(rel: str, cfg: Path, dry_run: bool) -> dict:
    out_dir = RESULTS_DIR / rel
    log_file = LOGS_DIR / f'{rel}.log'
    cmd = [sys.executable, str(ROOT / 'main_ecpfl.py'),
           '--config', str(cfg), '--output-dir', str(out_dir)]
    row = {'config': rel, 'status': 'dry-run' if dry_run else 'pending',
           'acc': '', 'TV_MB': '', 'PV_MB': '', 'TT_s': ''}
    print(f'[RUN] {rel}\n      -> {" ".join(cmd)}', flush=True)
    if dry_run:
        return row
    log_file.parent.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log_file, 'w', encoding='utf-8') as lf:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT)
    tt = time.time() - t0
    if proc.returncode != 0:
        row['status'] = f'FAILED(exit={proc.returncode})'
        print(f'[FAIL] {rel} (exit={proc.returncode})，日志：{log_file}', flush=True)
        return row
    row['status'] = 'ok'
    row['TT_s'] = f'{tt:.1f}'
    try:
        with open(out_dir / 'ecpfl_results.json', 'r', encoding='utf-8') as f:
            s = json.load(f)
        row['acc'] = f"{s['final_test_acc']:.2f}"
        row['TV_MB'] = f"{s['total_tv_mb']:.2f}"
        row['PV_MB'] = f"{s['total_pv_mb']:.2f}"
        row['dataset'] = s['config']['data']['dataset']
        row['model'] = s['config']['model']['name']
        row['variant'] = Path(rel).name
    except (OSError, KeyError, json.JSONDecodeError) as e:
        row['status'] = f'ok(汇总缺失:{e})'
    print(f'[OK] {rel} | acc={row["acc"]}% | TV={row["TV_MB"]}MB '
          f'| PV={row["PV_MB"]}MB | TT={row["TT_s"]}s', flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description='ECPFL V17 论文实验批量运行')
    parser.add_argument('--only', default=None,
                        help='子树/配置过滤，如 table3 或 table3/mnist_th,ablation')
    parser.add_argument('--dry-run', action='store_true', help='只打印命令不执行')
    args = parser.parse_args()

    configs = collect_configs(args.only)
    if not configs:
        print(f'未找到配置：--only {args.only}（树根 {CONFIG_TREE}）')
        sys.exit(1)
    print(f'共 {len(configs)} 个实验待运行，结果目录 {RESULTS_DIR}')
    rows = [run_one(rel, cfg, args.dry_run) for rel, cfg in configs]

    if not args.dry_run:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        fields = ['config', 'dataset', 'model', 'variant', 'status',
                  'acc', 'TV_MB', 'PV_MB', 'TT_s']
        with open(SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, '') for k in fields})
        n_ok = sum(1 for r in rows if r['status'] == 'ok')
        print(f'[DONE] {n_ok}/{len(rows)} 成功，汇总：{SUMMARY_CSV}')
        if n_ok < len(rows):
            print('失败项：' + ', '.join(r['config'] for r in rows if r['status'] != 'ok'))


if __name__ == '__main__':
    main()
