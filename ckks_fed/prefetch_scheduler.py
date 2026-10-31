"""
预取调度器 (Prefetch Scheduler)
==============================
借鉴 FedFetch 的 T_percentile 预取调度策略，适配 CKKS 密文场景。

核心逻辑 (来自 FedFetch aggregator.py::schedule_prefetch / estimate_fetch_time):
------------------------------------------------------------------------
服务器在轮次 R 为 future_round = R + max_prefetch_round 的客户端决定：
"每个客户端应该从哪一轮开始预取，才能使得目标轮次时的 fetch_time 不超过阈值。"

调度器不是决定"能预取几个"，而是决定"从哪一轮开始预取"。
客户端在 [start_round, target_round) 期间的每一轮都有 time_budget = EMA_round_duration
可用于后台下载。如果某轮下载不完一个完整的 delta，剩余部分留到 fetch 阶段补齐。

关键公式:
    T_percentile = percentile(fetch_times, 100 * (1 + beta*(OC-1)) / OC)
    其中 OC = overcommitment, beta = scheduler_beta (松弛系数)

CKKS 适配点:
    - 密文 delta 大小固定（与明文内容无关），size_evaluator 可精确预测
    - 不需要 FedFetch 中复杂的 mask-based sparsification ratio 计算
"""

import logging
import math
from typing import Dict, List, Tuple

import numpy as np
from ckks_fed.log_utils import LogTag, tag_info, fmt_size

logger = logging.getLogger(__name__)


