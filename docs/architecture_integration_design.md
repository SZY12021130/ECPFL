# CKKS-FL 架构方案与 PAMP 框架集成设计

> 将三个外层密码学架构方案映射到现有代码模块的具体集成路径

---

## 现有 PAMP 框架模块结构

```
crypto.py
├── CKKSManager
│   ├── encrypt_model_update()     # 客户端加密
│   ├── decrypt_model_update()     # 服务器/客户端解密
│   └── sparsification_strategy    # TopK/Random 稀疏化
│
client.py
├── PrefetchFederatedClient
│   ├── local_train()              # 本地训练
│   ├── apply_prefetched_state()   # 应用预取密文
│   └── ckks_manager               # 引用 CKKSManager
│
server.py
├── PrefetchAggregationServer
│   ├── update_global_model()      # 聚合 + 更新
│   ├── _update_plain_global_model()   # 明文模型更新路径
│   ├── _update_encrypted_global_state()  # 密文状态更新路径
│   └── ckks_manager               # 引用 CKKSManager
│
ptopk.py
├── PTopkModule
│   ├── server_update_plain()      # 服务器累加器
│   └── wrap_strategy()            # 包装稀疏化策略
```

**当前密钥管理**：单密钥，sk 存储在 Server 的 CKKSManager 中，pk/evk 所有实体共享。

---

## 方案一：3S-EAD 集成设计

### 架构变化概述
引入 **EdgeNode** 实体，sk 拆分为 sk_server + sk_edge + sk_client，需要两方协同解密。

### 新增模块

```python
# edge_node.py
class EdgeNode:
    """边缘辅助节点，持有 sk_edge，提供部分解密服务"""
    
    def __init__(self, config: Dict):
        self.sk_edge = load_sk_edge(config['edge']['sk_path'])
        self.port = config['edge']['port']
        self.server = None  # 网络服务
    
    def partial_decrypt(self, ciphertext: ts.CKKSVector) -> bytes:
        """
        执行部分解密：
        partial = c0 + c1 * sk_edge
        
        注意：TenSEAL 不原生支持部分解密，需要手动实现。
        对于 CKKSVector，内部结构为 (b, a)，其中 b = a*s + m + e。
        部分解密需要访问内部多项式系数。
        """
        # 提取密文内部多项式
        raw_data = ciphertext.serialize()
        # 反序列化得到 (c0, c1)
        c0, c1 = deserialize_ciphertext(raw_data)
        
        # 计算 partial = c0 + c1 * sk_edge
        partial = c0 + c1 * self.sk_edge
        
        return serialize_polynomial(partial)
```

```python
# threshold_crypto.py
class ThresholdCKKSManager(CKKSManager):
    """扩展 CKKSManager 支持阈值解密"""
    
    def __init__(self, config: Dict, share: Polynomial = None):
        super().__init__(config)
        self.share = share  # sk_server 或 sk_client
        self.edge_endpoint = config.get('edge', {}).get('endpoint')
    
    def partial_decrypt(self, ciphertext: ts.CKKSVector) -> bytes:
        """计算部分解密份额"""
        c0, c1 = extract_coefficients(ciphertext)
        partial = c0 + c1 * self.share
        return serialize_polynomial(partial)
    
    def combine_decrypt(self, 
                       ciphertext: ts.CKKSVector,
                       partial_local: bytes,
                       partial_remote: bytes) -> np.ndarray:
        """
        组合两个部分解密份额得到明文。
        
        对于两方加法共享（sk = sk_A + sk_B）：
        partial_A = c0 + c1 * sk_A
        partial_B = c1 * sk_B          (注意：partial_B 不包含 c0)
        m = partial_A + partial_B = c0 + c1 * (sk_A + sk_B) = c0 + c1 * sk
        """
        p_local = deserialize_polynomial(partial_local)
        p_remote = deserialize_polynomial(partial_remote)
        
        # 组合
        m_approx = p_local + p_remote
        
        # CKKS Decode
        return self.decode_polynomial(m_approx)
```

### 密钥分发实现

