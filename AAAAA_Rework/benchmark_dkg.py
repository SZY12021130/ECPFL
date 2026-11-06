# -*- coding: utf-8 -*-
"""
DKG setup 基准：正确性（N=50 端到端）+ 性能（N=1000，进程池并行模拟）
================================================================
- 正确性：逐 dealer 生成份额并聚合到各客户端 running total（功能等价公告板，
  内存 O(N) 不物化 N^2 板）；抽样拉格朗日重构验证 + S 合成验证
- 性能：N=1000、τ=3、n=4096、AES-GCM 加密，6 进程池测墙钟
结果写入 AAAAA_Rework/ECPFL/result/complexity/dkg_benchmark_<ts>.json
"""
import json
import os
import sys
import time
import datetime
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np  # noqa: E402
from ckks_fed.dkg import DKGSetup  # noqa: E402

N_RING, TAU, SEED = 4096, 3, 42


# ---------------- 进程池 worker ----------------
_DKG = None


def _init(n, N, tau, seed):
    global _DKG
    _DKG = DKGSetup(n=n, num_clients=N, tau=tau, seed=seed)


def _work(k):
    _DKG.dealer_phase(k, aes=True)          # 产物即发即弃（模拟发往公告板）
    st = _DKG.stats[k]
    return (st.t_keygen_ms, st.t_eval_ms, st.t_crypto_ms, st.bytes_posted)


# ---------------- 正确性：N=50 端到端 ----------------
def correctness(N=50):
    print(f"=== 正确性验证 N={N} ===")
    dkg = DKGSetup(n=N_RING, num_clients=N, tau=TAU, seed=SEED)
    q1, q2 = dkg.ring.q1, dkg.ring.q2
    totals_s = [np.zeros(N_RING, dtype=np.int64) for _ in range(2)]
    totals_z = [np.zeros(N_RING, dtype=np.int64) for _ in range(2)]
    secrets, evals_f = [], []
    for k in range(1, N + 1):
        posts = dkg.dealer_phase(k, aes=False)
        secrets.append(dkg._last[1])
        evals_f.append(dkg._last[2][0])
        for i, (s, z) in posts.items():
            totals_s[0] = (totals_s[0] + s[0]) % q1
            totals_s[1] = (totals_s[1] + s[1]) % q2
            totals_z[0] = (totals_z[0] + z[0]) % q1
            totals_z[1] = (totals_z[1] + z[1]) % q2
    # R3
    g_list = []
    for i in range(1, N + 1):
        col_s = [(evals_f[k - 1][0][i - 1], evals_f[k - 1][1][i - 1]) for k in range(1, N + 1)]
        col_z = [(np.zeros(N_RING, dtype=np.int64), np.zeros(N_RING, dtype=np.int64))] * N  # z 列同理（略存，用零占位不影响 S 验证）
        g, _ = dkg.client_finalize(i, col_s, col_z)
        g_list.append(g)
    S1, S2 = DKGSetup.synthesize_S(g_list, dkg.ring)
    ok_S = dkg.verify_S(S1, S2, secrets)
    sample = [1, 2, 3, N // 2, N - 1, N]
    ok_dealers = [dkg.verify_dealer(k, secrets[k - 1], evals_f[k - 1]) for k in sample]
    print(f"  S 合成正确: {ok_S} | 抽样 dealer 重构: {sum(ok_dealers)}/{len(sample)}")
    return ok_S and all(ok_dealers)


# ---------------- 性能：N=1000 并行 ----------------
def perf(N=1000, workers=6):
    print(f"=== 性能基准 N={N}（{workers} 进程并行，AES-GCM）===")
    t0 = time.perf_counter()
    agg = np.zeros(4)
    with ProcessPoolExecutor(max_workers=workers,
                             initializer=_init,
                             initargs=(N_RING, N, TAU, SEED)) as ex:
        for r in ex.map(_work, range(1, N + 1), chunksize=8):
            agg += np.array(r)
    wall = time.perf_counter() - t0
    total_cpu_s = agg.sum() / 1e3
    print(f"  墙钟: {wall:.1f}s | 总CPU: {total_cpu_s:.0f}s | 每客户端平均: "
          f"keygen={agg[0]/N:.1f}ms eval={agg[1]/N:.1f}ms crypto={agg[2]/N:.1f}ms")
    print(f"  每客户端发布: {agg[3]/N/1e6:.0f} MB | 总发布: {agg[3]/1e9:.0f} GB")
    per_client_ms = (agg[0] + agg[1] + agg[2]) / N
    print(f"  真实部署墙钟估计（N 台设备全并行 + 千兆网下 256MB 双向 ≈ 4s）: "
          f"≈ {per_client_ms/1e3 + 4:.1f}s")
    return {'N': N, 'wall_s': round(wall, 1), 'total_cpu_s': round(total_cpu_s, 1),
            'per_client_keygen_ms': round(agg[0] / N, 1),
            'per_client_eval_ms': round(agg[1] / N, 1),
            'per_client_crypto_ms': round(agg[2] / N, 1),
            'bytes_posted_per_client_mb': round(agg[3] / N / 1e6, 1),
            'bytes_posted_total_gb': round(agg[3] / 1e9, 1)}


def main():
    ok = correctness(50)
    perf_result = perf(1000, workers=6)
    out_dir = os.path.join('AAAAA_Rework', 'ECPFL', 'result', 'complexity')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(out_dir, f'dkg_benchmark_{ts}.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'correctness_ok': ok, 'config': {'n': N_RING, 'tau': TAU, 'seed': SEED},
                   'perf': perf_result}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved -> {out}")


if __name__ == '__main__':
    main()
