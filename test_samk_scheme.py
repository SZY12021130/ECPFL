# -*- coding: utf-8 -*-
"""
SAMK（TDSC 2025）复现自检
=========================
覆盖：Paillier（加解密/同态加法/打包）、BFV（加解密/同态加法）、
拉格朗日插值、SAMK 全流程（无掉线 / 上传前掉线 / 上传后掉线重连）、
明文与噪声界的参数校验、通信量核算。

用法：
    python test_samk_scheme.py            # 全部用例
    python test_samk_scheme.py -k dropout # 仅含关键字的用例
"""

import argparse
import sys
import time
import traceback
from typing import Callable, Dict, List, Tuple

import numpy as np

from ckks_fed.samk_crypto import (
    BFVContext, BFVParams, LagrangeInterpolator, SAMKAccessError, SAMKParams,
    SAMKScheme, pack_points, paillier_keygen, unpack_points,
)

CASES: List[Tuple[str, Callable[[], None]]] = []


def case(fn: Callable[[], None]) -> Callable[[], None]:
    CASES.append((fn.__name__, fn))
    return fn


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# =============================================================================
# 1. Paillier
# =============================================================================
@case
def test_paillier_roundtrip_and_homomorphism():
    """Paillier.Encrypt/Decrypt 正确 + 同态加法 = 明文相加 + 打包拆包。"""
    kp = paillier_keygen(512, np.random.default_rng(1), slot_bits=64)
    msgs = [0, 1, 12345, 2 ** 60 + 7]
    for m in msgs:
        _assert(kp.secret.decrypt_int(kp.public.encrypt_int(m)) == m,
                f"Paillier 单条加解密失败 m={m}")

    a, b = 987654321, 123456789
    ca = kp.public.encrypt_int(a)
    cb = kp.public.encrypt_int(b)
    _assert(kp.secret.decrypt_int(kp.public.add_ciphertexts([ca, cb])) == a + b,
            "Paillier 同态加法失败")

    vals = [(i * 7919) % (1 << 63) for i in range(20)]
    cts = kp.public.encrypt_points(vals)
    got = []
    for i, c in enumerate(cts):
        cnt = min(kp.public.max_slots, len(vals) - i * kp.public.max_slots)
        got.extend(kp.public.decode_points(kp.secret.decrypt_int(c), cnt))
    _assert(got == vals, f"Paillier 打包/拆包失败: {got[:3]} vs {vals[:3]}")
    # 打包后同态相加 == 各槽相加（无进位）
    cts2 = kp.public.encrypt_points(vals)
    summed = [kp.public.add_ciphertexts([x, y]) for x, y in zip(cts, cts2)]
    merged = []
    for i, c in enumerate(summed):
        cnt = min(kp.public.max_slots, len(vals) - i * kp.public.max_slots)
        merged.extend(kp.public.decode_points(kp.secret.decrypt_int(c), cnt))
    _assert(merged == [2 * v for v in vals], "打包态同态加法失败（进位/槽宽问题）")


# =============================================================================
# 2. BFV
# =============================================================================
@case
def test_bfv_encrypt_decrypt_and_add():
    """BFV 单密钥加解密 + 同态加法（多密钥聚合的 c0 求和）。"""
    bfv = BFVContext(BFVParams(n=256, t_bits=40, seed=2))
    k1, k2 = bfv.keygen(), bfv.keygen()
    m1 = np.random.default_rng(1).integers(-1000, 1000, 256)
    m2 = np.random.default_rng(2).integers(-1000, 1000, 256)
    c1 = bfv.encrypt(k1.pk, m1)
    c2 = bfv.encrypt(k2.pk, m2)
    _assert(np.array_equal(bfv.decrypt(k1.sk, c1), m1), "BFV 加解密失败")
    # SAMK 视角：c0 相加 + 各自的 f_i(x)=sk_i·c1_i 插值后解密
    ct_sum = c1 + c2
    f = k1.sk.mul(c1.c1).add(k2.sk.mul(c2.c1))
    got = bfv.decrypt_with_poly(ct_sum.c0, bfv.crt_combine(f.r1, f.r2))
    _assert(np.array_equal(got, m1 + m2), "BFV 多密钥 c0 求和 + F(x) 解密失败")


