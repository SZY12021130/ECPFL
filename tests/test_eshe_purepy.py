# -*- coding: utf-8 -*-
"""
ESAFL PUREPY（纯 Python ESHE 复现）测试。

覆盖：
  1. 环运算（negacyclic NTT 乘法 vs 朴素多项式乘对照）
  2. 1 / 5 / 25 客户端 Enc → aggregate → Dec round-trip（精确恢复）
  3. 跨轮解密（密文减法链 = 论文 Δ_a·s 校正）
  4. ESAFLPacking 打包 → PUREPY 加密 → 解密 → 解包 round-trip
  5. CKKSManager PUREPY 集成 + ESAFLAdapter.extended_decrypt
"""

import numpy as np
import pytest
import torch

from ckks_fed.eshe import (
    RingContext,
    PurePyESHE,
    naive_negacyclic_mul,
)
from ckks_fed.packing import ESAFLPacking, PackingMetadata, ESHEEPPacking


# ---------------------------------------------------------------------------
# 1. 环运算
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n", [64, 256])
def test_ring_mul_vs_naive(n):
    """NTT 加速 negacyclic 乘法须与朴素 O(n^2) 参考实现一致（mod q1/q2）。"""
    ring = RingContext(n)
    rng = np.random.default_rng(0)
    a = rng.integers(0, 1 << 20, n, dtype=np.int64)
    b = rng.integers(0, 1 << 20, n, dtype=np.int64)

    prod = ring.from_ints(a).mul(ring.from_ints(b))

    ref1 = naive_negacyclic_mul(a % ring.q1, b % ring.q1, ring.q1)
    ref2 = naive_negacyclic_mul(a % ring.q2, b % ring.q2, ring.q2)
    assert np.array_equal(prod.r1, ref1)
    assert np.array_equal(prod.r2, ref2)


def test_ring_add_sub():
    ring = RingContext(64)
    rng = np.random.default_rng(1)
    a = ring.from_ints(rng.integers(0, 1 << 30, 64, dtype=np.int64))
    b = ring.from_ints(rng.integers(0, 1 << 30, 64, dtype=np.int64))
    assert ((a.add(b)).sub(b)) == a
    assert a.sub(a) == ring.zeros()


# ---------------------------------------------------------------------------
# 2. Enc → aggregate → Dec round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("num_clients", [1, 5, 25])
def test_enc_aggregate_dec_roundtrip(num_clients):
    """聚合密文 one-shot 解密须精确恢复 Σ m_i（mod p）。"""
    n = 512
    eshe = PurePyESHE(n=n, seed=42)
    rng = np.random.default_rng(0)
    # 模拟 ESAFLPacking 的 bit 编码值（20 bit）
    m = rng.integers(0, 1 << 20, n, dtype=np.int64)

    cts = [eshe.encrypt_chunk(i, m, counter=7) for i in range(num_clients)]
    agg = PurePyESHE.aggregate(cts)
    dec = eshe.decrypt(agg)

    expect = np.array(
        (int(num_clients) * m.astype(object)) % eshe.p, dtype=np.int64
    )
    assert np.array_equal(dec, expect)

    # 单客户端密文解密也须精确恢复
    for ct in cts:
        assert np.array_equal(eshe.decrypt(ct), m)


def test_encrypt_zero():
    """Enc(0)（ESHE-PS 全参与补齐密文）解密须为 0。"""
    eshe = PurePyESHE(n=512, seed=1)
    z = eshe.encrypt_zero(client_id=3, counter=2)
    assert np.all(eshe.decrypt(z) == 0)


def test_server_encrypt_roundtrip():
    """服务器（AS）侧加密（e=0, mask=a^t·s）解密须精确恢复。"""
    eshe = PurePyESHE(n=512, seed=1)
    for cid in range(4):
        eshe.register_client(cid)
    rng = np.random.default_rng(2)
    m = rng.integers(0, 1 << 20, 512, dtype=np.int64)
    ct = eshe.encrypt_server(m, counter=0)
    assert np.array_equal(eshe.decrypt(ct), m)