```python
# key_generation.py
class SplitSecretKGC:
    """KGC：生成拆分密钥并分发"""
    
    def generate_and_distribute(self, n_clients: int, output_dir: str):
        # 1. 生成标准 CKKS 密钥
        context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192)
        context.generate_galois_keys()
        context.generate_relin_keys()
        
        # 2. 提取私钥（TenSEAL 不直接暴露 sk，需要底层操作）
        sk = extract_secret_key(context)
        pk = extract_public_key(context)
        evk = extract_eval_keys(context)
        
        # 3. 拆分 sk
        sk_server = sample_random_polynomial(sk.modulus, sk.degree)
        sk_edge = sample_random_polynomial(sk.modulus, sk.degree)
        sk_client = sk - sk_server - sk_edge  # 系数模 q
        
        # 4. 分发
        save_polynomial(sk_server, f"{output_dir}/server/sk_server.bin")
        save_polynomial(sk_edge, f"{output_dir}/edge/sk_edge.bin")
        
        for i in range(n_clients):
            save_polynomial(sk_client, f"{output_dir}/client_{i}/sk_client.bin")
        
        save_public_key(pk, f"{output_dir}/public/pk.bin")
        save_eval_keys(evk, f"{output_dir}/public/evk.bin")
```

### 集成到 server.py

```python
class EADAggregationServer(PrefetchAggregationServer):
    """3S-EAD 架构下的聚合服务器"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 加载 sk_server
        self.sk_server = load_sk_server(config['server']['sk_path'])
        self.edge_endpoint = config['edge']['endpoint']
        self.threshold_crypto = ThresholdCKKSManager(config, self.sk_server)
    
    def _decrypt_with_edge(self, ciphertext: ts.CKKSVector) -> np.ndarray:
        """与 Edge 协同解密"""
        # 1. 计算本地部分解密
        partial_server = self.threshold_crypto.partial_decrypt(ciphertext)
        
        # 2. 发送密文给 Edge
        ct_bytes = ciphertext.serialize()
        response = requests.post(
            f"{self.edge_endpoint}/partial_decrypt",
            data=ct_bytes
        )
        partial_edge = response.content
        
        # 3. 组合
        plaintext = self.threshold_crypto.combine_decrypt(
            ciphertext, partial_server, partial_edge
        )
        return plaintext
    
    def _update_encrypted_global_state(self, aggregated_update, learning_rate):
        """覆盖原方法：使用协同解密替代直接解密"""
        if isinstance(aggregated_update, dict) and aggregated_update.get('__sparse__'):
            # 稀疏路径：需要解密
            ciphertexts = aggregated_update['ciphertexts']
            masks = aggregated_update['mask']
            
            # 协同解密每个 batch
            plaintext_batches = []
            for ct in ciphertexts:
                plain = self._decrypt_with_edge(ct)
                plaintext_batches.append(plain)
            
            # 重组完整更新
            dense_update = reconstruct_from_batches(plaintext_batches, masks)
            
            # PTopk 服务器累加器
            if self.ckks_manager.ptopk.enabled:
                dense_update = self.ckks_manager.ptopk.server_update_plain(
                    dense_update, learning_rate
                )
            
            # 更新明文模型
            self._apply_dense_update(dense_update, learning_rate)
            
            # 重新加密 packed 全局状态
            self.encrypted_global_state = self._reencrypt_global_state()
    
    def _send_prefetch(self, client_id: str, delta_plain: np.ndarray):
        """预取：与 Client 协同加密/传输"""
        # 方案一选项 A：Server 直接用 pk 加密，Client 无法解密
        # 方案一选项 B：Server 与 Client 协同解密后发送明文（不安全）
        # 方案一选项 C：Server 计算密文，Client 与 Server 协同解密
        
        # 选项 C 实现：
        # 1. Server 用 pk 加密 delta
        ct_prefetch = self.ckks_manager.encrypt(delta_plain)
        
        # 2. Server 计算部分解密
        partial_server = self.threshold_crypto.partial_decrypt(ct_prefetch)
        
        # 3. 发送密文 + partial_server 给 Client
        return {
            'ciphertext': ct_prefetch.serialize(),
            'partial': partial_server
        }
```

### 集成到 client.py

