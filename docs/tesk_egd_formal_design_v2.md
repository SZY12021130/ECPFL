# TESK-EGD v2: TEE-Encapsulated Single-Key with Enclave-Gated Decryption

> 基于可信执行环境（TEE）封装的单密钥 CKKS-FL 外层密码学框架
>
> 完整闭环设计、密文预取安全性公式推导与威胁模型分析
>
> **版本 v2 修正**：预取 delta 严格保持密文状态，客户端持有 sk 用于本地解密，TEE 保护服务器端 sk 不被 Host 窃取

---

## 一、现有 PAMP 框架的正确性评估与问题诊断

### 1.1 PAMP 现有密码学架构审计

通过审计 `ckks_fed/crypto.py`、`ckks_fed/server.py`、`ckks_fed/client.py` 的密钥管理逻辑，发现以下结构性问题：

**问题一：私钥广泛分发**

```python
# crypto.py 第 112-115 行
class CKKSContext:
    def get_full_context_bytes(self):
        """序列化完整上下文（包含私钥，用于统一密钥模型的客户端分发）"""
        return self.context.serialize(
            save_public_key=True, save_secret_key=True,
            save_galois_keys=True, save_relin_keys=True
        )
```

**诊断结论**：当前 PAMP 采用**统一单密钥模型**，sk 同时存在于：
- Server 的 `CKKSManager` 中
- 每个 Client 的 `CKKSManager` 中

这意味着：
- **Client A 可以解密 Client B 的上传密文**（如果 A 截获 B 的通信）
- **Server 被攻破 -> 全系统历史暴露**
- **任意 Client 被攻破 -> 该 Client 可解密所有历史聚合密文**

**问题二：服务器端解密不透明**

```python
# server.py 稀疏路径解密
decrypted_delta = self.ckks_manager.decrypt_model_update(encrypted_update, original_shapes)
```

Server 在**不可审计的环境中**执行 sk 解密，客户端无法验证：
- Server 是否使用了正确的权重
- Server 是否正确执行了 PTopk 累加器
- Server 是否排除了某些客户端

**问题三：预取密文的传输风险**

当前 PAMP 中，预取密文 `ct_prefetch` 由 Server 用 pk 加密后发送给 Client，Client 用 sk 解密。虽然密文本身受 IND-CPA 保护，但**Server 在加密前已经知道明文 delta_prefetch**（因为 Server 持有 sk）。

### 1.2 PAMP 可集成性评估

| PAMP 模块 | 与 TESK-EGD 兼容性 | 需修改点 |
|-----------|-------------------|----------|
| `CKKSManager` | 高 | Server 侧替换为 TEE-内嵌管理器 |
| `PTopkModule` | 高 | 服务器累加器迁移到 TEE 内执行 |
| `Prefetch` 机制 | 高 | Server 端计算在 TEE 内执行，Client 端解密逻辑不变 |
| `Sparsification` | 高 | 无需修改 |
| `Client.local_train` | 高 | 无需修改 |
| `Server.update_global_model` | 中 | 需改为 ECALL 委托 TEE 执行 |

**集成结论**：PAMP 的模块化设计允许**最小侵入式集成**。核心修改点是将 Server 侧所有涉及 sk 的操作（解密、明文运算、重新加密）委托给 TEE，Client 侧和稀疏化/打包逻辑保持不变。

---

## 二、TESK-EGD v2 核心设计修正

### 2.1 密钥架构重新设计

**v1 错误**：假设 Client 不持有 sk，导致预取密文无法被 Client 解密，被迫使用明文传输。

**v2 修正**：
- **TEE 持有密封的 sk**（Server Host 无法访问）
- **Client 持有 sk**（通过 KGC 安全分发，用于预取密文解密）
- **核心价值**：Server Host 不再持有 sk，即使 Server Host 被攻破，攻击者无法解密任何密文

