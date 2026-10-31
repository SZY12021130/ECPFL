"""
TEE 模拟器模块
================
提供 TEEProcessor 类，在模拟可信执行环境内执行：
  1. 解密客户端上传（TEE 持有私钥）
  2. 明文域稀疏聚合（按 batch 位置加权平均）
  3. 全局包级残差累加（补偿下行压缩损失）
  4. 二次包级 TopK 压缩（TEE 内明文域）
  5. 重新加密返回 Host

真实部署时，此类的方法应在 SGX/TrustZone enclave 内执行（C++）。
单机实验时，它只是一个普通 Python 类，但接口和逻辑与真实 TEE 等价。

与 Host 的接口边界：
  - 输入：密文（Host 无法解密）
  - 输出：密文（Host 无法解密）
  - TEE 内部：明文运算（Host 无法访问）
"""

import numpy as np
import torch
import tenseal as ts
from typing import List, Dict, Tuple, Optional, Any
import logging
import time

logger = logging.getLogger(__name__)


class ResidualStrategy:
    """
    TEE 全局残差处理策略（可插拔）

    支持四种模式：
      - none:      默认行为，残差 100% 保留（原逻辑）
      - decay:     残差衰减，未选中 batch 的历史残差按 gamma 折扣
      - clipping:  包级裁剪，限制每个 batch 更新向量的 L2 范数上限
      - both:      同时启用 decay + clipping

    配置示例（yaml）：
      tee:
        compression:
          enabled: true
          sparsity_rate: 0.5
        residual_strategy:
          mode: "both"          # none | decay | clipping | both
          decay_gamma: 0.9      # decay 模式用
          clip_tau: 0.0         # clipping 模式用；0 表示自动（滑动平均+3σ）
          clip_window: 5        # 自动阈值的历史窗口轮数
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.mode = cfg.get('mode', 'none').lower().strip()
        self.gamma = float(cfg.get('decay_gamma', 0.9))
        self.tau = float(cfg.get('clip_tau', 0.0))
        self.clip_window = int(cfg.get('clip_window', 5))

        # 自动阈值模式的状态
        self._norm_history: List[float] = []
        self._auto_tau: float = float('inf')  # 初始不设限

        if self.mode not in ('none', 'decay', 'clipping', 'both'):
            logger.warning(f"Unknown residual_strategy.mode='{self.mode}', fallback to 'none'")
            self.mode = 'none'

        if self.mode in ('decay', 'both'):
            logger.info(f"ResidualStrategy | mode={self.mode} | decay_gamma={self.gamma}")
        if self.mode in ('clipping', 'both'):
            tau_str = f"tau={self.tau:.2f}" if self.tau > 0 else "tau=auto"
            logger.info(f"ResidualStrategy | mode={self.mode} | {tau_str} | window={self.clip_window}")

    def update_auto_tau(self, compensated_batches: List[np.ndarray]):
        """根据历史 compensated 范数自动更新裁剪阈值（仅 auto 模式用）"""
        if self.mode not in ('clipping', 'both'):
            return
        if self.tau > 0:
            return  # 用户指定了固定阈值，跳过
        norms = [float(np.linalg.norm(b)) for b in compensated_batches]
        avg_norm = float(np.mean(norms)) if norms else 0.0
        self._norm_history.append(avg_norm)
        if len(self._norm_history) >= 2:
            window = self._norm_history[-self.clip_window:]
            mean_val = np.mean(window)
            std_val = np.std(window) if len(window) > 1 else 0.0
            self._auto_tau = float(mean_val + 3.0 * std_val)
            logger.debug(f"ResidualStrategy auto-tau updated: {self._auto_tau:.4f}")

    def apply(self, aggregated_delta: List[np.ndarray],
              global_residual: List[np.ndarray]) -> List[np.ndarray]:
        """
        对 aggregated_delta + global_residual 的 compensated 值应用策略。

        Returns:
            处理后的 compensated 列表（长度 = num_batches）
        """
        compensated = [agg + res for agg, res in zip(aggregated_delta, global_residual)]

        # ---- 1) 包级裁剪（在残差更新之前，对所有 batch 统一裁剪）----
        if self.mode in ('clipping', 'both'):
            tau = self.tau if self.tau > 0 else self._auto_tau
            clipped = []
            for comp in compensated:
                norm = float(np.linalg.norm(comp))
                if norm > tau:
                    clipped.append(comp * (tau / norm))
                else:
                    clipped.append(comp)
            compensated = clipped

        # ---- 2) 残差衰减（仅影响未选中 batch 的残差更新方式）----
        # decay 逻辑不在本函数中完成，因为需要知道 selected_indices。
        # 调用方在更新 global_residual 时自行处理。
        # 本函数返回 compensated 供 TopK 选择使用。

        return compensated

    def compute_new_residual(self, aggregated_delta: List[np.ndarray],
                             global_residual: List[np.ndarray],
                             selected_indices: List[int],
                             compensated: List[np.ndarray]) -> List[np.ndarray]:
        """
        根据策略计算新一轮的全局残差。

        Args:
            aggregated_delta: 本轮纯净聚合更新（已减补偿）
            global_residual:  旧的全局残差
            selected_indices: 本轮选中的 batch 索引
            compensated:      经过裁剪后的 compensated 值（供未选中时直接保留用）
        """
        new_residual = []
        for j in range(len(global_residual)):
            if j in selected_indices:
                new_residual.append(np.zeros_like(global_residual[j]))
            else:
                if self.mode in ('decay', 'both'):
                    # 衰减旧残差 + 本轮新更新
                    new_residual.append(self.gamma * global_residual[j] + aggregated_delta[j])
                else:
                    # 默认：完整保留 compensated
                    new_residual.append(compensated[j])
        return new_residual


class TEEProcessor:
    """
    TEE 处理器（模拟可信执行环境）

    核心职责：
      - 持有 CKKS 私钥，可解密客户端上传
      - 在明文域执行聚合、全局残差累加、二次压缩
      - 将压缩后的结果重新加密返回 Host
      - Host 无法访问 TEE 内存（模拟中的接口边界）
    """

    def __init__(self, ckks_manager, config: Dict[str, Any], blinding_mask=None):
        """
        Args:
            ckks_manager: CKKSManager 实例（共享上下文，含私钥）
            config: TEE 配置字典
                - sparsity_rate: TEE 内二次压缩比例（默认 0.1）
            blinding_mask: ZeroSumBlindingMask 实例（可插拔，默认 None）
        """
        self.ckks_manager = ckks_manager
        self.context = ckks_manager.context.context  # TenSEAL context
        self.batch_size = ckks_manager.batch_size

        # 压缩配置（可插拔）
        compression_cfg = config.get('compression', {})
        self.compression_enabled = compression_cfg.get('enabled', True)
        # 向后兼容：旧配置直接写 sparsity_rate 在 tee 根下
        self.sparsity_rate = compression_cfg.get(
            'sparsity_rate', config.get('sparsity_rate', 0.1)
        )

        # 可插拔：全局残差处理策略
        residual_cfg = config.get('residual_strategy', {})
        self.residual_strategy = ResidualStrategy(residual_cfg)

        # TEE 内部状态（Host 不可见）
        self.global_residual: Optional[List[np.ndarray]] = None
        self.old_global_plain_batches: Optional[List[np.ndarray]] = None

        # 零和盲化掩码（可插拔）
        self.blinding_mask = blinding_mask

        # TEE 时间统计（每轮结束后由调用者读取）
        self.tee_decrypt_time = 0.0
        self.tee_aggregate_time = 0.0
        self.tee_compensate_time = 0.0
        self.tee_compress_time = 0.0
        self.tee_reencrypt_time = 0.0
        self.tee_total_time = 0.0

        logger.info(
            f"TEEProcessor initialized | compression={self.compression_enabled} | "
            f"sparsity_rate={self.sparsity_rate} | batch_size={self.batch_size} | "
            f"blinding_mask={blinding_mask is not None and blinding_mask.enabled}"
        )

    # ==================================================================
    # 主入口：处理一轮联邦学习
    # ==================================================================
    def process_round(
        self,
        old_global_enc: Dict[str, Any],
        client_uploads: List[Dict[str, Any]],
        client_weights: List[float],
        upload_difference: bool = True,
        client_masks: Optional[List[Dict[str, Any]]] = None,
        round_num: int = 0,
    ) -> Dict[str, Any]:
        """
        TEE 处理一轮客户端上传，返回稀疏新全局密文。

        完整流程：
          1. 解密旧全局模型 → batch 列表
          2. 解密所有客户端上传 → batch 列表（None 表示未提交）
          3. 按 batch 位置明文聚合（加权平均）
          4. 加全局包级残差
          5. 包级 TopK 二次压缩
          6. 更新全局残差（选中清零，未选中保留）
          7. 合并到旧全局模型明文
          8. 只加密选中的 batch 返回

        Args:
            old_global_enc: 上一轮全局模型密文（skip_sparsification=True，所有 batch）
            client_uploads: List[客户端上传的稀疏密文]
            client_weights: 客户端权重列表（样本数占比）
            upload_difference: True=客户端上传差值，False=上传完整模型

        Returns:
            {
                'ciphertexts': [选中 batch 的密文字节串],
                'mask': [0/1, ...],
                'batch_size': int,
                'total_elements': int,
                'shapes': Dict,
                'offsets': Dict,
            }
        """
        # Step 1: 解密旧全局模型 → batch 列表
        old_batches = self._decrypt_global_to_batches(old_global_enc)
        num_batches = len(old_batches)

        # Step 2: 解密所有客户端上传 → batch 列表（None = 未提交）
        client_batch_lists = []
        for upload in client_uploads:
            batches = self._decrypt_upload_to_batches(upload)
            client_batch_lists.append(batches)

        # Step 3: 按 batch 位置明文聚合
        aggregated_delta = self._aggregate_plain_sparse(
            client_batch_lists=client_batch_lists,
            client_weights=client_weights,
            num_batches=num_batches,
            old_batches=old_batches,
            upload_difference=upload_difference,
            client_masks=client_masks,
            round_num=round_num,
        )

        if self.compression_enabled:
            # ---- 压缩模式：全局残差 + TopK 二次压缩 ----
            # Step 4: 初始化全局残差（第一轮）
            if self.global_residual is None:
                self.global_residual = [
                    np.zeros(self.batch_size, dtype=np.float64)
                    for _ in range(num_batches)
                ]

            # Step 5: 加全局残差
            compensated = [
                agg + res for agg, res in zip(aggregated_delta, self.global_residual)
            ]

            # Step 6: 包级 TopK 二次压缩
            selected_indices, compressed = self._topk_batch_select(
                compensated, self.sparsity_rate
            )
            mask = [1 if j in selected_indices else 0 for j in range(num_batches)]

            # Step 7: 更新全局残差
            self.global_residual = [
                np.zeros(self.batch_size, dtype=np.float64)
                if j in selected_indices
                else comp
                for j, comp in enumerate(compensated)
            ]

            # Step 8: 合并到旧全局模型明文
            new_global_batches = []
            for j in range(num_batches):
                if j in selected_indices:
                    idx = selected_indices.index(j)
                    new_global_batches.append(old_batches[j] + compressed[idx])
                else:
                    new_global_batches.append(old_batches[j])
            self.old_global_plain_batches = new_global_batches

            # Step 9: 只加密选中的 batch
            selected_plain = [new_global_batches[j] for j in selected_indices]
            encrypted_selected = []
            for plain_batch in selected_plain:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())

            logger.info(
                f"TEE round | compression=ON | selected={len(selected_indices)}/{num_batches} "
                f"({len(selected_indices) / max(1, num_batches):.1%}) | "
                f"residual_norm={sum(np.linalg.norm(r) for r in self.global_residual):.4f}"
            )
        else:
            # ---- 无压缩模式：全量回传，无全局残差 ----
            selected_indices = list(range(num_batches))
            mask = [1] * num_batches

            # 直接聚合 delta 加到旧全局
            new_global_batches = [
                old_batches[j] + aggregated_delta[j]
                for j in range(num_batches)
            ]
            self.old_global_plain_batches = new_global_batches

            # 加密所有 batch
            encrypted_selected = []
            for plain_batch in new_global_batches:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())

            logger.info(
                f"TEE round | compression=OFF | selected={num_batches}/{num_batches} "
                f"(100.0%) | full aggregation, no residual"
            )

        return {
            'ciphertexts': encrypted_selected,
            'mask': mask,
            'batch_size': self.batch_size,
            'total_elements': old_global_enc['total_elements'],
            'shapes': old_global_enc['shapes'],
            'offsets': old_global_enc['offsets'],
        }

    # ==================================================================
    # 主入口（Host 预聚合版）：处理 Host 同态聚合后的密文
    # ==================================================================
    def process_aggregated_round(
        self,
        old_global_enc: Dict[str, Any],
        aggregated_upload: Dict[str, Any],
        agg_weights: List[float],
        client_weights: List[float],
        upload_difference: bool = True,
        client_masks: Optional[List[Dict[str, Any]]] = None,
        client_upload_masks: Optional[List[List[int]]] = None,
        round_num: int = 0,
    ) -> Dict[str, Any]:
        """
        TEE 处理 Host 同态预聚合后的密文，返回稀疏新全局密文。

        与 process_round 的区别：
          - Host 已执行同态预聚合：agg_ct_j = Σ_{i∈S_j} w_i · ct_{i,j}
          - TEE 只需解密 J 个聚合密文（而非 n·J 个客户端密文）
          - TEE 内对每个 batch 做一次标量除法（除以 W_j）即可得加权平均

        Args:
            old_global_enc: 上一轮全局模型密文
            aggregated_upload: Host 预聚合后的稀疏密文包（含 '__aggregated__' 标记）
            agg_weights: 每个 batch 的聚合权重 W_j = Σ_{i∈S_j} w_i
            client_weights: 原始客户端权重列表（用于掩码补偿计算）
            upload_difference: True=上传差值
            client_masks: 盲化掩码字典列表（TEE 补偿用）

        Returns:
            同 process_round
        """
        round_start = time.time()
        self._reset_tee_timers()

        # ---- Step 1: 解密旧全局模型 ----
        t0 = time.time()
        old_batches = self._decrypt_global_to_batches(old_global_enc)
        num_batches = len(old_batches)
        self.tee_decrypt_time += time.time() - t0

        # ---- Step 2: 解密聚合密文（仅 J 个）----
        t0 = time.time()
        aggregated_batches = self._decrypt_aggregated_upload(
            aggregated_upload, agg_weights, num_batches
        )
        self.tee_decrypt_time += time.time() - t0

        # ---- Step 3: 掩码补偿 ----
        t0 = time.time()
        need_compensation = (
            self.blinding_mask is not None
            and self.blinding_mask.enabled
            and client_masks is not None
            and len(client_masks) > 0
        )
        compensations = None
        if need_compensation:
            if client_upload_masks is not None:
                compensations = self.blinding_mask.compute_compensation(
                    client_masks=client_masks,
                    client_weights=client_weights,
                    client_upload_masks=client_upload_masks,
                    batch_size=self.batch_size,
                    round_num=round_num,
                )
                logger.info(
                    f"TEE aggregated blinding mask compensation | clients={len(client_masks)} | "
                    f"compensation_norm={sum(np.linalg.norm(c) for c in compensations):.4f}"
                )
            else:
                logger.warning(
                    "TEE aggregated mode: mask compensation requires client_upload_masks. "
                    "Compensation skipped."
                )
        self.tee_compensate_time += time.time() - t0

        # ---- Step 4-9: 残差、压缩、更新、重加密（与 process_round 共享）----
        result = self._tee_post_process(
            old_batches=old_batches,
            aggregated_delta=aggregated_batches,
            num_batches=num_batches,
            upload_difference=upload_difference,
            compensations=compensations,
        )
        # 填充 shapes/offsets/total_elements（来自旧全局密文）
        result['shapes'] = old_global_enc.get('shapes', {})
        result['offsets'] = old_global_enc.get('offsets', {})
        result['total_elements'] = old_global_enc.get('total_elements', self.batch_size * num_batches)

        self.tee_total_time = time.time() - round_start
        logger.info(
            f"TEE aggregated round | total={self.tee_total_time:.4f}s | "
            f"decrypt={self.tee_decrypt_time:.4f}s | "
            f"aggregate={self.tee_aggregate_time:.4f}s | "
            f"compensate={self.tee_compensate_time:.4f}s | "
            f"compress={self.tee_compress_time:.4f}s | "
            f"reencrypt={self.tee_reencrypt_time:.4f}s"
        )
        return result

    def _reset_tee_timers(self):
        """重置本轮 TEE 时间统计"""
        self.tee_decrypt_time = 0.0
        self.tee_aggregate_time = 0.0
        self.tee_compensate_time = 0.0
        self.tee_compress_time = 0.0
        self.tee_reencrypt_time = 0.0
        self.tee_total_time = 0.0

    def _tee_post_process(
        self,
        old_batches: List[np.ndarray],
        aggregated_delta: List[np.ndarray],
        num_batches: int,
        upload_difference: bool,
        compensations: Optional[List[np.ndarray]] = None,
    ) -> Dict[str, Any]:
        """
        TEE 公共后处理流程：残差累加 → TopK 压缩 → 更新全局 → 重加密。
        被 process_round 和 process_aggregated_round 共享。
        """
        # 应用掩码补偿
        if compensations is not None:
            aggregated_delta = [
                agg - comp for agg, comp in zip(aggregated_delta, compensations)
            ]

        if self.compression_enabled:
            # 加全局残差
            if self.global_residual is None:
                self.global_residual = [
                    np.zeros(self.batch_size, dtype=np.float64)
                    for _ in range(num_batches)
                ]

            # ---- 可插拔：应用残差处理策略（裁剪等）----
            compensated = self.residual_strategy.apply(
                aggregated_delta, self.global_residual
            )
            # 更新自动裁剪阈值的历史统计
            self.residual_strategy.update_auto_tau(compensated)

            # TopK 二次压缩
            t0 = time.time()
            selected_indices, compressed = self._topk_batch_select(
                compensated, self.sparsity_rate
            )
            self.tee_compress_time += time.time() - t0
            mask = [1 if j in selected_indices else 0 for j in range(num_batches)]

            # 更新全局残差（根据策略：默认保留 / 衰减 / 裁剪后保留）
            self.global_residual = self.residual_strategy.compute_new_residual(
                aggregated_delta=aggregated_delta,
                global_residual=self.global_residual,
                selected_indices=selected_indices,
                compensated=compensated,
            )

            # 合并到旧全局
            new_global_batches = []
            for j in range(num_batches):
                if j in selected_indices:
                    idx = selected_indices.index(j)
                    new_global_batches.append(old_batches[j] + compressed[idx])
                else:
                    new_global_batches.append(old_batches[j])
            self.old_global_plain_batches = new_global_batches

            # 重加密选中 batch
            t0 = time.time()
            selected_plain = [new_global_batches[j] for j in selected_indices]
            encrypted_selected = []
            for plain_batch in selected_plain:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())
            self.tee_reencrypt_time += time.time() - t0

            logger.info(
                f"TEE post-process | compression=ON | selected={len(selected_indices)}/{num_batches} "
                f"({len(selected_indices) / max(1, num_batches):.1%}) | "
                f"residual_norm={sum(np.linalg.norm(r) for r in self.global_residual):.4f}"
            )
        else:
            selected_indices = list(range(num_batches))
            mask = [1] * num_batches

            # DEBUG
            for j in range(num_batches):
                d_norm = float(np.linalg.norm(aggregated_delta[j]))
                o_norm = float(np.linalg.norm(old_batches[j]))
                if d_norm > 1000 or o_norm > 1000:
                    print("[DEBUG TEE] batch=%d old_norm=%.2f delta_norm=%.2f" % (j, o_norm, d_norm))
            # END DEBUG

            new_global_batches = [
                old_batches[j] + aggregated_delta[j]
                for j in range(num_batches)
            ]
            self.old_global_plain_batches = new_global_batches

            t0 = time.time()
            encrypted_selected = []
            for plain_batch in new_global_batches:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())
            self.tee_reencrypt_time += time.time() - t0

            # DEBUG
            ng_norms = [float(np.linalg.norm(b)) for b in new_global_batches]
            print("[DEBUG TEE] compression=OFF new_global_norms max=%.2f min=%.2f" % (max(ng_norms), min(ng_norms)))
            # END DEBUG

            logger.info(
                f"TEE post-process | compression=OFF | selected={num_batches}/{num_batches} "
                f"(100.0%) | full aggregation, no residual"
            )

        return {
            'ciphertexts': encrypted_selected,
            'mask': mask,
            'batch_size': self.batch_size,
            'total_elements': self.batch_size * num_batches,
            'shapes': {},
            'offsets': {},
        }

    def _decrypt_aggregated_upload(
        self,
        aggregated_upload: Dict[str, Any],
        agg_weights: List[float],
        num_batches: int,
    ) -> List[np.ndarray]:
        """
        解密 Host 预聚合后的密文，并除以聚合权重得到加权平均。

        数学：
          Dec(agg_ct_j) = Σ_{i∈S_j} w_i · (g_{i,j} + b_{i,j})
          δ_j_raw = Dec(agg_ct_j) / W_j

        Returns:
            List[np.ndarray]，长度 num_batches，每个元素 shape=(batch_size,)
        """
        mask = aggregated_upload['mask']
        ciphertexts = aggregated_upload['ciphertexts']
        ctx = self.ckks_manager.context.context

        aggregated_batches = []
        t0 = time.time()

        for j in range(num_batches):
            if mask[j] == 1 and ciphertexts[j] is not None:
                ct = ts.CKKSVector.load(ctx, ciphertexts[j])
                decrypted = ct.decrypt()
                W_j = agg_weights[j]
                dec_norm = float(np.linalg.norm(np.array(decrypted, dtype=np.float64)))
                if j == 0 or dec_norm > 1e6:
                    print("[DEBUG DECRYPT] batch=%d decrypted_norm=%.2e W_j=%.2f" % (j, dec_norm, W_j))
                if W_j > 1e-12:
                    avg_batch = np.array(decrypted, dtype=np.float64) / W_j
                else:
                    avg_batch = np.zeros(self.batch_size, dtype=np.float64)
                aggregated_batches.append(avg_batch)
            else:
                aggregated_batches.append(np.zeros(self.batch_size, dtype=np.float64))

        self.tee_aggregate_time += time.time() - t0
        return aggregated_batches

    # ==================================================================
    # 内部辅助方法
    # ==================================================================
    def _decrypt_global_to_batches(
        self, encrypted_global: Dict[str, Any]
    ) -> List[np.ndarray]:
        """
        解密完整全局模型密文 → batch 列表

        全局模型是 skip_sparsification=True 的，所有 batch 都加密。
        """
        shapes = encrypted_global['shapes']
        params = self.ckks_manager.decrypt_model_update(encrypted_global, shapes)

        # Flatten 所有参数为一个长数组
        all_values = []
        for name in sorted(params.keys()):
            all_values.extend(params[name].detach().cpu().numpy().flatten().tolist())

        # 切分为 batches
        batches = []
        for i in range(0, len(all_values), self.batch_size):
            chunk = np.array(all_values[i : i + self.batch_size], dtype=np.float64)
            if len(chunk) < self.batch_size:
                chunk = np.pad(
                    chunk, (0, self.batch_size - len(chunk)), mode='constant'
                )
            batches.append(chunk)

        return batches

    def _decrypt_upload_to_batches(
        self, upload: Dict[str, Any]
    ) -> List[Optional[np.ndarray]]:
        """
        解密客户端稀疏上传 → batch 列表

        Returns:
            List[Optional[np.ndarray]]: 长度 = batch_num
                - 选中的 batch → np.ndarray
                - 未选中的 batch → None
        """
        shapes = upload['shapes']
        params = self.ckks_manager.decrypt_model_update(upload, shapes)

        # Flatten 为长数组（未选中 batch 已被 decrypt_model_update 补零）
        all_values = []
        for name in sorted(params.keys()):
            all_values.extend(params[name].detach().cpu().numpy().flatten().tolist())

        # 切分为 batches，根据 mask 标记是否提交
        mask = upload['mask']
        batches = []
        for j in range(len(mask)):
            start = j * self.batch_size
            end = start + self.batch_size
            chunk = np.array(all_values[start:end], dtype=np.float64)
            if len(chunk) < self.batch_size:
                chunk = np.pad(
                    chunk, (0, self.batch_size - len(chunk)), mode='constant'
                )

            if mask[j] == 1:
                batches.append(chunk)
            else:
                batches.append(None)

        return batches

    def _aggregate_plain_sparse(
        self,
        client_batch_lists: List[List[Optional[np.ndarray]]],
        client_weights: List[float],
        num_batches: int,
        old_batches: List[np.ndarray],
        upload_difference: bool,
        client_masks: Optional[List[Dict[str, Any]]] = None,
        round_num: int = 0,
    ) -> List[np.ndarray]:
        """
        明文域稀疏聚合（按 batch 位置加权平均）

        无论客户端上传的是差值还是完整模型，TEE 内统一输出 delta（变化量）。

        Args:
            client_batch_lists: 每个客户端的 batch 列表（None = 未提交）
            client_weights: 客户端权重
            num_batches: batch 总数
            old_batches: 旧全局模型的 batch 列表
            upload_difference: True=上传差值, False=上传完整模型
            client_masks: 每个客户端的盲化掩码字典（含 'batches'），用于 TEE 显式补偿

        Returns:
            每个 batch 位置的聚合 delta（加权平均，已补偿掩码）
        """
        aggregated = []

        # ---- 可插拔：零和盲化掩码 TEE 补偿 ----
        # 判断是否需要补偿（稀疏化场景下子集权重零和不自动成立）
        need_compensation = (
            self.blinding_mask is not None
            and self.blinding_mask.enabled
            and client_masks is not None
            and len(client_masks) > 0
        )
        if need_compensation:
            # 从 client_batch_lists 推断每个客户端的上传 mask（None=未提交）
            client_upload_masks = []
            for i, batches in enumerate(client_batch_lists):
                upload_mask = [1 if batches[j] is not None else 0 for j in range(num_batches)]
                client_upload_masks.append(upload_mask)
            compensations = self.blinding_mask.compute_compensation(
                client_masks=client_masks,
                client_weights=client_weights,
                client_upload_masks=client_upload_masks,
                batch_size=self.batch_size,
                round_num=round_num,
            )
            logger.info(
                f"TEE blinding mask compensation applied | clients={len(client_masks)} | "
                f"compensation_norm={sum(np.linalg.norm(c) for c in compensations):.4f}"
            )
        else:
            compensations = None

        for j in range(num_batches):
            # 收集提交了该 batch 的所有客户端
            vals = []
            weights_sub = []
            for i, batches in enumerate(client_batch_lists):
                if batches[j] is not None:
                    vals.append(batches[j])
                    weights_sub.append(client_weights[i])

            if len(vals) == 0:
                # 没有任何客户端提交该 batch → delta = 0
                aggregated.append(np.zeros(self.batch_size, dtype=np.float64))
                continue

            # 加权平均
            total_w = sum(weights_sub)
            norm_ws = [w / total_w for w in weights_sub]

            agg_batch = np.zeros(self.batch_size, dtype=np.float64)
            for val, nw in zip(vals, norm_ws):
                agg_batch += val * nw

            if not upload_difference:
                # 客户端上传的是完整模型，需要减去旧全局得到 delta
                agg_batch = agg_batch - old_batches[j]

            # 减去盲化掩码补偿（使稀疏化场景下零和约束仍成立）
            if compensations is not None:
                agg_batch = agg_batch - compensations[j]

            aggregated.append(agg_batch)

        return aggregated

    def _topk_batch_select(
        self, batches: List[np.ndarray], sparsity_rate: float
    ) -> Tuple[List[int], List[np.ndarray]]:
        """
        包级 TopK 选择

        对每个 batch 计算平均绝对值，保留 avg(|x|) 最大的 top-k%。

        Returns:
            (selected_indices, selected_batches)
        """
        batch_num = len(batches)
        if batch_num == 0:
            return [], []

        # 计算每个 batch 的平均绝对值
        avg_abs = [float(np.mean(np.abs(batch))) for batch in batches]

        # 计算 TopK 数量（至少选 1 个）
        topk_num = max(1, int(np.ceil(batch_num * sparsity_rate)))

        # 选择 avg(|x|) 最大的 topk_num 个 batch
        sorted_indices = np.argsort(avg_abs)[::-1][:topk_num]
        selected_indices = sorted(sorted_indices.tolist())

        selected_batches = [batches[i] for i in selected_indices]

        return selected_indices, selected_batches
