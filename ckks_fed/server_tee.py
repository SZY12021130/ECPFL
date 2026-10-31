"""
TEE Aggregation Server 模块
===========================

TESK-EGD v2 架构下 Server 侧的适配实现。

核心设计：
- Server Host 不持有 sk，所有涉及 sk 的操作委托给 TEE Enclave
- TEE 内执行：聚合 -> 解密 -> PTopk -> 更新 -> 重新加密 -> 预取加密
- 预取 delta 始终为密文状态，Client 用本地 sk 解密
- 支持 SIMULATION 模式（纯 Python 模拟）和 NATIVE 模式占位（真实 TEE）

与 PAMP 集成点：
- 继承自 PrefetchAggregationServer
- 重写 update_global_model() 为 ECALL 委托模式
- 重写 _update_encrypted_global_state() 为 TEE 内执行
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import torch

from ckks_fed.server import PrefetchAggregationServer
from ckks_fed.crypto import CKKSManager, CKKSContext
from ckks_fed.tee_enclave import TEEProxy, EnclaveMemory

logger = logging.getLogger(__name__)


class TEEAggregationServer(PrefetchAggregationServer):
    """
    TEE 架构下的聚合服务器
    
    与标准 PrefetchAggregationServer 的区别：
    1. 不持有 sk（sk 密封在 TEE 内）
    2. update_global_model() 委托 TEE 执行核心逻辑
    3. 预取内容始终为密文状态
    
    SIMULATION 模式：
    - TEE 是同一进程内的 Python 对象（EnclaveMemory）
    - 用于验证架构流程和接口设计
    
    NATIVE 模式（TODO）：
    - 通过 SGX/SEV SDK 加载真实 Enclave
    """
    
    def __init__(self, config: Dict):
        """
        初始化 TEE 聚合服务器
        
        Args:
            config: 配置字典，需包含 tee 配置块
        """
        # 初始化基础属性（但不创建标准 CKKSManager，因为不持有 sk）
        self.config = config
        self.model = None
        self.global_params = {}
        self.round_num = 0
        
        # TEE 配置
        tee_config = config.get('tee', {})
        self.tee_enabled = tee_config.get('enable', False)
        self.tee_mode = tee_config.get('mode', 'simulation')
        
        if self.tee_enabled:
            # 初始化 TEE 代理
            self.tee_proxy = self._init_tee_proxy(tee_config)
            
            # Server Host 仅持有 pk/evk 上下文（无 sk）
            self.ckks_manager = self._init_host_ckks_manager(config)
            
            # 预取密文存储（按客户端索引）
            self.prefetch_store = {}
            
            logger.info(f"TEEAggregationServer 初始化: mode={self.tee_mode}, TEE={self.tee_enabled}")
        else:
            # 回退到标准模式
            self.tee_proxy = None
            super().__init__(config)
    
    def _init_tee_proxy(self, tee_config: Dict) -> TEEProxy:
        """初始化 TEE 代理"""
        proxy = TEEProxy(mode=self.tee_mode)
        
        if self.tee_mode == 'simulation':
            # SIMULATION 模式：创建本地 EnclaveMemory
            enclave = EnclaveMemory()
            
            # 加载密封密钥（从 KGC 生成的密钥目录）
            key_dir = tee_config.get('key_dir', 'keys/tee')
            sealed_sk_path = os.path.join(key_dir, 'sealed_sk.bin')
            
            if os.path.exists(sealed_sk_path):
                with open(sealed_sk_path, 'rb') as f:
                    sealed_sk = f.read()
                
                # 加载公钥上下文
                pub_ctx_path = os.path.join(key_dir, 'public', 'context_pub.seal')
                if os.path.exists(pub_ctx_path):
                    with open(pub_ctx_path, 'rb') as f:
                        pub_ctx = CKKSContext.from_bytes(f.read())
                else:
                    # 创建新的公钥上下文
                    pub_ctx = CKKSContext(
                        poly_modulus_degree=tee_config.get('poly_modulus_degree', 8192),
                        coeff_mod_bit_sizes=tee_config.get('coeff_mod_bit_sizes', [60, 40, 40, 60]),
                        global_scale=tee_config.get('global_scale', 2**40)
                    )
                
                code_hash = tee_config.get('expected_mrenclave', 'simulation_hash')
                enclave.initialize(sealed_sk, pub_ctx, code_hash)
                proxy.enclave = enclave
                proxy.initialized = True
                logger.info("TEE SIMULATION 模式初始化完成")
            else:
                logger.warning(f"密封密钥不存在: {sealed_sk_path}，TEE 未初始化")
        
        return proxy
    
    def _init_host_ckks_manager(self, config: Dict) -> CKKSManager:
        """
        初始化 Server Host 侧的 CKKSManager（仅 pk/evk，无 sk）
        
        用于：序列化/反序列化密文、同态运算准备
        """
        # 创建仅含公钥的上下文
        pub_ctx = CKKSContext(
            poly_modulus_degree=config.get('ckks', {}).get('poly_modulus_degree', 8192),
            coeff_mod_bit_sizes=config.get('ckks', {}).get('coeff_mod_bit_sizes', [60, 40, 40, 60]),
            global_scale=config.get('ckks', {}).get('global_scale', 2**40)
        )
        pub_ctx.context.make_context_public()  # 移除私钥
        
        # 创建 CKKSManager（标准初始化，但 sk 已移除）
        return CKKSManager(config, context=pub_ctx)
    
    def update_global_model(self, encrypted_updates: List[Dict], 
                           weights: List[float]) -> bool:
        """
        重写：委托 TEE 执行全局模型更新
        
        流程：
        1. 序列化所有密文
        2. ECALL 委托 TEE 处理
        3. 接收 TEE 输出（ct_global, ct_prefetch_map）
        4. 更新服务器状态
        
        Args:
            encrypted_updates: 客户端加密更新列表
            weights: 聚合权重
        
        Returns:
            更新是否成功
        """
        if not self.tee_enabled or self.tee_proxy is None:
            # 回退到标准模式
            return super().update_global_model(encrypted_updates, weights)
        
        try:
            # 1. 序列化密文
            ct_bytes_list = []
            for update in encrypted_updates:
                if isinstance(update, dict) and update.get('__sparse__'):
                    # 稀疏更新：序列化所有批次
                    for ct in update['ciphertexts']:
                        ct_bytes_list.append(ct.serialize())
                elif hasattr(update, 'serialize'):
                    ct_bytes_list.append(update.serialize())
                else:
                    logger.warning(f"无法序列化更新: {type(update)}")
                    continue
            
            # 2. ECALL 委托 TEE 处理
            logger.info(f"ECALL: 委托 TEE 处理 {len(ct_bytes_list)} 个密文")
            result = self.tee_proxy.process_round(
                ct_bytes_list, weights
            )
            
            # 3. 解析结果
            if isinstance(result, tuple) and len(result) == 2:
                ct_global_bytes, prefetch_map = result
            else:
                logger.error(f"TEE 返回格式错误: {type(result)}")
                return False
            
            # 4. 更新全局密文状态
            import tenseal as ts
            self.encrypted_global_state = ts.CKKSVector.deserialize(ct_global_bytes)
            
            # 5. 存储预取密文（按客户端索引）
            self.prefetch_store = {}
            for client_id, ct_prefetch_bytes in prefetch_map.items():
                self.prefetch_store[client_id] = ts.CKKSVector.deserialize(
                    ct_prefetch_bytes
                )
            
            # 6. 同步明文模型（OCALL：用于评估）
            self._sync_model_from_tee()
            
            # 7. 递增轮次
            self.round_num += 1
            
            logger.info(f"TEE 处理完成: 轮次={self.round_num}")
            return True
            
        except Exception as e:
            logger.error(f"TEE 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_prefetch_for_client(self, client_id: str) -> Optional[Dict]:
        """
        获取指定客户端的预取密文（密文状态）
        
        Args:
            client_id: 客户端标识
        
        Returns:
            {'ciphertext': bytes, 'signature': bytes} 或 None
        """
        if not self.tee_enabled:
            return super().get_prefetch_for_client(client_id)
        
        ct_prefetch = self.prefetch_store.get(client_id)
        if ct_prefetch is None:
            logger.warning(f"客户端 {client_id} 无预取密文")
            return None
        
        # 获取 TEE 签名（用于客户端验证）
        try:
            signature = self.tee_proxy.get_prefetch_signature(client_id)
        except AttributeError:
            # SIMULATION 模式下可能无签名
            signature = b''
        
        return {
            'ciphertext': ct_prefetch.serialize(),
            'signature': signature
        }
    
    def _sync_model_from_tee(self):
        """
        OCALL：从 TEE 同步明文模型用于评估
        
        在 SIMULATION 模式下：直接从 EnclaveMemory 读取
        在 NATIVE 模式下：通过 OCALL 接口获取
        """
        if self.tee_mode == 'simulation':
            # 直接读取 EnclaveMemory 中的模型
            if (self.tee_proxy.enclave and 
                self.tee_proxy.enclave._enclave_state.model_state is not None):
                self.model = self.tee_proxy.enclave._enclave_state.model_state
        
        # NATIVE 模式 TODO：通过 OCALL 获取
    
    def evaluate(self, test_loader) -> Dict[str, float]:
        """
        模型评估（使用从 TEE 同步的明文模型）
        
        Args:
            test_loader: 测试数据加载器
        
        Returns:
            评估指标字典
        """
        if self.model is None:
            logger.warning("模型未同步，无法评估")
            return {}
        
        # 标准评估逻辑
        self.model.eval()
        # ... 评估代码 ...
        return {'accuracy': 0.0}  # 占位
    
    def get_tee_audit_log(self) -> List[Dict]:
        """获取 TEE 审计日志"""
        if self.tee_proxy and self.tee_proxy.initialized:
            return self.tee_proxy.get_enclave_log()
        return []
