"""
SecureRes-Fetch 协议骨架实现
对应 docs/complete_sequence_diagrams.md 中的完整时序图

包含：
- Phase 0: 阈值密钥生成与分发
- Phase 1: 主训练循环（含SRCA、TPW、预取、阈值解密）
- Phase 2: 异常处理与训练结束
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import hashlib
import copy
import random


# ============================================================================
# 基础数据结构与类型定义
# ============================================================================

class VerificationResult(Enum):
    ACCEPT = "accept"
    REJECT_REPLAY = "reject_replay"
    REJECT_FORGERY = "reject_forgery"
    REJECT_BUDGET = "reject_budget"


@dataclass
class CKKSCiphertext:
    """CKKS密文结构 (c_0, c_1)"""
    c0: bytes  # b_agg·v + e_0 + m
    c1: bytes  # a·v + e_1
    scale: float
    level: int


@dataclass
class EncryptedDelta:
    """带元数据的密文Delta"""
    delta_ct: CKKSCiphertext
    round_num: int
    timestamp: float
    pk_agg_hash: str


@dataclass
class PartialDecryption:
    """部分解密份额"""
    share_id: int
    D_j: bytes  # sk_j · c_1 + e_smudge
    smudge_proof: bytes


@dataclass
class BLSSignature:
    """BLS阈值签名"""
    sigma: bytes
    signers: Set[int]
    aggregated: bool = False


@dataclass
class SparseUpdate:
    """稀疏化加密更新"""
    ciphertexts: List[CKKSCiphertext]  # 按batch
    mask: List[bool]  # batch选中掩码
    idx_set: List[int]  # 选中batch索引
    is_sparse: bool = True


# ============================================================================
# Phase 0: KGC - 阈值密钥生成与分发
# ============================================================================

class ThresholdKGC:
    """
    [P0-1] ~ [P0-3]
    密钥生成中心：生成阈值CKKS密钥，分发后永久离线
    """

    def __init__(self, security_param: int = 128, n_parties: int = 10, threshold: int = 6):
        self.λ = security_param
        self.n = n_parties
        self.t = threshold
        self._destroyed = False

    def keygen(self) -> Dict:
        """
        [P0-1] ThresholdCKKS.KeyGen(λ, n, t)
        执行步骤：
        [2.1] s ← χ_key
        [2.2] a ← U(R_qL)
        [2.3] e ← χ_err
        [2.4] b = -a·s + e
        """
        # 模拟RLWE采样
        s_agg = self._sample_secret_key()
        a_agg = self._sample_uniform()
        e_agg = self._sample_error()
        b_agg = self._compute_b(a_agg, s_agg, e_agg)

        # [2.5-2.10] 阈值密钥生成
        secret_shares = self._shamir_split(s_agg, self.n, self.t)
        a_shares = [self._sample_uniform() for _ in range(self.n)]
        e_shares = [self._sample_error() for _ in range(self.n)]
        b_shares = [self._compute_b(a_shares[i], secret_shares[i], e_shares[i])
                    for i in range(self.n)]

        # 聚合公钥
        pk_agg = (sum(b_shares), a_agg)
        evk = self._generate_eval_key(secret_shares)

        return {
            'pk_agg': pk_agg,
            'evk': evk,
            'secret_shares': secret_shares,
            'a_shares': a_shares,
            'e_shares': e_shares,
        }

    def distribute_keys(self, key_material: Dict, clients: List, aux_nodes: List, witnesses: List):
        """
        [P0-2] 分发密钥材料
        KGC→AS: (pk_agg, evk)
        KGC→C_i: sk_i
        KGC→AN_j: sk_j
        KGC→WN_k: sk_WN_k
        """
        pk_agg, evk = key_material['pk_agg'], key_material['evk']
        shares = key_material['secret_shares']

        # AS获得公钥
        as_context = {'pk_agg': pk_agg, 'evk': evk, 'sk': None}

        # 客户端获得私钥份额
        client_keys = {}
        for i, client in enumerate(clients):
            client_keys[client] = {
                'sk_i': shares[i],
                'pk_agg': pk_agg,
                'evk': evk,
            }

        # 辅助节点获得私钥份额
        aux_keys = {}
        for j, an in enumerate(aux_nodes):
            idx = len(clients) + j
            aux_keys[an] = {
                'sk_j': shares[idx],
                'pk_agg': pk_agg,
                'evk': evk,
            }

        # 见证节点获得签名密钥
        witness_keys = self._generate_witness_keys(witnesses)

        return as_context, client_keys, aux_keys, witness_keys

    def shred_keys(self):
        """
        [P0-3] KGC销毁所有密钥材料并永久离线
        """
        self._destroyed = True
        # 安全擦除内存
        # (实际实现中需要使用安全内存清零)

    # ---- 内部辅助方法 ----
    def _sample_secret_key(self): return b'secret_key_sample'
    def _sample_uniform(self): return b'uniform_sample'
    def _sample_error(self): return b'error_sample'
    def _compute_b(self, a, s, e): return b'computed_b'
    def _shamir_split(self, secret, n, t): return [f'share_{i}' for i in range(n)]
    def _generate_eval_key(self, shares): return b'eval_key'
    def _generate_witness_keys(self, witnesses): return {}


# ============================================================================
# 第一篇：客户端 (C_i)
# ============================================================================

class SecureResFetchClient:
    """
    [P1-1] ~ [P1-7], [P1-19] ~ [P1-24]
    带SRCA残差累积和阈值解密的联邦学习客户端
    """

    def __init__(self, client_id: int, sk_i, pk_agg, evk, vk_wn):
        self.client_id = client_id
        self.sk_i = sk_i          # [P0-2b] 私钥份额
        self.pk_agg = pk_agg      # 聚合公钥
        self.evk = evk            # 评估密钥
        self.vk_wn = vk_wn        # 见证验证公钥

        # 预取状态
        self.ct_prefetch: Optional[CKKSCiphertext] = None
        self.prefetch_rounds: List[int] = []
        self.last_accepted_round = 0

        # SRCA残差状态
        self.residual: Dict = {}  # r_i^(t)
        self.gamma = 0.90         # 残差衰减系数
        self.sparsity_rate = 0.30  # 稀疏率 s

        # 训练状态
        self.w_base: Dict = {}    # 上次同步的base model
        self.w_sync: Dict = {}    # 同步后模型

    def check_prefetch_and_sync(self, current_round: int) -> Dict:
        """
        [P1-1] 检查预取缓存
        if ct_prefetch ≠ ∅: 进入阈值解密
        else: w_sync ← w_base
        """
        if self.ct_prefetch is not None and len(self.prefetch_rounds) > 0:
            # [P1-19] ~ [P1-23] 阈值解密流程
            self.w_sync = self._threshold_decrypt_and_apply(
                self.ct_prefetch,
                self.prefetch_rounds,
                current_round
            )
            # [P1-23] 清空预取缓存，更新base
            self.ct_prefetch = None
            self.prefetch_rounds = []
            self.w_base = copy.deepcopy(self.w_sync)
        else:
            self.w_sync = copy.deepcopy(self.w_base)

        return self.w_sync

    def local_train_and_encrypt(self, train_loader, current_round: int, total_rounds: int) -> SparseUpdate:
        """
        [P1-2] ~ [P1-7] 本地训练、SRCA合成、稀疏化、加密
        """
        # [P1-2] 本地训练
        w_new = self._local_train(train_loader, self.w_sync)
        delta_w = self._model_subtract(w_new, self.w_sync)

        # [P1-5] 自适应稀疏率
        self.sparsity_rate = self._adaptive_sparsity(current_round, total_rounds)

        # [P1-3] SRCA残差合成: g_i = Δw_i + γ·r_i
        g = self._residual_compose(delta_w, self.residual, self.gamma)

        # [P1-4] 包级稀疏化
        idx_set, g_sparse, mask = self._sparse_batches(g, self.sparsity_rate)

        # [P1-6] CKKS加密
        ct_list = [self._ckks_encrypt(batch, self.pk_agg) for batch in g_sparse]

        # [P1-7] 更新残差 [4.6]
        self._update_residual(g, mask)

        return SparseUpdate(
            ciphertexts=ct_list,
            mask=mask,
            idx_set=idx_set
        )

    def receive_prefetch_delta(self, encrypted_delta: EncryptedDelta,
                                signature: BLSSignature) -> VerificationResult:
        """
        [P1-16] ~ [P1-18] 接收预取Delta并验证
        """
        delta = encrypted_delta.delta_ct
        t = encrypted_delta.round_num

        # [P1-16] 验证BLS签名
        h = self._hash_delta(encrypted_delta)
        if not self._verify_bls(signature, h, self.vk_wn):
            return VerificationResult.REJECT_FORGERY

        # 检查重放
        if t <= self.last_accepted_round:
            return VerificationResult.REJECT_REPLAY

        # [P1-17] 接受并累加
        if self.ct_prefetch is None:
            self.ct_prefetch = copy.deepcopy(delta)
        else:
            self.ct_prefetch = self._homomorphic_add(self.ct_prefetch, delta)

        self.prefetch_rounds.append(t)
        self.last_accepted_round = t
        return VerificationResult.ACCEPT

    def _threshold_decrypt_and_apply(self, ct_prefetch: CKKSCiphertext,
                                      prefetch_rounds: List[int],
                                      current_round: int) -> Dict:
        """
        [P1-19] ~ [P1-23] 阈值解密子流程
        """
        # [P1-19] 计算自身部分解密份额
        D_i = self._partial_decrypt(self.sk_i, ct_prefetch)

        # 收集 t-1 个外部份额
        external_shares: List[PartialDecryption] = []
        selected_aux_nodes = self._select_aux_nodes(self.t - 1)

        for an_id in selected_aux_nodes:
            # [P1-20] 向辅助节点请求部分解密
            share = self._request_partial_decryption(an_id, ct_prefetch)
            external_shares.append(share)

        # [P1-21] 拉格朗日组合
        all_shares = [PartialDecryption(share_id=self.client_id, D_j=D_i, smudge_proof=b'')] + external_shares
        m_combined = self._lagrange_combine(all_shares, ct_prefetch)

        # [P1-22] CKKS解码
        delta_w_cum = self._ckks_decode(m_combined)

        # [P1-23] 应用累积更新
        w_sync = self._model_add(self.w_base, delta_w_cum)
        return w_sync

    def _partial_decrypt(self, sk_i, ct: CKKSCiphertext) -> bytes:
        """
        [16] D_i = sk_i · c_1 + e_smudge
        σ_smudge ≥ 2^s · ‖e_prefetch‖_can
        """
        # e_smudge ← D_{R, σ_smudge}
        e_smudge = self._sample_smudging_noise(ct.level)
        D_i = self._ring_mul_add(sk_i, ct.c1, e_smudge)
        return D_i

    # ---- SRCA辅助方法 ----
    def _residual_compose(self, delta_w, residual, gamma):
        """[4.3] g_i = Δw_i + γ·r_i"""
        result = {}
        for k in delta_w:
            r = residual.get(k, 0)
            result[k] = delta_w[k] + gamma * r
        return result

    def _update_residual(self, g, mask):
        """[4.6] 残差更新"""
        for i, selected in enumerate(mask):
            if not selected:
                self.residual[i] = g.get(i, 0)
            else:
                self.residual[i] = 0

    def _sparse_batches(self, g, sparsity_rate):
        """[4.4] 包级稀疏化"""
        batches = list(g.items())
        n_select = max(1, int(len(batches) * sparsity_rate))
        idx_set = random.sample(range(len(batches)), n_select)
        mask = [i in idx_set for i in range(len(batches))]
        g_sparse = [batches[i][1] for i in idx_set]
        return idx_set, g_sparse, mask

    def _adaptive_sparsity(self, t, T):
        """[4.18-4.30] 自适应稀疏率"""
        if t < T / 4:
            return 0.50  # [4.19] 预热期
        elif t < 3 * T / 4:
            return 0.30  # [4.22] 稳定期
        else:
            return 0.15  # [4.25] 精调期

    # ---- 占位符方法 ----
    def _local_train(self, loader, w): return {}
    def _model_subtract(self, a, b): return {k: a[k]-b[k] for k in a}
    def _model_add(self, a, b): return {k: a[k]+b[k] for k in a}
    def _ckks_encrypt(self, m, pk): return CKKSCiphertext(b'c0', b'c1', 2**20, 5)
    def _ckks_decode(self, m): return {}
    def _homomorphic_add(self, ct1, ct2): return ct1
    def _verify_bls(self, sig, h, vk): return True
    def _hash_delta(self, ed): return b'hash'
    def _select_aux_nodes(self, count): return list(range(count))
    def _request_partial_decryption(self, an_id, ct): return PartialDecryption(an_id, b'D', b'')
    def _lagrange_combine(self, shares, ct): return b'combined'
    def _sample_smudging_noise(self, level): return b'smudge'
    def _ring_mul_add(self, a, b, c): return b'result'


# ============================================================================
# 第一篇 + 第四篇：聚合服务器 (AS)
# ============================================================================

class SecureResFetchServer:
    """
    [P1-8] ~ [P1-15], [4.9] ~ [4.17]
    带SRCA残差补偿、TPW签名、带宽感知预取的聚合服务器
    """

    def __init__(self, pk_agg, evk, witness_pubkeys: Dict):
        self.pk_agg = pk_agg
        self.evk = evk
        self.vk_wn = witness_pubkeys

        # 全局状态
        self.ct_agg_prev: Optional[CKKSCiphertext] = None
        self.ct_agg_current: Optional[CKKSCiphertext] = None
        self.round_num = 0

        # SRCA全局残差 [4.13]
        self.R_global: Dict = {}
        self.gamma_R = 0.90

        # 预取状态
        self.client_bandwidth: Dict[int, Tuple[float, float]] = {}  # (down, up)
        self.ema_round_duration = 10.0  # 秒
        self.prefetch_budget_ratio = 0.3

    def aggregate_updates(self, encrypted_updates: List[SparseUpdate],
                          weights: List[float]) -> CKKSCiphertext:
        """
        [P1-8] 同态聚合 + [4.10-4.12] SRCA全局残差补偿
        """
        # 按batch分桶
        batch_count = len(encrypted_updates[0].ciphertexts)
        ct_agg_batches = []

        for b in range(batch_count):
            # 找出选中此batch的客户端
            participants = [(i, w) for i, (eu, w) in enumerate(zip(encrypted_updates, weights))
                            if b < len(eu.mask) and eu.mask[b]]

            if len(participants) > 0:
                # [4.11] 正常聚合
                ct_batch = self._weighted_homomorphic_sum(
                    [encrypted_updates[i].ciphertexts[b] for i, _ in participants],
                    [w for _, w in participants]
                )
            else:
                # [4.12] 全局残差补偿
                ct_batch = self.R_global.get(b, self._zero_ciphertext())

            ct_agg_batches.append(ct_batch)

        # 打包所有batch为单个密文（简化表示）
        self.ct_agg_current = self._pack_batches(ct_agg_batches)

        # [4.13] 更新全局残差
        self._update_global_residual(encrypted_updates)

        return self.ct_agg_current

    def compute_and_sign_delta(self, witness_nodes: List) -> Tuple[EncryptedDelta, BLSSignature]:
        """
        [P1-10] ~ [P1-13] 计算Delta + TPW见证签名
        """
        # [P1-10] 密文减法: δ^(t) = ct_agg^(t) - ct_agg^(t-1)
        if self.ct_agg_prev is None:
            delta_ct = self.ct_agg_current
        else:
            delta_ct = self._homomorphic_subtract(self.ct_agg_current, self.ct_agg_prev)

        encrypted_delta = EncryptedDelta(
            delta_ct=delta_ct,
            round_num=self.round_num,
            timestamp=self._get_timestamp(),
            pk_agg_hash=self._hash_pk(self.pk_agg)
        )

        # [P1-11] 请求见证签名
        h = self._hash_delta(encrypted_delta)
        signatures = []

        for wn in witness_nodes[:self.t_w]:
            # [P1-12] WN_k签名
            sigma_k = wn.sign(h, self.round_num)
            signatures.append(sigma_k)

        # [P1-13] 聚合签名
        sigma = self._aggregate_bls_signatures(signatures)
        bls_sig = BLSSignature(sigma=sigma, signers=set(range(len(signatures))), aggregated=True)

        return encrypted_delta, bls_sig

    def schedule_and_broadcast_prefetch(self, unselected_clients: List[int],
                                         client_residuals: Dict[int, Dict]) -> Dict[int, EncryptedDelta]:
        """
        [P1-14] ~ [P1-15] 残差感知预取调度 + 广播
        [4.15-4.17] 带宽感知调度
        """
        # [4.15] 计算优先级
        priorities = {}
        for cid in unselected_clients:
            residual_norm = self._compute_residual_norm(client_residuals.get(cid, {}))
            feasible = self._check_prefetch_feasible(cid)
            # [4.15] priority = α·residual_norm + (1-α)·feasible
            priorities[cid] = 0.7 * residual_norm + 0.3 * (1.0 if feasible else 0.0)

        # [4.16] 选择预取目标
        budget = self._compute_bandwidth_budget()
        sorted_clients = sorted(priorities.items(), key=lambda x: x[1], reverse=True)

        pref_set = []
        bytes_used = 0
        delta_size = self._estimate_delta_size()

        for cid, _ in sorted_clients:
            if bytes_used + delta_size <= budget:
                pref_set.append(cid)
                bytes_used += delta_size
            else:
                break

        # [P1-15] 广播
        delta, sig = self.compute_and_sign_delta([])  # 实际应有见证节点
        broadcasts = {}
        for cid in pref_set:
            broadcasts[cid] = delta

        # 更新状态
        self.ct_agg_prev = copy.deepcopy(self.ct_agg_current)
        self.round_num += 1

        return broadcasts

    def _update_global_residual(self, encrypted_updates: List[SparseUpdate]):
        """[4.13] 更新全局残差 R_global"""
        batch_count = len(encrypted_updates[0].ciphertexts) if encrypted_updates else 0
        for b in range(batch_count):
            has_participant = any(b < len(eu.mask) and eu.mask[b] for eu in encrypted_updates)
            if not has_participant:
                # 没有任何客户端选中此batch，保留残差
                self.R_global[b] = self.R_global.get(b, self._zero_ciphertext())
            else:
                # 衰减残差
                if b in self.R_global:
                    self.R_global[b] = self._scale_ciphertext(self.R_global[b], self.gamma_R)

    def _check_prefetch_feasible(self, client_id: int) -> bool:
        """[4.33-4.34] 预取可行性检查"""
        bw_down, _ = self.client_bandwidth.get(client_id, (1.0, 1.0))
        delta_size = self._estimate_delta_size()
        download_time = delta_size / bw_down
        return download_time <= self.ema_round_duration * 1.2  # β=1.2

    def _compute_bandwidth_budget(self) -> int:
        """计算本轮预取带宽预算"""
        # 基于EMA轮次时长和总带宽计算
        return int(self.ema_round_duration * 1000 * self.prefetch_budget_ratio)

    # ---- 占位符方法 ----
    def _weighted_homomorphic_sum(self, cts, weights): return cts[0]
    def _homomorphic_subtract(self, a, b): return a
    def _pack_batches(self, batches): return CKKSCiphertext(b'packed', b'', 2**20, 5)
    def _zero_ciphertext(self): return CKKSCiphertext(b'0', b'0', 2**20, 5)
    def _scale_ciphertext(self, ct, scale): return ct
    def _hash_delta(self, ed): return b'hash'
    def _hash_pk(self, pk): return b'pk_hash'
    def _aggregate_bls_signatures(self, sigs): return b'aggregated'
    def _get_timestamp(self): return 0.0
    def _compute_residual_norm(self, residual): return 1.0
    def _estimate_delta_size(self): return 1024

    @property
    def t_w(self): return 3  # 见证阈值


# ============================================================================
# 第三篇：见证节点 (WN_k)
# ============================================================================

class WitnessNode:
    """
    [P1-12] TPW见证节点
    """

    def __init__(self, node_id: int, sk_wn, vk_wn):
        self.node_id = node_id
        self.sk_wn = sk_wn          # 签名私钥
        self.vk_wn = vk_wn          # 验证公钥
        self.last_signed_round: Dict[int, int] = {}  # AS_id -> last_round

    def sign(self, h: bytes, round_num: int, as_id: int = 0) -> bytes:
        """
        [3.3] 验证并签名
        if t > last_signed_round[AS]: 签名
        else: REJECT
        """
        last_round = self.last_signed_round.get(as_id, 0)
        if round_num <= last_round:
            raise ValueError("Reject: replay signature request")

        # BLS签名: σ = H(h)^{sk}
        sigma = self._bls_sign(h, self.sk_wn)
        self.last_signed_round[as_id] = round_num
        return sigma

    def _bls_sign(self, h, sk): return b'signature'


# ============================================================================
# 第三篇：辅助节点 (AN_j)
# ============================================================================

class AuxiliaryNode:
    """
    [P1-20] 辅助节点：参与阈值解密
    """

    def __init__(self, node_id: int, sk_j, pk_agg, evk):
        self.node_id = node_id
        self.sk_j = sk_j
        self.pk_agg = pk_agg
        self.evk = evk

    def partial_decrypt(self, ct: CKKSCiphertext) -> PartialDecryption:
        """
        [18] D_j = sk_j · c_1 + e_smudge,j
        """
        e_smudge = self._sample_smudging_noise(ct.level)
        D_j = self._ring_mul_add(self.sk_j, ct.c1, e_smudge)

        return PartialDecryption(
            share_id=self.node_id,
            D_j=D_j,
            smudge_proof=b'proof'
        )

    def _sample_smudging_noise(self, level): return b'smudge'
    def _ring_mul_add(self, a, b, c): return b'result'


# ============================================================================
# 融合主循环
# ============================================================================

def run_secure_res_fetch():
    """
    完整的 SecureRes-Fetch 端到端协议流程
    对应图5.1的完整时序
    """

    # ===== PHASE 0: 初始化 =====
    print("=" * 60)
    print("PHASE 0: 系统初始化")
    print("=" * 60)

    kgc = ThresholdKGC(security_param=128, n_parties=10, threshold=6)
    key_material = kgc.keygen()

    # 模拟实体
    n_clients = 10
    n_aux = 4
    n_witness = 5

    clients = [f"client_{i}" for i in range(n_clients)]
    aux_nodes = [f"aux_{j}" for j in range(n_aux)]
    witnesses = [WitnessNode(k, f"sk_wn_{k}", f"vk_wn_{k}") for k in range(n_witness)]

    as_context, client_keys, aux_keys, witness_keys = kgc.distribute_keys(
        key_material, clients, aux_nodes, witnesses
    )
    kgc.shred_keys()
    print("[P0-3] KGC密钥已销毁，永久离线\n")

    # 创建服务器和客户端实例
    server = SecureResFetchServer(
        pk_agg=as_context['pk_agg'],
        evk=as_context['evk'],
        witness_pubkeys=witness_keys
    )

    client_objects = {
        i: SecureResFetchClient(
            client_id=i,
            sk_i=client_keys[c]['sk_i'],
            pk_agg=client_keys[c]['pk_agg'],
            evk=client_keys[c]['evk'],
            vk_wn=witness_keys.get('vk_WN', b'vk')
        )
        for i, c in enumerate(clients)
    }

    aux_node_objects = {
        j: AuxiliaryNode(
            node_id=j,
            sk_j=aux_keys[a]['sk_j'],
            pk_agg=aux_keys[a]['pk_agg'],
            evk=aux_keys[a]['evk']
        )
        for j, a in enumerate(aux_nodes)
    }

    # ===== PHASE 1: 主训练循环 =====
    T = 100  # 总轮次
    for t in range(1, T + 1):
        print(f"\n{'=' * 60}")
        print(f"ROUND {t}/{T}")
        print(f"{'=' * 60}")

        # [P1-1] 客户端检查预取缓存
        selected_clients = random.sample(range(n_clients), k=3)
        unselected_clients = [i for i in range(n_clients) if i not in selected_clients]

        for cid in selected_clients:
            client = client_objects[cid]
            client.check_prefetch_and_sync(t)

        # [P1-2] ~ [P1-7] 选中客户端训练并上传
        encrypted_updates = []
        weights = []
        for cid in selected_clients:
            client = client_objects[cid]
            sparse_update = client.local_train_and_encrypt(
                train_loader=None, current_round=t, total_rounds=T
            )
            encrypted_updates.append(sparse_update)
            weights.append(1.0 / len(selected_clients))

        # [P1-8] ~ [P1-9] 服务器聚合 + SRCA残差补偿
        ct_agg = server.aggregate_updates(encrypted_updates, weights)
        print(f"[P1-8] 聚合完成: {len(encrypted_updates)} 个客户端")

        # [P1-10] ~ [P1-13] 计算Delta + TPW签名
        delta, signature = server.compute_and_sign_delta(witnesses)
        print(f"[P1-13] TPW签名聚合完成")

        # [P1-14] ~ [P1-15] 预取调度 + 广播
        broadcasts = server.schedule_and_broadcast_prefetch(
            unselected_clients,
            {cid: client_objects[cid].residual for cid in unselected_clients}
        )

        # [P1-16] ~ [P1-18] 客户端验证预取
        for cid, delta in broadcasts.items():
            result = client_objects[cid].receive_prefetch_delta(delta, signature)
            if result == VerificationResult.ACCEPT:
                print(f"  [P1-17] Client {cid}: 预取接受 (round {delta.round_num})")
            else:
                print(f"  [{result.value}] Client {cid}: 预取被拒绝")

    # ===== PHASE 2: 训练结束 =====
    print(f"\n{'=' * 60}")
    print("PHASE 2: 训练结束")
    print("=" * 60)
    print("[P2-1] 最终模型输出完成")


if __name__ == "__main__":
    run_secure_res_fetch()
