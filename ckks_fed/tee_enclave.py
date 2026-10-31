"""
TEE Enclave 模拟模块
===================

TESK-EGD (TEE-Encapsulated Single-Key with Enclave-Gated Decryption) 架构的 TEE 封装实现。

由于真实 TEE (Intel SGX/AMD SEV) 需要专用硬件和 SDK，本模块提供：
1. SIMULATION 模式：纯 Python 模拟 TEE 行为，用于验证架构流程
2. NATIVE 模式占位：定义了与真实 TEE 集成的接口（TODO）

核心设计：
- Enclave 内持有完整 sk，Server Host 无法访问
- 所有涉及 sk 的操作（解密、重新加密）在 Enclave 内执行
- Enclave 与 Host 通过受控接口通信（ECALL/OCALL 的 Python 模拟）
"""

import logging
import pickle
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from ckks_fed.crypto import CKKSContext, CKKSManager

logger = logging.getLogger(__name__)


# ============================================================================
# Enclave 安全状态（模拟 TEE 内存隔离）
# ============================================================================

@dataclass
class EnclaveState:
    """
    Enclave 内部状态（模拟 TEE 隔离内存）
    
    在真实 TEE 中，这些字段存储在 Enclave 的受保护内存中，
    Server Host 无法直接访问。
    """
    sk_context: Optional[CKKSContext] = None  # 密封的密钥上下文
    pk_context: Optional[CKKSContext] = None  # 公钥上下文
    model_state: Optional[Dict[str, Any]] = None  # 明文模型状态
    code_hash: Optional[str] = None  # 代码完整性哈希
    initialized: bool = False


class EnclaveMemory:
    """
    模拟 Enclave 隔离内存。
    
    在 SIMULATION 模式下：
    - 使用 Python 对象隔离（通过私有属性模拟）
    - Host 代码无法直接访问 _enclave_state
    
    在 NATIVE 模式下（TODO）：
    - 通过 SGX/SEV SDK 分配受保护内存页
    """
    
    def __init__(self):
        self._enclave_state = EnclaveState()
        self._access_log = []
    
    def _log_access(self, action: str, caller: str):
        """记录访问日志（模拟 TEE 审计）"""
        self._access_log.append({'action': action, 'caller': caller})
    
    def initialize(self, sealed_sk: bytes, pk_context: CKKSContext, 
                   code_hash: str, caller: str = 'host'):
        """
        初始化 Enclave（模拟 ECALL: ecall_init）
        
        在真实 TEE 中：
        - sealed_sk 由 TEE 密封密钥解封
        - code_hash 由远程证明验证
        """
        self._log_access('initialize', caller)
        
        # 解封 sk（模拟：直接反序列化）
        sk_ctx = CKKSContext.from_full_bytes(sealed_sk, poly_modulus_degree=8192)
        
        self._enclave_state.sk_context = sk_ctx
        self._enclave_state.pk_context = pk_context
        self._enclave_state.code_hash = code_hash
        self._enclave_state.initialized = True
        
        logger.info("Enclave 初始化完成")
    
    def is_initialized(self) -> bool:
        return self._enclave_state.initialized
    
    def get_pk_context(self, caller: str = 'host') -> CKKSContext:
        """获取公钥上下文（安全，不包含 sk）"""
        self._log_access('get_pk_context', caller)
        return self._enclave_state.pk_context
    
    def decrypt_and_update(self, 
                          ciphertexts: List[bytes],
                          weights: List[float],
                          ptopk_config: Dict,
                          caller: str = 'host') -> Tuple[bytes, bytes]:
        """
        在 Enclave 内执行解密、聚合、更新、重新加密（模拟 ECALL: ecall_process_round）
        
        这是核心安全操作，所有涉及 sk 的计算都在此函数内完成。
        
        Args:
            ciphertexts: 序列化的密文列表
            weights: 聚合权重
            ptopk_config: PTopk 配置
        
        Returns:
            (ct_global_bytes, enc_prefetch_bytes)
        """
        self._log_access('decrypt_and_update', caller)
        
        if not self._enclave_state.initialized:
            raise RuntimeError("Enclave 未初始化")
        
        import tenseal as ts
        
        # 1. 反序列化密文
        sk_ctx = self._enclave_state.sk_context
        cts = [ts.ckks_vector_from(sk_ctx.context, ct_bytes) for ct_bytes in ciphertexts]
        
        # 2. 同态聚合
        ct_agg = None
        for i, ct in enumerate(cts):
            weighted = ct * weights[i]
            ct_agg = weighted if ct_agg is None else ct_agg + weighted
        
        # 3. 解密（Enclave 内，Host 无法看到）
        plaintext = ct_agg.decrypt()
        
        # 4. PTopk 服务器累加器（明文操作）
        # 简化：直接返回明文，实际应调用 ptopk.server_update_plain()
        delta = plaintext
        
        # 5. 更新模型
        if self._enclave_state.model_state is None:
            self._enclave_state.model_state = {'delta': delta}
        else:
            self._enclave_state.model_state['delta'] = delta
        
        # 6. 重新加密全局状态
        pk_ctx = self._enclave_state.pk_context
        ct_global = ts.ckks_vector(pk_ctx.context, delta, scale=sk_ctx.global_scale)
        
        # 7. 计算预取内容并用会话密钥加密
        # 模拟：直接序列化明文，实际应使用 AES-GCM
        enc_prefetch = pickle.dumps(delta)
        
        return ct_global.serialize(), enc_prefetch
    
    def get_access_log(self) -> List[Dict]:
        """获取访问日志（模拟 TEE 审计日志）"""
        return self._access_log.copy()


