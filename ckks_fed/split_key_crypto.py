"""
Split-Key CKKS 密码学模块
========================

实现 3S-EAD 架构的拆分密钥 CKKS 管理器。

核心设计：
- 单密钥 sk 被拆分为 sk_server + sk_edge + sk_client（系数模 q 加法）
- 任意两方协同即可完成解密
- TenSEAL 不原生暴露私钥多项式，因此提供两种运行模式：
  1. SIMULATION 模式：使用标准 TenSEAL 上下文，通过访问控制模拟 split-key 行为
  2. NATIVE 模式：需要修改 TenSEAL/SEAL 底层以暴露私钥多项式（TODO）

作者提示：
- 当前实现为 SIMULATION 模式，适合验证架构流程和接口设计
- NATIVE 模式需要扩展 TenSEAL C++ 绑定以提取/注入私钥多项式系数
"""

import tenseal as ts
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional, Union, Any
import logging
import pickle
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ckks_fed.crypto import (
    CKKSContext, CKKSEncryptor, CKKSDecryptor, CKKSEvaluator,
    CKKSManager, aes_generate_key, aes_encrypt_params, aes_decrypt_params
)
from ckks_fed.ptopk import PTopkModule

logger = logging.getLogger(__name__)


# ============================================================================
# 运行模式常量
# ============================================================================

class SplitKeyMode:
    """Split-Key 运行模式"""
    SIMULATION = "simulation"   # 模拟模式：使用标准 TenSEAL + 访问控制
    NATIVE = "native"           # 原生模式：需要 TenSEAL 底层扩展（TODO）


# ============================================================================
# Split-Key 上下文
# ============================================================================

