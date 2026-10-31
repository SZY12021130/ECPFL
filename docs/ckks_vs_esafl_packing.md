# CKKS（merged）打包 vs ESAFL EP 打包：两条加密聚合路径的对比

> 面向懂联邦学习、但不太熟悉同态加密的读者。
> 涉及的代码：`ckks_fed/packing.py`（`MergedPacking` / `ESAFLPacking` / `ESHEEPPacking`）、
> `ckks_fed/crypto.py`（`CKKSManager` 及 PUREPY 分支）、`ckks_fed/eshe.py`（`PurePyESHE`）。
> ESAFL 论文：arXiv:2305.08599，§V-B2（EP：Messages Encoding and Polynomials Packing）。

## 1. 总览表

| 维度 | CKKS（merged）打包 | ESAFL EP 打包 |
|---|---|---|
| 加密方案 | CKKS（TenSEAL，`ts.ckks_vector`） | ESHE（`ckks_fed/eshe.py` 纯 Python 复现） |
| 密文形式 | 一对多项式 `(c0, c1)` | **单个多项式** `ct = a^t·s_i + p·e + m`（再附带明文 mask 字段，仅供服务器） |
| 打包单位 | 复数 SIMD slot（每个 slot 一个浮点值，4096 个/密文） | 整数多项式系数，每个系数用**位域**再切 T 个 slot |
| slot 结构 | slot 间相互独立，值就是浮点数本身 | 每个系数 ß_j 内：T−1 个数据 slot + 1 个全零 slot（进位余量） |
| 数据进密文前 | 可选量化（`ESAFLPacking` 走 53-bit double 位域） | **必须**对称量化到 logq0=10 bit 无符号整数 |
| 聚合方式 | 密文加法 / 标量乘加权平均 | 密文**逐系数整数加法**（纯加法同态） |
| 解密方式 | 私钥 `s` 一次解出全部 slot 浮点值（近似） | one-shot `[[ct − a^t·s]_Q]_p`：mod p 精确消噪，再位域拆分、求平均、反量化 |
| 误差来源 | CKKS 编码/加密噪声，**近似**精度 | 仅量化误差；聚合在整数域**精确**进行 |
| 数值语义 | 浮点 SIMD（"每个 slot 一个浮点数"） | 定点整数（"每个 slot 一个小整数，靠 pad 位防进位串位"） |

一句话概括：**CKKS 路径是"浮点 SIMD + scale 管理"，EP 路径是"定点整数 + 位域 slot + pad 防进位"。**

---

## 2. CKKS 路径：从梯度到多项式到密文

代码路径：`CKKSManager.encrypt_model_update` → `MergedPacking.pack` →
`CKKSEncryptor.encrypt_chunks` → TenSEAL。实验配置 `configs/config_optimal.yaml`：
`poly_modulus_degree=8192`，`coeff_mod_bit_sizes=[60,40,40,60]`，`global_scale=2^40`。

1. **flatten + 切块**：所有层按参数名排序后 concat 成一个长数组
   （`MergedPacking.pack`，`ckks_fed/packing.py:123`），
   再按 `slot_count = poly_modulus_degree // 2 = 4096` 切成若干 chunk，不足补 0。

2. **CKKS 编码（浮点 → SIMD slot）**：每个 chunk 是 4096 个 float64。
   TenSEAL 把它们编码成环 `R = Z[X]/(X^8192+1)` 上的一个多项式，使得解密后
   多项式的"典范嵌入"（canonical embedding，可理解为对每个 slot 做一次 4096 点 FFT
   的逆变换）恰好还原这 4096 个浮点数。直觉：**一个多项式系数空间被"掰"成了
   4096 个并行的复数通道（slot）**，每个通道独立存一个实数/复数，互不干扰。

3. **加密（scale = 2^40）**：`ts.ckks_vector(ctx, chunk, scale=2^40)`
   （`ckks_fed/crypto.py:205`）。实际过程是"先乘 2^40 取整 → 编码进 slot →
   加 RLWE 噪声加密"。密文是一对多项式 `(c0, c1)`，满足
   `c0 + c1·s ≈ encode(m·2^40)`。系数模数链共 60+40+40+60 = 200 bit，
   这是整份密文能承受的"噪声预算"总量。

