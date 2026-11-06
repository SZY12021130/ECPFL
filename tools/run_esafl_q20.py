# -*- coding: utf-8 -*-
"""ESAFL 方案A 重跑（logq0=20 + quant_clip=1.0），串行，等待 ECPFL 队列完成后自动开始。"""
import os
import subprocess
import time
from datetime import datetime

ROOT = r'E:\GithubProjects\ckks_fed_robustness'
CFG_DIR = os.path.join(ROOT, r'AAAAA_Rework\ESAFL\config\rerun_q20')
PYEXE = r'D:\ProgramData\anaconda3\envs\concrete-env\python.exe'
ECPFL_PROGRESS = os.path.join(ROOT, r'AAAAA_Rework\ECPFL\config\rerun_tt\_progress.txt')

ORDER = [
    # 表三 alpha=1（results_dir=accuracy_diri1）
    'esafl_mnist_a1.yaml', 'esafl_fmnist_a1.yaml', 'esafl_cifar10_a1.yaml', 'esafl_svhn_a1.yaml',
    # alpha 扫描（results_dir=noniid）
    'esafl_fmnist_a0.1.yaml', 'esafl_fmnist_a0.5.yaml', 'esafl_fmnist_a5.yaml', 'esafl_fmnist_a10.yaml',
    'esafl_cifar10_a0.1.yaml', 'esafl_cifar10_a0.5.yaml', 'esafl_cifar10_a5.yaml', 'esafl_cifar10_a10.yaml',
]

LOG_DIR = os.path.join(CFG_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
progress = os.path.join(CFG_DIR, '_progress.txt')

env = os.environ.copy()
env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
env['PYTHONIOENCODING'] = 'utf-8'


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(progress, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ---- 等待 ECPFL 队列结束 ----
log("WAITING for ECPFL queue (ALL DONE) ...")
while True:
    try:
        with open(ECPFL_PROGRESS, encoding='utf-8') as f:
            if 'ALL DONE' in f.read():
                break
    except FileNotFoundError:
        pass
    time.sleep(60)
log("ECPFL queue finished -> START ESAFL rerun")

for name in ORDER:
    cfg_path = os.path.join(CFG_DIR, name)
    log_path = os.path.join(LOG_DIR, name.replace('.yaml', '.log'))
    log(f"START {name}")
    t0 = time.time()
    with open(log_path, 'w', encoding='utf-8', errors='replace') as lf:
        ret = subprocess.call([PYEXE, os.path.join(ROOT, 'main.py'), '--config', cfg_path],
                              stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
    dt = time.time() - t0
    status = 'OK' if ret == 0 else f'FAIL(exit={ret})'
    log(f"END   {name} -> {status}  ({dt/60:.1f} min)")

log("ESAFL ALL DONE")
