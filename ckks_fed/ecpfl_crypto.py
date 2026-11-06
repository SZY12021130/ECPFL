# -*- coding: utf-8 -*-
"""
ECPFL-Lite（scheme/ECPFL-Lite公式推导及答疑.md）密码学核心 — ESP + ECP 纯 Python 实现
================================================================================

复用 ckks_fed/eshe.py 的 RingContext（CRT 双素数 R_Q、negacyclic NTT）与 PRPG。

**Lite 化简（相对 V17 的关键差异）**：KGC 不再为每个客户端采样个体密钥 s_i
并构造 N 个 Shamir 多项式（O(N^2) 份额矩阵），而是**直接对全局密钥 S 做一次
Shamir 分片**：

  Phase 0  KGC  采样 S ← U(R_q)；构造 **1 个 τ 阶**全局多项式 F_S（F_S(0)=S，
           重构需 τ+1 个份额）与 **1 个 (τ−1) 阶**零多项式 Z（Z(0)=0）；
           求值 S_i = F_S(i)、z_i = Z(i) 后仅向客户端 i 发送 3 个环元素 + 2 种子：
               K_i^Lite = (S, S_i, z_i, σ_a, σ_b)      —— 单客户端存储 3×64KB = 192KB
           KGC 全程仅 2 次多项式求值，计算 O(N·τ·n)、内存 O(τ·n)、分发 O(N·n)，
           随后永久离线。任意 |A| ≥ τ+1 子集满足 Σλ_i S_i = S、Σλ_i z_i = 0。

  Phase 1  ESP-Vote / ESP-Tally（式 9/10，与 V17 相同）：a_0·λ_i z_i 盲化投票。

  Phase 2  ESP-Enc（Lite 有效密钥，仅 1 次环乘 + 1 次标量乘）：
               s̃_{i,j} = λ_i·(S_i + b_j·z_i)，  b_j = PRPG(σ_b, t‖j‖0)
           b_j z_i 项为逐包随机化：防止合谋者用公共 a_{j1},a_{j2} 交叉相消
           解出 S_i（跨包/跨轮消元攻击）。

  Phase 3  ESP-Comp / ESP-Agg：掉线时补发差值密文 δ = a_j·κ + p̃ê，
               κ = ŝ − s̃ = (λ̂−λ)S_i + (λ̂b̂ − λb)z_i，  b̂ = PRPG(σ_b, t‖j‖1)
           与原密文相加后旧 λ 项正负对消，新集合下 Σλ̂_i(S_i + b̂ z_i) = S。

  Phase 4  ECP 跨轮预取与一步本地解密（式 16/17，与 V17 相同）：
           Dec(A, S, C) = [[C − A·S]_q]_p，无任何解密份额上传。

参数（默认）：n=4096（Q≈2^60）、p̃=p=2^50、Δ=2^20、η=4。
无回绕条件（启动断言）：K·max|m| < p/2 且 p̃·K·η + K·max|m| < Q/2。
"""

import numpy as np
from typing import Dict, List, Optional, Tuple

from ckks_fed.eshe import (
    RingContext, RingArray, PRPG, ESHEPurePyCiphertext,
)

# 域分离编码：a_j^(t) = PRPG(σ_a, t·10^6 + j)，j ≥ 1；a_0^(t) = PRPG(σ_b, t·10^6)
# b_j^(t) = PRPG(σ_b, t·10^6 + 2j)；掉线补偿 b̂_j^(t) = PRPG(σ_b, t·10^6 + 2j + 1)
PRPG_DOMAIN_MULT = 10 ** 6


def _sample_uniform_ring(ring: RingContext, rng: np.random.Generator) -> RingArray:
    """r ← U(R_q)：均匀随机环元素。"""
    r1 = rng.integers(0, ring.q1, ring.n, dtype=np.int64)
    r2 = rng.integers(0, ring.q2, ring.n, dtype=np.int64)
    return RingArray(ring, r1, r2)


def _sample_noise(n: int, eta: int) -> np.ndarray:
    """χ_e：中心二项分布（系数 ∈ [−eta, eta]）。"""
    rng = np.random.default_rng()
    b1 = rng.binomial(eta, 0.5, n)
    b2 = rng.binomial(eta, 0.5, n)
    return (b1 - b2).astype(np.int64)