```python
class EADFederatedClient(PrefetchFederatedClient):
    """3S-EAD 架构下的客户端"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 加载 sk_client
        self.sk_client = load_sk_client(config['client']['sk_path'])
        self.threshold_crypto = ThresholdCKKSManager(config, self.sk_client)
    
    def apply_prefetched_state(self, prefetched_data: Dict):
        """应用预取状态：协同解密"""
        ct = ts.CKKSVector.deserialize(prefetched_data['ciphertext'])
        partial_server = prefetched_data['partial']
        
        # Client 计算部分解密
        partial_client = self.threshold_crypto.partial_decrypt(ct)
        
        # 组合得到明文
        delta = self.threshold_crypto.combine_decrypt(
            ct, partial_client, partial_server
        )
        
        # 应用到本地模型
        self.apply_delta(delta)
        
        # 清除缓存
        self.prefetched_state = None
```

### 3S-EAD 集成风险与缓解

| 风险点 | 缓解措施 |
|--------|----------|
| TenSEAL 不暴露 sk | 需要修改 TenSEAL 底层或使用其内部 API |
| 部分解密通信开销 | 批量处理：一次往返解密多个 batch |
| Edge 节点单点故障 | 部署多个 Edge 节点，sk_edge 分发给主备 |
| Client 与 Server 共谋 | 引入 Edge 作为第三方，两方共谋无法绕过 |

---

## 方案二：TESK-EGD 集成设计

### 架构变化概述
在 Server 上部署 TEE Enclave，所有涉及 sk 的操作在 enclave 内执行。Server Host 只传递密文。

### TEE Enclave 内部模块

```c
// enclave/aggregator_trusted.c (SGX Enclave)
#include <sgx_tcrypto.h>

// 密封的密钥存储在 enclave 内
static uint8_t sealed_sk[SEALED_SK_SIZE];
static size_t sealed_sk_len = 0;

// ECALL: 初始化（加载密封密钥）
sgx_status_t ecall_init_aggregator(uint8_t* sealed_key, size_t key_len) {
    memcpy(sealed_sk, sealed_key, key_len);
    sealed_sk_len = key_len;
    return SGX_SUCCESS;
}

// ECALL: 处理一轮聚合
sgx_status_t ecall_process_round(
    uint8_t** ct_list,      // 输入密文列表
    size_t* ct_lengths,
    int n_clients,
    double* weights,
    uint8_t** ct_global_out,    // 输出全局密文
    size_t* ct_global_len,
    uint8_t** enc_prefetch_out, // 输出加密预取
    size_t* enc_prefetch_len
) {
    // 1. 解封 sk
    sgx_sealed_data_t* sealed = (sgx_sealed_data_t*)sealed_sk;
    uint8_t sk[SK_SIZE];
    uint32_t sk_len = SK_SIZE;
    sgx_unseal_data(sealed, NULL, NULL, sk, &sk_len);
    
    // 2. 同态聚合（调用 TenSEAL 同态库，或自行实现 RLWE 加法）
    // 注意：SGX enclave 内可链接 TenSEAL C++ 库
    
    // 3. 解密稀疏聚合结果
    // 调用 CKKS 解密
    
    // 4. PTopk 服务器累加器（明文操作）
    // 注意：enclave 内内存有限，需要优化
    
    // 5. 更新明文模型
    
    // 6. 重新加密 packed 全局状态
    
    // 7. 计算预取并用会话密钥加密
    
    return SGX_SUCCESS;
}
```

### Python 端 TEE 代理模块

```python
# tee_proxy.py
import ctypes
from ctypes import cdll

class TEEFederatedProxy:
    """TEE 代理：Python 端通过 ECALL/OCALL 与 Enclave 通信"""
    
    def __init__(self, enclave_path: str, sealed_sk_path: str):
        # 加载 SGX untrusted runtime
        self.lib = cdll.LoadLibrary('libsgx_urts.so')
        
        # 创建 enclave
        self.enclave_id = self._create_enclave(enclave_path)
        
        # 加载密封密钥
        with open(sealed_sk_path, 'rb') as f:
            sealed_sk = f.read()
        
        # ECALL 初始化
        self._ecall_init(self.enclave_id, sealed_sk)
    
    def process_round(self, ct_list: List[bytes], weights: List[float]) -> Tuple[bytes, bytes]:
        """
        委托 enclave 处理一轮聚合。
        
        返回：(ct_global_bytes, enc_prefetch_bytes)
        """
        # 准备 ECALL 参数
        n = len(ct_list)
        ct_ptrs = (ctypes.c_char_p * n)(*ct_list)
        ct_lens = (ctypes.c_size_t * n)(*[len(c) for c in ct_list])
        weights_arr = (ctypes.c_double * n)(*weights)
        
        # 输出缓冲区
        global_out = ctypes.c_char_p()
        global_len = ctypes.c_size_t()
        prefetch_out = ctypes.c_char_p()
        prefetch_len = ctypes.c_size_t()
        
        # ECALL
        ret = self.lib.ecall_process_round(
            self.enclave_id,
            ct_ptrs, ct_lens, n, weights_arr,
            ctypes.byref(global_out), ctypes.byref(global_len),
            ctypes.byref(prefetch_out), ctypes.byref(prefetch_len)
        )
        
        if ret != 0:
            raise RuntimeError(f"Enclave processing failed: {ret}")
        
        return (
            ctypes.string_at(global_out, global_len.value),
            ctypes.string_at(prefetch_out, prefetch_len.value)
        )
    
    def verify_enclave(self, expected_mrenclave: bytes) -> bool:
        """远程证明：验证 enclave 代码完整性"""
        quote = self._get_quote()
        return quote.mrenclave == expected_mrenclave
```

