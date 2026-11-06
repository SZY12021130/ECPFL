"""
ESAFL ESHE 加密方案的纯 Python 复现（PUREPY 模式）
====================================================

对应 ESAFL 论文（arXiv:2305.08599）的 ESHE 结构：

  环 R_q = Z_q[X] / (X^n + 1)，n 为 2 的幂；明文模 p < q；p̃ 为常数多项式 p。

  KeyGen：
    - 每客户端加密密钥 s_i ← χ_s（小系数，本项目取 {-1,0,1}^n）
    - 共享解密密钥 s = [Σ_i s_i]_q（可信 AS 生成；PUREPY 为研究复现，
      全部 s_i 由本后端持有，等价于可信 AS 的角色）
  PRPG(t, B)：所有方由种子 B + 计数器 t 本地确定性再生公共多项式 a^t ∈ R_q。
    论文使用密码学 PRG 输出 bit-string 再编码；这里直接用 numpy
    SeedSequence 生成 [0,q) 均匀整数，结构等价但 **非 bit-compatible**。
  Enc：ct_i = [a^t · s_i + p̃ · e_i + m_i]_q，e_i ← χ_e（中心二项分布）
  Eval/聚合：C = Σ_i ct_i（逐系数加法，环上无标量乘法）
  Dec（one-shot）：M = [[C − a^t · s]_q]_p（系数级先 mod q 再 mod p，
    p·e 项自动消去；只要 |p·Σe_i + Σm_i| < Q/2 即精确恢复）

实现要点：
  - 环元素以 CRT 表示：Q = q1 · q2，q1/q2 为两个 31-bit NTT 友好素数
    （q_i ≡ 1 mod 2n）。点值域乘积 < 2^62，numpy int64 免溢出。
  - 乘法用 negacyclic NTT（ψ-扭曲的标准技巧，ψ 为 2n 次本原根）。
  - 无重缩放 / 重线性化 / 自举。精度条件：Σe_i 系数上界 ≪ p/2。
    参考官方 logq0=16；PUREPY 取 p = 2^40（默认）以容纳 bit-packing 编码值。

跨轮解密（ESAFL 预取）：
  每个密文携带其 mask 多项式（= a^t · s_i，聚合/减法时同步累加），
  因此任意跨轮累加密文 Δ 的解密 [[Δ − mask_Δ]_q]_p 自动实现论文中的
  [[ct − Δ_a·s]_q]_p（Δ_a = Σ(a^(r_j) − a^(r_(j-1)))），无需额外轮次信息。

已知差异（相对论文 / 官方实现）：
  1. numpy PRG 非 bit-compatible（见上）。
  2. 环上无标量乘法，加权平均在解密后的明文（量化整数/浮点）域完成。
  3. 打包直接复用 ckks_fed.packing.ESAFLPacking（量化后的整数值直接作为
     多项式系数），不实现论文的 EP 打包。
  4. 全参与约束：论文要求未采样客户端上传 Enc(0)；PUREPY 中服务器持有
     每个密文的 mask（可信 AS 模拟），直接按参与客户端解密，等价处理。
"""

from dataclasses import dataclass
import numpy as np
from typing import Dict, List, Optional

# 31-bit 内确定性 Miller-Rabin 基（覆盖 < 3,215,031,751）
_MR_BASES = (2, 3, 5, 7)


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    for b in _MR_BASES:
        if n % b == 0:
            return n == b
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in _MR_BASES:
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


def _find_ntt_prime(two_n: int, bit_length: int = 31) -> int:
    """搜索最小的 q = k·2n + 1，且 q 为素数、q < 2^bit_length。"""
    upper = (1 << bit_length) - 1
    k = upper // two_n
    while k > 0:
        q = k * two_n + 1
        if _is_prime(q):
            return q
        k -= 1
    raise RuntimeError(f"找不到 {bit_length}-bit NTT 友好素数 (2n={two_n})")


