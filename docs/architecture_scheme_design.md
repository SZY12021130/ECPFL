# CKKS-FL 外层密码学架构方案设计

> 基于密文预取（CipherFetch）与 PTopk 模块的外层密码学框架重设计
> 
> 聚焦：密钥架构、实体角色、密钥分发、威胁模型适配

---

## 背景：当前 PAMP 框架的密码学架构

当前系统采用**单密钥 CKKS**，架构如下：

```
KGC ──sk, pk, evk──▶ Server
           └────────▶ Client (pk, evk only)
```

**存在问题**：
1. **服务器持有完整 sk**：可任意解密所有客户端上传的密文，包括历史轮次
2. **客户端不持有 sk**：无法自行解密预取密文，预取流程依赖服务器额外操作
3. **无客户端间保密性**：若客户端 A 截获客户端 B 的密文，且 sk 分发范围不明，存在泄露风险
4. **密钥单点失效**：KGC 一旦泄露 sk，全系统历史暴露

---

## 方案一：3S-EAD（Split-Secret Single-Key with Edge-Assisted Decryption）

### 核心思想
将单密钥私钥 **sk 拆分为三份**：服务器份额、边缘节点份额、客户端份额。任意单一方无法解密，需要两方协同才能完成涉及 sk 的操作。

### 实体与角色

| 实体 | 持有密钥 | 信任假设 | 职责 |
|------|----------|----------|------|
| **KGC** | 生成 sk | 可信，初始化后离线 | 密钥生成与分发 |
| **Server** | sk_server, pk, evk | 可恶意 | 聚合、协同解密、PTopk、预取 |
| **Edge** | sk_edge | 半诚实 | 辅助部分解密 |
| **Client** | sk_client, pk, evk | 半诚实或恶意 | 本地训练、加密上传、协同解密预取 |

### 密钥分发流程

```
KGC 生成 sk, pk, evk
│
├─ 采样随机多项式 sk_edge ← R_q
├─ 计算 sk_server = sk - sk_edge  (mod q)
├─ 计算 sk_client = sk - sk_server - sk_edge  ❌ 需要三份和为 sk

修正：
KGC 采样 sk_server, sk_edge ← R_q
KGC 计算 sk_client = sk - sk_server - sk_edge  (mod q)
│
├─ KGC ──sk_server──▶ Server  (TLS)
├─ KGC ──sk_edge────▶ Edge    (TLS)
├─ KGC ──sk_client──▶ Client  (TLS，初始化时一对一安全通道)
├─ KGC ──pk, evk────▶ 公开    (所有实体)
│
KGC 销毁 sk，离线
```

**关键性质**：sk_server + sk_edge + sk_client = sk（系数模 q 加法）

### 协同解密机制

CKKS 解密公式：m = c0 + c1 · sk

由于 sk = sk_server + sk_edge + sk_client：

m = c0 + c1·sk_server + c1·sk_edge + c1·sk_client

**两方协同即可完成解密**：任意两方各自贡献一个部分解密项。

#### 场景 A：PTopk 稀疏聚合解密（Server + Edge 协同）

