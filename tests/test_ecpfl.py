# -*- coding: utf-8 -*-
"""
ECPFL（V17，scheme/V17-ecpfl.md）密码学核心与端到端测试。

覆盖：
  1. 环上 Shamir 拉格朗日恒等式（D2.2 / D2.3），τ=3/5、多个参与集合
  2. ESP-Tally：得票精确正确
  3. 同步聚合（式 13）：部分参与、bar S ≠ ∅ → 解密 = Σω_i x_i
  4. 掉线补偿（式 15）：|D|=1/3/半数 → 解密仍 = Σ_{i∈Ŝ} ω_i x_i
  5. ECP（式 16-17）：3 轮累加解密 = 逐轮解密之和
  6. KGC 参数断言
"""

import numpy as np
import pytest
from typing import Dict, Tuple

from ckks_fed.ecpfl_crypto import KGC, ECPFLClient, ECPFLServer, lagrange_coeffs


def _setup(n=512, N=8, tau=3, seed=42):
    kgc = KGC(n=n, num_clients=N, tau=tau, seed=seed)
    materials = kgc.distribute()
    clients = {i: ECPFLClient(kgc, materials[i]) for i in materials}
    server = ECPFLServer(kgc)
    return kgc, clients, server


def _ring_coeffs(ra):
    """RingArray → CRT 重建的整数系数（仅测试小数值场景使用）。"""
    ctx = ra.ctx
    q1, q2 = ctx.q1, ctx.q2
    q1_inv = pow(q1 % q2, q2 - 2, q2)
    c1 = ra.r1.astype(object)
    c2 = ra.r2.astype(object)
    k = ((c2 - c1) % q2 * q1_inv) % q2
    x = (c1 + q1 * k)
    half = ctx.Q // 2
    return np.where(x > half, x - ctx.Q, x).astype(object)


# ---------------------------------------------------------------------------
# 1. Shamir 拉格朗日恒等式（D2.2 / D2.3）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tau", [3, 5])
@pytest.mark.parametrize("S_set", [[1, 2, 3, 4], [2, 4, 6, 8], [1, 3, 5, 7, 8], list(range(1, 9))])
def test_shamir_lagrange(tau, S_set):
    """ECPFL-Lite：Σλ_i S_i = S（F_S(0)）；Σλ_i z_i = 0（Z(0)）。

    F_S 为 τ 阶（F_S(0)=S），任意 ≥ τ+1 子集可重构。"""
    N = 8
    if len(S_set) < tau + 1:
        pytest.skip("参与数须 ≥ τ+1（F_S 为 τ 阶）")
    kgc, _, _ = _setup(N=N, tau=tau)
    materials = kgc.distribute()
    lam = lagrange_coeffs(S_set, kgc.Q)
    acc = kgc.ring.zeros()
    zacc = kgc.ring.zeros()
    for i in S_set:
        acc = acc.add(materials[i]['S_i'].scalar_mul(lam[i]))
        zacc = zacc.add(materials[i]['z_i'].scalar_mul(lam[i]))
    recon = _ring_coeffs(acc)
    secret = _ring_coeffs(kgc.S)
    assert np.array_equal([int(a) % kgc.Q for a in recon],
                          [int(b) % kgc.Q for b in secret])
    # 零共享归零
    zrecon = _ring_coeffs(zacc)
    assert np.all(np.array([int(a) % kgc.Q for a in zrecon], dtype=object) == 0)


# ---------------------------------------------------------------------------
# 2. ESP-Tally（式 10）
# ---------------------------------------------------------------------------

def test_esp_tally_exact():
    """随机投票矩阵 → ν_j 精确正确；服务器仅接触密文。"""
    n, N, J = 512, 8, 11
    kgc, clients, server = _setup(n=n, N=N, tau=3)
    rng = np.random.default_rng(0)
    votes = rng.integers(0, 2, (N, J))
    S_set = list(range(1, N + 1))
    cts = [clients[i].esp_vote(1, S_set, votes[i - 1]) for i in S_set]
    nu = server.esp_tally(cts, J)
    assert np.array_equal(nu, votes.sum(axis=0))


