"""
AdaptiveGlobalMaskVote: 可插拔的自适应全局掩码投票模块
=========================================================

在 GlobalMaskVote 之上封装一层自适应策略，支持三种可配置策略：
  1. cosine    : 基于训练轮次的余弦退火调整 topk_pct
  2. accuracy  : 基于验证准确率变化动态调整 topk_pct
  3. consensus : 基于客户端投票共识度动态调整 threshold_pct

使用方式：
  在 config.yaml 中启用 adaptive_vote 块，并指定 strategy。
  当 adaptive_vote.enabled=false 或未配置时，行为与原始 GlobalMaskVote 完全一致。

设计原则：
  - 完全可插拔：不修改 GlobalMaskVote 核心逻辑
  - 向后兼容：未启用时原有实验行为不变
  - 策略可切换：通过 YAML 配置一键切换策略
"""

import numpy as np
from typing import List, Dict, Optional, Any
import logging

from .global_mask_vote import GlobalMaskVote

logger = logging.getLogger(__name__)


class AdaptiveGlobalMaskVote:
    """
    自适应全局掩码投票器。

    Args:
        gmv_cfg: global_mask_vote 配置块
        total_rounds: 训练总轮数（用于 cosine/accuracy 策略）
    """

    STRATEGIES = ["none", "cosine", "accuracy", "consensus"]

    def __init__(self, gmv_cfg: Dict[str, Any], total_rounds: int = 50):
        self.strategy = gmv_cfg.get("adaptive_strategy", "none")
        if self.strategy not in self.STRATEGIES:
            raise ValueError(
                f"adaptive_strategy must be one of {self.STRATEGIES}, got {self.strategy}"
            )

        self.total_rounds = max(1, total_rounds)
        self.cfg = gmv_cfg
        self.adaptive_config = gmv_cfg.get("adaptive_config", {}) or {}

        # 底层投票器
        self.voter = GlobalMaskVote(
            mode=gmv_cfg.get("mode", "topk"),
            threshold_pct=gmv_cfg.get("threshold_pct", 0.2),
            topk_k=gmv_cfg.get("topk_count_k", 5),
            topk_pct=gmv_cfg.get("topk_pct", None),
        )

        # 暴露 mode 属性，供 server.py 检查
        self.mode = self.voter.mode

        # 记录初始值
        self.initial_topk_pct = self.voter.topk_pct
        self.initial_threshold_pct = self.voter.threshold_pct

        if self.strategy == "none":
            logger.info("AdaptiveGlobalMaskVote disabled (strategy=none)")
        else:
            logger.info(
                f"AdaptiveGlobalMaskVote enabled | strategy={self.strategy} | "
                f"base_mode={self.voter.mode} | total_rounds={self.total_rounds}"
            )

    # ==================================================================
    # 透传客户端接口
    # ==================================================================
    def client_compute_mask(self, *args, **kwargs):
        return self.voter.client_compute_mask(*args, **kwargs)

    def client_compute_mask_from_update(self, *args, **kwargs):
        return self.voter.client_compute_mask_from_update(*args, **kwargs)

    @staticmethod
    def compute_mask_from_update(*args, **kwargs):
        return GlobalMaskVote.compute_mask_from_update(*args, **kwargs)

    # ==================================================================
    # 服务器侧：聚合 + 自适应更新
    # ==================================================================
    def server_aggregate(
        self,
        client_masks: List[Optional[np.ndarray]],
        total_batches: int,
        round_num: int = 0,
        history: Optional[Dict[str, List[float]]] = None,
    ) -> Optional[np.ndarray]:
        """
        服务器聚合入口。会根据当前策略更新底层投票器参数，再执行聚合。

        Args:
            client_masks: 客户端 mask 列表
            total_batches: batch 总数
            round_num: 当前轮次（从 1 开始）
            history: 训练历史，包含 test_acc 等（accuracy 策略需要）

        Returns:
            全局掩码
        """
        self._update(round_num, history, client_masks, total_batches)
        return self.voter.server_aggregate(client_masks, total_batches)

    def _update(
        self,
        round_num: int,
        history: Optional[Dict[str, List[float]]],
        client_masks: List[Optional[np.ndarray]],
        total_batches: int,
    ):
        if self.strategy == "none":
            return
        elif self.strategy == "cosine":
            self._update_cosine(round_num)
        elif self.strategy == "accuracy":
            self._update_accuracy(history)
        elif self.strategy == "consensus":
            self._update_consensus(client_masks, total_batches)

    # ------------------------------------------------------------------
    # 策略 1：Round-based Cosine Annealing
    # ------------------------------------------------------------------
    def _update_cosine(self, round_num: int):
        """按余弦退火调整 topk_pct。"""
        cfg = self.adaptive_config.get("cosine", {})
        start = cfg.get("topk_pct_start", self.initial_topk_pct or 0.5)
        end = cfg.get("topk_pct_end", 0.1)
        min_pct, max_pct = min(start, end), max(start, end)

        if self.total_rounds <= 1:
            new_pct = start
        else:
            # round_num 从 1 开始，progress 从 0 到 1
            progress = (round_num - 1) / (self.total_rounds - 1)
            new_pct = end + (start - end) * 0.5 * (1.0 + np.cos(np.pi * progress))

        self.voter.topk_pct = float(np.clip(new_pct, min_pct, max_pct))
        # cosine 策略作用于 topk 模式
        if self.voter.mode != "topk":
            self.voter.mode = "topk"
            self.mode = "topk"
            logger.warning("Adaptive cosine strategy overrides mode to 'topk'")

        logger.info(
            f"[Adaptive cosine] round={round_num}/{self.total_rounds} | "
            f"topk_pct={self.voter.topk_pct:.4f}"
        )

    # ------------------------------------------------------------------
    # 策略 2：Accuracy-Triggered Adaptation
    # ------------------------------------------------------------------
    def _update_accuracy(self, history: Optional[Dict[str, List[float]]]):
        """基于最近一轮验证准确率变化调整 topk_pct。"""
        test_acc = history.get("test_acc", []) if history else []
        if len(test_acc) < 2:
            logger.debug("[Adaptive accuracy] not enough history, skip")
            return

        cfg = self.adaptive_config.get("accuracy", {})
        delta = cfg.get("improvement_threshold", 0.005)
        decay = cfg.get("decay_factor", 0.9)
        growth = cfg.get("growth_factor", 1.1)
        min_pct = cfg.get("min_topk_pct", 0.05)
        max_pct = cfg.get("max_topk_pct", 0.9)

        recent_improvement = test_acc[-1] - test_acc[-2]
        current = self.voter.topk_pct if self.voter.topk_pct is not None else 0.5

        if recent_improvement > delta:
            new_pct = current * decay
        elif recent_improvement < 0:
            new_pct = current * growth
        else:
            new_pct = current

        self.voter.topk_pct = float(np.clip(new_pct, min_pct, max_pct))
        # accuracy 策略作用于 topk 模式
        if self.voter.mode != "topk":
            self.voter.mode = "topk"
            self.mode = "topk"
            logger.warning("Adaptive accuracy strategy overrides mode to 'topk'")

        logger.info(
            f"[Adaptive accuracy] acc_improvement={recent_improvement:.4f} | "
            f"topk_pct={self.voter.topk_pct:.4f}"
        )

    # ------------------------------------------------------------------
    # 策略 3：Vote-Consensus Adaptive Threshold
    # ------------------------------------------------------------------
    def _update_consensus(
        self,
        client_masks: List[Optional[np.ndarray]],
        total_batches: int,
    ):
        """基于客户端投票共识度动态调整 threshold_pct。"""
        valid_masks = [m for m in client_masks if m is not None]
        if not valid_masks or total_batches <= 0:
            return

        cfg = self.adaptive_config.get("consensus", {})
        high_threshold = cfg.get("high_consensus_threshold", 0.7)
        low_threshold = cfg.get("low_consensus_threshold", 0.3)
        high_pct = cfg.get("high_threshold_pct", 0.7)
        low_pct = cfg.get("low_threshold_pct", 0.3)

        mask_matrix = np.stack(valid_masks, axis=0)
        counts = np.sum(mask_matrix, axis=0)
        num_clients = len(valid_masks)

        # 归一化投票计数为概率分布
        p = counts / num_clients
        p_nonzero = p[p > 0]
        entropy = (
            -np.sum(p_nonzero * np.log(p_nonzero))
            if len(p_nonzero) > 0
            else 0.0
        )
        max_entropy = np.log(total_batches) if total_batches > 1 else 1.0
        consensus = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0.0)

        # 根据共识度映射 threshold_pct
        if consensus >= high_threshold:
            new_threshold = high_pct
        elif consensus <= low_threshold:
            new_threshold = low_pct
        else:
            alpha = (consensus - low_threshold) / (
                high_threshold - low_threshold + 1e-10
            )
            new_threshold = low_pct + alpha * (high_pct - low_pct)

        self.voter.threshold_pct = float(new_threshold)
        # consensus 策略作用于 threshold 模式
        if self.voter.mode != "threshold":
            self.voter.mode = "threshold"
            self.mode = "threshold"
            logger.warning("Adaptive consensus strategy overrides mode to 'threshold'")

        logger.info(
            f"[Adaptive consensus] consensus={consensus:.4f} | "
            f"threshold_pct={self.voter.threshold_pct:.4f}"
        )
