"""
CKKS同态加密工具封装模块
基于TenSEAL库实现CKKS方案的封装
"""

import tenseal as ts
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Any
import logging
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ckks_fed.packing import (
    PackingStrategy, PackingMetadata,
    LayerwisePacking, MergedPacking, ConjugatePacking,
    CRTStackPacking, ESAFLPacking,
    create_packing_strategy,
)
from ckks_fed.sparsification import (
    SparsificationStrategy, NoSparsification,
    create_sparsification_strategy,
)
from ckks_fed.ptopk import PTopkModule, PTopkWrappedStrategy

try:
    from esafl_eshe import ESHEManager, ESAFL_ESHE_AVAILABLE
except Exception:  # pragma: no cover
    ESAFL_ESHE_AVAILABLE = False
    ESHEManager = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def aes_generate_key() -> bytes:
    """生成256-bit AES-GCM密钥"""
    return AESGCM.generate_key(bit_length=256)


def aes_encrypt_params(params: Dict[str, torch.Tensor], key: bytes) -> Dict:
    """用AES-GCM加密模型参数字典"""
    aesgcm = AESGCM(key)
    ciphertexts = {}
    metadata = {}
    for name, param in params.items():
        shape = list(param.shape)
        flat = param.detach().cpu().numpy().astype(np.float32).tobytes()
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, flat, None)
        ciphertexts[name] = ct
        metadata[name] = {'shape': shape, 'nonce': nonce.hex()}
    return {'ciphertexts': ciphertexts, 'metadata': metadata}


def aes_decrypt_params(package: Dict, key: bytes) -> Dict[str, torch.Tensor]:
    """用AES-GCM解密模型参数字典"""
    aesgcm = AESGCM(key)
    params = {}
    for name, ct in package['ciphertexts'].items():
        meta = package['metadata'][name]
        nonce = bytes.fromhex(meta['nonce'])
        flat_bytes = aesgcm.decrypt(nonce, ct, None)
        flat_arr = np.frombuffer(flat_bytes, dtype=np.float32)
        params[name] = torch.tensor(flat_arr.reshape(meta['shape']))
    return params


class CKKSContext:
    """CKKS上下文管理器 - 封装TenSEAL的CKKSContext"""
    
    def __init__(self, poly_modulus_degree: int = 8192,
                 coeff_mod_bit_sizes: List[int] = None,
                 global_scale: float = 2**20):
        """
        初始化CKKS上下文
        
        Args:
            poly_modulus_degree: 多项式模数度 (1024, 2048, 4096, 8192, 16384)
            coeff_mod_bit_sizes: 系数模数比特大小列表
            global_scale: 全局缩放因子
        """
        if coeff_mod_bit_sizes is None:
            coeff_mod_bit_sizes = [40, 20, 40]
        
        self.poly_modulus_degree = poly_modulus_degree
        self.coeff_mod_bit_sizes = coeff_mod_bit_sizes
        self.global_scale = global_scale
        
        # 创建TenSEAL上下文
        self.context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes
        )
        
        # 设置全局缩放因子
        self.context.global_scale = global_scale
        
        # 启用自动重新线性化
        self.context.auto_relin = True
        
        # 启用自动模数切换
        self.context.auto_mod_switch = True
        
        # 生成Galois密钥（支持密文旋转操作）
        self.context.generate_galois_keys()
        
        logger.info(f"CKKS上下文创建成功: N={poly_modulus_degree}, "
                   f"mod_bits={coeff_mod_bit_sizes}, scale={global_scale}")
    
    def get_context_bytes(self) -> bytes:
        """序列化上下文（用于传输公钥信息）"""
        return self.context.serialize(save_public_key=True, save_secret_key=False)
    
    def get_secret_context_bytes(self) -> bytes:
        """序列化完整上下文（包含私钥，仅用于可信辅助节点）"""
        return self.context.serialize(save_public_key=True, save_secret_key=True)
    
    def get_full_context_bytes(self) -> bytes:
        """序列化完整上下文（包含私钥，用于统一密钥模型的客户端分发）"""
        return self.context.serialize(save_public_key=True, save_secret_key=True,
                                       save_galois_keys=True, save_relin_keys=True)
    
    @classmethod
    def from_bytes(cls, context_bytes: bytes):
        """从字节反序列化上下文"""
        context = ts.context_from(context_bytes)
        obj = cls.__new__(cls)
        obj.context = context
        return obj
    
    @classmethod
    def from_full_bytes(cls, context_bytes: bytes, poly_modulus_degree: int = 8192):
        """从字节反序列化完整上下文（恢复所有密钥）
        
        Args:
            context_bytes: 序列化的上下文字节
            poly_modulus_degree: 多项式模数度（TenSEAL反序列化后无法直接读取，需外部传入）
        """
        context = ts.context_from(context_bytes)
        obj = cls.__new__(cls)
        obj.context = context
        obj.poly_modulus_degree = poly_modulus_degree
        obj.coeff_mod_bit_sizes = []  # 反序列化后无法直接读取，留空表示未知
        obj.global_scale = getattr(context, 'global_scale', 2**20)
        return obj
    
    def get_noise_budget(self, ciphertext) -> float:
        """
        获取密文的噪声预算（近似估计）
        
        Args:
            ciphertext: CKKS密文
        
        Returns:
            噪声预算（比特）
        """
        try:
            total_bits = sum(self.coeff_mod_bit_sizes)
            return total_bits * 0.8
        except Exception as e:
            logger.warning(f"噪声预算估计失败: {e}")
            return 0.0