def test_consensus_rules():
    nu = np.array([8, 3, 5, 1, 0, 8, 2, 8, 1, 4])
    assert ECPFLServer.consensus(nu, 'un', 0, 10) == [0, 1, 2, 3, 5, 6, 7, 8, 9]
    rk = ECPFLServer.consensus(nu, 'rk', 0.3, 10)
    assert sorted(rk) == [0, 5, 7]  # 前 ⌈0.3·10⌉=3 名（并列 8 分按索引序取前 3）
    th = ECPFLServer.consensus(nu, 'th', 0.5, 10)
    assert th == [0, 2, 5, 7]  # ν ≥ 5


# ---------------------------------------------------------------------------
# 3. 同步聚合（式 13）
# ---------------------------------------------------------------------------

def test_sync_aggregation_partial_participation():
    """部分参与 S（|S|≥τ，bar S ≠ ∅）：解密 = Σ_{i∈S} ω_i x_i。"""
    n, N, tau = 512, 8, 3
    kgc, clients, server = _setup(n=n, N=N, tau=tau)
    rng = np.random.default_rng(1)
    S_set = [1, 2, 4, 6, 7]           # |S| = 5 ≥ τ，bar S = {3,5,8} ≠ ∅
    J_sel = [0, 3]
    omegas = {i: 1.0 / len(S_set) for i in S_set}
    xs = {i: rng.uniform(-0.03, 0.03, n) for i in S_set}

    for j in J_sel:
        cts = [clients[i].esp_enc(2, j, S_set, xs[i], omegas[i]) for i in S_set]
        C = server.esp_agg(cts)
        for i in S_set:
            dec = clients[i].decrypt_pack(2, j, C)
            ref = sum(omegas[u] * xs[u] for u in S_set)
            assert np.max(np.abs(dec - ref)) < 1e-3


# ---------------------------------------------------------------------------
# 4. 掉线补偿（式 15）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("num_drop", [1, 3, 2])  # 半数掉线 = 8//2-1=3? N=8,S=7
def test_dropout_compensation(num_drop):
    """掉线 |D|=1/3：C = Σ_{i∈Ŝ}(ct+δ) 解密仍 = Σ_{i∈Ŝ} ω_i x_i（旧 λ 项抵消）。"""
    n, N, tau = 512, 8, 3
    kgc, clients, server = _setup(n=n, N=N, tau=tau)
    rng = np.random.default_rng(2)
    S_set = [1, 2, 3, 4, 5, 6, 7]      # |S|=7 ≥ τ
    D = S_set[:num_drop]
    Shat = [i for i in S_set if i not in D]
    assert len(Shat) >= tau
    omegas = {i: 1.0 / len(S_set) for i in S_set}   # 固定活跃集权重
    xs = {i: rng.uniform(-0.03, 0.03, n) for i in S_set}
    j = 1

    cts = {i: clients[i].esp_enc(3, j, S_set, xs[i], omegas[i]) for i in Shat}
    comps = [clients[i].esp_comp(3, j, S_set, Shat) for i in Shat]
    C = server.esp_agg([cts[i] for i in Shat], comps)
    dec = clients[Shat[0]].decrypt_pack(3, j, C)
    ref = sum(omegas[u] * xs[u] for u in Shat)
    assert np.max(np.abs(dec - ref)) < 1e-3


# ---------------------------------------------------------------------------
# 5. ECP 跨轮累加（式 16-17）
# ---------------------------------------------------------------------------

