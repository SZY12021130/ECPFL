# -*- coding: utf-8 -*-
"""
ECPFL-Lite KGC 初始化基准
==============================
Phase 0 全部开销：KGC 构造（采样 S + 2 个多项式）+ distribute（2 次多项式
在 N 点求值，分块向量化）+ 内存峰值。复杂度：时间 O(N·τ·n)，内存 O(τ·n)，
分发总量 O(N·n)（每客户端恒定 3 环元素 = 192 KB）。
结果写入 AAAAA_Rework/ECPFL/result/complexity/kgc_lite_benchmark_<ts>.json
"""
import json
import os
import sys
import time
import datetime

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ckks_fed.ecpfl_crypto import KGC  # noqa: E402

N_RING, TAU, SEED = 4096, 3, 42
RING_BYTES = 2 * 8 * N_RING  # CRT int64 x2 = 64 KB


def rss_mb():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    except Exception:
        return None


def main():
    print(f"ring element = {RING_BYTES} B | tau = {TAU} | per-client material = "
          f"3 x 64 KB = 192 KB (constant)\n")
    print(f"{'N':>7} {'t_init(s)':>10} {'t_dist(s)':>10} {'total(s)':>9} "
          f"{'KGC_mem(MB)':>12} {'dist_total(MB)':>15}")
    results = []
    for N in [50, 100, 500, 1000, 5000, 10000]:
        rss0 = rss_mb()
        t0 = time.perf_counter()
        kgc = KGC(n=N_RING, num_clients=N, tau=TAU, seed=SEED)
        t_init = time.perf_counter() - t0
        rss1 = rss_mb()
        t0 = time.perf_counter()
        materials = kgc.distribute()
        t_dist = time.perf_counter() - t0
        rss2 = rss_mb()
        # 校验：单客户端材料 = 3 个环元素
        m1 = materials[1]
        n_elems = len([k for k in ('S', 'S_i', 'z_i') if m1[k] is not None])
        assert n_elems == 3
        print(f"{N:>7} {t_init:>10.3f} {t_dist:>10.3f} {t_init + t_dist:>9.3f} "
              f"{(rss2 or 0) - (rss0 or 0):>12.1f} {3 * RING_BYTES * N / 1e6:>15.1f}")
        results.append({'N': N, 't_init_s': round(t_init, 4), 't_distribute_s': round(t_dist, 4),
                        't_total_s': round(t_init + t_dist, 4),
                        'rss_delta_mb': round((rss2 or 0) - (rss0 or 0), 1),
                        'distributed_bytes': 3 * RING_BYTES * N,
                        'per_client_bytes': 3 * RING_BYTES})
    out_dir = os.path.join('AAAAA_Rework', 'ECPFL', 'result', 'complexity')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(out_dir, f'kgc_lite_benchmark_{ts}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'config': {'n': N_RING, 'tau': TAU, 'seed': SEED},
                   'complexity': {'time': 'O(N*tau*n)', 'kgc_memory': 'O(tau*n)',
                                  'distribution': 'O(N*n)', 'per_client_storage': 'O(n) = 192KB const'},
                   'results': results}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {out}")


if __name__ == '__main__':
    main()
