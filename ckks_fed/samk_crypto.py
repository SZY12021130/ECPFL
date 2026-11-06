# -*- coding: utf-8 -*-
"""
SAMK（TDSC 2025）纯 Python 复现：多密钥 BFV + Paillier + 多项式插值
=====================================================================

对应论文 *SAMK: Secure Aggregation for Federated Learning Under Multiple Keys
With Low Communication Rounds*（IEEE TDSC, Vol.22 No.6, 2025）的 Algorithm 1-5。

本模块与论文的对应关系
----------------------
  Algorithm 1 Setup      -> :class:`SAMKScheme` 构造：BFV 公开参数 pp、Paillier
                            安全参数 κ、自变量集合 X（本模块 X 由 seed 确定性生成）
  Algorithm 2 KeyGen     -> :meth:`SAMKScheme.register_client`（客户端 BFV+Paillier 密钥）
                            + :attr:`SAMKScheme.server_public_key`（服务器 Paillier 密钥）
  Algorithm 3 Encrypt    -> :meth:`SAMKScheme.client_upload`：
                              1) BFV.Encrypt(m_i) -> ct_i=(c_{i,0}, c_{i,1})
                              2) f_i(x) = sk_i · c_{i,1}（环上 negacyclic 乘）
                              3) 在 X 的 N 个点上求值 f_i(x_t)
                              4) 前 N-1 点用服务器 Paillier 公钥打包加密；
                                 第 N-1 点用**每个客户端**的 Paillier 公钥分别加密
  Algorithm 4 Aggregate  -> :meth:`SAMKServer.aggregate`：
                              CT_agg 的 c_0 分量 = Σ_j c_{j,0}（BFV 同态加法）；
                              各采样点的 Paillier 密文做同态乘法（= 加法）；
                              服务器用自身私钥解密 N-1 个点，得到 F(x_0..x_{N-2})
  Algorithm 5 Decrypt    -> :meth:`SAMKScheme.client_decrypt`：
                              客户端用自己的 Paillier 私钥解出 F(x_{N-1})，
                              凑齐 N 点做拉格朗日插值恢复 F(x)，
                              再算 m_agg = round(t·[c_0 + F(x)]_Q / Q) mod t

掉线语义（与论文 Proposition 1 一致）
------------------------------------
* `H` = 实际上传密文的在线集合；服务器只聚合 H 内的密文。
* 上传成功后再掉线的客户端，可从服务器缓存 :meth:`SAMKServer.fetch_download`
  取回同一份下载包，仍能独立解出聚合结果。
* **上传前**掉线的客户端不在 H 内，只能拿到 N-1 个点，无法插值恢复 F(x)，
  :meth:`SAMKServer.fetch_download` 会抛 :class:`SAMKAccessError`。

实现要点与相对论文的差异（均为原型可跑通所需，见各方法 docstring）
------------------------------------------------------------------
1. 环 R_Q = Z_Q[X]/(X^N+1)，Q = q1·q2 由两个 NTT 友好素数 CRT 组成
   （复用 ``ckks_fed.eshe.RingContext``，乘法为 negacyclic NTT）。
2. 密钥 sk_i ∈ R_3（系数取 {-1,0,1}），噪声为中心二项分布；因此
   f_i(x)=sk_i·c_{i,1} 是**真正的环乘法**，F(x)=Σ_j sk_j·c_{j,1} 仍是次数 < N
   的多项式。客户端在 X 上求值、服务器聚合这些求值结果、客户端插值即可
   精确恢复同一个多项式 F —— 这就是论文“用 N 个点恢复 Σ sk_j c_{j,1}”的技巧。
3. 论文 Setup 要求 (q-1)·(x_max^N-1)/(x_max-1) < 2^{2κ}（直接对未取模的整数
   求值），κ 会爆炸。本实现让客户端**先把 f_i(x_t) 对 Q 取模**再加密，
   等价于论文“对 f' = Q 取模、商恒为 0”的特例；插值在 Z_Q 上做，
   因此结果仍然精确，且 κ 只需覆盖 n·Q（约 66 bit）。
4. Paillier 打包（论文 Fig.3(b)）：每个采样点占 ``slot_bits`` 位，高位补 0
   容纳聚合进位；``slot_bits = bit_length(n_clients·(Q-1))``。
   Paillier 公钥统一用 g = N+1（等价且更快，L(g^λ)=λ mod N）。
5. 明文定点：x -> round(x·φ)，φ = 2^{scale_bits}；BFV 明文模数 t = 2^{t_bits}，
   Δ = ⌊Q/t⌋。正确性条件（构造时断言）：
      |Σ_{j∈H} m_j| < t/2          （明文不回绕）
      |Σ noise|     < Δ/2          （噪声不越界）
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ckks_fed.eshe import RingArray, RingContext

__all__ = [
    "SAMKParams", "SAMKUpload", "SAMKDownload", "SAMKRoundResult",
    "BFVContext", "BFVCiphertext", "BFVKeyPair",
    "PaillierPublicKey", "PaillierSecretKey", "PaillierKeyPair", "paillier_keygen",
    "LagrangeInterpolator", "SAMKClient", "SAMKServer", "SAMKScheme",
    "SAMKAccessError", "pack_points", "unpack_points",
]


class SAMKAccessError(RuntimeError):
    """未上传密文的客户端试图获取聚合结果（论文：只拿到 N-1 个点，无法插值）。"""


# =============================================================================
# 0. 大整数工具
# =============================================================================
_SMALL_PRIMES = np.array(
    [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67,
     71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139,
     149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199], dtype=np.int64)


def _is_probable_prime(n: int, rounds: int = 16) -> bool:
    """Miller-Rabin 素性检测（大整数，纯 Python）。"""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)[:rounds]:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _rand_prime(bits: int, rng: np.random.Generator) -> int:
    """生成 bits 位随机素数（先用小素数筛，再做 Miller-Rabin）。"""
    if bits < 8:
        raise ValueError("素数位宽过小")
    low = 1 << (bits - 1)
    nbytes = (bits + 7) // 8
    while True:
        cand = (int.from_bytes(rng.bytes(nbytes), "big") % (1 << bits)) | low | 1
        if any(cand % int(p) == 0 for p in _SMALL_PRIMES):
            continue
        if _is_probable_prime(cand):
            return cand


# =============================================================================
# 1. Paillier（论文 Section II-B）
# =============================================================================
def pack_points(values: Sequence[int], slot_bits: int) -> int:
    """把若干非负整数按 ``slot_bits`` 位宽打包成一个大整数（论文 Fig.3(b)）。"""
    packed = 0
    for i, v in enumerate(values):
        iv = int(v)
        if iv < 0:
            raise ValueError("打包的采样点必须为非负整数（先 mod Q）")
        if iv >= (1 << slot_bits):
            raise ValueError(f"采样点 {iv.bit_length()} bit 超出槽宽 {slot_bits} bit")
        packed |= iv << (i * slot_bits)
    return packed


def unpack_points(packed: int, slot_bits: int, count: int) -> List[int]:
    """``pack_points`` 的逆操作。"""
    mask = (1 << slot_bits) - 1
    return [(packed >> (i * slot_bits)) & mask for i in range(count)]


class PaillierPublicKey:
    """
    Paillier 公钥 pk = (N, g)，g 取 N+1（加速：g^m = 1 + mN mod N²）。

    加密：c = g^m · r^N mod N²；同态加法：c1·c2 mod N²。
    """

    __slots__ = ("N", "N2", "g", "bits", "slot_bits", "max_slots")

    def __init__(self, N: int, g: Optional[int] = None, slot_bits: Optional[int] = None):
        self.N = int(N)
        self.N2 = self.N * self.N
        self.g = self.N + 1 if g is None else int(g)
        self.bits = self.N.bit_length()
        # 默认槽宽：容纳 n 个客户端的 Q 量级采样点之和（由 SAMKScheme 覆盖）
        self.slot_bits = int(slot_bits) if slot_bits else (self.bits - 1)
        # 预留 1 bit 保证打包结果 < N（槽内不进位，故 N 以下的整数可用）
        self.max_slots = max(1, (self.bits - 1) // self.slot_bits)

    # ---------------- 基本运算 ----------------
    def encrypt_int(self, m: int, rng: Optional[np.random.Generator] = None) -> int:
        """单条消息加密（r 由系统随机数生成，保证语义安全）。"""
        m = int(m) % self.N
        r = self._random_unit(rng)
        if self.g == self.N + 1:
            gm = (1 + m * self.N) % self.N2
        else:
            gm = pow(self.g, m, self.N2)
        return (gm * pow(r, self.N, self.N2)) % self.N2

    def add_ciphertexts(self, cts: Sequence[int]) -> int:
        """同态加法：∏ c_j mod N²。"""
        acc = 1
        for c in cts:
            acc = (acc * c) % self.N2
        return acc

    # ---------------- 打包 ----------------
    def encrypt_points(self, values: Sequence[int]) -> List[int]:
        """
        把采样点按槽宽打包后加密：每 ``max_slots`` 个点 -> 1 条 Paillier 密文。
        返回密文列表（长度 = ⌈len(values)/max_slots⌉）。
        """
        out = []
        k = self.max_slots
        for start in range(0, len(values), k):
            chunk = [int(v) for v in values[start:start + k]]
            out.append(self.encrypt_int(pack_points(chunk, self.slot_bits)))
        return out

    def decode_points(self, packed: int, count: int) -> List[int]:
        return unpack_points(packed, self.slot_bits, count)

    def _random_unit(self, rng: Optional[np.random.Generator] = None) -> int:
        """r ← Z*_N（均匀取 bits 位随机数模 N，非互素则重抽）。"""
        nbytes = (self.bits + 7) // 8
        while True:
            raw = rng.bytes(nbytes) if rng is not None else np.random.bytes(nbytes)
            r = int.from_bytes(raw, "big") % self.N
            if r > 1 and math.gcd(r, self.N) == 1:
                return r

    def nbytes(self) -> int:
        return 2 * self.bits // 8


class PaillierSecretKey:
    """Paillier 私钥 sk = (λ, μ)，g = N+1 时 μ = λ^{-1} mod N。"""

    __slots__ = ("N", "N2", "lam", "mu", "g")

    def __init__(self, N: int, lam: int, g: Optional[int] = None, mu: Optional[int] = None):
        self.N = int(N)
        self.N2 = self.N * self.N
        self.g = self.N + 1 if g is None else int(g)
        self.lam = int(lam)
        if mu is None:
            if self.g != self.N + 1:
                raise ValueError("仅 g=N+1 时可用 μ = λ^{-1} mod N 的简化式")
            self.mu = pow(self.lam % self.N, -1, self.N)
        else:
            self.mu = int(mu)

    def decrypt_int(self, c: int) -> int:
        """m = L(c^λ mod N²)·μ mod N，L(x) = (x-1)/N。"""
        x = pow(int(c), self.lam, self.N2)
        return ((x - 1) // self.N * self.mu) % self.N

    def decrypt_points(self, packed: int, count: int, slot_bits: int) -> List[int]:
        return unpack_points(self.decrypt_int(packed), slot_bits, count)


class PaillierKeyPair:
    __slots__ = ("public", "secret")

    def __init__(self, public: PaillierPublicKey, secret: PaillierSecretKey):
        self.public = public
        self.secret = secret


def paillier_keygen(modulus_bits: int = 512, rng: Optional[np.random.Generator] = None,
                    slot_bits: Optional[int] = None) -> PaillierKeyPair:
    """
    Paillier.KeyGen(1^κ)：|p|=|q|=κ，N=p·q，λ=lcm(p-1,q-1)，g=N+1。

    论文用 1024 bit 模数；原型默认 512 bit（明文空间仍远大于 n·Q，约 66 bit）。
    """
    rng = rng if rng is not None else np.random.default_rng()
    half = modulus_bits // 2
    while True:
        p = _rand_prime(half, rng)
        q = _rand_prime(half, rng)
        if p == q:
            continue
        N = p * q
        if N.bit_length() != modulus_bits:
            continue
        break
    lam = int((p - 1) * (q - 1) // math.gcd(p - 1, q - 1))
    pub = PaillierPublicKey(N, slot_bits=slot_bits)
    sec = PaillierSecretKey(N, lam)
    return PaillierKeyPair(pub, sec)


# =============================================================================
# 2. BFV（论文 Section II-A，单密钥部分 + 多密钥聚合视角）
# =============================================================================
@dataclass(frozen=True)
class BFVParams:
    n: int = 1024          # 环维度 N
    t_bits: int = 40       # 明文模数 t = 2^t_bits
    eta: int = 3           # 噪声中心二项分布参数（χ）
    seed: int = 42


@dataclass
class BFVKeyPair:
    sk: RingArray                       # s ∈ R_3
    pk: Tuple[RingArray, RingArray]     # (p0, p1) = (-(s·a+e), a)


class BFVCiphertext:
    """ct = (c_0, c_1) ∈ R_Q²，同态加法逐分量相加（MK-BFV 的 Add）。"""

    __slots__ = ("c0", "c1")

    def __init__(self, c0: RingArray, c1: RingArray):
        self.c0 = c0
        self.c1 = c1

    def __add__(self, other: "BFVCiphertext") -> "BFVCiphertext":
        return BFVCiphertext(self.c0.add(other.c0), self.c1.add(other.c1))

    def nbytes(self, q_bits: int) -> int:
        return 2 * self.c0.ctx.n * q_bits // 8


class BFVContext:
    """
    BFV 参数与加解密（NTT 加速的 negacyclic 环，CRT 双素数 Q = q1·q2）。

    与其他 BFV 实现一致，只做加法同态（SAMK 只需要加法）。
    """

    def __init__(self, params: BFVParams):
        self.params = params
        self.ring = RingContext(params.n)
        self.Q = self.ring.Q
        self.t = 1 << params.t_bits
        if not (self.t < self.Q):
            raise ValueError("明文模数 t 必须小于密文模数 Q")
        self.delta = self.Q // self.t
        self.q1, self.q2 = self.ring.q1, self.ring.q2
        self._q1_inv_mod_q2 = pow(self.q1 % self.q2, -1, self.q2)
        self._rng = np.random.default_rng(params.seed)

    # ---------------- 采样 ----------------
    def _ternary(self) -> RingArray:
        return self.ring.from_ints(self._rng.integers(-1, 2, self.params.n, dtype=np.int64))

    def _noise(self) -> RingArray:
        eta = self.params.eta
        b1 = self._rng.binomial(eta, 0.5, self.params.n)
        b2 = self._rng.binomial(eta, 0.5, self.params.n)
        return self.ring.from_ints((b1 - b2).astype(np.int64))

    def _uniform(self) -> RingArray:
        n = self.params.n
        # CRT 两个分量独立均匀 => R_Q 上均匀
        return RingArray(self.ring, self._rng.integers(0, self.q1, n, dtype=np.int64),
                         self._rng.integers(0, self.q2, n, dtype=np.int64))

    # ---------------- 密钥 ----------------
    def keygen(self) -> BFVKeyPair:
        """SecKeyGen: s ← R_3；PubKeyGen: pk = (p0, p1) = (-(s·a+e), a)。"""
        s = self._ternary()
        a = self._uniform()
        e = self._noise()
        p0 = s.mul(a).add(e).neg()
        return BFVKeyPair(sk=s, pk=(p0, a))

    # ---------------- 加解密 ----------------
    def quantize(self, x: np.ndarray, scale: float) -> np.ndarray:
        return np.round(np.asarray(x, dtype=np.float64) * scale).astype(np.int64)

    def encrypt(self, pk: Tuple[RingArray, RingArray], m: np.ndarray) -> BFVCiphertext:
        """ct = (Δ[m]_t + u·p0 + e0, u·p1 + e1)，u ← R_3，e0,e1 ← χ。"""
        mv = np.asarray(m, dtype=np.int64).reshape(-1)
        if mv.shape[0] != self.params.n:
            raise ValueError(f"明文长度 {mv.shape[0]} != 环维度 {self.params.n}")
        p0, p1 = pk
        u = self._ternary()
        e0, e1 = self._noise(), self._noise()
        delta_m = self.ring.from_ints(mv * self.delta)
        c0 = delta_m.add(u.mul(p0)).add(e0)
        c1 = u.mul(p1).add(e1)
        return BFVCiphertext(c0, c1)

    # ---------------- CRT / 中心化工具 ----------------
    def crt_combine(self, a1: np.ndarray, a2: np.ndarray) -> np.ndarray:
        """(a1 mod q1, a2 mod q2) -> [0, Q) 的整数（int64）。"""
        k = ((a2.astype(np.int64) - a1.astype(np.int64)) % self.q2) \
            * self._q1_inv_mod_q2 % self.q2
        return (a1.astype(np.int64) + self.q1 * k).astype(np.int64)

    def centered(self, a1: np.ndarray, a2: np.ndarray) -> np.ndarray:
        """CRT 复原后中心化到 (-Q/2, Q/2]（object dtype，避免溢出）。"""
        x = [int(v) for v in self.crt_combine(a1, a2)]
        half = self.Q // 2
        return np.array([v - self.Q if v > half else v for v in x], dtype=object)

    def _round_scale_down(self, v: np.ndarray) -> np.ndarray:
        """m = round(t·v/Q) mod t，中心化到 (-t/2, t/2]。"""
        t, Q, half_t = self.t, self.Q, self.t // 2
        out = np.empty(len(v), dtype=np.int64)
        for i, vi in enumerate(v):
            m = int(vi) * t
            m = (m + Q // 2) // Q if m >= 0 else -((-m + Q // 2) // Q)
            m %= t
            out[i] = m - t if m > half_t else m
        return out

    def decrypt(self, sk: RingArray, ct: BFVCiphertext) -> np.ndarray:
        """单密钥解密（自检/测试用）：m = round(t·[c0 + c1·s]_Q / Q) mod t。"""
        v = ct.c0.add(ct.c1.mul(sk))
        return self._round_scale_down(self.centered(v.r1, v.r2))

    def decrypt_with_poly(self, c0_sum: RingArray, f_coeffs: np.ndarray) -> np.ndarray:
        """
        多密钥聚合密文解密（Algorithm 5 第 3 步）：

            m_agg = round( t·[ c0_sum + F(x) ]_Q / Q ) mod t

        ``f_coeffs`` 是插值恢复出来的 F(x) 系数（[0,Q) 的整数）。
        """
        f = np.asarray(f_coeffs, dtype=np.int64) % self.Q
        v1 = (c0_sum.r1 + f) % self.q1
        v2 = (c0_sum.r2 + f) % self.q2
        return self._round_scale_down(self.centered(v1, v2))

    # ---------------- 采样点求值（f_i(x_t) mod Q）----------------
    def eval_poly_mod_q(self, poly: RingArray, xs: np.ndarray) -> np.ndarray:
        """
        在整数点 xs 上求多项式值并 mod Q（Horner，分 CRT 分量计算避免溢出）。

        f_i 的系数本身在 [0,Q)，故 e 步先按 q1/q2 求值再 CRT 复原。
        """
        y1 = self._horner(poly.r1, xs, self.q1)
        y2 = self._horner(poly.r2, xs, self.q2)
        return self.crt_combine(y1, y2)

    @staticmethod
    def _horner(coeffs: np.ndarray, xs: np.ndarray, q: int) -> np.ndarray:
        v = np.zeros(len(xs), dtype=np.int64)
        for c in coeffs[::-1]:
            v = (v * xs + int(c)) % q
        return v


# =============================================================================
# 3. 拉格朗日插值（论文 Section II-C，Poly.Inter）
# =============================================================================
class LagrangeInterpolator:
    """
    固定自变量集合 X 的插值算子（预计算矩阵，O(N²) 单次预计算 + O(N²) 每次求值）。

    给定 y_t = F(x_t) mod q，返回 F 的系数 [a_0..a_{N-1}] mod q：
        F(x) = Σ_t y_t · L_t(x),   L_t(x) = Π_{j≠t}(x-x_j) / Π_{j≠t}(x_t-x_j)
    """

    def __init__(self, xs: Sequence[int], q: int):
        self.xs = np.asarray(xs, dtype=np.int64) % q
        if len(np.unique(self.xs)) != len(self.xs):
            raise ValueError("插值自变量必须互不相同")
        self.q = int(q)
        self.n = len(self.xs)
        self._M = self._build_matrix()

    def _build_matrix(self) -> np.ndarray:
        q, xs, n = self.q, self.xs, self.n
        # g(x) = Π (x - x_j)，首一，次数 n
        g = np.zeros(n + 1, dtype=np.int64)
        g[0] = 1
        for j in range(n):
            xj = int(xs[j])
            prev = g.copy()
            g[0] = (-xj * int(prev[0])) % q
            g[1:] = (prev[:-1] - xj * prev[1:]) % q
        # g'(x_t) = Π_{j≠t}(x_t - x_j)
        dg = np.array([(k + 1) * int(g[k + 1]) % q for k in range(n)], dtype=np.int64)
        acc = np.zeros(n, dtype=np.int64)
        for k in range(n - 1, -1, -1):
            acc = (acc * xs + int(dg[k])) % q
        denom = acc
        if np.any(denom == 0):
            raise ValueError("存在重复插值点，无法求逆")
        inv = np.array([pow(int(d), -1, q) for d in denom], dtype=np.int64)
        # b_t(x) = g(x)/(x - x_t)：首一除法，向量化到所有 t
        b = np.zeros((n, n), dtype=np.int64)
        b[:, n - 1] = 1
        for k in range(n - 1, 0, -1):
            b[:, k - 1] = (int(g[k]) + xs * b[:, k]) % q
        M = np.empty((n, n), dtype=np.int64)
        for t in range(n):
            M[t] = (b[t] * int(inv[t])) % q
        return M

    def interpolate(self, ys: np.ndarray) -> np.ndarray:
        """ys: 长度 N 的 F(x_t) mod q；返回系数 [a_0..a_{N-1}] mod q。"""
        y = np.asarray(ys, dtype=np.int64) % self.q
        q, acc = self.q, np.zeros(self.n, dtype=np.int64)
        M = self._M
        for t in range(self.n):
            acc = (acc + M[t] * int(y[t])) % q
        return acc


# =============================================================================
# 4. 协议数据结构
# =============================================================================
@dataclass
class SAMKParams:
    """
    SAMK 全局参数（论文 Algorithm 1 的 PP = {pp, κ, X}）。

    n             : BFV 环维度 N（同时是“单密文打包参数量”与插值点数）
    t_bits        : BFV 明文模数位数，t = 2^t_bits
    scale_bits    : 定点缩放位数，φ = 2^scale_bits（模型更新 -> 整数）
    paillier_bits : Paillier 模数位宽（论文 1024；原型 512/1024 均可）
    x_spread      : 自变量取值上界（X ⊂ [1, x_spread]，默认 4n，需 ≪ q1）
    seed          : 参数/噪声/自变量生成的随机种子
    """

    n: int = 1024
    t_bits: int = 40
    scale_bits: int = 16
    paillier_bits: int = 512
    x_spread: int = 0
    eta: int = 3
    seed: int = 42

    @property
    def scale(self) -> float:
        return float(1 << self.scale_bits)


@dataclass
class SAMKUpload:
    """客户端一次上传的全部密文（算法 3 的输出）。"""

    client_id: int
    bfv_cts: List[BFVCiphertext]
    server_point_cts: List[List[int]]        # [chunk][pack] 服务器 Paillier 密文
    client_point_cts: List[Dict[int, int]]   # [chunk][目标客户端] 最后一点密文
    dim: int
    num_chunks: int
    nbytes: int = 0

    def num_paillier_cts(self) -> int:
        return sum(len(p) for p in self.server_point_cts) + \
            sum(len(p) for p in self.client_point_cts)


@dataclass
class SAMKDownload:
    """服务器下发给单个在线客户端的数据（算法 4/5）。"""

    client_id: int
    c0_sums: List[RingArray]         # [chunk] Σ_j c_{j,0}
    points: List[np.ndarray]         # [chunk] F(x_0..x_{N-2})（明文，[0, n·Q)）
    last_point_cts: List[int]        # [chunk] [[F(x_{N-1})]]_client
    online_ids: List[int]
    dim: int
    nbytes: int = 0


@dataclass
class SAMKRoundResult:
    """服务器一轮聚合的结果与统计。"""

    online_ids: List[int]
    dropouts: List[int]
    downloads: Dict[int, SAMKDownload]
    upload_bytes: int = 0
    download_bytes: int = 0
    agg_time: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# 5. 客户端 / 服务器
# =============================================================================
class SAMKClient:
    """客户端 Ui：持有 BFV(sk_i, pk_i) 与 Paillier(sk_i', pk_i')。"""

    def __init__(self, client_id: int, scheme: "SAMKScheme", bfv_keys: BFVKeyPair,
                 paillier: PaillierKeyPair):
        self.client_id = int(client_id)
        self.scheme = scheme
        self.bfv = scheme.bfv
        self.bfv_keys = bfv_keys
        self.paillier = paillier

    # ---------------- Algorithm 3：Encrypt ----------------
    def encrypt_update(self, update: np.ndarray) -> SAMKUpload:
        """
        加密本地模型更新：

          1) 量化 m = round(x·φ)，按 n 分块（BFV 批编码）
          2) ct_i = BFV.Encrypt(pk_i, m) = (c_{i,0}, c_{i,1})
          3) f_i(x) = sk_i · c_{i,1}（环乘法）
          4) 在 X 的 N 个点求值；前 N-1 点用服务器公钥打包加密，
             最后一点用每个客户端的公钥分别加密
        """
        sch = self.scheme
        x = np.asarray(update, dtype=np.float64).reshape(-1)
        dim = x.shape[0]
        m_all = self.bfv.quantize(x, sch.params.scale)
        n = sch.params.n
        num_chunks = int(math.ceil(dim / n))
        # 明文不回绕约束：|m_i| ≤ t/(2·n_clients)
        limit = sch.max_abs_quantized()
        if m_all.size and int(np.max(np.abs(m_all))) > limit:
            raise ValueError(
                f"量化明文越界：max|m|={int(np.max(np.abs(m_all)))} > t/(2n)={limit}；"
                f"请降低 scale_bits / 裁剪更新，或增大 t_bits")

        bfv_cts: List[BFVCiphertext] = []
        server_cts: List[List[int]] = []
        client_cts: List[Dict[int, int]] = []
        xs = sch.x_points
        server_pk = sch.server_public_key

        for j in range(num_chunks):
            seg = m_all[j * n:(j + 1) * n]
            m = np.zeros(n, dtype=np.int64)
            m[:len(seg)] = seg
            ct = self.bfv.encrypt(self.bfv_keys.pk, m)
            # f_i(x) = sk_i · c_{i,1}，再在 X 上求值（结果 mod Q）
            f = self.bfv_keys.sk.mul(ct.c1)
            y = self.bfv.eval_poly_mod_q(f, xs)
            bfv_cts.append(ct)
            server_cts.append(server_pk.encrypt_points(y[:-1]))
            last = int(y[-1])
            client_cts.append(
                {cid: client.paillier.public.encrypt_int(last)
                 for cid, client in sch.clients.items()})

        up = SAMKUpload(client_id=self.client_id, bfv_cts=bfv_cts,
                        server_point_cts=server_cts,
                        client_point_cts=client_cts,
                        dim=dim, num_chunks=num_chunks)
        up.nbytes = sch.estimate_upload_bytes(up)
        return up

    # ---------------- Algorithm 5：Decrypt ----------------
    def decrypt_aggregate(self, download: SAMKDownload) -> np.ndarray:
        """
        独立解密聚合密文：先用自身 Paillier 私钥解出 F(x_{N-1})，
        凑齐 N 点插值恢复 F(x)，再 BFV 解出 Σ_j m_j。
        """
        sch = self.scheme
        n = sch.params.n
        q1, q2 = sch.bfv.q1, sch.bfv.q2
        out = np.zeros(download.dim, dtype=np.int64)

        for j in range(len(download.c0_sums)):
            # 1) 自己的最后一点（Paillier 解密 + 拆包）
            packed = self.paillier.secret.decrypt_int(download.last_point_cts[j])
            last_vals = unpack_points(packed, sch.slot_bits, 1)
            last = last_vals[0]
            # 2) N-1 个服务器明文点 + 自己的最后一点 => N 个点
            ys = np.empty(n, dtype=np.int64)
            ys[:n - 1] = np.asarray(download.points[j], dtype=np.int64) % sch.bfv.Q
            ys[n - 1] = last % sch.bfv.Q
            # 3) 分别在 q1/q2 上插值，再 CRT 复原 F 的系数
            f1 = sch.interp_q1.interpolate(ys % q1)
            f2 = sch.interp_q2.interpolate(ys % q2)
            f_coeffs = sch.bfv.crt_combine(f1, f2)
            # 4) m_agg = round(t·[c0_sum + F]_Q / Q)
            m = self.bfv.decrypt_with_poly(download.c0_sums[j], f_coeffs)
            seg_len = min(n, download.dim - j * n)
            out[j * n:j * n + seg_len] = m[:seg_len]

        return out.astype(np.float64) / sch.params.scale


class SAMKServer:
    """半诚实服务器：持有 Paillier 密钥，**没有** BFV 密钥。"""

    def __init__(self, scheme: "SAMKScheme", paillier: PaillierKeyPair):
        self.scheme = scheme
        self.paillier = paillier
        self._download_cache: Dict[int, SAMKDownload] = {}
        self.last_result: Optional[SAMKRoundResult] = None

    # ---------------- Algorithm 4：Aggregate ----------------
    def aggregate(self, uploads: Dict[int, SAMKUpload],
                  dropouts: Optional[Sequence[int]] = None) -> SAMKRoundResult:
        """
        聚合同一轮所有在线客户端的上传。``uploads`` 的键集合即论文中的 H。

        返回 :class:`SAMKRoundResult`，其中 ``downloads[cid]`` 只发给上传过密文
        的客户端（离线/未上传者无法解密聚合结果）。
        """
        import time as _time
        t0 = _time.time()
        sch = self.scheme
        if not uploads:
            raise ValueError("没有可聚合的上传（H 为空）")
        online = sorted(int(c) for c in uploads)
        num_chunks = uploads[online[0]].num_chunks
        n = sch.params.n
        server_pk = self.paillier.public
        server_sk = self.paillier.secret

        c0_sums: List[RingArray] = []
        plain_points: List[np.ndarray] = []
        for j in range(num_chunks):
            # 1) BFV 同态加法：CT_agg 的 c0 分量
            c0 = uploads[online[0]].bfv_cts[j].c0.copy()
            for cid in online[1:]:
                c0 = c0.add(uploads[cid].bfv_cts[j].c0)
            c0_sums.append(c0)
            # 2) Paillier 同态乘法聚合 N-1 个点，再用服务器私钥解密
            n_packs = len(uploads[online[0]].server_point_cts[j])
            pts = []
            for p in range(n_packs):
                prod = server_pk.add_ciphertexts(
                    [uploads[cid].server_point_cts[j][p] for cid in online])
                packed = server_sk.decrypt_int(prod)
                # 最后一段可能不足 max_slots 个点
                count = min(server_pk.max_slots, (n - 1) - p * server_pk.max_slots)
                # 采样点对公开模数 Q 取模（插值在 Z_Q 上进行，结果不变）
                pts.extend(int(v) % sch.bfv.Q
                           for v in server_pk.decode_points(packed, count))
            plain_points.append(np.asarray(pts, dtype=np.int64))

        # 3) 每个客户端一份下载包：F(x_{N-1}) 的密文按目标客户端聚合
        downloads: Dict[int, SAMKDownload] = {}
        for cid in online:
            last_cts = []
            for j in range(num_chunks):
                cts = [uploads[c].client_point_cts[j][cid] for c in online]
                last_cts.append(sch.clients[cid].paillier.public.add_ciphertexts(cts))
            dl = SAMKDownload(client_id=cid, c0_sums=c0_sums,
                              points=plain_points, last_point_cts=last_cts,
                              online_ids=online, dim=uploads[cid].dim)
            dl.nbytes = sch.estimate_download_bytes(dl)
            downloads[cid] = dl

        # 只保留本轮下载包：上传后掉线者可在本轮内重连取回；跨轮不保留旧包
        self._download_cache = dict(downloads)
        dropped = sorted(int(d) for d in (dropouts or []))
        res = SAMKRoundResult(
            online_ids=online, dropouts=dropped, downloads=downloads,
            upload_bytes=sum(up.nbytes for up in uploads.values()),
            download_bytes=sum(dl.nbytes for dl in downloads.values()),
            agg_time=_time.time() - t0,
            stats={
                "online": len(online),
                "num_chunks": num_chunks,
                "paillier_packs_per_chunk": len(uploads[online[0]].server_point_cts[0]),
                "paillier_cts": sum(uploads[c].num_paillier_cts() for c in online),
            })
        self.last_result = res
        return res

    # ---------------- 下载包（含“上传后掉线重连”）----------------
    def fetch_download(self, client_id: int) -> SAMKDownload:
        """
        客户端取回上一轮的下载包。

        上传成功后掉线的客户端可在重连时调用（服务器缓存仍有效）；
        **未上传**的客户端只能看到 N-1 个明文点，无法插值，抛 SAMKAccessError。
        """
        cid = int(client_id)
        if cid not in self._download_cache:
            raise SAMKAccessError(
                f"客户端 {cid} 未上传本轮密文：只能获得 N-1 个点，"
                f"无法插值恢复 F(x)，因而不能解密聚合结果（论文 Proposition 1/3）")
        return self._download_cache[cid]

    def clear_round(self) -> None:
        self._download_cache.clear()


# =============================================================================
# 6. 门面：一轮 SAMK 安全聚合
# =============================================================================
class SAMKScheme:
    """
    SAMK 全流程门面（对应论文 Algorithm 1-5 的五阶段）。

    典型用法::

        sch = SAMKScheme(SAMKParams(n=1024, paillier_bits=512), num_clients=10)
        sch.setup()
        sch.client_upload(1, update_1)          # 加密上传
        res = sch.server.aggregate(uploads)     # 服务器聚合
        agg = sch.clients[1].decrypt_aggregate(res.downloads[1])

    ``num_clients`` 用于确定 Paillier 打包槽宽与明文上界（论文中的 n）。
    """

    def __init__(self, params: SAMKParams, num_clients: int, seed: Optional[int] = None):
        self.params = params
        self.num_clients = int(num_clients)
        if self.num_clients < 1:
            raise ValueError("num_clients 必须 >= 1")
        self.seed = int(params.seed if seed is None else seed)
        self.rng = np.random.default_rng(self.seed)
        self.bfv = BFVContext(BFVParams(n=params.n, t_bits=params.t_bits,
                                       eta=params.eta, seed=self.seed))

        # ---- Algorithm 1：自变量集合 X + Paillier 安全参数 ----
        spread = params.x_spread if params.x_spread > 0 else 4 * params.n
        if spread > self.bfv.q1:
            raise ValueError("x_spread 必须远小于 q1")
        xs = self.rng.choice(np.arange(1, spread + 1), size=params.n, replace=False)
        self.x_points = np.sort(xs).astype(np.int64)
        self.interp_q1 = LagrangeInterpolator(self.x_points, self.bfv.q1)
        self.interp_q2 = LagrangeInterpolator(self.x_points, self.bfv.q2)

        # Paillier 打包槽宽：容纳 n 个客户端的采样点之和（进位预留，图 3(b)）
        self.slot_bits = int((self.num_clients * (self.bfv.Q - 1)).bit_length())
        self.clients: Dict[int, SAMKClient] = {}
        self.server: Optional[SAMKServer] = None
        self._server_paillier: Optional[PaillierKeyPair] = None
        self._pp_broadcast = False

    # ---------------- Algorithm 2：KeyGen ----------------
    def register_client(self, client_id: int, bfv_keys: Optional[BFVKeyPair] = None,
                        paillier: Optional[PaillierKeyPair] = None) -> SAMKClient:
        """客户端独立生成 BFV + Paillier 密钥；Paillier 公钥加入广播表。"""
        cid = int(client_id)
        bfv_keys = bfv_keys or self.bfv.keygen()
        paillier = paillier or paillier_keygen(
            self.params.paillier_bits, self.rng, slot_bits=self.slot_bits)
        cli = SAMKClient(cid, self, bfv_keys, paillier)
        self.clients[cid] = cli
        return cli

    def server_keygen(self) -> PaillierKeyPair:
        """服务器生成自己的 Paillier 密钥（服务器没有 BFV 密钥）。"""
        self._server_paillier = paillier_keygen(
            self.params.paillier_bits, self.rng, slot_bits=self.slot_bits)
        self.server = SAMKServer(self, self._server_paillier)
        return self._server_paillier

    def setup(self, client_ids: Optional[Sequence[int]] = None) -> "SAMKScheme":
        """一键完成 Setup + KeyGen（本地仿真：所有实体在同一进程内）。"""
        ids = list(client_ids) if client_ids is not None else list(
            range(1, self.num_clients + 1))
        self.num_clients = len(ids)
        self.slot_bits = int((self.num_clients * (self.bfv.Q - 1)).bit_length())
        self.server_keygen()
        for cid in ids:
            self.register_client(cid)
        return self

    # ---------------- 便捷接口 ----------------
    @property
    def server_public_key(self) -> PaillierPublicKey:
        if self._server_paillier is None:
            self.server_keygen()
        return self._server_paillier.public

    @property
    def public_params(self) -> Dict:
        """PP = {pp, κ, X}（Algorithm 1 的公开输出）。"""
        return {
            "n": self.params.n, "t": self.bfv.t, "delta": self.bfv.delta,
            "q_bits": self.bfv.Q.bit_length(),
            "paillier_bits": self.params.paillier_bits,
            "slot_bits": self.slot_bits,
            "max_slots": self.server_public_key.max_slots,
            "scale": self.params.scale,
            "x_points": self.x_points.tolist(),
        }

    def client_upload(self, client_id: int, update: np.ndarray) -> SAMKUpload:
        return self.clients[int(client_id)].encrypt_update(update)

    def aggregate(self, uploads: Dict[int, SAMKUpload],
                  dropouts: Optional[Sequence[int]] = None) -> SAMKRoundResult:
        return self.server.aggregate(uploads, dropouts=dropouts)

    def client_decrypt(self, client_id: int, download: SAMKDownload) -> np.ndarray:
        return self.clients[int(client_id)].decrypt_aggregate(download)

    # ---------------- 正确性约束（论文的明文/噪声界）----------------
    def max_abs_quantized(self) -> int:
        """单客户端量化明文的安全上界：|Σ m| < t/2 按 num_clients 均摊。"""
        return int(self.bfv.t // 2 // max(1, self.num_clients))

    def check_bounds(self, updates: Sequence[np.ndarray]) -> Tuple[bool, str]:
        """检查 |Σ m_j| < t/2 与 |Σ noise| < Δ/2 是否能满足。"""
        scale = self.params.scale
        worst = max((int(np.max(np.abs(np.asarray(u, dtype=np.float64)))) for u in updates),
                    default=0.0)
        total = int(math.ceil(worst * scale)) * max(1, len(updates))
        if total >= self.bfv.t // 2:
            return False, (f"明文回绕风险：Σ|m| ≈ {total} ≥ t/2 = {self.bfv.t // 2}；"
                           f"请增大 t_bits 或降低 scale_bits")
        # 噪声上界（中心二项 eta，环维度 n，聚合客户端数 k）：
        #   noise ≈ e0 + e1·s - u·e，系数上界 ~ 6·eta·sqrt(2n/3)·2
        noise = 6.0 * self.params.eta * math.sqrt(2 * self.params.n / 3.0) * 2 * \
            math.sqrt(max(1, len(updates)))
        if noise >= self.bfv.delta / 2:
            return False, (f"噪声越界：σ_noise ≈ {noise:.0f} ≥ Δ/2 = {self.bfv.delta // 2}；"
                           f"请增大 t_bits 或减小环维度")
        return True, "ok"

    # ---------------- 通信量核算 ----------------
    def estimate_upload_bytes(self, up: SAMKUpload) -> int:
        q_bits = self.bfv.Q.bit_length()
        ring_bytes = self.params.n * q_bits // 8
        paillier = self.server_public_key.nbytes()
        n_server = sum(len(p) for p in up.server_point_cts)
        n_client = sum(len(p) for p in up.client_point_cts)
        return up.num_chunks * 2 * ring_bytes + (n_server + n_client) * paillier

    def estimate_download_bytes(self, dl: SAMKDownload) -> int:
        q_bits = self.bfv.Q.bit_length()
        ring_bytes = self.params.n * q_bits // 8
        point_bytes = q_bits // 8
        num_chunks = len(dl.c0_sums)
        # c0 聚合密文 + (N-1) 个明文点 + 1 条 Paillier 密文/块
        return num_chunks * (ring_bytes + (self.params.n - 1) * point_bytes +
                             self.server_public_key.nbytes())