### 集成到 server.py

```python
class TEEAggregationServer(PrefetchAggregationServer):
    """TEE 架构下的聚合服务器"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # 初始化 TEE 代理
        self.tee = TEEFederatedProxy(
            enclave_path=config['tee']['enclave_so'],
            sealed_sk_path=config['tee']['sealed_sk_path']
        )
        
        # 远程证明验证
        expected_mrenclave = bytes.fromhex(config['tee']['expected_mrenclave'])
        if not self.tee.verify_enclave(expected_mrenclave):
            raise SecurityError("Enclave remote attestation failed!")
    
    def update_global_model(self, encrypted_updates: List[Dict], weights: List[float]):
        """覆盖：委托 TEE 处理整轮聚合"""
        # 1. 序列化所有密文
        ct_bytes_list = []
        for update in encrypted_updates:
            if isinstance(update, dict) and update.get('__sparse__'):
                # 序列化稀疏密文
                ct_list = update['ciphertexts']
                for ct in ct_list:
                    ct_bytes_list.append(ct.serialize())
            else:
                ct_bytes_list.append(update.serialize())
        
        # 2. TEE 处理
        ct_global_bytes, enc_prefetch_bytes = self.tee.process_round(
            ct_bytes_list, weights
        )
        
        # 3. 更新服务器状态
        self.encrypted_global_state = ts.CKKSVector.deserialize(ct_global_bytes)
        
        # 4. 存储预取数据
        self.prefetch_cache = enc_prefetch_bytes
    
    def get_prefetch_for_client(self, client_id: str) -> bytes:
        """获取预取数据（对称加密）"""
        return self.prefetch_cache
```

### 集成到 client.py

```python
class TEEFederatedClient(PrefetchFederatedClient):
    """TEE 架构下的客户端"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        # 加载会话密钥
        self.session_key = load_session_key(config['client']['session_key_path'])
    
    def apply_prefetched_state(self, enc_prefetch: bytes):
        """应用预取状态：对称解密"""
        # AES-GCM 解密
        delta = aes_gcm_decrypt(enc_prefetch, self.session_key)
        
        # 应用到本地模型
        self.apply_delta(delta)
        
        # 清除缓存
        self.prefetched_state = None
```

### TEE 集成风险与缓解

| 风险点 | 缓解措施 |
|--------|----------|
| TEE 内存限制（128MB）| 模型分页加载，或使用 SGX2/SEV-SNP（支持更大内存） |
| TEE 侧信道攻击 | 实现常数时间算法，禁用超线程，使用 TEE 专用 SDK 防护 |
| TEE 漏洞（如 Foreshadow）| 及时更新微码，使用最新 TEE 版本，启用 SGX FLC |
| 远程证明伪造 | 使用 Intel Attestation Service (IAS) 或 DCAP 验证 |

---

## 方案三：SSCKKS-tn 集成设计

### 架构变化概述
每个客户端持有 sk 的一份，AggServer 无 sk。解密需要 t 个客户端提供部分解密份额。

### 新增模块