# ---------------------------------------------------------------------------
# 3. 跨轮解密（Δ_a·s 校正）
# ---------------------------------------------------------------------------

def test_cross_round_decrypt():
    """
    跨轮累加密文 Δ = ct^(r2) − ct^(r1)（不同 PRPG 计数器）解密：
    mask 同步相减即实现论文的 [[ct − Δ_a·s]_q]_p，结果须为 (m2 − m1) mod p。
    """
    eshe = PurePyESHE(n=512, seed=7)
    rng = np.random.default_rng(3)
    m1 = rng.integers(0, 1 << 20, 512, dtype=np.int64)
    m2 = rng.integers(0, 1 << 20, 512, dtype=np.int64)

    ct1 = eshe.encrypt_chunk(0, m1, counter=5)
    ct2 = eshe.encrypt_chunk(0, m2, counter=6)
    delta = PurePyESHE.subtract(ct2, ct1)

    dec = eshe.decrypt(delta)
    expect = np.array((m2.astype(object) - m1.astype(object)) % eshe.p,
                      dtype=np.int64)
    assert np.array_equal(dec, expect)


# ---------------------------------------------------------------------------
# 4. ESAFLPacking round-trip（经 PUREPY 加密）
# ---------------------------------------------------------------------------

def test_packing_roundtrip_via_purepy():
    """ESAFLPacking pack → ESHE 加密 → 解密 → unpack 须近似还原随机小更新。"""
    slot_count = 512
    packing = ESAFLPacking(slot_count, slots2=2, quant_bits=10)
    eshe = PurePyESHE(n=slot_count, seed=42)

    rng = np.random.default_rng(0)
    model_update = {
        "layer.weight": torch.randn(20, 10) * 0.01,
        "layer.bias": torch.randn(10) * 0.01,
    }

    chunks, metadata = packing.pack(model_update)
    decrypted_chunks = []
    for i, chunk in enumerate(chunks):
        m = np.round(chunk).astype(np.int64)
        ct = eshe.encrypt_chunk(client_id=i, message=m, counter=0)
        # 解密结果为 float 表示的编码整数，与 ESAFLPacking.unpack 的输入格式一致
        decrypted_chunks.append(eshe.decrypt(ct).astype(np.float64))

    restored = packing.unpack(decrypted_chunks, metadata)
    for name in model_update:
        assert torch.allclose(restored[name].double(),
                              model_update[name].double(), rtol=1e-2, atol=1e-3), name


# ---------------------------------------------------------------------------
# 5. CKKSManager PUREPY 集成
# ---------------------------------------------------------------------------

def _make_purepy_manager():
    from ckks_fed.crypto import CKKSManager
    config = {
        'poly_modulus_degree': 4096,
        'coeff_mod_bit_sizes': [40, 20, 40],
        'global_scale': 2 ** 20,
        'slot_packing': True,
        'packing': {
            'strategy': 'esafl',
            'quant_bits': 10,
            'quant_clip': 0.05,
        },
        'sparsification': {'strategy': None},
        'esafl': {'enabled': True, 'mode': 'PUREPY', 'prpg_seed': 42,
                  'num_clients': 5},
    }
    return CKKSManager(config)