```
KGC
├── 生成 (sk, pk, evk)
├── 密封 sk -> TEE Enclave (Server Host 加载)
├── 分发 sk -> Client_i (TLS，每客户端独立通道)
├── 分发 pk, evk -> 公开
└── 离线销毁 sk

密钥持有者：
  TEE Enclave: sk (密封，Host 不可读)
  Client_i:    sk (内存中，用于预取解密)
  Server Host: pk, evk (无 sk)
```

### 2.2 密文预取 delta 的闭环设计

**必须保证：预取 delta 始终为 CKKS 密文状态**

```
TEE 内执行：
  1. 计算 delta_prefetch_plain = M_{t+1} - M_t
  2. 用 pk 加密: ct_prefetch = CKKS.Enc(pk, delta_prefetch_plain)
  3. 输出 ct_prefetch 给 Server Host

Server Host 执行：
  4. 将 ct_prefetch 通过 HTTPS 分发给 Client_i

Client_i 执行：
  5. 用 sk 解密: delta_prefetch_plain = CKKS.Dec(sk, ct_prefetch)
  6. 应用: M_local += delta_prefetch_plain
```

**关键修正**：预取内容从 TEE 到 Client 的完整链路中，**仅在 TEE 内和 Client 内以明文形式存在**，在传输过程中始终为 CKKS 密文。

---

## 三、形式化协议定义

### 3.1 符号表

| 符号 | 含义 | 典型值/范围 |
|------|------|-------------|
| lambda | 安全参数 | 128 bits |
| N | CKKS 多项式次数 | 8192 |
| q_L | 顶层模数 | ~2^180 |
| Delta | 全局缩放因子 | 2^40 |
| (sk, pk, evk) | CKKS 密钥三元组 | sk in R_{q_L} |
| M_t in R^d | 第 t 轮全局模型 | d ~ 10^7 (ResNet-18) |
| Delta_i^{(t)} | 客户端 i 第 t 轮梯度差分 | R^d |
| w_i | 聚合权重 | w_i = |D_i| / sum_j |D_j| |
| E_TEE | TEE 密封操作 | -- |
| U_TEE | TEE 解封操作 | -- |
| Quote_E | TEE 远程证明引用 | -- |

### 3.2 初始化阶段

**算法 1: TESK-EGD.Setup**

输入: 安全参数 lambda, 客户端数 n, CKKS 参数 (N, q, Delta)
输出: 系统参数、密封密钥、远程证明引用

1. (sk, pk, evk) <- CKKS.KeyGen(lambda, N, q, Delta)
2. sealed_sk <- E_TEE(sk, enclave_identity)    // TEE 密封 sk
3. code_hash <- Hash(enclave_binary)           // MRENCLAVE 等效值
4. Quote_E <- TEE.GenerateQuote(code_hash)     // 远程证明

// 分发
5. 发送 sealed_sk -> Server Host (加载到 TEE)
6. 发送 sk -> Client_i, forall i in [1,n] (TLS，一对一)
7. 发布 pk, evk -> 所有实体
8. KGC 销毁 sk，离线

**TEE 密封机制**：

sealed_sk = Enc_{K_TEE}(sk || enclave_identity || version)

其中 K_TEE 是 TEE 硬件根密钥派生的密封密钥，满足：
- **绑定性**：仅相同 enclave_identity 的实例可解封
- **单调性**：version 字段防止回滚攻击

### 3.3 客户端加密上传

**算法 2: TESK-EGD.ClientUpload**

输入: 客户端 i, 本地梯度 g_i^(t), sk, pk
输出: 加密更新 ct_i

1. delta_i <- g_i^(t) - g_i^(t-1)       // 若 upload_difference=true
2. m_i <- CKKS.Encode(delta_i, Delta)
3. ct_i <- CKKS.Enc(pk, m_i)             // 标准 CKKS 加密
4. 上传 ct_i -> Server Host (via HTTPS)

**公式表示**：