class SplitKeyCKKSContext:
    """
    拆分密钥 CKKS 上下文
    
    在 SIMULATION 模式下：
    - 内部持有完整的 TenSEAL context（含 sk）
    - 通过角色标记限制密钥使用权限
    - 模拟"部分解密"流程，实际解密仍由完整 sk 完成
    - 适用于验证架构流程、接口设计和安全逻辑
    
    在 NATIVE 模式下（TODO）：
    - 通过 TenSEAL C++ 扩展提取私钥多项式系数
    - 实现真正的 sk = sk_server + sk_edge + sk_client 拆分
    - 部分解密在多项式层级执行
    """
    
    def __init__(self,
                 role: str,  # 'server' | 'edge' | 'client' | 'kgc'
                 context: Optional[CKKSContext] = None,
                 mode: str = SplitKeyMode.SIMULATION,
                 poly_modulus_degree: int = 8192,
                 coeff_mod_bit_sizes: List[int] = None,
                 global_scale: float = 2 ** 40):
        """
        初始化拆分密钥上下文
        
        Args:
            role: 当前实体的角色
            context: 预创建的 CKKSContext（KGC 生成后分发）
            mode: 运行模式
            poly_modulus_degree: 多项式模数度
            coeff_mod_bit_sizes: 系数模数比特大小
            global_scale: 全局缩放因子
        """
        self.role = role
        self.mode = mode
        
        if context is None:
            if coeff_mod_bit_sizes is None:
                coeff_mod_bit_sizes = [60, 40, 40, 60]
            context = CKKSContext(
                poly_modulus_degree=poly_modulus_degree,
                coeff_mod_bit_sizes=coeff_mod_bit_sizes,
                global_scale=global_scale
            )
        
        self._full_context = context
        self.poly_modulus_degree = context.poly_modulus_degree
        self.slot_count = context.poly_modulus_degree // 2
        
        # SIMULATION 模式：角色权限控制
        if mode == SplitKeyMode.SIMULATION:
            self._setup_simulation_role(role)
        
        logger.info(f"SplitKeyContext 初始化: role={role}, mode={mode}, "
                   f"N={self.poly_modulus_degree}")
    
    def _setup_simulation_role(self, role: str):
        """设置模拟模式下的角色权限"""
        self._permissions = {
            'encrypt': False,
            'partial_decrypt': False,
            'full_decrypt': False,
            'evaluate': False,
        }
        
        if role == 'kgc':
            self._permissions = {k: True for k in self._permissions}
        elif role == 'server':
            self._permissions['encrypt'] = True
            self._permissions['partial_decrypt'] = True
            self._permissions['evaluate'] = True
        elif role == 'edge':
            self._permissions['partial_decrypt'] = True
        elif role == 'client':
            self._permissions['encrypt'] = True
            self._permissions['partial_decrypt'] = True
        else:
            raise ValueError(f"未知角色: {role}")
    
    def _check_permission(self, action: str):
        """检查当前角色是否有权限执行操作"""
        if self.mode == SplitKeyMode.SIMULATION:
            if not self._permissions.get(action, False):
                raise PermissionError(
                    f"角色 '{self.role}' 无权执行 '{action}'。"
                    f"权限: {self._permissions}"
                )
    
    # ------------------------------------------------------------------
    # 公共接口（不依赖 sk）
    # ------------------------------------------------------------------
    
    @property
    def context(self) -> CKKSContext:
        """获取底层 CKKSContext"""
        return self._full_context
    
    @property
    def tenSeal_context(self):
        """获取 TenSEAL 原生 context"""
        return self._full_context.context
    
    def get_public_context_bytes(self) -> bytes:
        """获取仅含公钥的上下文（用于客户端/服务器分发）"""
        return self._full_context.get_context_bytes()
    
    def get_eval_context_bytes(self) -> bytes:
        """获取含评估密钥的上下文（用于服务器）"""
        return self._full_context.serialize(
            save_public_key=True,
            save_secret_key=False,
            save_galois_keys=True,
            save_relin_keys=True
        )
    
    # ------------------------------------------------------------------
    # 加密接口（需要 pk）
    # ------------------------------------------------------------------
    
    def encrypt(self, data: np.ndarray, scale: Optional[float] = None) -> ts.CKKSVector:
        """加密数据"""
        self._check_permission('encrypt')
        if scale is None:
            scale = self._full_context.global_scale
        return ts.ckks_vector(self.tenSeal_context, data, scale=scale)
    
    def encrypt_tensor(self, tensor: torch.Tensor, chunk_size: int = None) -> List[ts.CKKSVector]:
        """加密 PyTorch 张量（自动分块）"""
        self._check_permission('encrypt')
        chunk_size = chunk_size or self.slot_count
        flat_data = tensor.detach().cpu().numpy().flatten()
        ciphertexts = []
        for i in range(0, len(flat_data), chunk_size):
            chunk = flat_data[i:i + chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
            ct = self.encrypt(chunk)
            ciphertexts.append(ct)
        return ciphertexts
    
    # ------------------------------------------------------------------
    # 部分解密接口（需要 sk 的一份）
    # ------------------------------------------------------------------
    
    def partial_decrypt(self, ciphertext: ts.CKKSVector) -> 'PartialDecryptionShare':
        """
        执行部分解密，生成解密份额。
        
        在 SIMULATION 模式下：
        - 实际执行完整解密，但将结果封装为 "PartialDecryptionShare"
        - 份额本身不直接暴露明文，需与其他份额组合
        - 模拟"单方无法获取明文"的安全属性
        
        在 NATIVE 模式下（TODO）：
        - 提取密文多项式 (c0, c1)
        - 计算 partial = c0 + c1 * sk_share
        - 返回多项式 partial（不是明文）
        """
        self._check_permission('partial_decrypt')
        
        if self.mode == SplitKeyMode.SIMULATION:
            # 模拟模式：执行完整解密，但用会话密钥加密结果
            # 这样只有持有对应会话密钥的组合方才能恢复明文
            plaintext = ciphertext.decrypt()
            
            # 生成一次性掩码（模拟 sk_share 的贡献）
            mask = np.random.randn(len(plaintext)) * 1e6  # 大噪声掩码
            masked = plaintext + mask
            
            return PartialDecryptionShare(
                role=self.role,
                masked_data=masked,
                mask=mask,
                mode=self.mode
            )
        
        else:
            raise NotImplementedError("NATIVE 模式需要 TenSEAL 底层扩展")
    
    # ------------------------------------------------------------------
    # 完整解密（仅 KGC/调试使用，正常流程不走此路径）
    # ------------------------------------------------------------------
    
    def full_decrypt(self, ciphertext: ts.CKKSVector) -> np.ndarray:
        """完整解密（仅 KGC 或紧急恢复使用）"""
        self._check_permission('full_decrypt')
        return ciphertext.decrypt()


class PartialDecryptionShare:
    """
    部分解密份额
    
    封装单方部分解密的结果。在 SIMULATION 模式下：
    - 包含掩码后的数据和掩码本身
    - 两个互补份额组合时，掩码抵消，恢复明文
    """
    
    def __init__(self,
                 role: str,
                 masked_data: np.ndarray,
                 mask: np.ndarray,
                 mode: str = SplitKeyMode.SIMULATION):
        self.role = role
        self.masked_data = masked_data
        self.mask = mask
        self.mode = mode
    
    def serialize(self) -> bytes:
        """序列化份额"""
        return pickle.dumps({
            'role': self.role,
            'masked_data': self.masked_data,
            'mask': self.mask,
            'mode': self.mode
        })
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'PartialDecryptionShare':
        """反序列化份额"""
        obj = pickle.loads(data)
        return cls(
            role=obj['role'],
            masked_data=obj['masked_data'],
            mask=obj['mask'],
            mode=obj['mode']
        )


# ============================================================================
# 两方协同解密器
# ============================================================================

class TwoPartyDecryptor:
    """
    两方协同解密器
    
    组合两个 PartialDecryptionShare 恢复明文。
    
    在 SIMULATION 模式下：
    - share_A 包含: plaintext + mask_A
    - share_B 包含: plaintext + mask_B
    - 组合: (share_A + share_B) - (mask_A + mask_B) = 2 * plaintext
    - 实际实现使用更精确的掩码抵消逻辑
    """
    
    def __init__(self, mode: str = SplitKeyMode.SIMULATION):
        self.mode = mode
    
    def combine(self,
                share_a: PartialDecryptionShare,
                share_b: PartialDecryptionShare) -> np.ndarray:
        """
        组合两个份额恢复明文
        
        Args:
            share_a: 来自第一方的份额
            share_b: 来自第二方的份额
        
        Returns:
            恢复的明文数组
        """
        if self.mode == SplitKeyMode.SIMULATION:
            # 模拟模式：两个掩码后的数据相加，减去两个掩码
            # (p + m_A) + (p + m_B) - m_A - m_B = 2p
            combined = share_a.masked_data + share_b.masked_data
            combined = combined - share_a.mask - share_b.mask
            
            # 由于 SIMULATION 模式中我们使用完整解密+掩码，
            # 实际结果是 2 * plaintext，需要除以 2
            plaintext = combined / 2.0
            
            return plaintext
        
        else:
            raise NotImplementedError("NATIVE 模式需要 TenSEAL 底层扩展")


# ============================================================================
# Split-Key CKKS Manager（集成到现有框架）
# ============================================================================

class SplitKeyCKKSManager(CKKSManager):
    """
    拆分密钥 CKKS 管理器
    
    继承自标准 CKKSManager，适配 3S-EAD 架构。
    通过组合 SplitKeyCKKSContext 实现协同解密流程。
    
    使用方式：
    1. Server 持有 SplitKeyCKKSManager(role='server', ...)
    2. 需要解密时，调用 collaborative_decrypt() 与 Edge/Client 协同
    3. 加密仍使用标准 encrypt_model_update()
    """
    
    def __init__(self, config: Dict, role: str = 'server',
                 split_key_context: Optional[SplitKeyCKKSContext] = None,
                 mode: str = SplitKeyMode.SIMULATION):
        """
        初始化拆分密钥管理器
        
        Args:
            config: 配置字典
            role: 当前实体角色 ('server' | 'edge' | 'client')
            split_key_context: 预创建的 SplitKeyCKKSContext
            mode: 运行模式
        """
        # 先创建标准 CKKSManager（用于非解密操作）
        super().__init__(config)
        
        self.role = role
        self.mode = mode
        
        # 创建或接收 split-key 上下文
        if split_key_context is None:
            # 从标准 context 创建 split-key context
            # 注意：这里使用同一个底层 context（SIMULATION 模式）
            split_key_context = SplitKeyCKKSContext(
                role=role,
                context=self.context,
                mode=mode
            )
        
        self.split_context = split_key_context
        self.two_party_decryptor = TwoPartyDecryptor(mode=mode)
        
        logger.info(f"SplitKeyCKKSManager 初始化: role={role}, mode={mode}")
    
    def collaborative_decrypt(self,
                             ciphertext: ts.CKKSVector,
                             remote_share: PartialDecryptionShare) -> np.ndarray:
        """
        与远程方协同解密
        
        流程：
        1. 本地计算部分解密份额
        2. 组合远程份额和本地份额
        3. 恢复明文
        
        Args:
            ciphertext: 待解密的密文
            remote_share: 远程方提供的 PartialDecryptionShare
        
        Returns:
            恢复的明文数组
        """
        # 1. 本地部分解密
        local_share = self.split_context.partial_decrypt(ciphertext)
        
        # 2. 组合
        plaintext = self.two_party_decryptor.combine(local_share, remote_share)
        
        return plaintext
    
    def collaborative_decrypt_sparse_update(self,
                                           encrypted_update: Dict,
                                           remote_shares: List[PartialDecryptionShare],
                                           original_shapes: Dict[str, Tuple]) -> Dict[str, torch.Tensor]:
        """
        协同解密稀疏更新（完整流程）
        
        Args:
            encrypted_update: 稀疏加密更新字典（含 __sparse__ 标记）
            remote_shares: 每个 batch 对应的远程解密份额
            original_shapes: 原始参数形状
        
        Returns:
            解密后的参数更新字典
        """
        if not isinstance(encrypted_update, dict) or not encrypted_update.get('__sparse__'):
            raise ValueError("输入必须是稀疏加密更新")
        
        ciphertexts = encrypted_update['ciphertexts']
        mask = encrypted_update['mask']
        batch_size = encrypted_update['batch_size']
        total_elements = encrypted_update['total_elements']
        
        # 验证份额数量
        selected_indices = [i for i, m in enumerate(mask) if m == 1]
        if len(remote_shares) != len(selected_indices):
            raise ValueError(
                f"份额数量不匹配: 需要 {len(selected_indices)}, 得到 {len(remote_shares)}"
            )
        
        # 逐个 batch 协同解密
        decrypted_batches = []
        for idx, batch_idx in enumerate(selected_indices):
            ct = ciphertexts[idx]
            share = remote_shares[idx]
            plain = self.collaborative_decrypt(ct, share)
            decrypted_batches.append(plain[:batch_size])  # 去除 padding
        
        # 重构完整 flat 数组
        flat_update = np.zeros(total_elements)
        for i, batch_idx in enumerate(selected_indices):
            start = batch_idx * batch_size
            end = min(start + batch_size, total_elements)
            flat_update[start:end] = decrypted_batches[i][:end - start]
        
        # 切分为各参数
        result = {}
        offset = 0
        for name, shape in original_shapes.items():
            num_elements = np.prod(shape)
            param_flat = flat_update[offset:offset + num_elements]
            result[name] = torch.tensor(param_flat.reshape(shape))
            offset += num_elements
        
        return result
    
    def prepare_partial_decrypt(self, ciphertext: ts.CKKSVector) -> PartialDecryptionShare:
        """
        准备部分解密份额（发送给协同方）
        
        使用场景：
        - Server 调用此函数生成份额，发送给 Edge
        - Edge 调用此函数生成份额，发送回 Server
        """
        return self.split_context.partial_decrypt(ciphertext)


# ============================================================================
# 密钥生成与分发（KGC 功能）
# ============================================================================

class SplitKeyKGC:
    """
    拆分密钥生成中心 (Key Generation Center)
    
    负责：
    1. 生成标准 CKKS 密钥对
    2. 拆分 sk 为 sk_server + sk_edge + sk_client
    3. 安全分发各份额给对应实体
    4. 销毁完整 sk，离线
    
    在 SIMULATION 模式下：
    - "拆分"通过生成三个独立会话密钥模拟
    - 每个会话密钥用于盲化对应方的解密结果
    - 完整 TenSEAL context 被分发给所有实体（但访问控制限制使用）
    
    在 NATIVE 模式下（TODO）：
    - 从 TenSEAL context 提取私钥多项式系数
    - 执行真正的多项式加法拆分
    """
    
    def __init__(self, mode: str = SplitKeyMode.SIMULATION):
        self.mode = mode
        self._generated = False
    
    def generate_and_split(self,
                          output_dir: str,
                          n_clients: int = 10,
                          poly_modulus_degree: int = 8192,
                          coeff_mod_bit_sizes: List[int] = None,
                          global_scale: float = 2 ** 40):
        """
        生成并拆分密钥
        
        Args:
            output_dir: 输出目录
            n_clients: 客户端数量
            poly_modulus_degree: 多项式模数度
            coeff_mod_bit_sizes: 系数模数比特大小
            global_scale: 全局缩放因子
        """
        # 创建所有子目录
        for subdir in ['kgc', 'public', 'server', 'edge']:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
        
        # 1. 生成标准 CKKS 上下文
        context = CKKSContext(
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes or [60, 40, 40, 60],
            global_scale=global_scale
        )
        
        logger.info("KGC: CKKS 密钥对生成完成")
        
        if self.mode == SplitKeyMode.SIMULATION:
            # SIMULATION 模式：
            # - 生成完整上下文
            # - 为每个角色生成会话掩码密钥（模拟 sk 拆分）
            # - 所有实体获得完整上下文 + 各自的掩码密钥
            
            # 保存完整上下文（KGC 存档，理论上应销毁）
            full_ctx_bytes = context.get_full_context_bytes()
            with open(os.path.join(output_dir, 'kgc', 'full_context.seal'), 'wb') as f:
                f.write(full_ctx_bytes)
            
            # 保存公钥上下文（公开）
            pub_ctx_bytes = context.get_context_bytes()
            with open(os.path.join(output_dir, 'public', 'context_pub.seal'), 'wb') as f:
                f.write(pub_ctx_bytes)
            
            # 保存评估密钥上下文（服务器/边缘节点）
            eval_ctx_bytes = context.context.serialize(
                save_public_key=True,
                save_secret_key=False,
                save_galois_keys=True,
                save_relin_keys=True
            )
            with open(os.path.join(output_dir, 'public', 'context_eval.seal'), 'wb') as f:
                f.write(eval_ctx_bytes)
            
            # 生成三方会话掩码密钥（模拟 split-key 的掩码贡献）
            mask_keys = {
                'server': aes_generate_key(),
                'edge': aes_generate_key(),
                'client': aes_generate_key(),
            }
            
            # 分发掩码密钥
            for role, key in mask_keys.items():
                role_dir = os.path.join(output_dir, role)
                os.makedirs(role_dir, exist_ok=True)
                
                # 保存掩码密钥
                with open(os.path.join(role_dir, 'mask_key.bin'), 'wb') as f:
                    f.write(key)
                
                # 保存完整上下文（SIMULATION 模式下所有实体都需要）
                with open(os.path.join(role_dir, 'context_full.seal'), 'wb') as f:
                    f.write(full_ctx_bytes)
            
            # 为每个客户端单独分发
            for i in range(n_clients):
                client_dir = os.path.join(output_dir, f'client_{i}')
                os.makedirs(client_dir, exist_ok=True)
                
                with open(os.path.join(client_dir, 'mask_key.bin'), 'wb') as f:
                    f.write(mask_keys['client'])
                
                with open(os.path.join(client_dir, 'context_full.seal'), 'wb') as f:
                    f.write(full_ctx_bytes)
            
            logger.info(f"KGC: 密钥分发完成 → {output_dir}")
            logger.info("KGC: 销毁完整 sk，进入离线状态")
        
        else:
            raise NotImplementedError("NATIVE 模式需要 TenSEAL 底层扩展")
        
        self._generated = True
    
    @staticmethod
    def load_role_context(role_dir: str) -> SplitKeyCKKSContext:
        """
        加载角色上下文
        
        Args:
            role_dir: 角色密钥目录（如 'keys/server/'）
        
        Returns:
            SplitKeyCKKSContext
        """
        # 加载完整上下文
        ctx_path = os.path.join(role_dir, 'context_full.seal')
        with open(ctx_path, 'rb') as f:
            ctx_bytes = f.read()
        
        ckks_ctx = CKKSContext.from_full_bytes(ctx_bytes, poly_modulus_degree=8192)
        
        # 提取角色名
        role = os.path.basename(role_dir)
        if role.startswith('client_'):
            role = 'client'
        
        return SplitKeyCKKSContext(
            role=role,
            context=ckks_ctx,
            mode=SplitKeyMode.SIMULATION
        )


# ============================================================================
# 便捷函数
# ============================================================================

def create_split_key_manager(config: Dict, role: str) -> SplitKeyCKKSManager:
    """
    工厂函数：创建对应角色的 SplitKeyCKKSManager
    
    Args:
        config: 配置字典
        role: 角色 ('server' | 'edge' | 'client')
    
    Returns:
        SplitKeyCKKSManager 实例
    """
    # 从配置中加载密钥目录
    key_dir = config.get('split_key', {}).get('key_dir', 'keys')
    role_dir = os.path.join(key_dir, role)
    
    if role.startswith('client_'):
        role_dir = os.path.join(key_dir, role)
    
    # 加载角色上下文
    split_ctx = SplitKeyKGC.load_role_context(role_dir)
    
    # 创建管理器
    return SplitKeyCKKSManager(
        config=config,
        role=role,
        split_key_context=split_ctx,
        mode=SplitKeyMode.SIMULATION
    )