4. **聚合（同态加法，可加可加权）**：服务器用 `CKKSEvaluator` 做密文加法
   （`ct1 + ct2`，slot 对应相加）或 `weighted_average`（标量乘权重再相加，
   `ckks_fed/crypto.py:267`）。注意：
   - **加法**不消耗噪声预算，但 slot 值求和可能溢出 double/scale 的有效位；
   - **乘法**（标量乘权重也是一种乘法）会让 scale 相乘（2^40 × w），
     必须靠 coeff_mod_bit_sizes 中预留的"中间模数"做**重线性化/重缩放**
     把 scale 拉回 2^40——每乘一次消耗一段模数链，链用完密文就"死"了。
     这是 CKKS 的 scale 管理问题，也是配置里 `[60,40,40,60]` 中间两项存在的原因。

5. **解密**：服务器持私钥 `s`，`ct.decrypt()` 一次解出全部 4096 个 slot 的
   浮点值（`CKKSDecryptor.decrypt`，`ckks_fed/crypto.py:218`），
   `MergedPacking.unpack` 按 metadata 里的 shapes/offsets 还原各层张量。
   结果是**近似值**——CKKS 的编码和噪声都带来 10^-3 ~ 10^-6 量级误差。

> 变体：若 `packing.strategy="esafl"`，则走项目自研 `ESAFLPacking`
> （`ckks_fed/packing.py:679`）——先量化成 10-bit 无符号整数，再把 `slots2` 个整数
> **bit-shift 拼进一个 double 的 53-bit 精确整数位域**，然后当普通浮点送 CKKS。
> 它只是"借 CKKS 当传输管道"，加密、聚合、解密完全还是上面这套 CKKS 流程。

---

## 3. ESAFL EP 路径：从梯度到多项式到打包

代码路径：`CKKSManager` PUREPY 分支（`ckks_fed/crypto.py:403-439`）→
`ESHEEPPacking.pack` → `PurePyESHE.encrypt_chunk` → `aggregate_ciphertexts` →
`PurePyESHE.decrypt` + `ESHEEPPacking.unpack_average`。
EP 参数由公式推导（`ckks_fed/packing.py:976-990`），实验典型值：
`n=4096, logp=50, logq0=10, N=25` → `pad=6, T=3, data_slots=2`。

1. **归一化 + 对称量化（全客户端共享 scale）**：
   `scale = quant_clip / max_q`，其中 `max_q = 2^(logq0−1) − 1 = 511`。
   所有客户端必须用配置里同一个 `quant_clip`
   （`ckks_fed/packing.py:1028-1046`）——这是 EP 密文求和语义正确的前提。
   浮点 x 被 clip 到 `[-scale·511, scale·511]`，四舍五入成有符号整数 q，
   再 `+ max_q` 映射成**无符号整数 u ∈ [0, 1023]**。

2. **EP.EcdPack（位域打包）**：明文是 `n=4096` 个系数的多项式。
   EP.Setup 推导参数：
   - `pad = ⌈log2 N⌉ + 1`（N=25 → pad=6，防进位串位）
   - `slot_bits = pad + logq0 = 16`
   - `T = ⌊logp / slot_bits⌋ = ⌊50/16⌋ = 3` → **每系数 3 个 slot，其中只有
     T−1=2 个放数据，最高 slot 恒为 0**（零多项式 ϑ，进位余量）
   - 安全校验：`N·(2^logq0 − 1) = 25·1023 < 2^16 = slot 位域容量`
   第 i 个数据 slot 放在 `shift = (T−1−i)·slot_bits` 的位上
   （`ckks_fed/packing.py:1074-1077`，对应论文 Eq. 9）。
   每个密文打包 `n × (T−1) = 4096 × 2 = 8192` 个值。

