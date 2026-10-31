"""
联邦学习客户端模块
实现本地训练、模型加密和上传功能
扩展支持：恶意客户端（数据攻击 + 模型攻击）
"""

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List, Tuple, Optional
import numpy as np
import time
import logging
import tenseal as ts
from ckks_fed.log_utils import (
    LogTag, tag_info, tag_warn, fmt_size,
    log_training_result, log_encryption_result,
)
from ckks_fed.crypto import merge_sparse_encrypted_updates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FederatedClient:
    """联邦学习客户端：负责本地训练、模型加密和上传"""
    
    def __init__(self, client_id: int, model: nn.Module, 
                 train_loader, config: Dict, device: str = "cpu",
                 blinding_mask=None, client_mask=None):
        self.client_id = client_id
        self.model = model.to(device)
        self.train_loader = train_loader
        self.config = config
        self.device = device
        
        self.num_epochs = config['system']['num_epochs']
        self.learning_rate = config['system']['learning_rate']
        self.batch_size = config['system']['batch_size']
        
        self.criterion = nn.CrossEntropyLoss()
        
        # ---- 可配置优化器（SGD / Adam / AdamW）----
        opt_cfg = config.get('system', {}).get('optimizer', {})
        opt_name = opt_cfg.get('name', 'sgd').lower()
        lr = opt_cfg.get('lr', config['system']['learning_rate'])
        
        if opt_name == 'adam':
            self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        elif opt_name == 'adamw':
            self.optimizer = optim.AdamW(self.model.parameters(), lr=lr)
        else:
            momentum = opt_cfg.get('momentum', 0.0)
            self.optimizer = optim.SGD(self.model.parameters(), lr=lr, momentum=momentum)
        
        # ---- 可配置学习率调度器 ----
        sched_cfg = config.get('system', {}).get('lr_scheduler', {})
        self.scheduler = None
        if sched_cfg.get('enabled', False):
            sched_name = sched_cfg.get('name', 'step').lower()
            if sched_name == 'step':
                self.scheduler = optim.lr_scheduler.StepLR(
                    self.optimizer,
                    step_size=sched_cfg.get('step_size', 5),
                    gamma=sched_cfg.get('gamma', 0.5)
                )
            elif sched_name == 'cosine':
                total_epochs = config['system']['num_rounds'] * config['system']['num_epochs']
                self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                    self.optimizer,
                    T_max=sched_cfg.get('T_max', total_epochs),
                    eta_min=sched_cfg.get('eta_min', 0.0)
                )
            elif sched_name == 'exponential':
                self.scheduler = optim.lr_scheduler.ExponentialLR(
                    self.optimizer,
                    gamma=sched_cfg.get('gamma', 0.95)
                )
            tag_info(LogTag.CLIENT, f"#{self.client_id} scheduler={sched_name} | step_size={sched_cfg.get('step_size', 'N/A')} | gamma={sched_cfg.get('gamma', 'N/A')}")
        
        self.local_train_time = 0.0
        self.encryption_time = 0.0
        self.plaintext_size = 0
        self.ciphertext_size = 0
        self.data_size = len(train_loader.dataset)
        
        # CKKS 管理器（明文客户端为 None，加密客户端由外部注入）
        self.ckks_manager = None
        
        # 零和盲化掩码（可插拔，由 KGC 在初始化时分发）
        self.blinding_mask = blinding_mask      # ZeroSumBlindingMask 实例（或 None）
        self.client_mask = client_mask          # 本客户端的掩码字典（或 None）
        
        # PTopk: 记录上次本地训练轮次，用于标准路径下判断跨轮残差衰减
        self._ptopk_last_trained_round = -1
        
        tag_info(LogTag.CLIENT, f"#{client_id} initialized  |  data_size={self.data_size}")
    
    def get_model_params(self) -> Dict[str, torch.Tensor]:
        params = {name: param.data.clone() for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                params[name] = buf.clone()
        return params
    
    def set_model_params(self, params: Dict[str, torch.Tensor]):
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if name in params:
                    param.copy_(params[name])
            for name, buf in self.model.named_buffers():
                if name in params:
                    buf.copy_(params[name])
    
    def _apply_ptopk_stale_decay(self, round_num: int) -> None:
        """
        标准路径下：客户端本次被选中时，若距离上次训练有 gap>1 轮，
        则按 stale_gamma^(gap-1) 衰减本地残差累加器。
        """
        if (self.ckks_manager is not None and
            hasattr(self.ckks_manager, 'ptopk') and
            self.ckks_manager.ptopk.client_residual_enabled):
            if self._ptopk_last_trained_round >= 0 and round_num is not None:
                gap = round_num - self._ptopk_last_trained_round
                if gap > 1:
                    self.ckks_manager.ptopk.decay_residual_by_gap(gap)
                    tag_info(LogTag.CLIENT,
                             f"#{self.client_id} PTopk residual DECAY | gap={gap} | last=R{self._ptopk_last_trained_round}")
                else:
                    tag_info(LogTag.CLIENT,
                             f"#{self.client_id} PTopk residual KEEP | continuous | last=R{self._ptopk_last_trained_round}")
            else:
                tag_info(LogTag.CLIENT,
                         f"#{self.client_id} PTopk residual INIT | first training")

    def local_train(self, global_params: Optional[Dict[str, torch.Tensor]] = None,
                    encrypted_global_params: Optional[Dict[str, List]] = None,
                    round_num: int = 0,
                    ) -> Tuple[Dict[str, torch.Tensor], float, float]:
        start_time = time.time()
        
        # 如果提供了密文全局模型，先解密
        if encrypted_global_params is not None:
            if self.ckks_manager is None:
                raise RuntimeError(f"Client {self.client_id}: ckks_manager not injected, cannot decrypt encrypted_global_params")
            shapes = {name: param.shape for name, param in self.model.named_parameters()}
            for name, buf in self.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    shapes[name] = buf.shape
            global_params = self.ckks_manager.decrypt_model_update(encrypted_global_params, shapes)
        
        if global_params is not None:
            self.set_model_params(global_params)
        old_params = self.get_model_params()
        
        # ---- PTopk: 标准路径下对跨轮残差进行陈旧衰减 ----
        self._apply_ptopk_stale_decay(round_num)
        
        # ---- 梯度裁剪配置 ----
        grad_clip_cfg = self.config.get('system', {}).get('gradient_clipping', {})
        grad_clip_enabled = grad_clip_cfg.get('enabled', False)
        grad_clip_max_norm = grad_clip_cfg.get('max_norm', 1.0)
        
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        for epoch in range(self.num_epochs):
            epoch_loss = 0.0
            epoch_correct = 0
            epoch_total = 0
            for batch_idx, (data, target) in enumerate(self.train_loader):
                data, target = data.to(self.device), target.to(self.device)
                self.optimizer.zero_grad()
                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()
                # ---- 梯度裁剪 (BatchCrypt/QuanCrypt-FL 推荐) ----
                if grad_clip_enabled:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip_max_norm)
                self.optimizer.step()
                epoch_loss += loss.item()
                _, predicted = output.max(1)
                epoch_total += target.size(0)
                epoch_correct += predicted.eq(target).sum().item()
            total_loss += epoch_loss / len(self.train_loader)
            correct += epoch_correct
            total += epoch_total
            # ---- 学习率调度器步进（每个本地 epoch）----
            if self.scheduler is not None:
                self.scheduler.step()
        
        avg_loss = total_loss / self.num_epochs
        accuracy = 100. * correct / total
        
        new_params = self.get_model_params()
        upload_difference = self.config['system'].get('upload_difference', True)
        if upload_difference:
            model_update = {name: new_params[name] - old_params[name] for name in old_params}
            mode_str = "差值"
        else:
            model_update = new_params
            mode_str = "完整权重"
        
        # ---- 模型更新裁剪 (Update Clipping, QuanCrypt-FL 风格) ----
        update_clip_cfg = self.config.get('system', {}).get('update_clipping', {})
        update_clip_enabled = update_clip_cfg.get('enabled', False)
        if update_clip_enabled and upload_difference:
            clip_method = update_clip_cfg.get('method', 'layerwise_mean')
            clip_factor = update_clip_cfg.get('clip_factor', 3.0)
            model_update = self._clip_model_update(model_update, clip_method, clip_factor)
        
        # ---- 可插拔：成对盲化掩码（KGC 生成，加密前注入）----
        # post_topk 模式：训练后直接全参数加掩码
        # pre_topk  模式：掩码延迟到 TopK 之后、加密之前注入（在 encrypt_model_update 中处理）
        if (self.blinding_mask is not None and self.client_mask is not None
                and getattr(self.blinding_mask, 'apply_mode', 'post_topk') == 'post_topk'):
            model_update = self.blinding_mask.apply_mask(model_update, self.client_mask, round_num=round_num)
            tag_info(LogTag.CLIENT, f"#{self.client_id} blinding mask applied (post_topk)  |  range=[-{self.blinding_mask.mask_range:.0e}, {self.blinding_mask.mask_range:.0e}] | round={round_num}")
        
        self.local_train_time = time.time() - start_time
        log_training_result(self.client_id, avg_loss, accuracy, self.local_train_time, mode_str)
        
        # 记录本轮训练轮次，供下次判断是否为连续参与
        self._ptopk_last_trained_round = round_num
        
        return model_update, avg_loss, accuracy
    
    def compute_local_mask(self, model_update: Dict[str, torch.Tensor], ckks_manager, round_num: int = 0) -> Optional[np.ndarray]:
        """
        客户端本地计算稀疏化 mask（隐私安全：不上传明文梯度，只返回 0/1 mask）。
        
        支持两种模式：
        1. ckks.sparsification.strategy != 'none' 时，计算 batch 级 mask
        2. maser.enable=true 时，计算参数级 mask（对齐原始 MASER）
        """
        ckks_cfg = self.config.get('ckks', {})
        sparsity_cfg = ckks_cfg.get('sparsification', {})
        strategy = sparsity_cfg.get('strategy', 'none')
        
        # MASER 模式：计算参数级 mask
        maser_cfg = self.config.get('maser', {})
        if maser_cfg.get('enable', False):
            from ckks_fed.maser_mask import compute_maser_mask
            masks = compute_maser_mask(model_update, maser_cfg.get('topk_ratio', 0.5))
            mask_list = []
            for name in sorted(masks.keys()):
                mask_list.extend(masks[name].detach().cpu().numpy().flatten().tolist())
            mask = np.array(mask_list, dtype=np.int8)
            active = int(mask.sum())
            total = len(mask)
            tag_info(LogTag.CLIENT, f"#{self.client_id} local mask computed | strategy=maser_param | "
                     f"active={active}/{total} | rate={maser_cfg.get('topk_ratio', 0.5)}")
            return mask
        
        # 如果 sparsification 未开启，不进行稀疏化，返回 None
        if strategy == 'none' or strategy is None:
            return None
        
        # 读取 sparsification 配置（稀疏率、打分方式等）
        sparsity_rate = sparsity_cfg.get('sparsity_rate', 0.1)
        scoring_method = sparsity_cfg.get('scoring_method', 'avg_abs')
        
        # 计算与 packing 策略对齐的 batch_size
        packing = ckks_manager.packing_strategy if ckks_manager else None
        values_per_chunk = packing.get_values_per_chunk() if packing else 8192
        
        # 调用 GlobalMaskVote 的静态方法在本地计算 mask
        from ckks_fed.global_mask_vote import GlobalMaskVote
        mask = GlobalMaskVote.compute_mask_from_update(
            model_update=model_update,
            batch_size=values_per_chunk,
            sparsity_rate=sparsity_rate,
            scoring_method=scoring_method,
            round_num=round_num,
        )
        
        active = int(mask.sum()) if mask is not None else 0
        total = len(mask) if mask is not None else 0
        tag_info(LogTag.CLIENT, f"#{self.client_id} local mask computed | strategy={strategy} | "
                 f"active={active}/{total} | rate={sparsity_rate} | scoring={scoring_method}")
        return mask
    
    def encrypt_update(self, model_update: Dict[str, torch.Tensor], ckks_manager, round_num: int = 0,
                        global_mask=None, global_maser_indices=None) -> Dict[str, List]:
        start_time = time.time()
        # ---- Warmup 支持：前 N 轮跳过客户端稀疏化（可插拔）----
        ckks_cfg = self.config.get('ckks', {})
        sparsity_cfg = ckks_cfg.get('sparsification', {})
        use_warmup = sparsity_cfg.get('use_warmup_skip_sparse', False)
        warmup_rounds = sparsity_cfg.get('warmup_rounds', 0)
        skip_sparse = use_warmup and (round_num < warmup_rounds)
        if skip_sparse:
            tag_info(LogTag.CLIENT, f"#{self.client_id} warmup round {round_num} | skip sparsification")
        # 将掩码信息传递给 encrypt_model_update，支持 pre_topk 模式
        encrypted_update = ckks_manager.encrypt_model_update(
            model_update, round_num=round_num,
            skip_sparsification=skip_sparse,
            blinding_mask=self.blinding_mask,
            client_mask=self.client_mask,
            client_id=self.client_id,
            global_mask=global_mask,
            global_maser_indices=global_maser_indices,
        )
        self.encryption_time = time.time() - start_time
        # MASER/稀疏模式：plaintext_size 应反映实际加密的参数数量
        if encrypted_update.get('__sparse__'):
            # 使用 total_elements 或 indices 长度计算实际明文大小
            actual_elements = encrypted_update.get('total_elements', len(encrypted_update.get('indices', [])))
            self.plaintext_size = actual_elements * 4
        else:
            self.plaintext_size = sum(p.numel() * 4 for p in model_update.values())
        self.ciphertext_size = ckks_manager.compute_encrypted_update_size(encrypted_update)
        if encrypted_update.get('__sparse__'):
            self.num_ciphertexts = len(encrypted_update['ciphertexts'])
        else:
            self.num_ciphertexts = sum(len(v) for v in encrypted_update.values())
        log_encryption_result(self.client_id, self.encryption_time, self.ciphertext_size, self.num_ciphertexts)
        return encrypted_update
    
    def _clip_model_update(self, model_update: Dict[str, torch.Tensor], 
                           method: str, clip_factor: float) -> Dict[str, torch.Tensor]:
        """
        对模型更新进行逐层裁剪，防止量化溢出 (QuanCrypt-FL 风格 mean-based clipping)。
        
        Args:
            model_update: 模型更新字典
            method: 'layerwise_mean' (每层按均值裁剪) 或 'global_norm' (全局L2裁剪)
            clip_factor: 裁剪倍数 (mean-based: 超过 factor*mean_abs 被裁剪)
        """
        clipped = {}
        if method == 'layerwise_mean':
            for name, tensor in model_update.items():
                mean_abs = tensor.abs().mean().item()
                if mean_abs < 1e-12:
                    clipped[name] = tensor
                    continue
                max_val = clip_factor * mean_abs
                clipped[name] = torch.clamp(tensor, -max_val, max_val)
        elif method == 'global_norm':
            # 计算全局L2 norm，按比例裁剪
            total_norm = 0.0
            for tensor in model_update.values():
                total_norm += tensor.pow(2).sum().item()
            total_norm = total_norm ** 0.5
            if total_norm > 1e-12 and total_norm > clip_factor:
                scale = clip_factor / total_norm
                for name, tensor in model_update.items():
                    clipped[name] = tensor * scale
            else:
                clipped = dict(model_update)
        else:
            clipped = dict(model_update)
        return clipped
    
    def get_weight(self) -> float:
        return float(self.data_size)
    
    def get_stats(self) -> Dict:
        return {
            'client_id': self.client_id,
            'data_size': self.data_size,
            'local_train_time': self.local_train_time,
            'encryption_time': self.encryption_time,
            'plaintext_size': self.plaintext_size,
            'ciphertext_size': self.ciphertext_size
        }


