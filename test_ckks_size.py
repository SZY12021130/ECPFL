"""
CKKS 密文大小验证实验
验证：同态加法和标量乘法后，密文大小是否变化
"""
import torch
import numpy as np
import sys
sys.path.insert(0, '.')

from ckks_fed.crypto import CKKSManager
from ckks_fed.models import create_model
import yaml

def fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def main():
    # 加载配置
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    ckks_config = config['ckks']
    print(f"CKKS 配置: N={ckks_config['poly_modulus_degree']}, "
          f"scale=2^{ckks_config['global_scale'].bit_length()-1}, "
          f"mod={ckks_config['coeff_mod_bit_sizes']}")

    ckks = CKKSManager(ckks_config)

    # 创建模型
    model = create_model(config['model']['name'], config)
    print(f"\n模型: {config['model']['name']}")
    print(f"参数量: {sum(p.numel() for p in model.parameters())}")

    # 获取模型参数
    params = {name: param.data.clone() for name, param in model.named_parameters()}
    plaintext_size = sum(p.numel() * 4 for p in params.values())
    print(f"明文大小: {fmt_size(plaintext_size)}")

    # === 实验1: 单客户端加密 ===
    print("\n" + "=" * 60)
    print("实验1: 单客户端加密")
    print("=" * 60)

    enc1 = ckks.encrypt_model_update(params)
    size1 = ckks.compute_encrypted_update_size(enc1)
    print(f"客户端1 密文大小: {fmt_size(size1)}")

    # === 实验2: 10个客户端分别加密 ===
    print("\n" + "=" * 60)
    print("实验2: 10个客户端分别加密（相同参数内容）")
    print("=" * 60)

    sizes = []
    enc_list = []
    for i in range(10):
        # 故意用不同的数值（加小噪声）来模拟不同客户端
        noisy_params = {name: p + torch.randn_like(p) * 0.001 for name, p in params.items()}
        enc = ckks.encrypt_model_update(noisy_params)
        sz = ckks.compute_encrypted_update_size(enc)
        sizes.append(sz)
        enc_list.append(enc)
        print(f"  客户端{i} 密文大小: {fmt_size(sz)}")

    print(f"\n10个客户端密文大小: min={fmt_size(min(sizes))}, max={fmt_size(max(sizes))}, "
          f"avg={fmt_size(sum(sizes)//len(sizes))}")

    # === 实验3: 同态聚合（加权平均）===
    print("\n" + "=" * 60)
    print("实验3: 10个密文同态聚合（加权平均）")
    print("=" * 60)

    weights = [1.0 / 10.0] * 10
    agg_enc = ckks.aggregate_encrypted_updates(enc_list, weights)
    agg_size = ckks.compute_encrypted_update_size(agg_enc)
    print(f"聚合后密文大小: {fmt_size(agg_size)}")
    print(f"与单个密文大小对比: {agg_size} vs {sizes[0]} → "
          f"{'相同' if agg_size == sizes[0] else f'差异 {abs(agg_size - sizes[0])} bytes'}")

    # === 实验4: 密文加法（不 scalar multiply）===
    print("\n" + "=" * 60)
    print("实验4: 两个密文直接相加（不加权）")
    print("=" * 60)

    evaluator = ckks.evaluator
    add_result = {}
    for name in enc_list[0]:
        add_result[name] = []
        for i in range(len(enc_list[0][name])):
            ct_sum = evaluator.add(enc_list[0][name][i], enc_list[1][name][i])
            add_result[name].append(ct_sum)

    add_size = ckks.compute_encrypted_update_size(add_result)
    print(f"加法后密文大小: {fmt_size(add_size)}")
    print(f"与原始密文大小对比: {add_size} vs {sizes[0]} → "
          f"{'相同' if add_size == sizes[0] else f'差异 {abs(add_size - sizes[0])} bytes'}")

    # === 实验5: 标量乘法后 ===
    print("\n" + "=" * 60)
    print("实验5: 密文 × 标量 (0.1)")
    print("=" * 60)

    mul_result = {}
    for name in enc_list[0]:
        mul_result[name] = []
        for i in range(len(enc_list[0][name])):
            ct_mul = evaluator.multiply_scalar(enc_list[0][name][i], 0.1)
            mul_result[name].append(ct_mul)

    mul_size = ckks.compute_encrypted_update_size(mul_result)
    print(f"标量乘后密文大小: {fmt_size(mul_size)}")
    print(f"与原始密文大小对比: {mul_size} vs {sizes[0]} → "
          f"{'相同' if mul_size == sizes[0] else f'差异 {abs(mul_size - sizes[0])} bytes'}")

    # === 实验6: 加权平均中的 multiply_scalar + add ===
    print("\n" + "=" * 60)
    print("实验6: 逐步模拟 weighted_average (multiply_scalar + add)")
    print("=" * 60)

    step_result = {}
    for name in enc_list[0]:
        step_result[name] = []
        for i in range(len(enc_list[0][name])):
            r = evaluator.multiply_scalar(enc_list[0][name][i], weights[0])
            for j in range(1, 3):  # 只加前3个
                w = evaluator.multiply_scalar(enc_list[j][name][i], weights[j])
                r = evaluator.add(r, w)
            step_result[name].append(r)

    step_size = ckks.compute_encrypted_update_size(step_result)
    print(f"加权累加后密文大小: {fmt_size(step_size)}")
    print(f"与原始密文大小对比: {step_size} vs {sizes[0]} → "
          f"{'相同' if step_size == sizes[0] else f'差异 {abs(step_size - sizes[0])} bytes'}")

    # === 实验7: 多次累加后的 global state ===
    print("\n" + "=" * 60)
    print("实验7: 模拟 global state 多次 += delta")
    print("=" * 60)

    # 初始全局模型
    global_enc = ckks.encrypt_model_update(params)
    global_size = ckks.compute_encrypted_update_size(global_enc)
    print(f"初始 global state 大小: {fmt_size(global_size)}")

    # 累加 5 次 delta
    for step in range(5):
        delta_params = {name: torch.randn_like(p) * 0.001 for name, p in params.items()}
        delta_enc = ckks.encrypt_model_update(delta_params)
        for name in global_enc:
            for i in range(len(global_enc[name])):
                global_enc[name][i] = evaluator.add(global_enc[name][i], delta_enc[name][i])
        new_size = ckks.compute_encrypted_update_size(global_enc)
        print(f"  累加 delta {step+1} 后大小: {fmt_size(new_size)} "
              f"({'相同' if new_size == global_size else f'变化 {abs(new_size - global_size)} bytes'})")
        global_size = new_size

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print("CKKS 同态加法不增加密文大小，标量乘法也不增加密文大小。")
    print("10 个人聚合后的密文大小 = 单个人的密文大小。")
    print("多次累加 global state 后，密文大小保持不变。")

if __name__ == "__main__":
    main()