3. **ESHE 加密（无 scale 概念）**：
   `ct = [a^t·s_i + p̃·e + m]_Q`（`ckks_fed/eshe.py:435`），其中：
   - `a^t`：由共享种子 B + 计数器 t（轮次号）本地再生的公共随机多项式（PRPG），无需传输；
   - `s_i`：客户端私钥，三元分布 `{-1,0,1}^4096`；服务器（可信 AS）持有 `s = Σs_i`；
   - `p̃·e`：噪声项，p = 2^50，e 为中心二项分布（η=4），系数上界 ±4；
   - `Q = q1·q2`，两个 31/30-bit NTT 友好素数之积，**Q ≈ 2^60**；
   - `m`：上一步打包好的整数系数多项式（系数 < p）。
   密文是**一个**多项式（外加 mask 字段 `a^t·s_i`，明文存储、仅服务器用）。

4. **聚合（EP.Eval：密文逐系数求和）**：服务器把 N 个密文系数相加：
   `C = Σ_i ct_i`（`ckks_fed/eshe.py:339`）。因为是整数域加法：
   - 每个 slot 内是 Σu（< 2^16），**不串位**（这就是 pad 存在的意义）；
   - 总噪声是 Σp·e_i，只要 `|p·Σe + Σm| < Q/2`（≈2^59）解密就精确——
     25 个客户端时噪声上界离 2^59 非常远，**加法聚合不会"用完预算"**；
   - 只有加法同态，没有乘法/标量乘：FedAvg 的 1/N 权重是解密后在明文域除的。

5. **解密（one-shot）**：`M = [[C − a^t·s]_Q]_p`（`ckks_fed/eshe.py:498`）：
   系数级先 mod Q 再 mod p。p·Σe 项被 mod p **精确消掉**，得到整数系数 ß。
   然后 `unpack_average`（`ckks_fed/packing.py:1097`）按 slot 移位截取
   （论文 Eq. 10）还原每个位置的整数和，减偏移 `N·max_q`，
   **除以 N 得平均**，乘 scale 反量化回浮点。

---

## 4. 参数对比表（项目实际配置值）

| 参数 | CKKS（merged） | ESAFL EP |
|---|---|---|
| 底层方案 | CKKS / TenSEAL | ESHE（纯 Python） |
| 多项式维度 | `poly_modulus_degree = 8192` | `n = 4096` |
| slot 数 / 密文 | 4096（= poly/2） | n=4096 个系数 × T−1=2 个数据 slot |
| 模数 | `coeff_mod_bit_sizes = [60,40,40,60]`，链总长 200 bit | `Q = q1·q2 ≈ 2^60`（两个 NTT 素数 CRT） |
| 明文模数 | 无（明文是浮点） | `p = 2^logp = 2^50` |
| scale | `global_scale = 2^40` | **无 scale**；量化 `scale = quant_clip/511` 全客户端共享 |
| 量化位宽 | 可选（`esafl` 策略下 `quant_bits=10`） | **必须**，`logq0 = 10`（u ∈ [0,1023]） |
| 每值占用位宽 | 浮点 53 bit（隐式） | logq0+pad = 16 bit（含 6 bit pad） |
| 每系数打包值数 | `slots2 = 2`（ESAFLPacking 位域时） | `T−1 = 2`（T=3） |
| 噪声参数 | 由 TenSEAL 内部管理，噪声预算 ≈ 模数链 | η=4 中心二项分布；密钥 `{-1,0,1}^n` |
| 聚合误差 | scale 相乘需重缩放；噪声随乘法增长 | **加法是精确的**，仅受 `N·2^logq0 < 2^(logq0+pad)` 约束 |
| 密文结构 | `(c0, c1)` 两多项式 | 单多项式 + mask |
| 每值密文大小（估算） | 8192 系数×2×200 bit ≈ 400 KB/密文 → ≈ **50 B/值** | 4096×60 bit ≈ 30 KB/密文 → ≈ **3.8 B/值**（mask 只服务器持有） |
| 同态能力 | 加、减、乘、标量乘（丰富） | **仅加减**（加权在解密后明文域做） |
| 全参与约束 | 无 | 论文要求未采样客户端上传 Enc(0)；本项目由服务器 mask 机制等价处理 |

---

## 5. 关键区别总结

1. **数值语义**：CKKS 是"浮点 SIMD"——slot 里装的就是浮点数，靠 `global_scale=2^40`
   管理精度；EP 是"定点整数位域"——值必须先量化成 10-bit 整数，
   多个整数 bit-shift 拼进一个大整数的不同位段（slot），靠 pad 位保证
   同态加法不串位。