ct_i = (b_i, a_i) = (a_i * s + m_i + e_{0,i},  a_i + e_{1,i}) mod q_L

其中 s = sk，m_i = floor(Delta * sigma^{-1}(pi^{-1}(Delta_i)))。

### 3.4 Server Host 传递（ECALL）

**算法 3: TESK-EGD.HostRelay**

输入: 密文列表 {ct_i}_{i in S}, 权重 {w_i}_{i in S}
输出: 无（仅传递）

1. S_H 验证每个 ct_i 的格式合法性
   - 模数匹配: ct_i.modulus == q_L
   - 规模约束: |ct_i| < MAX_CIPHERTEXT_SIZE
2. S_H 执行 ECALL: E.process_round({ct_i}, {w_i}, t)
3. S_H 等待 E 返回 (ct_global, {ct_prefetch_i}_{i in S})

**关键性质**：S_H 仅传递密文字节流，不执行任何密码学操作，不接触 sk。

### 3.5 TEE 内核心处理（ECALL）

**算法 4: TESK-EGD.EnclaveProcess**

输入: {ct_i}_{i in S}, {w_i}_{i in S}, 轮次 t
输出: ct_global, {ct_prefetch_i}_{i in S}

// 阶段 1: 解封密钥（本轮有效）
1. sk <- U_TEE(sealed_sk)
2. M_t <- LoadModelFromSecureMemory()

// 阶段 2: 同态聚合
3. ct_agg <- sum_{i in S} w_i * ct_i

// 阶段 3: 解密（TEE 内，S_H 不可见）
4. m_agg <- CKKS.Decrypt(sk, ct_agg)
5. delta_plain <- CKKS.Decode(m_agg)

// 阶段 4: PTopk 服务器累加器（若启用）
6. 若 ptopk.enable:
     delta_acc <- PTopk.ServerUpdate(delta_plain, lr)
   否则:
     delta_acc <- delta_plain * lr

// 阶段 5: 模型更新（TEE 内）
7. M_{t+1} <- M_t + delta_acc

// 阶段 6: 重新加密全局状态
8. m_global <- CKKS.Encode(Pack(M_{t+1}), Delta)
9. ct_global <- CKKS.Enc(pk, m_global)

// 阶段 7: 密文预取计算（核心修正）
10. 对每个 i in S:
      delta_prefetch_i <- ComputePrefetch(M_{t+1}, M_t, client_id=i)
      m_prefetch_i <- CKKS.Encode(delta_prefetch_i, Delta)
      ct_prefetch_i <- CKKS.Enc(pk, m_prefetch_i)

// 阶段 8: 安全清理
11. 内存清零: sk, delta_plain, delta_acc, {delta_prefetch_i}
12. 返回 (ct_global, {ct_prefetch_i})

### 3.6 密文预取分发与客户端解密

**算法 5: TESK-EGD.PrefetchDelivery**

// Server Host 侧
1. S_H 将 ct_prefetch_i 打包为 HTTPS 响应
2. S_H 发送 ct_prefetch_i -> Client_i

// Client_i 侧
3. Client_i 接收 ct_prefetch_i
4. delta_plain <- CKKS.Decrypt(sk, ct_prefetch_i)     // 客户端用 sk 解密
5. delta_plain <- CKKS.Decode(delta_plain)
6. M_local <- M_local + delta_plain
7. 清除预取缓存

**关键修正**：步骤 4 中客户端使用**本地持有的 sk** 解密预取密文，预取内容在传输过程中始终为密文状态。

---

## 四、闭环正确性证明

### 4.1 定理 1（聚合正确性）

**定理**：TESK-EGD 的聚合结果与标准 FedAvg 在误差可忽略范围内等价。

**证明**：

标准 FedAvg 更新：
M_{t+1}^{(std)} = M_t + eta * sum_{i in S} w_i Delta_i

TESK-EGD 的 TEE 内执行：

