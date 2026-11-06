# -*- coding: utf-8 -*-
"""MASER 真实多密钥（xMK-CKKS）重跑：先 smoke 验证，再四数据集串行。
等待 ESAFL q20 队列（ESAFL ALL DONE）完成后自动开始。"""
import os
import subprocess
import time
from datetime import datetime

ROOT = r'E:\GithubProjects\ckks_fed_robustness'
CFG_DIR = os.path.join(ROOT, r'accuracy_baseline\maser\config_mk')
PYEXE = r'D:\ProgramData\anaconda3\envs\concrete-env\python.exe'
ESAFL_PROGRESS = os.path.join(ROOT, r'AAAAA_Rework\ESAFL\config\rerun_q20\_progress.txt')

ORDER = [
    'maser_mk_smoke_mnist.yaml',   # 2 轮 smoke：失败即中止
    'maser_mk_mnist.yaml',
    'maser_mk_fashionmnist.yaml',
    'maser_mk_cifar10.yaml',
    'maser_mk_svhn.yaml',
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


# ---- 等待 ESAFL q20 队列结束 ----
log("WAITING for ESAFL q20 queue (ESAFL ALL DONE) ...")
while True:
    try:
        with open(ESAFL_PROGRESS, encoding='utf-8') as f:
            if 'ESAFL ALL DONE' in f.read():
                break
    except FileNotFoundError:
        pass
    time.sleep(60)
log("ESAFL queue finished -> START MASER xMK rerun")

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
    if ret != 0:
        if 'smoke' in name:
            log("SMOKE FAILED -> abort MASER queue（检查 logs/maser_mk_smoke_mnist.log）")
            break
        log(f"WARNING: {name} failed, continue next")

log("MASER MK ALL DONE")
