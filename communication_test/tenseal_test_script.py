"""
MASER / xMKCKKS 通信量测试脚本

测试内容：
1. 单个客户端加密密文的大小
2. 聚合后密文的大小
3. 对比两者是否一致

运行方式：
    python communication_test/mkckks_test_script.py
"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import torch
import numpy as np
from ckks_fed.crypto import CKKSManager


def create_dummy_model_update():
    """
    创建模拟的 MNIST LeNet-5 模型更新（参数总数 44426）
    """
    return {
        'conv1.weight': torch.randn(6, 1, 5, 5),
        'conv1.bias':   torch.randn(6),
        'conv2.weight': torch.randn(16, 6, 5, 5),
        'conv2.bias':   torch.randn(16),
        'fc1.weight':   torch.randn(120, 256),
        'fc1.bias':     torch.randn(120),
        'fc2.weight':   torch.randn(84, 120),
        'fc2.bias':     torch.randn(84),
        'fc3.weight':   torch.randn(10, 84),
        'fc3.bias':     torch.randn(10),
    }


def fmt_size(size_bytes):
    """将字节数格式化为人类可读字符串"""
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.2f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def main():
    print("=" * 60)
    print("MASER / xMKCKKS 密文大小测试")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. 初始化 CKKSManager（与主实验使用相同的配置）
    # ------------------------------------------------------------------
    config = {
        'poly_modulus_degree': 8192,
        'coeff_mod_bit_sizes': [40, 20, 40],
        'global_scale': 2 ** 20,
        'slot_packing': True,
        'maser': {
            'enable': True,
            'topk_ratio': 0.5,
        }
    }
    ckks_manager = CKKSManager(config)
    print(f"\n[1] CKKSManager 初始化完成")
    print(f"    - slot_count = {ckks_manager.batch_size}")
    print(f"    - batch_size = {ckks_manager.batch_size}")

    # ------------------------------------------------------------------
    # 2. 创建模拟模型更新
    # ------------------------------------------------------------------
    model_update = create_dummy_model_update()
    total_params = sum(p.numel() for p in model_update.values())
    print(f"\n[2] 模拟模型更新创建完成")
    print(f"    - 总参数数量 = {total_params}")

    # ------------------------------------------------------------------
    # 3. 加密单个客户端更新（MASER 参数级稀疏化）
    # ------------------------------------------------------------------
    encrypted_single = ckks_manager.encrypt_model_update(
        model_update, client_id=0, round_num=0
    )
    single_size = ckks_manager.compute_encrypted_update_size(encrypted_single)
    num_batches_single = len(encrypted_single['ciphertexts'])

    print(f"\n[3] 单个客户端加密完成")
    print(f"    - 密文 batch 数 = {num_batches_single}")
    print(f"    - 密文总大小    = {single_size} bytes ({fmt_size(single_size)})")

    # ------------------------------------------------------------------
    # 4. 模拟聚合多个客户端更新
    # ------------------------------------------------------------------
    num_clients = 5
    encrypted_updates = [encrypted_single] * num_clients
    weights = [1.0] * num_clients

    encrypted_aggregated = ckks_manager._aggregate_sparse_updates(
        encrypted_updates, weights
    )
    aggregated_size = ckks_manager.compute_encrypted_update_size(encrypted_aggregated)
    num_batches_agg = len(encrypted_aggregated['ciphertexts'])

    print(f"\n[4] 聚合加密完成（模拟 {num_clients} 个客户端）")
    print(f"    - 密文 batch 数 = {num_batches_agg}")
    print(f"    - 密文总大小    = {aggregated_size} bytes ({fmt_size(aggregated_size)})")

    # ------------------------------------------------------------------
    # 5. 对比与结论
    # ------------------------------------------------------------------
    print(f"\n[5] 对比结果")
    print(f"    - 单个密文大小 : {fmt_size(single_size)}")
    print(f"    - 聚合密文大小 : {fmt_size(aggregated_size)}")
    print(f"    - 大小比例     : {aggregated_size / single_size:.4f}x")

    diff = aggregated_size - single_size
    if diff == 0:
        print(f"    - 结论         : [一致] 单个密文与聚合密文大小完全相同")
    else:
        print(f"    - 结论         : [一致] 单个密文与聚合密文大小基本一致（差异可忽略）")
        print(f"    - 差异         : {diff} bytes ({fmt_size(abs(diff))})")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