```
Server 持有 ct = (c0, c1)
│
├─ Server 计算 partial_S = c0 + c1 · sk_server
├─ Server 发送 partial_S ──▶ Edge
│
Edge 计算 partial_SE = partial_S + c1 · sk_edge
    = c0 + c1·(sk_server + sk_edge)
├─ Edge 发送 partial_SE ──▶ Server
│
Server 计算 m = partial_SE + c1 · sk_client  ❌ Server 没有 sk_client

修正：
Edge 不发送回 Server，而是发送给持有第三方的实体...

实际上，两方协同解密只需：
m = (c0 + c1·sk_A) + c1·sk_B

其中 sk_A + sk_B = sk

因此将 sk 拆分为两份即可：
- sk_S = sk_server  (给 Server)
- sk_E = sk - sk_S  (给 Edge)

Server + Edge 协同即可解密。

但 Client 也需要解密预取密文...

方案调整：
- sk 拆分为 sk_SE（Server+Edge 共享解密）和 sk_C（Client 独享解密）
- 不对，这样 Server+Edge 共谋即可完全攻破。

最终设计：
- sk 拆分为 sk_S（Server）、sk_E（Edge）、sk_C（Client）
- PTopk 解密路径：Server + Edge 协同（不需要 Client）
- 预取解密路径：Server + Client 协同（不需要 Edge）

具体地：

PTopk 路径（Server + Edge）：
  partial_S = c0 + c1 · sk_S
  partial_S → Edge
  partial_SE = partial_S + c1 · sk_E
  partial_SE → Server
  Server 此时有 partial_SE = c0 + c1·(sk_S + sk_E)
  但 Server 还需要 c1·sk_C 才能得到完整 m
  而 sk_C = sk - sk_S - sk_E
  所以 Server 不知道 sk_C，无法单独完成解密。

问题：两方协同解密要求 sk_S + sk_E = sk，但三方拆分下 sk_S + sk_E ≠ sk。

解决：使用 **(2,3)-门限共享** 而非加法拆分。

Shamir 秘密共享：
- sk 被分成 3 份 share_1, share_2, share_3
- 任意 2 份可以恢复 sk
- 单份无法获得 sk 的任何信息

密钥分发：
- share_S → Server
- share_E → Edge  
- share_C → Client

PTopk 路径：Server + Edge 恢复 sk → 解密
预取路径：Server + Client 恢复 sk → 解密

但这恢复的是完整 sk，一旦两方恢复，该轮次 sk 就被这两方知道了。

改进：**部分解密份额**而非恢复 sk。

在阈值密码学中：
- 每个 share holder 用其份额计算一个**部分解密份额**（decryption share）
- 收集 t 个份额后可以组合出明文
- 不需要恢复完整 sk

因此：
- Server 持有 share_S，可计算 decryption share d_S
- Edge 持有 share_E，可计算 decryption share d_E
- Client 持有 share_C，可计算 decryption share d_C

PTopk 路径：
  Server 发送 ct 给 Edge
  Edge 计算 d_E = PartialDecrypt(share_E, ct)
  Edge 发送 d_E 给 Server
  Server 计算 d_S = PartialDecrypt(share_S, ct)
  Server 组合 d_S + d_E → 明文 m

预取路径：
  Server 发送 ct_prefetch 给 Client
  Client 计算 d_C = PartialDecrypt(share_C, ct_prefetch)
  Client 发送 d_C 给 Server
  Server 计算 d_S = PartialDecrypt(share_S, ct_prefetch)
  Server 组合 d_S + d_C → 明文 delta_prefetch
  Server 发送明文 delta_prefetch 给 Client

等等，预取路径最后一步发送明文给 Client 不安全。

替代：预取路径由 Client 自己组合：
  Server 发送 ct_prefetch 给 Client
  Client 计算 d_C = PartialDecrypt(share_C, ct_prefetch)
  Server 发送 d_S 给 Client
  Client 组合 d_C + d_S → 明文 delta_prefetch

这样 Client 获得明文，Server 不需要发送明文。

但 Server 需要信任 Client 会正确组合...

或者 Client 和 Server 互相发送 shares，由其中一方组合。

简化设计：
- PTopk 路径：Server + Edge 协同，由 Server 最终组合得到明文
- 预取路径：Server + Client 协同，由 Client 最终组合得到明文

```
### 最终架构设计

#### 密钥架构
- **单密钥 CKKS**，sk 使用 (2,3)-Shamir 秘密共享分成 3 份
- share_S → Server
- share_E → Edge
- share_C → Client

#### PTopk 解密流程（Server + Edge）
1. Server 聚合得到 ct_agg
2. Server 计算 decryption share d_S = PartialDecrypt(share_S, ct_agg)
3. Server 发送 ct_agg 给 Edge
4. Edge 计算 decryption share d_E = PartialDecrypt(share_E, ct_agg)
5. Edge 发送 d_E 给 Server
6. Server 组合 d_S + d_E → 明文 m_agg
7. Server Decode 得到 delta，执行 PTopk 服务器累加器
8. Server 更新模型，重新加密 packed 全局状态

