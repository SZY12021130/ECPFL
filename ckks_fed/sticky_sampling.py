"""
Sticky Sampling 管理器 (FedFetch-style)
=========================================

FedFetch 中的 Sticky Sampling 机制：
1. 维护 sticky_group：带宽较好的客户端候选池
2. 每轮从 sticky_group 中选大部分 (num_needed - change_num)
3. 从 sticky_group 外部随机选少量 (change_num) 作为替换
4. 更新 sticky_group：移除最老的，加入新选中的
5. 为 target_round = cur_round + max_prefetch_round 预采样客户端列表
6. 被预取但未选中的客户端 score 累积，增加未来被选中的概率

配置开关 (config.yaml -> prefetch):
    use_sticky_sampling: false/true
    overcommitment: 1.0          # OC = 预采样数 / 实际需要数
    sticky_decay: 0.9            # 选中后 score 衰减因子
    sticky_group_size: 8         # sticky group 大小 k
    sticky_change_num: 1         # 每轮替换的客户端数
"""

import logging
from typing import Dict, List, Optional

import numpy as np
from ckks_fed.log_utils import LogTag, tag_info

logger = logging.getLogger(__name__)


class StickySamplingManager:
    """
    FedFetch 风格的 Sticky Sampling 客户端选择管理器。

    核心机制：
    - sticky_group: 带宽较好的客户端候选池，每轮优先从中选择
    - change_num: 每轮从外部随机引入的新客户端数，保持多样性
    - 预采样池 (presample_pool): {target_round: {client_id: sticky_score}}
    - 全局 sticky score: 客户端累积的预取收益
    """

    def __init__(
        self,
        num_clients: int,
        overcommitment: float = 1.0,
        decay_factor: float = 0.9,
        seed: int = 42,
        use_sticky: bool = True,
        sticky_group_size: int = None,
        change_num: int = 1,
        bandwidth_info: Dict[int, float] = None,
    ):
        """
        Args:
            num_clients: 客户端总数
            overcommitment: 过承诺比例 OC
            decay_factor: 选中训练后 sticky score 的衰减因子 [0,1]
            seed: 随机种子
            use_sticky: True=STICKY 模式, False=UNIFORM 模式
            sticky_group_size: sticky group 大小 k（默认 num_clients）
            change_num: 每轮从外部替换的客户端数
            bandwidth_info: {client_id: dl_bw_kbps}，用于初始化 sticky_group
        """
        self.num_clients = num_clients
        self.overcommitment = max(1.0, overcommitment)
        self.decay_factor = max(0.0, min(1.0, decay_factor))
        self.use_sticky = use_sticky
        self.sticky_group_size = sticky_group_size if sticky_group_size is not None else num_clients
        self.change_num = max(0, min(change_num, num_clients))
        self.bandwidth_info = bandwidth_info or {}
        np.random.seed(seed)

        # 预采样池: {target_round: {client_id: sticky_score}}
        self.presample_pool: Dict[int, Dict[int, float]] = {}

        # 客户端全局 sticky score（累积未被选中的预取收益）
        self.sticky_scores: Dict[int, float] = {i: 1.0 for i in range(num_clients)}

        # Sticky Group: 带宽较好的客户端候选池（FedFetch 中的 k）
        self.sticky_group: List[int] = []
        self.historical_sticky_group: List[List[int]] = []

        # 每轮实际选中的客户端记录
        self.selection_history: Dict[int, List[int]] = {}

        mode_str = "STICKY" if use_sticky else "UNIFORM"
        tag_info(LogTag.STICKY,
                 f"Initialized  |  mode={mode_str}  |  clients={num_clients}  |  "
                 f"OC={self.overcommitment}  |  decay={self.decay_factor}  |  "
                 f"group_size={self.sticky_group_size}  |  change_num={self.change_num}")

    # ==================================================================
    # Sticky Group 管理
    # ==================================================================
    def _init_sticky_group(self):
        """初始化 sticky_group（对齐 FedFetch）。
        
        从 (group_size * overcommitment) 个随机候选中按带宽排序，
        取带宽最高的 group_size 个作为粘性组。
        """
        clients = list(range(self.num_clients))
        np.random.shuffle(clients)

        # FedFetch：候选池 = min(group_size, num_clients-1) * overcommitment
        candidate_len = round(
            min(self.sticky_group_size, self.num_clients - 1) * self.overcommitment
        )
        candidate_len = min(candidate_len, self.num_clients)
        candidates = clients[:candidate_len]

        group_len = min(self.sticky_group_size, self.num_clients)
        if self.bandwidth_info:
            # 按下行带宽排序（带宽高的优先）
            sorted_clients = sorted(
                candidates,
                key=lambda c: self.bandwidth_info.get(c, 0.0)
            )
            self.sticky_group = sorted_clients[-group_len:]
        else:
            # 没有带宽信息，直接随机选
            self.sticky_group = candidates[:group_len]

        self.historical_sticky_group.append(self.sticky_group.copy())
        np.random.shuffle(self.sticky_group)
        tag_info(LogTag.STICKY,
                 f"Init sticky_group  |  candidates={candidate_len}  |  size={len(self.sticky_group)}  |  "
                 f"ids={sorted(self.sticky_group)}")

    def _select_sticky_fallback(self, num_needed: int) -> List[int]:
        """
        预采样池为空时的 Sticky 选择逻辑（对齐 FedFetch select_participants_sticky）。

        每轮从 sticky_group 中选 (num_needed - change_num) 个，
        从 sticky_group 外部随机选 change_num 个作为替换。
        
        运行时保护：
          - 若 sticky_group 为空，自动初始化
          - 若 sticky_group 大小 < num_needed，自动从全体客户端中按带宽扩展
        """
        if not self.sticky_group:
            self._init_sticky_group()

        # 运行时自适应：确保 sticky_group 至少能容纳 num_needed 个客户端
        # 这样即使配置 group_size < num_needed，也能正常工作
        if len(self.sticky_group) < num_needed:
            missing = num_needed - len(self.sticky_group)
            # 从全体客户端中按带宽排序，取未在 group 中的高带宽客户端补充
            all_clients = list(range(self.num_clients))
            not_in_group = [c for c in all_clients if c not in self.sticky_group]
            if self.bandwidth_info:
                not_in_group = sorted(
                    not_in_group,
                    key=lambda c: self.bandwidth_info.get(c, 0.0),
                    reverse=True
                )
            else:
                np.random.shuffle(not_in_group)
            
            extension = not_in_group[:missing]
            self.sticky_group.extend(extension)
            tag_info(LogTag.STICKY,
                     f"Group auto-extended  |  old_size={len(self.sticky_group)-len(extension)}  |  "
                     f"new_size={len(self.sticky_group)}  |  added={extension}")

        # 确定每轮从 sticky_group 中选多少个
        sticky_select = max(0, num_needed - self.change_num)
        new_select = min(self.change_num, num_needed)

        # 从 sticky_group 中随机选 sticky_select 个
        np.random.shuffle(self.sticky_group)
        selected_sticky = self.sticky_group[:sticky_select]

        # 从 sticky_group 外部随机选 new_select 个
        outside = [c for c in range(self.num_clients) if c not in self.sticky_group]
        selected_new = []
        if outside and new_select > 0:
            np.random.shuffle(outside)
            selected_new = outside[:min(new_select, len(outside))]

        # 合并
        selected = selected_sticky + selected_new

        # 最终保护：去重并确保数量（理论上不会触发，但保留以防边界情况）
        selected = list(dict.fromkeys(selected))  # 去重，保持顺序
        if len(selected) < num_needed:
            remaining = num_needed - len(selected)
            pool = [c for c in range(self.num_clients) if c not in selected]
            np.random.shuffle(pool)
            selected.extend(pool[:remaining])

        # 更新 sticky_group：移除最老的，加入新选的
        self._update_sticky_group(selected_new)

        tag_info(LogTag.STICKY,
                 f"Select-sticky  |  needed={num_needed}  |  "
                 f"sticky={sorted(selected_sticky)}  |  new={sorted(selected_new)}  |  "
                 f"selected={len(selected)}  |  "
                 f"group_size={len(self.sticky_group)}")
        return selected

    def _update_sticky_group(self, new_clients: List[int]):
        """更新 sticky_group：移除最老的，加入新客户端。"""
        if not new_clients:
            return
        self.historical_sticky_group.append(self.sticky_group.copy())
        np.random.shuffle(self.sticky_group)
        # 移除最后 len(new_clients) 个，加入新客户端
        drop_count = min(len(new_clients), len(self.sticky_group))
        self.sticky_group = self.sticky_group[:-drop_count] + list(new_clients)

    # ==================================================================
    # 预采样接口
    # ==================================================================
    def presample_for_target(self, target_round: int, num_needed: int) -> List[int]:
        """
        为 target_round 预采样客户端。

        预采样数 = max(num_needed, int(num_needed * overcommitment))
        采样按 sticky score 加权（score 高的客户端更可能被预采样）。
        """
        num_to_sample = max(num_needed, int(num_needed * self.overcommitment))
        num_to_sample = min(num_to_sample, self.num_clients)

        if self.use_sticky:
            # STICKY: 按 sticky score 加权采样
            scores = np.array([self.sticky_scores[i] for i in range(self.num_clients)], dtype=float)
            probs = scores / scores.sum()
            sampled = np.random.choice(
                self.num_clients,
                size=num_to_sample,
                replace=False,
                p=probs,
            ).tolist()
        else:
            # UNIFORM: 均匀随机采样
            sampled = np.random.choice(
                self.num_clients,
                size=num_to_sample,
                replace=False,
            ).tolist()

        # 存入预采样池
        self.presample_pool[target_round] = {
            cid: float(self.sticky_scores[cid]) for cid in sampled
        }

        tag_info(LogTag.STICKY,
                 f"Presample  |  目标轮={target_round + 1}  |  "
                 f"sampled={len(sampled)} (need={num_needed}, OC={self.overcommitment})  |  "
                 f"ids={sampled}")
        return sampled

    # ==================================================================
    # 选择接口
    # ==================================================================
    def select_for_round(self, target_round: int, num_needed: int) -> List[int]:
        """
        为 target_round 选择客户端。

        对齐 FedFetch：
        - 如果预采样池存在，从池中按 sticky score 概率选取
        - 如果池为空，回退到 _select_sticky_fallback（sticky group 逻辑）
        """
        pool = self.presample_pool.get(target_round, {})

        if not pool:
            # 没有预采样池，回退到 sticky group 选择（对齐 FedFetch）
            selected = self._select_sticky_fallback(num_needed)
            self.selection_history[target_round] = selected.copy()
            return selected

        # 从预采样池中选取
        candidates = list(pool.keys())
        num_from_pool = min(num_needed, len(candidates))

        if self.use_sticky:
            # STICKY: 按 pool score 加权
            scores = np.array([pool[cid] for cid in candidates], dtype=float)
            probs = scores / scores.sum()
            selected = np.random.choice(
                candidates,
                size=num_from_pool,
                replace=False,
                p=probs,
            ).tolist()
        else:
            # UNIFORM: 从池中均匀随机
            selected = np.random.choice(
                candidates,
                size=num_from_pool,
                replace=False,
            ).tolist()

        # 如果预采样池不够，从非预采样客户端中随机补足
        if len(selected) < num_needed:
            remaining = num_needed - len(selected)
            other_candidates = [
                i for i in range(self.num_clients)
                if i not in selected
            ]
            if other_candidates:
                extra = np.random.choice(
                    other_candidates,
                    size=min(remaining, len(other_candidates)),
                    replace=False,
                ).tolist()
                selected.extend(extra)

        self.selection_history[target_round] = selected.copy()
        tag_info(LogTag.STICKY,
                 f"Select  |  target={target_round}  |  selected={selected}  |  pool={list(pool.keys())}")
        return selected

    # ==================================================================
    # Score 更新接口
    # ==================================================================
    def update_on_prefetch(self, client_ids: List[int]):
        """客户端被预取后，增加其 sticky score。"""
        if not self.use_sticky:
            return
        for cid in client_ids:
            self.sticky_scores[cid] += 1.0
            for pool in self.presample_pool.values():
                if cid in pool:
                    pool[cid] = self.sticky_scores[cid]

    def update_on_select(self, selected_ids: List[int]):
        """客户端被选中训练后，衰减其 sticky score。"""
        if not self.use_sticky:
            return
        for cid in selected_ids:
            old_score = self.sticky_scores[cid]
            self.sticky_scores[cid] = max(0.5, old_score * self.decay_factor)
            for pool in self.presample_pool.values():
                if cid in pool:
                    pool[cid] = self.sticky_scores[cid]

    # ==================================================================
    # 清理与统计
    # ==================================================================
    def cleanup(self, current_round: int, num_rounds: int = None):
        """清理已过期的预采样池。
        
        Args:
            current_round: 当前轮次索引
            num_rounds: 训练总轮数（可选），超出此范围的池也视为无效
        """
        expired = [
            r for r in list(self.presample_pool.keys())
            if r < current_round
        ]
        if num_rounds is not None:
            expired += [
                r for r in list(self.presample_pool.keys())
                if r >= num_rounds
            ]
        for r in set(expired):
            del self.presample_pool[r]

    def get_stats(self) -> Dict:
        """返回 sticky sampling 统计信息。"""
        return {
            "sticky_scores": self.sticky_scores.copy(),
            "sticky_group": self.sticky_group.copy(),
            "active_pools": sorted(self.presample_pool.keys()),
            "num_active_pools": len(self.presample_pool),
            "avg_score": float(np.mean(list(self.sticky_scores.values()))),
            "max_score": float(np.max(list(self.sticky_scores.values()))),
            "min_score": float(np.min(list(self.sticky_scores.values()))),
        }
