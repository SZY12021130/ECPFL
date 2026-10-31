"""
KGC 成对盲化掩码（Pairwise Blinding Mask）模块
===============================================

可插拔的隐私增强组件：KGC 为每对客户端 (i, k) 生成共享种子 s_{i,k}=s_{k,i}，
客户端 i 在轮次 t、batch j 的掩码为：

    b_{i,j}^{(t)} = (1 / w_i) * sum_{k != i} sgn(i,k) * PRNG(s_{i,k}, t, j)

其中 sgn(i,k) = +1 if i < k else -1。

TEE 聚合后，参与集合 S_j 中的加权掩码和为：
    sum_{i in S_j} w_i * b_{i,j}^{(t)} = sum_{i in S_j} sum_{k != i} sgn(i,k) * PRNG(...)

注意该和**与权重无关**，TEE 可独立重新计算并精确补偿。

设计要点
--------
1. 【可插拔】默认关闭，通过 config['blinding_mask']['enabled'] 控制
2. 【成对种子】每对客户端共享一个种子，独立生成掩码
3. 【轮次演化】PRNG 依赖轮次 t，每轮掩码不同，防止跨轮次攻击
4. 【扁平化对齐】掩码与 model_update 按相同 key 排序后扁平化，确保与 CKKS 打包一致
5. 【稀疏化兼容】当 sparsification != "none" 时，TEE 显式减去掩码贡献
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class PairwiseBlindingMask:
    """
    KGC 成对盲化掩码管理器。

    Args:
        config: 配置字典，支持字段：
            - enabled (bool): 是否启用，默认 False
            - mask_range (float): 掩码采样范围 [-B, B]，默认 1.0
            - compensation_mode (str): TEE 补偿模式，"auto" | "always" | "never"
                * auto:   仅当 sparsification != "none" 时补偿（默认）
                * always: 总是显式补偿
                * never:  从不补偿（仅在 NoSparsification 下精确）
            - apply_mode (str): "post_topk" | "pre_topk"
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.enabled = cfg.get('enabled', False)
        self.mask_range = float(cfg.get('mask_range', 1.0))
        self.compensation_mode = cfg.get('compensation_mode', 'auto')
        self.apply_mode = cfg.get('apply_mode', 'post_topk')

        if self.enabled:
            logger.info(
                f"PairwiseBlindingMask enabled | range=[-{self.mask_range:.0e}, {self.mask_range:.0e}] | "
                f"compensation={self.compensation_mode} | apply_mode={self.apply_mode}"
            )
        else:
            logger.info("PairwiseBlindingMask disabled")

    # ==================================================================
    # PRNG：确定性伪随机生成器
    # ==================================================================
    def _prng(self, seed: int, round_num: int, batch_idx: int, length: int) -> np.ndarray:
        """
        基于种子、轮次、batch 索引生成确定性随机数组。

        输出范围: [-mask_range, mask_range]
        """
        # 组合种子，确保不同 (seed, round, batch) 产生独立序列
        combined_seed = int(seed) + int(round_num) * 1000000 + int(batch_idx) * 1000
        rng = np.random.default_rng(combined_seed)
        return rng.uniform(-self.mask_range, self.mask_range, length).astype(np.float64)

    # ==================================================================
    # 掩码生成（KGC 离线执行）
    # ==================================================================
    def generate_masks(
        self,
        num_clients: int,
        weights: List[float],
        shapes: Dict[str, Tuple],
        total_elements: int,
        batch_size: int,
    ) -> List[Dict[str, Any]]:
        """
        为每个客户端生成成对种子和掩码描述。

        Args:
            num_clients: 客户端数量 n
            weights:     每个客户端的权重列表 [w_1, ..., w_n]
            shapes:      模型参数形状字典
            total_elements: 扁平化后的总元素数
            batch_size:  CKKS batch_size

        Returns:
            List[mask_dict]，每个 mask_dict 包含客户端掩码所需的全部信息
        """
        if num_clients != len(weights):
            raise ValueError(f"num_clients ({num_clients}) != len(weights) ({len(weights)})")
        if num_clients == 0:
            return []

        rng = np.random.default_rng(seed=42)

        # 生成成对种子矩阵（上三角，对称）
        seed_matrix = {}
        for i in range(num_clients):
            for j in range(i + 1, num_clients):
                s = int(rng.integers(0, 2**32))
                seed_matrix[(i, j)] = s
                seed_matrix[(j, i)] = s

        num_batches = (total_elements + batch_size - 1) // batch_size

        masks = []
        for cid in range(num_clients):
            partner_seeds = {}
            for k in range(num_clients):
                if k == cid:
                    continue
                partner_seeds[k] = seed_matrix[(cid, k)]

            masks.append({
                'client_id': cid,
                'client_weight': float(weights[cid]),
                'partner_seeds': partner_seeds,
                'num_clients': num_clients,
                'total_elements': total_elements,
                'batch_size': batch_size,
                'num_batches': num_batches,
                'shapes': dict(shapes),
            })

        logger.info(
            f"Pairwise seeds generated | clients={num_clients} | pairs={num_clients*(num_clients-1)//2} | "
            f"total_elements={total_elements} | num_batches={num_batches}"
        )
        return masks

    # ==================================================================
    # 客户端掩码计算
    # ==================================================================
    def _compute_client_mask_flat(
        self,
        client_id: int,
        client_weight: float,
        partner_seeds: Dict[int, int],
        round_num: int,
        total_elements: int,
    ) -> np.ndarray:
        """
        计算客户端在指定轮次的全参数扁平掩码。

        b_i = (1 / w_i) * sum_{k != i} sgn(i,k) * PRNG(s_{i,k}, t, 0, total_elements)
        """
        if abs(client_weight) < 1e-12:
            raise ValueError(f"Client {client_id} weight is zero")

        mask = np.zeros(total_elements, dtype=np.float64)
        for k, seed in partner_seeds.items():
            prng_out = self._prng(seed, round_num, 0, total_elements)
            if client_id < k:
                mask += prng_out
            else:
                mask -= prng_out

        mask /= client_weight
        return mask

    def _compute_client_mask_batch(
        self,
        client_id: int,
        client_weight: float,
        partner_seeds: Dict[int, int],
        round_num: int,
        batch_idx: int,
        batch_size: int,
    ) -> np.ndarray:
        """
        计算客户端在指定轮次、指定 batch 的掩码。

        b_{i,j}^{(t)} = (1 / w_i) * sum_{k != i} sgn(i,k) * PRNG(s_{i,k}, t, j, batch_size)
        """
        if abs(client_weight) < 1e-12:
            raise ValueError(f"Client {client_id} weight is zero")

        mask = np.zeros(batch_size, dtype=np.float64)
        for k, seed in partner_seeds.items():
            prng_out = self._prng(seed, round_num, batch_idx, batch_size)
            if client_id < k:
                mask += prng_out
            else:
                mask -= prng_out

        mask /= client_weight
        return mask

    # ==================================================================
    # 掩码应用（客户端侧）
    # ==================================================================
    def apply_mask(
        self,
        model_update: Dict[str, torch.Tensor],
        mask_dict: Optional[Dict[str, Any]],
        round_num: int = 0,
    ) -> Dict[str, torch.Tensor]:
        """
        将成对掩码加到 model_update 上（post_topk 模式用）。

        Args:
            model_update: Dict[name -> Tensor]
            mask_dict:    来自 generate_masks 的单个客户端掩码字典
            round_num:    当前轮次（用于 PRNG 演化）

        Returns:
            加了掩码后的 model_update
        """
        if mask_dict is None or not self.enabled or self.apply_mode != 'post_topk':
            return model_update

        total_elements = sum(p.numel() for p in model_update.values())
        flat_mask = self._compute_client_mask_flat(
            client_id=mask_dict['client_id'],
            client_weight=mask_dict['client_weight'],
            partner_seeds=mask_dict['partner_seeds'],
            round_num=round_num,
            total_elements=total_elements,
        )

        offset = 0
        for name in sorted(model_update.keys()):
            param = model_update[name]
            numel = param.numel()
            mask_chunk = flat_mask[offset:offset + numel]
            mask_tensor = torch.from_numpy(mask_chunk).reshape(param.shape).to(
                dtype=param.dtype, device=param.device
            )
            model_update[name] = param + mask_tensor
            offset += numel

        logger.debug(
            f"Pairwise mask applied (post_topk) | cid={mask_dict['client_id']} | "
            f"round={round_num} | keys={list(model_update.keys())}"
        )
        return model_update

    def apply_mask_to_batches(
        self,
        selected_batches: List[np.ndarray],
        selected_indices: List[int],
        mask_dict: Optional[Dict[str, Any]],
        round_num: int = 0,
    ) -> List[np.ndarray]:
        """
        对 TopK 选中的 batch 注入 batch-level 成对掩码（pre_topk 模式用）。

        Args:
            selected_batches: TopK 选中的 batch 列表
            selected_indices: 选中的 batch 索引（对应全局 batch 位置）
            mask_dict:        来自 generate_masks 的单个客户端掩码字典
            round_num:        当前轮次

        Returns:
            加了掩码后的 selected_batches
        """
        if mask_dict is None or not self.enabled or self.apply_mode != 'pre_topk':
            return selected_batches

        result = []
        batch_size = mask_dict.get('batch_size', len(selected_batches[0]) if selected_batches else 4096)
        for batch_idx, global_j in enumerate(selected_indices):
            target_len = len(selected_batches[batch_idx])
            mask = self._compute_client_mask_batch(
                client_id=mask_dict['client_id'],
                client_weight=mask_dict['client_weight'],
                partner_seeds=mask_dict['partner_seeds'],
                round_num=round_num,
                batch_idx=global_j,
                batch_size=batch_size,
            )
            # 截断到目标长度（最后一块可能不足 batch_size）
            masked = selected_batches[batch_idx] + mask[:target_len]
            result.append(masked)

        logger.debug(
            f"Pairwise mask applied (pre_topk) | cid={mask_dict['client_id']} | "
            f"round={round_num} | selected_batches={len(selected_indices)} | indices={selected_indices}"
        )
        return result

    # ==================================================================
    # TEE 补偿判断
    # ==================================================================
    def needs_tee_compensation(self, sparsification_strategy_name: str) -> bool:
        """
        判断当前配置下是否需要 TEE 显式补偿掩码。
        """
        if not self.enabled:
            return False
        if self.compensation_mode == 'always':
            return True
        if self.compensation_mode == 'never':
            return False
        # auto
        return sparsification_strategy_name != 'none'

    # ==================================================================
    # TEE 补偿计算（TEE 内调用）
    # ==================================================================
    def compute_compensation(
        self,
        client_masks: List[Dict[str, Any]],
        client_weights: List[float],
        client_upload_masks: List[List[int]],
        batch_size: int,
        round_num: int = 0,
    ) -> List[np.ndarray]:
        """
        计算每个 batch 位置的掩码补偿值。

        对于参与集合 S_j 中的客户端，加权掩码和为：
            sum_{i in S_j} w_i * b_{i,j} = sum_{i in S_j} sum_{k != i} sgn(i,k) * PRNG(s_{i,k}, t, j)

        补偿值 = (上述和) / (sum_{i in S_j} w_i)

        注意：分子中的 w_i 与 b_{i,j} 中的 1/w_i 抵消，结果仅依赖 PRNG 输出。

        Args:
            client_masks:      List[mask_dict]，每个客户端的掩码描述
            client_weights:    List[float]，客户端原始权重（与分子抵消）
            client_upload_masks: List[List[int]]，每个客户端的上传 mask（0/1）
            batch_size:        int
            round_num:         当前轮次

        Returns:
            List[np.ndarray]，长度 = batch 总数
        """
        if not client_masks:
            return []

        num_batches = client_masks[0].get('num_batches', 0)
        if num_batches == 0:
            # 从 total_elements 和 batch_size 推算
            total_elements = client_masks[0].get('total_elements', batch_size)
            num_batches = (total_elements + batch_size - 1) // batch_size

        compensations = []

        # 预计算每个客户端的全参数加权掩码（与客户端侧生成逻辑完全一致）
        # w_i * b_i = sum_{k != i} sgn(i,k) * PRNG(s_{i,k}, round_num, 0, total_elements)
        total_elements = client_masks[0].get('total_elements', batch_size * num_batches)
        client_weighted_masks = []
        for i, mask_dict in enumerate(client_masks):
            weighted_mask = np.zeros(total_elements, dtype=np.float64)
            for k, seed in mask_dict['partner_seeds'].items():
                prng_out = self._prng(seed, round_num, 0, total_elements)
                if mask_dict['client_id'] < k:
                    weighted_mask += prng_out
                else:
                    weighted_mask -= prng_out
            client_weighted_masks.append(weighted_mask)

        for j in range(num_batches):
            # 收集上传了 batch j 的客户端
            active_clients = []
            for i, upload_mask in enumerate(client_upload_masks):
                if j < len(upload_mask) and upload_mask[j] == 1:
                    active_clients.append(i)

            if not active_clients:
                compensations.append(np.zeros(batch_size, dtype=np.float64))
                continue

            # 提取 batch j 的切片
            start = j * batch_size
            end = min(start + batch_size, total_elements)
            slice_len = end - start

            # 分子 = sum_{i in S_j} (w_i * b_i)[j]
            numerator = sum(
                client_weighted_masks[i][start:end] for i in active_clients
            )

            # 如果切片长度不足 batch_size，pad 到 batch_size（与 CKKS 解密结果对齐）
            if slice_len < batch_size:
                numerator = np.pad(numerator, (0, batch_size - slice_len), mode='constant')

            # 分母 = sum_{i in S_j} w_i
            denominator = sum(client_weights[i] for i in active_clients)

            if denominator > 1e-12:
                compensations.append(numerator / denominator)
            else:
                compensations.append(np.zeros(batch_size, dtype=np.float64))

        return compensations
