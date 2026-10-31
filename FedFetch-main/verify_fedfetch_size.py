"""
验证 FedFetch 中 delta 大小与完整模型大小的关系
对比明文 FedAvg 和 CKKS+FedAvg 两种情况
"""

import pickle
import sys
import numpy as np
import torch
import torch.nn as nn

# ============================================================
# Part 1: 明文 FedAvg 验证
# ============================================================

print("=" * 70)
print("Part 1: 明文 FedAvg - 模型与 Delta 大小对比")
print("=" * 70)


def get_size(obj):
    """获取对象 pickle 序列化后的字节数"""
    return len(pickle.dumps(obj))


# 创建一个简单的神经网络
class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 10)

    def forward(self, x):
        return self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(x)))))


model = SimpleModel()

# 模拟多轮 FedAvg 聚合
rounds = 5
models = []          # 每轮聚合后的全局模型
deltas = []          # 每轮的 delta: W_{t+1} - W_t

# 初始模型 W_0
w_curr = {k: v.detach().clone() for k, v in model.state_dict().items()}
models.append(w_curr)

# 模拟 R 轮聚合（随机生成一些更新）
for r in range(rounds):
    # 模拟聚合后的新模型: W_{t+1} = W_t + random_update
    w_next = {}
    for k, v in w_curr.items():
        # 模拟一个很小的但非零的更新（稠密更新）
        update = torch.randn_like(v) * 0.01
        w_next[k] = v + update
    
    # 计算 delta_t = W_{t+1} - W_t
    delta_t = {k: w_next[k] - w_curr[k] for k in w_curr}
    deltas.append(delta_t)
    
    models.append(w_next)
    w_curr = w_next

# 获取各轮模型和 delta 的大小
model_sizes = [get_size(m) for m in models]
delta_sizes = [get_size(d) for d in deltas]

print(f"\n[1.1] 单轮模型与 Delta 大小对比")
print(f"{'Round':<8} {'|W_t| (bytes)':<18} {'|Δ_t| (bytes)':<18} {'Ratio |Δ|/|W|'}")
print("-" * 65)
for i in range(1, rounds + 1):
    ratio = delta_sizes[i-1] / model_sizes[i]
    print(f"{i:<8} {model_sizes[i]:<18} {delta_sizes[i-1]:<18} {ratio:.4f}")

print(f"\n结论: 无压缩时，单轮 delta 大小 ≈ 完整模型大小 (ratio ≈ 1.0)")

# 多轮 delta 张量累加 vs 独立序列化累加
print(f"\n[1.2] 多轮 Delta 累积大小对比 (从 W_0 到 W_{rounds})")

# 方法 A: 先把所有 delta 张量累加，再序列化
cum_delta_tensors = {}
for k in models[0]:
    cum_delta_tensors[k] = sum(d[k] for d in deltas)

# 验证: W_0 + sum(delta) == W_R
reconstructed = {k: models[0][k] + cum_delta_tensors[k] for k in models[0]}
match = all(torch.allclose(reconstructed[k], models[-1][k]) for k in models[0])
print(f"  W_0 + ΣΔ_t == W_{rounds} ? {match} (张量层面等式成立)")

cum_delta_tensor_size = get_size(cum_delta_tensors)
print(f"  |ΣΔ_t (张量累加后再序列化)| = {cum_delta_tensor_size} bytes")
print(f"  |W_{rounds}| = {model_sizes[-1]} bytes")
print(f"  Ratio = {cum_delta_tensor_size / model_sizes[-1]:.4f}")

# 方法 B: 每轮 delta 独立序列化，字节数累加
cum_delta_independent_size = sum(delta_sizes)
print(f"\n  Σ|Δ_t| (每轮独立序列化后累加) = {cum_delta_independent_size} bytes")
print(f"  R * |W| = {rounds} * {model_sizes[-1]} = {rounds * model_sizes[-1]} bytes")
print(f"  Ratio Σ|Δ_t| / |W_R| = {cum_delta_independent_size / model_sizes[-1]:.2f}x")