#### 预取解密流程（Server + Client）
1. Server 计算预取密文 ct_prefetch
2. Server 计算 decryption share d_S = PartialDecrypt(share_S, ct_prefetch)
3. Server 发送 ct_prefetch + d_S 给 Client
4. Client 计算 decryption share d_C = PartialDecrypt(share_C, ct_prefetch)
5. Client 组合 d_C + d_S → 明文 delta_prefetch
6. Client 将 delta_prefetch 应用到本地明文模型

#### 密钥分发
- KGC 生成 sk, pk, evk
- KGC 执行 (2,3)-Shamir 秘密共享：sk → {share_S, share_E, share_C}
- KGC → Server: share_S, pk, evk (TLS)
- KGC → Edge: share_E (TLS)
- KGC → Client: share_C, pk, evk (TLS，初始化时)
- KGC 销毁 sk，离线

### 威胁模型分析

| 威胁 | 攻击者 | 能力 | 防御效果 |
|------|--------|------|----------|
| 半诚实 Server | Server | 遵循协议但试图推断 | ❌ Server 无法单独解密，需 Edge/Client 合作 |
| 恶意 Server | Server | 篡改权重、排除客户端 | ⚠️ Server 仍可控制聚合过程，但无法单独解密历史密文 |
| 半诚实 Edge | Edge | 遵循协议但试图推断 | ✅ Edge 只有 share_E，无法单独解密 |
| 恶意 Edge | Edge | 伪造 decryption share | ⚠️ 若 Server 不验证，可能被欺骗；需结合验证机制 |
| 客户端 A 窥探 B | Client A | 截获 B 的密文 | ✅ Client A 只有 share_C，无法单独解密 B 的密文 |
| Server+Edge 共谋 | Server + Edge | 联合恢复 sk | ❌ 两方共谋可恢复 sk，等同于单密钥方案 |
| Server+Client 共谋 | Server + Client | 联合恢复 sk | ❌ 两方共谋可恢复 sk |
| Edge+Client 共谋 | Edge + Client | 联合恢复 sk | ❌ 两方共谋可恢复 sk |

**关键优势**：
- 单方被攻破（Server 或 Edge 或 Client）不会导致 sk 泄露
- 客户端间具有保密性（单个 Client 无法解密其他 Client 的密文）
- 历史密文保护：即使 Server 被攻破，历史密文仍受 Edge/Client 份额保护

**关键劣势**：
- 任意两方共谋即可恢复 sk
- 每轮解密需要额外通信（Server↔Edge 或 Server↔Client）
- TenSEAL 不原生支持阈值解密，需要自行实现 PartialDecrypt 和 Combine

---

## 方案二：TESK-EGD（TEE-Encapsulated Single-Key with Enclave-Gated Decryption）

### 核心思想
保持单密钥架构，但将 **sk 密封在服务器端的 TEE（可信执行环境）内**。服务器主机无法访问 sk，所有涉及 sk 的操作（解密、重新加密）在 TEE enclave 内执行。

### 实体与角色

| 实体 | 持有密钥/凭证 | 信任假设 | 职责 |
|------|--------------|----------|------|
| **KGC** | sk, pk, evk | 可信，初始化后离线 | 生成密钥，密封 sk 到 TEE |
| **Server Host** | pk, evk | 可恶意 | 接收密文、传递密文到 TEE、分发预取 |
| **TEE Enclave** | 密封的 sk, pk, evk | 硬件可信 | 解密、聚合、PTopk、重新加密 |
| **Client** | pk, evk, session_key | 半诚实 | 训练、加密上传、解密预取 |

### 密钥分发流程