# ============================================================================
# TEE 代理（Host 侧）
# ============================================================================

class TEEProxy:
    """
    TEE 代理（运行在 Server Host 上）
    
    职责：
    1. 管理 Enclave 生命周期（创建、初始化、销毁）
    2. 转发 ECALL 请求到 Enclave
    3. 验证 Enclave 代码完整性（远程证明）
    
    在 SIMULATION 模式下：
    - Enclave 是同一进程内的 Python 对象
    - 通过 EnclaveMemory 模拟隔离
    
    在 NATIVE 模式下（TODO）：
    - 通过 SGX uRTS 加载 .so Enclave
    - 通过 ECALL/OCALL 与 Enclave 通信
    """
    
    def __init__(self, mode: str = 'simulation'):
        self.mode = mode
        self.enclave = None
        self.initialized = False
    
    def create_enclave(self, sealed_sk_path: str, 
                      pk_context: CKKSContext,
                      expected_code_hash: str) -> bool:
        """
        创建并初始化 Enclave
        
        Args:
            sealed_sk_path: 密封私钥文件路径
            pk_context: 公钥上下文
            expected_code_hash: 预期的代码哈希（远程证明）
        
        Returns:
            初始化是否成功
        """
        if self.mode == 'simulation':
            # 模拟模式：创建 EnclaveMemory
            self.enclave = EnclaveMemory()
            
            # 加载密封密钥
            with open(sealed_sk_path, 'rb') as f:
                sealed_sk = f.read()
            
            # 初始化
            self.enclave.initialize(sealed_sk, pk_context, expected_code_hash)
            self.initialized = True
            
            logger.info("TEEProxy: Enclave 创建并初始化成功（模拟模式）")
            return True
        
        else:
            raise NotImplementedError("NATIVE 模式需要 SGX/SEV SDK")
    
    def verify_attestation(self, expected_hash: str) -> bool:
        """
        验证 Enclave 远程证明
        
        在 SIMULATION 模式下：
        - 直接比较 code_hash
        
        在 NATIVE 模式下：
        - 通过 Intel Attestation Service (IAS) 或 DCAP 验证 Quote
        """
        if not self.initialized:
            return False
        
        if self.mode == 'simulation':
            actual_hash = self.enclave._enclave_state.code_hash
            return actual_hash == expected_hash
        
        else:
            raise NotImplementedError("NATIVE 模式需要远程证明验证")
    
    def process_round(self,
                     ciphertexts: List[bytes],
                     weights: List[float],
                     ptopk_config: Dict = None) -> Tuple[bytes, bytes]:
        """
        委托 Enclave 处理一轮聚合
        
        这是 Host → Enclave 的 ECALL。
        
        Returns:
            (ct_global_bytes, enc_prefetch_bytes)
        """
        if not self.initialized:
            raise RuntimeError("Enclave 未初始化")
        
        return self.enclave.decrypt_and_update(
            ciphertexts, weights, ptopk_config or {}, caller='host'
        )
    
    def get_enclave_log(self) -> List[Dict]:
        """获取 Enclave 审计日志"""
        if not self.initialized:
            return []
        return self.enclave.get_access_log()
    
    def destroy_enclave(self):
        """销毁 Enclave"""
        self.enclave = None
        self.initialized = False
        logger.info("TEEProxy: Enclave 已销毁")


# ============================================================================
# 辅助函数
# ============================================================================

def compute_code_hash(enclave_code_path: str) -> str:
    """
    计算 Enclave 代码哈希（模拟 MRENCLAVE）
    
    在真实 SGX 中，MRENCLAVE 是 Enclave 代码和数据的 SHA-256 哈希。
    """
    with open(enclave_code_path, 'rb') as f:
        code = f.read()
    return hashlib.sha256(code).hexdigest()