def test_ckks_manager_purepy_e2e():
    """EP 全链路：客户端加密 → 密文求和聚合（EP.Eval）→ 解密除 N 平均。"""
    manager = _make_purepy_manager()
    assert manager.purepy_eshe is not None
    n = manager.purepy_eshe.n
    assert n == 2048  # poly 4096 / 2
    ep = manager.ep_packing
    assert ep is not None and ep.N == 5

    rng = np.random.default_rng(0)
    updates = [
        {"p.0": torch.rand(30, 10) * 0.04 - 0.02}
        for _ in range(5)
    ]
    weights = [float(cid + 1) for cid in range(5)]
    shapes = {"p.0": (30, 10)}

    # 客户端上传（skip_sparsification=False → 统一 quant_clip 固定 scale）
    enc_updates = [
        manager.encrypt_model_update(u, round_num=0, client_id=cid,
                                     skip_sparsification=False)
        for cid, u in enumerate(updates)
    ]
    for eu in enc_updates:
        assert eu['__purepy__'] is True
        assert eu['strategy'] == 'eshe_ep'

    # EP.Eval：密文逐系数求和（真正的密文域聚合，非逐客户端解密）
    agg = manager.aggregate_encrypted_updates(enc_updates, weights)
    assert agg['__purepy__'] is True
    assert agg.get('__num_sum__') == 5

    # 参考：各客户端量化值（num_sum=1 解密）的等权平均
    quantized = [manager.decrypt_model_update(eu, shapes) for eu in enc_updates]
    ref = sum(q["p.0"] for q in quantized) / len(quantized)

    # 聚合密文解密 = 密文求和 → slot 整数和 → 除 N → 反量化
    dec_agg = manager.decrypt_model_update(agg, shapes)
    assert torch.allclose(dec_agg["p.0"].double(), ref.double(),
                          rtol=1e-2, atol=1e-4)

    # 且须近似原始更新的等权平均（量化误差 ≤ 1 个量化步）
    ref_plain = sum(u["p.0"] for u in updates) / len(updates)
    assert torch.allclose(dec_agg["p.0"].double(), ref_plain.double(),
                          rtol=1e-2, atol=ep.quant_clip / ep.max_q)

    # 减法（delta）路径：同一密文域的自差分须为 0（整数级精确）
    delta = manager.subtract_encrypted_updates(agg, agg)
    assert delta['__purepy__'] is True
    dec_delta_ints = manager.purepy_eshe.decrypt(delta['ciphertexts'][0])
    assert np.all(dec_delta_ints == 0)


# ---------------------------------------------------------------------------
# 6. 论文 EP（Messages Encoding and Polynomials Packing, §V-B2）
# ---------------------------------------------------------------------------

def test_ep_setup_params():
    """论文 EP.Setup 公式：pad = ⌈log N⌉+1，T = ⌊log p/(log q0+pad)⌋。"""
    ep = ESHEEPPacking(n=4096, logq0=10, logp=50, num_clients=25)
    assert ep.pad == 6              # ⌈log2 25⌉ + 1
    assert ep.T == 3                # ⌊50 / (10+6)⌋
    assert ep.data_slots == 2       # 论文：T−1 个数据 slot + 1 个零多项式 slot
    assert ep.values_per_chunk == 4096 * 2
    # 论文进位安全：N·(2^logq0 − 1) < 2^(logq0+pad)
    assert 25 * (2 ** 10 - 1) < 2 ** (10 + 6)
    # 系数上界：β < 2^{T·slot_bits} ≤ p
    assert (1 << (ep.T * ep.slot_bits)) <= (1 << 50)


def test_ep_pack_unpack_roundtrip():
    """EP.EcdPack/DcdUnpk：量化 + slot 位域打包 round-trip。"""
    ep = ESHEEPPacking(n=512, logq0=8, logp=40, num_clients=5,
                       quant_clip=0.05)
    assert ep.pad == 4 and ep.T == 3 and ep.values_per_chunk == 1024
    update = {"w": torch.rand(600) * 0.04 - 0.02, "b": torch.rand(24) * 0.04 - 0.02}
    chunks, meta = ep.pack(update)   # 624 值 → 1 个密文
    assert len(chunks) == 1
    bound = 1 << (ep.T * ep.slot_bits)
    assert 0 <= chunks[0].min() and chunks[0].max() < bound
    assert bound <= (1 << ep.logp)
    restored = ep.unpack_average(chunks, meta, num_sum=1)
    step = ep.quant_clip / ep.max_q
    for name in update:
        assert torch.allclose(restored[name].double(), update[name].double(),
                              rtol=1e-2, atol=step)