def _primitive_2n_root(q: int, two_n: int) -> int:
    """求模 q 下的 2n 次本原根（q-1 = 2n·k）。"""
    k = (q - 1) // two_n
    h = 2
    while True:
        psi = pow(h, k, q)
        if pow(psi, two_n, q) == 1 and pow(psi, two_n // 2, q) == q - 1:
            return psi
        h += 1


class RingArray:
    """R_Q 元素，CRT 表示：r1 = coeffs mod q1，r2 = coeffs mod q2（int64 数组）。"""

    __slots__ = ("r1", "r2", "ctx")

    def __init__(self, ctx: "RingContext", r1: np.ndarray, r2: np.ndarray):
        self.ctx = ctx
        self.r1 = np.mod(r1, ctx.q1).astype(np.int64)
        self.r2 = np.mod(r2, ctx.q2).astype(np.int64)

    # ---------------- 基本运算 ----------------
    def add(self, other: "RingArray") -> "RingArray":
        ctx = self.ctx
        return RingArray(ctx, (self.r1 + other.r1) % ctx.q1, (self.r2 + other.r2) % ctx.q2)

    def sub(self, other: "RingArray") -> "RingArray":
        ctx = self.ctx
        return RingArray(ctx, (self.r1 - other.r1) % ctx.q1, (self.r2 - other.r2) % ctx.q2)

    def neg(self) -> "RingArray":
        ctx = self.ctx
        return RingArray(ctx, (-self.r1) % ctx.q1, (-self.r2) % ctx.q2)

    def copy(self) -> "RingArray":
        return RingArray(self.ctx, self.r1.copy(), self.r2.copy())

    def mul(self, other: "RingArray") -> "RingArray":
        # 实现见模块级 _ring_mul（需先定义 RingContext）
        return _ring_mul(self, other)

    def scalar_mul(self, c: int) -> "RingArray":
        # 先取模再乘，避免 int64 溢出（c 可达 2^60 量级，如拉格朗日系数）
        ctx = self.ctx
        c1, c2 = int(c) % ctx.q1, int(c) % ctx.q2
        return RingArray(ctx, (self.r1 * c1) % ctx.q1, (self.r2 * c2) % ctx.q2)

    def nbytes(self) -> int:
        return int(self.r1.nbytes + self.r2.nbytes)

    def __eq__(self, other) -> bool:
        return (isinstance(other, RingArray)
                and np.array_equal(self.r1, other.r1)
                and np.array_equal(self.r2, other.r2))


class RingContext:
    """环上下文：模数 Q = q1·q2、NTT 预计算表、negacyclic 卷积。"""

    def __init__(self, n: int, prime_bits: int = 31):
        if n < 2 or (n & (n - 1)) != 0:
            raise ValueError("n 必须为 2 的幂")
        self.n = n
        two_n = 2 * n
        self.q1 = _find_ntt_prime(two_n, prime_bits)
        self.q2 = _find_ntt_prime(two_n, prime_bits - 1)
        # 保证 q1 != q2（n 较小时两个搜索结果可能相同）
        if self.q2 == self.q1:
            self.q2 = _find_ntt_prime(two_n, prime_bits - 2)
        self.Q = self.q1 * self.q2  # ≈ 2^(2*prime_bits-1)

        self.psi1 = _primitive_2n_root(self.q1, two_n)
        self.psi2 = _primitive_2n_root(self.q2, two_n)
        self.zeta1 = pow(self.psi1, 2, self.q1)  # n 次本原根
        self.zeta2 = pow(self.psi2, 2, self.q2)

        # 预计算正向 NTT twiddle：levels 从 half=1 开始
        self._fw1 = self._build_twiddles(self.zeta1, self.q1)
        self._fw2 = self._build_twiddles(self.zeta2, self.q2)
        self._bw1 = self._build_twiddles(pow(self.zeta1, self.q1 - 2, self.q1), self.q1)
        self._bw2 = self._build_twiddles(pow(self.zeta2, self.q2 - 2, self.q2), self.q2)
        # ψ^j 扭曲因子及其逆
        j = np.arange(n, dtype=np.int64)
        self._twist1 = np.array([pow(self.psi1, int(x), self.q1) for x in j], dtype=np.int64)
        self._twist2 = np.array([pow(self.psi2, int(x), self.q2) for x in j], dtype=np.int64)
        self._untwist1 = np.array(
            [pow(pow(self.psi1, int(x), self.q1), self.q1 - 2, self.q1) for x in j],
            dtype=np.int64)
        self._untwist2 = np.array(
            [pow(pow(self.psi2, int(x), self.q2), self.q2 - 2, self.q2) for x in j],
            dtype=np.int64)
        self._ninv1 = pow(n % self.q1, self.q1 - 2, self.q1)
        self._ninv2 = pow(n % self.q2, self.q2 - 2, self.q2)
        # 位反转置换索引
        bits = n.bit_length() - 1
        self._bitrev = np.array(
            [int(f"{i:0{bits}b}"[::-1], 2) for i in range(n)], dtype=np.int64)

    # ---------------- NTT ----------------
    def _build_twiddles(self, zeta: int, q: int) -> List[np.ndarray]:
        """levels[ell] = [zeta^{k·n/2^(ell+1)} for k in range(2^ell)]"""
        levels = []
        length = 2
        while length <= self.n:
            wlen = pow(zeta, self.n // length, q)
            half = length // 2
            levels.append(np.array(
                [pow(wlen, k, q) for k in range(half)], dtype=np.int64))
            length *= 2
        return levels

    def _ntt_core(self, a: np.ndarray, twiddles: List[np.ndarray],
                  bitrev: np.ndarray, q: int) -> np.ndarray:
        x = a[bitrev]
        n = self.n
        length = 2
        ell = 0
        while length <= n:
            half = length // 2
            blocks = x.reshape(-1, length)
            w = twiddles[ell]
            u = blocks[:, :half].copy()
            v = (blocks[:, half:] * w) % q
            blocks[:, :half] = (u + v) % q
            blocks[:, half:] = (u - v) % q
            length *= 2
            ell += 1
        return x

    def _fwd(self, a: np.ndarray, twist: np.ndarray,
             twiddles: List[np.ndarray], q: int) -> np.ndarray:
        return self._ntt_core((a * twist) % q, twiddles, self._bitrev, q)

    def _inv(self, A: np.ndarray, untwist: np.ndarray,
             twiddles: List[np.ndarray], q: int, ninv: int) -> np.ndarray:
        x = self._ntt_core(A, twiddles, self._bitrev, q)
        return (x * untwist % q) * ninv % q

    # 便捷构造
    def zeros(self) -> RingArray:
        return RingArray(self, np.zeros(self.n, dtype=np.int64),
                         np.zeros(self.n, dtype=np.int64))

    def from_ints(self, coeffs: np.ndarray) -> RingArray:
        """从整数系数（可为负）构造环元素。"""
        c = np.asarray(coeffs, dtype=np.int64)
        return RingArray(self, c % self.q1, c % self.q2)

    def mul_polys(self, a: np.ndarray, b: np.ndarray,
                  twist: np.ndarray, untwist: np.ndarray,
                  fw, bw, q: int, ninv: int) -> np.ndarray:
        """negacyclic 卷积 mod q（NTT 加速），供 RingArray.mul 使用。"""
        A = self._fwd(a, twist, fw, q)
        B = self._fwd(b, twist, fw, q)
        return self._inv((A * B) % q, untwist, bw, q, ninv)


def _ring_mul(ring: RingArray, other: RingArray) -> RingArray:
    ctx = ring.ctx
    a1 = ctx.mul_polys(ring.r1, other.r1, ctx._twist1, ctx._untwist1,
                       ctx._fw1, ctx._bw1, ctx.q1, ctx._ninv1)
    a2 = ctx.mul_polys(ring.r2, other.r2, ctx._twist2, ctx._untwist2,
                       ctx._fw2, ctx._bw2, ctx.q2, ctx._ninv2)
    return RingArray(ctx, a1, a2)


def naive_negacyclic_mul(a: np.ndarray, b: np.ndarray, modulus: int) -> np.ndarray:
    """朴素 negacyclic 卷积参考实现（测试对照用），O(n^2)。"""
    n = len(a)
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    # 用 Python 大整数精确计算再取模，避免任何溢出风险
    full = np.zeros(2 * n - 1, dtype=object)
    for i in range(n):
        for j in range(n):
            full[i + j] += int(a[i]) * int(b[j])
    res = np.zeros(n, dtype=object)
    for k in range(2 * n - 1):
        idx = k % n
        sign = -1 if k >= n else 1
        res[idx] = (res[idx] + sign * full[k]) % modulus
    return np.array(res, dtype=np.int64)


@dataclass
class ESHEParameters:
    """ESHE 方案参数。"""
    n: int = 2048            # 环维度（= packing slot_count）
    logq: int = 62           # 密文模数位宽（实际 Q=q1·q2 ≈ 2^61/2^62）
    logp: int = 40           # 明文模数 p = 2^logp（须 > 编码值上界且留噪声余量）
    eta: int = 4             # 噪声中心二项分布参数（χ_e）
    key_hamming: int = 0     # s_i 的汉明重量上限（0 = 不限制，取 {-1,0,1}^n）

    @property
    def p(self) -> int:
        return 1 << self.logp


class ESHEPurePyCiphertext:
    """
    ESHE 密文（PUREPY）。

    coeffs : [a^t · s_i + p·e_i + m]_Q
    mask   : a^t · s_i（聚合时相加、减法时相减；跨轮累加自动实现 Δ_a·s）
    counter: PRPG 计数器 t（诊断/日志用，解密只依赖 mask）

    解密：m = [[coeffs − mask]_Q]_p（系数级先 mod Q 再 mod p）。
    """

    __slots__ = ("coeffs", "mask", "counter")

    def __init__(self, coeffs: RingArray, mask: RingArray, counter: int):
        self.coeffs = coeffs
        self.mask = mask
        self.counter = counter

    def __add__(self, other: "ESHEPurePyCiphertext") -> "ESHEPurePyCiphertext":
        return aggregate_ciphertexts([self, other])

    def __sub__(self, other: "ESHEPurePyCiphertext") -> "ESHEPurePyCiphertext":
        return subtract_ciphertexts(self, other)

    def nbytes(self) -> int:
        return int(self.coeffs.nbytes() + self.mask.nbytes())

    def coeffs_nbytes(self) -> int:
        """
        线上密文大小：仅计 coeffs 多项式的紧凑系数表示。
        mask = a^t·s_i 中 a^t 由 PRPG(t, B) 公开再生、解密方持 s_i，
        因此 mask 无需传输（聚合密文同理，仅 coeffs 求和结果需下发）。

        大小 = n × log₂Q / 8 字节（每系数 log₂Q bit，与 ECPFL 的
        ct_coeff_bytes = n × Q.bit_length() // 8 完全同一口径）。
        注：CRT 双 int64 存储（16 B/系数）仅为内存表示，非线上大小。
        """
        return int(self.coeffs.ctx.n * self.coeffs.ctx.Q.bit_length() // 8)


class PRPG:
    """
    伪随机多项式生成器：PRPG(t, B) → a^t ∈ R_Q。

    由种子 B + 计数器 t 本地确定性再生（所有方可独立重构）。
    论文使用密码学 PRG（bit 输出再编码为多项式）；这里用 numpy
    SeedSequence 直接生成 [0,q) 均匀整数，结构等价但非 bit-compatible。
    """

    def __init__(self, seed: int, ring: RingContext):
        self.seed = int(seed)
        self.ring = ring
        self._cache: Dict[int, RingArray] = {}

    def generate(self, counter: int) -> RingArray:
        counter = int(counter)
        if counter in self._cache:
            return self._cache[counter]
        ss = np.random.SeedSequence([self.seed & 0xFFFFFFFF, counter & 0xFFFFFFFF])
        child1, child2 = ss.spawn(2)
        r1 = np.random.default_rng(child1).integers(
            0, self.ring.q1, self.ring.n, dtype=np.int64)
        r2 = np.random.default_rng(child2).integers(
            0, self.ring.q2, self.ring.n, dtype=np.int64)
        a = RingArray(self.ring, r1, r2)
        self._cache[counter] = a
        return a


def aggregate_ciphertexts(cts: List[ESHEPurePyCiphertext]) -> ESHEPurePyCiphertext:
    """Eval：逐系数加法聚合 C = Σ_i ct_i。"""
    if not cts:
        raise ValueError("密文列表为空")
    coeffs = cts[0].coeffs.copy()
    mask = cts[0].mask.copy()
    counter = cts[0].counter
    for ct in cts[1:]:
        if ct.counter != counter:
            raise ValueError(
                f"聚合密文计数器不一致: {ct.counter} != {counter}"
                "（跨轮累加应使用 subtract_ciphertexts/密文减法链）")
        coeffs = coeffs.add(ct.coeffs)
        mask = mask.add(ct.mask)
    return ESHEPurePyCiphertext(coeffs, mask, counter)


def subtract_ciphertexts(c1: ESHEPurePyCiphertext,
                         c2: ESHEPurePyCiphertext) -> ESHEPurePyCiphertext:
    """同态减法 δ = c1 − c2（mask 同步相减，即论文 Δ_a·s 的累加形式）。"""
    return ESHEPurePyCiphertext(
        c1.coeffs.sub(c2.coeffs),
        c1.mask.sub(c2.mask),
        c1.counter,
    )


class PurePyESHE:
    """
    ESHE 方案后端（PUREPY 模式）。

    可信 AS 角色：持有全部客户端 s_i 与共享种子 B，负责生成 s = Σ s_i。
    客户端保密 s_i 的语义在模拟中由 client_id 级别的 encrypt 接口体现。

    加权平均说明：环上无标量乘法（与论文一致），FedAvg 权重在解密后的
    明文域应用（见 crypto.py 的 PUREPY 聚合分支）。
    """

    def __init__(self, n: int = 2048, seed: int = 42,
                 logp: int = 40, eta: int = 4,
                 encoding: str = "ep", delta_scale: int = 1 << 20):
        """
        Args:
            encoding:  "ep"   = 论文 EP 位打包（ct = a·s_i + p·e + m，mod p 解密；
                                m ∈ [0, p) 为位域编码整数，配合 ESHEEPPacking）
                       "fixed" = CKKS 式定点编码变体（ct = a·s_i + e + m，m 可为负；
                                无 p̃ 噪声项、无 mod p，解密 = (ct − mask)/Δ）
            delta_scale: fixed 模式的定点缩放 Δ（x̂ = round(x·Δ)/Δ）
        """
        if encoding not in ("ep", "fixed"):
            raise ValueError(f"未知 encoding: {encoding}（可选 'ep' | 'fixed'）")
        self.encoding = encoding
        self.delta = int(delta_scale)
        self.params = ESHEParameters(n=n, logp=logp, eta=eta)
        self.ring = RingContext(n)
        self.prpg = PRPG(seed, self.ring)
        self._client_secrets: Dict[int, RingArray] = {}
        self._secret_keys: Dict[int, np.ndarray] = {}
        self.s_total: Optional[RingArray] = None

    # ---------------- 参数 ----------------
    @property
    def n(self) -> int:
        return self.params.n

    @property
    def p(self) -> int:
        return self.params.p

    @property
    def Q(self) -> int:
        return self.ring.Q

    # ---------------- KeyGen ----------------
    def register_client(self, client_id: int) -> None:
        """为客户端生成加密密钥 s_i ← {-1,0,1}^n，并更新 s = Σ s_i。"""
        client_id = int(client_id)
        if client_id in self._secret_keys:
            return
        rng = np.random.default_rng(
            np.random.SeedSequence([0xE5AF, client_id & 0xFFFFFFFF]))
        s = rng.integers(0, 3, self.n, dtype=np.int64) - 1  # {-1,0,1}
        if self.params.key_hamming > 0:
            # 限制非零系数个数（ ternary 稀疏密钥）
            idx = rng.choice(self.n, self.params.key_hamming, replace=False)
            s = np.zeros(self.n, dtype=np.int64)
            s[idx] = rng.integers(0, 3, self.params.key_hamming, dtype=np.int64) - 1
        self._secret_keys[client_id] = s
        self._client_secrets[client_id] = self.ring.from_ints(s)
        self._refresh_s_total()

    def _refresh_s_total(self):
        s = self.ring.zeros()
        for si in self._client_secrets.values():
            s = s.add(si)
        self.s_total = s

    def client_ids(self) -> List[int]:
        return sorted(self._secret_keys.keys())

    # ---------------- 加密 ----------------
    def _sample_noise(self) -> np.ndarray:
        """χ_e：中心二项分布（η 次 Bernoulli(1/2) 之差）。"""
        eta = self.params.eta
        rng = np.random.default_rng()
        b1 = rng.binomial(eta, 0.5, self.n)
        b2 = rng.binomial(eta, 0.5, self.n)
        return (b1 - b2).astype(np.int64)

    def encrypt_chunk(self, client_id: int, message: np.ndarray,
                      counter: int) -> ESHEPurePyCiphertext:
        """
        Enc：ct = [a^t · s_i + p·e + m]_Q。

        Args:
            client_id: 客户端 ID（自动注册密钥）
            message:   明文多项式系数，须满足 0 <= m < p
            counter:   PRPG 计数器 t（通常取轮次号）
        """
        self.register_client(client_id)
        m = np.asarray(message, dtype=np.int64).reshape(-1)
        if m.shape[0] != self.n:
            raise ValueError(f"明文长度 {m.shape[0]} != 环维度 {self.n}")
        if m.min() < 0 or m.max() >= self.p:
            raise ValueError(
                f"明文系数须在 [0, p) 内 (p=2^{self.params.logp})，"
                f"实际 [{m.min()}, {m.max()}]。请检查 packing 编码位宽。")
        ring = self.ring
        a = self.prpg.generate(counter)
        s_i = self._client_secrets[client_id]
        e = self._sample_noise()
        # p̃ 为常数多项式（仅 X^0 系数 = p，见方案文档）：
        # 稠密 p̃ 的 negacyclic 卷积 p̃·e 系数 ~ p·n·eta，会随机超出 Q/2 触发回绕
        _pc = np.zeros(self.n, dtype=np.int64); _pc[0] = self.p
        p_const = ring.from_ints(_pc)
        coeffs = a.mul(s_i).add(p_const.mul(ring.from_ints(e))).add(
            ring.from_ints(m))
        mask = a.mul(s_i)
        return ESHEPurePyCiphertext(coeffs, mask, int(counter))

    def encrypt_chunk_fixed(self, client_id: int, values: np.ndarray,
                            counter: int) -> ESHEPurePyCiphertext:
        """
        fixed 编码 Enc：ct = [a^t · s_i + e + m]_Q，m = round(x·Δ)（可为负）。

        与论文 EP 模式的差异：噪声项为系数级小整数 e（非 p̃·e），明文为有符号
        定点整数；解密不取 mod p。精度：单客户端误差 ≤ eta/Δ。
        越界检查：|m| 须 ≪ Q/2（含聚合噪声余量，取 |m| < Q/8）。
        """
        if self.encoding != "fixed":
            raise RuntimeError("encrypt_chunk_fixed 仅在 encoding='fixed' 下可用")
        self.register_client(client_id)
        x = np.asarray(values, dtype=np.float64).reshape(-1)
        if x.shape[0] != self.n:
            raise ValueError(f"明文长度 {x.shape[0]} != 环维度 {self.n}")
        bound = self.Q // 8
        x_bound = bound / self.delta
        if x.min() < -x_bound or x.max() >= x_bound:
            raise ValueError(
                f"fixed 定点明文越界 [{x.min():.6g}, {x.max():.6g}]，要求 |x| < "
                f"Q/(8Δ) ≈ {x_bound:.3g}；请减小 esafl.delta_scale 或裁剪梯度")
        m = np.round(x * self.delta).astype(np.int64)
        if m.min() < -bound or m.max() >= bound:
            raise ValueError(
                f"fixed 定点明文越界 [{m.min()}, {m.max()}]，要求 |m| < Q/8 = 2^"
                f"{(self.Q.bit_length() - 4)}；请减小 esafl.delta_scale 或裁剪梯度")
        ring = self.ring
        a = self.prpg.generate(counter)
        s_i = self._client_secrets[client_id]
        e = self._sample_noise()
        coeffs = a.mul(s_i).add(ring.from_ints(e)).add(ring.from_ints(m))
        mask = a.mul(s_i)
        return ESHEPurePyCiphertext(coeffs, mask, int(counter))

    def decrypt_fixed_ints(self, ct: ESHEPurePyCiphertext) -> np.ndarray:
        """fixed 解密（整数级）：y = [ct.coeffs − ct.mask]_Q（中心化，可为负）。"""
        t = ct.coeffs.sub(ct.mask)
        q1, q2 = self.ring.q1, self.ring.q2
        q1_inv = pow(q1 % q2, q2 - 2, q2)
        c1 = t.r1.astype(object)
        c2 = t.r2.astype(object)
        k = ((c2 - c1) % q2 * q1_inv) % q2
        x = (c1 + q1 * k)
        half = self.Q // 2
        x = np.where(x > half, x - self.Q, x)
        return np.array(x, dtype=np.int64)

    def decrypt_fixed(self, ct: ESHEPurePyCiphertext) -> np.ndarray:
        """fixed 解密（浮点级）：x̂ = [ct − mask]_Q / Δ，误差 ≤ eta/Δ（聚合 ≤ N·eta/Δ）。"""
        return self.decrypt_fixed_ints(ct).astype(np.float64) / self.delta

    def encrypt_zero(self, client_id: int, counter: int) -> ESHEPurePyCiphertext:
        """Enc(0)：未采样客户端的全参与补齐密文（ESHE-PS 修正）。"""
        return self.encrypt_chunk(client_id, np.zeros(self.n, dtype=np.int64), counter)

    def encrypt_server(self, message: np.ndarray, counter: int = 0,
                       noise: bool = False) -> ESHEPurePyCiphertext:
        """
        服务器（AS）侧加密：mask = a^t · s（s = Σ s_i），e 可选（默认 0）。
        用于加密全局状态 / 聚合结果，客户端无需知晓 s。
        """
        m = np.asarray(message, dtype=np.int64).reshape(-1)
        if m.shape[0] != self.n:
            raise ValueError(f"明文长度 {m.shape[0]} != 环维度 {self.n}")
        if m.min() < 0 or m.max() >= self.p:
            raise ValueError(f"明文系数须在 [0, p) 内，实际 [{m.min()}, {m.max()}]")
        ring = self.ring
        a = self.prpg.generate(counter)
        mask = self.ring.zeros() if self.s_total is None else a.mul(self.s_total)
        coeffs = ring.from_ints(m).add(mask)
        if noise:
            # p̃ 为常数多项式（仅 X^0 系数 = p，见方案文档）：
            # 稠密 p̃ 的 negacyclic 卷积 p̃·e 系数 ~ p·n·eta，会随机超出 Q/2 触发回绕
            _pc = np.zeros(self.n, dtype=np.int64); _pc[0] = self.p
            p_const = ring.from_ints(_pc)
            coeffs = coeffs.add(p_const.mul(ring.from_ints(self._sample_noise())))
        return ESHEPurePyCiphertext(coeffs, mask, int(counter))

    # ---------------- Eval ----------------
    @staticmethod
    def aggregate(cts: List[ESHEPurePyCiphertext]) -> ESHEPurePyCiphertext:
        return aggregate_ciphertexts(cts)

    @staticmethod
    def subtract(c1: ESHEPurePyCiphertext,
                 c2: ESHEPurePyCiphertext) -> ESHEPurePyCiphertext:
        return subtract_ciphertexts(c1, c2)

    # ---------------- Dec ----------------
    def decrypt(self, ct: ESHEPurePyCiphertext) -> np.ndarray:
        """
        One-shot 解密：M = [[ct.coeffs − ct.mask]_Q]_p。

        返回系数数组（int64，值域 [0, p)）。当 |p·Σe_i + Σm_i| < Q/2 时
        精确恢复（无 CKKS 式噪声误差）。
        """
        t = ct.coeffs.sub(ct.mask)  # mod Q（CRT 表示，分量在 [0, q_i)）
        # CRT 重建到 [0, Q) 后中心化到 (−Q/2, Q/2]，再 mod p
        q1, q2 = self.ring.q1, self.ring.q2
        q1_inv = pow(q1 % q2, q2 - 2, q2)
        c1 = t.r1.astype(object)
        c2 = t.r2.astype(object)
        k = ((c2 - c1) % q2 * q1_inv) % q2
        x = (c1 + q1 * k)  # ∈ [0, Q)
        half = self.Q // 2
        x = np.where(x > half, x - self.Q, x)
        return np.array(x % self.p, dtype=np.int64)

    # ---------------- 兼容性接口（对齐 esafl_eshe.ESHEManager 风格）----------------
    def encrypt(self, client_id: int, values: List[float], counter: int = 0) -> ESHEPurePyCiphertext:
        """便捷接口：将整数编码 chunk（float 表示的精确整数）加密为密文。"""
        m = np.round(np.asarray(values, dtype=np.float64)).astype(np.int64)
        return self.encrypt_chunk(client_id, m, counter)

    def decode(self, ct_or_cts, client_indices=None) -> np.ndarray:
        """解密单个聚合密文并返回系数数组（float，调试用）。"""
        if isinstance(ct_or_cts, list):
            ct = aggregate_ciphertexts(ct_or_cts)
        else:
            ct = ct_or_cts
        return self.decrypt(ct).astype(np.float64)
