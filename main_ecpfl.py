# -*- coding: utf-8 -*-
"""
ECPFL（V17，scheme/V17-ecpfl.md）Phase A-D 端到端入口
======================================================

单密文结构 ESP 全流程（Phase 0-3）单机模拟：
  Phase 0  KGC 初始化并分发密钥材料（环上 Shamir 份额 + 零份额 + PRPG 种子）
  每轮 t：
    Phase 1  活跃客户端明文本地训练 → Δw → 包级 Top-ζ 投票 → ESP-Vote 上传
             服务器 ESP-Tally 广播共识包集 K^(t)
    Phase 2  客户端按固定权重 ω_i 缩放，ESP-Enc 上传入选包密文
    Phase 3  ESP-Agg 密文求和（同步式 13 / 掉线补偿式 15）
    活跃客户端下载缺失包密文 one-shot 解密 → w ← w + Δw
  Phase B 范围（默认配置）：全参与、无掉线、无预取
  Phase C 部分参与 + 随机掉线（sampling/dropout_rate 配置）：
    - 预采样池提前 R 轮过承诺 β 倍活跃集；|S|=K ≥ τ；掉线集 D 保 |Ŝ| ≥ τ
    - 掉线路径走 esp_comp 补偿聚合（式 15）
    - 残差双衰减 r_i ← γ_d·γ_s^{ℓ-1}·(x_i ⊙ (1−k))（式 12，ℓ = 距上次参与轮数）
  Phase D ECP 密文预取（prefetch 配置）：
    - 服务器滑动队列保留近 R 轮 (t, K^(t), C^(t))
    - ECP-Fetch：预采样池客户端后台下载缺失 (r, C_j^(r)) 存缓存 L_{i,j}（记 PV）
    - ECP-Sync：活跃客户端训练前按包累加缓存密文，one-shot 解密（式 17）补模型
    - 客户端不再整模型下发，只下载缺失包密文（下行节省来源）

用法：
  python main_ecpfl.py --config configs/test_ecpfl.yaml [--output-dir out]
"""

import argparse
import json
import logging
import os
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import yaml

from ckks_fed.models import create_model
from ckks_fed.data import create_client_dataloaders, evaluate
from ckks_fed.ecpfl_crypto import KGC, ECPFLClient, ECPFLServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-7s %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


def flatten_params(model: nn.Module) -> np.ndarray:
    """展平全部可训练状态：parameters + buffers（含 BN running_mean/var、
    num_batches_tracked）。仅用 parameters() 会把 BN 统计量排除在更新流外，
    导致全局模型 BN 永远停留在初始值（CIFAR/FMNIST eval 崩溃、MNIST 无 BN 故正常）。"""
    return np.concatenate([t.detach().cpu().numpy().flatten()
                           for t in model.state_dict().values()])


def assign_params(model: nn.Module, flat: np.ndarray):
    """与 flatten_params 严格同序（state_dict 顺序）回写全部参数与 buffers。"""
    with torch.no_grad():
        offset = 0
        for t in model.state_dict().values():
            numel = t.numel()
            t.copy_(torch.tensor(flat[offset:offset + numel].reshape(t.shape),
                                 dtype=t.dtype, device=t.device))
            offset += numel
    assert offset == flat.shape[0], f"回写字节数 {offset} != 向量长度 {flat.shape[0]}"


def select_top_packs(x: np.ndarray, J: int, n: int, zeta: float) -> List[int]:
    """包级 Top-ζ（按 ℓ2 范数），至少选 1 个包。"""
    scores = []
    for j in range(J):
        pack = x[j * n:(j + 1) * n]
        scores.append(float(np.linalg.norm(pack)))
    k_count = max(1, int(np.ceil(zeta * J)))
    order = np.argsort(-np.array(scores), kind='stable')
    return sorted(order[:k_count].tolist())


