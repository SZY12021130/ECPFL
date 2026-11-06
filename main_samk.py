# -*- coding: utf-8 -*-
"""
SAMK（TDSC 2025）端到端实验：固定集合采样 → 加密上传（可能掉线）→ 聚合 → 独立解密
====================================================================================

与项目的结合点（沿用现有 prefetch / sticky 采样基础设施）：
  1. **先采样，确定固定集合**：用 ``create_client_selection_strategy`` +
     ``PrefetchPoolManager`` 提前 R 轮预采样（过承诺 OC 倍），本轮取池 → OC 截断
     得到固定集合 S^(t)（与 main.py 的预取实验同一条路径）。
  2. **固定集合内加密上传时可能掉线**：每个客户端按 ``sampling.dropout_rate``
     在**上传阶段**掉线，服务器只聚合在线集合 H = S \\ D（SAMK Algorithm 4）。
  3. 客户端各自持 BFV + Paillier 密钥，服务器只有 Paillier 密钥；在线客户端
     用自己一把 Paillier 私钥 + N-1 个公开点插值恢复 F(x)，独立解出 Σ_{j∈H} m_j。
  4. 每轮记录：固定集合、上传前掉线、在线集合、解密误差、上下行通信量、
     各阶段耗时；并验证“上传后掉线重连可解密 / 上传前掉线不可解密”。

两种模式：
  ``samk.mode = synthetic``  只跑密码学流程（随机更新，秒级出结果，默认）
  ``samk.mode = fl``         真实联邦训练（项目 data/models，明文训练 + SAMK 加密聚合）

用法：
  python main_samk.py --config configs/samk.yaml
  python main_samk.py --config configs/samk.yaml --output-dir results_samk
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml

from ckks_fed.client_selection import PrefetchPoolManager, create_client_selection_strategy
from ckks_fed.samk_crypto import (SAMKAccessError, SAMKParams, SAMKScheme,
                                  SAMKUpload)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-7s %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


# =============================================================================
# 模型工具（fl 模式）
# =============================================================================
def flatten_params(model) -> np.ndarray:
    return np.concatenate([p.detach().cpu().numpy().flatten()
                           for p in model.parameters()]).astype(np.float64)


def assign_params(model, flat: np.ndarray) -> None:
    import torch
    with torch.no_grad():
        offset = 0
        for p in model.parameters():
            numel = p.numel()
            p.copy_(torch.tensor(flat[offset:offset + numel].reshape(p.shape),
                                 dtype=p.dtype, device=p.device))
            offset += numel


# =============================================================================
# 采样：固定集合 + 上传阶段掉线
# =============================================================================
class FixedSetSampler:
    """
    固定集合采样器（预采样池 + OC 截断），与项目 main.py 的预取路径一致。

    * ``presample_round(t)``  提前 R 轮把候选池写入 ``PrefetchPoolManager``
    * ``fixed_set(t)``        取池并截断到 K 个 -> 本轮固定集合 S^(t)（返回 1-based id）
    * ``sample_upload_dropout`` 在上传阶段抽掉线集 D，保 |H| ≥ min_online
    """

    def __init__(self, config: Dict, num_clients: int, active_count: int,
                 overcommit: float, prefetch_rounds: int, dropout_rate: float,
                 min_online: int, seed: int = 42):
        self.num_clients = num_clients
        self.K = min(active_count, num_clients)
        self.oc = max(1.0, overcommit)
        self.R = max(0, prefetch_rounds)
        self.dropout_rate = float(dropout_rate)
        self.min_online = max(1, min(min_online, self.K))
        self.rng = np.random.default_rng(seed)

        self.strategy = create_client_selection_strategy(config, num_clients)
        self.pool = PrefetchPoolManager(num_clients, overcommitment=self.oc)

    # ---------------- 预采样 ----------------
    def presample_round(self, target_round: int) -> List[int]:
        if self.pool.get_pool(target_round):
            return list(self.pool.get_pool(target_round))
        ids = self.pool.presample(
            target_round, self.K, self.strategy,
            clients=list(range(self.num_clients)), overcommitment=self.oc)
        logger.info(f"[SAMPLING] 预采样 target={target_round} "
                    f"pool={len(ids)} (K={self.K}, OC={self.oc}) ids={sorted(ids)}")
        return ids

    def warmup(self, rounds: int) -> None:
        for t in range(1, min(self.R, rounds) + 1):
            self.presample_round(t)

    # ---------------- 固定集合 ----------------
    def fixed_set(self, t: int) -> Tuple[List[int], List[int]]:
        """返回 (固定集合 S^(t) 的 1-based id, 池中因 OC 截断未入选的 id)。"""
        if not self.pool.get_pool(t):
            self.presample_round(t)
        cand = list(self.pool.get_pool(t))          # 0-based
        selected = cand[:self.K]
        truncated = cand[self.K:]
        return [c + 1 for c in selected], [c + 1 for c in truncated]

    # ---------------- 上传阶段掉线 ----------------
    def sample_upload_dropout(self, fixed: List[int]) -> Tuple[List[int], List[int]]:
        """按 dropout_rate 抽上传前掉线集 D，保证 |H| ≥ min_online。"""
        if self.dropout_rate <= 0 or len(fixed) <= self.min_online:
            return [], sorted(fixed)
        mask = self.rng.random(len(fixed)) < self.dropout_rate
        n_drop = int(mask.sum())
        n_drop = min(n_drop, len(fixed) - self.min_online)
        if n_drop <= 0:
            return [], sorted(fixed)
        order = np.argsort(-mask.astype(np.int64), kind='stable')  # 掉线者优先
        drop = sorted(fixed[j] for j in order[:n_drop])
        online = sorted(i for i in fixed if i not in set(drop))
        return drop, online


# =============================================================================
# 主实验
# =============================================================================
def run_experiment(config: Dict, output_dir: Optional[str] = None,
                   tag: Optional[str] = None) -> Dict:
    sys_cfg = config.get('system', {})
    samk_cfg = config.get('samk', {})
    samp_cfg = config.get('sampling', {})

    N = int(sys_cfg.get('num_clients', 12))
    num_rounds = int(sys_cfg.get('num_rounds', 3))
    seed = int(sys_cfg.get('random_seed', 42))
    np.random.seed(seed)

    mode = str(samk_cfg.get('mode', 'synthetic')).lower()
    if mode not in ('synthetic', 'fl'):
        raise ValueError(f"未知 samk.mode={mode}（synthetic | fl）")

    K = int(samp_cfg.get('active_count', N))
    OC = float(samp_cfg.get('overcommit', 1.5))
    R = int(samp_cfg.get('prefetch_rounds', 2))
    dropout_rate = float(samp_cfg.get('dropout_rate', 0.25))
    min_online = int(samk_cfg.get('min_online', 2))
    max_dim = int(samk_cfg.get('max_dim', 1024))

    # ---------------- Algorithm 1 + 2：Setup / KeyGen ----------------
    params = SAMKParams(
        n=int(samk_cfg.get('n', 1024)),
        t_bits=int(samk_cfg.get('t_bits', 40)),
        scale_bits=int(samk_cfg.get('scale_bits', 16)),
        paillier_bits=int(samk_cfg.get('paillier_bits', 512)),
        seed=seed,
    )
    t0 = time.time()
    scheme = SAMKScheme(params, num_clients=N).setup()
    keygen_time = time.time() - t0
    pp = scheme.public_params
    logger.info(f"[SETUP] N={N} n={params.n} Q={pp['q_bits']}bit "
                f"Paillier={params.paillier_bits}bit 槽宽={pp['slot_bits']}bit "
                f"每密文{pp['max_slots']}个点 | keygen={keygen_time:.2f}s")

    sampler = FixedSetSampler(config, N, K, OC, R, dropout_rate, min_online, seed)
    sampler.warmup(num_rounds)
    sampler.presample_round(num_rounds)  # 末轮预留

    # ---------------- 数据 / 模型（仅 fl 模式）----------------
    if mode == 'fl':
        import torch
        import torch.nn as nn
        from ckks_fed.data import create_client_dataloaders, evaluate
        from ckks_fed.models import create_model

        data_cfg = config['data']
        device = sys_cfg.get('device', 'cpu')
        torch.manual_seed(seed)
        loaders, test_loader = create_client_dataloaders(
            data_cfg['dataset'], N, int(sys_cfg.get('batch_size', 64)),
            data_dir=data_cfg.get('data_dir', './data'),
            iid=data_cfg.get('iid', True), alpha=data_cfg.get('alpha', 0.5))
        global_model = create_model(config['model']['name'], config).to(device)
        criterion = nn.CrossEntropyLoss()
        w_global = flatten_params(global_model)
        dim_full = w_global.size
        lr = float(sys_cfg.get('learning_rate', 0.001))
        epochs = int(sys_cfg.get('num_epochs', 1))
        logger.info(f"[INIT] mode=fl model={config['model']['name']} d={dim_full} "
                    f"加密维度={min(dim_full, max_dim) if max_dim > 0 else dim_full}")
    else:
        dim_full = int(samk_cfg.get('dim', 1024))
        update_std = float(samk_cfg.get('update_std', 0.05))
        synth_rng = np.random.default_rng(seed + 1)
        logger.info(f"[INIT] mode=synthetic d={dim_full} std={update_std}")

    dim = dim_full if max_dim <= 0 else min(dim_full, max_dim)
    rounds: List[Dict] = []
    late_fetch_checked = False

    for t in range(1, num_rounds + 1):
        rt = time.time()
        # ---- 1) 固定集合（预采样池 -> OC 截断）----
        fixed, truncated = sampler.fixed_set(t)
        if t + R <= num_rounds:
            sampler.presample_round(t + R)

        # ---- 2) 本地训练 / 生成更新 ----
        t_train = time.time()
        if mode == 'fl':
            updates: Dict[int, np.ndarray] = {}
            for cid in fixed:
                local_model = create_model(config['model']['name'], config).to(device)
                assign_params(local_model, w_global)
                opt = torch.optim.Adam(local_model.parameters(), lr=lr)
                local_model.train()
                loader = loaders[cid - 1]
                for _ in range(epochs):
                    for images, labels in loader:
                        images, labels = images.to(device), labels.to(device)
                        opt.zero_grad()
                        loss = nn.functional.cross_entropy(local_model(images), labels)
                        loss.backward()
                        opt.step()
                delta = flatten_params(local_model) - w_global
                updates[cid] = delta[:dim]      # 原型裁剪（max_dim<=0 时即全量）
            train_time = time.time() - t_train
        else:
            updates = {cid: synth_rng.normal(0, update_std, dim) for cid in fixed}
            train_time = time.time() - t_train

        # ---- 3) 上传阶段掉线：只聚合 H ----
        dropped, online = sampler.sample_upload_dropout(fixed)
        if not online:
            logger.warning(f"[ROUND] t={t} 无在线客户端，跳过")
            continue

        # ---- 4) Algorithm 3：在线客户端加密上传 ----
        t_enc = time.time()
        uploads: Dict[int, SAMKUpload] = {}
        for cid in online:
            uploads[cid] = scheme.client_upload(cid, updates[cid])
        enc_time = time.time() - t_enc

        # ---- 5) Algorithm 4：服务器聚合（无 BFV 私钥）----
        res = scheme.aggregate(uploads, dropouts=dropped)

        # ---- 6) Algorithm 5：在线客户端独立解密 ----
        t_dec = time.time()
        expected = np.sum([updates[c] for c in online], axis=0)
        dec_errors = []
        dec_first = None
        for cid in online:
            got = scheme.client_decrypt(cid, res.downloads[cid])
            if dec_first is None:
                dec_first = got
            dec_errors.append(float(np.max(np.abs(got - expected))))
        dec_time = time.time() - t_dec
        max_err = max(dec_errors)

        # ---- 7) 掉线语义验证（每轮都验，结果写入 metrics）----
        late_ok, blocked_ok = None, None
        if dropped:
            try:
                scheme.server.fetch_download(dropped[0])
                blocked_ok = False
            except SAMKAccessError:
                blocked_ok = True
        if not late_fetch_checked and online:
            # 模拟“上传成功后掉线、稍后重连取结果”
            reconnected = online[-1]
            late = scheme.server.fetch_download(reconnected)
            late_ok = bool(np.max(np.abs(
                scheme.client_decrypt(reconnected, late) - expected)) <=
                len(online) * 0.5 / params.scale + 1e-9)
            late_fetch_checked = True

        # ---- 8) 更新全局模型 / 评估 ----
        if mode == 'fl':
            # dec_first = Σ_{j∈H} m_j（已含 H 内所有客户端），FedAvg 取均值
            w_global[:dim] += dec_first / len(online)
            assign_params(global_model, w_global)
            test_loss, test_acc = evaluate(global_model, test_loader, criterion, device)
        else:
            test_loss, test_acc = float('nan'), float('nan')

        round_time = time.time() - rt
        rounds.append({
            'round': t,
            'fixed_set': fixed,
            'oc_truncated': truncated,
            'dropouts_before_upload': dropped,
            'online': online,
            'num_chunks': int(np.ceil(dim / params.n)),
            'dim': dim,
            'max_abs_err': max_err,
            'late_fetch_ok': late_ok,
            'preupload_dropout_blocked': blocked_ok,
            'upload_bytes': res.upload_bytes,
            'download_bytes': res.download_bytes,
            'train_time': train_time,
            'enc_time': enc_time,
            'agg_time': res.agg_time,
            'dec_time': dec_time,
            'round_time': round_time,
            'test_loss': test_loss,
            'test_acc': test_acc,
        })
        logger.info(
            f"[ROUND] t={t} | 固定集合={len(fixed)} 掉线={len(dropped)} 在线={len(online)} | "
            f"误差={max_err:.2e} | ↑{res.upload_bytes / 1e6:.2f}MB "
            f"↓{res.download_bytes / 1e6:.2f}MB | enc={enc_time:.2f}s "
            f"agg={res.agg_time:.2f}s dec={dec_time:.2f}s | {round_time:.1f}s")

    summary = {
        'config': config,
        'mode': mode,
        'params': pp,
        'keygen_time': keygen_time,
        'dim': dim,
        'num_rounds': len(rounds),
        'rounds': rounds,
        'total_upload_mb': sum(r['upload_bytes'] for r in rounds) / 1e6,
        'total_download_mb': sum(r['download_bytes'] for r in rounds) / 1e6,
        'avg_client_enc_time': float(np.mean([r['enc_time'] / max(1, len(r['online']))
                                              for r in rounds])),
        'max_abs_err': max((r['max_abs_err'] for r in rounds), default=None),
        'final_test_acc': rounds[-1]['test_acc'] if rounds else None,
    }

    if output_dir:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = f"samk_{mode}_{tag}_{ts}" if tag else f"samk_{mode}_{ts}"
        out = os.path.join(output_dir, name)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, 'config.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        with open(os.path.join(out, 'samk_results.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        with open(os.path.join(out, 'samk_results.md'), 'w', encoding='utf-8') as f:
            f.write(_to_markdown(summary))
        logger.info(f"[DONE] 结果已保存至 {out}/samk_results.json|md")
    return summary


def _to_markdown(summary: Dict) -> str:
    pp = summary['params']
    lines = [
        "# SAMK（TDSC 2025）端到端实验结果",
        "",
        f"- 模式：**{summary['mode']}**",
        f"- BFV：N={pp['n']}，log Q={pp['q_bits']}，t=2^{int(pp['t'].bit_length()) - 1}，"
        f"Δ={pp['delta']}",
        f"- Paillier：{pp['paillier_bits']} bit，打包槽宽 {pp['slot_bits']} bit，"
        f"每密文 {pp['max_slots']} 个点",
        f"- 加密维度 d={summary['dim']}，分块数 "
        f"{int(np.ceil(summary['dim'] / pp['n']))}",
        f"- 密钥生成（Setup+KeyGen）：{summary['keygen_time']:.2f}s",
        f"- 每客户端平均加密耗时：{summary['avg_client_enc_time']:.2f}s",
        f"- 总上行 {summary['total_upload_mb']:.2f} MB / "
        f"总下行 {summary['total_download_mb']:.2f} MB",
        f"- 解密最大绝对误差：{summary['max_abs_err']:.2e}",
    ]
    if summary['final_test_acc'] is not None and not np.isnan(summary['final_test_acc']):
        lines.append(f"- 最终测试精度：**{summary['final_test_acc']:.2f}%**")
    lines += [
        "",
        "## 实现与依赖（密码学库）",
        "",
        "- **不使用任何第三方密码学库**：未依赖 phe / tenseal / Pyfhel / sympy，"
        "全部自研实现（保证与项目 `ckks_fed/eshe.py` 同源的环算术）。",
        "- BFV：纯 Python + NumPy；环 R_Q = Z_Q[X]/(X^N+1) 复用项目自研 "
        "`ckks_fed/eshe.py:RingContext`（双素数 CRT + negacyclic NTT，Q≈2^61）。",
        "- Paillier：纯 Python 大整数实现（g=N+1 加速、"
        "同态乘法聚合、自定义 Miller-Rabin 素数生成）。",
        "- 拉格朗日插值：NumPy 向量化 + 预计算插值矩阵（Z_q 上精确恢复）。",
        f"- 运行环境：Python {sys.version.split()[0]}，NumPy {np.__version__}。",
    ]
    lines += [
        "",
        "| 轮次 | 固定集合 | 上传前掉线 | 在线 | 误差 | 上行(MB) | 下行(MB) | 加密(s) | 聚合(s) | 解密(s) | 重连可解 | 掉线者被拒 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary['rounds']:
        lines.append(
            f"| {r['round']} | {r['fixed_set']} | {r['dropouts_before_upload']} | "
            f"{len(r['online'])} | {r['max_abs_err']:.2e} | "
            f"{r['upload_bytes'] / 1e6:.3f} | {r['download_bytes'] / 1e6:.3f} | "
            f"{r['enc_time']:.2f} | {r['agg_time']:.2f} | {r['dec_time']:.2f} | "
            f"{r['late_fetch_ok']} | {r['preupload_dropout_blocked']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description='SAMK（TDSC 2025）端到端实验')
    parser.add_argument('--config', required=True, help='YAML 配置文件')
    parser.add_argument('--output-dir', default=None, help='结果输出目录')
    parser.add_argument('--tag', default=None, help='结果子目录标签（如 d20）')
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    run_experiment(config, args.output_dir, tag=args.tag)


if __name__ == '__main__':
    main()