def lagrange_coeffs(S_set: List[int], Q: int) -> Dict[int, int]:
    """
    常数评估点 α_i = i 的拉格朗日插值系数（式 D2.1）：
        λ_i = Π_{u≠i} (−u)·(i−u)^{-1} mod q   （整数模逆，常数多项式）
    满足 Σ_{i∈S_set} λ_i·F(i) = F(0)（对任意 deg F < |S_set| 成立）。
    """
    S_set = sorted(int(i) for i in S_set)
    if len(S_set) < 2:
        raise ValueError("拉格朗日插值至少需要 2 个评估点")
    out = {}
    for i in S_set:
        num, den = 1, 1
        for u in S_set:
            if u == i:
                continue
            num = (num * (-u)) % Q
            den = (den * (i - u)) % Q
        out[i] = int((num * pow(den, -1, Q)) % Q)
    return out


def _eval_poly(coeffs: List[RingArray], x: int) -> RingArray:
    """Horner 求值：F(x) = f_0 + x(f_1 + x(...))，x 为整数常量（环上乘 int）。"""
    acc = coeffs[-1].copy()
    for c in reversed(coeffs[:-1]):
        acc = acc.scalar_mul(x).add(c)
    return acc


class KGC:
    """
    可信密钥生成中心（Phase 0，单机模拟）—— ECPFL-Lite 版。

    仅生成 2 个 Shamir 多项式（τ 阶 F_S 与 (τ−1) 阶 Z），对每个客户端求值并
    分发 (S, S_i, z_i, σ_a, σ_b) 共 3 个环元素 + 2 个种子，随后永久离线。
    计算 O(N·τ·n)、内存 O(τ·n)、分发总量 O(N·n)。
    """

    def __init__(self, n: int = 4096, num_clients: int = 25, tau: int = 3,
                 seed: int = 42, logp: int = 50, delta: int = 1 << 20,
                 eta: int = 4):
        if not (2 <= tau + 1 <= num_clients):
            raise ValueError(f"须满足 τ+1 ≤ N（F_S 为 τ 阶，重构需 τ+1 份）："
                             f"τ={tau} N={num_clients}")
        self.n, self.N, self.tau = n, num_clients, tau
        self.logp, self.p = logp, 1 << logp
        self.delta, self.eta = int(delta), eta
        self.ring = RingContext(n)
        self.Q = self.ring.Q

        rng = np.random.default_rng(seed)
        # 全局聚合解密密钥 S ← U(R_q)（Lite：直接采样，不再分解为 Σs_i）
        self.S = _sample_uniform_ring(self.ring, rng)
        # F_S：τ 阶（τ 个随机系数 + 常数项 S），F_S(0) = S
        self._fs_coeffs = [self.S] + [
            _sample_uniform_ring(self.ring, rng) for _ in range(tau)]
        # Z：(τ−1) 阶零多项式，Z(0) = 0
        self._z_coeffs = [self.ring.zeros()] + [
            _sample_uniform_ring(self.ring, rng) for _ in range(tau - 1)]
        # PRPG 种子（σ_a 派生 a_j 公开再生；σ_b 派生 b_j 盲化乘子，对服务器保密）
        self.sigma_a = int(rng.integers(0, 2 ** 31))
        self.sigma_b = int(rng.integers(0, 2 ** 31))

    # ---------------- Phase 0 分发 ----------------
    def distribute(self) -> Dict[int, dict]:
        """向每个客户端 i 分发 K_i^Lite = (S, S_i, z_i, σ_a, σ_b)。

        求值分块向量化：系数 (τ, n) × 幂表 (B, τ) → B 个客户端的份额行，
        每块 O(B·τ·n)，总计 O(N·τ·n)，峰值内存 O(B·n)。"""
        block = 256
        out: Dict[int, dict] = {}
        idx_all = np.arange(1, self.N + 1, dtype=np.int64)
        for s in range(0, self.N, block):
            e = min(s + block, self.N)
            ii = idx_all[s:e]
            vals: Dict[str, List[RingArray]] = {'fs': [], 'z': []}
            for key, coeffs in (('fs', self._fs_coeffs), ('z', self._z_coeffs)):
                deg = len(coeffs) - 1
                rows = []
                for prime, q in (('r1', self.ring.q1), ('r2', self.ring.q2)):
                    c = np.stack([getattr(p, prime) for p in coeffs])          # (deg+1, n)
                    P = np.stack([np.mod(ii ** j, q) for j in range(deg + 1)], axis=1)
                    rows.append(np.einsum('ij,jn->in', P, c) % q)              # (B, n)
                vals[key] = [RingArray(self.ring, r1, r2)
                             for r1, r2 in zip(rows[0], rows[1])]
            for b, i in enumerate(range(s + 1, e + 1)):
                out[i] = {
                    'client_id': i,
                    'S': self.S,
                    'S_i': vals['fs'][b],
                    'z_i': vals['z'][b],
                    'sigma_a': self.sigma_a,
                    'sigma_b': self.sigma_b,
                }
        return out

    # ---------------- PRPG 域分离 ----------------
    def prpg_a(self, t: int, j: int) -> RingArray:
        """a_j^(t) = PRPG(σ_a, t·10^6 + j)，j ≥ 1。"""
        return PRPG(self.sigma_a, self.ring).generate(t * PRPG_DOMAIN_MULT + j)

    def prpg_b(self, t: int, j: int) -> RingArray:
        """b_j^(t) = PRPG(σ_b, t·10^6 + 2j)：包盲化乘子（上传阶段）。"""
        return PRPG(self.sigma_b, self.ring).generate(t * PRPG_DOMAIN_MULT + 2 * j)

    def prpg_bhat(self, t: int, j: int) -> RingArray:
        """b̂_j^(t) = PRPG(σ_b, t·10^6 + 2j + 1)：掉线补偿新鲜盲化乘子。"""
        return PRPG(self.sigma_b, self.ring).generate(t * PRPG_DOMAIN_MULT + 2 * j + 1)

    def prpg_a0(self, t: int) -> RingArray:
        """a_0^(t) = PRPG(σ_b, t·10^6)：投票专用（域分离预留索引 0）。"""
        return PRPG(self.sigma_b, self.ring).generate(t * PRPG_DOMAIN_MULT)

    # ---------------- 参数断言 ----------------
    def assert_bounds(self, K: int, max_abs_x: float, omega_max: float = 1.0):
        """
        无回绕条件（式 D1.3 / D3.2）：
          聚合明文上界 K·max|m| < p/2（外层 mod p 无损）
          p̃·K·η + K·max|m| < Q/2（内层 mod q 无回绕）
        """
        max_m = int(np.ceil(omega_max * max_abs_x * self.delta)) + 1
        if K * max_m >= self.p // 2:
            raise ValueError(
                f"ECPFL 参数无效：K·max|m| = {K}·{max_m} ≥ p/2 = 2^{self.logp - 1}。"
                f"请增大 esafl.logp、降低 delta_scale，或裁剪梯度（减小 x 上界）")
        noise_term = self.p * K * self.eta
        if noise_term + K * max_m >= self.Q // 2:
            raise ValueError(
                f"ECPFL 参数无效：p̃·K·η + K·max|m| = {noise_term} + {K} * {max_m} "
                f"≥ Q/2 ≈ 2^{self.Q.bit_length() - 2}。请增大环模数位数或降低 p/delta")