class CKKSSizeEvaluator:
    """
    CKKS 密文大小评估器。

    由于 CKKS 密文大小仅取决于加密参数（poly_modulus_degree, coeff_mod_bit_sizes）
    和模型结构，与具体数值无关，因此每轮的密文 delta 大小是**固定且可精确预测**的。

    这相比 FedFetch 的明文压缩场景（大小取决于梯度稀疏度、量化位数等）大幅简化。
    """

    def __init__(self, ckks_manager, config: Dict = None):
        """
        Args:
            ckks_manager: CKKSManager 实例，用于加密一个 dummy delta 以测量大小
            config: 外部传入的配置字典（优先使用；为 None 时回退到读取 configs/config.yaml）
        """
        self.ckks_manager = ckks_manager

        # 构造一个 dummy model update（全零），加密后测量其密文大小
        # 由于 CKKS 密文大小与明文内容无关，这就是真实的 per-round delta 大小
        from ckks_fed.models import create_model
        import yaml
        import torch

        cfg = config
        if cfg is None:
            try:
                with open("configs/config.yaml", "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"CKKSSizeEvaluator 无法读取默认配置: {e}")
                cfg = None

        try:
            if cfg is None:
                raise ValueError("config is None")
            dummy_model = create_model(cfg["model"]["name"], cfg)
            dummy_update = {
                name: torch.zeros_like(param.data)
                for name, param in dummy_model.named_parameters()
            }
            enc_dummy = ckks_manager.encrypt_model_update(dummy_update)
            self.per_delta_size_bits = (
                ckks_manager.compute_encrypted_update_size(enc_dummy) * 8
            )  # bytes -> bits
        except Exception as e:
            logger.warning(f"CKKSSizeEvaluator init warning: {e}, using fallback size")
            self.per_delta_size_bits = 8 * 1024 * 1024  # fallback: 8 Mbits

        tag_info(LogTag.SCHEDULER,
                 f"Delta size = {fmt_size(self.per_delta_size_bits / 8)} per round")

    # ------------------------------------------------------------------
    # 大小估算接口
    # ------------------------------------------------------------------
    def estimate_delta_size(self, l: int, r: int) -> float:
        """
        估算从轮次 l 到 r（含）的累积密文 delta 总大小 (bits)。
        如果 l > r 返回 0。
        """
        if l > r:
            return 0.0
        num_deltas = r - l + 1
        return num_deltas * self.per_delta_size_bits

    def estimate_size_base_and_delta(
        self, r_min: int, r: int, last_synced_round: int = 1
    ) -> float:
        """
        估算客户端需要下载的 "base + delta" 大小。
        在 CKKS 预取方案中，base 理解为从 last_synced_round 到 r 的所有 delta。

        Args:
            r_min:    调度器当前考虑的最小预取轮次
            r:        预取开始轮次
            last_synced_round: 客户端上次同步的轮次
        Returns:
            大小 (bits)
        """
        last_synced_round = max(last_synced_round, 1)
        # 客户端需要从 last_synced_round 同步到 r 的所有 delta
        return self.estimate_delta_size(last_synced_round, r)

    def estimate_single_delta_size(self) -> float:
        """返回单个轮次的密文 delta 大小 (bits)"""
        return self.per_delta_size_bits


class PrefetchScheduler:
    """
    FedFetch 风格的预取调度器。

    服务器在轮次 R 为 future_round = R + max_prefetch_round 的客户端计算：
    如果从轮次 r 开始预取，到 future_round 时还剩下多少 fetch_time？
    然后使用 T_percentile 策略筛选出"能成功预取"的客户端，并决定其 start_round。
    """

    def __init__(
        self,
        max_prefetch_round: int,
        warmup_round: int,
        bandwidth_simulator,
        size_evaluator: CKKSSizeEvaluator,
        scheduler_beta: float = 0.5,
        overcommitment: float = 1.0,
        avg_alpha: float = 0.125,
    ):
        """
        Args:
            max_prefetch_round: 最大提前预取轮数（窗口大小）
            warmup_round:       预热轮数（此期间不调度预取）
            bandwidth_simulator: BandwidthSimulator 实例
            size_evaluator:     CKKSSizeEvaluator 实例
            scheduler_beta:     T_percentile 松弛系数 [0, 1]
            overcommitment:     过承诺比例（>=1），FedFetch 用于 sticky sampling
            avg_alpha:          EMA 平滑系数
        """
        self.max_prefetch_round = max_prefetch_round
        self.warmup_round = warmup_round
        self.bandwidth_simulator = bandwidth_simulator
        self.size_evaluator = size_evaluator
        self.scheduler_beta = scheduler_beta
        self.overcommitment = overcommitment
        self.avg_alpha = avg_alpha

        # EMA 轮次持续时间（秒），由外部实验循环每轮更新
        self.exp_mov_avg_dur: float = 0.0

        # 调度结果存储
        self.prefetch_schedules: Dict[int, Dict[int, int]] = {}  # target_round -> {client_id: start_round}
        self.min_prefetch_round: Dict[int, int] = {}             # target_round -> min_start_round

    def update_ema_duration(self, new_duration: float):
        """由外部实验循环每轮调用，更新 EMA 轮次耗时"""
        if self.exp_mov_avg_dur <= 0:
            self.exp_mov_avg_dur = new_duration
        else:
            self.exp_mov_avg_dur = (
                self.avg_alpha * new_duration
                + (1.0 - self.avg_alpha) * self.exp_mov_avg_dur
            )

    def schedule_prefetch(
        self,
        clients: List[int],
        cur_round: int,
        last_update_index: Dict[int, int],
    ) -> Tuple[Dict[int, int], int]:
        """
        为 target_round = cur_round + max_prefetch_round 的客户端调度预取。

        Args:
            clients:          预采样到的未来客户端列表
            cur_round:        当前轮次（调度发生在此轮）
            last_update_index: client_id -> 该客户端上次同步的轮次

        Returns:
            prefetch_schedule: {client_id: start_round}
            r_min:             所有客户端中最早开始预取的轮次
        """
        if not clients or self.exp_mov_avg_dur <= 0:
            return {c: cur_round for c in clients}, cur_round

        prefetch_schedule = {c: cur_round for c in clients}
        r_min = cur_round
        clients_can_finish = clients.copy()
        T_percentile = float("inf")

        # 遍历可能的预取开始轮次，逐步放宽
        for r in range(cur_round, cur_round + self.max_prefetch_round + 1):
            # 估计每个客户端如果从轮次 r 开始预取，到目标轮时的 fetch_time
            fetch_times = {
                i: self.estimate_fetch_time(i, r, r_min, last_update_index.get(i, 1), cur_round)
                for i in clients_can_finish
            }

            if T_percentile == float("inf"):
                # T_percentile 计算：基于 overcommitment 和 beta
                # 公式来自 FedFetch: percentile = 100 * (1 + beta*(OC-1)) / OC
                # 当 OC = 1 时，等价于取最大值 (T_max)
                pct = 100.0 * (
                    (1.0 + self.scheduler_beta * (self.overcommitment - 1.0))
                    / self.overcommitment
                )
                T_percentile = float(np.percentile(list(fetch_times.values()), pct))
                # 第一次筛选：只保留 fetch_time < T_percentile 的客户端
                clients_can_finish = [
                    i for i in clients_can_finish if fetch_times[i] <= T_percentile
                ]

            # 后续轮次：继续筛选 fetch_time <= T_percentile 的客户端
            clients_can_finish = [
                i for i in clients_can_finish if fetch_times[i] <= T_percentile
            ]

            # 如果所有原始客户端都能 finish，提升 r_min 并更新 T_percentile
            if len(clients_can_finish) == len(clients):
                r_min = min(r, cur_round + self.max_prefetch_round)
                pct = 100.0 * (
                    (1.0 + self.scheduler_beta * (self.overcommitment - 1.0))
                    / self.overcommitment
                )
                T_percentile = float(np.percentile(list(fetch_times.values()), pct))

            # 为能 finish 的客户端设置预取开始轮次
            for i in clients_can_finish:
                prefetch_schedule[i] = r

            if not clients_can_finish:
                break

        # 为被回退的客户端设置最早的预取轮次
        for c in clients:
            if c not in clients_can_finish:
                prefetch_schedule[c] = r_min

        scheduled_early = len([v for v in prefetch_schedule.values() if v > r_min])
        rollbacked = len(clients) - len(clients_can_finish)
        # 中文解释关键术语：
        #   r_min        = 最早开始预取的轮次（所有客户端至少从这个轮次开始）
        #   early        = 被允许延后启动的客户端数（>r_min 表示带宽好、可以偷懒）
        #   rollbacked   = 被回退到最早时间的客户端数（带宽差、必须立即开始）
        tag_info(LogTag.SCHEDULER,
                 f"当前轮={cur_round}  目标轮={cur_round + self.max_prefetch_round}  |  "
                 f"最早启动轮=r_min({r_min})  可延后={scheduled_early}人  需立即启动={rollbacked}人  |  "
                 f"(OC={self.overcommitment}, β={self.scheduler_beta})")
        return prefetch_schedule, r_min

    def estimate_fetch_time(
        self,
        client_id: int,
        start_round: int,
        r_min: int,
        last_synced_round: int,
        cur_round: int,
    ) -> float:
        """
        估算客户端 client_id 如果从 start_round 开始预取，
        到 target_round = cur_round + max_prefetch_round 时还剩下的 fetch_time (秒)。

        模拟逻辑（来自 FedFetch estimate_fetch_time）：
        1. 客户端在 [start_round, target_round) 的每一轮都有 time_budget = EMA_duration
        2. 先用 time_budget 下载 base 到 start_round 的 update
        3. 如果还有剩余时间，继续预取下一个 delta
        4. 如果某轮 time_budget 不够用，update_size 累积到下一轮
        5. 最后返回 (剩余未下载量 + final_delta) / 带宽

        Args:
            client_id:        客户端 ID
            start_round:      假设从此轮开始预取
            r_min:            最小预取轮次（用于 base 大小计算）
            last_synced_round: 客户端上次同步轮次
            cur_round:        当前调度轮次

        Returns:
            剩余 fetch_time (秒)
        """
        dl_bw = self.bandwidth_simulator.get_dl_bw_bits(client_id)
        if dl_bw <= 0:
            return float("inf")

        # 每轮可下载的数据量 = 轮次持续时间 * 带宽
        round_download_amount = self.exp_mov_avg_dur * dl_bw

        # 初始需要下载的 update：从 last_synced 到 start_round 的 base
        update_size = self.size_evaluator.estimate_size_base_and_delta(
            r_min, start_round, last_synced_round
        )

        target_round = cur_round + self.max_prefetch_round
        l = start_round
        time_budget = 0.0

        # 模拟从 start_round 到 target_round 的每一轮预取过程
        for j in range(start_round, target_round):
            time_budget = self.exp_mov_avg_dur
            # 用本轮时间预算下载当前累积的 update_size
            time_budget = max(0.0, time_budget - update_size / dl_bw)

            if time_budget > 0:
                # 有剩余时间，尝试预取下一个 delta
                # 对齐 FedFetch 原始逻辑：next_delta_size = estimate_delta_size(l, j - 1)
                # 当 j == start_round 时，j - 1 = start_round - 1，l = start_round
                # estimate_delta_size(start_round, start_round - 1) = 0（l > r），这是正确的
                # 第一个间隙只消化 base，不预取新 delta
                next_delta_size = self.size_evaluator.estimate_delta_size(l, j - 1)
                # 用剩余时间下载 next_delta，记下还没下载完的部分
                update_size = max(0.0, next_delta_size - time_budget * dl_bw)
                l = j
                time_budget = 0.0
            else:
                # 本轮时间全部用于下载也不够，update_size 累积到下一轮
                update_size -= round_download_amount

        # 最终还需要下载从 l 到 target_round-1 的 final_delta
        final_delta = self.size_evaluator.estimate_delta_size(l, target_round - 1)
        remaining = update_size + final_delta

        return remaining / dl_bw
