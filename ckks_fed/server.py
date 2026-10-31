"""
联邦学习聚合服务器模块
实现模型聚合、全局模型更新和分发功能
扩展支持：多种鲁棒聚合规则与异常检测防御
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import time
import logging
import copy
from collections import deque
import tenseal as ts
from ckks_fed.defenses import aggregation_rules, anomaly_detection
from ckks_fed.log_utils import (
    LogTag, tag_info, tag_warn, fmt_size, fmt_time,
    log_aggregation_result, log_evaluation_result,
)
from ckks_fed.crypto import merge_sparse_encrypted_updates
from ckks_fed.global_mask_vote import GlobalMaskVote
from ckks_fed.adaptive_vote import AdaptiveGlobalMaskVote
from ckks_fed.tee_simulator import TEEProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AggregationServer:
    """联邦学习聚合服务器：负责收集客户端更新、执行聚合和分发全局模型"""
    
    def __init__(self, model: nn.Module, config: Dict, device: str = "cpu", ckks_manager=None, blinding_mask=None):
        self.model = model.to(device)
        self.config = config
        self.device = device
        self.ckks_manager = ckks_manager
        
        self.aggregation_time = 0.0
        self.communication_cost = 0.0
        self.upload_cost = 0.0
        self.download_cost = 0.0
        self.round_num = 0
        
        # 加密全局状态：服务器在密文域维护全局模型，不下发明文
        self.encrypted_global_state = None
        
        # TEE 可插拔配置
        tee_cfg = config.get('tee', {})
        self.tee_enabled = tee_cfg.get('enabled', False)
        self.tee_processor = None
        if self.tee_enabled:
            if ckks_manager is None:
                raise ValueError("TEE 开启时必须有 ckks_manager")
            self.tee_processor = TEEProcessor(ckks_manager, tee_cfg, blinding_mask=blinding_mask)
            compression_cfg = tee_cfg.get('compression', {})
            comp_enabled = compression_cfg.get('enabled', True)
            comp_rate = compression_cfg.get('sparsity_rate', tee_cfg.get('sparsity_rate', 0.1))
            tag_info(LogTag.SERVER,
                     f"TEE enabled | compression={comp_enabled} | sparsity_rate={comp_rate}")
        else:
            tag_info(LogTag.SERVER, "TEE disabled | using standard aggregation path")
        
        # ---- 全局掩码投票（ESAFL 多密钥适配）----
        gmv_cfg = config.get('global_mask_vote', {})
        adaptive_cfg = config.get('adaptive_vote', {}) or {}
        total_rounds = config.get('system', {}).get('num_rounds', 50)

        if adaptive_cfg.get('enabled', False):
            # 启用自适应投票：将 global_mask_vote 配置与 adaptive 配置合并
            merged_cfg = dict(gmv_cfg)
            merged_cfg['adaptive_strategy'] = adaptive_cfg.get('strategy', 'none')
            merged_cfg['adaptive_config'] = adaptive_cfg.get('config', {})
            self.global_mask_vote = AdaptiveGlobalMaskVote(merged_cfg, total_rounds=total_rounds)
        else:
            self.global_mask_vote = GlobalMaskVote(
                mode=gmv_cfg.get('mode', 'none'),
                threshold_pct=gmv_cfg.get('threshold_pct', 0.2),
                topk_k=gmv_cfg.get('topk_count_k', 5),
                topk_pct=gmv_cfg.get('topk_pct', None),
            )
        self.current_global_mask = None  # 当前轮次的全局掩码
        self.current_global_maser_indices = None  # 当前轮次 MASER 全局选中索引
        
        self.history = {
            'train_loss': [], 'train_acc': [], 'test_loss': [], 'test_acc': [],
            'aggregation_time': [], 'communication_cost': [],
            'upload_cost': [], 'download_cost': []
        }
        
        # 防御配置
        defense_cfg = config.get('defense', {})
        self.aggregation_rule = defense_cfg.get('aggregation_rule', 'fedavg')
        self.anomaly_filter = defense_cfg.get('anomaly_filter', None)
        self.defense_params = defense_cfg.get('params', {})
        
        tag_info(LogTag.SERVER, f"Initialized  |  rule={self.aggregation_rule}  |  filter={self.anomaly_filter}")
    
    def get_global_params(self) -> Dict[str, torch.Tensor]:
        params = {name: param.data.clone() for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                params[name] = buf.clone()
        return params
    
    def set_global_params(self, params: Dict[str, torch.Tensor]):
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if name in params:
                    param.copy_(params[name])
            for name, buf in self.model.named_buffers():
                if name in params:
                    buf.copy_(params[name])
    
    def compute_download_cost(self) -> int:
        global_params = self.get_global_params()
        return sum(p.numel() * 4 for p in global_params.values())
    
    def set_encrypted_global_state(self, encrypted_state):
        self.encrypted_global_state = encrypted_state
    
    def get_encrypted_global_state(self):
        return self.encrypted_global_state
    
    def init_encrypted_global_state(self, ckks_manager):
        """初始化加密全局状态：用公钥加密当前明文模型"""
        self.ckks_manager = ckks_manager
        self.encrypted_global_state = ckks_manager.encrypt_model_update(self.get_global_params(), skip_sparsification=True)
        tag_info(LogTag.SERVER, "加密全局状态已初始化（服务器不下发明文模型）")
    
    def get_encrypted_global_params(self):
        """返回加密全局模型（下发给客户端的密文）"""
        return self.encrypted_global_state
    
    def _is_encrypted_update(self, update) -> bool:
        """检测更新是否为密文格式（FedPHE 对齐：统一 __sparse__）"""
        if not isinstance(update, dict) or len(update) == 0:
            return False
        return update.get('__sparse__', False)
    
    def _update_plain_global_model(self, aggregated_update: Dict[str, torch.Tensor], learning_rate: float):
        """明文更新全局模型（兼容旧代码）"""
        upload_difference = self.config['system'].get('upload_difference', True)
        
        # PTopk 服务器累加器（明文路径）
        # 只在启用包级稀疏化时才生效，否则跳过
        from ckks_fed.sparsification import NoSparsification
        ptopk = self.ckks_manager.ptopk if self.ckks_manager else None
        sparsification_enabled = (
            self.ckks_manager is not None and
            not isinstance(self.ckks_manager.sparsification_strategy, NoSparsification)
        )
        actual_lr = learning_rate
        if (ptopk is not None and ptopk.enabled and ptopk.server_mode != 'none'
                and sparsification_enabled):
            aggregated_update = ptopk.server_update_plain(aggregated_update, learning_rate)
            actual_lr = 1.0  # learning_rate 已在累加器内部应用
            # delayed 模式可能返回零更新，此时跳过模型参数更新
            has_nonzero = any(torch.any(v != 0).item() for v in aggregated_update.values())
            if not has_nonzero:
                self.round_num += 1
                tag_info(LogTag.SERVER, f"全局模型已更新(明文|PTopk {ptopk.server_mode} 跳过)  |  当前轮次={self.round_num}")
                return
        
        with torch.no_grad():
            if upload_difference:
                for name, param in self.model.named_parameters():
                    if name in aggregated_update:
                        update_tensor = aggregated_update[name].to(param.device)
                        param.add_(update_tensor, alpha=actual_lr)
                for name, buf in self.model.named_buffers():
                    if name in aggregated_update:
                        update_tensor = aggregated_update[name].to(buf.device)
                        buf.add_(update_tensor, alpha=actual_lr)
                mode_str = "差值累加"
            else:
                for name, param in self.model.named_parameters():
                    if name in aggregated_update:
                        update_tensor = aggregated_update[name].to(param.device)
                        param.copy_(update_tensor)
                for name, buf in self.model.named_buffers():
                    if name in aggregated_update:
                        update_tensor = aggregated_update[name].to(buf.device)
                        buf.copy_(update_tensor)
                mode_str = "完整权重替换"
        self.round_num += 1
        tag_info(LogTag.SERVER, f"全局模型已更新(明文)  |  当前轮次={self.round_num}  |  上传模式={mode_str}")
    
    def _update_encrypted_global_state(self, encrypted_update, learning_rate: float):
        """
        更新加密全局状态（FedPHE 对齐：统一 __sparse__ 格式，batch = N/2 slot = 一个密文）。
        upload_difference=true 时：同态累加 W += Δ * lr（按 batch 逐个加法）
        upload_difference=false 时：直接替换 W = new_W
        """
        if self.encrypted_global_state is None:
            raise RuntimeError("encrypted_global_state 未初始化，请先调用 init_encrypted_global_state()")
        if not encrypted_update.get('__sparse__'):
            raise ValueError("加密更新必须使用 __sparse__ 格式（FedPHE 对齐）")

        # ================================================================
        # 打包策略明文更新路径：当 packing_metadata 包含量化信息时，
        # 整数编码（CRTStack/TwoTier/ESAFL）对同态加法/乘法的噪声极度敏感，
        # 同态累加会导致编码完全失效。因此切换到明文更新后重新加密。
        # ================================================================
        packing_metadata = encrypted_update.get('packing_metadata')
        if packing_metadata is not None and (
            packing_metadata.get('quant_bits') is not None
            or packing_metadata.get('layers') is not None
        ):
            original_shapes = {name: param.shape for name, param in self.model.named_parameters()}
            for name, buf in self.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    original_shapes[name] = buf.shape
            # 解密当前全局状态和本次更新
            global_plain = self.ckks_manager.decrypt_model_update(self.encrypted_global_state, original_shapes)
            update_plain = self.ckks_manager.decrypt_model_update(encrypted_update, original_shapes)
            
            # === NaN/Inf debug checks (before aggregation) ===
            for name, tensor in global_plain.items():
                if torch.isnan(tensor).any():
                    nan_count = torch.isnan(tensor).sum().item()
                    logger.warning(f"[AGG-DEBUG] global_plain {name} has {nan_count} NaN after decrypt!")
                if torch.isinf(tensor).any():
                    inf_count = torch.isinf(tensor).sum().item()
                    logger.warning(f"[AGG-DEBUG] global_plain {name} has {inf_count} Inf after decrypt!")
            for name, tensor in update_plain.items():
                if torch.isnan(tensor).any():
                    nan_count = torch.isnan(tensor).sum().item()
                    logger.warning(f"[AGG-DEBUG] update_plain {name} has {nan_count} NaN after decrypt!")
                if torch.isinf(tensor).any():
                    inf_count = torch.isinf(tensor).sum().item()
                    logger.warning(f"[AGG-DEBUG] update_plain {name} has {inf_count} Inf after decrypt!")
                if 'running_var' in name and (tensor < 0).any():
                    neg_count = (tensor < 0).sum().item()
                    logger.warning(f"[AGG-DEBUG] update_plain {name} has {neg_count} negative values!")
            # =================================================
            
            # 明文累加
            for name in global_plain:
                if learning_rate != 1.0:
                    global_plain[name] += update_plain[name] * learning_rate
                else:
                    global_plain[name] += update_plain[name]
            
            # === NaN/Inf debug check (after aggregation) ===
            for name, tensor in global_plain.items():
                if torch.isnan(tensor).any():
                    nan_count = torch.isnan(tensor).sum().item()
                    logger.error(f"[AGG-DEBUG] aggregated global_plain {name} has {nan_count} NaN after aggregation!")
                if torch.isinf(tensor).any():
                    inf_count = torch.isinf(tensor).sum().item()
                    logger.error(f"[AGG-DEBUG] aggregated global_plain {name} has {inf_count} Inf after aggregation!")
            # ================================================
            # 重新加密
            self.encrypted_global_state = self.ckks_manager.encrypt_model_update(global_plain, skip_sparsification=True)
            self._sync_model_from_encrypted_state()
            tag_info(LogTag.SERVER, f"全局模型已更新(明文累加重加密)  |  当前轮次={self.round_num}  |  策略=packing_plain")
            return

        upload_difference = self.config['system'].get('upload_difference', True)
        agg_mask = encrypted_update['mask']
        agg_cts = encrypted_update['ciphertexts']
        global_cts = self.encrypted_global_state['ciphertexts']

        if upload_difference:
            # 按 batch 逐个同态累加：只对 mask=1 的 batch 执行加法
            ct_idx = 0
            for batch_idx, is_selected in enumerate(agg_mask):
                if is_selected:
                    ct = agg_cts[ct_idx]
                    if learning_rate != 1.0:
                        ct = self.ckks_manager.evaluator.multiply_scalar(ct, learning_rate)
                    global_cts[batch_idx] = self.ckks_manager.evaluator.add(
                        global_cts[batch_idx], ct
                    )
                    ct_idx += 1
            mode_str = "差值累加"
        else:
            # 客户端上传完整权重：直接替换对应 batch
            ct_idx = 0
            for batch_idx, is_selected in enumerate(agg_mask):
                if is_selected:
                    global_cts[batch_idx] = agg_cts[ct_idx]
                    ct_idx += 1
            mode_str = "完整权重替换"

        self._sync_model_from_encrypted_state()
        tag_info(LogTag.SERVER, f"全局模型已更新(密文累加)  |  当前轮次={self.round_num}  |  模式={mode_str}")
    
    def _sync_model_from_encrypted_state(self):
        """将加密全局状态解密到明文模型（用于评估）"""
        if self.encrypted_global_state is None or self.ckks_manager is None:
            return
        original_shapes = {name: param.shape for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                original_shapes[name] = buf.shape
        decrypted = self.ckks_manager.decrypt_model_update(self.encrypted_global_state, original_shapes)
        
        # ==== 调试与修复：检查解密后参数是否有 NaN 或 BN running_var 负值 ====
        import torch
        has_nan = False
        neg_var_names = []
        for name, tensor in decrypted.items():
            if torch.isnan(tensor).any():
                has_nan = True
                nan_count = torch.isnan(tensor).sum().item()
                logger.warning(f"[SYNC-DEBUG] {name} 包含 {nan_count} 个 NaN!")
            if 'running_var' in name and (tensor < 0).any():
                neg_count = (tensor < 0).sum().item()
                min_val = tensor.min().item()
                neg_var_names.append(f"{name}({neg_count}个负值,min={min_val:.4f})")
        if has_nan:
            logger.error("[SYNC-DEBUG] ⚠️ 解密后的全局模型包含 NaN，评估将出错!")
        if neg_var_names:
            logger.warning(f"[SYNC-DEBUG] ⚠️ BN running_var 负值: {', '.join(neg_var_names)}")
        
        # 修复：对 BN running_var 做兜底保护，防止 CKKS 精度损失导致负值
        for name, tensor in decrypted.items():
            if 'running_var' in name:
                if (tensor < 0).any() or torch.isnan(tensor).any():
                    original_min = tensor.min().item()
                    decrypted[name] = tensor.clamp(min=1e-5)
                    logger.info(
                        f"[SYNC-FIX] {name} clamped: min={original_min:.6f} → {decrypted[name].min().item():.6f}"
                    )
        # ================================================================
        
        self.set_global_params(decrypted)
    
    def _apply_defense(self, client_updates: List[Dict[str, torch.Tensor]],
                       client_weights: List[float]) -> Tuple[Dict[str, torch.Tensor], List[int]]:
        """应用防御机制：先异常过滤，再用鲁棒聚合规则聚合"""
        kept_indices = list(range(len(client_updates)))
        filtered_updates = client_updates
        filtered_weights = client_weights
        
        # 第一步：异常检测过滤
        if self.anomaly_filter is not None and len(client_updates) > 1:
            if self.anomaly_filter == 'norm_clip':
                filtered_updates, filtered_weights, kept_indices = anomaly_detection.norm_clip_updates(
                    client_updates, client_weights,
                    max_norm_ratio=self.defense_params.get('max_norm_ratio', 3.0)
                )
            elif self.anomaly_filter == 'cosine_similarity':
                filtered_updates, filtered_weights, kept_indices = anomaly_detection.cosine_similarity_filter(
                    client_updates, client_weights,
                    threshold=self.defense_params.get('cos_threshold', 0.5)
                )
            elif self.anomaly_filter == 'mad':
                filtered_updates, filtered_weights, kept_indices = anomaly_detection.median_absolute_deviation_filter(
                    client_updates, client_weights,
                    threshold=self.defense_params.get('mad_threshold', 3.0)
                )
            elif self.anomaly_filter == 'multi_criteria':
                filtered_updates, filtered_weights, kept_indices = anomaly_detection.multi_criteria_filter(
                    client_updates, client_weights,
                    norm_ratio=self.defense_params.get('norm_ratio', 5.0),
                    cos_threshold=self.defense_params.get('cos_threshold', -0.1)
                )
            tag_info(LogTag.SERVER,
                     f"Anomaly filter [{self.anomaly_filter}]  |  "
                     f"original={len(client_updates)}  kept={len(filtered_updates)}  "
                     f"dropped={len(client_updates) - len(filtered_updates)}")
        
        # 第二步：鲁棒聚合
        if self.aggregation_rule == 'fedavg':
            aggregated = aggregation_rules.fedavg_aggregate(filtered_updates, filtered_weights)
        elif self.aggregation_rule == 'median':
            aggregated = aggregation_rules.median_aggregate(filtered_updates)
        elif self.aggregation_rule == 'trimmed_mean':
            aggregated = aggregation_rules.trimmed_mean_aggregate(
                filtered_updates,
                trim_ratio=self.defense_params.get('trim_ratio', 0.1)
            )
        elif self.aggregation_rule == 'krum':
            aggregated = aggregation_rules.krum_aggregate(
                filtered_updates,
                f=self.defense_params.get('f', max(0, len(filtered_updates) // 2 - 1))
            )
        elif self.aggregation_rule == 'multi_krum':
            aggregated = aggregation_rules.multi_krum_aggregate(
                filtered_updates,
                f=self.defense_params.get('f', max(0, len(filtered_updates) // 2 - 1)),
                m=self.defense_params.get('m', None)
            )
        elif self.aggregation_rule == 'geometric_median':
            aggregated = aggregation_rules.geometric_median_aggregate(
                filtered_updates,
                max_iter=self.defense_params.get('gm_max_iter', 10)
            )
        else:
            logger.warning(f"未知聚合规则 {self.aggregation_rule}，回退到 FedAvg")
            aggregated = aggregation_rules.fedavg_aggregate(filtered_updates, filtered_weights)
        
        return aggregated, kept_indices
    
    def aggregate_plain_updates(self, client_updates: List[Dict[str, torch.Tensor]],
                                client_weights: List[float],
                                client_upload_sizes: List[int] = None) -> Dict[str, torch.Tensor]:
        """聚合明文模型更新（支持防御机制）"""
        start_time = time.time()
        if len(client_updates) == 0:
            raise ValueError("客户端更新列表为空")
        
        aggregated_update, kept_indices = self._apply_defense(client_updates, client_weights)
        self.aggregation_time = time.time() - start_time
        
        self.download_cost = self.compute_download_cost() * len(client_updates)
        if client_upload_sizes:
            self.upload_cost = sum([client_upload_sizes[i] for i in kept_indices])
        else:
            total_params = sum(p.numel() for p in self.model.parameters())
            self.upload_cost = total_params * 4 * len(client_updates)
        self.communication_cost = self.upload_cost + self.download_cost
        
        log_aggregation_result(
            num_clients=len(client_updates), kept=len(kept_indices),
            rule=self.aggregation_rule, agg_time=self.aggregation_time,
            upload=self.upload_cost, download=self.download_cost,
        )
        return aggregated_update
    
    def aggregate_encrypted_updates(self, encrypted_updates: List[Dict[str, List]],
                                    client_weights: List[float],
                                    ckks_manager,
                                    client_upload_sizes: List[int] = None):
        """聚合加密的模型更新（CKKS同态聚合，返回密文结果）"""
        start_time = time.time()
        if len(encrypted_updates) == 0:
            raise ValueError("加密更新列表为空")

        total_weight = sum(client_weights)
        normalized_weights = [w / total_weight for w in client_weights]
        tag_info(LogTag.AGG, f"Aggregating {len(encrypted_updates)} encrypted updates...")

        aggregated_encrypted = ckks_manager.aggregate_encrypted_updates(
            encrypted_updates, normalized_weights
        )

        self.aggregation_time = time.time() - start_time
        
        # 通信统计：单密钥方案
        # - upload_cost：客户端密文上传
        # - download_cost：服务器下发加密全局模型（密文）
        if self.encrypted_global_state is not None:
            download_size = ckks_manager.compute_encrypted_update_size(self.encrypted_global_state)
        else:
            download_size = self.compute_download_cost()  # 明文大小作为fallback
        self.download_cost = download_size * len(encrypted_updates)
        
        if client_upload_sizes:
            self.upload_cost = sum(client_upload_sizes)
        else:
            total_params = sum(p.numel() for p in self.model.parameters())
            ciphertext_expansion = 20
            self.upload_cost = total_params * 4 * ciphertext_expansion * len(encrypted_updates)
        self.communication_cost = self.upload_cost + self.download_cost
        
        log_aggregation_result(
            num_clients=len(encrypted_updates), kept=len(encrypted_updates),
            rule="CKKS+" + self.aggregation_rule, agg_time=self.aggregation_time,
            upload=self.upload_cost, download=self.download_cost,
        )
        return aggregated_encrypted
    
    # ==================================================================
    # TEE 路径（方案①）
    # ==================================================================
    def process_encrypted_round_via_tee(
        self,
        encrypted_updates: List[Dict[str, Any]],
        client_weights: List[float],
        client_upload_sizes: List[int] = None,
        client_masks: Optional[List[Dict[str, Any]]] = None,
        use_host_aggregation: bool = True,
    ) -> Dict[str, Any]:
        """
        TEE 路径：一轮加密联邦学习的完整处理（可插拔方案①）
        
        流程：
          1. Host 收集客户端上传
          2. Host 侧同态预聚合（按 batch 对齐，标量乘权重，同态加法）
          3. Host 将聚合密文转发 TEE
          4. TEE 解密聚合密文 → 除以权重 → 掩码补偿 → 全局残差 → TopK → 重加密
          5. Host 合并到旧全局密文 → 计算稀疏 delta
          6. Host 更新 encrypted_global_state
          7. Host 将稀疏 delta 存入历史（供 Prefetch 使用）
        
        Args:
            encrypted_updates: 客户端上传的稀疏密文列表
            client_weights: 客户端权重列表
            client_upload_sizes: 每个客户端上传大小（字节）
            use_host_aggregation: 是否启用 Host 侧同态预聚合（默认 True）
        
        Returns:
            稀疏 delta 密文（供客户端下载）
        """
        if self.tee_processor is None:
            raise RuntimeError("TEE 未初始化，请检查 config['tee']['enabled']")
        if self.encrypted_global_state is None:
            raise RuntimeError("encrypted_global_state 未初始化")
        
        start_time = time.time()
        upload_difference = self.config['system'].get('upload_difference', True)
        
        tag_info(LogTag.SERVER, f"TEE round start | clients={len(encrypted_updates)} | host_agg={use_host_aggregation}")
        
        if use_host_aggregation:
            # ---- Step 1-2: Host 侧同态预聚合 ----
            from ckks_fed.host_aggregator import host_homomorphic_aggregate
            aggregated_upload, agg_weights, client_upload_masks, host_agg_time = host_homomorphic_aggregate(
                client_uploads=encrypted_updates,
                client_weights=client_weights,
                ckks_manager=self.ckks_manager,
            )
            
            # ---- Step 3-4: TEE 处理聚合后的密文 ----
            tee_result = self.tee_processor.process_aggregated_round(
                old_global_enc=self.encrypted_global_state,
                aggregated_upload=aggregated_upload,
                agg_weights=agg_weights,
                client_weights=client_weights,
                upload_difference=upload_difference,
                client_masks=client_masks,
                client_upload_masks=client_upload_masks,
                round_num=self.round_num,
            )
        else:
            # 原始路径：不启用 Host 预聚合（向后兼容）
            tee_result = self.tee_processor.process_round(
                old_global_enc=self.encrypted_global_state,
                client_uploads=encrypted_updates,
                client_weights=client_weights,
                upload_difference=upload_difference,
                client_masks=client_masks,
                round_num=self.round_num,
            )
        
        # Step 5: 先计算稀疏 delta（旧全局密文尚未被覆盖）
        delta_enc = self._compute_sparse_delta(tee_result)
        
        # Step 6: 再合并 TEE 返回的稀疏密文到旧全局密文
        self._merge_tee_result(tee_result)
        
        # Step 7: 通信统计
        self.aggregation_time = time.time() - start_time
        
        # 上行通信量（客户端上传总和）
        if client_upload_sizes:
            self.upload_cost = sum(client_upload_sizes)
        else:
            total_params = sum(p.numel() for p in self.model.parameters())
            ciphertext_expansion = 20
            self.upload_cost = total_params * 4 * ciphertext_expansion * len(encrypted_updates)
        
        # 下行通信量
        self.download_cost = self.ckks_manager.compute_encrypted_update_size(self.encrypted_global_state)
        self.communication_cost = self.upload_cost + self.download_cost
        
        log_aggregation_result(
            num_clients=len(encrypted_updates), kept=len(encrypted_updates),
            rule="CKKS+TEE", agg_time=self.aggregation_time,
            upload=self.upload_cost, download=self.download_cost,
        )
        
        self.round_num += 1
        tag_info(LogTag.SERVER,
                 f"TEE round done | delta_batches={sum(delta_enc['mask'])}/"
                 f"{len(delta_enc['mask'])} | ↓={fmt_size(self.download_cost)} | "
                 f"round={self.round_num}")
        
        return delta_enc
    
    def _merge_tee_result(self, tee_result: Dict[str, Any]):
        """
        将 TEE 返回的稀疏新全局密文合并到旧全局密文中。
        
        选中的 batch → 用 TEE 返回的新密文替换（反序列化为 CKKSVector）
        未选中的 batch → 保持旧全局密文不变
        """
        old_cts = self.encrypted_global_state['ciphertexts']
        tee_cts = tee_result['ciphertexts']
        mask = tee_result['mask']
        
        # 逐个 batch 替换
        ct_idx = 0
        for batch_idx, is_selected in enumerate(mask):
            if is_selected:
                # TEE 返回的是序列化字节串，需要反序列化为 CKKSVector
                old_cts[batch_idx] = ts.CKKSVector.load(
                    self.ckks_manager.context.context, tee_cts[ct_idx]
                )
                ct_idx += 1
            # else: 保持旧密文不变
        
        # 更新 mask 为全 1（全局模型现在包含所有 batch）
        self.encrypted_global_state['mask'] = [1] * len(mask)
    
    def _compute_sparse_delta(self, tee_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算稀疏 delta = 新全局密文 - 旧全局密文（同态减法）
        
        必须在 _merge_tee_result 之前调用，否则旧全局密文已被覆盖。
        只对 TEE 选中的 batch 做减法，未选中的 batch delta = 0（不传）。
        
        Returns:
            稀疏 delta 密文（__sparse__ 格式）
        """
        old_cts = self.encrypted_global_state['ciphertexts']
        tee_cts = tee_result['ciphertexts']
        tee_mask = tee_result['mask']
        
        delta_cts = []
        ct_idx = 0
        for batch_idx, is_selected in enumerate(tee_mask):
            if is_selected:
                # 同态减法：delta = new_global - old_global
                # tee_cts 是序列化字节串，需要先 load
                new_ct = ts.CKKSVector.load(
                    self.ckks_manager.context.context, tee_cts[ct_idx]
                )
                delta_ct = self.ckks_manager.evaluator.sub(new_ct, old_cts[batch_idx])
                # 序列化再反序列化，刷新内部表示以确保与后续密文兼容
                delta_cts.append(
                    ts.CKKSVector.load(
                        self.ckks_manager.context.context,
                        delta_ct.serialize()
                    ).serialize()
                )
                ct_idx += 1
        
        return {
            '__sparse__': True,
            'ciphertexts': delta_cts,
            'mask': tee_mask,
            'batch_size': tee_result['batch_size'],
            'total_elements': tee_result['total_elements'],
            'shapes': tee_result['shapes'],
            'offsets': tee_result['offsets'],
        }
    
    def update_global_model(self, aggregated_update,
                           learning_rate: float = 1.0):
        """
        更新全局模型。
        如果 aggregated_update 是密文，执行同态更新（encrypted_global_state += update）。
        如果是明文，执行明文更新（兼容旧代码）。
        如果是 MASER 压缩密文（原版 MASER 风格），先解密并 0 填充恢复完整更新，
        再明文应用到全局模型。
        """
        if self._is_encrypted_update(aggregated_update):
            if aggregated_update.get('maser_mode') == 'maser_global_compressed':
                # 原版 MASER：密文聚合后解密，0 填充恢复完整更新，明文更新全局模型
                plain_update = self._decrypt_maser_compressed_update(aggregated_update)
                self._update_plain_global_model(plain_update, learning_rate)
            else:
                self._update_encrypted_global_state(aggregated_update, learning_rate)
        else:
            self._update_plain_global_model(aggregated_update, learning_rate)

    def _decrypt_maser_compressed_update(self, encrypted_update: Dict[str, Any]) -> Dict[str, torch.Tensor]:
        """
        解密 MASER 压缩聚合更新，并恢复为完整模型更新（明文）。
        """
        if self.ckks_manager is None:
            raise RuntimeError("ckks_manager 未初始化，无法解密 MASER 压缩更新")

        if encrypted_update.get('__multi_key__'):
            raise RuntimeError(
                "多密钥 MASER 更新请调用 update_global_model_maser_multikey("
                "aggregated_update, partial_shares, client_ids)"
            )

        shapes = {name: param.shape for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                shapes[name] = buf.shape

        decrypted = self.ckks_manager.decrypt_model_update(encrypted_update, shapes)
        return decrypted

    def update_global_model_maser_multikey(
        self,
        aggregated_update: Dict[str, Any],
        partial_shares: List[List[Any]],
        client_ids: List[int],
        learning_rate: float = 1.0,
    ):
        """
        多密钥 MASER：聚合客户端解密份额并解码，明文更新全局模型。

        Args:
            aggregated_update: 同态聚合后的加密更新（__multi_key__=True）
            partial_shares: 每个客户端对每个 slice 的部分解密份额
            client_ids: 对应客户端 ID 列表
            learning_rate: 全局模型更新学习率
        """
        if self.ckks_manager is None:
            raise RuntimeError("ckks_manager 未初始化，无法解密多密钥 MASER 更新")
        if not aggregated_update.get('__multi_key__'):
            raise ValueError("update_global_model_maser_multikey 仅支持 __multi_key__=True 的更新")

        plain_update = self.ckks_manager.decrypt_maser_compressed_multikey(
            aggregated_update, partial_shares, client_ids
        )
        self._update_plain_global_model(plain_update, learning_rate)

    def update_global_model_esafl_native_multikey(
        self,
        aggregated_update: Dict[str, Any],
        partial_shares: List[List[Any]],
        client_ids: List[int],
        learning_rate: float = 1.0,
    ):
        """
        ESAFL NATIVE 多密钥：聚合客户端解密份额并解码，明文更新全局模型。

        Args:
            aggregated_update: 同态聚合后的加密更新（__native_multi_key__=True）
            partial_shares: 每个客户端对每个 batch 的部分解密份额
            client_ids: 对应客户端 ID 列表
            learning_rate: 全局模型更新学习率
        """
        if self.ckks_manager is None:
            raise RuntimeError("ckks_manager 未初始化，无法解密 ESAFL NATIVE 更新")
        if not aggregated_update.get('__native_multi_key__'):
            raise ValueError("update_global_model_esafl_native_multikey 仅支持 __native_multi_key__=True 的更新")

        plain_update = self.ckks_manager.decrypt_esafl_native_multikey(
            aggregated_update, partial_shares, client_ids
        )
        self._update_plain_global_model(plain_update, learning_rate)
    
    # ==================================================================
    # 全局掩码投票（ESAFL 多密钥适配）
    # ==================================================================
    def run_global_mask_vote(self, client_masks: List[Optional[np.ndarray]],
                              num_batches: int, round_num: int) -> Optional[np.ndarray]:
        """
        执行全局掩码投票流程。

        修正后的隐私安全流程：
          1. 客户端本地计算 mask（不上传明文梯度）
          2. 服务器只接收 client_masks（0/1 向量），聚合生成全局掩码
          3. 广播全局掩码给所有客户端

        Args:
            client_masks: 客户端 mask 列表，每个元素 shape=(num_batches,) 或 None
            num_batches: batch 总数
            round_num: 当前轮次

        Returns:
            全局掩码 np.ndarray（shape=(num_batches,)），如果 mode='none' 则返回 None
        """
        if self.global_mask_vote.mode == 'none':
            self.current_global_mask = None
            return None

        # 过滤掉 None（sparsification 未开启的客户端）
        valid_masks = [m for m in client_masks if m is not None]
        if not valid_masks:
            self.current_global_mask = None
            return None

        # 对齐 mask 长度
        aligned_masks = []
        for mask in valid_masks:
            if len(mask) != num_batches:
                aligned = np.zeros(num_batches, dtype=np.int8)
                copy_len = min(len(mask), num_batches)
                aligned[:copy_len] = mask[:copy_len]
                aligned_masks.append(aligned)
            else:
                aligned_masks.append(mask)

        # 服务器聚合生成全局掩码（传递 round_num/history 以支持自适应策略）
        global_mask = self.global_mask_vote.server_aggregate(
            aligned_masks, num_batches, round_num=round_num, history=self.history
        )
        self.current_global_mask = global_mask

        active_batches = int(np.sum(global_mask)) if global_mask is not None else 0
        tag_info(LogTag.SERVER,
                 f"GlobalMaskVote[{self.global_mask_vote.mode}] | "
                 f"batches={active_batches}/{num_batches} | "
                 f"clients={len(valid_masks)} | round={round_num}")

        return global_mask
    
    def get_current_global_mask(self) -> Optional[np.ndarray]:
        """获取当前轮次的全局掩码"""
        return self.current_global_mask

    def run_maser_global_vote(self,
                              client_masks: List[Optional[np.ndarray]],
                              total_elements: int,
                              voting_threshold: float = 0.5,
                              topk_ratio: float = None,
                              round_num: int = 0) -> Optional[np.ndarray]:
        """
        MASER 全局参数级 mask 投票。

        流程：
          1. 客户端本地计算参数级 mask（只上传 mask，不上传明文梯度）
          2. 服务器聚合 client_masks，按 threshold/topk 生成全局 mask
          3. 返回全局选中的参数索引
        """
        from ckks_fed.maser_mask import aggregate_maser_masks, get_indices_from_mask

        valid_masks = [m for m in client_masks if m is not None]
        if not valid_masks:
            self.current_global_maser_indices = None
            return None

        global_mask = aggregate_maser_masks(
            valid_masks,
            total_elements=total_elements,
            voting_threshold=voting_threshold,
            topk_ratio=topk_ratio,
        )
        self.current_global_maser_indices = get_indices_from_mask(global_mask)

        active = len(self.current_global_maser_indices)
        tag_info(LogTag.SERVER,
                 f"MASER global vote | active={active}/{total_elements} "
                 f"({active / max(1, total_elements):.2%}) | clients={len(valid_masks)} | round={round_num}")
        return self.current_global_maser_indices

    def get_current_global_maser_indices(self) -> Optional[np.ndarray]:
        """获取当前轮次 MASER 全局选中的参数索引"""
        return getattr(self, 'current_global_maser_indices', None)

    def evaluate(self, test_loader, criterion: nn.Module) -> Tuple[float, float]:
        # 服务器可解密：先同步明文模型再评估
        if self.encrypted_global_state is not None:
            self._sync_model_from_encrypted_state()
        
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = criterion(output, target)
                total_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()
        
        avg_loss = total_loss / len(test_loader)
        accuracy = 100. * correct / total
        
        self.history['test_loss'].append(avg_loss)
        self.history['test_acc'].append(accuracy)
        self.history['aggregation_time'].append(self.aggregation_time)
        self.history['communication_cost'].append(self.communication_cost)
        self.history['upload_cost'].append(self.upload_cost)
        self.history['download_cost'].append(self.download_cost)
        
        log_evaluation_result(avg_loss, accuracy)
        return avg_loss, accuracy
    
    def get_history(self) -> Dict:
        return self.history.copy()
    
    def get_stats(self) -> Dict:
        return {
            'round_num': self.round_num,
            'total_aggregation_time': sum(self.history['aggregation_time']),
            'total_communication_cost': sum(self.history['communication_cost']),
            'total_upload_cost': sum(self.history['upload_cost']),
            'total_download_cost': sum(self.history['download_cost']),
            'avg_aggregation_time': sum(self.history['aggregation_time']) / max(1, len(self.history['aggregation_time'])),
            'avg_communication_cost': sum(self.history['communication_cost']) / max(1, len(self.history['communication_cost']))
        }


class PrefetchAggregationServer(AggregationServer):
    """
    支持 CKKS 密文预取的聚合服务器（CipherFetch）。

    设计要点：
    --------------------------------------------------------------------
    1. 【模型增量队列】维护 server_models_queue，用于计算每轮明文增量 Δ
    2. 【统一加密】所有客户端共享 CKKS 密钥，服务器每轮只需加密 Δ 一次
    3. 【历史密文记录】encrypted_deltas_history 记录每轮加密增量（用于 fetch 补齐）
    4. 【预取计数】client_prefetch_counts 记录每个客户端已预取了多少个 delta
    5. 【虚拟时钟】模拟客户端完成时间，推进 global_virtual_clock
    6. 【外部调度器】PrefetchScheduler 决定每个客户端的预取开始轮次
    """

    def __init__(self, model: nn.Module, config: Dict, device: str = "cpu", ckks_manager=None, blinding_mask=None, esafl_adapter=None):
        super().__init__(model, config, device, ckks_manager, blinding_mask=blinding_mask)

        prefetch_cfg = config.get('prefetch', {})
        self.enable_prefetch = prefetch_cfg.get('enable_prefetch', False)
        self.max_prefetch_round = prefetch_cfg.get('max_prefetch_round', 3)
        self.warmup_round = prefetch_cfg.get('warmup_round', 2)
        
        # ---- ESAFL 适配器（可插拔）----
        self.esafl_adapter = esafl_adapter
        self.esafl_enabled = esafl_adapter is not None
        if self.esafl_enabled:
            tag_info(LogTag.SERVER, f"ESAFL enabled | mode={esafl_adapter.mode} | delta=encrypted")
        else:
            tag_info(LogTag.SERVER, "ESAFL disabled | using standard plaintext delta")

        # ---------- 历史密文（用于 fetch 补齐） ----------
        self.encrypted_deltas_history = []  # [{delta, size, from_round}, ...]
        self.client_prefetch_counts = {}    # client_id -> 已预取的 delta 数量
        
        # ---------- Batch 级别预取进度追踪 ----------
        # 记录每个客户端已预收到的 batch 位置（用于 batch 分片间隙预取）
        self.client_prefetched_batch_mask: Dict[int, List[int]] = {}

        # ---------- 虚拟时钟 ----------
        self.global_virtual_clock = 0.0
        self.round_durations = []
        self.exp_mov_avg_dur = 0.0

        # ---------- 外部依赖（实验循环注入） ----------
        self.bandwidth_simulator = None
        self.prefetch_scheduler = None
        self.last_update_index = {}         # client_id -> last_synced_round

        # ---------- 调度结果存储（由 main.py 写入） ----------
        self.prefetch_schedules: Dict[int, Dict[int, int]] = {}  # target_round -> {client_id: start_round}
        self.min_prefetch_round: Dict[int, int] = {}             # target_round -> min_start_round

        tag_info(LogTag.SERVER,
                 f"PrefetchServer init  |  enable={self.enable_prefetch}  |  "
                 f"window={self.max_prefetch_round}  |  warmup={self.warmup_round}")

    # ==================================================================
    # 模型更新与增量计算
    # ==================================================================
    def update_global_model(self, aggregated_update,
                            learning_rate: float = 1.0):
        """
        更新全局模型，并准备 delta 供预取。
        
        标准路径：delta 从明文模型差值计算，然后加密。
        ESAFL 路径：直接使用聚合密文作为 delta（upload_difference=true 时，
                    聚合结果本身就是 delta，无需额外计算）。
        """
        # 保存更新前的状态，用于计算 delta
        if self.enable_prefetch and not self.esafl_enabled:
            # 标准路径：保存更新前的明文状态
            prev_plain_state = {k: v.clone() for k, v in self.get_global_params().items()}

        super().update_global_model(aggregated_update, learning_rate)

        # 计算 delta
        if self.enable_prefetch:
            if self.esafl_enabled and self._is_encrypted_update(aggregated_update):
                # ESAFL: upload_difference=true 时，aggregated_update 本身就是 delta
                # 直接复用，无需同态减法（避免 TenSEAL 共享 context 导致的 transparent 问题）
                self.current_delta_encrypted_esafl = aggregated_update
                self.esafl_adapter.on_global_updated(self.encrypted_global_state)
                self.current_delta_plain = None
                active = sum(aggregated_update['mask'])
                total = len(aggregated_update['mask'])
                logger.info(f"ESAFL delta | aggregated_update reused | batches={active}/{total}")
            else:
                # 标准路径：明文差值
                current_plain_state = self.get_global_params()
                delta_plain = {}
                for name in prev_plain_state:
                    delta_plain[name] = current_plain_state[name] - prev_plain_state[name]
                self.current_delta_plain = delta_plain
                self.current_delta_encrypted_esafl = None

    # ==================================================================
    # 预取加密与广播
    # ==================================================================
    def _update_prefetch_masks_for_new_delta(self, new_delta_mask: List[int]):
        """新 delta 加入 history 后，更新所有未同步客户端的 sent_mask。

        新 delta 在 sent_mask=1 的位置有值时，该位置的 base_enc 值已改变
        （旧值 + 新 delta 的贡献），需要重置为未发送状态，以便后续重新发送。
        """
        for cid, sent_mask in list(self.client_prefetched_batch_mask.items()):
            if len(sent_mask) != len(new_delta_mask):
                # 长度不匹配（模型结构变化），重置为全 0
                self.client_prefetched_batch_mask[cid] = [0] * len(new_delta_mask)
            else:
                # 新 delta 有值且之前已发送的位置，重置为 0
                new_mask = []
                for i in range(len(sent_mask)):
                    if new_delta_mask[i] == 1 and sent_mask[i] == 1:
                        new_mask.append(0)
                    else:
                        new_mask.append(sent_mask[i])
                self.client_prefetched_batch_mask[cid] = new_mask

    def encrypt_and_stage_prefetch(self, ckks_manager):
        """
        将本轮 delta 加密后存入 history。
        
        标准路径：明文 delta → 加密。
        ESAFL 路径：直接使用密文 delta（已预先计算）。
        """
        if not self.enable_prefetch:
            self.current_delta_encrypted = None
            return None
        
        # ESAFL 路径：直接使用密文 delta
        if self.esafl_enabled and self.current_delta_encrypted_esafl is not None:
            delta_enc = self.current_delta_encrypted_esafl
            delta_size = ckks_manager.compute_encrypted_update_size(delta_enc)
            self.current_delta_encrypted = {
                'delta': delta_enc,
                'size': delta_size,
                'from_round': self.round_num,
                'encrypt_time': 0.0,  # 同态减法无额外加密开销
            }
            self.encrypted_deltas_history.append(self.current_delta_encrypted)
            # Bug2修复：新 delta 加入后更新所有未同步客户端的 sent_mask
            self._update_prefetch_masks_for_new_delta(delta_enc['mask'])
            tag_info(LogTag.SERVER,
                     f"ESAFL delta staged | size={fmt_size(delta_size)} | round={self.round_num}")
            self.current_delta_encrypted_esafl = None
            return self.current_delta_encrypted
        
        # 标准路径：明文 delta → 加密
        if not hasattr(self, 'current_delta_plain') or self.current_delta_plain is None:
            self.current_delta_encrypted = None
            return None

        start = time.time()
        encrypted_delta = ckks_manager.encrypt_model_update(
            self.current_delta_plain, skip_sparsification=True)
        encrypt_time = time.time() - start

        delta_size = ckks_manager.compute_encrypted_update_size(encrypted_delta)

        self.current_delta_encrypted = {
            'delta': encrypted_delta,
            'size': delta_size,
            'from_round': self.round_num,
            'encrypt_time': encrypt_time,
        }
        self.encrypted_deltas_history.append(self.current_delta_encrypted)
        # Bug2修复：新 delta 加入后更新所有未同步客户端的 sent_mask
        self._update_prefetch_masks_for_new_delta(encrypted_delta['mask'])

        tag_info(LogTag.SERVER,
                 f"密文增量已准备(明文加密)  |  大小={fmt_size(delta_size)}")

        self.current_delta_plain = None
        return self.current_delta_encrypted

    def _slice_delta_batches(self, delta_enc: Dict, target_mask: List[int]) -> Dict:
        """
        从 delta 包中按 target_mask 提取指定 batch。
        target_mask 与 delta_enc['mask'] 长度相同，为 1 的位置提取。
        """
        cts = delta_enc['ciphertexts']
        mask = delta_enc['mask']
        new_cts = []
        ct_idx = 0
        for i in range(len(mask)):
            if mask[i] == 1:
                if target_mask[i] == 1:
                    new_cts.append(cts[ct_idx])
                ct_idx += 1
        result = {
            '__sparse__': True,
            'ciphertexts': new_cts,
            'mask': list(target_mask),
            'batch_size': delta_enc['batch_size'],
            'total_elements': delta_enc['total_elements'],
            'shapes': delta_enc['shapes'],
            'offsets': delta_enc['offsets'],
        }
        if delta_enc.get('packing_metadata') is not None:
            result['packing_metadata'] = delta_enc['packing_metadata']
        return result

    def broadcast_prefetch_to_unselected(self, unselected_ids: List[int],
                                          client_objects: Dict[int, object],
                                          target_pool_ids: Optional[List[int]] = None,
                                          time_budget: Optional[float] = None) -> int:
        """
        向本轮未被选中的客户端广播密文增量（Batch-Level 间隙预取）。

        核心逻辑（对齐 FedFetch 间隙模型）：
        1. 合并所有缺失 delta 为 base（同态累积）
        2. 计算 base 的 batch 粒度和单个 batch 大小
        3. 获取客户端已预收到的 batch mask
        4. 计算还缺失的 batch
        5. 按间隙带宽切分：本轮间隙能下几个 batch 就下几个
        6. 发送切分后的 batch chunk，客户端收到后同态累加
        7. 下不完的 batch 留下一轮继续（跨间隙续传）

        相比旧版"能下完就发全部，下不完就跳过"：
        - 低带宽客户端不再被永久跳过
        - 每轮间隙逐步消化 backlog，与 FedFetch 逐坐标消化语义一致
        """
        if not self.enable_prefetch or not self.encrypted_deltas_history:
            return 0

        ids_to_broadcast = unselected_ids
        if target_pool_ids is not None:
            pool_set = set(target_pool_ids)
            ids_to_broadcast = [cid for cid in unselected_ids if cid in pool_set]
            if not ids_to_broadcast and unselected_ids:
                ids_to_broadcast = unselected_ids

        total_broadcast_size = 0
        total_delta_count = 0
        synced_count = 0
        need_prefetch_clients = []
        skipped_clients = []
        ema_dur = max(time_budget if time_budget is not None else self.exp_mov_avg_dur, 1.0)

        for cid in ids_to_broadcast:
            client = client_objects.get(cid)
            if client is None:
                continue

            last_synced = self.last_update_index.get(cid, 0)
            # 方案A修复：不再用 client_prefetch_counts 截断，直接取所有从 last_synced 开始的 delta
            start_idx = last_synced
            missing_deltas = self.encrypted_deltas_history[start_idx:]

            if not missing_deltas:
                synced_count += 1
                continue

            missing_count = len(missing_deltas)

            # Step 1: 合并所有缺失 delta 为 base
            base_enc = None
            for d in missing_deltas:
                delta = d['delta']
                if not delta.get('__sparse__'):
                    raise ValueError("预取 delta 必须使用 __sparse__ 格式")
                if base_enc is None:
                    base_enc = {
                        '__sparse__': True,
                        'ciphertexts': list(delta['ciphertexts']),
                        'mask': list(delta['mask']),
                        'batch_size': delta['batch_size'],
                        'total_elements': delta['total_elements'],
                        'shapes': delta['shapes'],
                        'offsets': delta['offsets'],
                        'packing_metadata': delta.get('packing_metadata'),
                    }
                else:
                    base_enc = merge_sparse_encrypted_updates(
                        base_enc, delta, evaluator=self.ckks_manager.evaluator
                    )

            base_size = (self.ckks_manager.compute_encrypted_update_size(base_enc)
                         if self.ckks_manager else missing_deltas[0]['size'])
            total_batches = sum(base_enc['mask'])
            per_batch_size = base_size / max(1, total_batches)

            # Step 2: 获取已预收到的 batch mask
            sent_mask = self.client_prefetched_batch_mask.get(cid, [0] * len(base_enc['mask']))
            if len(sent_mask) != len(base_enc['mask']):
                # mask 长度不一致（可能因为模型结构变化），重置
                sent_mask = [0] * len(base_enc['mask'])

            # Step 3: 计算还缺失的 batch
            remaining_mask = [1 if b == 1 and s == 0 else 0
                              for b, s in zip(base_enc['mask'], sent_mask)]
            remaining_batches = sum(remaining_mask)

            if remaining_batches == 0:
                # 该客户端 base 的所有 batch 已经预收齐
                synced_count += 1
                self.client_prefetch_counts[cid] = missing_count
                continue

            from_round_start = missing_deltas[0]['from_round']
            from_round_end = missing_deltas[-1]['from_round']
            from_round_str = (f"{from_round_start}..{from_round_end}"
                              if from_round_start != from_round_end else str(from_round_start))

            # Step 4: 计算本轮间隙能下几个 batch
            batches_can_send = remaining_batches
            if self.bandwidth_simulator is not None:
                dl_bw = self.bandwidth_simulator.get_dl_bw_bits(cid)
                can_download_bytes = ema_dur * dl_bw / 8
                batches_can_send = int(can_download_bytes / per_batch_size)

            if batches_can_send <= 0:
                # 连 1 个 batch 都下不完，本轮跳过
                skipped_clients.append(
                    f"#{cid}(需{per_batch_size * 8 / max(dl_bw, 1):.1f}s/batch>预算{ema_dur:.1f}s)"
                )
                continue

            # 安全截断：不要超过剩余 batch 数
            batches_can_send = min(batches_can_send, remaining_batches)

            # Step 5: 从 remaining_mask 中切出前 batches_can_send 个 1
            remaining_positions = [i for i, m in enumerate(remaining_mask) if m == 1]
            send_positions = remaining_positions[:batches_can_send]
            send_mask = [1 if i in send_positions else 0 for i in range(len(base_enc['mask']))]

            chunk_enc = self._slice_delta_batches(base_enc, send_mask)
            chunk_size = (self.ckks_manager.compute_encrypted_update_size(chunk_enc)
                          if self.ckks_manager else int(per_batch_size * batches_can_send))

            # Step 6: 发送 chunk
            client.receive_prefetch_delta(chunk_enc, chunk_size, from_round_str)

            # Step 7: 更新已预收到 mask
            new_sent_mask = [1 if s == 1 or sm == 1 else 0
                             for s, sm in zip(sent_mask, send_mask)]
            self.client_prefetched_batch_mask[cid] = new_sent_mask

            # Step 8: 更新 delta 计数（仅用于统计，不再用于索引）
            # 如果所有 batch 都已发送，则标记为完全预取
            if sum(new_sent_mask) >= total_batches:
                self.client_prefetch_counts[cid] = missing_count
            else:
                # 部分预取：保持原值，避免高估导致 start_idx 跳过未完整 delta
                pass

            total_broadcast_size += chunk_size
            total_delta_count += 1
            if hasattr(client, 'prefetch_download_time'):
                dl_time = self.bandwidth_simulator.estimate_download_time(cid, chunk_size * 8) if self.bandwidth_simulator else 0.0
                client.prefetch_download_time += dl_time

            need_prefetch_clients.append(
                f"#{cid}(补{batches_can_send}/{remaining_batches}batch→{fmt_size(chunk_size)})"
            )

        client_count = len(ids_to_broadcast)
        pool_info = f"(池内{client_count}/{len(unselected_ids)})" if target_pool_ids is not None else ""

        if client_count > 0:
            avg_cached = sum(self.client_prefetch_counts.get(cid, 0) for cid in ids_to_broadcast) // client_count
            summary = (f"预取摘要{pool_info}: {synced_count}/{client_count}已同步"
                       f" | {len(need_prefetch_clients)}个需补"
                       f" | 实际发送{total_delta_count}个chunk={fmt_size(total_broadcast_size)}"
                       f" | 跳过{len(skipped_clients)}个(带宽不够)"
                       f" | 平均缓存={avg_cached}个"
                       f" | 预算={ema_dur:.1f}s")
            if need_prefetch_clients and len(need_prefetch_clients) <= 5:
                summary += f" | 需补: {' '.join(need_prefetch_clients)}"
            elif need_prefetch_clients:
                summary += f" | 需补: {len(need_prefetch_clients)}个客户端"
            if skipped_clients and len(skipped_clients) <= 3:
                summary += f" | 跳过: {' '.join(skipped_clients)}"
            tag_info(LogTag.PREFETCH, summary)
        return total_broadcast_size

    # ==================================================================
    # Fetch 补齐：计算客户端还需要下载多少
    # ==================================================================
    def get_remaining_fetch_info(self, client_id: int, current_round: int, is_warmup: bool = False) -> Dict:
        """
        计算客户端 client_id 在 current_round 训练时，
        还需要从服务器 Fetch 多少剩余密文增量（Batch-Aware 版本）。

        核心逻辑：
        1. 合并所有缺失 deltas 为 base（同态累积）
        2. 排除已通过 batch 分片间隙预取收到的 batch
        3. 只 fetch 还缺失的 batch，避免重复发送导致同态累加数值翻倍

        Args:
            is_warmup: 是否为 warmup 阶段。

        Returns:
            None:  预取已完全覆盖（包括 batch 级别）
            dict:  {
                'count': 1,
                'total_size': 剩余缺失 batch 的总字节数,
                'deltas': [chunk_dict]  # 只包含还缺失的 batch
            }
        """
        if not self.enable_prefetch:
            return None

        last_synced = self.last_update_index.get(client_id, 0)
        # 方案A修复：直接取所有从 last_synced 到 current_round 的缺失 delta
        # 不再用 client_prefetch_counts 截断，避免跳过未完整预取的 delta
        end_idx = min(current_round, len(self.encrypted_deltas_history))
        deltas_to_fetch = self.encrypted_deltas_history[last_synced:end_idx]

        if not deltas_to_fetch:
            return None

        # Step 1: 合并所有缺失 delta 为 base
        base_enc = None
        for d in deltas_to_fetch:
            delta = d['delta']
            if not delta.get('__sparse__'):
                raise ValueError("fetch delta 必须使用 __sparse__ 格式")
            if base_enc is None:
                base_enc = {
                    '__sparse__': True,
                    'ciphertexts': list(delta['ciphertexts']),
                    'mask': list(delta['mask']),
                    'batch_size': delta['batch_size'],
                    'total_elements': delta['total_elements'],
                    'shapes': delta['shapes'],
                    'offsets': delta['offsets'],
                    'packing_metadata': delta.get('packing_metadata'),
                }
            else:
                base_enc = merge_sparse_encrypted_updates(
                    base_enc, delta, evaluator=self.ckks_manager.evaluator
                )

        # Step 2: 排除已预收到的 batch
        sent_mask = self.client_prefetched_batch_mask.get(client_id, [0] * len(base_enc['mask']))
        if len(sent_mask) != len(base_enc['mask']):
            sent_mask = [0] * len(base_enc['mask'])

        remaining_mask = [1 if b == 1 and s == 0 else 0
                          for b, s in zip(base_enc['mask'], sent_mask)]
        remaining_batches = sum(remaining_mask)

        if remaining_batches == 0:
            # 所有 batch 已通过间隙预取收到
            return None

        # Step 3: 从 base 中提取剩余缺失 batch
        chunk_enc = self._slice_delta_batches(base_enc, remaining_mask)
        chunk_size = (self.ckks_manager.compute_encrypted_update_size(chunk_enc)
                      if self.ckks_manager else 0)

        from_round_start = deltas_to_fetch[0]['from_round']
        from_round_end = deltas_to_fetch[-1]['from_round']
        from_round_str = (f"{from_round_start}..{from_round_end}"
                          if from_round_start != from_round_end else str(from_round_start))

        merged_delta = {
            'delta': chunk_enc,
            'size': chunk_size,
            'from_round': from_round_str,
            'from_round_start': from_round_start,
            'from_round_end': from_round_end,
        }

        return {
            'count': 1,
            'total_size': chunk_size,
            'deltas': [merged_delta],
        }

    # ==================================================================
    # 虚拟时钟
    # ==================================================================
    def calculate_round_duration(self, selected_ids: List[int],
                                  client_objects: Dict[int, object],
                                  current_round: int = None) -> float:
        """
        计算本轮持续时间 = max(选中客户端的完成时间)。
        完成时间 = fetch_time（剩余下载） + compute_time（训练） + upload_time（上传）。

        对齐 FedFetch：fetch_time 基于 get_remaining_fetch_info 计算理论下载时间，
        不依赖 client.fetch_time（因为 global_params 内存同步时 client.fetch_time=0）。
        调用方应确保在 record_client_sync 之前调用此方法，使 get_remaining_fetch_info
        看到训练前的状态（last_update_index 为上一轮训练后的值）。
        """
        cr = current_round if current_round is not None else self.round_num

        completion_times = []

        for cid in selected_ids:
            client = client_objects.get(cid)
            if client is None:
                continue

            compute_time = getattr(client, 'local_train_time', 5.0)

            upload_time = 0.0
            ciphertext_size_bits = getattr(client, 'ciphertext_size', 0) * 8
            if self.bandwidth_simulator and ciphertext_size_bits > 0:
                upload_time = self.bandwidth_simulator.estimate_upload_time(
                    cid, ciphertext_size_bits
                )

            # fetch_time：优先使用客户端实际测量的值（已训练客户端更准确），
            # 回退到 get_remaining_fetch_info 理论估算（用于未训练客户端或启动时）
            fetch_time = 0.0
            if self.bandwidth_simulator:
                # 本轮已训练的客户端：local_train 中已经执行了 fetch_remaining_deltas，
                # client.fetch_time 是真实的 wall-clock fetch 耗时（含 0）
                actual_fetch = getattr(client, 'fetch_time', 0.0)
                if actual_fetch > 0 or (hasattr(client, '_current_server_round') and client._current_server_round == cr):
                    fetch_time = actual_fetch
                else:
                    fetch_info = self.get_remaining_fetch_info(cid, cr)
                    if fetch_info:
                        fetch_time = self.bandwidth_simulator.estimate_download_time(
                            cid, fetch_info['total_size'] * 8)
                    # get_remaining_fetch_info 返回 None 表示客户端已完全同步，fetch_time = 0

            total_time = fetch_time + compute_time + upload_time
            completion_times.append(total_time)

        round_duration = max(completion_times) if completion_times else 1.0
        self.round_durations.append(round_duration)

        alpha = 0.125
        if self.exp_mov_avg_dur <= 0:
            self.exp_mov_avg_dur = round_duration
        else:
            self.exp_mov_avg_dur = (
                alpha * round_duration + (1.0 - alpha) * self.exp_mov_avg_dur
            )

        if self.prefetch_scheduler is not None:
            self.prefetch_scheduler.update_ema_duration(round_duration)

        return round_duration

    def advance_virtual_clock(self, duration: float):
        self.global_virtual_clock += duration

    def record_client_sync(self, client_id: int, round_num: int):
        self.last_update_index[client_id] = round_num
        # 同步后，客户端的预取计数清零（因为它已经同步到了最新状态）
        self.client_prefetch_counts[client_id] = 0
        # 同步后，batch 级别预取进度也清零
        self.client_prefetched_batch_mask.pop(client_id, None)