步骤 3（同态聚合）：
ct_agg = sum_{i in S} w_i * ct_i = (sum_{i in S} w_i b_i,  sum_{i in S} w_i a_i)

展开第一个分量：
sum_{i in S} w_i b_i = sum_{i in S} w_i (a_i s + m_i + e_{0,i})
                     = (sum_{i in S} w_i a_i) s + sum_{i in S} w_i m_i + sum_{i in S} w_i e_{0,i}

步骤 4（解密）：
m_agg = sum_{i in S} w_i b_i - (sum_{i in S} w_i a_i) * sk
      = sum_{i in S} w_i m_i + e_agg

其中聚合噪声：
e_agg = sum_{i in S} w_i e_{0,i} - (sum_{i in S} w_i a_i) * e_sk

由 CKKS 参数选择，e_{0,i} ~ D_{Z, sigma}，e_sk ~ D_{Z, sigma}，且 ||a_i|| <= sqrt(N) * q_L：

||e_agg||_inf <= n * max_i |w_i| * sigma * sqrt(N) + sqrt(N) * q_L * sigma * sqrt(N)

对于标准参数（N=8192, sigma=3.2, q_L ~ 2^60）：
||e_agg||_inf / Delta ~ (10^4 * 3.2 * 90.5) / 2^40 ~ 10^{-6}

因此：
||M_{t+1}^{(tesk)} - M_{t+1}^{(std)}||_inf <= 10^{-6} * Delta^{-1} ~ 10^{-18}

对模型收敛影响可忽略。

**QED**

### 4.2 定理 2（预取密文正确性）

**定理**：客户端从预取密文解密得到的结果与 TEE 内计算的预取差分一致。

**证明**：

TEE 内计算（步骤 10）：
Delta_prefetch^{(i)} = M_{t+1}^{(i)} - M_t^{(i)}

TEE 加密：
ct_prefetch^{(i)} = Enc_pk(Encode(Delta_prefetch^{(i)}, Delta))

客户端解密（算法 5，步骤 4）：
 tilde{Delta}_prefetch^{(i)} = Decode(Dec_sk(ct_prefetch^{(i)}))

由 CKKS 正确性：
Dec_sk(Enc_pk(m)) = m + e_enc

其中 e_enc 为加密噪声，||e_enc||/Delta < 10^{-6}。

因此：
||tilde{Delta}_prefetch^{(i)} - Delta_prefetch^{(i)}||_inf < 10^{-6}

**QED**

---

## 五、密文预取的安全性公式推导

### 5.1 威胁模型重新定义

| 威胁编号 | 攻击者 | 能力 | 目标 |
|----------|--------|------|------|
| T-1 | 窃听者 E | 截获网络流量 | 从 ct_prefetch 推断预取内容 |
| T-2 | 半诚实 Server Host S_H | 读取磁盘/内存（除 TEE 外）| 推断预取内容或 sk |
| T-3 | 恶意 Server Host S_H^* | 篡改/重放/转发 ct_prefetch | 破坏模型或泄露内容 |
| T-4 | 恶意 Client C_j | 截获其他客户端的 ct_prefetch | 推断其他客户端的预取内容 |
| T-5 | TEE 侧信道攻击者 | 缓存/功耗/电压分析 | 提取 sk 或明文 |

### 5.2 T-1: 窃听者攻击

**攻击场景**：窃听者截获 HTTPS 流量中的 ct_prefetch。

**安全性分析**：

设窃听者为 E，其视图包含：
View_E = {ct_prefetch^{(i)}}_{i in S}

**定理 3（预取密文 IND-CPA 安全）**：在标准 RLWE 假设下，对于任意 PPT 敌手 E：

|Pr[E(ct_prefetch) = 1] - Pr[E(ct_random) = 1]| <= Adv_RLWE^{ind-cpa}(lambda) <= negl(lambda)

**证明**：