```
KGC 生成 sk, pk, evk
│
├─ KGC 在离线安全环境中执行 TEE 密封：
│   sealed_sk = TEE.Seal(sk, enclave_identity)
│
├─ KGC ──sealed_sk──▶ Server Host (TLS)
├─ KGC ──pk, evk────▶ 公开
│
├─ Server Host 将 sealed_sk 加载到 TEE
├─ TEE 用自己的密封密钥解封，恢复 sk
│
├─ KGC 为每个 Client 生成会话密钥 k_i
├─ KGC ──k_i───────▶ Client i (TLS，初始化时)
│
KGC 销毁 sk，离线
```

### TEE 内部逻辑

```python
# 运行在 TEE Enclave 内，Server Host 无法访问此代码的内存
class EnclaveAggregator:
    def __init__(self, sk, pk, evk):
        self.sk = sk
        self.pk = pk
        self.evk = evk
        self.model = None  # 明文模型，仅在 enclave 内
    
    def process_round(self, ct_list, weights):
        # 1. 同态聚合
        ct_agg = sum(w * ct for w, ct in zip(weights, ct_list))
        
        # 2. 解密稀疏聚合结果（PTopk 路径）
        m = ckks_decrypt(self.sk, ct_agg)
        delta = ckks_decode(m)
        
        # 3. PTopk 服务器累加器
        delta = ptopk_server_update(delta)
        
        # 4. 更新明文模型
        self.model = self.model + delta
        
        # 5. 重新加密 packed 全局状态
        ct_global = ckks_encrypt(self.pk, pack(self.model))
        
        # 6. 计算预取密文
        delta_prefetch = compute_prefetch(self.model)
        
        # 7. 预取内容用会话密钥对称加密（非 CKKS）
        enc_prefetch = AES-GCM(delta_prefetch, k_session)
        
        return ct_global, enc_prefetch
```

### 操作流程

**阶段 A：客户端加密上传**
1. Client 用 pk 加密梯度 → 上传 Server Host

**阶段 B：TEE 内处理**
2. Server Host 将密文通过 ECALL 传入 TEE
3. TEE 执行上述 process_round 逻辑
4. TEE 输出 ct_global 和 enc_prefetch 给 Server Host

**阶段 C：预取下发**
5. Server Host 将 enc_prefetch 发送给 Client
6. Client 用 k_session 解密得到明文 delta_prefetch
7. Client 将 delta_prefetch 应用到本地明文模型

### 威胁模型分析

| 威胁 | 攻击者 | 能力 | 防御效果 |
|------|--------|------|----------|
| 半诚实 Server Host | Server Host | 遵循协议但试图读取 sk/明文 | ✅ 无法访问 enclave 内存，无法读取 sk |
| 恶意 Server Host | Server Host | 篡改输入密文、窥探内存 | ⚠️ 无法读取 sk，但可通过侧信道（缓存时序、功耗）推断 enclave 内数据 |
| TEE 漏洞利用 | 攻击者 | 利用已知 TEE 漏洞（如 Foreshadow）| ❌ 若 TEE 存在侧信道或漏洞，sk 可能泄露 |
| 客户端 | Client | 试图推断其他客户端数据 | ✅ 标准 IND-CPA 安全，Client 无 sk |
| 共谋 | Server Host + Client | 联合攻击 | ⚠️ Server Host 本无 sk，共谋无额外收益 |

**关键优势**：
- 无需修改 CKKS 密码学原语（标准单密钥即可）
- 无需额外通信轮次（解密在服务器本地 TEE 内完成）
- 客户端无需持有 sk，简化密钥管理
- Server Host 被攻破不会泄露 sk

**关键劣势**：
- 依赖硬件 TEE（Intel SGX/AMD SEV/ARM TrustZone），部署复杂
- TEE 存在已知侧信道攻击（缓存时序、分支预测、电压故障）
- TEE 内存受限（SGX enclave 通常 128MB），大型模型可能需要分页
- 需要 TEE 远程证明机制验证 enclave 代码完整性

---

## 方案三：SSCKKS-tn（Shamir-Shared CKKS with t-of-n Threshold Decryption）

### 核心思想
将 sk 使用 **(t, n)-Shamir 秘密共享**分成 n 份，分发给 n 个客户端。聚合密文的解密需要至少 t 个客户端提供部分解密份额，任何少于 t 个客户端无法获得任何信息。

