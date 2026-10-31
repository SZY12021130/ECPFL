"""
测试 GlobalMaskVote 和 PackingStrategy 的边界对齐。
验证投票切分大小和加密 chunk 大小完全一致。
"""
import sys
sys.path.insert(0, 'E:\GithubProjects\ckks_fed_robustness')

import torch
import numpy as np
from ckks_fed.packing import MergedPacking, CRTStackPacking
from ckks_fed.global_mask_vote import GlobalMaskVote


def make_lenet_update():
    """构造 LeNet 风格的模型更新（44,426 参数）"""
    return {
        'conv1.weight': torch.randn(6, 1, 5, 5),
        'conv1.bias': torch.randn(6),
        'conv2.weight': torch.randn(16, 6, 5, 5),
        'conv2.bias': torch.randn(16),
        'fc1.weight': torch.randn(120, 256),
        'fc1.bias': torch.randn(120),
        'fc2.weight': torch.randn(84, 120),
        'fc2.bias': torch.randn(84),
        'fc3.weight': torch.randn(10, 84),
        'fc3.bias': torch.randn(10),
    }


def test_merged_alignment():
    """MergedPacking: batch_size = slot_count = 4096"""
    slot_count = 4096
    packing = MergedPacking(slot_count)
    update = make_lenet_update()
    
    # packing 切分
    chunks, metadata = packing.pack(update)
    packing_batches = len(chunks)
    
    # 投票切分
    gmv = GlobalMaskVote(mode="union")
    total_params = sum(p.numel() for p in update.values())
    values_per_chunk = packing.get_values_per_chunk()  # = 4096
    expected_batches = (total_params + values_per_chunk - 1) // values_per_chunk
    
    mask = gmv.client_compute_mask_from_update(
        update, batch_size=values_per_chunk, sparsity_rate=0.3
    )
    
    print(f"[Merged] total_params={total_params}, values_per_chunk={values_per_chunk}")
    print(f"[Merged] packing_batches={packing_batches}, expected_batches={expected_batches}, mask_len={len(mask)}")
    
    assert packing_batches == expected_batches, \
        f"Merged: packing_batches({packing_batches}) != expected_batches({expected_batches})"
    assert len(mask) == packing_batches, \
        f"Merged: mask_len({len(mask)}) != packing_batches({packing_batches})"
    print("[Merged] PASS: 边界对齐\n")


def test_crtstack_alignment():
    """CRTStackPacking: batch_size = slot_count * layers = 16384"""
    slot_count = 4096
    layers = 4
    packing = CRTStackPacking(slot_count, layers=layers, quant_bits=8)
    update = make_lenet_update()
    
    # packing 切分
    chunks, metadata = packing.pack(update)
    packing_batches = len(chunks)
    
    # 投票切分
    gmv = GlobalMaskVote(mode="union")
    total_params = sum(p.numel() for p in update.values())
    values_per_chunk = packing.get_values_per_chunk()  # = 16384
    expected_batches = (total_params + values_per_chunk - 1) // values_per_chunk
    
    mask = gmv.client_compute_mask_from_update(
        update, batch_size=values_per_chunk, sparsity_rate=0.3
    )
    
    print(f"[CRTStack] total_params={total_params}, values_per_chunk={values_per_chunk}")
    print(f"[CRTStack] packing_batches={packing_batches}, expected_batches={expected_batches}, mask_len={len(mask)}")
    
    assert packing_batches == expected_batches, \
        f"CRTStack: packing_batches({packing_batches}) != expected_batches({expected_batches})"
    assert len(mask) == packing_batches, \
        f"CRTStack: mask_len({len(mask)}) != packing_batches({packing_batches})"
    print("[CRTStack] PASS: 边界对齐\n")


def test_old_vs_new_behavior():
    """
    对比旧行为（不对齐）和新行为（对齐）的差异。
    旧行为：total_batches=3, batch_size=4096 → aligned_batch_size=14809
    新行为：batch_size=16384 → 3 batches
    两者 mask 长度都是 3，但每个 mask 位对应的参数范围不同。
    """
    update = make_lenet_update()
    total_params = sum(p.numel() for p in update.values())
    
    # 旧行为模拟
    old_num_batches = 3
    old_batch_size = (total_params + old_num_batches - 1) // old_num_batches  # = 14809
    
    gmv = GlobalMaskVote(mode="union")
    old_mask = gmv.client_compute_mask_from_update(
        update, batch_size=old_batch_size, sparsity_rate=0.3, total_batches=old_num_batches
    )
    
    # 新行为
    packing = CRTStackPacking(4096, layers=4, quant_bits=8)
    new_mask = gmv.client_compute_mask_from_update(
        update, batch_size=packing.get_values_per_chunk(), sparsity_rate=0.3
    )
    
    print(f"[Old vs New] total_params={total_params}")
    print(f"[Old] batch_size={old_batch_size}, mask_len={len(old_mask)}")
    print(f"[New] batch_size={packing.get_values_per_chunk()}, mask_len={len(new_mask)}")
    
    # 旧行为：3 个 batch，每个 14809 → 边界 [14809, 29618]
    # 新行为：3 个 batch，每个 16384 → 边界 [16384, 32768]
    # 这两个边界不同！
    assert old_batch_size != packing.get_values_per_chunk(), \
        "旧 batch_size 应该和新 batch_size 不同，否则测试无意义"
    print("[Old vs New] PASS: 确认旧行为和新行为的切分边界不同\n")


if __name__ == '__main__':
    test_merged_alignment()
    test_crtstack_alignment()
    test_old_vs_new_behavior()
    print("=" * 60)
    print("All GlobalMaskVote alignment tests passed!")
