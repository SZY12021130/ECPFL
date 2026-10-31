"""
ESAFL-Style Crypto Adapter for TenSEAL / Multi-Key CKKS
========================================================

本模块提供 ESAFL 协议的协议级适配，支持两种模式：

SIMULATION 模式（默认）：
  - 由于 TenSEAL 不原生支持 ESAFL 的多密钥注入（a * s_i），
    采用协议级模拟：底层仍使用标准单密钥 CKKS（TenSEAL 原生），
    所有 N 个客户端共享同一个 CKKS context（含 sk）。
  - 通过全局掩码投票 + 全客户端密文补齐模拟 ESAFL 的全参与聚合。
  - 预取 delta = C^(r) - C^(r-1) 可跨轮累加，客户端本地 sk 解密。

NATIVE 模式：
  - 使用项目根目录下 esafl_eshe 包中的真实多密钥 CKKS 后端。
  - 底层为 MASER 的 xMK-CKKS Go 动态库（xmkckks.dll），通过 ctypes 暴露给 Python。
  - 每个客户端持有独立私钥 s_i；服务器聚合各客户端公钥得到联合公钥 P。
  - 客户端用联合公钥加密本地更新，服务器通过同态加法聚合，
    再收集各客户端的 partial decrypt 份额解码明文聚合结果。
  - NATIVE 模式下，加密 / 聚合 / 解密由 CKKSManager 直接调用 ESHEManager 完成，
    本适配器主要保留 SIMULATION 模式下的 delta 计算与扩展解密逻辑。

密钥管理（SIMULATION）：
  - KGC 生成标准 CKKS 密钥对 (pk, sk)
  - sk 分发给所有客户端（ESAFL 风格：所有客户端共享解密密钥）
  - 服务器只持有 pk（无法单独解密）

与盲化掩码的关系：
  - 如果启用 blinding_mask，客户端间保密性由成对掩码保证
  - 如果关闭 blinding_mask，客户端可以解密其他客户端的单个密文（当 |S_r|=1 时）
  - 建议：cross-silo 场景下保持 blinding_mask 启用
"""

import numpy as np
import torch
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ESAFLKeyManager:
    """
    ESAFL 风格密钥管理器。

    在当前 TenSEAL 模拟实现中：
      - 所有客户端共享同一个 CKKS context（含 sk）
      - 未来可扩展为真正的多密钥 ESHE（需修改 TenSEAL C++ 绑定）
    """

    def __init__(self, ckks_manager):
        """
        Args:
            ckks_manager: CKKSManager 实例（TenSEAL 单密钥上下文）
        """
        self.ckks_manager = ckks_manager
        # 在模拟模式下，所有客户端共享同一个加密器/解密器
        self.encryptor = ckks_manager.encryptor if hasattr(ckks_manager, 'encryptor') else None
        self.decryptor = ckks_manager.decryptor if hasattr(ckks_manager, 'decryptor') else None

    def client_encrypt(self, plaintext_chunks: List[np.ndarray]) -> List[Any]:
        """客户端加密（使用共享 pk）。"""
        return self.ckks_manager.encryptor.encrypt_chunks(plaintext_chunks)

    def client_decrypt(self, ciphertexts: List[Any]) -> List[np.ndarray]:
        """客户端解密（使用共享 sk）。"""
        return self.ckks_manager.decryptor.decrypt_chunks(ciphertexts)