print(f"\n  关键结论:")
print(f"  - 张量先累加再序列化: 大小 ≈ |W| (1x)")
print(f"  - 每轮独立序列化再累加: 大小 ≈ R * |W| ({rounds}x)")


# ============================================================
# Part 2: CKKS + FedAvg 验证
# ============================================================

print("\n" + "=" * 70)
print("Part 2: CKKS + FedAvg - 密文大小对比")
print("=" * 70)

try:
    import tenseal as ts

    # 创建 CKKS context
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60]
    )
    context.global_scale = 2 ** 40
    context.generate_galois_keys()

    # 模拟一个小的权重向量（CKKS 通常按向量/张量加密）
    # 为了效率，我们取模型中一层的小权重
    sample_weight = models[0]['fc1.weight']  # [256, 784]
    
    # 扁平化并取前 N 个元素（poly_modulus_degree/2 = 4096 slots）
    flat_weight = sample_weight.flatten()[:4096].numpy()
    
    # 加密原始权重
    enc_weight = ts.ckks_vector(context, flat_weight.tolist())
    enc_weight_size = get_size(enc_weight.serialize())
    
    # 加密 delta (W_1 - W_0)
    delta_flat = deltas[0]['fc1.weight'].flatten()[:4096].numpy()
    enc_delta = ts.ckks_vector(context, delta_flat.tolist())
    enc_delta_size = get_size(enc_delta.serialize())
    
    # 加密后的 delta 做加法（模拟累积）
    enc_sum = enc_delta
    for i in range(1, 3):  # 再加密几个 delta 并累加
        d_flat = deltas[i]['fc1.weight'].flatten()[:4096].numpy()
        enc_d = ts.ckks_vector(context, d_flat.tolist())
        enc_sum = enc_sum + enc_d
    enc_sum_size = get_size(enc_sum.serialize())
    
    print(f"\n[2.1] 单条 CKKS 密文大小对比 (poly_modulus_degree=8192, slots=4096)")
    print(f"  明文权重向量大小 ({len(flat_weight)} floats): {get_size(flat_weight)} bytes")
    print(f"  加密后权重 |Enc(W)|: {enc_weight_size} bytes")
    print(f"  加密后 delta |Enc(Δ)|: {enc_delta_size} bytes")
    print(f"  密文膨胀倍数: {enc_weight_size / get_size(flat_weight):.1f}x")
    print(f"  |Enc(Δ)| / |Enc(W)| = {enc_delta_size / enc_weight_size:.4f}")
    print(f"\n  结论: CKKS 密文大小只取决于加密参数，与明文是 W 还是 Δ 无关")
    
    print(f"\n[2.2] CKKS 密文累加后大小")
    print(f"  |Enc(Δ_0)| = {enc_delta_size} bytes")
    print(f"  |Enc(Δ_0 + Δ_1 + Δ_2)| = {enc_sum_size} bytes")
    print(f"  累加后大小变化: {enc_sum_size / enc_delta_size:.4f}")
    print(f"  结论: CKKS 密文加法后大小**基本不变**（仍是1个密文）")
    
    # 模拟多轮独立加密 delta 的总大小
    r = 5
    total_enc_deltas = r * enc_delta_size
    print(f"\n[2.3] 预取 R={r} 轮独立加密 Delta 的总大小")
    print(f"  R * |Enc(Δ)| = {r} * {enc_delta_size} = {total_enc_deltas} bytes")
    print(f"  对比单轮加密模型 |Enc(W)| = {enc_weight_size} bytes")
    print(f"  Ratio = {total_enc_deltas / enc_weight_size:.1f}x")
    print(f"\n  结论: 预取 {r} 轮独立加密的 delta，总密文大小是单轮模型的 {r}x")
    
    # 如果先累加再加密呢？
    sum_flat = sum(d['fc1.weight'].flatten()[:4096].numpy() for d in deltas[:r])
    enc_sum_direct = ts.ckks_vector(context, sum_flat.tolist())
    enc_sum_direct_size = get_size(enc_sum_direct.serialize())
    print(f"\n[2.4] 先累加明文 delta，再一次性加密")
    print(f"  |Enc(ΣΔ_t)| = {enc_sum_direct_size} bytes")
    print(f"  Ratio vs |Enc(W)| = {enc_sum_direct_size / enc_weight_size:.4f}")
    print(f"  结论: 先累加再加密，总大小 ≈ 1x |Enc(W)|")