class CKKSEncryptor:
    """CKKS加密器 - 处理明文加密"""
    
    def __init__(self, context: CKKSContext, slot_count: int = None):
        self.context = context
        # CKKS slot 数量 = poly_modulus_degree // 2
        self.slot_count = slot_count or (context.poly_modulus_degree // 2)
    
    def encode(self, data: np.ndarray, scale: Optional[float] = None) -> ts.CKKSVector:
        """编码数据为CKKS明文向量"""
        if scale is None:
            scale = self.context.global_scale
        data = np.array(data, dtype=np.float64).flatten()
        ckks_vector = ts.ckks_vector(self.context.context, data, scale=scale)
        return ckks_vector
    
    def encrypt(self, data: np.ndarray, scale: Optional[float] = None) -> ts.CKKSVector:
        """加密数据"""
        return self.encode(data, scale)
    
    def encrypt_tensor(self, tensor: torch.Tensor, chunk_size: int = None) -> List[ts.CKKSVector]:
        """加密PyTorch张量（自动分块，支持Slot Packing）"""
        chunk_size = chunk_size or self.slot_count
        flat_data = tensor.detach().cpu().numpy().flatten()
        ciphertexts = []
        for i in range(0, len(flat_data), chunk_size):
            chunk = flat_data[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            ct = self.encrypt(chunk)
            ciphertexts.append(ct)
        return ciphertexts

    def encrypt_chunks(self, chunks: List[np.ndarray]) -> List[ts.CKKSVector]:
        """加密已打包好的数组块列表"""
        ciphertexts = []
        for chunk in chunks:
            if np.iscomplexobj(chunk):
                # TenSEAL 支持复数数组编码
                ct = ts.ckks_vector(self.context.context, chunk, scale=self.context.global_scale)
            else:
                ct = self.encrypt(chunk)
            ciphertexts.append(ct)
        return ciphertexts


class CKKSDecryptor:
    """CKKS解密器 - 处理密文解密"""
    
    def __init__(self, context: CKKSContext):
        self.context = context
    
    def decrypt(self, ciphertext: ts.CKKSVector) -> np.ndarray:
        """解密密文"""
        return ciphertext.decrypt()
    
    def decrypt_to_tensor(self, ciphertexts: List[ts.CKKSVector], 
                          original_shape: Tuple[int, ...]) -> torch.Tensor:
        """解密CKKS密文列表并恢复为PyTorch张量"""
        decrypted_chunks = []
        for ct in ciphertexts:
            chunk = self.decrypt(ct)
            decrypted_chunks.extend(chunk)
        total_elements = np.prod(original_shape)
        flat_data = np.array(decrypted_chunks[:total_elements])
        return torch.tensor(flat_data.reshape(original_shape))

    def decrypt_chunks(self, ciphertexts: List[ts.CKKSVector]) -> List[np.ndarray]:
        """解密密文列表，返回数组块列表"""
        decrypted = []
        for ct in ciphertexts:
            decrypted.append(self.decrypt(ct))
        return decrypted


class CKKSEvaluator:
    """CKKS评估器 - 执行同态运算"""
    
    def __init__(self, context: CKKSContext):
        self.context = context
    
    def add(self, ct1: ts.CKKSVector, ct2: ts.CKKSVector) -> ts.CKKSVector:
        """密文加法"""
        return ct1 + ct2
    
    def sub(self, ct1: ts.CKKSVector, ct2: ts.CKKSVector) -> ts.CKKSVector:
        """密文减法：ct1 - ct2"""
        return ct1 - ct2
    
    def add_scalar(self, ct: ts.CKKSVector, scalar: float) -> ts.CKKSVector:
        """密文+标量"""
        return ct + scalar
    
    def multiply_scalar(self, ct: ts.CKKSVector, scalar: float) -> ts.CKKSVector:
        """密文*标量"""
        return ct * scalar
    
    def multiply(self, ct1: ts.CKKSVector, ct2: ts.CKKSVector) -> ts.CKKSVector:
        """密文乘法"""
        return ct1 * ct2
    
    def weighted_average(self, ciphertexts: List[ts.CKKSVector], 
                         weights: List[float]) -> ts.CKKSVector:
        """计算加权平均值（用于联邦学习聚合）"""
        if len(ciphertexts) != len(weights):
            raise ValueError("密文数量和权重数量必须相同")
        if len(ciphertexts) == 0:
            raise ValueError("密文列表不能为空")
        result = self.multiply_scalar(ciphertexts[0], weights[0])
        for i in range(1, len(ciphertexts)):
            weighted = self.multiply_scalar(ciphertexts[i], weights[i])
            result = self.add(result, weighted)
        return result


def merge_sparse_encrypted_updates(enc1: Dict, enc2: Dict, evaluator=None) -> Dict:
    """
    按 batch 索引对齐合并两个稀疏加密更新。

    关键：不能简单按 ciphertexts 列表索引相加，因为两个稀疏更新的 mask 可能不同。
    必须按 mask 中标记的 batch 位置逐一比对后累加。

    Args:
        enc1: 稀疏加密更新 dict（含 '__sparse__', 'ciphertexts', 'mask'）
        enc2: 同上
        evaluator: CKKSEvaluator 实例（服务器端用 evaluator.add，客户端可用 +）

    Returns:
        合并后的稀疏加密更新 dict
    """
    mask1 = enc1['mask']
    mask2 = enc2['mask']
    cts1 = enc1['ciphertexts']
    cts2 = enc2['ciphertexts']

    # Auto-deserialize bytes -> CKKSVector to avoid _add_plain weirdness
    ctx = evaluator.context.context if evaluator is not None else None
    if ctx is not None and cts1 and isinstance(cts1[0], bytes):
        cts1 = [ts.CKKSVector.load(ctx, c) for c in cts1]
    if ctx is not None and cts2 and isinstance(cts2[0], bytes):
        cts2 = [ts.CKKSVector.load(ctx, c) for c in cts2]

    batch_num = len(mask1)
    merged_mask = [0] * batch_num
    merged_cts = []

    idx1 = 0
    idx2 = 0
    for i in range(batch_num):
        has1 = mask1[i]
        has2 = mask2[i]
        if has1 and has2:
            try:
                if evaluator is not None:
                    merged_cts.append(evaluator.add(cts1[idx1], cts2[idx2]))
                else:
                    merged_cts.append(cts1[idx1] + cts2[idx2])
            except ValueError as e:
                ct1, ct2 = cts1[idx1], cts2[idx2]
                # 尝试序列化再反序列化后相加（刷新内部表示）
                try:
                    ctx = ct1.context
                    ct1_fresh = ts.CKKSVector.load(ctx, ct1.serialize())
                    ct2_fresh = ts.CKKSVector.load(ctx, ct2.serialize())
                    merged_cts.append(ct1_fresh + ct2_fresh)
                except ValueError as e2:
                    raise ValueError(
                        f"merge_sparse_encrypted_updates failed at batch {i}: "
                        f"scale1={getattr(ct1, 'scale', 'N/A')}, "
                        f"scale2={getattr(ct2, 'scale', 'N/A')}, "
                        f"size1={getattr(ct1, 'size', lambda: 'N/A')() if callable(getattr(ct1, 'size', None)) else getattr(ct1, 'size', 'N/A')}, "
                        f"size2={getattr(ct2, 'size', lambda: 'N/A')() if callable(getattr(ct2, 'size', None)) else getattr(ct2, 'size', 'N/A')}, "
                        f"context_same={getattr(ct1, 'context', None) is getattr(ct2, 'context', None)}. "
                        f"Original error: {e}; Refresh error: {e2}"
                    )
            merged_mask[i] = 1
            idx1 += 1
            idx2 += 1
        elif has1:
            # 直接引用原密文（不执行 +0，避免噪声累积）
            # 原列表在此 merge 后不再使用，直接引用安全
            merged_cts.append(cts1[idx1])
            merged_mask[i] = 1
            idx1 += 1
        elif has2:
            merged_cts.append(cts2[idx2])
            merged_mask[i] = 1
            idx2 += 1

    result = {
        '__sparse__': True,
        'ciphertexts': merged_cts,
        'mask': merged_mask,
        'batch_size': enc1['batch_size'],
        'total_elements': enc1['total_elements'],
        'shapes': enc1['shapes'],
        'offsets': enc1['offsets'],
    }
    # 传递 packing_metadata（CRTStack/TwoTier 解密必需）
    pm1 = enc1.get('packing_metadata')
    pm2 = enc2.get('packing_metadata')
    if pm1 is not None:
        result['packing_metadata'] = pm1
    elif pm2 is not None:
        result['packing_metadata'] = pm2
    return result


class CKKSManager:
    """CKKS管理器 - 整合所有CKKS功能"""
    
    def __init__(self, config: Dict, context: CKKSContext = None):
        self.config = config
        if context is not None:
            self.context = context
        else:
            self.context = CKKSContext(
                poly_modulus_degree=config.get('poly_modulus_degree', 8192),
                coeff_mod_bit_sizes=config.get('coeff_mod_bit_sizes', [40, 20, 40]),
                global_scale=config.get('global_scale', 2**20)
            )
        # Slot Packing: 根据多项式模数度计算最大slot数
        # 优先从config读取poly_modulus_degree（兼容外部传入的context）
        poly_degree = config.get('poly_modulus_degree', 8192)
        slot_count = poly_degree // 2 if config.get('slot_packing', True) else 4096
        self.encryptor = CKKSEncryptor(self.context, slot_count=slot_count)
        self.decryptor = CKKSDecryptor(self.context)
        self.evaluator = CKKSEvaluator(self.context)
        # 多密钥 MASER 后端（由 main.py 在 maser.multi_key=true 时注入）
        self.xmkckks = None
        # ESAFL NATIVE 多密钥后端（由 main.py 在 esafl.mode=NATIVE 时注入）
        self.eshe = None
        # ESAFL PUREPY 后端（esafl.mode=PUREPY 时在本管理器内直接创建，
        # 纯 Python ESHE 复现，见 ckks_fed/eshe.py；
        # 打包使用论文 §V-B2 EP 机制，见 ckks_fed/packing.py ESHEEPPacking）
        self.purepy_eshe = None
        self.ep_packing = None
        _esafl_cfg = config.get('esafl', {})
        if (_esafl_cfg.get('enabled', False)
                and _esafl_cfg.get('mode', 'SIMULATION') == 'PUREPY'):
            from ckks_fed.eshe import PurePyESHE
            from ckks_fed.packing import ESHEEPPacking
            self.purepy_eshe = PurePyESHE(
                n=slot_count,
                seed=_esafl_cfg.get('prpg_seed', 42),
                logp=_esafl_cfg.get('logp', 50),
                eta=_esafl_cfg.get('eta', 4),
            )
            # EP 打包参数：logq0 复用 packing.quant_bits；slots2/pad_bits 不再使用
            _packing_cfg = config.get('packing', {})
            _logq0 = _packing_cfg.get('quant_bits', 10)
            _num_clients = int(_esafl_cfg.get('num_clients', 0))
            if _num_clients < 1:
                raise ValueError(
                    "ESAFL PUREPY 模式需要 esafl.num_clients（或 system.num_clients，"
                    "由 main.py 自动注入）以推导 EP 打包参数 pad=⌈logN⌉+1"
                )
            if 'slots2' in _packing_cfg or 'pad_bits' in _packing_cfg:
                logger.warning(
                    "[ESAFL-PUREPY] packing.slots2 / packing.pad_bits 在 EP 打包下"
                    "不再使用（pad 由客户端数 N 推导，T 由 logp/(logq0+pad) 推导）"
                )
            self.ep_packing = ESHEEPPacking(
                n=slot_count,
                logq0=_logq0,
                logp=self.purepy_eshe.params.logp,
                num_clients=_num_clients,
                quant_clip=_packing_cfg.get('quant_clip',
                                            _esafl_cfg.get('quant_clip')),
            )
            logger.info(
                f"ESAFL PUREPY 后端已初始化 | n={slot_count} | "
                f"logp={self.purepy_eshe.params.logp} | Q≈2^{self.purepy_eshe.Q.bit_length()-1}"
            )
        # 初始化可插拔打包策略
        self.packing_strategy = create_packing_strategy(config, slot_count)
        # 初始化可插拔包级稀疏化策略
        self.sparsification_strategy = create_sparsification_strategy(config)
        # 强制 batch_size = slot_count，与 FedPHE 对齐：一个 batch = N/2 个 slot = 一个密文
        self.batch_size = slot_count
        # PTopk: 初始化残差累积模块，并在启用时包装稀疏化策略
        self.ptopk = PTopkModule(config)
        if self.ptopk.client_residual_enabled and not isinstance(self.sparsification_strategy, NoSparsification):
            self.sparsification_strategy = self.ptopk.wrap_strategy(self.sparsification_strategy)
            logger.info(f"PTopk client_residual 已启用: 包装策略={self.sparsification_strategy.name}")
        elif self.ptopk.client_residual_enabled:
            logger.warning("PTopk client_residual 已启用，但 sparsification_strategy=none，残差补偿不生效")
        else:
            logger.info("PTopk client_residual 已禁用: 无残差补偿")
        logger.info(
            f"CKKS管理器初始化完成 (slot_count={slot_count}, "
            f"slot_packing={'ON' if config.get('slot_packing', True) else 'OFF'}, "
            f"packing={self.packing_strategy.name}, "
            f"sparsification={self.sparsification_strategy.name}, "
            f"batch_size={self.batch_size})"
        )
    
    def encrypt_model_update(self, model_update: Dict[str, torch.Tensor], round_num: int = 0,
                             skip_sparsification: bool = False,
                             blinding_mask=None, client_mask=None, client_id: int = 0,
                             global_mask: Optional[np.ndarray] = None,
                             global_maser_indices: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """加密模型更新（FedPHE 对齐：一个 batch = N/2 slot = 一个密文）
        
        Args:
            model_update: 模型参数字典
            round_num: 当前轮次（用于 RandK 种子）
            skip_sparsification: 是否跳过稀疏化。服务器端加密完整全局模型时必须设为 True。
            blinding_mask: ZeroSumBlindingMask 实例（pre_topk 模式用）
            client_mask: 本客户端的掩码字典（pre_topk 模式用）
            global_maser_indices: MASER 全局选中的参数索引（启用全局投票时用）
            client_id: 客户端 ID（用于日志）
            global_mask: 全局掩码（ESAFL 模式用），shape=(num_batches,)，值为 1 的 batch 才加密
        """
        # 初始化 packing_metadata，避免在某些代码路径下未赋值
        packing_metadata = None
        
        # 1) 合并所有参数为一个长数组（FedPHE 风格）
        all_values = []
        shapes = {}
        offsets = {}
        offset = 0
        for name in sorted(model_update.keys()):
            param = model_update[name]
            flat = param.detach().cpu().numpy().flatten()
            shapes[name] = list(param.shape)
            offsets[name] = (offset, param.numel())
            all_values.extend(flat.tolist())
            offset += param.numel()
        total_elements = len(all_values)

        # 2) 按 slot_count (= batch_size) 切分为 batch，每个 batch 对应一个密文
        batches = []
        for i in range(0, total_elements, self.batch_size):
            chunk = np.array(all_values[i:i + self.batch_size], dtype=np.float64)
            if len(chunk) < self.batch_size:
                chunk = np.pad(chunk, (0, self.batch_size - len(chunk)), mode='constant')
            batches.append(chunk)

        num_batches = len(batches)

        # ================================================================
        # MASER 模式：参数级 mask 裁剪，只上传重要参数值 + 索引
        # ================================================================
        maser_cfg = self.config.get('maser', {})
        if maser_cfg.get('enable', False) and not skip_sparsification:
            from ckks_fed.maser_mask import (
                extract_important_params, pack_important_values,
                extract_values_by_indices, pack_maser_global_values,
                pack_maser_compressed_values,
            )
            topk_ratio = maser_cfg.get('topk_ratio', 0.5)
            maser_mode = maser_cfg.get('mode', 'compressed')  # compressed=原版 MASER, aligned=密文域直接累加

            if global_maser_indices is not None and len(global_maser_indices) > 0:
                indices = np.asarray(global_maser_indices, dtype=np.int64)
                total_elements = sum(p.numel() for p in model_update.values())

                if maser_mode == 'aligned':
                    # 对齐原始参数位置：所有客户端密文结构一致，可直接同态累加
                    batches, mask = pack_maser_global_values(model_update, indices, self.batch_size)
                    strategy_tag = "maser_global_aligned"
                    padded_len = len(indices)
                else:
                    # 压缩打包（默认/原版 MASER）：只传 ceil(k/batch_size) 个 slice
                    batches, padded_len = pack_maser_compressed_values(model_update, indices, self.batch_size)
                    mask = [1] * len(batches)
                    strategy_tag = "maser_global_compressed"
            else:
                # 本地模式：每个客户端各自选 top-k（保持向后兼容）
                values, indices, total_elements = extract_important_params(model_update, topk_ratio)
                batches, padded_len = pack_important_values(values, self.batch_size)
                mask = [1] * len(batches)
                strategy_tag = "maser_local"

            # ================================================================
            # 多密钥 MASER：使用 xMKCKKS 真实多密钥加密
            # ================================================================
            use_multi_key = maser_cfg.get('multi_key', False) and self.xmkckks is not None
            if use_multi_key:
                if maser_mode == 'aligned':
                    raise NotImplementedError(
                        "多密钥 MASER 暂仅支持 compressed 模式，"
                        "请将 maser.mode 设为 'compressed'"
                    )
                xmkckks = self.xmkckks
                client_idx = xmkckks.get_client_idx(client_id)
                ciphertexts = []
                for batch in batches:
                    ct = xmkckks.encrypt_for_client(batch.tolist(), client_idx)
                    ciphertexts.append(ct)
                strategy_tag = "maser_global_compressed_multikey"
                logger.info(
                    f"[MASER-MK] Client {client_id} (idx={client_idx}) xMKCKKS encrypt | "
                    f"values={len(indices)}/{total_elements} | batches={len(ciphertexts)} | "
                    f"topk_ratio={topk_ratio} | round={round_num}"
                )
            else:
                ciphertexts = self.encryptor.encrypt_chunks(batches)
                logger.info(
                    f"[MASER] Client {client_id} encrypt | values={len(indices)}/{total_elements} | "
                    f"batches={len(ciphertexts)} | topk_ratio={topk_ratio} | "
                    f"mode={strategy_tag} | round={round_num}"
                )
            return {
                '__sparse__': True,
                '__multi_key__': use_multi_key,
                'ciphertexts': ciphertexts,
                'indices': indices.tolist(),
                'num_params': total_elements,
                'total_elements': total_elements,
                'batch_size': self.batch_size,
                'shapes': shapes,
                'offsets': offsets,
                'mask': mask,
                'padded_len': padded_len,
                'strategy': 'maser_param_mask',
                'sparsity_rate': topk_ratio,
                'maser_mode': strategy_tag,
            }

        # ================================================================
        # ESAFL PUREPY 模式：纯 Python ESHE 复现。
        # 打包使用论文 §V-B2 EP 机制（ESHEEPPacking）：量化值 u ∈ [0, 2^logq0−1]
        # 按 (pad+logq0)-bit slot 位域拼接为整数多项式系数（slot 1 在最高位，
        # 第 T 个 slot 为零多项式作进位余量），系数 β < p 直接作为 ESHE 明文。
        # ================================================================
        esafl_cfg = self.config.get('esafl', {})
        if (esafl_cfg.get('enabled', False)
                and esafl_cfg.get('mode', 'SIMULATION') == 'PUREPY'
                and self.purepy_eshe is not None):
            if global_mask is not None and len(global_mask) > 0:
                logger.warning(
                    "[ESAFL-PUREPY] global_mask 投票与 PUREPY 全参与解密不兼容，已忽略掩码。"
                )
            # 客户端更新使用统一固定 scale（quant_clip）；服务器加密全局状态
            # （skip_sparsification=True）用自适应 scale（仅 num_sum=1 解密）
            _fixed = None if skip_sparsification else self.ep_packing.quant_clip
            chunks, metadata = self.ep_packing.pack(model_update, fixed_scale=_fixed)
            ciphertexts = []
            for chunk in chunks:
                # EP chunk 已是 int64 整数系数（β < p），直接加密
                ct = self.purepy_eshe.encrypt_chunk(client_id, chunk, round_num)
                ciphertexts.append(ct)
            logger.info(
                f"[ESAFL-PUREPY] Client {client_id} ESHE-EP encrypt | "
                f"batches={len(ciphertexts)} | n={self.purepy_eshe.n} | "
                f"values/ct={self.ep_packing.values_per_chunk} | round={round_num}"
            )
            return {
                '__sparse__': True,
                '__purepy__': True,
                'ciphertexts': ciphertexts,
                'mask': [1] * len(ciphertexts),
                'batch_size': self.batch_size,
                'total_elements': metadata.data['total_elements'],
                'shapes': metadata.data['shapes'],
                'offsets': metadata.data['offsets'],
                'strategy': 'eshe_ep',
                'sparsity_rate': 1.0,
                'packing_metadata': metadata.data,
            }

        # ================================================================
        # ESAFL NATIVE 多密钥模式：使用真实多密钥 CKKS 加密每个 batch
        # ================================================================
        if (esafl_cfg.get('enabled', False)
                and esafl_cfg.get('mode', 'SIMULATION') == 'NATIVE'
                and self.eshe is not None):
            ciphertexts = []
            for batch in batches:
                ct = self.eshe.encrypt(client_id, batch.tolist())
                ciphertexts.append(ct)
            logger.info(
                f"[ESAFL-NATIVE] Client {client_id} multi-key encrypt | "
                f"batches={len(ciphertexts)} | round={round_num}"
            )
            return {
                '__sparse__': True,
                '__native_multi_key__': True,
                'ciphertexts': ciphertexts,
                'mask': [1] * len(ciphertexts),
                'batch_size': self.batch_size,
                'total_elements': total_elements,
                'shapes': shapes,
                'offsets': offsets,
                'strategy': 'esafl_native_multikey',
                'sparsity_rate': 1.0,
            }

        # ================================================================
        # ESAFL 全局掩码模式：按全局掩码决定哪些 batch 需要加密
        # ================================================================
        if global_mask is not None and len(global_mask) > 0:
            # 检查是否使用非 layerwise 的 packing 策略（如 CRTStack）
            # 注意：global_mask 模式下，packing 独立于 sparsification 策略。
            # GlobalMaskVote 已经决定了哪些 chunk 上传，不需要额外的稀疏化检查。
            use_packing = self.packing_strategy.name != 'layerwise'

            if use_packing:
                # packing 路径：在 chunk 级别应用 global_mask，确保与全局状态的 chunk 语义一致
                # 注意：只加密被选中的 chunk（和原始 global_mask 分支一致），
                # 否则 ct_idx 在服务器端会错位。
                chunks, metadata = self.packing_strategy.pack(model_update)
                num_batches = len(chunks)
                selected_batches = []
                mask = [0] * num_batches
                for b in range(num_batches):
                    if b < len(global_mask) and global_mask[b] == 1:
                        mask[b] = 1
                        selected_batches.append(chunks[b])
                    # mask=0 的 chunk 不加密（服务器端会补零）
                ciphertexts = self.encryptor.encrypt_chunks(selected_batches)
                packing_metadata = metadata.data
                shapes = metadata.data['shapes']
                offsets = metadata.data['offsets']
                total_elements = metadata.data['total_elements']
                active_count = int(np.sum(global_mask[:num_batches]))
                logger.info(
                    f"[ESAFL] Client {client_id} encrypt | packing={self.packing_strategy.name} | "
                    f"global_batches={active_count}/{num_batches} | round={round_num}"
                )
                result = {
                    '__sparse__': True,
                    'ciphertexts': ciphertexts,
                    'mask': mask,
                    'batch_size': self.batch_size,
                    'total_elements': total_elements,
                    'shapes': shapes,
                    'offsets': offsets,
                    'strategy': 'esafl_global_mask',
                    'sparsity_rate': 1.0,
                    'packing_metadata': packing_metadata,
                }
                return result

            # 非 packing 路径：按原始 batch 级别处理 global_mask
            # 注意：global_mask 模式下，本地 sparsification 被忽略。
            # GlobalMaskVote 已经通过 server 聚合决定了哪些 batch 上传，
            # 不需要客户端再执行独立的 TopK/RandK 稀疏化（避免双重稀疏）。
            if not skip_sparsification and not isinstance(self.sparsification_strategy, NoSparsification):
                logger.warning(
                    f"[ESAFL] Client {client_id} | global_mask 模式下本地 sparsification "
                    f"({self.sparsification_strategy.name}) 被忽略，仅使用全局掩码。"
                    f"如需独立稀疏化，请设置 global_mask_vote.mode='none'。"
                )
            selected_indices = list(range(num_batches))
            
            # 按全局掩码构建加密 batch：
            #   - 全局掩码为 1 → 加密真实值
            #   - 全局掩码为 0 → 跳过（服务器端补零）
            selected_batches = []
            mask = [0] * num_batches
            for b in range(num_batches):
                if b < len(global_mask) and global_mask[b] == 1:
                    mask[b] = 1
                    selected_batches.append(batches[b])
            
            # pre_topk 掩码注入（如果启用）
            if (blinding_mask is not None and client_mask is not None
                    and getattr(blinding_mask, 'apply_mode', 'post_topk') == 'pre_topk'):
                active_indices = [b for b in range(num_batches) if mask[b] == 1]
                selected_batches = blinding_mask.apply_mask_to_batches(
                    selected_batches, active_indices, client_mask, round_num=round_num
                )
            
            ciphertexts = self.encryptor.encrypt_chunks(selected_batches)
            active_count = int(np.sum(global_mask[:num_batches]))
            logger.info(
                f"[ESAFL] Client {client_id} encrypt | global_batches={active_count}/{num_batches} | "
                f"own_selected={len(selected_indices)} | round={round_num}"
            )
            return {
                '__sparse__': True,
                'ciphertexts': ciphertexts,
                'mask': mask,
                'batch_size': self.batch_size,
                'total_elements': total_elements,
                'shapes': shapes,
                'offsets': offsets,
                'strategy': 'esafl_global_mask',
                'sparsity_rate': 1.0,  # ESAFL 模式下全局掩码决定
            }

        # ================================================================
        # 原始模式：独立稀疏化（无全局掩码）
        # ================================================================
        if not skip_sparsification and not isinstance(self.sparsification_strategy, NoSparsification):
            selected_indices, selected_batches = self.sparsification_strategy.select_batches(batches, round_num)
            
            # ---- pre_topk 模式：TopK 之后、加密之前注入 batch-level 掩码 ----
            if (blinding_mask is not None and client_mask is not None
                    and getattr(blinding_mask, 'apply_mode', 'post_topk') == 'pre_topk'):
                selected_batches = blinding_mask.apply_mask_to_batches(
                    selected_batches, selected_indices, client_mask, round_num=round_num
                )
                logger.info(
                    f"[pre_topk] Client {client_id} mask injected after TopK | "
                    f"selected_batches={len(selected_indices)}, indices={selected_indices}"
                )
            
            mask = [0] * len(batches)
            for idx in selected_indices:
                mask[idx] = 1
            ciphertexts = self.encryptor.encrypt_chunks(selected_batches)
            logger.info(
                f"稀疏加密: strategy={self.sparsification_strategy.name}, "
                f"total_batches={len(batches)}, selected={len(selected_indices)}, "
                f"sparsity={len(selected_indices)/max(1,len(batches)):.2%}, round={round_num}"
            )
        else:
            # 非稀疏路径：使用 packing_strategy 打包（如果配置了非 layerwise 策略）
            use_packing = (
                self.packing_strategy.name != 'layerwise'
                and isinstance(self.sparsification_strategy, NoSparsification)
            )
            if use_packing:
                chunks, metadata = self.packing_strategy.pack(model_update)
                selected_batches = chunks
                mask = [1] * len(chunks)
                ciphertexts = self.encryptor.encrypt_chunks(selected_batches)
                packing_metadata = metadata.data
                # 从 metadata 中获取 shapes/offsets/total_elements
                shapes = metadata.data['shapes']
                offsets = metadata.data['offsets']
                total_elements = metadata.data['total_elements']
                logger.info(
                    f"打包加密: strategy={self.packing_strategy.name}, "
                    f"chunks={len(chunks)}, round={round_num}"
                )
            else:
                # 默认 layerwise 行为
                selected_indices = list(range(len(batches)))
                selected_batches = batches
                
                # 非稀疏路径下，pre_topk 模式仍然要给所有 batch 加掩码
                if (blinding_mask is not None and client_mask is not None
                        and getattr(blinding_mask, 'apply_mode', 'post_topk') == 'pre_topk'):
                    selected_batches = blinding_mask.apply_mask_to_batches(
                        selected_batches, selected_indices, client_mask, round_num=round_num
                    )
                
                mask = [1] * len(batches)
                ciphertexts = self.encryptor.encrypt_chunks(selected_batches)
                packing_metadata = None

        result = {
            '__sparse__': True,
            'ciphertexts': ciphertexts,
            'mask': mask,
            'batch_size': self.batch_size,
            'total_elements': total_elements,
            'shapes': shapes,
            'offsets': offsets,
            'strategy': self.sparsification_strategy.name if not skip_sparsification else 'none',
            'sparsity_rate': getattr(self.sparsification_strategy, 'sparsity_rate', 1.0),
        }
        if packing_metadata is not None:
            result['packing_metadata'] = packing_metadata
        return result
    
    def decrypt_model_update(self, encrypted_update: Dict[str, Any],
                             original_shapes: Dict[str, Tuple]) -> Dict[str, torch.Tensor]:
        """解密模型更新（FedPHE 对齐：统一 __sparse__ 格式）"""
        if not encrypted_update.get('__sparse__'):
            raise ValueError("加密更新必须使用 __sparse__ 格式（FedPHE 对齐）")

        # 多密钥 MASER：解密需要客户端 partial decrypt 份额，不能在此直接解密
        if encrypted_update.get('__multi_key__'):
            raise RuntimeError(
                "多密钥 MASER 更新不能通过 decrypt_model_update 直接解密，"
                "请调用 decrypt_maser_compressed_multikey(partial_shares, client_indices)"
            )

        ciphertexts = encrypted_update['ciphertexts']
        batch_size = encrypted_update['batch_size']
        shapes = encrypted_update['shapes']
        offsets = encrypted_update['offsets']

        # 解密选中的 ciphertexts
        # 兼容序列化字节串（来自 TEE 路径或网络传输）
        if encrypted_update.get('__purepy__'):
            # ESAFL PUREPY：one-shot 解密 [[ct − mask]_Q]_p 得整数系数。
            # 单个密文（客户端上传 / 服务器加密的全局状态）：slot 内即编码值；
            # 聚合密文（__num_sum__=N）：slot 内为 N 个客户端编码值的整数和
            # （EP pad 保证位域不串位），unpack_average 减 N·max_q 后除 N 得平均。
            decrypted_chunks = [
                self.purepy_eshe.decrypt(ct)
                for ct in ciphertexts
            ]
            packing_metadata = encrypted_update.get('packing_metadata')
            if packing_metadata is None:
                raise ValueError("[ESAFL-PUREPY] 缺少 packing_metadata，无法解包")
            num_sum = int(encrypted_update.get('__num_sum__', 1))
            metadata = PackingMetadata(
                packing_metadata.get('strategy', 'eshe_ep'), packing_metadata)
            zero_point = encrypted_update.get('__zero_point__', None)
            return self.ep_packing.unpack_average(
                decrypted_chunks, metadata, num_sum, zero_point=zero_point)
        if ciphertexts and isinstance(ciphertexts[0], bytes):
            ciphertexts = [ts.CKKSVector.load(self.context.context, c) for c in ciphertexts]
        if not encrypted_update.get('__purepy__'):
            decrypted_batches = self.decryptor.decrypt_chunks(ciphertexts)

        # ================================================================
        # MASER 模式：按索引恢复完整参数向量
        # ================================================================
        if encrypted_update.get('strategy') == 'maser_param_mask':
            from ckks_fed.maser_mask import restore_full_params
            indices = np.array(encrypted_update.get('indices', []), dtype=np.int64)
            num_params = encrypted_update.get('num_params', 0)
            padded_len = encrypted_update.get('padded_len', 0)
            # 解密出的 values 可能包含 padding，取前 padded_len 个
            all_values = []
            for batch in decrypted_batches:
                all_values.extend(np.array(batch, dtype=np.float64).tolist())
            values = np.array(all_values, dtype=np.float64)
            if padded_len > 0 and len(values) > padded_len:
                values = values[:padded_len]
            # 用 np.zeros 恢复完整参数
            full = restore_full_params(values, indices, num_params)
            result = {}
            for name in sorted(shapes.keys()):
                off, numel = offsets[name]
                shape = shapes[name]
                result[name] = torch.tensor(full[off:off + numel].reshape(shape))
            return result

        # 非 MASER 模式：继续原有逻辑
        mask = encrypted_update['mask']
        total_elements = encrypted_update.get('total_elements', encrypted_update.get('num_params', 0))

        # 如果使用了 packing_strategy，通过 unpack 恢复
        packing_metadata = encrypted_update.get('packing_metadata')
        if packing_metadata is not None:
            # 按 mask 还原 decrypted chunks（未选中的补零值 chunk）
            decrypted_chunks = []
            ct_idx = 0
            for batch_idx, is_selected in enumerate(mask):
                if is_selected:
                    decrypted_chunks.append(np.array(decrypted_batches[ct_idx], dtype=np.float64))
                    ct_idx += 1
                else:
                    # 使用 packing_strategy 生成的零值 chunk，确保 unpack 后得到浮点 0
                    decrypted_chunks.append(self.packing_strategy.create_zero_chunk())
            metadata = PackingMetadata(packing_metadata.get('strategy', 'unknown'), packing_metadata)
            return self.packing_strategy.unpack(decrypted_chunks, metadata)

        # 根据 mask 还原所有 batch（未选中的补 0）
        all_values = []
        ct_idx = 0
        for batch_idx, is_selected in enumerate(mask):
            if is_selected:
                chunk = np.array(decrypted_batches[ct_idx], dtype=np.float64)
                ct_idx += 1
                all_values.extend(chunk.tolist())
            else:
                all_values.extend([0.0] * batch_size)

        all_values = np.array(all_values[:total_elements], dtype=np.float64)

        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(all_values[off:off + numel].reshape(shape))
        return result

    def partial_decrypt_maser_update(self, encrypted_update: Dict[str, Any],
                                     client_id: int) -> List[Any]:
        """
        多密钥 MASER：由指定客户端对聚合密文的每个 slice 产生部分解密份额。

        Args:
            encrypted_update: 聚合后的加密更新字典（__multi_key__=True）
            client_id: 客户端 ID

        Returns:
            该客户端对每个 slice 的部分解密份额列表
        """
        if not encrypted_update.get('__multi_key__'):
            raise ValueError("partial_decrypt_maser_update 仅支持 __multi_key__=True 的更新")
        if self.xmkckks is None:
            raise RuntimeError("xmkckks 后端未初始化")

        client_idx = self.xmkckks.get_client_idx(client_id)
        shares = []
        for agg_ct in encrypted_update['ciphertexts']:
            pd = self.xmkckks.partial_decrypt(agg_ct, client_idx)
            shares.append(pd)
        return shares

    def decrypt_esafl_native_multikey(
        self,
        encrypted_update: Dict[str, Any],
        partial_shares: List[List[Any]],
        client_ids: List[int],
        client_weights: Optional[List[float]] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        ESAFL NATIVE 多密钥模式：聚合所有客户端的解密份额并解码，恢复明文模型更新。

        Args:
            encrypted_update: 聚合后的加密更新字典（__native_multi_key__=True）
            partial_shares: 每个客户端对每个 batch 的部分解密份额
            client_ids: 对应客户端 ID 列表
            client_weights: 可选客户端权重，用于 FedAvg 加权；默认等权平均

        Returns:
            恢复出的模型更新字典 {name: torch.Tensor}
        """
        if not encrypted_update.get('__native_multi_key__'):
            raise ValueError("decrypt_esafl_native_multikey 仅支持 __native_multi_key__=True 的更新")
        if self.eshe is None:
            raise RuntimeError("eshe 后端未初始化")

        shapes = encrypted_update['shapes']
        offsets = encrypted_update['offsets']
        total_elements = encrypted_update['total_elements']
        batch_size = encrypted_update['batch_size']

        client_indices = [self.eshe._resolve_client_idx(cid) for cid in client_ids]

        all_values = []
        for batch_idx, agg_ct in enumerate(encrypted_update['ciphertexts']):
            slice_shares = [shares[batch_idx] for shares in partial_shares]
            decoded = self.eshe.decode(slice_shares, client_indices)
            all_values.extend(decoded.tolist())

        values = np.array(all_values, dtype=np.float64)
        # xMK-CKKS 同态加法得到的是未加权求和，按参与客户端数做等权平均。
        # 如需按数据量加权，客户端需在加密前将本地更新乘以 w_i / W_total。
        values = values / len(client_indices)
        values = values[:total_elements]
        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(values[off:off + numel].reshape(shape))
        return result

    def decrypt_maser_compressed_multikey(self,
                                          encrypted_update: Dict[str, Any],
                                          partial_shares: List[List[Any]],
                                          client_ids: List[int]) -> Dict[str, torch.Tensor]:
        """
        多密钥 MASER：聚合所有客户端的解密份额并解码，恢复明文模型更新。

        Args:
            encrypted_update: 聚合后的加密更新字典（__multi_key__=True）
            partial_shares: List[List[Any]], 每个客户端对每个 slice 的部分解密份额
            client_ids: 对应客户端 ID 列表

        Returns:
            恢复出的模型更新字典 {name: torch.Tensor}
        """
        if not encrypted_update.get('__multi_key__'):
            raise ValueError("decrypt_maser_compressed_multikey 仅支持 __multi_key__=True 的更新")
        if self.xmkckks is None:
            raise RuntimeError("xmkckks 后端未初始化")

        client_indices = [self.xmkckks.get_client_idx(cid) for cid in client_ids]
        return self.xmkckks.decrypt_maser_compressed(
            encrypted_update, partial_shares, client_indices
        )

    def aggregate_encrypted_updates(self, encrypted_updates: List[Dict[str, Any]],
                                    weights: List[float]) -> Dict[str, Any]:
        """聚合加密的模型更新（FedPHE 对齐：统一 __sparse__ 格式）"""
        if len(encrypted_updates) == 0:
            raise ValueError("加密更新列表为空")

        if not encrypted_updates[0].get('__sparse__'):
            raise ValueError("加密更新必须使用 __sparse__ 格式（FedPHE 对齐）")

        return self._aggregate_sparse_updates(encrypted_updates, weights)

    def subtract_encrypted_updates(self, enc1: Dict[str, Any], enc2: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算两个稀疏加密更新的差值：delta = enc1 - enc2（同态减法）。
        
        用于 ESAFL 预取：δ^(r) = C^(r) - C^(r-1)。
        按 batch 位置对齐后逐 batch 执行同态减法。
        """
        if not enc1.get('__sparse__') or not enc2.get('__sparse__'):
            raise ValueError("输入必须使用 __sparse__ 格式")

        # ESAFL PUREPY：ESHE 密文逐系数减法（mask 同步相减，
        # 即论文跨轮解密的 Δ_a·s 校正项，客户端 extended_decrypt 直接使用）
        if enc1.get('__purepy__') or enc2.get('__purepy__'):
            if not (enc1.get('__purepy__') and enc2.get('__purepy__')):
                raise ValueError("PUREPY 密文只能与 PUREPY 密文相减")
            num = len(enc1['ciphertexts'])
            delta_cts = [
                self.purepy_eshe.subtract(enc1['ciphertexts'][i], enc2['ciphertexts'][i])
                for i in range(num)
            ]
            return {
                '__sparse__': True,
                '__purepy__': True,
                'ciphertexts': delta_cts,
                'mask': [1] * num,
                'batch_size': enc1['batch_size'],
                'total_elements': enc1['total_elements'],
                'shapes': enc1['shapes'],
                'offsets': enc1['offsets'],
                'packing_metadata': enc1.get('packing_metadata'),
                'strategy': 'eshe_ep',
                'sparsity_rate': 1.0,
                '__num_sum__': enc1.get('__num_sum__', 1),
                # delta 明文是编码值之差，不含无符号偏移（unpack 时 zero_point=0）
                '__zero_point__': 0,
            }

        mask1 = enc1['mask']
        mask2 = enc2['mask']
        cts1 = enc1['ciphertexts']
        cts2 = enc2['ciphertexts']
        
        # Auto-deserialize bytes -> CKKSVector
        ctx = self.context.context
        if cts1 and isinstance(cts1[0], bytes):
            cts1 = [ts.CKKSVector.load(ctx, c) for c in cts1]
        if cts2 and isinstance(cts2[0], bytes):
            cts2 = [ts.CKKSVector.load(ctx, c) for c in cts2]
        
        batch_num = len(mask1)
        delta_mask = [0] * batch_num
        delta_cts = []
        
        idx1 = 0
        idx2 = 0
        for i in range(batch_num):
            has1 = mask1[i]
            has2 = mask2[i]
            if has1 and has2:
                delta_ct = self.evaluator.sub(cts1[idx1], cts2[idx2])
                delta_cts.append(delta_ct)
                delta_mask[i] = 1
                idx1 += 1
                idx2 += 1
            elif has1 and not has2:
                # enc1 有，enc2 没有 → delta = enc1
                delta_cts.append(cts1[idx1])
                delta_mask[i] = 1
                idx1 += 1
            elif not has1 and has2:
                # enc1 没有，enc2 有 → delta = -enc2
                delta_ct = self.evaluator.multiply_scalar(cts2[idx2], -1.0)
                delta_cts.append(delta_ct)
                delta_mask[i] = 1
                idx2 += 1
            # else: 两者都没有，delta=0，跳过
        
        return {
            '__sparse__': True,
            'ciphertexts': delta_cts,
            'mask': delta_mask,
            'batch_size': enc1['batch_size'],
            'total_elements': enc1['total_elements'],
            'shapes': enc1['shapes'],
            'offsets': enc1['offsets'],
        }

    def _aggregate_sparse_updates(self, encrypted_updates: List[Dict[str, Any]],
                                  weights: List[float]) -> Dict[str, Any]:
        """
        稀疏加密更新的聚合。

        核心逻辑（与 FedPHE 论文对齐）：
          - 每个 batch 独立聚合
          - 只聚合提交了该 batch 的客户端
          - 记录每个 batch 的聚合权重和（__sum_weights__），供解密归一化
        """
        # ================================================================
        # MASER 全局投票模式：所有客户端按统一全局索引上传，结构一致，
        # 直接走下方通用密文加权平均路径，无需解密明文聚合。
        # ================================================================
        if encrypted_updates[0].get('strategy') == 'maser_param_mask':
            logger.info(f"[MASER] 密文聚合 | clients={len(encrypted_updates)}")
            # 安全检查：全局投票模式下所有客户端的 indices 必须一致
            first_indices = encrypted_updates[0].get('indices', [])
            for idx, update in enumerate(encrypted_updates[1:], start=1):
                other_indices = update.get('indices', [])
                if list(first_indices) != list(other_indices):
                    raise ValueError(
                        f"[MASER] 客户端 #{idx} 的 indices 与全局索引不一致，"
                        f"请启用 MASER 全局投票（main.py 中调用 run_maser_global_vote）"
                    )

            # ================================================================
            # 多密钥 MASER：使用 xMKCKKS 同态加法聚合。
            # xMKCKKS addCTs 仅支持同态加法，权重平均在解码后按参与客户端数进行
            # （MASER 原版风格：uniform average）。
            # ================================================================
            if encrypted_updates[0].get('__multi_key__'):
                if self.xmkckks is None:
                    raise RuntimeError("__multi_key__=True 但 xmkckks 后端未初始化")
                logger.info(f"[MASER-MK] xMKCKKS 同态聚合 | slices={len(encrypted_updates[0]['ciphertexts'])}")
                num_slices = len(encrypted_updates[0]['ciphertexts'])
                aggregated_cts = []
                for slice_idx in range(num_slices):
                    slice_cts = [upd['ciphertexts'][slice_idx] for upd in encrypted_updates]
                    aggregated_cts.append(self.xmkckks.aggregate_ciphertexts(slice_cts))
                result = {
                    '__sparse__': True,
                    '__multi_key__': True,
                    'ciphertexts': aggregated_cts,
                    'indices': first_indices,
                    'num_params': encrypted_updates[0].get('num_params', 0),
                    'total_elements': encrypted_updates[0].get('total_elements', 0),
                    'batch_size': encrypted_updates[0]['batch_size'],
                    'shapes': encrypted_updates[0]['shapes'],
                    'offsets': encrypted_updates[0]['offsets'],
                    'mask': [1] * len(aggregated_cts),
                    'padded_len': encrypted_updates[0].get('padded_len', 0),
                    'strategy': 'maser_param_mask',
                    'sparsity_rate': encrypted_updates[0].get('sparsity_rate', 1.0),
                    'maser_mode': 'maser_global_compressed_multikey',
                }
                return result

        # ================================================================
        # ESAFL NATIVE 多密钥模式：使用 ESHEManager 同态加法聚合。
        # xMK-CKKS 仅支持同态加法，权重平均在解码后由服务器在明文域完成。
        # ================================================================
        if encrypted_updates[0].get('__native_multi_key__'):
            if self.eshe is None:
                raise RuntimeError("__native_multi_key__=True 但 eshe 后端未初始化")
            logger.info(
                f"[ESAFL-NATIVE] ESHE 同态聚合 | batches={len(encrypted_updates[0]['ciphertexts'])}"
            )
            num_batches = len(encrypted_updates[0]['ciphertexts'])
            aggregated_cts = []
            for batch_idx in range(num_batches):
                batch_cts = [upd['ciphertexts'][batch_idx] for upd in encrypted_updates]
                aggregated_cts.append(self.eshe.aggregate(batch_cts))
            return {
                '__sparse__': True,
                '__native_multi_key__': True,
                'ciphertexts': aggregated_cts,
                'mask': [1] * len(aggregated_cts),
                'batch_size': encrypted_updates[0]['batch_size'],
                'total_elements': encrypted_updates[0]['total_elements'],
                'shapes': encrypted_updates[0]['shapes'],
                'offsets': encrypted_updates[0]['offsets'],
                'strategy': 'esafl_native_multikey',
                'sparsity_rate': 1.0,
                '__client_weights__': weights,
            }

        # ================================================================
        # ESAFL PUREPY 模式：论文 EP.Eval——密文逐系数求和聚合。
        # EP 打包的 pad 保证 slot 内和 < 2^(logq0+pad) 不串位，因此求和密文
        # one-shot 解密后每 slot 即 N 个客户端编码值的整数和，除 N 得平均
        # （等价于等权 FedAvg；环上无标量乘，权重在解密后的明文域应用）。
        # 注意：聚合密文解密需用 __num_sum__ 除 N（见 decrypt_model_update）。
        # ================================================================
        if encrypted_updates[0].get('__purepy__'):
            if any(u.get('strategy') != 'eshe_ep' for u in encrypted_updates):
                raise ValueError("[ESAFL-PUREPY] 客户端密文策略不一致")
            num = len(encrypted_updates)
            w_min, w_max = min(weights), max(weights)
            if abs(w_max - w_min) > 1e-9:
                logger.warning(
                    f"[ESAFL-PUREPY] 客户端权重不均（{w_min:.4f}~{w_max:.4f}），"
                    f"EP 密文域求和聚合按等权平均处理（论文 ESAFL 同款 Eval）"
                )
            logger.info(
                f"[ESAFL-PUREPY] EP.Eval 密文求和聚合 | clients={num} | "
                f"batches={len(encrypted_updates[0]['ciphertexts'])}"
            )
            num_batches = len(encrypted_updates[0]['ciphertexts'])
            summed_cts = []
            for b in range(num_batches):
                batch_cts = [u['ciphertexts'][b] for u in encrypted_updates]
                summed_cts.append(self.purepy_eshe.aggregate(batch_cts))
            return {
                '__sparse__': True,
                '__purepy__': True,
                'ciphertexts': summed_cts,
                'mask': [1] * num_batches,
                'batch_size': encrypted_updates[0]['batch_size'],
                'total_elements': encrypted_updates[0]['total_elements'],
                'shapes': encrypted_updates[0]['shapes'],
                'offsets': encrypted_updates[0]['offsets'],
                'strategy': 'eshe_ep',
                'sparsity_rate': 1.0,
                'packing_metadata': encrypted_updates[0].get('packing_metadata'),
                '__num_sum__': num,
                '__client_weights__': weights,
            }

        # ================================================================
        # 打包策略明文聚合路径：当 packing_metadata 包含量化信息时，
        # 先解密所有客户端更新，明文加权平均后再重新打包加密。
        # 原因：CRTStack / TwoTier / ESAFL 等整数编码对同态乘法噪声极度敏感，
        # multiply_scalar 引入的舍入误差会导致量化解码完全失败。
        # ================================================================
        packing_metadata = encrypted_updates[0].get('packing_metadata')
        if packing_metadata is not None and (
            packing_metadata.get('quant_bits') is not None
            or packing_metadata.get('layers') is not None
        ):
            logger.info(
                f"打包策略明文聚合: strategy={encrypted_updates[0].get('packing_metadata', {}).get('strategy', '?')}, "
                f"clients={len(encrypted_updates)}"
            )
            # 1) 解密所有客户端更新
            decrypted_updates = []
            shapes = encrypted_updates[0]['shapes']
            for update in encrypted_updates:
                decrypted = self.decrypt_model_update(update, shapes)
                decrypted_updates.append(decrypted)

            # 2) 明文加权平均（FedAvg 逻辑，必须归一化）
            # 修复：原代码漏除 total_weight，导致聚合结果被放大 N 倍（N=客户端数），
            # 权重幅值暴增 → 前向 logit 爆炸 → CE loss = NaN（CIFAR10/SVHN 不收敛根因）。
            # 与 MASER 路径(见上方 :837)保持一致。
            # 注意：decrypted_updates 现在可能包含 BatchNorm running statistics（通过 metadata
            # 明文保存），需要一并参与平均，不能只遍历 shapes。
            total_weight = sum(weights)
            aggregated = {}
            for name in sorted(decrypted_updates[0].keys()):
                agg = sum(
                    w * upd[name] for w, upd in zip(weights, decrypted_updates)
                ) / total_weight
                aggregated[name] = agg
            
            # 3) 重新打包并加密
            chunks, metadata = self.packing_strategy.pack(aggregated)
            ciphertexts = self.encryptor.encrypt_chunks(chunks)
            mask = [1] * len(ciphertexts)
            
            return {
                '__sparse__': True,
                'ciphertexts': ciphertexts,
                'mask': mask,
                'batch_size': self.batch_size,
                'total_elements': metadata.data['total_elements'],
                'shapes': metadata.data['shapes'],
                'offsets': metadata.data['offsets'],
                'strategy': encrypted_updates[0]['strategy'],
                'sparsity_rate': encrypted_updates[0]['sparsity_rate'],
                'packing_metadata': metadata.data,
            }

        # 强制密文聚合路径：所有打包策略均通过同态运算聚合
        # 服务器不解密客户端更新，仅执行密文级别的加权加法操作
        batch_num = len(encrypted_updates[0]['mask'])
        batch_size = encrypted_updates[0]['batch_size']

        aggregated_ciphertexts = []
        aggregated_mask = [0] * batch_num
        sum_weights_per_batch = [0.0] * batch_num

        for batch_idx in range(batch_num):
            batch_cts = []
            batch_weights = []

            for client_idx, update in enumerate(encrypted_updates):
                if update['mask'][batch_idx] == 1:
                    # 找到该客户端这个 batch 在 ciphertexts 中的索引
                    ct_idx = sum(update['mask'][:batch_idx])
                    batch_cts.append(update['ciphertexts'][ct_idx])
                    batch_weights.append(weights[client_idx])
                    sum_weights_per_batch[batch_idx] += weights[client_idx]

            if len(batch_cts) > 0:
                # 聚合时直接归一化（方案 B），解密时无需再除。
                total_w = sum(batch_weights)
                norm_weights = [w / total_w for w in batch_weights]
                aggregated_batch = self.evaluator.weighted_average(batch_cts, norm_weights)
                aggregated_ciphertexts.append(aggregated_batch)
                aggregated_mask[batch_idx] = 1

        # 详细记录每个客户端的 mask 和聚合后的 mask
        for cid, update in enumerate(encrypted_updates):
            active = [i for i, m in enumerate(update['mask']) if m == 1]
            logger.info(f"  Client #{cid} upload mask: {active} (count={len(active)})")
        agg_active = [i for i, m in enumerate(aggregated_mask) if m == 1]
        logger.info(f"  Aggregated active: {agg_active} (count={len(agg_active)})")
        
        logger.info(
            f"稀疏聚合: clients={len(encrypted_updates)}, "
            f"total_batches={batch_num}, aggregated_batches={sum(aggregated_mask)}"
        )

        result = {
            '__sparse__': True,
            'ciphertexts': aggregated_ciphertexts,
            'mask': aggregated_mask,
            'batch_size': batch_size,
            'total_elements': encrypted_updates[0]['total_elements'],
            'shapes': encrypted_updates[0]['shapes'],
            'offsets': encrypted_updates[0]['offsets'],
            'strategy': encrypted_updates[0]['strategy'],
            'sparsity_rate': encrypted_updates[0]['sparsity_rate'],
            '__sum_weights__': sum_weights_per_batch,
        }
        # MASER 压缩/对齐模式需要保留 indices 和 padded_len，供服务端解密后 0 填充恢复
        if encrypted_updates[0].get('strategy') == 'maser_param_mask':
            result['indices'] = encrypted_updates[0].get('indices', [])
            result['padded_len'] = encrypted_updates[0].get('padded_len', 0)
            result['maser_mode'] = encrypted_updates[0].get('maser_mode', '')
            result['num_params'] = encrypted_updates[0].get('num_params', 0)
        return result
    
    def get_key_distribution_size(self) -> int:
        """
        计算需要分发给每个客户端的公钥/计算密钥大小（字节）。
        不包含私钥。
        """
        return len(self.context.context.serialize(save_secret_key=False))

    def compute_aggregated_ct_size(self, num_participants: int = 1) -> int:
        """
        计算聚合密文大小（字节）。

        - 标准 CKKS（TenSEAL）：同态加法不改变密文大小，返回单个密文大小。
        - 多密钥 MASER（xMK-CKKS）：聚合密文大小随参与客户端数线性增长，
          委托给 xmkckks 后端计算。
        """
        if self.xmkckks is not None:
            return self.xmkckks.compute_aggregated_ct_size(num_participants)
        # 标准 CKKS：聚合不改变密文大小，懒加载计算单个密文大小
        if not hasattr(self, '_single_ct_size') or self._single_ct_size == 0:
            dummy = torch.zeros(self.batch_size, dtype=torch.float32)
            ct = self.encryptor.encrypt(dummy)
            self._single_ct_size = len(ct.serialize())
        return self._single_ct_size

    def compute_encrypted_update_size(self, encrypted_update: Dict[str, Any]) -> int:
        """计算加密更新的序列化大小（字节）"""
        total_size = 0
        if encrypted_update.get('__sparse__'):
            # 多密钥 MASER：xMKCKKS Ciphertext 通过 pickle 序列化测大小
            if encrypted_update.get('__multi_key__'):
                if self.xmkckks is not None:
                    return self.xmkckks.compute_xmkckks_update_size(encrypted_update['ciphertexts'])
                # 兜底：按 pickle 估算
                import pickle
                for ct in encrypted_update['ciphertexts']:
                    try:
                        total_size += len(pickle.dumps(ct, protocol=2))
                    except Exception:
                        total_size += 0
                return total_size
            # ESAFL PUREPY：ESHE 密文（CRT 表示的 numpy 数组）按实际字节数统计
            if encrypted_update.get('__purepy__'):
                for ct in encrypted_update['ciphertexts']:
                    total_size += ct.nbytes()
                return total_size

            # ESAFL NATIVE 多密钥：同样按 pickle 估算 xMK-CKKS Ciphertext 大小
            if encrypted_update.get('__native_multi_key__'):
                import pickle
                for ct in encrypted_update['ciphertexts']:
                    try:
                        total_size += len(pickle.dumps(ct, protocol=2))
                    except Exception:
                        total_size += 0
                return total_size

            for ct in encrypted_update['ciphertexts']:
                try:
                    total_size += len(ct.serialize())
                except AttributeError:
                    # ct 已经是序列化后的 bytes
                    total_size += len(ct)
                except Exception:
                    total_size += 0
            return total_size
        raise ValueError("加密更新必须使用 __sparse__ 格式（FedPHE 对齐）")


def create_ckks_manager_from_config(config_path: str = "config.yaml") -> CKKSManager:
    """从配置文件创建CKKS管理器"""
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    ckks_config = config.get('ckks', {})
    return CKKSManager(ckks_config)


if __name__ == "__main__":
    logger.info("测试CKKS加密功能...")
    context = CKKSContext(poly_modulus_degree=4096, 
                         coeff_mod_bit_sizes=[40, 20, 40],
                         global_scale=2**20)
    encryptor = CKKSEncryptor(context)
    decryptor = CKKSDecryptor(context)
    evaluator = CKKSEvaluator(context)
    data1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    data2 = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    ct1 = encryptor.encrypt(data1)
    ct2 = encryptor.encrypt(data2)
    ct_add = evaluator.add(ct1, ct2)
    result_add = decryptor.decrypt(ct_add)
    logger.info(f"加法结果: {result_add[:5]}")
    logger.info(f"期望结果: {data1 + data2}")
    ct_scalar = evaluator.multiply_scalar(ct1, 2.0)
    result_scalar = decryptor.decrypt(ct_scalar)
    logger.info(f"标量乘法结果: {result_scalar[:5]}")
    logger.info(f"期望结果: {data1 * 2.0}")
    logger.info("CKKS测试完成!")
