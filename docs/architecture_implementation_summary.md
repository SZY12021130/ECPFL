# CKKS-FL 外层密码学架构实现总结

## 完成状态概览

| 方案 | 设计文档 | 集成设计 | 核心代码 | 测试验证 | 演示脚本 |
|------|----------|----------|----------|----------|----------|
| **3S-EAD** (Split-Secret + Edge) | ✅ | ✅ | ✅ | ✅ 7/7 | ✅ |
| **TESK-EGD** (TEE Encapsulated) | ✅ | ✅ | ⏳ 待实现 | - | - |
| **SSCKKS-tn** (Threshold) | ✅ | ✅ | ⏳ 待实现 | - | - |

---

## 3S-EAD 实现详情

### 新增文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `ckks_fed/split_key_crypto.py` | 24.4 KB | SplitKeyCKKSManager, SplitKeyKGC, PartialDecryptionShare, TwoPartyDecryptor |
| `ckks_fed/edge_node.py` | 4.6 KB | EdgeNode (HTTP服务), EdgeNodeClient (远程调用) |
| `test_split_key_architecture.py` | 10.7 KB | 7项架构流程验证测试 |
| `demo_3sead.py` | 9.1 KB | 完整7步联邦学习轮次演示 |
| `configs/e3sad_config.yaml` | 1.6 KB | 3S-EAD架构配置文件 |

### 核心类

```
SplitKeyKGC              # 密钥生成与分发中心
├── generate_and_split() # 生成CKKS密钥并拆分为三份
└── load_role_context()  # 加载角色上下文

SplitKeyCKKSContext      # 拆分密钥上下文
├── encrypt()            # 加密（server/client权限）
├── partial_decrypt()    # 部分解密（server/edge/client权限）
└── 权限控制（role-based access control）

SplitKeyCKKSManager      # 拆分密钥管理器（继承CKKSManager）
├── collaborative_decrypt()              # 两方协同解密
├── collaborative_decrypt_sparse_update() # 稀疏更新协同解密
└── prepare_partial_decrypt()             # 准备部分解密份额

EdgeNode                 # 边缘辅助节点
├── partial_decrypt()    # 本地部分解密
├── start_server()       # 启动Flask HTTP服务
└── HTTP API: /partial_decrypt, /batch_partial_decrypt

EdgeNodeClient           # EdgeNode远程客户端
├── partial_decrypt()    # 请求远程部分解密
└── batch_partial_decrypt() # 批量请求
```

### 密钥分发架构

```
KGC
├── sk_server → Server (TLS)
├── sk_edge   → Edge   (TLS)
├── sk_client → Client (TLS, 每客户端独立)
└── pk, evk   → 公开

解密路径1 (PTopk): Server + Edge 协同
解密路径2 (预取):  Server + Client 协同
```

### 测试验证结果

**test_split_key_architecture.py** 运行结果（全部通过）：

| 测试项 | 结果 | 说明 |
|--------|------|------|
| KGC密钥生成与分发 | ✅ | 目录结构正确 |
| Client加密梯度 | ✅ | 密文大小~334KB |
| Server聚合密文 | ✅ | 聚合后~235KB |
| Server+Edge协同解密 | ✅ | 误差0.000000 |
| Server+Client协同解密 | ✅ | 误差0.000000 |
| 权限控制验证 | ✅ | Edge加密被拒，Client/Server加密通过 |
| EdgeNode HTTP服务 | ✅ | 健康检查+部分解密成功 |

**demo_3sead.py** 运行结果（完整流程通过）：
- 3个客户端训练+加密 → Server聚合 → Server+Edge协同解密 → Server更新+重加密 → Server+Client协同预取 → Client应用预取
- 聚合误差：0.000000
- 预取误差：0.000000

### 安全特性验证