def test_ep_ciphertext_sum_aggregation():
    """
    论文 EP.Eval：N 个密文逐系数求和 → one-shot 解密 → 每 slot 为 N 个
    客户端编码值的整数和 → 除 N 平均。含全最大值进位边界用例。
    """
    N, n = 25, 512
    logq0, logp = 8, 40
    eshe = PurePyESHE(n=n, seed=3)
    ep = ESHEEPPacking(n=n, logq0=logq0, logp=logp, num_clients=N,
                       quant_clip=0.05)
    assert ep.data_slots == 1  # T = 40//14 = 2

    rng = np.random.default_rng(1)
    base = rng.uniform(-0.03, 0.03, 300)
    updates = [base + 0.0005 * i for i in range(N)]

    cts = []
    for cid, vals in enumerate(updates):
        u = {"v": torch.tensor(vals)}
        chunks, _ = ep.pack(u, fixed_scale=0.05)
        cts.append(eshe.encrypt_chunk(cid, chunks[0], counter=9))

    agg = PurePyESHE.aggregate(cts)
    dec = eshe.decrypt(agg)  # 求和密文解密：每 slot 内为 N 个 u 的整数和

    # slot 提取（data_slots=1，数据 slot 位于 (T−1)·slot_bits，论文 Eq.10）
    slot = (dec >> ((ep.T - 1) * ep.slot_bits)) & ep.slot_mask
    expect_sum_u = None
    for cid, vals in enumerate(updates):
        q = np.round(np.clip(vals, -ep.quant_clip, ep.quant_clip)
                     / (ep.quant_clip / ep.max_q)).astype(np.int64)
        u = q + ep.max_q
        pad_len = n - len(u)
        u = np.concatenate([u, np.full(pad_len, ep.max_q)])
        expect_sum_u = u if expect_sum_u is None else expect_sum_u + u
    assert np.array_equal(slot, expect_sum_u)

    # 平均恢复：(Σu − N·max_q)/N · scale = 量化值的平均（与原始均值误差 ≤ 半步）
    q_avg = (slot[:300].astype(np.float64) - N * ep.max_q) / N
    vals_avg = q_avg * (ep.quant_clip / ep.max_q)
    q_indiv = [np.round(np.clip(v, -ep.quant_clip, ep.quant_clip)
                        / (ep.quant_clip / ep.max_q))
               for v in updates]
    assert np.allclose(vals_avg, np.mean(q_indiv, axis=0) * (ep.quant_clip / ep.max_q),
                       atol=1e-9)
    assert np.allclose(vals_avg, np.mean(updates, axis=0),
                       atol=ep.quant_clip / ep.max_q)

    # 进位边界：所有客户端全部传最大值 2^logq0−1
    u_max = np.full(n, (1 << logq0) - 1, dtype=np.int64)
    beta_max = u_max << ((ep.T - 1) * ep.slot_bits)
    cts_max = [
        eshe.encrypt_chunk(cid, beta_max, counter=10) for cid in range(N)
    ]
    dec_max = eshe.decrypt(PurePyESHE.aggregate(cts_max))
    slot_max = (dec_max >> ((ep.T - 1) * ep.slot_bits)) & ep.slot_mask
    # 25·255 = 6375 < 2^14，无串位，slot 和精确
    assert np.all(slot_max == N * ((1 << logq0) - 1))
    # 低位零 slot（论文进位余量 slot T）与更高位不受进位污染
    assert np.all((dec_max & ((1 << ((ep.T - 1) * ep.slot_bits)) - 1)) == 0)
    assert np.all(dec_max >> (ep.T * ep.slot_bits) == 0)