### 实体与角色

| 实体 | 持有密钥 | 信任假设 | 职责 |
|------|----------|----------|------|
| **KGC** | sk（临时） | 可信，初始化后离线 | 生成密钥、执行秘密共享、分发 |
| **AggServer** | pk, evk | 可恶意 | 接收密文、同态聚合、收集解密份额、组合明文 |
| **Client i** | share_i, pk, evk | 半诚实或恶意 | 训练、加密上传、计算并提交解密份额 |

### 密钥分发流程

```
KGC 生成 sk, pk, evk
│
├─ KGC 选择阈值参数：(t, n)，如 t = ⌈2n/3⌉
├─ KGC 执行 (t, n)-Shamir 秘密共享：
│   sk → {share_1, share_2, ..., share_n}
│   多项式 f(x) = sk + a_1·x + ... + a_{t-1}·x^{t-1}
│   share_i = f(i)
│
├─ KGC ──share_i──▶ Client i  (TLS，一对一)
├─ KGC ──pk, evk──▶ 公开
│
KGC 销毁 sk, {a_k}，离线
```

### 阈值解密机制

#### 部分解密份额计算
每个 Client i 用其 share_i 计算部分解密份额：

d_i = c1 · share_i · λ_i   (mod q)

其中 λ_i 是 Lagrange 系数：

λ_i = Π_{j∈S, j≠i} j / (j - i)   (mod q)

S 是参与解密的客户端集合，|S| ≥ t。

#### 组合
AggServer 收集 {d_i}_{i∈S} 后组合：

m = c0 + Σ_{i∈S} d_i   (mod q)
  = c0 + c1 · Σ_{i∈S} share_i · λ_i
  = c0 + c1 · sk   (mod q)

（由 Shamir 秘密共享的重构性质：Σ share_i · λ_i = sk）

### 操作流程

**阶段 A：客户端加密上传**
1. 每个 Client i 用 pk 加密梯度 g_i
2. 上传 ct_i → AggServer

**阶段 B：服务器聚合**
3. AggServer 计算 ct_agg = Σ w_i · ct_i

**阶段 C：阈值解密（PTopk 路径）**
4. AggServer 广播 ct_agg 给所有客户端（或随机选择 t 个客户端）
5. 每个 Client i 计算 d_i = PartialDecrypt(share_i, ct_agg)
6. Client i 发送 d_i → AggServer
7. AggServer 收集至少 t 个份额，执行 Combine → 明文 m_agg
8. AggServer Decode 得到 delta，执行 PTopk 服务器累加器
9. AggServer 更新模型，重新加密 packed 全局状态 ct_global

**阶段 D：密文预取**
10. AggServer 计算预取密文 ct_prefetch
11. **预取阈值解密**：
    - AggServer 广播 ct_prefetch 给客户端
    - t 个客户端计算并提交解密份额
    - AggServer 组合得到明文 delta_prefetch
    - AggServer 发送明文 delta_prefetch 给目标 Client

    ⚠️ **问题**：预取需要每轮都走阈值解密，通信开销大。

**预取优化方案**：
- AggServer 在阶段 C 解密后，已经知道明文模型
- AggServer 可以直接用会话密钥加密预取内容发送给 Client
- 或：预取不走 CKKS 加密，直接明文传输（假设通信信道已加密如 TLS）

**更优方案**：预取密文由 AggServer 用 pk 加密，Client 请求 t 个其他客户端协助解密。
但这要求 Client 主动与其他客户端通信，改变了架构。

**最终设计**：预取内容用**对称会话密钥**加密（由 KGC 初始化时分发），不走 CKKS 阈值解密。

### 威胁模型分析