# =============================================================================
# 3. 插值
# =============================================================================
@case
def test_lagrange_interpolation():
    """N 个点恢复次数 < N 的多项式（多个模数规模）。"""
    rng = np.random.default_rng(3)
    for n, q in ((4, 101), (16, 1000003), (128, 2147483647)):
        xs = np.sort(rng.choice(np.arange(1, 4 * n), n, replace=False)).astype(np.int64)
        coef = rng.integers(0, q, n, dtype=np.int64)
        y = np.zeros(n, dtype=np.int64)
        for c in coef[::-1]:
            y = (y * xs + int(c)) % q
        back = LagrangeInterpolator(xs, q).interpolate(y)
        _assert(np.array_equal(back, coef), f"插值失败 n={n}")


# =============================================================================
# 4. SAMK 全流程
# =============================================================================
def _make_scheme(num_clients: int = 4, n: int = 64, dim: int = 128,
                 seed: int = 5) -> Tuple[SAMKScheme, Dict[int, np.ndarray]]:
    sch = SAMKScheme(SAMKParams(n=n, t_bits=40, scale_bits=16,
                                paillier_bits=512, seed=seed),
                     num_clients=num_clients).setup()
    rng = np.random.default_rng(seed)
    updates = {i: rng.normal(0, 0.05, dim) for i in range(1, num_clients + 1)}
    return sch, updates


@case
def test_samk_all_online():
    """H = 全体客户端：每个客户端都能独立解出 Σ m_j。"""
    sch, updates = _make_scheme()
    ups = {i: sch.client_upload(i, updates[i]) for i in updates}
    res = sch.aggregate(ups)
    expect = np.sum(list(updates.values()), axis=0)
    tol = len(updates) * 0.5 / sch.params.scale + 1e-9   # 量化误差上界
    for i in ups:
        got = sch.client_decrypt(i, res.downloads[i])
        _assert(np.max(np.abs(got - expect)) <= tol,
                f"客户端 {i} 解密误差 {np.max(np.abs(got - expect)):.2e} > {tol:.2e}")
    _assert(res.upload_bytes > 0 and res.download_bytes > 0, "通信量核算异常")


@case
def test_samk_dropout_before_upload():
    """上传前掉线：服务器只聚合在线者；掉线者无法解密聚合结果。"""
    sch, updates = _make_scheme(num_clients=5)
    online = [1, 2, 4]
    ups = {i: sch.client_upload(i, updates[i]) for i in online}
    res = sch.aggregate(ups, dropouts=[3, 5])
    expect = np.sum([updates[i] for i in online], axis=0)
    got = sch.client_decrypt(2, res.downloads[2])
    _assert(np.max(np.abs(got - expect)) < 3 * 0.5 / sch.params.scale + 1e-9,
            "掉线场景解密误差过大")
    for dropped in (3, 5):
        try:
            sch.server.fetch_download(dropped)
        except SAMKAccessError:
            continue
        raise AssertionError(f"未上传的客户端 {dropped} 不应拿到聚合结果")


@case
def test_samk_reconnect_after_upload():
    """上传后掉线：重连仍可取回同一份下载包并正确解密（论文核心卖点）。"""
    sch, updates = _make_scheme(num_clients=4)
    ups = {i: sch.client_upload(i, updates[i]) for i in updates}
    res = sch.aggregate(ups)
    late = sch.server.fetch_download(4)          # 客户端 4 上传后离线，此处模拟重连
    expect = np.sum(list(updates.values()), axis=0)
    got = sch.client_decrypt(4, late)
    _assert(np.max(np.abs(got - expect)) < 4 * 0.5 / sch.params.scale + 1e-9,
            "重连客户端解密结果不正确")