2. **密文结构**：CKKS 密文是 `(c0, c1)` 多项式对；EP/ESHE 密文是**单个**
   多项式 `a^t·s_i + p·e + m`，公共随机性 `a^t` 由种子本地再生不传输，
   因此单值密文体积小一个数量级（≈3.8 B/值 vs ≈50 B/值）。
3. **scale/噪声管理 vs 精确整数加法**：CKKS 乘法使 scale 相乘、消耗模数链，
   需重线性化/重缩放，且结果是近似的；EP 聚合只做整数加法，
   **精确、无 scale 增长、无模数链消耗**，解密时 mod p 一步精确消噪。
4. **同态能力不对等**：CKKS 支持完整算数（可加可加权平均在密文域完成）；
   ESHE 只有加法同态，FedAvg 的 ÷N 权重只能在解密后明文域施加。
5. **EP 的约束**：所有客户端必须共享同一 `quant_clip`（固定 scale），
   否则密文求和无意义；pad 随客户端数 N 增长（`⌈log2 N⌉+1`），
   N 越大每系数能装的数据 slot 越少（T 变小）；
   且存在全参与约束（未参与者须补 Enc(0) 或由可信方等价处理）。

---

## 6. 数值示例：同一组梯度值 `[0.7321, 0.1145]`

设量化 `quant_clip = 1.0`（EP 与 ESAFLPacking 共用），`logq0 = 10`，
`max_q = 511`，`scale = 1.0/511 ≈ 0.001957`。

**量化（两条路径共用第一步）**：
- `0.7321 / scale ≈ 374.1 → q = 374`，无符号 `u = 374 + 511 = 885`
- `0.1145 / scale ≈ 58.5 → q = 59`（四舍五入），无符号 `u = 59 + 511 = 570`

### CKKS（merged）路径

1. chunk = `[0.7321, 0.1145, 0, ..., 0]`（4096 维，补零）。
2. 编码：每个值乘以 `global_scale = 2^40 ≈ 1.1e12` 取整后嵌入 slot——
   slot_0 ≈ `0.7321 × 2^40 ≈ 8.05×10^11`，slot_1 ≈ `1.26×10^11`。
3. 加密：得到 `(c0, c1)` 多项式对，模数链 200 bit，密文 ≈ 400 KB。
4. 聚合：与其他客户端密文逐 slot 相加（若为 `esafl` 策略，
   则先 bit-shift 拼成 `β = 885·2^16 + 570 = 0x0375023A` 再编码）。
5. 解密：`s` 解出 slot 浮点值 ≈ `[0.7319…, 0.1144…]`——
   **有 10^-4 量级误差**。

### ESAFL EP 路径（logp=50, logq0=10, N=25 → pad=6, T=3）

1. 量化同上：`u = [885, 570]`。
2. EP.EcdPack：`slot_bits = 16`，第 1 个数据 slot 在 bit 32、
   第 2 个在 bit 16、最高 slot（bit 48..63 段，容量 2^16 内）为 0：
   `β = 885·2^32 + 570·2^16 + 0 = 0x0375023A0000`（< p = 2^50 ✓）。
   每个系数装 2 个值；4096 个系数装 8192 个值。
3. ESHE 加密：`ct = [a^t·s_i + 2^50·e + β]_Q`，Q ≈ 2^60，
   单多项式密文 ≈ 30 KB。
4. 聚合（25 个客户端）：`C = Σ ct_i`；每个 slot 内为整数和，
   如 slot_1 内为 `Σu ∈ [25·0, 25·1023]`，远小于 2^16，不串位。
5. 解密：先 mod Q 再 mod p，`2^50·Σe` 被精确消去，得 `Σβ`。
   位域拆 slot：slot_1 和 `= 25 × 885 = 22125`；
   减偏移 `N·max_q = 25×511 = 12775` → 9350；除以 N=25 → 374；
   反量化 `374 × scale ≈ 0.7319`。
   结果与 CKKS 路径**同一量化精度**，但聚合过程零误差——
   唯一误差来自量化本身。