```python
# threshold_sharing.py
class ShamirSecretSharing:
    """Shamir 秘密共享实现"""
    
    def __init__(self, prime: int):
        self.prime = prime  # 大素数，用于有限域运算
    
    def split(self, secret: int, n: int, t: int) -> List[Tuple[int, int]]:
        """
        将 secret 分成 n 份，任意 t 份可恢复。
        
        返回 [(1, share_1), (2, share_2), ..., (n, share_n)]
        """
        # 随机生成 t-1 次多项式系数
        coeffs = [secret] + [random.randint(0, self.prime - 1) for _ in range(t - 1)]
        
        shares = []
        for i in range(1, n + 1):
            # 计算 f(i)
            share = sum(c * pow(i, idx, self.prime) for idx, c in enumerate(coeffs)) % self.prime
            shares.append((i, share))
        
        return shares
    
    def reconstruct(self, shares: List[Tuple[int, int]]) -> int:
        """Lagrange 插值恢复 secret"""
        secret = 0
        for i, (x_i, y_i) in enumerate(shares):
            numerator = 1
            denominator = 1
            for j, (x_j, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime
            
            lagrange_coeff = numerator * pow(denominator, -1, self.prime) % self.prime
            secret = (secret + y_i * lagrange_coeff) % self.prime
        
        return secret
```

```python
# threshold_ckks.py
class ThresholdCKKSManager:
    """阈值 CKKS 管理器"""
    
    def __init__(self, config: Dict, share_id: int = None, share: int = None):
        self.config = config
        self.pk = load_pk(config['public']['pk_path'])
        self.evk = load_evk(config['public']['evk_path'])
        
        # 如果是客户端，加载份额
        if share_id is not None and share is not None:
            self.share_id = share_id
            self.share = share
    
    def encrypt(self, plaintext: np.ndarray) -> ts.CKKSVector:
        """标准加密（使用 pk）"""
        return ts.ckks_vector(self.pk, plaintext)
    
    def partial_decrypt(self, ciphertext: ts.CKKSVector) -> Tuple[int, np.ndarray]:
        """
        计算部分解密份额。
        
        对于 CKKS，部分解密份额为：
        d_i = c1 * share_i * λ_i
        
        其中 λ_i 是 Lagrange 系数。
        """
        # 提取 c1（密文的第二个多项式）
        c1 = extract_c1(ciphertext)
        
        # 计算 d_i = c1 * share_i
        # 注意：这是多项式标量乘
        d_i = c1 * self.share
        
        return (self.share_id, d_i)
    
    def combine(self, 
               ciphertext: ts.CKKSVector,
               shares: List[Tuple[int, np.ndarray]],
               t: int) -> np.ndarray:
        """
        组合至少 t 个部分解密份额得到明文。
        
        m = c0 + Σ d_i * λ_i
        """
        if len(shares) < t:
            raise ValueError(f"Need at least {t} shares, got {len(shares)}")
        
        c0 = extract_c0(ciphertext)
        
        # 计算 Lagrange 系数
        x_vals = [sid for sid, _ in shares]
        
        # 组合
        result = c0
        for sid, d_i in shares:
            λ_i = self._lagrange_coeff(sid, x_vals)
            result = result + d_i * λ_i
        
        # CKKS Decode
        return ckks_decode(result)
    
    def _lagrange_coeff(self, x_i: int, x_vals: List[int]) -> float:
        """计算 Lagrange 系数 λ_i"""
        numerator = 1.0
        denominator = 1.0
        for x_j in x_vals:
            if x_j != x_i:
                numerator *= -x_j
                denominator *= (x_i - x_j)
        return numerator / denominator
```

### 集成到 server.py