@case
def test_samk_paper_scale():
    """论文口径参数（n=1024, Paillier 512/1024bit）下单密文全流程。"""
    t0 = time.time()
    sch = SAMKScheme(SAMKParams(n=1024, t_bits=40, scale_bits=16,
                                paillier_bits=512, seed=11), num_clients=6).setup()
    rng = np.random.default_rng(0)
    updates = {i: rng.normal(0, 0.02, 1024) for i in range(1, 7)}
    ups = {i: sch.client_upload(i, updates[i]) for i in updates}
    res = sch.aggregate(ups)
    expect = np.sum(list(updates.values()), axis=0)
    got = sch.client_decrypt(1, res.downloads[1])
    err = float(np.max(np.abs(got - expect)))
    _assert(err < 6 * 0.5 / sch.params.scale + 1e-9, f"论文口径解密误差 {err:.2e}")
    _assert(len(sch.interp_q1.xs) == 1024, "插值点数应等于环维度 N")
    _assert(res.stats["paillier_packs_per_chunk"] ==
            int(np.ceil((1024 - 1) / sch.server_public_key.max_slots)),
            "Paillier 打包数量与槽宽不一致")
    print(f"      [info] 6 客户端×1024 维 = {time.time() - t0:.1f}s, "
          f"上行 {res.upload_bytes / 1e6:.2f}MB, 下行 {res.download_bytes / 1e6:.2f}MB")


@case
def test_samk_multi_chunk_and_bounds():
    """多块（dim > n）+ 明文/噪声界校验 + 越界报错。"""
    sch, updates = _make_scheme(num_clients=3, n=64, dim=200)
    ok, msg = sch.check_bounds(list(updates.values()))
    _assert(ok, f"合法更新的界校验失败: {msg}")
    ups = {i: sch.client_upload(i, updates[i]) for i in updates}
    res = sch.aggregate(ups)
    expect = np.sum(list(updates.values()), axis=0)
    got = sch.client_decrypt(1, res.downloads[1])
    _assert(np.max(np.abs(got - expect)) < 3 * 0.5 / sch.params.scale + 1e-9,
            "多块聚合误差过大")
    # 明显越界的大更新应被拒绝（|m| > t/(2n)）
    big = (sch.max_abs_quantized() * 2.0) / sch.params.scale + 1.0
    try:
        sch.client_upload(1, np.full(200, big))
    except ValueError as exc:
        _assert("越界" in str(exc), f"异常信息不匹配: {exc}")
    else:
        raise AssertionError("越界更新未被拒绝")


@case
def test_pack_points_roundtrip():
    """打包/拆包基础语义（含高位预留，防进位）。"""
    vals = [0, 1, (1 << 64) - 1, 123456789012345]
    packed = pack_points(vals, 66)
    _assert(unpack_points(packed, 66, len(vals)) == vals, "打包/拆包不一致")
    summed = pack_points(vals, 66) + pack_points(vals, 66)   # 等价于同态相加
    _assert(unpack_points(summed, 66, len(vals)) == [2 * v for v in vals],
            "槽宽不足导致进位污染")


# =============================================================================
# 运行器
# =============================================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="SAMK 复现自检")
    parser.add_argument("-k", default=None, help="只运行名字包含该关键字的用例")
    args = parser.parse_args()
    cases = [(n, f) for n, f in CASES if not args.k or args.k in n]

    failed = 0
    t_all = time.time()
    for name, fn in cases:
        t0 = time.time()
        try:
            fn()
        except Exception:
            failed += 1
            print(f"[FAIL] {name}  ({time.time() - t0:.2f}s)")
            traceback.print_exc()
        else:
            print(f"[PASS] {name}  ({time.time() - t0:.2f}s)")
    print(f"\n{len(cases) - failed}/{len(cases)} 通过，总耗时 {time.time() - t_all:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