def test_ecp_cross_round_accumulation():
    """3 轮密文累加解密 = 逐轮解密之和。"""
    n, N, tau = 512, 8, 3
    kgc, clients, server = _setup(n=n, N=N, tau=tau)
    rng = np.random.default_rng(3)
    S_set = list(range(1, N + 1))
    j = 2
    omegas = {i: 1.0 / N for i in S_set}

    round_C, round_A, per_round = [], [], []
    for t in [1, 2, 3]:
        xs = {i: rng.uniform(-0.02, 0.02, n) for i in S_set}
        cts = [clients[i].esp_enc(t, j, S_set, xs[i], omegas[i]) for i in S_set]
        C = server.esp_agg(cts)
        round_C.append(C)
        round_A.append(kgc.prpg_a(t, j))
        per_round.append(sum(omegas[i] * xs[i] for i in S_set))

    C_pre, A_pre = server.ecp_accumulate(round_C, round_A)
    dec = server.decrypt_prefetched(clients[1], C_pre, A_pre)
    ref = sum(per_round)
    assert np.max(np.abs(dec - ref)) < 1e-3


def test_sync_aggregation_large_n_const_p_tilde():
    """
    回归测试：n=4096、N=25 全参与同步聚合。
    p̃ 必须是常数多项式（仅 X^0 = p）；若误用稠密 p̃，negacyclic 卷积
    p̃·e 的系数 ~ p·n·eta 会随机超出 Q/2 触发 mod-q 回绕（约 40% 失败率）。
    """
    N, n = 25, 4096
    kgc = KGC(n=n, num_clients=N, tau=3, seed=7)
    mat = kgc.distribute()
    clients = {i: ECPFLClient(kgc, mat[i]) for i in mat}
    server = ECPFLServer(kgc)
    rng = np.random.default_rng(0)
    S_set = list(range(1, N + 1))
    om = {i: 1.0 / N for i in S_set}
    for j in (0, 1, 8):
        xs = {i: rng.uniform(-0.03, 0.03, n) for i in S_set}
        cts = [clients[i].esp_enc(1, j, S_set, xs[i], om[i]) for i in S_set]
        C = server.esp_agg(cts)
        dec = clients[1].decrypt_pack(1, j, C)
        ref = sum(om[i] * xs[i] for i in S_set)
        assert np.max(np.abs(dec - ref)) < 1e-3


# ---------------------------------------------------------------------------
# 6. 编排级测试：Phase C（部分参与+掉线）+ Phase D（ECP 预取）
#    5 轮、R=2、K=4、N=8、τ=3、dropout_rate=0.3
# ---------------------------------------------------------------------------

from main_ecpfl import ECPFLOrchestrator, select_top_packs


def _setup_orch(n=512, N=8, tau=3, K=4, R=2, beta=1.5, dropout=0.3, seed=0):
    kgc, clients, server = _setup(n=n, N=N, tau=tau, seed=seed)
    orch = ECPFLOrchestrator(kgc, clients, server, num_clients=N,
                             active_count=K, prefetch_rounds=R, overcommit=beta,
                             tau=tau, dropout_rate=dropout, prefetch_enabled=True,
                             prefetch_bytes_per_ct=1024, seed=seed)
    return kgc, clients, server, orch