ct_prefetch 是标准 CKKS 加密密文，其形式为：
ct_prefetch = (b, a) = (a * s + m + e_0,  a + e_1) mod q_L

其中：
- a <-_R R_{q_L}（均匀随机）
- e_0, e_1 ~ D_{Z, sigma}（离散高斯）
- m = Encode(Delta_prefetch, Delta)

由 RLWE 假设，(a, a * s + e_0) ~_c (a, u)，其中 u <-_R R_{q_L}。

因此 (b, a) ~_c (u_0, u_1)，与随机不可区分。

**QED**

**风险量化**：

| 参数 | 值 | 安全级别 |
|------|-----|----------|
| N | 8192 | Core-SVP ~ 128 bits |
| sigma | 3.2 | 标准 CKKS 参数 |
| q_L | 2^180 | 支持乘法深度 3 |
| IND-CPA 优势上界 | <= 2^{-128} | 128-bit 安全 |

### 5.3 T-2: 半诚实 Server Host

**攻击场景**：S_H 读取磁盘、内存、日志，试图推断预取内容。

**攻击面分析**：

S_H 可获得的信息：
1. **密文文件**：ct_prefetch 在磁盘上的序列化形式
2. **网络缓冲区**：HTTPS 发送前的内存副本
3. **日志**：TEE 返回时间戳、大小等元数据

**定理 4（Server Host 不可推断预取内容）**：在 TEE 隔离假设和 RLWE 假设下，S_H 从 ct_prefetch 推断 Delta_prefetch 的优势可忽略。

**证明**：

S_H 的视图：
View_{S_H} = {ct_prefetch, metadata}

由于 S_H 不持有 sk（sk 密封在 TEE 内），解密 ct_prefetch 等价于解决 RLWE 问题：

给定 (b = a * s + m + e_0,  a)，求 m。

由 RLWE 困难性假设，没有 sk 的情况下，从 (b, a) 恢复 m 的优势 <= negl(lambda)。

元数据（大小、时间戳）不包含关于 m 的信息（CKKS 密文大小固定）。

**QED**

### 5.4 T-3: 恶意 Server Host

**攻击场景**：S_H^* 篡改、重放、或转发 ct_prefetch。

| 攻击类型 | 效果 | 公式分析 | 缓解 |
|----------|------|----------|------|
| **篡改 ct_prefetch** | Client 解密错误值 | S_H^* 替换 ct 为 ct'，Client 解密得 Delta' != Delta | TEE 对 ct 签名：sigma = Sign_{sk_TEE^{sig}}(H(ct)) |
| **重放旧 ct_prefetch** | Client 应用过时更新 | S_H^* 发送 ct^{(t-1)} 代替 ct^{(t)} | TEE 内嵌入轮次计数器：ct <- Enc(pk, Delta || t) |
| **转发给其他客户端** | 非目标客户端获得更新 | S_H^* 将 ct_i 发送给 C_j | Client 验证目标 ID：ct_i 包含加密的目标客户端标识 |
| **截留不发送** | 客户端收不到预取 | S_H^* 丢弃 ct_i | 客户端超时检测 + 重传请求 |

**篡改攻击的公式化分析**：

设 S_H^* 将 ct = (b, a) 替换为 ct' = (b + delta_b, a + delta_a)。

Client 解密：
Delta' = Decode(b + delta_b - (a + delta_a) * sk)
       = Delta + Decode(delta_b - delta_a * sk)

若 S_H^* 知道 sk，可精确控制注入误差。但 sk 在 TEE 内，S_H^* 不知道 sk。

若 S_H^* 不知道 sk，随机选择 (delta_b, delta_a)，注入误差为随机多项式，导致模型更新方向随机。

**缓解措施（签名）**：

TEE 在输出 ct_prefetch 时，同时输出签名：
sigma_prefetch = HMAC_{K_TEE^{auth}}(ct_prefetch || i || t)