class ECPFLOrchestrator:
    """
    Phase C/D 编排器：预采样活跃集、随机掉线、ECP 滑动队列与预取缓存。

    与具体训练解耦（不触碰 torch），便于编排级测试：
      - active_set(t)：确认活跃集 S^(t)（|S|=K≥τ），预采样池提前 R 轮、过承诺 β
      - sample_dropout(t, S)：按 dropout_rate 抽掉线集 D，保 |Ŝ|≥τ（否则 D=∅）
      - push_queue / evict：服务器滑动队列，淘汰 r ≤ t−R 的旧轮次
      - prefetch(t)：预采样池 P^(t+R) 后台下载缺失 (r, C_j^(r)) 入缓存 L_{i,j}
      - sync_client(i, w)：活跃客户端训练前按包累加缓存密文，one-shot 解密
        （式 17）补到 w，返回 (新 w, 本回合补包数)；随后清空该客户端缓存
    """

    def __init__(self, kgc: KGC, clients: Dict[int, ECPFLClient],
                 server: ECPFLServer, num_clients: int,
                 active_count: int, prefetch_rounds: int, overcommit: float,
                 tau: int, dropout_rate: float, prefetch_enabled: bool,
                 prefetch_bytes_per_ct: int, seed: int = 42):
        # Lite：F_S 为 τ 阶多项式，重构需 τ+1 个份额，故活跃数须 ≥ τ+1
        if not (tau + 1 <= active_count <= num_clients):
            raise ValueError(f"须满足 τ+1 ≤ K ≤ N（Lite F_S 为 τ 阶）："
                             f"τ={tau} K={active_count} N={num_clients}")
        self.kgc, self.clients, self.server = kgc, clients, server
        self.N, self.K, self.R, self.beta = num_clients, active_count, prefetch_rounds, overcommit
        self.tau, self.dropout_rate = tau, dropout_rate
        self.prefetch_enabled = prefetch_enabled
        self.prefetch_bytes_per_ct = prefetch_bytes_per_ct
        self.rng = np.random.default_rng(seed)

        self.pools: Dict[int, List[int]] = {}        # t -> 预采样候选池 P^(t)（|P|=⌈βK⌉）
        self.confirmed: set = set()                  # 已被确认为活跃过的客户端
        self.last_active: List[int] = []             # 上一轮活跃集（避免立即重复入选）
        self.last_round: Dict[int, int] = {}         # i -> 上次参与轮 t_last
        self.queue: deque = deque()                  # [(r, K_set, {j: C_j})]，只留 r > t−R
        self.cache: Dict[Tuple[int, int, int], object] = {}   # (i, r, j) -> C_j^(r)
        self.prefetch_bytes: Dict[int, int] = {i: 0 for i in range(1, num_clients + 1)}
        self.prefetch_events: List[dict] = []        # 每次 fetch 的 (client, round, packs, bytes)

    # ---------------- Phase C：活跃集采样 ----------------
    def _ensure_pool(self, t: int) -> List[int]:
        """预采样候选池 P^(t)：大小 ⌈βK⌉，从"未被更早轮次预留/确认"的客户端中抽。"""
        if t not in self.pools:
            # 排除：更早轮次已预留的候选 + 上一轮活跃（其余客户端可跨轮复用）
            reserved = set(self.last_active)
            for tt, pool in self.pools.items():
                if tt < t:
                    reserved.update(pool)
            avail = [i for i in range(1, self.N + 1) if i not in reserved]
            size = min(int(np.ceil(self.beta * self.K)), len(avail))
            if size < self.K:
                # 复用客户端兜底：从"非上一轮活跃"的客户端中取 K 个
                # （保证相邻轮活跃集不相交；小 N 场景下允许跨轮复用）
                avail2 = [i for i in range(1, self.N + 1)
                          if i not in set(self.last_active)]
                if len(avail2) < self.K:
                    # K=N 全参与或候选枯竭：相邻轮允许重叠，全员可选
                    avail2 = list(range(1, self.N + 1))
                self.pools[t] = sorted(set(self.rng.choice(
                    avail2, size=min(self.K, len(avail2)), replace=False).tolist()))
                return self.pools[t]
            self.pools[t] = self.rng.choice(avail, size=size, replace=False).tolist()
        return self.pools[t]

    def active_set(self, t: int) -> List[int]:
        """确认活跃集 S^(t) = P^(t) 前 K 个（预采样已在 t−R 轮发生）。"""
        pool = self._ensure_pool(t)
        S_set = sorted(pool[:self.K])
        self.last_active = S_set
        self.confirmed.update(S_set)
        return S_set

    def prefetch_pool(self, t: int) -> List[int]:
        """预采样池 P^(t+R)：本轮为其预采样并返回（供 ECP-Fetch 与下轮活跃集）。"""
        return self._ensure_pool(t + self.R)

    # ---------------- Phase C：掉线抽取 ----------------
    def sample_dropout(self, t: int, S_set: List[int]) -> Tuple[List[int], List[int]]:
        """按 dropout_rate 抽掉线集 D^(t)，保证 |Ŝ|≥τ+1（否则本轮 D=∅）。"""
        if self.dropout_rate <= 0:
            return [], sorted(S_set)
        n_drop = int(self.rng.binomial(len(S_set), self.dropout_rate))
        n_drop = min(n_drop, len(S_set) - self.tau - 1)   # 保 |Ŝ| ≥ τ+1（Lite）
        if n_drop <= 0:
            return [], sorted(S_set)
        D = sorted(self.rng.choice(sorted(S_set), size=n_drop, replace=False).tolist())
        Shat = sorted(i for i in S_set if i not in set(D))
        return D, Shat

    # ---------------- Phase D：ECP 队列 ----------------
    def push_queue(self, t: int, K_set: List[int],
                   C_j: Dict[int, object]) -> None:
        """服务器 push (t, K^(t), C^(t))，并淘汰 r ≤ t−R 的旧轮次。"""
        self.queue.append((t, sorted(K_set), dict(C_j)))
        self.evict(t)

    def evict(self, t: int) -> List[int]:
        """淘汰 r ≤ t−R 的轮次；顺带清理所有客户端对这些轮次的缓存条目。"""
        evicted = []
        while self.queue and self.queue[0][0] <= t - self.R:
            r = self.queue.popleft()[0]
            evicted.append(r)
            stale = [k for k in self.cache if k[1] == r]
            for k in stale:
                del self.cache[k]
        return evicted

    def queued_rounds(self) -> List[int]:
        return [r for r, _, _ in self.queue]

    # ---------------- Phase D：ECP-Fetch ----------------
    def prefetch(self, t: int) -> Dict[int, int]:
        """
        预采样池 P^(t+R) 后台下载其缺失轮次的 (r, C_j^(r)) 存入缓存 L_{i,j}。
        返回本回合每客户端预取字节数增量（仿真中直接执行，带宽仅用于计时）。
        """
        fetched = {i: 0 for i in range(1, self.N + 1)}
        if not self.prefetch_enabled:
            return fetched
        self.prefetch_pool(t)          # 本轮为 t+R 预采样（其预取从此刻开始）
        if not self.queue:
            return fetched
        # 所有已预采样的未来轮次候选池（P^(s)，s > t）都在后台补齐缺失轮次
        for r, K_set, C in self.queue:
            for j in K_set:
                for t_pool, pool in sorted(self.pools.items()):
                    if t_pool <= t:
                        continue
                    for i in pool:
                        if r <= self.last_round.get(i, 0):
                            continue   # i 已参与过轮 r：不再缓存，防 sync 重复应用
                        key = (i, r, j)
                        if key not in self.cache:
                            self.cache[key] = C[j]
                            self.prefetch_bytes[i] += self.prefetch_bytes_per_ct
                            fetched[i] += self.prefetch_bytes_per_ct
        for i in range(1, self.N + 1):
            if fetched[i]:
                self.prefetch_events.append({'client': i, 'after_round': t,
                                             'bytes': fetched[i]})
        return fetched

    # ---------------- Phase D：ECP-Sync ----------------
    def sync_client(self, i: int, w: np.ndarray, d: int, n: int) -> Tuple[np.ndarray, int]:
        """
        活跃客户端 i 训练前补齐缓存：按包累加 C_pre（式 16），每包 one-shot
        解密（式 17），w ← w + g̃_pre；随后清空该客户端缓存。
        返回 (新 w, 消耗的缓存包数)。
        """
        entries = [(r, j) for (ci, r, j) in self.cache if ci == i]
        if not entries:
            return w, 0
        by_pack: Dict[int, List[int]] = {}
        for r, j in entries:
            by_pack.setdefault(j, []).append(r)
        w_new = w.copy()
        for j, rounds in sorted(by_pack.items()):
            cts, a_s = [], []
            for r in sorted(rounds):
                cts.append(self.cache[(i, r, j)])
                a_s.append(self.kgc.prpg_a(r, j))
            C_pre, A_pre = self.server.ecp_accumulate(cts, a_s)
            g_pre = self.server.decrypt_prefetched(self.clients[i], C_pre, A_pre)
            seg_len = min(n, d - j * n)
            w_new[j * n:j * n + seg_len] += g_pre[:seg_len]
        for r, j in entries:
            del self.cache[(i, r, j)]
        return w_new, len(entries)