class ECPFLClient:
    """ECPFL-Lite 客户端：仅持有 (S, S_i, z_i, σ_a, σ_b)，无任何份额矩阵。"""

    def __init__(self, kgc: KGC, key_material: dict):
        self.kgc = kgc
        self.ring = kgc.ring
        self.n = kgc.n
        self.client_id = key_material['client_id']
        # Lite：3 个环元素（S 用于本地一步解密；S_i/z_i 用于构造逐包有效密钥）
        self.S = key_material['S']
        self.S_i = key_material['S_i']
        self.z_i = key_material['z_i']
        self.sigma_a = key_material['sigma_a']
        self.sigma_b = key_material['sigma_b']
        self.p, self.delta, self.eta = kgc.p, kgc.delta, kgc.eta

    # ---------------- 内部工具 ----------------
    def _lam(self, S_set: List[int]) -> int:
        return lagrange_coeffs(sorted(S_set), self.ring.Q)[self.client_id]

    def _a_j(self, t: int, j: int) -> RingArray:
        return self.kgc.prpg_a(t, j)

    def _enc(self, a: RingArray, s_tilde: RingArray, pt: np.ndarray) -> ESHEPurePyCiphertext:
        """ct = [a·s̃ + p̃·e + pt]_Q（式 4/9/11 通用）。"""
        e = _sample_noise(self.n, self.eta)
        # p̃ 为常数多项式（仅 X^0 系数 = p）：
        # 稠密 p̃ 的 negacyclic 卷积 p̃·e 系数 ~ p·n·eta，会随机超出 Q/2 触发回绕
        _pc = np.zeros(self.n, dtype=np.int64); _pc[0] = self.p
        p_const = self.ring.from_ints(_pc)
        coeffs = a.mul(s_tilde).add(p_const.mul(self.ring.from_ints(e))).add(
            self.ring.from_ints(pt))
        return ESHEPurePyCiphertext(coeffs, self.ring.zeros(), 0)

    # ---------------- Phase 1：ESP-Vote（式 9）----------------
    def esp_vote(self, t: int, S_set: List[int], vote_bits: np.ndarray) -> ESHEPurePyCiphertext:
        """v̂_i = [a_0·(λ_i z_i) + p̃·e + v_i(X)]_q，v_i 低 J 系数 ∈ {0,1}。"""
        lam = self._lam(S_set)
        v = np.zeros(self.n, dtype=np.int64)
        bits = np.asarray(vote_bits, dtype=np.int64).reshape(-1)
        v[:len(bits)] = bits
        a0 = self.kgc.prpg_a0(t)
        mask_term = a0.mul(self.z_i.scalar_mul(lam))
        e = _sample_noise(self.n, self.eta)
        _pc = np.zeros(self.n, dtype=np.int64); _pc[0] = self.p
        p_const = self.ring.from_ints(_pc)
        coeffs = mask_term.add(p_const.mul(self.ring.from_ints(e))).add(
            self.ring.from_ints(v))
        return ESHEPurePyCiphertext(coeffs, self.ring.zeros(), 0)

    # ---------------- Phase 2：ESP-Enc（Lite 有效密钥，式 11）----------------
    def effective_key(self, t: int, j: int, S_set: List[int],
                      bhat: bool = False) -> RingArray:
        """s̃_{i,j} = λ_i·(S_i + b_j·z_i)（或掉线补偿的 b̂ 变体）。

        仅 1 次环乘（b_j·z_i）+ 1 次加 + 1 次标量乘，O(n)；
        b_j z_i 逐包随机化防止跨包/跨轮消元攻击。"""
        lam = self._lam(S_set)
        bj = self.kgc.prpg_bhat(t, j) if bhat else self.kgc.prpg_b(t, j)
        return self.S_i.add(bj.mul(self.z_i)).scalar_mul(lam)

    def esp_enc(self, t: int, j: int, S_set: List[int],
                x_pack: np.ndarray, omega: float) -> ESHEPurePyCiphertext:
        """pt = round(ω·x·Δ)；ct = [a_j·s̃ + p̃·e + pt]_q（式 11）。"""
        m = np.round(omega * np.asarray(x_pack, dtype=np.float64) * self.delta).astype(np.int64)
        if m.shape[0] != self.n:
            raise ValueError(f"包长度 {m.shape[0]} != 环维度 {self.n}")
        if m.min() < -self.p // 4 or m.max() >= self.p // 4:
            raise ValueError(
                f"ECPFL 定点明文越界 [{m.min()}, {m.max()}]，要求 |m| < p/4；"
                f"请裁剪梯度或降低 delta")
        return self._enc(self._a_j(t, j), self.effective_key(t, j, S_set), m)

    # ---------------- Phase 3：ESP-Comp（Lite 差值补偿，式 14）----------------
    def esp_comp(self, t: int, j: int, S_set: List[int],
                 Shat_set: List[int]) -> ESHEPurePyCiphertext:
        """纯密钥差值补偿密文 δ = [a_j·κ + p̃·ê]_q，
        κ = ŝ − s̃ = (λ̂−λ)S_i + (λ̂b̂ − λb)z_i（与原密文相加后旧 λ 项对消，
        新集合下 Σλ̂_i(S_i + b̂ z_i) = S）。"""
        kappa = self.effective_key(t, j, Shat_set, bhat=True).sub(
            self.effective_key(t, j, S_set))
        return self._enc(self._a_j(t, j), kappa, np.zeros(self.n, dtype=np.int64))

    # ---------------- Dec（式 7/17）----------------
    def decrypt_poly(self, a: RingArray, C: ESHEPurePyCiphertext) -> np.ndarray:
        """one-shot Dec(a, S, C) = [[C − a·S]_q]_p，返回整数明文多项式。"""
        t = C.coeffs.sub(a.mul(self.S))
        q1, q2 = self.ring.q1, self.ring.q2
        q1_inv = pow(q1 % q2, q2 - 2, q2)
        c1 = t.r1.astype(object)
        c2 = t.r2.astype(object)
        k = ((c2 - c1) % q2 * q1_inv) % q2
        x = (c1 + q1 * k)
        half = self.ring.Q // 2
        x = np.where(x > half, x - self.ring.Q, x)
        # 中心化 mod p：定点明文 m 可为负，须映射回 (−p/2, p/2]
        x = (x + self.p // 2) % self.p - self.p // 2
        return np.array(x, dtype=np.int64)

    def decrypt_pack(self, t: int, j: int, C: ESHEPurePyCiphertext) -> np.ndarray:
        """解密并定点解码：x̂ = [[C − a_j·S]_q]_p / Δ（式 7）。"""
        return self.decrypt_poly(self._a_j(t, j), C).astype(np.float64) / self.delta


class ECPFLServer:
    """ECPFL 半诚实服务器：计票（式 10）、密文聚合（式 13/15）、ECP 队列（式 16）。"""

    def __init__(self, kgc: KGC):
        self.kgc = kgc
        self.ring = kgc.ring

    # ---------------- Phase 1：ESP-Tally（式 10）----------------
    @staticmethod
    def _centered(ct_sum_coeffs: RingArray, Q: int) -> np.ndarray:
        t = ct_sum_coeffs
        q1, q2 = t.ctx.q1, t.ctx.q2
        q1_inv = pow(q1 % q2, q2 - 2, q2)
        c1 = t.r1.astype(object)
        c2 = t.r2.astype(object)
        k = ((c2 - c1) % q2 * q1_inv) % q2
        x = (c1 + q1 * k)
        half = Q // 2
        return np.where(x > half, x - Q, x)

    def esp_tally(self, vote_cts: List[ESHEPurePyCiphertext],
                  J: int) -> np.ndarray:
        """Σv̂ → [[·]_q]_p → 前 J 系数即得票 ν_j（式 10；掩码自归零，无需 S）。"""
        acc = vote_cts[0].coeffs.copy()
        for ct in vote_cts[1:]:
            acc = acc.add(ct.coeffs)
        centered = self._centered(acc, self.ring.Q)
        return np.array(centered % self.kgc.p, dtype=np.int64)[:J]

    @staticmethod
    def consensus(nu: np.ndarray, rule: str, theta: float,
                  num_active: int) -> List[int]:
        """共识规则：UN（ν≥1）/ RK-θ（前 ⌈θJ⌉ 名）/ TH-θ（ν ≥ θ|S|）。"""
        J = len(nu)
        if rule == 'un':
            return [j for j in range(J) if nu[j] >= 1]
        if rule == 'rk':
            k_count = max(1, int(np.ceil(theta * J)))
            order = np.argsort(-nu, kind='stable')
            selected = set(order[:k_count].tolist())
            return [j for j in range(J) if j in selected]
        if rule == 'th':
            return [j for j in range(J) if nu[j] >= theta * num_active]
        raise ValueError(f"未知共识规则: {rule}")

    # ---------------- Phase 3：ESP-Agg（式 13/15）----------------
    @staticmethod
    def esp_agg(cts: List[ESHEPurePyCiphertext],
                comp_cts: Optional[List[ESHEPurePyCiphertext]] = None) -> ESHEPurePyCiphertext:
        """同步：C = Σ ct（式 13）；掉线：C = Σ(ct + δ)（式 15）。"""
        acc = cts[0].coeffs.copy()
        for ct in cts[1:]:
            acc = acc.add(ct.coeffs)
        if comp_cts:
            for d in comp_cts:
                acc = acc.add(d.coeffs)
        return ESHEPurePyCiphertext(acc, cts[0].mask.copy(), cts[0].counter)

    # ---------------- Phase 4：ECP（式 16）----------------
    @staticmethod
    def ecp_accumulate(round_cts: List[ESHEPurePyCiphertext],
                       round_as: List[RingArray]) -> Tuple[ESHEPurePyCiphertext, RingArray]:
        """C_pre = Σ_r C^(r)；A_pre = Σ_r a_j^(r)（式 16）。"""
        C_pre = round_cts[0].coeffs.copy()
        for ct in round_cts[1:]:
            C_pre = C_pre.add(ct.coeffs)
        A_pre = round_as[0].copy()
        for a in round_as[1:]:
            A_pre = A_pre.add(a)
        return (ESHEPurePyCiphertext(C_pre, round_cts[0].mask.copy(), 0), A_pre)

    def decrypt_prefetched(self, client: ECPFLClient, C_pre: ESHEPurePyCiphertext,
                           A_pre: RingArray) -> np.ndarray:
        """ECP 一步解密（式 17）：[[C_pre − A_pre·S]_q]_p / Δ。"""
        pt = client.decrypt_poly(A_pre, C_pre)
        return pt.astype(np.float64) / self.kgc.delta