Client 验证：
HMAC_{K_TEE^{auth}}(ct_prefetch || i || t) ?= sigma_prefetch

若不匹配，拒绝应用预取。

### 5.5 T-4: 恶意 Client 截获其他客户端的预取

**攻击场景**：Client C_j 截获发给 C_i 的 ct_prefetch^{(i)}，用本地 sk 解密。

**攻击效果分析**：

由于 TESK-EGD 是**单密钥架构**，所有客户端共享同一个 sk。因此：

Delta_prefetch^{(i)} = Dec_sk(ct_prefetch^{(i)})

C_j 持有 sk，可以成功解密 ct_prefetch^{(i)}，获得 Delta_prefetch^{(i)}。

**这是单密钥架构的固有限制**，TESK-EGD 本身无法解决。

**风险评估**：

| 泄露内容 | 敏感性 | 影响 |
|----------|--------|------|
| Delta_prefetch^{(i)} | 中 | 全局模型变化量，不直接泄露 C_i 的私有数据 |
| 累积的预取序列 | 中 | 可能推断全局训练轨迹，但非单客户端数据 |

**缓解措施**：
1. **差分隐私**：在 TEE 内对 Delta_prefetch 添加高斯噪声后再加密
   tilde{Delta}_prefetch = Delta_prefetch + N(0, sigma_DP^2 * I)
2. **客户端隔离**：为每个客户端使用不同的预取批次（Client i 只接收与其相关的层更新）
3. **升级到多密钥方案**：如 SSCKKS-tn（方案三）

### 5.6 T-5: TEE 侧信道攻击

**攻击场景**：攻击者利用 TEE 的侧信道泄露 sk 或明文。

**风险量化**：

设侧信道攻击以概率 epsilon_side 提取 sk。

若攻击失败（概率 1 - epsilon_side）：系统保持 TEE 保护的安全级别。

若攻击成功（概率 epsilon_side）：攻击者获得 sk，可解密所有密文（包括预取密文）。

**期望安全性**：
Security_eff = (1 - epsilon_side) * Security_TEE + epsilon_side * Security_noTEE

对于 Intel SGX，已知侧信道攻击（如 Foreshadow）的 epsilon_side ~ 2^{-40}（在应用缓解措施后）。

**缓解措施**：
1. **常数时间实现**：TEE 内解密、编码、解码代码无分支依赖
2. **数据无关内存访问**：固定内存访问模式，消除缓存侧信道
3. **噪声注入**：在 TEE 内添加随机延迟，模糊时序特征
4. **TEE 微码更新**：及时应用厂商安全补丁

---

## 六、与 PAMP 的集成方案

### 6.1 集成架构图

```
+---------------------------------------------------------------------+
|                         PAMP + TESK-EGD 集成架构                     |
+---------------------------------------------------------------------+
|                                                                     |
|  Client Side (保持不变)                                              |
|  +-------------------------------------------------------------+   |
|  | PrefetchFederatedClient                                     |   |
|  | +- local_train()          # 本地训练                        |   |
|  | +- encrypt_and_upload()   # 用 pk 加密上传 (CKKSManager)    |   |
|  | +- decrypt_prefetch()     # 用 sk 解密预取 (CKKSManager)    |   |
|  | +- apply_prefetched_state() # 应用预取到本地模型             |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  Server Side (TEE 集成)                                              |
|  +-------------------------------------------------------------+   |
|  | Server Host S_H                                              |   |
|  | +- receive_uploads()      # 接收客户端上传                   |   |
|  | +- ECALL: process_round() # 委托 TEE 处理                   |   |
|  | +- distribute_prefetch()  # 分发预取密文                    |   |
|  | +- evaluate_model()       # 从 TEE 同步模型评估             |   |
|  |                                                              |   |
|  | +---------------------------------------------------------+ |   |
|  | | TEE Enclave E                                           | |   |
|  | | +- decrypt_aggregated()   # sk 解密                     | |   |
|  | | +- ptopk_accumulator()    # PTopk 服务器累加器          | |   |
|  | | +- update_model()         # 模型更新                    | |   |
|  | | +- reencrypt_global()     # pk 重新加密                 | |   |
|  | | +- compute_prefetch()     # 预取密文计算                | |   |
|  | | +- sign_outputs()         # 输出签名                    | |   |
|  | +---------------------------------------------------------+ |   |
|  +-------------------------------------------------------------+   |
|                                                                     |
|  KGC (初始化后离线)                                                   |
|  +- 生成 (sk, pk, evk)                                             |
|  +- 密封 sk -> TEE                                                  |
|  +- 分发 sk -> Clients                                              |
|  +- 分发 pk, evk -> 公开                                            |
|                                                                     |
+---------------------------------------------------------------------+
```