class MaliciousClient(FederatedClient):
    """恶意联邦学习客户端：训练后对模型更新执行攻击"""
    
    def __init__(self, client_id: int, model: nn.Module, train_loader, config: Dict,
                 device: str = "cpu", model_attack=None):
        super().__init__(client_id, model, train_loader, config, device)
        self.model_attack = model_attack
        self.is_malicious = True
        tag_warn(LogTag.CLIENT, f"#{client_id} marked MALICIOUS  |  attack={model_attack.attack_name if model_attack else 'None'}")
    
    def local_train(self, global_params: Optional[Dict[str, torch.Tensor]] = None,
                    encrypted_global_params: Optional[Dict[str, List]] = None
                    ) -> Tuple[Dict[str, torch.Tensor], float, float]:
        model_update, avg_loss, accuracy = super().local_train(global_params, encrypted_global_params)
        # 攻击基于解密后的明文模型更新，global_params 可能为 None（当使用 encrypted_global_params 时）
        effective_params = global_params
        if effective_params is None and encrypted_global_params is not None:
            effective_params = {name: param.data.clone() for name, param in self.model.named_parameters()}
            for name, buf in self.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    effective_params[name] = buf.clone()
        if self.model_attack is not None:
            model_update = self.model_attack.attack(model_update, effective_params)
            tag_warn(LogTag.CLIENT, f"#{self.client_id} ATTACK executed: {self.model_attack.attack_name}")
        return model_update, avg_loss, accuracy


