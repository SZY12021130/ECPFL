"""
Threshold CKKS 密码学模块
========================

SSCKKS-tn (Shamir-Shared CKKS with t-of-n Threshold Decryption) 架构实现。

核心设计：
- KGC 将 sk 使用 (t,n)-Shamir 秘密共享分成 n 份
- 每个 Client i 持有 share_i
- 聚合密文需要至少 t 个 Client 提供部分解密份额才能恢复明文
- 任何少于 t 个份额无法获得 sk 或明文的任何信息

实现模式：
1. SIMULATION 模式：纯 Python 模拟，使用标准 TenSEAL + 掩码模拟
2. NATIVE 模式占位：需要 TenSEAL 底层扩展以支持私钥多项式提取（TODO）
"""

import logging
import random
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

import numpy as np

from ckks_fed.crypto import CKKSContext, CKKSManager

logger = logging.getLogger(__name__)


# ============================================================================
# Shamir 秘密共享
# ============================================================================

class ShamirSecretSharing:
    """
    Shamir (t, n) 门限秘密共享
    
    在有限域 Z_p 上实现，其中 p 为大素数。
    """
    
    def __init__(self, prime: int = None):
        """
        初始化 Shamir 秘密共享
        
        Args:
            prime: 有限域素数。若为 None，使用默认大素数。
        """
        if prime is None:
            # 使用一个接近 2^128 的大素数
            self.prime = 2**127 - 1  # 梅森素数
        else:
            self.prime = prime
    
    def split(self, secret: int, n: int, t: int) -> List[Tuple[int, int]]:
        """
        将 secret 分成 n 份，任意 t 份可恢复。
        
        算法：
        1. 随机生成 t-1 次多项式：f(x) = secret + a_1*x + ... + a_{t-1}*x^{t-1}
        2. 计算 share_i = f(i) for i = 1, ..., n
        
        Args:
            secret: 要共享的秘密（整数）
            n: 总份额数
            t: 门限值（最少需要的份额数）
        
        Returns:
            [(1, share_1), (2, share_2), ..., (n, share_n)]
        """
        if t > n:
            raise ValueError(f"门限 t ({t}) 不能大于总份额 n ({n})")
        if t < 2:
            raise ValueError("门限 t 至少为 2")
        
        # 随机生成多项式系数（a_0 = secret）
        coeffs = [secret] + [
            random.randint(1, self.prime - 1) for _ in range(t - 1)
        ]
        
        # 计算 n 个份额
        shares = []
        for i in range(1, n + 1):
            share = sum(
                c * pow(i, idx, self.prime) 
                for idx, c in enumerate(coeffs)
            ) % self.prime
            shares.append((i, share))
        
        return shares
    
    def reconstruct(self, shares: List[Tuple[int, int]]) -> int:
        """
        Lagrange 插值恢复 secret。
        
        给定至少 t 个份额，恢复原始秘密。
        
        Args:
            shares: [(x_1, y_1), (x_2, y_2), ...]
        
        Returns:
            恢复的秘密
        """
        if len(shares) < 2:
            raise ValueError("至少需要 2 个份额才能恢复")
        
        secret = 0
        
        for i, (x_i, y_i) in enumerate(shares):
            # 计算 Lagrange 基多项式在 x=0 处的值：
            # λ_i(0) = Π_{j≠i} (0 - x_j) / (x_i - x_j)
            numerator = 1
            denominator = 1
            
            for j, (x_j, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime
            
            # λ_i = numerator / denominator (mod prime)
            lagrange_coeff = (numerator * pow(denominator, -1, self.prime)) % self.prime
            
            secret = (secret + y_i * lagrange_coeff) % self.prime
        
        return secret


# ============================================================================
# 阈值 CKKS 管理器
# ============================================================================

@dataclass
class DecryptionShare:
    """部分解密份额"""
    client_id: int
    share_id: int
    share_value: int
    partial_result: np.ndarray  # 部分解密结果（模拟模式下为掩码后的数据）


class ThresholdCKKSManager:
    """
    阈值 CKKS 管理器
    
    管理阈值解密流程：
    1. 加密：使用全局 pk（标准 CKKS）
    2. 部分解密：每个 Client 使用 share_i 生成解密份额
    3. 组合：收集至少 t 个份额，恢复明文
    
    在 SIMULATION 模式下：
    - 所有 Client 共享同一个 TenSEAL context（含 sk）
    - 部分解密通过掩码模拟：每个份额添加不同的随机噪声
    - 组合时噪声抵消，恢复明文
    """
    
    def __init__(self,
                 config: Dict,
                 t: int,
                 n: int,
                 shares: Optional[List[Tuple[int, int]]] = None,
                 mode: str = 'simulation'):
        """
        初始化阈值 CKKS 管理器
        
        Args:
            config: 配置字典
            t: 门限值
            n: 总客户端数
            shares: 预计算的份额列表（可选）
            mode: 运行模式
        """
        self.config = config
        self.t = t
        self.n = n
        self.mode = mode
        
        # 创建标准 CKKS 上下文
        self.context = CKKSContext(
            poly_modulus_degree=config.get('poly_modulus_degree', 8192),
            coeff_mod_bit_sizes=config.get('coeff_mod_bit_sizes', [60, 40, 40, 60]),
            global_scale=config.get('global_scale', 2**40)
        )
        
        # Shamir 秘密共享
        self.sss = ShamirSecretSharing()
        
        # 份额管理
        self.shares = shares or []
        
        logger.info(f"ThresholdCKKSManager 初始化: t={t}, n={n}, mode={mode}")
    
    def generate_shares(self, secret_seed: int = None) -> List[Tuple[int, int]]:
        """
        生成份额。
        
        在 SIMULATION 模式下：
        - 使用随机数作为 secret
        - 生成 (t, n) 份额
        
        在 NATIVE 模式下（TODO）：
        - 从 TenSEAL context 提取 sk 多项式系数
        - 对每个系数执行 Shamir 分割
        """
        if secret_seed is None:
            secret_seed = random.randint(1, self.sss.prime - 1)
        
        self.shares = self.sss.split(secret_seed, self.n, self.t)
        logger.info(f"生成 {self.n} 个份额，门限 t={self.t}")
        return self.shares
    
    def encrypt(self, data: np.ndarray) -> bytes:
        """加密数据（标准 CKKS）"""
        import tenseal as ts
        ckks_vector = ts.ckks_vector(
            self.context.context, data, scale=self.context.global_scale
        )
        return ckks_vector.serialize()
    
    def partial_decrypt(self, 
                       ciphertext_bytes: bytes,
                       share_id: int,
                       share_value: int) -> DecryptionShare:
        """
        执行部分解密。
        
        在 SIMULATION 模式下：
        1. 使用完整 sk 解密（内部操作）
        2. 添加基于 share_value 的确定性掩码
        3. 返回掩码后的部分结果
        
        在 NATIVE 模式下（TODO）：
        - 提取密文多项式 (c0, c1)
        - 计算 partial = c1 * share_value * λ_i
        """
        import tenseal as ts
        
        # 解密（模拟：完整解密）
        ciphertext = ts.ckks_vector_from(self.context.context, ciphertext_bytes)
        plaintext = ciphertext.decrypt()
        
        # 生成确定性掩码（基于 share_value）
        np.random.seed(share_value % (2**32))
        mask = np.random.randn(len(plaintext)) * 1e6
        
        masked_plaintext = plaintext + mask
        
        return DecryptionShare(
            client_id=share_id,
            share_id=share_id,
            share_value=share_value,
            partial_result=masked_plaintext
        )
    
    def combine(self, 
               shares: List[DecryptionShare],
               ciphertext_bytes: bytes) -> np.ndarray:
        """
        组合部分解密份额恢复明文。
        
        在 SIMULATION 模式下：
        1. 收集所有掩码后的部分结果
        2. 使用 Shamir 重构恢复掩码
        3. 从组合结果中减去掩码
        
        在 NATIVE 模式下（TODO）：
        - m = c0 + Σ partial_i
        """
        if len(shares) < self.t:
            raise ValueError(
                f"份额不足: 需要至少 {self.t} 个，实际 {len(shares)}"
            )
        
        # 使用 Shamir 重构恢复秘密（用于生成掩码）
        shamir_shares = [(s.share_id, s.share_value) for s in shares]
        reconstructed_secret = self.sss.reconstruct(shamir_shares)
        
        # 重新生成掩码
        np.random.seed(reconstructed_secret % (2**32))
        mask = np.random.randn(len(shares[0].partial_result)) * 1e6
        
        # 组合：取平均值然后减去掩码
        combined = sum(s.partial_result for s in shares) / len(shares)
        plaintext = combined - mask
        
        return plaintext
    
    def verify_share(self, share: DecryptionShare, 
                    ciphertext_bytes: bytes) -> bool:
        """
        验证部分解密份额的有效性。
        
        在 SIMULATION 模式下：
        - 验证 share_id 在有效范围内
        
        在 NATIVE 模式下（TODO）：
        - 使用零知识证明验证份额正确性
        """
        return 1 <= share.share_id <= self.n


# ============================================================================
# 辅助函数
# ============================================================================

def create_threshold_setup(n_clients: int, 
                          threshold_ratio: float = 0.67,
                          config: Dict = None) -> Tuple[ThresholdCKKSManager, List[Tuple[int, int]]]:
    """
    创建阈值 CKKS 设置。
    
    Args:
        n_clients: 客户端数量
        threshold_ratio: 门限比例（默认 2/3）
        config: CKKS 配置
    
    Returns:
        (manager, shares)
    """
    t = max(2, int(n_clients * threshold_ratio))
    
    config = config or {
        'poly_modulus_degree': 8192,
        'coeff_mod_bit_sizes': [60, 40, 40, 60],
        'global_scale': 2**40
    }
    
    manager = ThresholdCKKSManager(config, t=t, n=n_clients)
    shares = manager.generate_shares()
    
    return manager, shares