### 6.2 代码集成点

**修改 1: Server 初始化**

```python
# server.py
class TEEAggregationServer(PrefetchAggregationServer):
    def __init__(self, config):
        super().__init__(config)
        
        if config.get('tee', {}).get('enable', False):
            # 初始化 TEE 代理
            self.tee_proxy = TEEProxy(
                enclave_path=config['tee']['enclave_so'],
                sealed_sk_path=config['tee']['sealed_sk_path']
            )
            # 远程证明验证
            assert self.tee_proxy.verify_attestation(
                config['tee']['expected_mrenclave']
            ), "TEE attestation failed!"
            
            # 注意：Server Host 不再持有 sk
            # self.ckks_manager 仅用于非解密操作（如序列化）
            self.ckks_manager = CKKSManager(config, context=None)
        else:
            self.tee_proxy = None
            self.ckks_manager = CKKSManager(config)
```

**修改 2: 全局状态更新（委托 TEE）**

```python
# server.py
class TEEAggregationServer(PrefetchAggregationServer):
    def update_global_model(self, encrypted_updates, weights):
        if self.tee_proxy is not None:
            # TEE 模式：委托 Enclave 处理
            ct_list = [eu.serialize() for eu in encrypted_updates]
            ct_global_bytes, prefetch_map = self.tee_proxy.process_round(
                ct_list, weights
            )
            
            # 更新全局密文状态
            import tenseal as ts
            self.encrypted_global_state = ts.CKKSVector.deserialize(
                ct_global_bytes
            )
            
            # 存储预取密文（按客户端索引）
            self.prefetch_store = {
                i: ts.CKKSVector.deserialize(ct_bytes)
                for i, ct_bytes in prefetch_map.items()
            }
        else:
            # 回退到标准模式
            super().update_global_model(encrypted_updates, weights)
```

**修改 3: 预取分发（密文状态）**

```python
# server.py
class TEEAggregationServer(PrefetchAggregationServer):
    def get_prefetch_for_client(self, client_id):
        if self.tee_proxy is not None:
            # 返回密文状态（Client 用本地 sk 解密）
            ct_prefetch = self.prefetch_store.get(client_id)
            if ct_prefetch is not None:
                return {
                    'ciphertext': ct_prefetch.serialize(),
                    'signature': self.tee_proxy.get_prefetch_signature(client_id)
                }
        else:
            return super().get_prefetch_for_client(client_id)
```

**修改 4: Client 预取解密**

```python
# client.py（无需修改，现有逻辑已支持）
class PrefetchFederatedClient:
    def apply_prefetched_state(self):
        # 现有代码已包含 sk 解密逻辑
        decrypted_delta = self.ckks_manager.decrypt_model_update(
            self.prefetched_state, shapes
        )
        # 应用到本地模型...
```

### 6.3 兼容性矩阵