def test_orchestrator_five_rounds():
    """5 轮编排：活跃集/掉线约束/队列淘汰/缓存命中/掉线聚合=明文对照/预取解密=逐轮和。"""
    n, N, K, tau, R, zeta, T = 512, 8, 6, 3, 2, 0.5, 5
    kgc, clients, server, orch = _setup_orch(n=n, N=N, tau=tau, K=K, R=R)
    rng = np.random.default_rng(7)
    J, d = 3, 3 * 512
    n_i = {i: i for i in range(1, N + 1)}
    ref_by_round: Dict[int, Dict[int, np.ndarray]] = {}   # r -> j -> Σ_{Ŝ} ω x 明文参照
    saw_dropout = False

    for t in range(1, T + 1):
        S_set = orch.active_set(t)
        assert len(S_set) == K and len(S_set) >= tau + 1
        n_S = sum(n_i[i] for i in S_set)
        omegas = {i: n_i[i] / n_S for i in S_set}
        xs = {i: rng.uniform(-0.03, 0.03, d) for i in S_set}

        D_set, Shat_set = orch.sample_dropout(t, S_set)
        assert len(Shat_set) >= tau + 1 and set(Shat_set).isdisjoint(D_set)
        if D_set:
            saw_dropout = True

        # Phase 1：投票 + 共识
        vote_bits = {i: np.zeros(J, dtype=np.int64) for i in S_set}
        vote_cts = []
        for i in S_set:
            top = select_top_packs(xs[i], J, n, zeta)
            vote_bits[i][top] = 1
            vote_cts.append(clients[i].esp_vote(t, S_set, vote_bits[i]))
        nu = server.esp_tally(vote_cts, J)
        K_set = server.consensus(nu, 'rk', zeta, len(S_set))
        assert len(K_set) >= 1

        # Phase 2/3：存活者加密；掉线路径加 esp_comp 补偿
        pack_cts, comp_cts = {}, {}
        for j in K_set:
            pack_cts[j] = []
            for i in Shat_set:
                pack = np.zeros(n)
                seg = xs[i][j * n:(j + 1) * n]
                pack[:len(seg)] = seg
                pack_cts[j].append(clients[i].esp_enc(t, j, S_set, pack, omegas[i]))
            comp_cts[j] = [clients[i].esp_comp(t, j, S_set, Shat_set)
                           for i in Shat_set] if D_set else []
        C_j = {j: server.esp_agg(pack_cts[j], comp_cts[j] or None) for j in K_set}

        # 掉线轮聚合正确性 = 明文对照（Σ_{i∈Ŝ} ω_i x_i，仅存活者）
        ref_by_round[t] = {}
        for j in K_set:
            ref = sum(omegas[u] * xs[u][j * n:(j + 1) * n] for u in Shat_set)
            ref_by_round[t][j] = ref
            dec = clients[Shat_set[0]].decrypt_pack(t, j, C_j[j])
            assert np.max(np.abs(dec[:len(ref)] - ref)) < 1e-3

        # Phase D：入队 + 淘汰（队列只留 r > t−R）
        orch.push_queue(t, K_set, C_j)
        assert all(r > t - R for r in orch.queued_rounds())
        if t > R:
            assert len(orch.queued_rounds()) <= R

        # ECP-Fetch：预采样池下载缺失包；重复调用应全部命中（增量为 0）
        fetched1 = orch.prefetch(t)
        assert all(v >= 0 for v in fetched1.values())
        assert sum(orch.prefetch(t).values()) == 0
    assert saw_dropout, "5 轮内应至少出现一轮掉线"

    # ECP-Sync：对任一持有缓存的客户端，one-shot 解密 = 缓存各 (r,j) 的逐轮明文和
    holders = sorted({i for (i, r, j) in orch.cache})
    assert holders, "预采样池应持有缓存"
    for i in holders:
        keys = [(r, j) for (ci, r, j) in orch.cache if ci == i]
        expected = np.zeros(d)
        for r, j in keys:
            seg_len = min(n, d - j * n)
            expected[j * n:j * n + seg_len] += ref_by_round[r][j][:seg_len]
        w_sync, used = orch.sync_client(i, np.zeros(d), d, n)
        assert used == len(keys)
        assert np.max(np.abs(w_sync - expected)) < 1e-3
        # 缓存已清空，再次 sync 应为 no-op
        w_again, used_again = orch.sync_client(i, w_sync, d, n)
        assert used_again == 0 and np.array_equal(w_again, w_sync)