class ESAFLAggregator:
    """
    ESAFL 风格聚合器：支持全客户端密文聚合（含零密文补齐）。
    """

    @staticmethod
    def aggregate_with_zeros(
        encrypted_updates: List[Dict[str, Any]],
        client_weights: List[float],
        ckks_manager,
        global_mask: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        聚合客户端密文更新，支持全局掩码对齐。

        Args:
            encrypted_updates: 客户端上传的加密更新列表（含未采样客户端的零密文）
            client_weights: 客户端权重列表
            ckks_manager: CKKSManager 实例
            global_mask: 全局掩码（可选，用于日志）

        Returns:
            聚合后的加密更新（与 ckks_manager.aggregate_encrypted_updates 格式一致）
        """
        # 复用现有的同态聚合逻辑
        total_weight = sum(client_weights)
        normalized_weights = [w / total_weight for w in client_weights]

        aggregated = ckks_manager.aggregate_encrypted_updates(
            encrypted_updates, normalized_weights
        )

        active_batches = int(global_mask.sum()) if global_mask is not None else "N/A"
        logger.info(
            f"ESAFL aggregate | clients={len(encrypted_updates)} | "
            f"active_batches={active_batches} | weights_sum={total_weight:.2f}"
        )
        return aggregated

    @staticmethod
    def compute_delta(
        current_global: Dict[str, Any],
        previous_global: Dict[str, Any],
        ckks_manager,
    ) -> Dict[str, Any]:
        """
        计算两轮全局密文之间的 delta：δ^(r) = C^(r) - C^(r-1)。

        这是 ESAFL 预取机制的核心：delta 密文可跨轮累加，
        客户端通过扩展解密恢复累积梯度。
        """
        return ckks_manager.subtract_encrypted_updates(current_global, previous_global)


class ESAFLAdapter:
    """
    ESAFL 协议适配器（可插拔）。

    在 SIMULATION 模式下：
      - 所有客户端共享同一个 TenSEAL 密钥
      - 扩展解密退化为普通 CKKS 解密（因为单密钥无需 Delta_a 校正）
      - 服务器用密文同态减法计算 delta（省去明文差值+重新加密的开销）

    在 NATIVE 模式下：
      - 每个客户端持有独立的 s_i（由 esafl_eshe.ESHEManager 管理）
      - 服务器聚合密文后需收集参与客户端的 partial decrypt 份额才能解码
      - 真实多密钥加密 / 聚合 / 解密由 CKKSManager 通过 ESHEManager 执行，
        本适配器保留 delta 计算接口以兼容预取逻辑（当前与 SIMULATION 共享）

    Args:
        ckks_manager: CKKSManager 实例
        mode: "SIMULATION" | "NATIVE"
        prpg_seed: PRPG 种子（SIMULATION 模式下保留）
    """

    def __init__(self, ckks_manager, mode: str = "SIMULATION", prpg_seed: int = 42):
        self.ckks_manager = ckks_manager
        self.mode = mode
        self.prpg_seed = prpg_seed
        
        # 协议状态
        self.previous_global_enc = None  # C^(r-1)
        self.current_round = 0
        
        # Delta_a 累积（SIMULATION 模式下未使用，保留用于 NATIVE 扩展）
        self.delta_a_accumulated = None
        
        self.key_manager = ESAFLKeyManager(ckks_manager)
        self.aggregator = ESAFLAggregator()
        
        logger.info(f"ESAFLAdapter initialized | mode={mode} | prpg_seed={prpg_seed}")

    def is_enabled(self) -> bool:
        """检查 ESAFL 是否处于启用状态（总是 True，由外部配置控制是否注入）。"""
        return True

    def on_round_start(self, round_num: int):
        """每轮开始时调用，更新轮次计数。"""
        self.current_round = round_num

    def on_global_updated(self, encrypted_global_state: Dict[str, Any]):
        """
        全局模型更新后调用。
        
        保存当前全局密文状态，用于下一轮计算 delta。
        注意：应在 update_global_model 之后、计算 delta 之前调用。
        """
        self.previous_global_enc = encrypted_global_state

    def compute_delta_encrypted(
        self,
        current_global_enc: Dict[str, Any],
        previous_global_enc: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        计算加密 delta：δ^(r) = C^(r) - C^(r-1)。
        
        如果 previous_global_enc 为 None（第一轮），返回 None。
        
        Args:
            current_global_enc: 当前轮次的全局密文状态 C^(r)
            previous_global_enc: 上一轮的全局密文状态 C^(r-1)
        
        Returns:
            delta 密文（__sparse__ 格式）或 None
        """
        prev = previous_global_enc or self.previous_global_enc
        if prev is None:
            logger.info("ESAFL delta: first round, no previous global state")
            return None
        
        delta = self.aggregator.compute_delta(current_global_enc, prev, self.ckks_manager)
        active = sum(delta['mask'])
        total = len(delta['mask'])
        logger.info(
            f"ESAFL delta computed | batches={active}/{total} | "
            f"round={self.current_round}"
        )
        return delta

    def extended_decrypt(
        self,
        encrypted_state: Dict[str, Any],
        original_shapes: Dict[str, torch.Size],
        rounds_list: Optional[List[int]] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        ESAFL 扩展解密。
        
        SIMULATION 模式下：退化为普通 CKKS 解密（单密钥无需 Delta_a 校正）。
        
        NATIVE 模式下（未来扩展）：
          Delta_a = sum(a^{(r_j)} - a^{(r_{j-1})}) for j in rounds_list
          执行 [[ct - Delta_a * s]_q]_p
        
        Args:
            encrypted_state: 密文状态（__sparse__ 格式）
            original_shapes: 原始参数形状
            rounds_list: 参与累积的轮次列表（NATIVE 模式用）
        
        Returns:
            解密后的明文参数字典
        """
        if self.mode == "SIMULATION":
            # SIMULATION: 单密钥，直接解密
            return self.ckks_manager.decrypt_model_update(encrypted_state, original_shapes)
        
        # NATIVE 模式（未来扩展）
        # TODO: 实现真正的扩展解密（需要访问 TenSEAL 内部多项式）
        raise NotImplementedError(
            "NATIVE mode extended_decrypt requires multi-key CKKS support"
        )

    def get_stats(self) -> Dict[str, Any]:
        """返回 ESAFL 协议统计信息。"""
        return {
            'mode': self.mode,
            'current_round': self.current_round,
            'has_previous_global': self.previous_global_enc is not None,
            'prpg_seed': self.prpg_seed,
        }