def test_adapter_extended_decrypt_purepy():
    """ESAFLAdapter.extended_decrypt 在 PUREPY 模式下须正确解密（含跨轮 delta）。"""
    manager = _make_purepy_manager()
    from ckks_fed.esafl_crypto import ESAFLAdapter
    adapter = ESAFLAdapter(manager, mode="PUREPY", prpg_seed=42)
    ep = manager.ep_packing

    rng = np.random.default_rng(0)
    upd = {"q.0": torch.randn(20, 5) * 0.02}
    shapes = {"q.0": (20, 5)}

    enc = manager.encrypt_model_update(upd, round_num=3, client_id=0,
                                       skip_sparsification=False)
    dec = adapter.extended_decrypt(enc, shapes, rounds_list=[3])
    chunks, meta = ep.pack(upd, fixed_scale=ep.quant_clip)
    q_ref = ep.unpack_average(chunks, meta, num_sum=1)
    assert torch.allclose(dec["q.0"].double(), q_ref["q.0"].double(),
                          rtol=1e-2, atol=1e-6)

    # 跨轮 delta：两个"全局状态"密文须共享同一 packing scale 才有意义。
    # 将 a（slot 1）、b（slot 2）拼成一次 EP pack（强制同一 scale），
    # 再构造两轮全局状态密文做减法。b ≥ a 保证差分无符号回绕。
    a = torch.rand(manager.purepy_eshe.n) * 0.02
    b = a + torch.rand(manager.purepy_eshe.n) * 0.02
    combined = {"q.0": torch.cat([a, b])}
    chunks, metadata = ep.pack(combined, fixed_scale=ep.quant_clip)
    assert len(chunks) == 1  # 2n 值 = 单密文容量
    m = chunks[0]
    sb = metadata.data['slot_bits']
    T = metadata.data['T']
    slot_mask = (1 << sb) - 1
    # slot 2 的编码值（论文 Eq.10 移位截取）
    u_b = (m >> sb) & slot_mask
    m_b = (u_b << ((T - 1) * sb)) | (u_b << ((T - 2) * sb))

    base = {
        '__sparse__': True, '__purepy__': True,
        'mask': [1], 'batch_size': manager.batch_size,
        'total_elements': metadata.data['total_elements'],
        'shapes': metadata.data['shapes'],
        'offsets': metadata.data['offsets'],
        'strategy': 'eshe_ep', 'sparsity_rate': 1.0,
        'packing_metadata': metadata.data,
    }
    eshe = manager.purepy_eshe
    state_a = dict(base, ciphertexts=[eshe.encrypt_server(m.copy(), counter=5)])
    state_b = dict(base, ciphertexts=[eshe.encrypt_server(m_b, counter=6)])

    delta = manager.subtract_encrypted_updates(state_b, state_a)
    # 整数系数级校验：[[Δ − mask_Δ]_Q]_p 须精确等于 (m_b − m_a) mod p
    dec_ints = eshe.decrypt(delta['ciphertexts'][0])
    expect_ints = np.array(
        (m_b.astype(object) - m.astype(object)) % eshe.p, dtype=np.int64)
    assert np.array_equal(dec_ints, expect_ints)

    # 浮点路径：b ≥ a，差分无回绕，extended_decrypt 须还原 (b − a) 量化差
    n = manager.purepy_eshe.n
    dec_delta = adapter.extended_decrypt(delta, shapes, rounds_list=[5, 6])
    scale = metadata.data['layer_scales']["q.0"]
    qa = torch.round(a / scale)
    qb = torch.round(b / scale)
    expect_delta = (qb - qa) * scale
    assert torch.allclose(dec_delta["q.0"].double().reshape(-1)[:n],
                          expect_delta.double(), rtol=1e-2, atol=1e-6)


def test_plaintext_range_guard():
    """明文系数越界（≥ p）须抛出清晰错误。"""
    eshe = PurePyESHE(n=512, seed=1)
    bad = np.full(512, eshe.p, dtype=np.int64)
    with pytest.raises(ValueError, match="p"):
        eshe.encrypt_chunk(0, bad, counter=0)