def test_orchestrator_sync_equals_per_round_sum():
    """预取解密严格等于逐轮明文和：同步前核对缓存键集合对应的明文累计。"""
    n, N, K, tau, R, zeta, T = 512, 8, 6, 3, 2, 0.5, 5
    kgc, clients, server, orch = _setup_orch(n=n, N=N, tau=tau, K=K, R=R)
    rng = np.random.default_rng(11)
    J, d = 3, 3 * 512
    n_i = {i: 2 * i for i in range(1, N + 1)}
    ref: Dict[Tuple[int, int], np.ndarray] = {}   # (r, j) -> Σ_{Ŝ} ω x

    for t in range(1, T + 1):
        S_set = orch.active_set(t)
        n_S = sum(n_i[i] for i in S_set)
        omegas = {i: n_i[i] / n_S for i in S_set}
        xs = {i: rng.uniform(-0.02, 0.02, d) for i in S_set}
        D_set, Shat_set = orch.sample_dropout(t, S_set)
        vote_bits = {i: np.zeros(J, dtype=np.int64) for i in S_set}
        vote_cts = []
        for i in S_set:
            top = select_top_packs(xs[i], J, n, zeta)
            vote_bits[i][top] = 1
            vote_cts.append(clients[i].esp_vote(t, S_set, vote_bits[i]))
        K_set = server.consensus(server.esp_tally(vote_cts, J), 'rk', zeta, len(S_set))
        pack_cts = {j: [clients[i].esp_enc(
            t, j, S_set, np.pad(xs[i][j * n:(j + 1) * n], (0, max(0, n - (d - j * n)))
                                if j * n + n > d else (0, 0)), omegas[i])
            for i in Shat_set] for j in K_set}
        comps = {j: ([clients[i].esp_comp(t, j, S_set, Shat_set)
                      for i in Shat_set] if D_set else []) for j in K_set}
        C_j = {j: server.esp_agg(pack_cts[j], comps[j] or None) for j in K_set}
        for j in K_set:
            seg = min(n, d - j * n)
            ref[(t, j)] = sum(omegas[u] * xs[u][j * n:j * n + seg] for u in Shat_set)
        orch.push_queue(t, K_set, C_j)
        orch.prefetch(t)

    # 在 sync 前记录缓存键，计算期望明文和，再 sync 核对（式 16/17）
    for i in sorted({i for (i, r, j) in orch.cache}):
        keys = [(r, j) for (ci, r, j) in orch.cache if ci == i]
        expected = np.zeros(d)
        for r, j in keys:
            seg = min(n, d - j * n)
            expected[j * n:j * n + seg] += ref[(r, j)][:seg]
        w_sync, used = orch.sync_client(i, np.zeros(d), d, n)
        assert used == len(keys)
        assert np.max(np.abs(w_sync - expected)) < 1e-3


def test_orchestrator_queue_eviction_and_prefetch_bytes():
    """队列容量/淘汰语义 + 每客户端预取字节累计与事件流一致。"""
    n, N, K, tau, R = 512, 8, 6, 3, 2
    kgc, clients, server, orch = _setup_orch(n=n, N=N, tau=tau, K=K, R=R, dropout=0.0)
    for t in range(1, 6):
        S_set = orch.active_set(t)
        pack = np.zeros(n)
        C = clients[S_set[0]].esp_enc(t, 0, S_set, pack, 1.0 / K)
        orch.push_queue(t, [0], {0: C})
        assert all(r > t - R for r in orch.queued_rounds())
        orch.prefetch(t)
    total_events = sum(e['bytes'] for e in orch.prefetch_events)
    assert total_events == sum(orch.prefetch_bytes.values())
    assert total_events > 0


# ---------------------------------------------------------------------------
# 7. 参数断言
# ---------------------------------------------------------------------------

def test_kgc_bounds_assertion():
    """K·max|m| ≥ p/2 时须 raise 并提示调参。"""
    kgc = KGC(n=512, num_clients=8, tau=3)
    with pytest.raises(ValueError, match="参数无效"):
        kgc.assert_bounds(K=8, max_abs_x=1e8)  # 8·round(1e8·2^20) ≥ 2^49 = p/2
    kgc.assert_bounds(K=8, max_abs_x=1e-3)  # 正常范围通过