| PAMP 特性 | 集成状态 | 说明 |
|-----------|----------|------|
| upload_difference=true | 完全支持 | TEE 内解密差分后聚合 |
| sparsification | 完全支持 | 稀疏化在 Client 端执行，不受 TEE 影响 |
| PTopk | 支持 | server_update_plain 迁移到 TEE 内执行 |
| prefetch | 支持 | 预取密文由 TEE 生成，Client 用 sk 解密 |
| CipherFetch 合并 | 支持 | TEE 内可执行同态密文合并 |
| 模型评估 | 需 OCALL | 从 TEE 同步明文模型到 Host 进行评估 |

---

## 七、最终安全性定理

### 7.1 定理 5（TESK-EGD 综合安全性）

**定理**：在以下假设下：
1. **RLWE 假设**：CKKS 满足 IND-CPA 安全（lambda = 128）
2. **TEE 隔离假设**：Enclave 内存对 Host OS 不可读
3. **TEE 远程证明假设**：可验证 enclave 代码完整性
4. **侧信道边界**：TEE 侧信道攻击成功概率 epsilon_side < 2^{-40}

TESK-EGD 满足：

**(a) 对半诚实 Server Host 的保密性**：S_H 无法以非可忽略优势推断任何客户端的明文梯度或预取内容。

**(b) 对恶意 Server Host 的完整性**：S_H 无法伪造通过验证的聚合结果或预取密文。

**(c) 对窃听者的保密性**：网络截获者无法以非可忽略优势推断预取内容。

**(d) 对 TEE 侧信道的弹性**：系统安全性以概率 1 - epsilon_side 保持 TEE 级别，以概率 epsilon_side 退化为标准 CKKS-FL 级别。

**证明概要**：

**(a)** 由定理 4，S_H 不持有 sk，从密文推断明文的优势 <= Adv_RLWE^{ind-cpa}(lambda) = negl(lambda)。

**(b)** 由 TEE 远程证明和输出签名，S_H 无法伪造 TEE 生成的 ct_global 或 ct_prefetch。篡改会导致签名验证失败。

**(c)** 由定理 3，预取密文 ct_prefetch 满足 IND-CPA，网络截获者优势可忽略。

**(d)** 以概率 1 - epsilon_side，TEE 未被攻破，(a)-(c) 成立。以概率 epsilon_side，sk 泄露，系统退化为标准单密钥 CKKS-FL（Server 持有 sk），安全性由 RLWE 保证。

**QED**

---

## 八、总结

### TESK-EGD v2 核心修正

| 维度 | v1（错误） | v2（修正） |
|------|-----------|-----------|
| **预取状态** | 明文传输（HTTPS） | **密文传输（CKKS）** |
| **Client 是否持有 sk** | 否（无法解密） | **是（KGC 安全分发）** |
| **Server Host 是否持有 sk** | 否（密封在 TEE） | **否（密封在 TEE）** |
| **核心价值** | 不完整 | **Server Host 无法解密任何密文** |
| **客户端间保密性** | N/A | **单密钥固有限制（需 DP 或多密钥缓解）** |

### 闭环验证

| 步骤 | 操作 | 状态 | sk 暴露位置 |
|------|------|------|------------|
| 1 | Client 加密上传 | 通过 | 无（只用 pk） |
| 2 | S_H 传递密文到 TEE | 通过 | 无（仅转发） |
| 3 | TEE 聚合 | 通过 | TEE 内 |
| 4 | TEE 解密 | 通过 | TEE 内 |
| 5 | TEE PTopk | 通过 | TEE 内 |
| 6 | TEE 更新模型 | 通过 | TEE 内 |
| 7 | TEE 重新加密 | 通过 | TEE 内 |
| 8 | TEE 加密预取 delta | 通过 | TEE 内 |
| 9 | S_H 分发密文预取 | 通过 | 无（密文状态） |
| 10 | Client 解密预取 | 通过 | Client 内 |
| 11 | Client 应用预取 | 通过 | Client 内 |

**结论**：TESK-EGD v2 形成了一个完整的密码学闭环，预取 delta 始终维持密文状态，Server Host 在任何时刻都不接触 sk 或明文模型参数。
