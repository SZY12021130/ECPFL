"""
可插拔客户端选择策略模块 (Pluggable Client Selection Strategies)
================================================================

支持以下策略：
  - random          : 纯随机采样
  - sticky          : Sticky Sampling (FedFetch 风格，包装 StickySamplingManager)
  - sketch_clustering: 基于 MinHash 草图聚类的代表选择 (FedPHE 风格)
  - fairness_wrapper: 公平性包装器，保证最低参与率

用法:
    from ckks_fed.client_selection import create_client_selection_strategy
    strategy = create_client_selection_strategy(config, num_clients=10)
    selected_ids = strategy.select(clients, num_needed=5, round_num=0,
                                   train_weights=weights, client_states=states)
"""

import logging
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from sklearn.cluster import KMeans

from ckks_fed.log_utils import LogTag, tag_info

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


# =============================================================================
# MinHash / Sketch 工具函数 (移植自 FedPHE)
# =============================================================================

def _gen_random_R(input_len: int, sim_len: int, seed: int = 42) -> List[np.ndarray]:
    """生成 MinHash 所需的随机排列矩阵。
    random_R[i] 是一个长度为 input_len 的随机排列数组。
    """
    rng = np.random.RandomState(seed)
    random_R = []
    for _ in range(sim_len):
        seq = np.arange(input_len)
        rng.shuffle(seq)
        random_R.append(seq)
    return random_R


def _sigGen(matrix: np.ndarray, random_seq: np.ndarray) -> List[int]:
    """对单个随机排列生成签名向量。
    对 matrix 的每一列，记录第一个非零行对应的行号。
    """
    result = [-1] * matrix.shape[1]
    count = 0
    for row in random_seq:
        for col in range(matrix.shape[1]):
            if matrix[row][col] != 0 and result[col] == -1:
                result[col] = int(row)
                count += 1
        if count == matrix.shape[1]:
            break
    return result


def _sigMatrixGen(input_matrix: np.ndarray, random_R: List[np.ndarray], n: int) -> np.ndarray:
    """生成 n 行签名矩阵（每行对应一个随机排列的签名）。"""
    result = []
    for i in range(n):
        sig = _sigGen(input_matrix, random_R[i])
        result.append(sig)
    return np.array(result)


def _quan_params(input_matrix: np.ndarray, threshold: float) -> np.ndarray:
    """量化（二值化）：绝对值小于 threshold 设为 0，否则设为 1。"""
    output = np.zeros_like(input_matrix)
    output[np.abs(input_matrix) >= threshold] = 1
    return output


def _jaccard_similarity(x: np.ndarray, y: np.ndarray) -> float:
    """计算两个一维数组的 Jaccard 相似度。"""
    intersection = len(np.intersect1d(x, y))
    union = len(np.union1d(x, y))
    if union == 0:
        return 0.0
    return intersection / union


def _jaccard_distance_matrix(matrix: np.ndarray) -> np.ndarray:
    """计算 Jaccard 距离矩阵（用于 KMeans 输入）。"""
    n = matrix.shape[0]
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = 1.0 - _jaccard_similarity(matrix[i], matrix[j])
            dist_matrix[i][j] = d
            dist_matrix[j][i] = d
    return dist_matrix


def _jaccard_kmeans_clustering(matrix: np.ndarray, k: int) -> List[np.ndarray]:
    """基于 Jaccard 距离的 KMeans 聚类，返回每类的客户端索引列表。"""
    distance_matrix = _jaccard_distance_matrix(matrix)
    while True:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(distance_matrix)
        cluster_indices = [np.where(clusters == i)[0] for i in range(k)]
        empty_clusters = [i for i, indices in enumerate(cluster_indices) if len(indices) == 0]
        if len(empty_clusters) == 0:
            break
        # 如果有空类，减少 k 重试
        k -= 1
        if k < 1:
            k = 1
            break
    return cluster_indices