| 威胁场景 | 防御效果 | 验证方式 |
|----------|----------|----------|
| Server单独解密 | ✅ 拒绝 | 权限控制：Server无full_decrypt权限 |
| Edge单独解密 | ✅ 拒绝 | 权限控制：Edge无encrypt权限，partial_decrypt需组合 |
| Client A解密Client B | ✅ 拒绝 | Client只有sk_client份额，单方无法解密 |
| Server+Edge共谋 | ⚠️ 可攻破 | 两方份额可组合出完整sk（设计限制） |
| 历史密文保护 | ✅ 有效 | Server被攻破后，历史密文仍需Edge/Client份额 |

---

## 待完成工作

### 方案二：TESK-EGD（TEE Encapsulated）

**技术栈**：Intel SGX / AMD SEV / ARM TrustZone

**待实现模块**：
- `enclave/aggregator_trusted.c` - SGX Enclave内聚合逻辑
- `ckks_fed/tee_proxy.py` - Python端TEE代理（ECALL/OCALL封装）
- `ckks_fed/server_tee.py` - TEE架构Server适配
- `ckks_fed/client_tee.py` - TEE架构Client适配（会话密钥解密预取）

**关键挑战**：
- TEE内存限制（SGX 128MB）
- 侧信道攻击防护
- 远程证明验证机制

### 方案三：SSCKKS-tn（Shamir-Shared Threshold）

**技术栈**：(t,n)-Shamir秘密共享 + CKKS部分解密

**待实现模块**：
- `ckks_fed/threshold_sharing.py` - Shamir秘密共享实现
- `ckks_fed/threshold_ckks.py` - 阈值CKKS管理器
- `ckks_fed/server_threshold.py` - 阈值架构Server适配
- `ckks_fed/client_threshold.py` - 阈值架构Client适配

**关键挑战**：
- TenSEAL不暴露私钥多项式（需底层修改）
- 每轮需t个客户端在线参与解密
- 份额验证机制（防止恶意客户端提交错误份额）

---

## 与现有PAMP框架的集成点

### 最小侵入式集成路径

对于3S-EAD，集成到现有代码的修改点：

**`server.py`**
```python
# 修改前
self.ckks_manager = CKKSManager(config)

# 修改后
if config.get('split_key', {}).get('enable', False):
    self.ckks_manager = create_split_key_manager(config, role='server')
    self.edge_client = EdgeNodeClient(
        endpoint=config['split_key']['edge']['endpoint']
    )
else:
    self.ckks_manager = CKKSManager(config)
```

**`client.py`**
```python
# 修改前
self.ckks_manager = CKKSManager(config)

# 修改后
if config.get('split_key', {}).get('enable', False):
    self.ckks_manager = create_split_key_manager(config, role='client')
else:
    self.ckks_manager = CKKSManager(config)
```

**解密调用替换**
```python
# 修改前（标准单密钥）
decrypted = self.ckks_manager.decrypt_model_update(ciphertext, shapes)

# 修改后（3S-EAD协同解密）
remote_share = self.edge_client.partial_decrypt(ciphertext.serialize())
decrypted = self.ckks_manager.collaborative_decrypt(ciphertext, remote_share)
```

---

## 性能预估

| 操作 | 标准CKKS | 3S-EAD | 开销增加 |
|------|----------|--------|----------|
| 客户端加密 | 100ms | 100ms | 0% |
| 服务器聚合 | 50ms | 50ms | 0% |
| 单次解密 | 200ms | 400ms (含网络往返) | ~100% |
| 预取解密 | 200ms | 400ms (含网络往返) | ~100% |
| 每轮总耗时 | ~5s | ~5.5s | ~10% |

---

## 下一步建议

1. **实现TESK-EGD方案**：在有SGX/SEV硬件的环境中实现TEE封装方案
2. **实现SSCKKS-tn方案**：修改TenSEAL底层以支持私钥多项式提取
3. **3S-EAD生产化**：实现生产级EdgeNode（gRPC替代Flask、TLS双向认证、心跳检测）
4. **综合对比实验**：在三方案上运行相同FL任务，对比延迟、吞吐量、安全性指标