except ImportError:
    print("tenseal not available, using theoretical estimation for CKKS")
    
    # 理论估算
    plaintext_size = 4096 * 4  # 4096 floats = 16384 bytes
    expansion_factor = 150     # CKKS typical expansion
    enc_size = plaintext_size * expansion_factor
    
    print(f"\n[2.1] 理论估算 CKKS 密文大小 (poly_modulus_degree=8192)")
    print(f"  明文大小: {plaintext_size} bytes")
    print(f"  密文膨胀倍数: ~{expansion_factor}x")
    print(f"  单条密文大小: ~{enc_size} bytes")
    print(f"  结论: 加密后 W 和 Δ 大小相同（密文大小与明文内容无关）")
    
    r = 5
    print(f"\n[2.2] 预取 R={r} 轮独立加密 Delta")
    print(f"  总大小 = {r} * {enc_size} = {r * enc_size} bytes = {r}x 单轮模型密文")
    print(f"  若先累加明文再加密: ~{enc_size} bytes = 1x")


# ============================================================
# Part 3: 对你的问题的直接回答
# ============================================================

print("\n" + "=" * 70)
print("Part 3: 核心结论总结")
print("=" * 70)

print("""
问题: 客户端预取了 Δ_{t+1} ... Δ_{t+R-1}，训练前只需下载 Δ_t。
        Δ_t 的大小是否和 W_{t+R} 一样大？

【明文 FedAvg - 无压缩】
  - Δ_t = W_{t+1} - W_t 是稠密张量
  - |Δ_t|_serialize ≈ |W|_serialize ≈ model_size
  - 训练前下载 Δ_t (model_size)  vs  不预取下载 W_{t+R} (model_size)
  → 两者大小一样！预取没有减少"训练前那一下"的下载量。
  
  但注意:
  - W_{t+R} = W_t + ΣΔ_i  只在张量层面成立
  - 序列化大小层面: |ΣΔ_i (先累加再序列化)| ≈ |W|  (1x)
  - 但 |Δ_0| + |Δ_1| + ... (独立序列化累加) ≈ R * |W|  (Rx)

【CKKS + FedAvg】
  - CKKS 密文大小只取决于加密参数(poly_modulus_degree, coeff_mod_bits)
  - 与明文是 W 还是 Δ 无关
  - |Enc(Δ_t)| ≈ |Enc(W)| ≈ enc_model_size
  
  关键差异:
  - 若每轮 Δ 独立加密、独立传输: 总大小 = R * enc_model_size
  - 若先累加明文再加密: 总大小 ≈ 1 * enc_model_size
  - CKKS 密文加法不增加大小！Enc(a) + Enc(b) 仍是1个密文

【对你的困惑的直接回答】
  Q: 预取了后面的 delta，训练前下载 Δ_t，Δ_t 和 W 一样大？
  A: 是的，无论明文还是 CKKS，单条 Δ_t 都和 W 一样大。
  
  Q: 那预取不就没意义了？
  A: 在"无压缩 + 每轮独立发 delta"的场景下，确实如此。
     预取的意义必须依赖:
     1. 压缩（让 |Δ| << |W|）
     2. 或者"先累加再加密/传输"（让总大小维持 1x）
     
  在 CKKS 下尤其重要:
     - 若 Server 每轮把 Δ 加密后发给客户端，R 轮就是 R 个密文
     - 若 Server 本地先累加 R 轮的明文 delta，再一次性加密发给客户端
       → 总传输量 = 1 个密文大小！
     - 但客户端本地就无法利用"流水线预取"了，必须等 R 轮结束后才能开始下载
""")