def _sse_statistic(X: np.ndarray, max_k: int) -> int:
    """使用肘部法则（SSE 差分比）自动确定最优聚类数。"""
    sse = []
    for k in range(1, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        sse.append(kmeans.inertia_)
    if len(sse) < 3:
        return max(1, min(max_k, len(X)))
    diff = np.diff(sse)
    diff_r = diff[1:] / np.maximum(diff[:-1], 1e-10)
    k_opt = int(np.argmax(diff_r)) + 2
    k_opt = max(1, min(k_opt, max_k, len(X)))
    return k_opt


def _gap_statistic_fallback(data: np.ndarray, max_k: int) -> int:
    """Gap Statistic 的 fallback（使用 SSE 肘部法则）。"""
    data = np.array(data).reshape(-1, 1)
    return _sse_statistic(data, max_k)


try:
    from gap_statistic import OptimalK

    def _gap_statistic(data: np.ndarray, max_k: int) -> int:
        data = np.array(data).reshape(-1, 1)
        optimalK = OptimalK(n_jobs=1, parallel_backend='joblib')
        n_clusters = optimalK(data, cluster_array=np.arange(1, max_k + 1))
        return max(1, min(int(n_clusters), max_k, len(data)))
except ImportError:
    _gap_statistic = _gap_statistic_fallback


def _clusters_selection_L2(
    hash_mat: np.ndarray,
    max_k: int,
    train_weights: List[float],
) -> Tuple[List[int], List[int], Dict[int, float]]:
    """
    基于 Gap Statistic + Jaccard KMeans 的客户端选择。

    Returns:
        selected_clients: 被选中的客户端 ID 列表
        rep_num: 每个客户端的代表数量（被选中的客户端为其聚类的代表数）
        weights_clusters: 聚类聚合后的权重
    """
    n_clients = hash_mat.shape[0]
    k_opt = _gap_statistic(hash_mat.astype(float), max_k)
    clusters = _jaccard_kmeans_clustering(hash_mat, k_opt)

    rep_num = [1] * n_clients
    selected_clients = []
    weights_clusters = {i: train_weights[i] for i in range(n_clients)}

    tag_info(LogTag.CLIENT_SELECT,
             f"SketchClustering  |  k_opt={k_opt}  |  clusters={clusters}")

    for indices in clusters:
        indices = list(indices)
        tmp_weights = [train_weights[i] for i in indices]
        tmp_list = list(indices)
        zipped = list(zip(tmp_weights, tmp_list))
        # 每类中选择样本权重最大的客户端作为代表
        max_tuple = max(zipped, key=lambda x: x[0])
        client_index = int(max_tuple[1])

        rep_num[client_index] = len(indices)
        tmp = sum(train_weights[i] for i in indices)
        weights_clusters[client_index] = tmp
        selected_clients.append(client_index)

    return selected_clients, rep_num, weights_clusters


# =============================================================================
# 抽象基类
# =============================================================================

class ClientSelectionStrategy(ABC):
    """客户端选择策略抽象基类。"""

    @abstractmethod
    def select(
        self,
        clients: List,
        num_needed: int,
        round_num: int = 0,
        **kwargs,
    ) -> List[int]:
        """
        选择参与本轮训练的客户端。

        Args:
            clients: 全部客户端对象列表
            num_needed: 需要选择的客户端数量
            round_num: 当前轮次
            **kwargs: 策略特定参数（如 train_weights, client_states 等）

        Returns:
            被选中的客户端 ID 列表
        """
        pass

    def presample_for_target(self, target_round: int, num_needed: int, **kwargs) -> List[int]:
        """
        为 target_round 预采样候选池（供预取调度使用）。

        子类可覆盖以实现策略感知的预采样（如 Sticky 按 score 加权、
        SketchClustering 按聚类扩展）。默认回退到均匀随机。

        Args:
            target_round: 目标轮次
            num_needed: 该轮需要选择的客户端数
            **kwargs: 额外参数（如 clients, overcommitment 等）

        Returns:
            预采样的客户端 ID 列表（长度 >= num_needed）
        """
        num_clients = len(kwargs.get('clients', []))
        if num_clients == 0 and hasattr(self, 'num_clients'):
            num_clients = self.num_clients
        oc = kwargs.get('overcommitment', 1.0)
        num_to_sample = max(num_needed, int(num_needed * oc))
        num_to_sample = min(num_to_sample, num_clients)
        rng = np.random.RandomState(target_round + 42)
        return rng.choice(num_clients, num_to_sample, replace=False).tolist()

    def update_signatures(self, client_id: int, params_dict: Dict[str, torch.Tensor]):
        """可选：更新客户端模型参数签名（用于 SketchClustering）。"""
        pass

    def on_round_end(self, selected_ids: List[int], round_num: int, dropped_ids: List[int] = None):
        """可选：每轮结束后的回调。

        Args:
            selected_ids: 本轮被选中的客户端 ID
            round_num: 当前轮次
            dropped_ids: 被 OC 截断丢弃的客户端 ID（None 表示现场选择，无截断丢弃）
        """
        pass

    def get_stats(self) -> Dict:
        """可选：返回策略统计信息。"""
        return {}


# =============================================================================
# 1. 随机采样
# =============================================================================

class RandomSelection(ClientSelectionStrategy):
    """纯随机客户端采样。"""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def select(self, clients, num_needed, round_num=0, **kwargs):
        num_clients = len(clients)
        num_needed = min(num_needed, num_clients)
        selected = self.rng.choice(num_clients, num_needed, replace=False).tolist()
        tag_info(LogTag.CLIENT_SELECT, f"Random  |  selected={sorted(selected)}")
        return selected


# =============================================================================
# 2. Sticky Sampling (包装现有 StickySamplingManager)
# =============================================================================

class StickySelection(ClientSelectionStrategy):
    """
    Sticky Sampling 策略包装器。
    直接代理到 StickySamplingManager，保持与现有预取逻辑的兼容。
    """

    def __init__(self, sticky_manager):
        self.sticky_manager = sticky_manager

    def select(self, clients, num_needed, round_num=0, **kwargs):
        selected = self.sticky_manager.select_for_round(round_num, num_needed)
        tag_info(LogTag.CLIENT_SELECT, f"Sticky  |  selected={sorted(selected)}")
        return selected

    def presample_for_target(self, target_round: int, num_needed: int, **kwargs) -> List[int]:
        """委托给 StickySamplingManager 的预采样逻辑。"""
        return self.sticky_manager.presample_for_target(target_round, num_needed)

    def on_round_end(self, selected_ids, round_num, dropped_ids=None):
        self.sticky_manager.update_on_select(selected_ids)
        if dropped_ids:
            for cid in dropped_ids:
                old_score = self.sticky_manager.sticky_scores.get(cid, 1.0)
                self.sticky_manager.sticky_scores[cid] = max(0.5, old_score * 0.5)

    def get_stats(self):
        return self.sticky_manager.get_stats()


# =============================================================================
# 3. 草图聚类选择 (FedPHE 风格)
# =============================================================================

class SketchClusteringSelection(ClientSelectionStrategy):
    """
    基于 MinHash 草图聚类的客户端选择策略。

    核心流程（对齐 FedPHE）：
      1. 收集每个客户端的模型参数，与全局参数拼接
      2. 量化二值化后生成 MinHash 签名
      3. Gap Statistic 自动确定聚类数 k
      4. Jaccard KMeans 聚类
      5. 每类选样本权重最大的客户端作为代表

    配置参数:
      sim_len: MinHash 签名维度（默认 64）
      quan_threshold: 量化阈值（默认 0.05）
      selection_interval: 每隔多少轮重新聚类（默认 10，0=每轮都聚类）
      max_k: 最大聚类数（默认 num_clients // 2）
    """

    def __init__(
        self,
        num_clients: int,
        sim_len: int = 64,
        quan_threshold: float = 0.05,
        selection_interval: int = 10,
        max_k: Optional[int] = None,
        seed: int = 42,
    ):
        self.num_clients = num_clients
        self.sim_len = sim_len
        self.quan_threshold = quan_threshold
        self.selection_interval = max(1, selection_interval)
        self.max_k = max_k if max_k is not None else max(2, num_clients // 2)
        self.seed = seed

        self.random_R = None          # 延迟初始化（需要知道参数维度）
        self.client_signatures = {}   # {client_id: np.ndarray signature}
        self.selected_clients = None  # 当前选中的客户端缓存
        self.rep_num = [1] * num_clients
        self.weights_clusters = {i: 1.0 for i in range(num_clients)}
        self.selection_history = []

        tag_info(LogTag.CLIENT_SELECT,
                 f"SketchClustering init  |  sim_len={sim_len}  |  "
                 f"threshold={quan_threshold}  |  interval={selection_interval}")

    def _ensure_random_R(self, param_len: int):
        """延迟初始化随机矩阵（仅在第一次知道参数维度时调用）。"""
        if self.random_R is None:
            self.random_R = _gen_random_R(param_len, self.sim_len, seed=self.seed)
            tag_info(LogTag.CLIENT_SELECT,
                     f"SketchClustering random_R initialized  |  dim={param_len}  |  sim_len={self.sim_len}")

    def _compute_signature(self, local_params: np.ndarray, global_params: np.ndarray) -> np.ndarray:
        """计算单个客户端的 MinHash 签名。"""
        # 拼接全局参数和本地参数 => shape: (param_len, 2)
        mat = np.stack([global_params, local_params], axis=1)
        # 量化二值化
        quan_matrix = _quan_params(mat, self.quan_threshold)
        # 生成签名矩阵 (sim_len, 2)
        sig_mat = _sigMatrixGen(quan_matrix, self.random_R, self.sim_len)
        # 提取本地参数对应的签名列（第 1 列）
        return sig_mat[:, 1]

    def update_signatures_from_state_dict(
        self,
        client_id: int,
        state_dict: Dict[str, torch.Tensor],
        global_state_dict: Dict[str, torch.Tensor],
    ):
        """从客户端和全局模型的 state_dict 更新签名。"""
        # 扁平化参数
        local_flat = []
        global_flat = []
        for key in sorted(state_dict.keys()):
            if key not in global_state_dict:
                continue
            local_flat.append(state_dict[key].cpu().numpy().flatten())
            global_flat.append(global_state_dict[key].cpu().numpy().flatten())
        local_params = np.concatenate(local_flat)
        global_params = np.concatenate(global_flat)

        self._ensure_random_R(len(local_params))
        sig = self._compute_signature(local_params, global_params)
        self.client_signatures[client_id] = sig

    def select(self, clients, num_needed, round_num=0, **kwargs):
        """
        kwargs 支持:
          - train_weights: List[float] 每个客户端的样本权重
          - global_state: Dict[str, torch.Tensor] 全局模型状态（用于首次签名）
          - client_states: Dict[int, Dict[str, torch.Tensor]] 每个客户端的模型状态
        """
        train_weights = kwargs.get('train_weights', [1.0] * self.num_clients)
        client_states = kwargs.get('client_states', None)
        global_state = kwargs.get('global_state', None)

        # 如果提供了客户端状态，更新签名
        if client_states is not None and global_state is not None:
            for cid, state in client_states.items():
                self.update_signatures_from_state_dict(cid, state, global_state)

        # 检查是否需要重新聚类
        need_reselect = (
            self.selected_clients is None
            or len(self.client_signatures) < self.num_clients
            or round_num % self.selection_interval == 0
        )

        if not need_reselect and self.selected_clients is not None:
            # 使用缓存的选择结果
            selected = [c for c in self.selected_clients if c < len(clients)]
            tag_info(LogTag.CLIENT_SELECT,
                     f"SketchClustering (cached)  |  round={round_num}  |  selected={sorted(selected)}")
            self.selection_history.append(selected.copy())
            return selected

        # 确保所有客户端都有签名
        if len(self.client_signatures) < self.num_clients:
            # 签名不足，回退到随机选择（第一轮常见）
            tag_warn(LogTag.CLIENT_SELECT,
                     f"SketchClustering signatures insufficient ({len(self.client_signatures)}/{self.num_clients}), "
                     f"fallback to random")
            rng = np.random.RandomState(self.seed + round_num)
            selected = rng.choice(self.num_clients, min(num_needed, self.num_clients), replace=False).tolist()
            self.selected_clients = selected
            self.selection_history.append(selected.copy())
            return selected

        # 构建签名矩阵
        signatures = []
        for cid in range(self.num_clients):
            sig = self.client_signatures.get(cid)
            if sig is None:
                sig = np.zeros(self.sim_len, dtype=int)
            signatures.append(sig)
        hash_mat = np.array(signatures)

        # 聚类选择
        max_k = min(self.max_k, len(hash_mat))
        selected, rep_num, weights_clusters = _clusters_selection_L2(
            hash_mat, max_k, train_weights
        )

        self.rep_num = rep_num
        self.weights_clusters = weights_clusters

        # 如果选中的数量不足 num_needed，从剩余中随机补足
        if len(selected) < num_needed:
            remaining = [c for c in range(self.num_clients) if c not in selected]
            extra_needed = min(num_needed - len(selected), len(remaining))
            rng = np.random.RandomState(self.seed + round_num)
            extra = rng.choice(remaining, extra_needed, replace=False).tolist()
            selected = selected + extra

        # 缓存补足后的最终选择结果（供后续轮次直接复用）
        self.selected_clients = selected

        tag_info(LogTag.CLIENT_SELECT,
                 f"SketchClustering  |  round={round_num}  |  k_opt={max_k}  |  "
                 f"selected={sorted(selected)}  |  n_signatures={len(self.client_signatures)}")
        self.selection_history.append(selected.copy())
        return selected

    def presample_for_target(self, target_round: int, num_needed: int, **kwargs) -> List[int]:
        """
        SketchClustering 的预采样：复用 select() 结果（对齐 FedFetch）。

        FedFetch 设计原则：预采样 = 提前 R 轮运行客户端选择函数本身。
        虽然未来轮次的聚类结果可能有偏差，但论文指出"提前几轮选择
        对统计效用影响很小"。使用当前缓存的聚类结果已足够。
        """
        clients = kwargs.get('clients', [])
        if clients:
            return self.select(clients, num_needed, round_num=target_round)
        return super().presample_for_target(target_round, num_needed, **kwargs)

    def get_stats(self):
        return {
            "num_signatures": len(self.client_signatures),
            "selection_history": self.selection_history,
            "rep_num": self.rep_num,
        }


# =============================================================================
# 4. 公平性包装器
# =============================================================================

class FairnessWrapper(ClientSelectionStrategy):
    """
    公平性包装器，包装任意基础策略，保证长期未参与的客户端也能被选中。

    机制:
      - 跟踪每个客户端的参与次数和总轮数
      - 如果某客户端的参与率低于 min_participation_ratio，则强制将其加入选中列表
      - 被强制加入的客户端会替换掉已选客户端中"超额参与"的客户端
    """

    def __init__(
        self,
        base_strategy: ClientSelectionStrategy,
        num_clients: int,
        min_participation_ratio: float = 0.3,
    ):
        self.base = base_strategy
        self.num_clients = num_clients
        self.min_participation_ratio = min_participation_ratio
        self.participation_count = defaultdict(int)
        self.total_rounds = 0
        self.forced_history = []

    def select(self, clients, num_needed, round_num=0, **kwargs):
        self.total_rounds += 1

        # 先让基础策略选
        selected = self.base.select(clients, num_needed, round_num, **kwargs)
        selected_set = set(selected)

        # 检查哪些客户端长期未参与
        under_represented = []
        for cid in range(self.num_clients):
            ratio = self.participation_count[cid] / max(1, self.total_rounds)
            if ratio < self.min_participation_ratio and cid not in selected_set:
                under_represented.append(cid)

        forced = []
        if under_represented and len(selected) >= num_needed:
            # 需要替换：移除已选客户端中参与率最高的，加入 under_represented
            sorted_by_participation = sorted(
                selected,
                key=lambda c: self.participation_count[c],
                reverse=True,
            )
            to_replace = sorted_by_participation[:len(under_represented)]
            new_selected = [c for c in selected if c not in to_replace]
            new_selected.extend(under_represented[:num_needed - len(new_selected)])
            forced = under_represented[:len(to_replace)]
            selected = new_selected[:num_needed]
        elif under_represented and len(selected) < num_needed:
            # 直接补足
            can_add = min(num_needed - len(selected), len(under_represented))
            selected.extend(under_represented[:can_add])
            forced = under_represented[:can_add]

        # 更新参与计数
        for cid in selected:
            self.participation_count[cid] += 1

        if forced:
            tag_info(LogTag.CLIENT_SELECT,
                     f"FairnessWrapper forced inclusion: {forced}  |  "
                     f"participation_rates={[round(self.participation_count[c]/self.total_rounds,2) for c in range(self.num_clients)]}")
            self.forced_history.append((round_num, forced.copy()))

        tag_info(LogTag.CLIENT_SELECT,
                 f"FairnessWrapper  |  selected={sorted(selected)}  |  "
                 f"under_represented={under_represented}")
        return selected

    def update_signatures(self, client_id, params_dict):
        if hasattr(self.base, 'update_signatures'):
            self.base.update_signatures(client_id, params_dict)

    def presample_for_target(self, target_round: int, num_needed: int, **kwargs) -> List[int]:
        if hasattr(self.base, 'presample_for_target'):
            return self.base.presample_for_target(target_round, num_needed, **kwargs)
        return super().presample_for_target(target_round, num_needed, **kwargs)

    def on_round_end(self, selected_ids, round_num, dropped_ids=None):
        if hasattr(self.base, 'on_round_end'):
            self.base.on_round_end(selected_ids, round_num, dropped_ids=dropped_ids)

    def get_stats(self):
        base_stats = self.base.get_stats() if hasattr(self.base, 'get_stats') else {}
        participation_rates = {
            cid: round(self.participation_count[cid] / max(1, self.total_rounds), 3)
            for cid in range(self.num_clients)
        }
        return {
            **base_stats,
            "participation_count": dict(self.participation_count),
            "participation_rates": participation_rates,
            "forced_history": self.forced_history,
        }


# =============================================================================
# 5. Power-of-Choice (PoC)  —  AISTATS 2022
# =============================================================================

class PowerOfChoiceSelection(ClientSelectionStrategy):
    """
    Power-of-Choice 策略 (Cho et al., AISTATS 2022)。

    核心思想：
      1. 从所有客户端中随机抽取 d 个候选者
      2. 从这 d 个中选出 local loss 最大的 m 个参与训练

    为什么有效：
      loss 大的客户端通常含有更多"新信息"，对全局模型改进最大。
      比纯随机收敛更快，且实现极简。

    配置参数 (config.yaml -> client_selection -> poc):
      d: 候选池大小（默认 20）
    """

    def __init__(self, num_clients: int, d: int = None, seed: int = 42,
                 sampling_rate: float = None):
        self.num_clients = num_clients
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # 自动计算 d：基于 num_needed 的 2 倍（AISTATS 2022 推荐）
        num_needed = max(1, int(num_clients * (sampling_rate or 0.5)))
        default_d = num_needed * 2
        min_d = max(num_needed, min(5, num_clients))  # 至少 num_needed 或 5
        max_d = num_clients

        if d is None or d <= 0:
            self.d = min(max_d, default_d)
            tag_info(LogTag.CLIENT_SELECT,
                     f"PoC init  |  auto_d={self.d} (num_needed={num_needed}, 2x)")
        else:
            raw_d = d
            self.d = min(max_d, max(min_d, d))
            if self.d != raw_d:
                tag_info(LogTag.CLIENT_SELECT,
                         f"PoC init  |  requested_d={raw_d}  |  "
                         f"clamped_d={self.d} (range=[{min_d},{max_d}])")
            else:
                tag_info(LogTag.CLIENT_SELECT,
                         f"PoC init  |  d={self.d}  |  num_needed={num_needed}")

        # 记录每个客户端最近一轮的 training loss
        self.client_losses: Dict[int, float] = defaultdict(float)
        self.selection_history: List[Tuple[int, List[int]]] = []

    def select(self, clients, num_needed, round_num=0, **kwargs):
        num_needed = min(num_needed, self.num_clients)
        all_ids = list(range(self.num_clients))

        # Step 1: 随机选 d 个候选
        d = min(self.d, self.num_clients)
        candidates = self.rng.choice(all_ids, size=d, replace=False).tolist()

        # Step 2: 从候选中选 loss 最大的 num_needed 个
        # 如果某个候选没有 loss 记录，赋予一个随机小值避免总是选同一批
        def _score(cid):
            base = self.client_losses.get(cid, 0.0)
            if base <= 0:
                # 冷启动：给一个基于 cid 的伪随机值，保证初始多样性
                base = 0.01 + 0.001 * (cid % 7)
            return base

        selected = sorted(candidates, key=_score, reverse=True)[:num_needed]

        loss_strs = [f"{_score(c):.3f}" for c in selected]
        tag_info(LogTag.CLIENT_SELECT,
                 f"PoC  |  d={d}  |  candidates={sorted(candidates)}  |  "
                 f"selected={sorted(selected)}  |  losses={loss_strs}")
        self.selection_history.append((round_num, selected.copy()))
        return selected

    def on_round_end(self, selected_ids, round_num, dropped_ids=None):
        """PoC 不需要显式更新——loss 记录由外部实验循环通过 kwargs 传入。
        但这里提供一个钩子，方便未来扩展（如时间衰减）。"""
        pass

    def get_stats(self):
        return {
            "d": self.d,
            "loss_records": dict(self.client_losses),
            "history": self.selection_history,
        }


# =============================================================================
# 6. TiFL  —  HPDC 2020
# =============================================================================

class TiFLSelection(ClientSelectionStrategy):
    """
    TiFL: Tier-based Federated Learning (Chai et al., HPDC 2020 / SC 2021)。

    核心思想：
      按客户端资源能力（如下行带宽）分成若干 Tier，
      每轮从某个 Tier 中选客户端，同 Tier 内完成时间相近，减少 straggler。

    实现方式：
      - 按带宽升序排列，均匀切分为 num_tiers 层
      - 轮询（round-robin）选择 Tier，保证各层都有机会参与
      - 若当前 Tier 人数不足，优先从相邻 Tier 借用（带宽更接近），再全局补

    配置参数 (config.yaml -> client_selection -> tifl):
      num_tiers: 分层数（默认 null=自动）
        - null: 自动计算。约束每层人数 >= num_needed，避免频繁跨层借用。
                公式: clamp(floor(N / num_needed), 2, 5)
        - int:  显式指定
    """

    def __init__(self, num_clients: int, bandwidth_info: Dict[int, float] = None,
                 num_tiers: int = None, seed: int = 42, sampling_rate: float = 0.5):
        self.num_clients = num_clients
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.current_tier = 0

        num_needed = max(1, int(num_clients * sampling_rate))
        # 自动计算 tier 数：约束每层 >= num_needed，且至少 2 层、最多 5 层
        if num_tiers is None:
            max_tiers = num_clients // num_needed
            self.num_tiers = max(2, min(5, max_tiers))
        else:
            self.num_tiers = max(1, num_tiers)

        # 构建 Tier：按带宽升序，均匀切分
        bw = bandwidth_info or {}
        sorted_cids = sorted(range(num_clients), key=lambda c: bw.get(c, 0.0))
        tier_size = max(1, num_clients // self.num_tiers)
        self.tiers: List[List[int]] = []
        for i in range(self.num_tiers):
            start = i * tier_size
            end = start + tier_size if i < self.num_tiers - 1 else num_clients
            self.tiers.append(sorted_cids[start:end])

        # 记录每层带宽范围，供日志使用
        self.tier_stats = []
        for tier in self.tiers:
            bws = [bw.get(c, 0.0) for c in tier]
            self.tier_stats.append((min(bws) if bws else 0, max(bws) if bws else 0))
        
        tag_info(LogTag.CLIENT_SELECT,
                 f"TiFL init  |  num_tiers={self.num_tiers}  |  "
                 f"tier_sizes={[len(t) for t in self.tiers]}  |  "
                 f"num_needed={num_needed}")

    def select(self, clients, num_needed, round_num=0, **kwargs):
        num_needed = min(num_needed, self.num_clients)
        tier_idx = self.current_tier
        tier = self.tiers[tier_idx]
        self.current_tier = (self.current_tier + 1) % self.num_tiers

        rng = np.random.RandomState(self.seed + round_num)
        selected = []
        selected_set = set()

        # 1) 优先从当前 Tier 选
        if len(tier) >= num_needed:
            selected = rng.choice(tier, num_needed, replace=False).tolist()
        else:
            selected = tier.copy()
            selected_set = set(selected)
            need_more = num_needed - len(selected)

            # 2) 人数不足时，优先从相邻 Tier 借用（带宽更接近当前 Tier）
            #    按距离当前 tier 的远近依次尝试
            neighbor_indices = []
            for dist in range(1, self.num_tiers):
                if tier_idx - dist >= 0:
                    neighbor_indices.append(tier_idx - dist)
                if tier_idx + dist < self.num_tiers:
                    neighbor_indices.append(tier_idx + dist)

            for ni in neighbor_indices:
                if need_more <= 0:
                    break
                candidates = [c for c in self.tiers[ni] if c not in selected_set]
                if candidates:
                    take = min(need_more, len(candidates))
                    chosen = rng.choice(candidates, take, replace=False).tolist()
                    selected.extend(chosen)
                    selected_set.update(chosen)
                    need_more -= take

            # 3) 仍然不够，从全局补
            if need_more > 0:
                all_remaining = [c for c in range(self.num_clients) if c not in selected_set]
                if all_remaining:
                    take = min(need_more, len(all_remaining))
                    chosen = rng.choice(all_remaining, take, replace=False).tolist()
                    selected.extend(chosen)

        lo, hi = self.tier_stats[tier_idx] if self.tier_stats else (0, 0)
        fallback_flag = " (fallback)" if any(c not in self.tiers[tier_idx] for c in selected) else ""
        tag_info(LogTag.CLIENT_SELECT,
                 f"TiFL  |  tier={tier_idx + 1}/{self.num_tiers}{fallback_flag}  |  "
                 f"bw=[{lo:.0f},{hi:.0f}]kbps  |  selected={sorted(selected)}")
        return selected

    def get_stats(self):
        return {
            "num_tiers": self.num_tiers,
            "tier_sizes": [len(t) for t in self.tiers],
            "tier_bw_ranges": self.tier_stats,
        }


# =============================================================================
# 7. HACCS  —  IPDPS 2022
# =============================================================================

class HACCSSelection(ClientSelectionStrategy):
    """
    HACCS: Heterogeneity-Aware Clustered Client Selection (Wolfrath et al., IPDPS 2022)。

    核心思想：
      按设备资源画像（带宽、数据量等）聚类，每轮从各簇中按比例选客户端，
      保证系统异构性和数据多样性同时被考虑。

    实现方式：
      - 特征向量 = [下行带宽_kbps, 数据量_samples]
      - KMeans 聚成 num_clusters 簇
      - 每轮从每个簇中按比例选，配额不足时自动再分配

    配置参数 (config.yaml -> client_selection -> haccs):
      num_clusters: 聚类数（默认 null=自动计算）
      recluster_interval: 每隔多少轮重新聚类（默认 0=每轮都聚）
    """

    def __init__(self, num_clients: int, bandwidth_info: Dict[int, float] = None,
                 train_weights: List[int] = None,
                 num_clusters: int = None, recluster_interval: int = 0, seed: int = 42,
                 sampling_rate: float = None):
        self.num_clients = num_clients
        self.recluster_interval = recluster_interval
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.last_recluster_round = -1
        self.clusters: Dict[int, int] = {}  # cid -> cluster_id
        self.sampling_rate = sampling_rate

        # 保存原始特征，用于重新聚类
        self.bandwidth_info = bandwidth_info or {}
        self.train_weights = train_weights or [100] * num_clients

        # 自动计算 num_clusters
        self.num_clusters = self._compute_num_clusters(num_clusters)
        tag_info(LogTag.CLIENT_SELECT,
                 f"HACCS init  |  requested_k={num_clusters}  |  "
                 f"auto_k={self.num_clusters}  |  clients={num_clients}")
        self._do_clustering()

    def _compute_num_clusters(self, num_clusters: Optional[int]) -> int:
        """
        自动计算合理的聚类数。

        策略：
          - 若用户显式传入整数，直接使用（但不超过 num_clients）
          - 若传入 None，基于 num_clients 和 sampling_rate 自动计算

        自动公式：
          k = clamp( sqrt(num_clients), 3, num_clients )
          同时确保 k <= num_needed // 2（保证每个簇至少贡献 2 人）
        """
        if num_clusters is not None and num_clusters > 0:
            return min(num_clusters, self.num_clients)

        # 自动计算
        num_needed = max(1, int(self.num_clients * (self.sampling_rate or 0.5)))
        # 目标：每个簇平均 3-5 人，且 base_per_cluster >= 2
        suggested = int(self.num_clients ** 0.5)  # sqrt(num_clients)
        max_k = min(num_needed // 2, self.num_clients)  # 保证 base >= 2
        min_k = 3
        k = max(min_k, min(suggested, max_k))
        return k

    def _do_clustering(self):
        """基于资源画像执行 KMeans 聚类。"""
        features = np.array([
            [self.bandwidth_info.get(i, 0.0), self.train_weights[i]]
            for i in range(self.num_clients)
        ], dtype=float)
        # 标准化
        mean = features.mean(axis=0)
        std = features.std(axis=0) + 1e-8
        features_norm = (features - mean) / std

        n_clusters = min(self.num_clusters, self.num_clients)
        if n_clusters <= 1:
            self.clusters = {i: 0 for i in range(self.num_clients)}
            return

        kmeans = KMeans(n_clusters=n_clusters, random_state=self.seed, n_init=10)
        labels = kmeans.fit_predict(features_norm)
        self.clusters = {i: int(labels[i]) for i in range(self.num_clients)}
        tag_info(LogTag.CLIENT_SELECT,
                 f"HACCS reclustered  |  k={n_clusters}  |  "
                 f"cluster_sizes={[sum(1 for v in self.clusters.values() if v == c) for c in range(n_clusters)]}")

    def select(self, clients, num_needed, round_num=0, **kwargs):
        num_needed = min(num_needed, self.num_clients)

        # 按需重新聚类
        if self.recluster_interval == 0 or (
            self.last_recluster_round >= 0
            and round_num - self.last_recluster_round >= self.recluster_interval
        ):
            if 'train_weights' in kwargs:
                self.train_weights = kwargs['train_weights']
            self._do_clustering()
            self.last_recluster_round = round_num

        # 按簇分组
        cluster_members: Dict[int, List[int]] = defaultdict(list)
        for cid, clabel in self.clusters.items():
            cluster_members[clabel].append(cid)

        n_clusters = len(cluster_members)
        base_per_cluster = num_needed // n_clusters
        remainder = num_needed % n_clusters

        # =============================================================
        # 改进：配额再分配机制
        #   第一轮：按基础配额分配，记录未用完的 leftover
        #   第二轮：将 leftover 分配给还有剩余成员的簇
        # 这样避免小簇（如只有 2 人）浪费配额
        # =============================================================
        rng = np.random.RandomState(self.seed + round_num)
        selected = []
        leftover = 0
        selected_set = set()

        # Round 1: 基础配额分配
        for clabel, members in sorted(cluster_members.items()):
            desired = base_per_cluster + (1 if clabel < remainder else 0)
            actual = min(desired, len(members))
            if actual > 0:
                chosen = rng.choice(members, actual, replace=False).tolist()
                selected.extend(chosen)
                selected_set.update(chosen)
            leftover += desired - actual  # 记录因成员不足而剩余的配额

        # Round 2: 配额再分配
        if leftover > 0:
            unselected = [c for c in range(self.num_clients) if c not in selected_set]
            # 优先从成员充足的簇中补充
            pool = []
            for clabel, members in sorted(cluster_members.items()):
                remaining_in_cluster = [c for c in members if c not in selected_set]
                pool.extend(remaining_in_cluster)
            # 如果 pool 不够，从全体未选中客户端补充
            if len(pool) < leftover:
                pool = unselected
            if pool:
                extra_count = min(leftover, len(pool))
                extra = rng.choice(pool, extra_count, replace=False).tolist()
                selected.extend(extra)
                selected_set.update(extra)
                leftover -= extra_count

        # 安全截断（理论上不应触发，但保留以防边界情况）
        selected = selected[:num_needed]

        tag_info(LogTag.CLIENT_SELECT,
                 f"HACCS  |  k={n_clusters}  |  base={base_per_cluster}  |  "
                 f"selected={len(selected)}/{num_needed}  |  "
                 f"cluster_map={ {c:self.clusters[c] for c in selected} }")
        return selected

    def get_stats(self):
        cluster_sizes = defaultdict(int)
        for clabel in self.clusters.values():
            cluster_sizes[clabel] += 1
        return {
            "num_clusters": self.num_clusters,
            "cluster_sizes": dict(cluster_sizes),
            "recluster_interval": self.recluster_interval,
        }


# =============================================================================
# 8. Oort  —  OSDI 2021
# =============================================================================

class OortSelection(ClientSelectionStrategy):
    """
    Oort: Efficient Federated Learning via Guided Participant Selection (Lai et al., OSDI 2021)。

    核心思想：
      同时考虑统计效用（带来的 loss 下降）和系统效率（完成时间），
      选择 utility = stat_utility / time_efficiency 最高的客户端。
      采用 ε-greedy 保留少量随机探索，避免陷入局部最优。

    实现方式：
      - 记录每个客户端的历史 loss 和训练时间
      - 计算效用：utility_i = (loss_improvement_i) / (train_time_i + upload_time_i)
      - 以 1-ε 概率选 top utility，以 ε 概率随机探索

    配置参数 (config.yaml -> client_selection -> oort):
      exploration_factor: ε, 探索率（默认 0.1）
      util_time_alpha: 时间惩罚系数（默认 1.0）
    """

    def __init__(self, num_clients: int, exploration_factor: float = 0.1,
                 util_time_alpha: float = 1.0, seed: int = 42):
        self.num_clients = num_clients
        self.epsilon = max(0.0, min(1.0, exploration_factor))
        self.alpha = util_time_alpha
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # 历史记录
        self.loss_history: Dict[int, List[float]] = defaultdict(list)
        self.time_history: Dict[int, List[float]] = defaultdict(list)
        self.utility: Dict[int, float] = {i: 1.0 for i in range(num_clients)}

    def select(self, clients, num_needed, round_num=0, **kwargs):
        num_needed = min(num_needed, self.num_clients)
        all_ids = list(range(self.num_clients))

        # 根据 kwargs 中可能传入的最新数据更新 utility
        if 'client_losses' in kwargs:
            self._update_utilities(kwargs['client_losses'], kwargs.get('client_times', {}))

        # ε-greedy
        rng = np.random.RandomState(self.seed + round_num)
        if self.rng.rand() < self.epsilon:
            # 探索：均匀随机
            selected = rng.choice(all_ids, num_needed, replace=False).tolist()
            tag_info(LogTag.CLIENT_SELECT,
                     f"Oort  |  explore(ε={self.epsilon})  |  selected={sorted(selected)}")
        else:
            # 利用：选 top utility
            sorted_by_util = sorted(all_ids, key=lambda c: self.utility.get(c, 0.0), reverse=True)
            selected = sorted_by_util[:num_needed]
            tag_info(LogTag.CLIENT_SELECT,
                     f"Oort  |  exploit(ε={self.epsilon})  |  "
                     f"top_utility={ [(c, round(self.utility[c], 3)) for c in selected[:5]] }  |  "
                     f"selected={sorted(selected)}")
        return selected

    def _update_utilities(self, client_losses: Dict[int, float], client_times: Dict[int, float]):
        """根据最新一轮数据更新各客户端效用。"""
        for cid, loss in client_losses.items():
            self.loss_history[cid].append(loss)
            # 计算统计效用：最近两次 loss 的下降量（越大越好）
            losses = self.loss_history[cid]
            if len(losses) >= 2:
                stat_util = max(0.0, losses[-2] - losses[-1])
            else:
                stat_util = 0.1  # 冷启动默认值

            # 系统效率：训练时间（越小越好，取倒数）
            time_s = client_times.get(cid, 5.0)
            time_eff = 1.0 / (time_s ** self.alpha + 0.1)

            self.utility[cid] = stat_util * time_eff

    def on_round_end(self, selected_ids, round_num, dropped_ids=None):
        """Oort 不需要像 Sticky 那样惩罚被丢弃者，但这里预留接口。"""
        pass

    def get_stats(self):
        return {
            "epsilon": self.epsilon,
            "utility": dict(self.utility),
            "loss_history_len": {k: len(v) for k, v in self.loss_history.items()},
        }


# =============================================================================
# 9. 通用预采样池管理器（与策略解耦）
# =============================================================================

class PrefetchPoolManager:
    """
    通用预采样池管理器，与具体客户端选择策略解耦。

    职责：
      - 维护 {target_round: candidate_ids} 的预采样池
      - 调用策略的 presample_for_target() 生成候选池
      - 为预取广播提供"池内客户端"范围控制
      - 清理过期池子
    """

    def __init__(self, num_clients: int, overcommitment: float = 1.0):
        self.num_clients = num_clients
        self.overcommitment = max(1.0, overcommitment)
        self.presample_pool: Dict[int, List[int]] = {}

    def presample(
        self,
        target_round: int,
        num_needed: int,
        strategy: ClientSelectionStrategy,
        **kwargs,
    ) -> List[int]:
        """
        为 target_round 预采样候选池。

        流程：
          1. 调用 strategy.presample_for_target() 获取策略感知的候选集
          2. 若数量不足，用均匀随机补足到 num_needed * overcommitment
          3. 存入 presample_pool
        """
        sampled = strategy.presample_for_target(target_round, num_needed, **kwargs)
        num_to_sample = max(num_needed, int(num_needed * self.overcommitment))
        num_to_sample = min(num_to_sample, self.num_clients)

        if len(sampled) < num_to_sample:
            remaining = [c for c in range(self.num_clients) if c not in sampled]
            rng = np.random.RandomState(target_round + 999)
            extra_count = min(num_to_sample - len(sampled), len(remaining))
            extra = rng.choice(remaining, extra_count, replace=False).tolist()
            sampled = sampled + extra

        self.presample_pool[target_round] = sampled[:num_to_sample]
        tag_info(LogTag.PREFETCH,
                 f"PoolManager presample  |  target={target_round}  |  "
                 f"sampled={len(sampled)} (need={num_needed}, OC={self.overcommitment})")
        return sampled

    def get_pool(self, target_round: int) -> List[int]:
        """获取指定目标轮次的预采样池。"""
        return self.presample_pool.get(target_round, [])

    def get_active_pools(self, current_round: int, num_rounds: int) -> List[int]:
        """获取当前仍有效的目标轮次列表。"""
        return [
            tr for tr in self.presample_pool.keys()
            if current_round <= tr < num_rounds
        ]

    def get_all_future_ids(self, current_round: int, num_rounds: int) -> List[int]:
        """获取所有活跃池中的客户端 ID 并集。"""
        future_ids = set()
        for tr in self.get_active_pools(current_round, num_rounds):
            future_ids.update(self.presample_pool[tr])
        return sorted(future_ids)

    def cleanup(self, current_round: int, num_rounds: int = None):
        """清理已过期的预采样池。"""
        expired = [tr for tr in list(self.presample_pool.keys()) if tr < current_round]
        if num_rounds is not None:
            expired += [tr for tr in list(self.presample_pool.keys()) if tr >= num_rounds]
        for tr in set(expired):
            del self.presample_pool[tr]

    def get_stats(self) -> Dict:
        return {
            "active_pools": sorted(self.presample_pool.keys()),
            "num_active_pools": len(self.presample_pool),
        }


# =============================================================================
# 工厂函数
# =============================================================================

def create_client_selection_strategy(config: Dict, num_clients: int, **kwargs):
    """
    根据配置创建客户端选择策略。

    Args:
        config: 配置字典（通常是 self.config）
        num_clients: 客户端总数
        **kwargs: 额外参数（如 sticky_manager 等）

    Returns:
        ClientSelectionStrategy 实例
    """
    cfg = config.get('client_selection', {})
    strategy_name = cfg.get('strategy', 'random')
    seed = config.get('system', {}).get('random_seed', 42)

    base_strategy = None

    if strategy_name == 'random':
        base_strategy = RandomSelection(seed=seed)

    elif strategy_name == 'sticky':
        sticky_manager = kwargs.get('sticky_manager')
        if sticky_manager is None:
            from ckks_fed.sticky_sampling import StickySamplingManager
            prefetch_cfg = config.get('prefetch', {})
            sticky_cfg = cfg.get('sticky', {})
            oc = prefetch_cfg.get('overcommitment', 1.0)
            change_num_base = sticky_cfg.get('change_num_base')
            if change_num_base is None:
                change_num = prefetch_cfg.get('sticky_change_num', 1)
            else:
                change_num = max(1, round(change_num_base * oc))
            sticky_manager = StickySamplingManager(
                num_clients=num_clients,
                overcommitment=oc,
                decay_factor=sticky_cfg.get('score_decay', prefetch_cfg.get('sticky_decay', 0.9)),
                seed=seed,
                use_sticky=sticky_cfg.get('use_sticky', prefetch_cfg.get('use_sticky_sampling', True)),
                sticky_group_size=sticky_cfg.get('group_size', prefetch_cfg.get('sticky_group_size', None)),
                change_num=change_num,
                bandwidth_info=kwargs.get('bandwidth_info', {}),
            )
        base_strategy = StickySelection(sticky_manager)

    elif strategy_name == 'sketch_clustering':
        base_strategy = SketchClusteringSelection(
            num_clients=num_clients,
            sim_len=cfg.get('sim_len', 64),
            quan_threshold=cfg.get('quan_threshold', 0.05),
            selection_interval=cfg.get('selection_interval', 10),
            max_k=cfg.get('max_k', None),
            seed=seed,
        )

    elif strategy_name == 'poc':
        base_strategy = PowerOfChoiceSelection(
            num_clients=num_clients,
            d=cfg.get('poc', {}).get('d', None),
            seed=seed,
            sampling_rate=config.get('system', {}).get('client_sampling_rate', 0.5),
        )

    elif strategy_name == 'tifl':
        base_strategy = TiFLSelection(
            num_clients=num_clients,
            bandwidth_info=kwargs.get('bandwidth_info', {}),
            num_tiers=cfg.get('tifl', {}).get('num_tiers', None),
            seed=seed,
            sampling_rate=config.get('system', {}).get('client_sampling_rate', 0.5),
        )

    elif strategy_name == 'haccs':
        base_strategy = HACCSSelection(
            num_clients=num_clients,
            bandwidth_info=kwargs.get('bandwidth_info', {}),
            train_weights=kwargs.get('train_weights', None),
            num_clusters=cfg.get('haccs', {}).get('num_clusters', None),
            recluster_interval=cfg.get('haccs', {}).get('recluster_interval', 0),
            seed=seed,
            sampling_rate=config.get('system', {}).get('client_sampling_rate', 0.5),
        )

    elif strategy_name == 'oort':
        base_strategy = OortSelection(
            num_clients=num_clients,
            exploration_factor=cfg.get('oort', {}).get('exploration_factor', 0.1),
            util_time_alpha=cfg.get('oort', {}).get('util_time_alpha', 1.0),
            seed=seed,
        )

    else:
        logger.warning(f"Unknown client_selection strategy '{strategy_name}', fallback to random")
        base_strategy = RandomSelection(seed=seed)

    # 公平性包装器
    if cfg.get('fairness', {}).get('enabled', False):
        base_strategy = FairnessWrapper(
            base_strategy=base_strategy,
            num_clients=num_clients,
            min_participation_ratio=cfg['fairness'].get('min_participation_ratio', 0.3),
        )

    tag_info(LogTag.CLIENT_SELECT,
             f"Strategy created: {strategy_name}  |  fairness={cfg.get('fairness', {}).get('enabled', False)}")
    return base_strategy
