# -*- coding: utf-8 -*-
"""
ECPFL (V17) 计算复杂度基准：KGC / 客户端 / 服务器各密码学组件耗时
====================================================================

输出 CSV + Markdown 到 AAAAA_Rework/ECPFL/result/complexity/（可用 --out 覆盖）。
每项 mean±std（重复 --reps 次，默认 5），n=4096、logp=50、Δ=2^20、eta=4、τ=3。

  KGC：keygen 耗时 vs N∈{50,100,500,1000}（含环上 Shamir 份额生成）、
        每客户端密钥材料字节数（s_i + S + z_i + N 个份额，O(N) 存储）
  客户端：ESP-Vote 生成、每包 ESP-Enc、one-shot Dec、ECP 预取累加（R=3）
  服务器：ESP-Tally 求和（K=25 票）、同步聚合（式 13）、掉线补偿聚合（式 15）

用法：
  python scripts/benchmark_complexity.py                        # 完整基准
  python scripts/benchmark_complexity.py --sizes 50 --reps 1    # 快速验证
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 项目根

from ckks_fed.ecpfl_crypto import KGC, ECPFLClient, ECPFLServer

N_DIM = 4096
TAU = 3
K_AGG = 25          # 聚合规模（= 活跃集大小）
R_PREFETCH = 3      # ECP 预取窗口


def timeit(fn, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return float(np.mean(ts)), float(np.std(ts))


def bench_kgc(N, reps):
    def once():
        kgc = KGC(n=N_DIM, num_clients=N, tau=TAU, seed=42)
        kgc.distribute()
    mean, std = timeit(once, reps)
    # 每客户端密钥材料字节数：s_i + S + z_i + N 个份额，每个 RingArray = n × 8B × 2 (CRT)
    bytes_per_client = (N + 3) * N_DIM * 8 * 2
    return mean, std, bytes_per_client


def bench_ops(reps):
    kgc = KGC(n=N_DIM, num_clients=50, tau=TAU, seed=42)
    materials = kgc.distribute()
    clients = {i: ECPFLClient(kgc, materials[i]) for i in materials}
    server = ECPFLServer(kgc)
    S_set = list(range(1, K_AGG + 1))
    rng = np.random.default_rng(0)
    x = rng.uniform(-0.02, 0.02, N_DIM)
    votes = np.zeros(N_DIM, dtype=np.int64)
    votes[:10] = 1

    def enc_pack():
        return clients[1].esp_enc(1, 0, S_set, x, 1.0 / K_AGG)

    def comp_pack():
        return clients[2].esp_comp(1, 0, S_set, S_set[1:])

    ct = enc_pack()
    comp = comp_pack()
    cts = [clients[i].esp_enc(1, 0, S_set, x, 1.0 / K_AGG) for i in S_set]
    vote_cts = [clients[i].esp_vote(1, S_set, votes) for i in S_set]
    round_cts = [clients[1].esp_enc(t, 0, S_set, x, 1.0 / K_AGG) for t in range(1, R_PREFETCH + 1)]
    round_as = [kgc.prpg_a(t, 0) for t in range(1, R_PREFETCH + 1)]

    def prefetch_acc():
        C_pre, A_pre = server.ecp_accumulate(round_cts, round_as)
        server.decrypt_prefetched(clients[1], C_pre, A_pre)

    jobs = {
        'client/esp_vote': lambda: clients[1].esp_vote(1, S_set, votes),
        'client/esp_enc_per_pack': enc_pack,
        'client/esp_comp_per_pack': comp_pack,
        'client/dec_one_shot': lambda: clients[1].decrypt_pack(1, 0, ct),
        'client/ecp_prefetch_R3': prefetch_acc,
        'server/esp_tally_K25': lambda: server.esp_tally(vote_cts, N_DIM),
        'server/esp_agg_sync_K25': lambda: server.esp_agg(cts),
        'server/esp_agg_dropout_K25': lambda: server.esp_agg(cts, [comp] * K_AGG),
    }
    out = {}
    for name, fn in jobs.items():
        mean, std = timeit(fn, reps)
        out[name] = (mean, std)
    return out


def main():
    ap = argparse.ArgumentParser(description='ECPFL V17 计算复杂度基准')
    ap.add_argument('--sizes', default='50,100,500,1000')
    ap.add_argument('--reps', type=int, default=5)
    ap.add_argument('--out', default='AAAAA_Rework/ECPFL/result/complexity')
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = [int(s) for s in args.sizes.split(',')]

    rows = []
    print(f'[KGC] n={N_DIM} τ={TAU} reps={args.reps}，N ∈ {sizes}')
    for N in sizes:
        mean, std, bpc = bench_kgc(N, args.reps)
        rows.append({'component': f'kgc/keygen_N{N}', 'mean_s': mean, 'std_s': std,
                     'bytes_per_client': bpc})
        print(f'  N={N:5d} | keygen = {mean:.3f}±{std:.3f}s | 材料 = {bpc / 1e6:.1f} MB/客户端')

    print(f'[OPS] n={N_DIM} K={K_AGG} R={R_PREFETCH} reps={args.reps}')
    ops = bench_ops(args.reps)
    for name, (mean, std) in ops.items():
        rows.append({'component': name, 'mean_s': mean, 'std_s': std, 'bytes_per_client': ''})
        print(f'  {name:28s} = {mean * 1e3:8.2f}±{std * 1e3:.2f} ms')

    csv_path = out_dir / 'complexity.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['component', 'mean_s', 'std_s', 'bytes_per_client'])
        w.writeheader()
        w.writerows(rows)

    md = ['# ECPFL (V17) 计算复杂度基准', '',
          f'- 环维度 n={N_DIM}，logp=50，Δ=2^20，eta=4，τ={TAU}，K={K_AGG}，R={R_PREFETCH}',
          f'- 重复 {args.reps} 次取 mean±std', '',
          '| 组件 | 耗时 mean±std (ms) | 每客户端材料 (MB) |', '|---|---|---|']
    for r in rows:
        ms = f'{r["mean_s"] * 1e3:.2f}±{r["std_s"] * 1e3:.2f}'
        mb = f'{r["bytes_per_client"] / 1e6:.1f}' if r['bytes_per_client'] != '' else '—'
        md.append(f'| {r["component"]} | {ms} | {mb} |')
    md_path = out_dir / 'complexity.md'
    md_path.write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'[DONE] {csv_path} | {md_path}')


if __name__ == '__main__':
    main()