```python
class ThresholdAggregationServer:
    """阈值架构下的聚合服务器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.pk = load_pk(config['public']['pk_path'])
        self.evk = load_evk(config['public']['evk_path'])
        self.t = config['threshold']['t']
        self.n = config['threshold']['n']
        
        # Server 不持有任何 sk 份额
        self.ckks_manager = ThresholdCKKSManager(config)
    
    def aggregate(self, encrypted_updates: List) -> ts.CKKSVector:
        """同态聚合（标准操作）"""
        ct_agg = None
        for update in encrypted_updates:
            if ct_agg is None:
                ct_agg = update
            else:
                ct_agg = ct_agg + update
        return ct_agg
    
    def threshold_decrypt(self, 
                         ciphertext: ts.CKKSVector,
                         client_pool: List['ThresholdFederatedClient']) -> np.ndarray:
        """
        阈值解密：收集 t 个客户端的部分解密份额。
        
        流程：
        1. Server 广播密文给所有客户端
        2. 每个客户端计算并返回部分解密份额
        3. Server 收集至少 t 个份额
        4. Server 组合得到明文
        """
        # 1. 广播
        ct_bytes = ciphertext.serialize()
        
        # 2. 收集份额
        shares = []
        for client in client_pool:
            try:
                share = client.provide_decrypt_share(ct_bytes)
                shares.append(share)
                if len(shares) >= self.t:
                    break
            except Exception as e:
                logger.warning(f"Client {client.id} failed to provide share: {e}")
                continue
        
        if len(shares) < self.t:
            raise RuntimeError(f"Only {len(shares)} shares available, need {self.t}")
        
        # 3. 组合
        plaintext = self.ckks_manager.combine(ciphertext, shares, self.t)
        return plaintext
    
    def run_round(self, 
                 encrypted_updates: List,
                 weights: List[float],
                 client_pool: List):
        """执行完整一轮"""
        # 1. 聚合
        ct_agg = self.aggregate(encrypted_updates)
        
        # 2. 阈值解密（PTopk 路径）
        delta = self.threshold_decrypt(ct_agg, client_pool)
        
        # 3. PTopk 服务器累加器
        # ...
        
        # 4. 重新加密
        # ...
        
        # 5. 预取：由于 Server 无 sk，预取内容用会话密钥加密
        # ...
```

### 集成到 client.py

```python
class ThresholdFederatedClient:
    """阈值架构下的客户端"""
    
    def __init__(self, config: Dict, client_id: int):
        self.client_id = client_id
        self.config = config
        
        # 加载份额
        share_data = load_share(config['client']['share_path'])
        self.share_id = share_data['id']
        self.share = share_data['value']
        
        self.ckks_manager = ThresholdCKKSManager(
            config, 
            share_id=self.share_id,
            share=self.share
        )
    
    def encrypt_update(self, gradient: np.ndarray) -> ts.CKKSVector:
        """加密梯度上传"""
        return self.ckks_manager.encrypt(gradient)
    
    def provide_decrypt_share(self, ct_bytes: bytes) -> Tuple[int, bytes]:
        """
        响应 Server 的解密请求，提供部分解密份额。
        
        注意：Client 不返回明文，只返回部分解密份额 d_i。
        单个 d_i 不泄露任何明文信息。
        """
        ct = ts.CKKSVector.deserialize(ct_bytes)
        sid, d_i = self.ckks_manager.partial_decrypt(ct)
        
        # 序列化 d_i
        d_i_bytes = serialize_polynomial(d_i)
        return (sid, d_i_bytes)
```

### SSCKKS-tn 集成风险与缓解

| 风险点 | 缓解措施 |
|--------|----------|
| 每轮需 t 个客户端在线 | 设置 t = ⌈n/2⌉，容忍近半数掉线 |
| 通信开销大 | 批量收集份额，使用异步通信 |
| 恶意客户端提交错误份额 | 引入份额验证机制（基于零知识证明或一致性检查） |
| 预取流程复杂 | 预取内容走对称加密通道，不走阈值解密 |
| TenSEAL 不支持阈值 | 需要自行实现 PartialDecrypt 和 Combine，或修改 TenSEAL 源码 |

---

## 三方案集成复杂度对比

| 维度 | 3S-EAD | TESK-EGD | SSCKKS-tn |
|------|--------|----------|-----------|
| **新增代码文件** | edge_node.py, threshold_crypto.py | tee_proxy.py, enclave C++ 代码 | threshold_sharing.py, threshold_ckks.py |
| **修改现有文件** | server.py, client.py | server.py, client.py | server.py, client.py |
| **TenSEAL 修改** | 需要暴露 sk 或内部系数 | 无（TEE 内使用标准 TenSEAL）| 需要实现 PartialDecrypt |
| **通信协议变化** | Server↔Edge 新增 HTTPS | Server↔TEE 为本地 ECALL | Server↔Client 新增份额交换 |
| **部署依赖** | Edge 节点（云端/边缘） | SGX/SEV 硬件 + TEE SDK | 无特殊硬件 |
| ** estimated 工期** | 1-2 周 | 3-4 周 | 2-3 周 |
