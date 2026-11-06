# -*- coding: utf-8 -*-
"""串行重跑 ECPFL 12 组实验（4 数据集 × un/th/rk），concrete-env + GPU。

- 严格串行：一次只跑一个实验，避免 GPU/CPU 争用卡顿
- 每组日志写入独立 log 文件，进度写入 _progress.txt
"""
import os
import subprocess
import sys
import time
from datetime import datetime

ROOT = r'E:\GithubProjects\ckks_fed_robustness'
CFG_DIR = os.path.join(ROOT, r'AAAAA_Rework\ECPFL\config\rerun_tt')
OUT_DIR = os.path.join(ROOT, r'AAAAA_Rework\ECPFL\result\accuracy_diri1_tt')
LOG_DIR = os.path.join(CFG_DIR, 'logs')
PYEXE = r'D:\ProgramData\anaconda3\envs\concrete-env\python.exe'

ORDER = [
    # 先小模型后大模型，尽快拿到 MNIST/FMNIST 结果
    'ecpfl_mnist_un.yaml', 'ecpfl_mnist_th.yaml', 'ecpfl_mnist_rk.yaml',
    'ecpfl_fmnist_un.yaml', 'ecpfl_fmnist_th.yaml', 'ecpfl_fmnist_rk.yaml',
    'ecpfl_cifar10_un.yaml', 'ecpfl_cifar10_th.yaml', 'ecpfl_cifar10_rk.yaml',
    'ecpfl_svhn_un.yaml', 'ecpfl_svhn_th.yaml', 'ecpfl_svhn_rk.yaml',
]

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

env = os.environ.copy()
env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
env['PYTHONIOENCODING'] = 'utf-8'

progress = os.path.join(CFG_DIR, '_progress.txt')


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(progress, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


for name in ORDER:
    cfg_path = os.path.join(CFG_DIR, name)
    log_path = os.path.join(LOG_DIR, name.replace('.yaml', '.log'))
    log(f"START {name}")
    t0 = time.time()
    with open(log_path, 'w', encoding='utf-8', errors='replace') as lf:
        ret = subprocess.call([PYEXE, os.path.join(ROOT, 'main_ecpfl.py'),
                               '--config', cfg_path, '--output-dir', OUT_DIR],
                              stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
    dt = time.time() - t0
    status = 'OK' if ret == 0 else f'FAIL(exit={ret})'
    log(f"END   {name} -> {status}  ({dt/60:.1f} min)")

log("ALL DONE")