class SimpleClient:
    """简化版联邦学习客户端（用于对比实验）"""
    
    def __init__(self, client_id: int, model: nn.Module, train_loader, config: Dict, device: str = "cpu",
                 blinding_mask=None, client_mask=None):
        self.client_id = client_id
        self.model = model.to(device)
        self.train_loader = train_loader
        self.config = config
        self.device = device
        self.num_epochs = config['system']['num_epochs']
        self.learning_rate = config['system']['learning_rate']
        self.criterion = nn.CrossEntropyLoss()
        
        # ---- 可配置优化器（SGD / Adam）----
        opt_cfg = config.get('system', {}).get('optimizer', {})
        opt_name = opt_cfg.get('name', 'sgd').lower()
        lr = opt_cfg.get('lr', config['system']['learning_rate'])
        
        if opt_name == 'adam':
            self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        elif opt_name == 'adamw':
            self.optimizer = optim.AdamW(self.model.parameters(), lr=lr)
        else:
            momentum = opt_cfg.get('momentum', 0.0)
            self.optimizer = optim.SGD(self.model.parameters(), lr=lr, momentum=momentum)
        
        # ---- 可配置学习率调度器 ----
        sched_cfg = config.get('system', {}).get('lr_scheduler', {})
        self.scheduler = None
        if sched_cfg.get('enabled', False):
            sched_name = sched_cfg.get('name', 'step').lower()
            if sched_name == 'step':
                self.scheduler = optim.lr_scheduler.StepLR(
                    self.optimizer,
                    step_size=sched_cfg.get('step_size', 5),
                    gamma=sched_cfg.get('gamma', 0.5)
                )
            elif sched_name == 'cosine':
                total_epochs = config['system']['num_rounds'] * config['system']['num_epochs']
                self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
                    self.optimizer,
                    T_max=sched_cfg.get('T_max', total_epochs),
                    eta_min=sched_cfg.get('eta_min', 0.0)
                )
            elif sched_name == 'exponential':
                self.scheduler = optim.lr_scheduler.ExponentialLR(
                    self.optimizer,
                    gamma=sched_cfg.get('gamma', 0.95)
                )
            tag_info(LogTag.CLIENT, f"#{self.client_id} scheduler={sched_name}")
        
        self.local_train_time = 0.0
        self.plaintext_size = 0
        self.ciphertext_size = 0
        self.data_size = len(train_loader.dataset)
        self.blinding_mask = blinding_mask
        self.client_mask = client_mask
    
    def local_train(self, global_params: Optional[Dict[str, torch.Tensor]] = None) -> Tuple[Dict[str, torch.Tensor], float, float]:
        start_time = time.time()
        if global_params is not None:
            with torch.no_grad():
                for name, param in self.model.named_parameters():
                    if name in global_params:
                        param.copy_(global_params[name])
                for name, buf in self.model.named_buffers():
                    if name in global_params:
                        buf.copy_(global_params[name])
        old_params = {name: param.data.clone() for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                old_params[name] = buf.clone()
        
        # ---- 梯度裁剪配置 ----
        grad_clip_cfg = self.config.get('system', {}).get('gradient_clipping', {})
        grad_clip_enabled = grad_clip_cfg.get('enabled', False)
        grad_clip_max_norm = grad_clip_cfg.get('max_norm', 1.0)
        
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        for epoch in range(self.num_epochs):
            for data, target in self.train_loader:
                data, target = data.to(self.device), target.to(self.device)
                self.optimizer.zero_grad()
                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()
                # ---- 梯度裁剪 ----
                if grad_clip_enabled:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), grad_clip_max_norm)
                self.optimizer.step()
                total_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()
            # ---- 学习率调度器步进（每个本地 epoch）----
            if self.scheduler is not None:
                self.scheduler.step()
        
        avg_loss = total_loss / (len(self.train_loader) * self.num_epochs)
        accuracy = 100. * correct / total
        
        upload_difference = self.config['system'].get('upload_difference', True)
        if upload_difference:
            model_update = {}
            for name, param in self.model.named_parameters():
                model_update[name] = param.data - old_params[name]
            for name, buf in self.model.named_buffers():
                if name in old_params:
                    model_update[name] = buf.data - old_params[name]
        else:
            model_update = {name: param.data.clone() for name, param in self.model.named_parameters()}
            for name, buf in self.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    model_update[name] = buf.data.clone()
        
        # ---- 可插拔：成对盲化掩码 ----
        if self.blinding_mask is not None and self.client_mask is not None:
            # SimpleClient 没有 round_num 参数，默认用 0
            model_update = self.blinding_mask.apply_mask(model_update, self.client_mask, round_num=0)
        
        self.plaintext_size = sum(p.numel() * 4 for p in model_update.values())
        self.local_train_time = time.time() - start_time
        return model_update, avg_loss, accuracy
    
    def get_weight(self) -> float:
        return float(self.data_size)
    
    def get_stats(self) -> Dict:
        return {
            'client_id': self.client_id,
            'data_size': self.data_size,
            'local_train_time': self.local_train_time,
            'plaintext_size': self.plaintext_size
        }


