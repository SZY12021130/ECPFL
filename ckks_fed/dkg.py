# -*- coding: utf-8 -*-
"""
DKG（分布式密钥生成）setup —— 客户端自治、无 P2P、公告板中继
==============================================================================
替代可信 KGC：每个客户端 k 是自己秘密 s_k 的唯一持有者（dealer），
经公共公告板（star 拓扑，与 FL 上传同信道）完成 3 轮 setup：

  R1  客户端 k：s_k ← U(R_q)；构造 τ−1 次 F_k（F_k(0)=s_k）与零多项式
      Ψ_k（Ψ_k(0)=0）
  R2  客户端 k：向量化多点求值 s_{k,i}=F_k(i)、z_{k,i}=Ψ_k(i)（i=1..N），
      逐目标 AEAD 加密后发布到公告板；客户端 i 下载属于自己的"列"
  R3  客户端 i：本地求 total_i = Σ_k s_{k,i}，发布 g_i = λ_i·total_i (mod Q)；
      全体本地求和 S = Σ_i g_i。total 多项式只暴露 S（各 F_k 互相掩蔽）

验证（模拟器视角）：抽样 dealer 检查 Σ_i λ_i·F_k(i) ≡ s_k (mod Q)，
并检查 S ≡ Σ_k s_k。

安全性质：≤τ−1 客户端合谋无法获得任何 s_k；公告板只含密文；
无任何客户端间直连（无 P2P）。

复杂度（N 客户端，τ 门限，n 多项式阶数）：
  每客户端计算  O(N·τ·n)（R2 求值主导，向量化 + N 路并行后墙钟秒级）
  每客户端通信  O(N·n)（发 2(N−1) 份 + 收 2N 份 ≈ 250 MB @ N=1000）
  总通信字节    O(N²·n)（信息论下界，与 KGC 版相同，但生成墙钟并行化）
  初始化轮数    3（常数轮）；在线训练协议与 KGC 版完全一致
"""
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ckks_fed.eshe import RingContext
from ckks_fed.ecpfl_crypto import _sample_uniform_ring, lagrange_coeffs


@dataclass
class DKGStats:
    t_keygen_ms: float = 0.0      # R1：采样 + 构造多项式
    t_eval_ms: float = 0.0        # R2a：向量化多点求值
    t_crypto_ms: float = 0.0      # R2b：AEAD 加密
    bytes_posted: int = 0         # R2 发布字节（含密文膨胀）
    t_finalize_ms: float = 0.0    # R3：列求和 + g_i