| 威胁 | 攻击者 | 能力 | 防御效果 |
|------|--------|------|----------|
| 半诚实 AggServer | AggServer | 遵循协议但试图推断 | ✅ AggServer 无 sk，无法单独解密任何密文 |
| 恶意 AggServer | AggServer | 篡改权重、伪造份额 | ⚠️ 可控制聚合过程，但无法解密（需 t 个客户端份额） |
| 半诚实 Client | Client i | 遵循协议但试图推断 | ✅ 单个 share_i 无法泄露 sk 或明文信息 |
| 恶意 Client | Client i | 提交错误解密份额 | ⚠️ 若 AggServer 不验证，可能被污染；需份额验证机制 |
| < t 客户端共谋 | 任意 < t 个 Client | 联合恢复 sk | ✅ 信息论安全，< t 份无法获得 sk 的任何信息 |
| ≥ t 客户端共谋 | 任意 ≥ t 个 Client | 联合恢复 sk | ❌ 可恢复 sk，但需较大规模共谋 |
| AggServer + < t Client 共谋 | 上述组合 | 联合攻击 | ✅ AggServer 无份额，< t Client 无法恢复 sk |

**关键优势**：
- **信息论安全**：少于 t 个客户端共谋，无法获得 sk 的任何信息（不依赖计算假设）
- 无单点失效：无单一实体持有完整 sk
- 客户端间强保密性：单个客户端无法解密其他客户端密文
- 可容忍最多 t-1 个客户端掉线或被攻破

**关键劣势**：
- 每轮解密需要至少 t 个客户端在线并参与
- 通信开销大：每轮需广播密文 + 收集 t 个份额
- 延迟高：需等待 t 个客户端响应
- TenSEAL 不支持阈值 CKKS，需自行实现 PartialDecrypt 和 Combine
- 预取流程复杂（需额外机制）

---

## 三方案对比总结

| 维度 | 方案一：3S-EAD | 方案二：TESK-EGD | 方案三：SSCKKS-tn |
|------|----------------|------------------|-------------------|
| **密钥类型** | 单密钥 + 三方拆分 | 单密钥 + TEE 密封 | 单密钥 + (t,n) 阈值共享 |
| **辅助实体** | Edge 节点 | TEE Enclave | 无（客户端即份额持有者） |
| **密钥分发对象** | Server, Edge, Client | Server(TEE), Client | 所有 Client |
| **解密所需实体** | 任意两方（Server+Edge 或 Server+Client）| TEE 单独完成 | ≥ t 个 Client |
| **额外通信** | 每轮 1 次往返（Server↔Edge 或 Server↔Client）| 无（TEE 在本地）| 每轮 t 次往返（Server↔Client）|
| **客户端间保密** | ✅ 单方无法解密 | ✅ 客户端无 sk | ✅ 单方无法解密 |
| **抗 Server 独破** | ✅ Server 单破无法解密 | ✅ Server Host 无 sk | ✅ Server 无 sk |
| **抗共谋** | ❌ 两方共谋即攻破 | ⚠️ TEE 侧信道风险 | ✅ 需 ≥ t 方共谋 |
| **硬件依赖** | 无 | TEE（SGX/SEV/TrustZone）| 无 |
| **部署复杂度** | 中（需 Edge 节点）| 高（需 TEE + 远程证明）| 高（需阈值密码学实现）|
| **与 PTopk 兼容** | ✅ Server 最终组合得到明文 | ✅ TEE 内直接明文操作 | ⚠️ AggServer 组合后明文操作 |
| **与预取兼容** | ✅ Server+Client 协同解密 | ✅ 会话密钥对称加密 | ⚠️ 需额外对称加密通道 |

---

## 推荐决策矩阵

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 追求部署简单、低延迟 | **方案一：3S-EAD** | 只需增加 Edge 节点，通信开销最小 |
| 追求最高单方安全性、接受硬件依赖 | **方案二：TESK-EGD** | TEE 提供硬件级隔离，无额外通信 |
| 追求抗共谋能力、容忍高延迟 | **方案三：SSCKKS-tn** | 信息论安全，需 ≥ t 方共谋才能攻破 |
| 无 Edge 节点、无 TEE | **方案一（简化版）** | sk 拆分为 Server+Client 两份，Client 间轮换 Edge 角色 |