class MaliciousSimpleClient(SimpleClient):
    """恶意简化客户端（明文实验用）"""
    
    def __init__(self, client_id: int, model: nn.Module, train_loader, config: Dict,
                 device: str = "cpu", model_attack=None):
        super().__init__(client_id, model, train_loader, config, device)
        self.model_attack = model_attack
        self.is_malicious = True
        tag_warn(LogTag.CLIENT, f"#{client_id} marked MALICIOUS (plain)  |  attack={model_attack.attack_name if model_attack else 'None'}")
    
    def local_train(self, global_params: Optional[Dict[str, torch.Tensor]] = None) -> Tuple[Dict[str, torch.Tensor], float, float]:
        model_update, avg_loss, accuracy = super().local_train(global_params)
        if self.model_attack is not None:
            model_update = self.model_attack.attack(model_update, global_params)
            tag_warn(LogTag.CLIENT, f"#{self.client_id} ATTACK executed: {self.model_attack.attack_name}")
        return model_update, avg_loss, accuracy


class PrefetchFederatedClient(FederatedClient):
    """
    支持 CKKS 密文预取的联邦学习客户端。

    核心设计（区别于 FedFetch 的纯服务器模拟）：
    --------------------------------------------------------------------
    1. 【客户端本地缓存】维护 prefetched_state（CKKS 密文累加器）
    2. 【同态加法累加】每轮收到服务器推送的密文 delta，本地执行 `+` 运算累加
    3. 【单次解密】被选中训练时，调用 apply_prefetched_state() 一次性解密并应用
    4. 【带宽信息】从 BandwidthSimulator 注入，用于统计和模拟

    客户端时间线（被选中时）:
        Fetch'（等待预取完成） → Apply（单次解密） → Compute（本地训练） → Upload（上传加密更新）
    客户端时间线（未被选中时）:
        Prefetch（接收密文 delta + 同态累加）
    """

    def __init__(self, client_id: int, model: nn.Module,
                 train_loader, config: Dict, device: str = "cpu",
                 blinding_mask=None, client_mask=None, esafl_adapter=None):
        super().__init__(client_id, model, train_loader, config, device,
                         blinding_mask=blinding_mask, client_mask=client_mask)

        prefetch_cfg = config.get('prefetch', {})
        self.enable_prefetch = prefetch_cfg.get('enable_prefetch', True)
        
        # ---- ESAFL 适配器（可插拔）----
        self.esafl_adapter = esafl_adapter
        self.esafl_enabled = esafl_adapter is not None

        # ---------- 本地密文缓存 ----------
        self.prefetched_state = None      # {layer_name: [CKKSVector, ...]}
        self.last_synced_round = 0        # 上次同步全局模型的轮次（由服务器维护，客户端参考）
        self.num_prefetch_deltas = 0      # 间隙预取接收的 delta 数
        self.num_fetch_deltas = 0         # Fetch 阶段接收的 delta 数
        self.num_prefetched_deltas = 0    # 已累加的预取增量数（deprecated，保留兼容）
        self.received_delta_rounds = []   # 已接收的 delta 来自哪些轮次（用于调试追踪）

        # ---------- Base Model（上一次被选中时的全局模型） ----------
        self.base_model_state = None      # {name: Tensor(CPU)}，训练前重置的目标状态

        # ---------- 带宽信息（外部注入） ----------
        self.dl_bandwidth_kbps = 0.0      # 下行带宽 (kbps)
        self.ul_bandwidth_kbps = 0.0      # 上行带宽 (kbps)

        # ---------- CKKS 管理器（统一密钥，外部注入） ----------
        self.ckks_manager = None

        # ---------- PTopk 残差状态追踪 ----------
        self._ptopk_last_trained_round = -1   # 上次执行本地训练的轮次（用于判断是否连续参与）

        # ---------- FedPHE 本地补全（local completion）----------
        sparsity_cfg = config.get('ckks', {}).get('sparsification', {})
        self.local_completion_enabled = sparsity_cfg.get('local_completion', {}).get('enabled', True)
        # 上一轮训练产生的完整本地 delta（未稀疏化），用于下轮全局稀疏更新为 0 的位置补全
        self.last_local_full_delta = None
        if self.local_completion_enabled:
            tag_info(LogTag.CLIENT, f"#{client_id} local_completion ENABLED")
        else:
            tag_info(LogTag.CLIENT, f"#{client_id} local_completion DISABLED (legacy reset-to-base)")

        # ---------- 统计指标 ----------
        # 单轮统计（每轮结束后 reset_round_stats 清零，用于 metrics 记录）
        self.prefetch_download_cost = 0   # 本轮预取下载量 (bytes)
        self.fetch_download_cost = 0      # 本轮 Fetch 阶段下载量 (bytes)
        # 累计统计（跨轮次累加，不清零，用于实验结束时的最终统计表）
        self.total_prefetch_download_cost = 0  # 累计预取下载量 (bytes)
        self.total_fetch_download_cost = 0     # 累计 Fetch 下载量 (bytes)
        self.prefetch_time = 0.0          # 同态累加耗时 (s)
        self.prefetch_download_time = 0.0 # 预取阶段理论下载耗时 (s)（由 bandwidth_simulator 计算）
        self.fetch_time = 0.0             # Fetch 下载耗时 (s)
        self.apply_time = 0.0             # 解密应用耗时 (s)

        tag_info(LogTag.CLIENT, f"#{client_id} PrefetchClient init  |  enable={self.enable_prefetch}")

    def _ensure_ckks_vectors(self, ciphertexts):
        """将序列化的 bytes 反序列化为 CKKSVector 对象（兼容 TEE 路径）"""
        if self.ckks_manager is None or not ciphertexts:
            return ciphertexts
        if isinstance(ciphertexts[0], bytes):
            ctx = self.ckks_manager.context.context
            return [ts.CKKSVector.load(ctx, c) for c in ciphertexts]
        return ciphertexts

    def _replace_prefetched_state(self, prefetched_state: Dict, new_delta: Dict) -> Dict:
        """
        用新 delta 覆盖/合并到 prefetched_state。
        
        关键修复：服务器发送的是合并后的最新值（已包含旧值 + 新 delta），
        客户端应当执行"覆盖替换"而非"同态累加"。
        
        逻辑：
          - 新 delta 在 mask=1 的位置：用新值替换旧值（新值已是最新合并值）
          - 新 delta 在 mask=0 的位置：保留 prefetched_state 中的旧值
          - 两者都 mask=0：mask[i] 保持 0（必须保留完整长度！）
        """
        old_mask = prefetched_state['mask']
        new_mask = new_delta['mask']
        old_cts = prefetched_state['ciphertexts']
        new_cts = new_delta['ciphertexts']
        
        # mask 长度必须一致，否则 batch 索引会错位
        if len(old_mask) != len(new_mask):
            raise ValueError(
                f"[Prefetch] Mask length mismatch: old={len(old_mask)} vs new={len(new_mask)}"
            )
        
        result_cts = []
        # CRITICAL FIX: 必须保留完整 mask 长度（含 0），否则 decrypt_model_update
        # 按 mask 循环补零时会丢失 batch，导致 all_values 长度不足
        result_mask = [0] * len(old_mask)
        old_idx = 0
        new_idx = 0
        
        for i in range(len(old_mask)):
            has_old = old_mask[i]
            has_new = new_mask[i]
            if has_new:
                # 服务器发送的是合并后的最新值，直接替换
                result_cts.append(new_cts[new_idx])
                result_mask[i] = 1
                new_idx += 1
                if has_old:
                    old_idx += 1
            elif has_old:
                result_cts.append(old_cts[old_idx])
                result_mask[i] = 1
                old_idx += 1
            # else: both 0, result_mask[i] 保持 0
        
        # 不变量检查
        if len(result_cts) != sum(result_mask):
            raise ValueError(
                f"[Prefetch] Invariant violated: cts={len(result_cts)} != sum(mask)={sum(result_mask)}"
            )
        if old_idx != sum(old_mask):
            raise ValueError(
                f"[Prefetch] Old index mismatch: {old_idx} != {sum(old_mask)}"
            )
        if new_idx != sum(new_mask):
            raise ValueError(
                f"[Prefetch] New index mismatch: {new_idx} != {sum(new_mask)}"
            )
        
        return {
            '__sparse__': True,
            'ciphertexts': result_cts,
            'mask': result_mask,
            'batch_size': prefetched_state['batch_size'],
            'total_elements': prefetched_state['total_elements'],
            'shapes': prefetched_state['shapes'],
            'offsets': prefetched_state['offsets'],
            'packing_metadata': prefetched_state.get('packing_metadata'),
        }

    # ==================================================================
    # 预取接口：接收单个密文 delta 并覆盖合并
    # ==================================================================
    def receive_prefetch_delta(self, encrypted_delta: Dict, delta_size: int, from_round: int):
        """
        接收服务器推送的密文增量（已合并为最新值），本地覆盖合并到 prefetched_state。
        （FedPHE 对齐：统一 __sparse__ 格式）
        """
        if not self.enable_prefetch or encrypted_delta is None:
            return
        if not encrypted_delta.get('__sparse__'):
            raise ValueError("预取 delta 必须使用 __sparse__ 格式（FedPHE 对齐）")

        fetch_start = time.time()

        # 反序列化 bytes（TEE 路径返回序列化密文）
        ciphertexts = self._ensure_ckks_vectors(encrypted_delta['ciphertexts'])
        encrypted_delta_loaded = dict(encrypted_delta)
        encrypted_delta_loaded['ciphertexts'] = ciphertexts

        if self.prefetched_state is None:
            self.prefetched_state = {
                '__sparse__': True,
                'ciphertexts': list(ciphertexts),
                'mask': list(encrypted_delta['mask']),
                'batch_size': encrypted_delta['batch_size'],
                'total_elements': encrypted_delta['total_elements'],
                'shapes': encrypted_delta['shapes'],
                'offsets': encrypted_delta['offsets'],
                'packing_metadata': encrypted_delta.get('packing_metadata'),
            }
        else:
            # FIX: 服务器发送合并值，客户端用覆盖而非累加
            self.prefetched_state = self._replace_prefetched_state(
                self.prefetched_state, encrypted_delta_loaded
            )

        self.prefetch_download_cost += delta_size
        self.total_prefetch_download_cost += delta_size
        self.num_prefetch_deltas += 1
        self.num_prefetched_deltas += 1
        self.received_delta_rounds.append(from_round)
        self.prefetch_time += time.time() - fetch_start

    # ==================================================================
    # Fetch 阶段：被选中时下载剩余密文并累加
    # ==================================================================
    def fetch_remaining_deltas(self, fetch_info: Dict, bandwidth_simulator=None):
        """
        训练轮 Fetch 阶段：下载服务器推送的"剩余没能预取到的密文增量"，
        并同态累加到本地缓存。

        Args:
            fetch_info: {
                'count': 剩余 delta 数量,
                'total_size': 总字节数,
                'deltas': [delta_dict, ...]  # 所有需要 fetch 的密文增量列表
            }
            bandwidth_simulator: BandwidthSimulator，用于计算理论下载时间
        """
        if not self.enable_prefetch or fetch_info is None:
            return

        count = fetch_info['count']
        total_size = fetch_info['total_size']
        deltas = fetch_info['deltas']

        # ---- 2a) 模拟下载时间（网络耗时） ----
        total_size_bits = total_size * 8
        if bandwidth_simulator:
            self.fetch_time += bandwidth_simulator.estimate_download_time(
                self.client_id, total_size_bits
            )
        # 注：SIMULATION_MODE 下不执行真实网络 I/O，fetch_time 是理论值

        # ---- 2b) 同态累加（CPU 计算） ----
        t0 = time.time()
        for delta_dict in deltas:
            delta_ct = delta_dict['delta']
            delta_size = delta_dict['size']
            if not delta_ct.get('__sparse__'):
                raise ValueError("fetch delta 必须使用 __sparse__ 格式（FedPHE 对齐）")
            # 反序列化 bytes（TEE 路径返回序列化密文）
            delta_ct_loaded = dict(delta_ct)
            delta_ct_loaded['ciphertexts'] = self._ensure_ckks_vectors(delta_ct['ciphertexts'])

            if self.prefetched_state is None:
                self.prefetched_state = {
                    '__sparse__': True,
                    'ciphertexts': list(delta_ct_loaded['ciphertexts']),
                    'mask': list(delta_ct['mask']),
                    'batch_size': delta_ct['batch_size'],
                    'total_elements': delta_ct['total_elements'],
                    'shapes': delta_ct['shapes'],
                    'offsets': delta_ct['offsets'],
                    'packing_metadata': delta_ct.get('packing_metadata'),
                }
            else:
                # FIX: 服务器发送合并值，客户端用覆盖而非累加
                self.prefetched_state = self._replace_prefetched_state(
                    self.prefetched_state, delta_ct_loaded
                )
            self.fetch_download_cost += delta_size
            self.total_fetch_download_cost += delta_size
            self.num_fetch_deltas += 1
            self.num_prefetched_deltas += 1
            from_round = delta_dict.get('from_round', '?')
            if isinstance(from_round, str) and '..' in from_round:
                self.received_delta_rounds.append(from_round)
            else:
                self.received_delta_rounds.append(from_round)

        self.prefetch_time += time.time() - t0

    # ==================================================================
    # 训练前接口：解密并应用累加的预取状态
    # ==================================================================
    def apply_prefetched_state(self, is_warmup: bool = False, current_round: int = None):
        """
        训练前调用：将本地累加的密文状态一次性解密为明文增量，并加到 base model 上。

        这是 CKKS 预取方案的核心：无论预取了多少轮的增量，
        客户端只需执行**一次解密**即可得到累积的明文更新，然后加到 base model。
        
        关键 invariant: apply 后，self.model 变为最新全局模型（不含本地梯度）。
        
        Args:
            is_warmup: 是否为 warmup 阶段。warmup 期间日志使用 "sync_model" 而非 "apply_prefetch"
        """
        if not self.enable_prefetch or self.prefetched_state is None:
            return

        if self.ckks_manager is None:
            raise RuntimeError(f"Client {self.client_id}: ckks_manager not injected")

        apply_start = time.time()

        # 1. 解密累加后的密文状态 → 明文增量
        shapes = {name: param.shape for name, param in self.model.named_parameters()}
        for name, buf in self.model.named_buffers():
            if 'running_mean' in name or 'running_var' in name:
                shapes[name] = buf.shape

        if self.esafl_enabled:
            # ESAFL 扩展解密（SIMULATION 模式下退化为普通解密）
            decrypted_delta = self.esafl_adapter.extended_decrypt(
                self.prefetched_state, shapes,
                rounds_list=self.received_delta_rounds if self.received_delta_rounds else None,
            )
        else:
            decrypted_delta = self.ckks_manager.decrypt_model_update(
                self.prefetched_state, shapes
            )

        # 2. 确定 base model：如果存在 base_model_state，从其开始累加；否则从当前模型开始
        if self.base_model_state is not None:
            base_params = {k: v.to(self.device) for k, v in self.base_model_state.items()}
        else:
            base_params = self.get_model_params()

        # 3. 累加全局 delta，并根据配置决定是否执行本地补全
        if self.local_completion_enabled:
            new_params = {}
            completion_logged = False
            for name in base_params:
                if name in decrypted_delta:
                    global_delta = decrypted_delta[name].to(self.device)
                    # 基础：base + global_delta（全局聚合部分）
                    completed = base_params[name] + global_delta

                    # --- 本地补全：global_delta ~ 0 的位置用上一轮本地训练值填充 ---
                    if (self.last_local_full_delta is not None
                            and name in self.last_local_full_delta):
                        local_delta = self.last_local_full_delta[name].to(self.device)
                        # 上一轮训练后的本地值 = base_params + local_delta
                        # base_params 是 local_delta 的基准点（训练前的全局状态）
                        local_val = base_params[name] + local_delta

                        # CKKS 同态累加后，未选中 batch 的解密值接近 0 但可能有 ~1e-3 噪声
                        mask = torch.abs(global_delta) < 1e-3
                        if mask.any():
                            completed = torch.where(mask, local_val, completed)
                            if not completion_logged and not is_warmup:
                                ratio = mask.float().mean().item()
                                tag_info(LogTag.CLIENT,
                                         f"#{self.client_id} local_completion | layer={name} | "
                                         f"ratio={ratio:.2%} | round={current_round}")
                                completion_logged = True

                    new_params[name] = completed
                else:
                    new_params[name] = base_params[name]

            self.set_model_params(new_params)
            # 更新 base_model_state 为补全后的模型（供下次预取/训练使用）
            self.base_model_state = {k: v.cpu().clone() for k, v in new_params.items()}
            # 本地补全已融入 base，清空上一轮 delta
            self.last_local_full_delta = None
        else:
            # 禁用本地补全：回退到旧行为（纯净全局模型，不含本地更新）
            new_params = {}
            for name in base_params:
                if name in decrypted_delta:
                    delta_tensor = decrypted_delta[name].to(self.device)
                    new_params[name] = base_params[name] + delta_tensor
                else:
                    new_params[name] = base_params[name]
            self.set_model_params(new_params)
            self.base_model_state = {k: v.cpu().clone() for k, v in new_params.items()}
            self.last_local_full_delta = None

        # 记录日志（在清空统计前）
        rounds_str = str(self.received_delta_rounds) if self.received_delta_rounds else "[]"
        num_deltas = self.num_prefetch_deltas + self.num_fetch_deltas

        # 4. 清空预取缓存（已应用，避免重复累加）
        self.prefetched_state = None
        self.num_prefetch_deltas = 0
        self.num_fetch_deltas = 0
        self.num_prefetched_deltas = 0
        self.received_delta_rounds.clear()
        if is_warmup:
            tag_info(LogTag.CLIENT,
                     f"#{self.client_id} sync_model  |  deltas={num_deltas}  |  "
                     f"rounds={rounds_str}  |  sync_time={time.time() - apply_start:.4f}s  |  "
                     f"[warmup：同步缺失更新到最新全局模型]")
        else:
            tag_info(LogTag.CLIENT,
                     f"#{self.client_id} apply_prefetch  |  deltas={num_deltas}  |  "
                     f"rounds={rounds_str}  |  apply_time={time.time() - apply_start:.4f}s")

        # 5. 清空缓存，释放内存
        self.prefetched_state = None
        self.num_prefetch_deltas = 0
        self.num_fetch_deltas = 0
        self.num_prefetched_deltas = 0
        self.received_delta_rounds = []
        self.apply_time += time.time() - apply_start

        # 5. PTopk: 根据客户端是否连续参与，决定是否衰减残差
        #    连续参与（gap=1）：保留残差，让它继续叠加
        #    跨轮参与（gap>1）：按 stale_gamma^(gap-1) 衰减陈旧残差
        if (self.ckks_manager is not None and
            hasattr(self.ckks_manager, 'ptopk') and
            self.ckks_manager.ptopk.client_residual_enabled):
            
            last_round = self._ptopk_last_trained_round
            # local_train 会在训练后更新 last_round，因此首次训练前 last_round=-1
            if last_round >= 0 and current_round is not None:
                gap = current_round - last_round
                if gap > 1:
                    # 跨轮：陈旧残差衰减
                    self.ckks_manager.ptopk.decay_residual_by_gap(gap)
                    tag_info(LogTag.CLIENT,
                             f"#{self.client_id} PTopk residual DECAY | gap={gap} | last=R{last_round}")
                else:
                    # 连续参与：保留残差
                    tag_info(LogTag.CLIENT,
                             f"#{self.client_id} PTopk residual KEEP | continuous | last=R{last_round}")
            else:
                tag_info(LogTag.CLIENT,
                         f"#{self.client_id} PTopk residual INIT | first training")

    # ==================================================================
    # 本地训练重写：先 Apply，再 Compute
    # ==================================================================
    def local_train(self, current_round: int = 0,
                    fetch_info: Dict = None, bandwidth_simulator=None,
                    global_params: Optional[Dict[str, torch.Tensor]] = None,
                    encrypted_global_params: Optional[Dict[str, List]] = None,
                    is_warmup: bool = False
                    ) -> Tuple[Dict[str, torch.Tensor], float, float]:
        """
        被选中时的完整训练流程（FedFetch 风格，含 FedPHE 本地补全）。

        核心 invariant（本地补全版本）：
        训练后客户端模型**保留**本地训练值（不重置为 base）。
        只有 base_model_state 记录纯净的全局模型起点，供下轮计算上传 delta。
        下轮 apply_prefetched_state 时，全局稀疏 delta 为 0 的位置会自动用
        本轮保留的本地值补全，从而避免 TopK 导致的信息丢失和 BN 失配。

        Args:
            current_round:       当前服务器轮次（用于状态追踪）
            fetch_info:          剩余密文信息（见 fetch_remaining_deltas）
            bandwidth_simulator: 用于计算 fetch 下载时间
            global_params:       兼容父类接口（PrefetchClient 忽略，使用 base_model_state）
            encrypted_global_params: 兼容父类接口（PrefetchClient 忽略）
            is_warmup:           是否为 warmup 阶段。warmup 期间日志使用 "sync" 而非 "fetch/apply"
        """
        if global_params is not None or encrypted_global_params is not None:
            logger.warning(
                f"Client {self.client_id}: PrefetchFederatedClient ignores "
                f"global_params/encrypted_global_params (uses base_model_state + prefetch). "
                f"Call via current_round=..., fetch_info=... instead."
            )

        # Step 1: Fetch 剩余 delta（预取未覆盖的部分）
        self.fetch_remaining_deltas(fetch_info, bandwidth_simulator)

        # Step 2: Apply（单次解密 prefetch + fetch 的全部密文，加到 base model）
        self.apply_prefetched_state(is_warmup=is_warmup, current_round=current_round)

        # Step 3: 保存 apply 后的全局模型（作为 base model）
        base_after_apply = self.get_model_params()

        # Step 4: Compute（标准训练，从最新全局模型开始）
        update, loss, acc = super().local_train(global_params=None, round_num=current_round)

        if self.local_completion_enabled:
            # Step 4b: 计算纯净本地完整 delta（不受盲化掩码影响）
            new_params = self.get_model_params()
            local_full_delta = {name: new_params[name] - base_after_apply[name]
                                for name in base_after_apply}

            # Step 5: FedPHE 本地补全——保留训练后模型，不重置为 base
            # 全局稀疏更新为 0 的位置，下轮 apply_prefetched_state 时会用本地值补全
            self.base_model_state = {k: v.cpu().clone() for k, v in base_after_apply.items()}
            self.last_local_full_delta = {k: v.cpu().clone() for k, v in local_full_delta.items()}
        else:
            # 禁用本地补全：回退到旧行为（训练后重置为 base，丢弃本地梯度）
            self.set_model_params(base_after_apply)
            self.base_model_state = {k: v.cpu().clone() for k, v in base_after_apply.items()}
            self.last_local_full_delta = None

        self.last_synced_round = current_round

        # 记录本轮训练轮次，供下次判断是否连续参与
        self._ptopk_last_trained_round = current_round

        return update, loss, acc

    # ==================================================================
    # 统计接口
    # ==================================================================
    def get_prefetch_stats(self) -> Dict:
        """返回预取相关统计指标（包含单轮值和累计值）"""
        return {
            'client_id': self.client_id,
            # 单轮值（用于 metrics 记录）
            'prefetch_download_cost': self.prefetch_download_cost,
            'fetch_download_cost': self.fetch_download_cost,
            'total_download_cost': self.prefetch_download_cost + self.fetch_download_cost,
            # 累计值（用于实验结束统计）
            'total_prefetch_download_cost': self.total_prefetch_download_cost,
            'total_fetch_download_cost': self.total_fetch_download_cost,
            'total_download_cost_cumulative': self.total_prefetch_download_cost + self.total_fetch_download_cost,
            'num_prefetch_deltas': self.num_prefetch_deltas,
            'num_fetch_deltas': self.num_fetch_deltas,
            'num_prefetched_deltas': self.num_prefetched_deltas,
            'last_synced_round': self.last_synced_round,
            'has_pending_prefetch': self.prefetched_state is not None,
            'prefetch_time': self.prefetch_time,
            'prefetch_download_time': self.prefetch_download_time,
            'fetch_time': self.fetch_time,
            'apply_time': self.apply_time,
            'dl_bw_kbps': self.dl_bandwidth_kbps,
            'ul_bw_kbps': self.ul_bandwidth_kbps,
        }

    def reset_round_stats(self):
        """每轮结束后重置单轮统计"""
        self.prefetch_time = 0.0
        self.prefetch_download_time = 0.0
        self.fetch_time = 0.0
        self.apply_time = 0.0
        self.prefetch_download_cost = 0
        self.fetch_download_cost = 0
        self.received_delta_rounds = []