class DKGSetup:
    """单机模拟 N 个客户端的 DKG setup（配合进程池可模拟并行部署）。"""

    def __init__(self, n: int = 4096, num_clients: int = 25, tau: int = 3,
                 seed: int = 42):
        if not (2 <= tau <= num_clients):
            raise ValueError("须满足 2 ≤ τ ≤ N")
        self.n, self.N, self.tau, self.seed = n, num_clients, tau, seed
        self.ring = RingContext(n)
        self.Q = self.ring.Q
        self.lam = lagrange_coeffs(list(range(1, num_clients + 1)), self.Q)
        self.stats: Dict[int, DKGStats] = {}

    # ------------------------------------------------------------------ R1+R2
    def dealer_phase(self, k: int, aes: bool = True) -> Dict[int, Tuple[object, object]]:
        """客户端 k 的 R1+R2：返回 {目标 i: (s_{k,i} 密文或明文, z_{k,i} 密文或明文)}。

        真实部署中该函数在客户端 k 本机执行，产物直接发往公告板。"""
        st = DKGStats()
        t0 = time.perf_counter()
        rng = np.random.default_rng((self.seed, 0xD6, k & 0xFFFFFFFF))
        s_k = _sample_uniform_ring(self.ring, rng)
        f_rest = [_sample_uniform_ring(self.ring, rng) for _ in range(self.tau - 1)]
        psi_rest = [_sample_uniform_ring(self.ring, rng) for _ in range(self.tau - 1)]
        st.t_keygen_ms = (time.perf_counter() - t0) * 1e3

        t0 = time.perf_counter()
        idx = np.arange(1, self.N + 1, dtype=np.int64)
        zero = self.ring.zeros()
        evals: List[List[np.ndarray]] = []
        for polys in ([s_k] + f_rest, [zero] + psi_rest):
            rows = []
            for prime, q in (('r1', self.ring.q1), ('r2', self.ring.q2)):
                c = np.stack([getattr(p, prime) for p in polys])            # (tau, n)
                P = np.stack([np.mod(idx ** j, q) for j in range(self.tau)], axis=1)  # (N, tau)
                rows.append(np.einsum('ij,jn->in', P, c) % q)               # (N, n)
            evals.append(rows)                                              # [F行, Ψ行]
        st.t_eval_ms = (time.perf_counter() - t0) * 1e3

        t0 = time.perf_counter()
        key = AESGCM.generate_key(bit_length=256) if aes else None
        posts: Dict[int, Tuple[object, object]] = {}
        nbytes = 0
        for i in range(1, self.N + 1):
            s_plain = (evals[0][0][i - 1], evals[0][1][i - 1])
            z_plain = (evals[1][0][i - 1], evals[1][1][i - 1])
            if aes:
                ct_s = AESGCM(key).encrypt(os.urandom(12),
                                           s_plain[0].tobytes() + s_plain[1].tobytes(), None)
                ct_z = AESGCM(key).encrypt(os.urandom(12),
                                           z_plain[0].tobytes() + z_plain[1].tobytes(), None)
                posts[i] = (ct_s, ct_z)
            else:
                posts[i] = (s_plain, z_plain)
            nbytes += 2 * 2 * self.n * 8 + (32 if aes else 0)
        st.t_crypto_ms = (time.perf_counter() - t0) * 1e3
        st.bytes_posted = nbytes
        self.stats[k] = st
        self._last = (k, s_k, evals)   # 模拟器可见，仅用于验证
        return posts

    # ------------------------------------------------------------------ R3
    def client_finalize(self, i: int,
                        column_s: List[Tuple[np.ndarray, np.ndarray]],
                        column_z: List[Tuple[np.ndarray, np.ndarray]]
                        ) -> Tuple[Tuple[np.ndarray, np.ndarray],
                                   Tuple[np.ndarray, np.ndarray]]:
        """客户端 i 的 R3：下载自己的列（模拟器传入），求 total_i、z_i，发布 g_i。"""
        t0 = time.perf_counter()
        q1, q2 = self.ring.q1, self.ring.q2
        ts1 = np.zeros(self.n, dtype=np.int64)
        ts2 = np.zeros(self.n, dtype=np.int64)
        z1 = np.zeros(self.n, dtype=np.int64)
        z2 = np.zeros(self.n, dtype=np.int64)
        for (a1, a2), (b1, b2) in zip(column_s, column_z):
            ts1 = (ts1 + a1) % q1
            ts2 = (ts2 + a2) % q2
            z1 = (z1 + b1) % q1
            z2 = (z2 + b2) % q2
        # λ 按 CRT 车道取模（λ mod Q 可达 2^60，直接乘 int64 溢出；
        # 拉格朗日恒等式在每个素数域内分别成立，按车道取模数学等价）
        g1 = ((self.lam[i] % q1) * ts1) % q1
        g2 = ((self.lam[i] % q2) * ts2) % q2
        self.stats.setdefault(i, DKGStats()).t_finalize_ms = \
            (time.perf_counter() - t0) * 1e3
        return (g1, g2), (z1, z2)

    @staticmethod
    def synthesize_S(g_list: List[Tuple[np.ndarray, np.ndarray]],
                     ring: RingContext) -> Tuple[np.ndarray, np.ndarray]:
        q1, q2 = ring.q1, ring.q2
        S1 = np.zeros(ring.n, dtype=np.int64)
        S2 = np.zeros(ring.n, dtype=np.int64)
        for g1, g2 in g_list:
            S1 = (S1 + g1) % q1
            S2 = (S2 + g2) % q2
        return S1, S2

    # ------------------------------------------------------------------ 验证
    @staticmethod
    def _crt(r1: np.ndarray, r2: np.ndarray, q1: int, q2: int) -> np.ndarray:
        """CRT 合成 mod Q（int64 安全：q1*q2 < 2^62）。"""
        q1_inv = pow(q1 % q2, q2 - 2, q2)
        return r1 + q1 * ((r2 - r1) % q2 * q1_inv % q2)

    def verify_dealer(self, k: int, s_k, evals_f: List[np.ndarray]) -> bool:
        """拉格朗日重构：Σ_i λ_i·F_k(i) ≡ s_k (mod Q)（模拟器视角，抽样调用）。"""
        acc = np.zeros(self.n, dtype=object)
        for i in range(1, self.N + 1):
            T = self._crt(evals_f[0][i - 1], evals_f[1][i - 1],
                          self.ring.q1, self.ring.q2).astype(object)
            acc += int(self.lam[i]) * T
        recon = np.array([x % self.Q for x in acc], dtype=object)
        s_true = self._crt(s_k.r1, s_k.r2, self.ring.q1, self.ring.q2).astype(object)
        return bool(np.all(recon == s_true % self.Q))

    def verify_S(self, S1: np.ndarray, S2: np.ndarray, s_secrets: list) -> bool:
        """S ≡ Σ_k s_k (mod Q)（模拟器视角）。"""
        q1, q2 = self.ring.q1, self.ring.q2
        total = np.zeros(self.n, dtype=object)
        for s_k in s_secrets:
            total += self._crt(s_k.r1, s_k.r2, q1, q2).astype(object)
        total %= self.Q
        S = self._crt(S1, S2, q1, q2).astype(object) % self.Q
        return bool(np.all(total == S))