def run_experiment(config: Dict, output_dir: str = None) -> Dict:
    sys_cfg = config['system']
    data_cfg = config['data']
    model_cfg = config['model']
    ecpfl_cfg = config.get('ecpfl', {})

    device = sys_cfg.get('device', 'cpu')
    N = sys_cfg['num_clients']
    n = int(ecpfl_cfg.get('n', 4096))
    tau = int(ecpfl_cfg.get('tau', 3))
    zeta = float(ecpfl_cfg.get('sparsity_rate', 0.3))
    num_rounds = sys_cfg['num_rounds']
    num_epochs = sys_cfg['num_epochs']
    lr = sys_cfg.get('learning_rate', 0.001)
    seed = sys_cfg.get('random_seed', 42)
    max_abs_x = float(ecpfl_cfg.get('max_abs_x', 1.0))
    torch.manual_seed(seed)
    np.random.seed(seed)

    # ---------------- Phase C/D 配置 ----------------
    sampling_cfg = ecpfl_cfg.get('sampling') or {}
    K_active = int(sampling_cfg.get('active_count', N))       # 活跃集大小（默认全参与）
    R_pre = int(sampling_cfg.get('prefetch_rounds', 2))       # 预采样提前轮数
    beta = float(sampling_cfg.get('overcommit', 1.0))         # 过承诺倍数
    dropout_rate = float(ecpfl_cfg.get('dropout_rate', 0.0))
    gamma_d = float(ecpfl_cfg.get('gamma_d', 1.0))            # 式 12 残差双衰减
    gamma_s = float(ecpfl_cfg.get('gamma_s', 1.0))
    prefetch_cfg = ecpfl_cfg.get('prefetch') or {}
    prefetch_enabled = bool(prefetch_cfg.get('enabled', False))
    # ---------------- Table VI 消融开关（默认 true = 论文完整版）----------------
    abl_cfg = ecpfl_cfg.get('ablation') or {}
    abl_sparse = bool(abl_cfg.get('local_sparse', True))          # LS：本地稀疏投票（关→稠密上传全部 J 包，跳过 ESP-Vote）
    abl_residual = bool(abl_cfg.get('residual_feedback', True))    # RF：残差反馈（关→x_i = Δw_i，无残差累积）
    abl_partial = bool(abl_cfg.get('partial_participation', True)) # PRD：部分参与（关→全参与 S=[N]）
    abl_dropcomp = bool(abl_cfg.get('dropout_comp', True))         # CRD：掉线补偿（关→强制同步 D=∅）
    if not abl_partial:
        K_active = N                       # 全参与
    if not abl_dropcomp:
        dropout_rate = 0.0                 # 同步路径，无掉线

    # ---------------- Phase 0：KGC ----------------
    t0 = time.time()
    kgc = KGC(n=n, num_clients=N, tau=tau, seed=seed,
              logp=int(ecpfl_cfg.get('logp', 50)),
              delta=int(ecpfl_cfg.get('delta_scale', 1 << 20)),
              eta=int(ecpfl_cfg.get('eta', 4)))
    kgc.assert_bounds(K=max(K_active, tau), max_abs_x=max_abs_x)
    materials = kgc.distribute()
    clients = {i: ECPFLClient(kgc, materials[i]) for i in materials}
    server = ECPFLServer(kgc)
    keygen_time = time.time() - t0
    logger.info(f"[Phase 0] KGC 完成 | N={N} τ={tau} n={n} K={K_active} | keygen={keygen_time:.2f}s")

    # ---------------- Phase D：带宽仿真（仅用于预取计时）----------------
    bw_sim = None
    bw_cfg = prefetch_cfg.get('bandwidth') or {}
    if prefetch_enabled and bw_cfg:
        from ckks_fed.bandwidth_simulator import BandwidthSimulator
        bw_sim = BandwidthSimulator(
            num_clients=N,
            base_dl_bw=bw_cfg.get('base_dl_bw', 8192.0),
            base_ul_bw=bw_cfg.get('base_ul_bw', 4096.0),
            variance=bw_cfg.get('variance', 0.3),
            distribution=bw_cfg.get('distribution', 'uniform'),
            seed=seed,
            filter_low_bandwidth=bw_cfg.get('filter_low_bandwidth', False),
            min_dl_bw_kbps=bw_cfg.get('min_dl_bw_kbps', 5120.0),
            min_ul_bw_kbps=bw_cfg.get('min_ul_bw_kbps', 5120.0),
            max_dl_bw_kbps=bw_cfg.get('max_dl_bw_kbps', 8192.0),
            max_ul_bw_kbps=bw_cfg.get('max_ul_bw_kbps', 4096.0))

    # ---------------- 数据与模型 ----------------
    client_loaders, test_loader = create_client_dataloaders(
        data_cfg['dataset'], N, sys_cfg['batch_size'],
        data_dir=data_cfg.get('data_dir', './data'),
        iid=data_cfg.get('iid', True), alpha=data_cfg.get('alpha', 0.5))
    global_model = create_model(model_cfg['name'], config).to(device)
    d = flatten_params(global_model).shape[0]   # parameters + buffers（BN 统计量）
    J = (d + n - 1) // n
    n_i = {i: len(client_loaders[i - 1].dataset) for i in range(1, N + 1)}
    logger.info(f"[INIT] model={model_cfg['name']} d={d} J={J} packs | "
                f"Top-ζ={zeta} → ≈{max(1, int(np.ceil(zeta * J)))} 包/轮")

    criterion = nn.CrossEntropyLoss()
    w0 = flatten_params(global_model)
    # 每客户端独立模型副本：未活跃客户端的模型停留在其最后参与轮（ECP-Sync 补齐）
    w_clients = {i: w0.copy() for i in range(1, N + 1)}
    # 双衰减残差（式 12）：未入选包的未加权更新进入残差
    residuals = {i: np.zeros(d, dtype=np.float64) for i in range(1, N + 1)}
    # 编排器（Phase C/D；默认参数退化为 Phase A+B 全参与同步行为）
    # 线上单密文字节数（论文口径）：单多项式 n 个系数 × logQ bit / 8。
    # 密文 ct = a_j·s̃ + p̃e + pt 只传 coeffs；a_j 由 PRPG 种子公开再生、
    # S 为共享解密密钥，mask(a_j·s̃) 不在线上传输。内存 CRT(int64×2素数) 表示不计入通信。
    ct_coeff_bytes = n * kgc.ring.Q.bit_length() // 8
    orch = ECPFLOrchestrator(
        kgc, clients, server, num_clients=N,
        active_count=K_active, prefetch_rounds=R_pre, overcommit=beta,
        tau=tau, dropout_rate=dropout_rate, prefetch_enabled=prefetch_enabled,
        prefetch_bytes_per_ct=ct_coeff_bytes, seed=seed)
    metrics = {'rounds': []}
    # ---- 计时口径（最慢客户端）：bw_sim 未启用时的兜底带宽（kbps→bps）----
    default_dl_bps = float(bw_cfg.get('base_dl_bw', 8192.0)) * 1024.0
    default_ul_bps = float(bw_cfg.get('base_ul_bw', 4096.0)) * 1024.0
    # 每客户端同步下行（FV）累计与带宽档案（供 Table VIII）
    client_sync_dl_bytes: Dict[int, int] = {i: 0 for i in range(1, N + 1)}

    for t in range(1, num_rounds + 1):
        rt = time.time()
        # ---- Phase C：确认活跃集 S^(t)，固定权重 ω_i = n_i/Σ_{u∈S}n_u ----
        S_set = orch.active_set(t)
        n_S = sum(n_i[i] for i in S_set)
        omegas = {i: n_i[i] / n_S for i in S_set}
        if K_active < N or dropout_rate > 0:
            logger.info(f"[ROUND] t={t} 活跃集 S={S_set}")

        # ---- Phase D：ECP-Sync（训练前补齐各自缓存，式 16/17）----
        sync_counts = {}
        for i in S_set:
            w_clients[i], sync_counts[i] = orch.sync_client(i, w_clients[i], d, n)

        # ---- 本地训练（明文，各自从本地模型副本出发；逐客户端计时）----
        train_losses, train_accs = [], []
        train_times: Dict[int, float] = {}
        xs: Dict[int, np.ndarray] = {}
        for i in S_set:
            tt_train = time.time()
            local_model = create_model(model_cfg['name'], config).to(device)
            assign_params(local_model, w_clients[i])
            optimizer = torch.optim.Adam(local_model.parameters(), lr=lr)
            local_model.train()
            for _ in range(num_epochs):
                for images, labels in client_loaders[i - 1]:
                    images, labels = images.to(device), labels.to(device)
                    optimizer.zero_grad()
                    loss = criterion(local_model(images), labels)
                    loss.backward()
                    optimizer.step()
            train_losses.append(float(loss.item()))
            correct = sum((local_model(images.to(device)).argmax(1) ==
                           labels.to(device)).sum().item()
                          for images, labels in client_loaders[i - 1])
            train_accs.append(correct / n_i[i])
            train_times[i] = time.time() - tt_train
            # x_i = Δw_i + r_i（式 12 的补偿更新）
            xs[i] = flatten_params(local_model) - w_clients[i] + residuals[i]

        # ---- Phase C：掉线抽取（保 |Ŝ| ≥ τ，否则 D=∅）----
        D_set, Shat_set = orch.sample_dropout(t, S_set)
        if D_set:
            logger.info(f"[ROUND] t={t} 掉线 D={D_set} → Ŝ={Shat_set}")

        # ---- Phase 1：ESP-Vote & ESP-Tally（LS 关闭 → 稠密上传全部 J 包，跳过投票）----
        t1 = time.time()
        vote_times: Dict[int, float] = {}
        if abl_sparse:
            vote_bits = {i: np.zeros(J, dtype=np.int64) for i in S_set}
            vote_cts = []
            for i in S_set:
                tv_i = time.time()
                top = select_top_packs(xs[i], J, n, zeta)
                vote_bits[i][top] = 1
                vote_cts.append(clients[i].esp_vote(t, S_set, vote_bits[i]))
                vote_times[i] = time.time() - tv_i
            nu = server.esp_tally(vote_cts, J)
            # 共识阈值 θ 独立于客户端投票稀疏度 ζ：TH-θ（ν≥θ|S|）/ RK-θ（前 ⌈θJ⌉ 名）
            vote_theta = float(ecpfl_cfg.get('vote_threshold', 0.3))
            K_set = server.consensus(nu, ecpfl_cfg.get('vote_rule', 'th'), vote_theta, len(S_set))
        else:
            K_set = list(range(J))
        vote_time = time.time() - t1

        # ---- 残差更新（式 12：r_i ← γ_d·γ_s^{ℓ-1}·(x_i ⊙ (1−k))，ℓ = 距上次参与）----
        k_full = np.zeros(J, dtype=np.int64)
        k_full[K_set] = 1
        mask = np.repeat(k_full, n)[:d]
        if abl_residual:
            for i in S_set:
                last_t = orch.last_round.get(i, t)         # 首次参与 ℓ=1
                ell = t - last_t
                residuals[i] = gamma_d * (gamma_s ** (ell - 1)) * xs[i] * (1.0 - mask)
                orch.last_round[i] = t
            for i in range(1, N + 1):                      # 未参与客户端残差同步衰减
                if i not in set(S_set) and i in orch.last_round:
                    ell = t - orch.last_round[i]
                    residuals[i] *= gamma_d * (gamma_s ** (ell - 1))
        else:
            for i in S_set:
                residuals[i] = np.zeros(d, dtype=np.float64)   # RF 关闭：无残差累积
                orch.last_round[i] = t

        # ---- Phase 2：ESP-Enc（固定权重 ω_i，入选包；掉线者不上传；逐客户端计时）----
        t2 = time.time()
        enc_times: Dict[int, float] = {}
        pack_cts: Dict[int, list] = {j: [] for j in K_set}
        pack_srcs: Dict[int, list] = {j: [] for j in K_set}
        for i in Shat_set:
            te_i = time.time()
            for j in K_set:
                pack = np.zeros(n, dtype=np.float64)
                seg = xs[i][j * n:(j + 1) * n]
                pack[:len(seg)] = seg
                pack_cts[j].append(clients[i].esp_enc(t, j, S_set, pack, omegas[i]))
                pack_srcs[j].append(i)
            enc_times[i] = time.time() - te_i
        comp_cts: Dict[int, list] = {j: [] for j in K_set}
        comp_counts: Dict[int, int] = {i: 0 for i in Shat_set}
        if D_set:   # 掉线补偿（式 14/15）：存活者对每个入选包上传 δ
            for i in Shat_set:
                for j in K_set:
                    comp_cts[j].append(clients[i].esp_comp(t, j, S_set, Shat_set))
                    comp_counts[i] += 1
        enc_time = time.time() - t2

        # ---- Phase 3：ESP-Agg（同步式 13 / 掉线式 15）----
        t3 = time.time()
        C_j = {j: server.esp_agg(pack_cts[j], comp_cts[j] or None) for j in K_set}
        agg_time = time.time() - t3

        # ---- Phase D：服务器滑动队列 push (t, K^(t), C^(t))，淘汰 r ≤ t−R ----
        orch.push_queue(t, K_set, C_j)
        # ECP-Fetch：预采样池 P^(t+R) 后台下载缺失轮次包密文（记 PV）
        t_pf = time.time()
        fetched = orch.prefetch(t)
        prefetch_time = time.time() - t_pf
        prefetch_bytes_round = sum(fetched.values())

        # ---- 活跃客户端只下载各自缺失的包密文（不再整模型下发），one-shot 解密 ----
        t4 = time.time()
        dec_packs: Dict[int, np.ndarray] = {}
        for j in K_set:
            dec_packs[j] = clients[Shat_set[0]].decrypt_pack(t, j, C_j[j])
        cache_hits = 0
        download_bytes = 0
        client_hits: Dict[int, int] = {i: 0 for i in Shat_set}
        client_dl_bytes: Dict[int, int] = {i: 0 for i in Shat_set}
        for i in Shat_set:
            w_i = w_clients[i]
            for j in K_set:
                if (i, t, j) in orch.cache:      # 预取已覆盖本轮 → 免下载
                    cache_hits += 1
                    client_hits[i] += 1
                else:
                    download_bytes += ct_coeff_bytes
                    client_dl_bytes[i] += ct_coeff_bytes
                seg_len = min(n, d - j * n)
                w_i[j * n:j * n + seg_len] += dec_packs[j][:seg_len]
                # 本轮已应用：清掉未来池为本客户端预取的同轮缓存，防止 sync 重复应用
                orch.cache.pop((i, t, j), None)
        dec_time = time.time() - t4

        # ---- 每客户端模拟 UT/DT 与最慢客户端口径 TT（与 main.py 基线同口径）----
        # 客户端 i 每轮上行 = 1 投票密文 + |K| 包密文 + 补偿密文；下行 = 未命中缓存的包密文
        ut_times: Dict[int, float] = {}
        dt_times: Dict[int, float] = {}
        for i in S_set:
            up_i = (1 + (len(K_set) + comp_counts.get(i, 0) if i in Shat_set else 0)) * ct_coeff_bytes
            dl_i = client_dl_bytes.get(i, 0)
            if bw_sim is not None:
                ut_times[i] = bw_sim.estimate_upload_time(i - 1, up_i * 8)
                dt_times[i] = bw_sim.estimate_download_time(i - 1, dl_i * 8)
            else:
                ut_times[i] = up_i * 8 / (default_ul_bps)
                dt_times[i] = dl_i * 8 / (default_dl_bps)
            client_sync_dl_bytes[i] = client_sync_dl_bytes.get(i, 0) + dl_i
        # 最慢客户端轮时 = 本地训练 + 投票 + 加密 + 模拟上传 + 模拟下载（服务端聚合不占客户端）
        client_round_times = {
            i: train_times[i] + vote_times.get(i, 0.0) + enc_times.get(i, 0.0)
               + ut_times[i] + dt_times[i]
            for i in S_set}
        tt_client = max(client_round_times, key=client_round_times.get)
        tt_round = client_round_times[tt_client]
        ut_round = max(ut_times.values())
        dt_round = max(dt_times.values())

        # ---- 评估（取本轮活跃客户端的模型；其已同步全部缺失轮次）----
        assign_params(global_model, w_clients[Shat_set[0]])
        test_loss, test_acc = evaluate(global_model, test_loader, criterion, device)

        num_enc = sum(len(v) for v in pack_cts.values())
        upload_bytes = (len(S_set) + num_enc + sum(len(v) for v in comp_cts.values())) * ct_coeff_bytes
        # 下行 = 活跃客户端各自缺失的包密文（缓存命中免下载；预取字节另记 PV/TV）
        round_time = time.time() - rt
        metrics['rounds'].append({
            'round': t, 'K': len(K_set), 'vote_rule': ecpfl_cfg.get('vote_rule', 'rk'),
            'active_set': S_set, 'dropouts': D_set, 'survivors': Shat_set,
            'train_loss': float(np.mean(train_losses)),
            'train_acc': float(np.mean(train_accs)),
            'test_loss': test_loss, 'test_acc': test_acc,
            'upload_bytes': upload_bytes, 'download_bytes': download_bytes,
            'prefetch_bytes': prefetch_bytes_round, 'cache_hits': cache_hits,
            'synced_packs': sum(sync_counts.values()),
            'queue_rounds': orch.queued_rounds(),
            'vote_time': vote_time, 'enc_time': enc_time,
            'agg_time': agg_time, 'dec_time': dec_time, 'prefetch_time': prefetch_time,
            'round_time': round_time,
            'tt_round': tt_round, 'tt_client': tt_client,
            'ut_round': ut_round, 'dt_round': dt_round,
        })
        logger.info(f"[ROUND] t={t} | K={len(K_set)}/{J} | 掉线={len(D_set)} | "
                    f"train_acc={np.mean(train_accs):.4f} | "
                    f"test_acc={test_acc:.2f}% | ↑{upload_bytes / 1e6:.2f}MB "
                    f"↓{download_bytes / 1e6:.2f}MB | 预取{prefetch_bytes_round / 1e6:.2f}MB "
                    f"| {round_time:.1f}s")

    total_upload = sum(r['upload_bytes'] for r in metrics['rounds'])
    total_download = sum(r['download_bytes'] for r in metrics['rounds'])
    total_prefetch = sum(r['prefetch_bytes'] for r in metrics['rounds'])
    summary = {
        'config': config,
        'model_params': d, 'pack_count': J,
        'final_test_acc': metrics['rounds'][-1]['test_acc'],
        'total_upload_mb': total_upload / 1e6,
        'total_download_mb': total_download / 1e6,
        'total_prefetch_mb': total_prefetch / 1e6,
        # TV = Σ(上行 + 同步下行 FV)；PV = 预取总量（空闲时间后台传输，单列不计入 TV）
        'total_tv_mb': (total_upload + total_download) / 1e6,
        'total_fv_mb': total_download / 1e6,
        'total_pv_mb': total_prefetch / 1e6,
        'per_client_prefetch_bytes': orch.prefetch_bytes,
        'per_client_sync_download_bytes': client_sync_dl_bytes,
        # ---- 最慢客户端口径计时（与 main.py 基线/FedFetch 一致）----
        'total_tt_sim': sum(r['tt_round'] for r in metrics['rounds']),
        'total_ut_sim': sum(r['ut_round'] for r in metrics['rounds']),
        'total_dt_sim': sum(r['dt_round'] for r in metrics['rounds']),
        'total_round_real_time': sum(r['round_time'] for r in metrics['rounds']),
        'per_client_bw': {
            i: {'dl_kbps': bw_sim.get_dl_bw_kbps(i - 1) if bw_sim else default_dl_bps / 1024.0,
                'ul_kbps': bw_sim.get_ul_bw_kbps(i - 1) if bw_sim else default_ul_bps / 1024.0}
            for i in range(1, N + 1)},
        'keygen_time': keygen_time,
        'rounds': metrics['rounds'],
    }
    if output_dir:
        # 与其它实验一致：结果写入时间戳子目录，并保存配置副本
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(output_dir, f"experiment_{ts}_{data_cfg['dataset']}")
        os.makedirs(output_dir, exist_ok=True)
        import yaml as _yaml
        with open(os.path.join(output_dir, 'config.yaml'), 'w', encoding='utf-8') as f:
            _yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        with open(os.path.join(output_dir, 'ecpfl_results.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        _write_markdown(summary, os.path.join(output_dir, 'ecpfl_results.md'))
        logger.info(f"[DONE] 结果已保存至 {output_dir}/ecpfl_results.json|md")
    return summary


def _write_markdown(summary: Dict, path: str) -> None:
    """每轮 (t, K, 掉线数, 精度, 上行, 下行, 预取) 表格 + TV/PV 汇总。"""
    lines = [
        "# ECPFL (V17) Phase A-D 实验结果",
        "",
        f"- 模型参数量 d = {summary['model_params']}，包数 J = {summary['pack_count']}",
        f"- 最终测试精度：**{summary['final_test_acc']:.2f}%**",
        f"- 总上行：{summary['total_upload_mb']:.2f} MB",
        f"- 总下行 FV（活跃客户端同步包密文）：{summary['total_fv_mb']:.2f} MB",
        f"- 总预取 PV（空闲时间后台，不计入 TV）：{summary['total_pv_mb']:.2f} MB",
        f"- 总通信 TV = 上行 + 同步下行：{summary['total_tv_mb']:.2f} MB",
        f"- 总训练时长 TT（最慢客户端口径）：**{summary['total_tt_sim']:.1f} s**"
        f"（UT={summary['total_ut_sim']:.1f} s，DT={summary['total_dt_sim']:.1f} s）",
        f"- 总真实串行时间（参考）：{summary['total_round_real_time']:.1f} s",
        "",
        "| 轮次 t | 共识包数 K | 掉线数 | 活跃集 | 测试精度(%) | 训练精度 | 上行(MB) | 下行(MB) | 预取(MB) | 缓存命中 | TT(s) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary['rounds']:
        lines.append(
            f"| {r['round']} | {r['K']} | {len(r['dropouts'])} | "
            f"{','.join(map(str, r['active_set']))} | {r['test_acc']:.2f} | "
            f"{r['train_acc']:.4f} | {r['upload_bytes'] / 1e6:.3f} | "
            f"{r['download_bytes'] / 1e6:.3f} | {r['prefetch_bytes'] / 1e6:.3f} | {r['cache_hits']} | "
            f"{r['tt_round']:.2f} |")
    pf = summary['per_client_prefetch_bytes']
    fvd = summary.get('per_client_sync_download_bytes', {})
    bwp = summary.get('per_client_bw', {})
    lines += ["", "## 每客户端通信明细", "",
              "| 客户端 | 预取PV(MB) | 同步FV(MB) | DL(Mbps) | UL(Mbps) |", "|---|---|---|---|---|"]
    for i in sorted(pf):
        bw_i = bwp.get(i, {})
        lines.append(f"| {i} | {pf[i] / 1e6:.3f} | {fvd.get(i, 0) / 1e6:.3f} | "
                     f"{bw_i.get('dl_kbps', 0) / 1000.0:.2f} | {bw_i.get('ul_kbps', 0) / 1000.0:.2f} |")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description='ECPFL (V17) Phase A-D 端到端')
    parser.add_argument('--config', required=True, help='YAML 配置文件')
    parser.add_argument('--output-dir', default=None, help='结果输出目录')
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    run_experiment(config, args.output_dir)


if __name__ == '__main__':
    main()
