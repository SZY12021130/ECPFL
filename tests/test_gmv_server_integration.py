"""
集成测试：验证 server.run_global_mask_vote 的边界对齐。
模拟完整的投票流程，确认 num_batches 和 batch_size 与 packing 策略一致。
"""
import sys
sys.path.insert(0, r'E:\GithubProjects\ckks_fed_robustness')

import torch
import numpy as np
from unittest.mock import MagicMock

from ckks_fed.server import AggregationServer
from ckks_fed.packing import CRTStackPacking, MergedPacking


class DummyClient:
    def __init__(self, cid):
        self.client_id = cid
        self.model = MagicMock()


def make_lenet_update():
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


def test_server_gmv_with_crtstack():
    """测试 CRTStack 场景下 server.run_global_mask_vote 的 num_batches 计算"""
    
    # 构造 mock model
    class MockModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = torch.nn.Conv2d(1, 6, 5)
            self.conv2 = torch.nn.Conv2d(6, 16, 5)
            self.fc1 = torch.nn.Linear(256, 120)
            self.fc2 = torch.nn.Linear(120, 84)
            self.fc3 = torch.nn.Linear(84, 10)
    
    model = MockModel()
    
    config = {
        'global_mask_vote': {
            'mode': 'union',
            'threshold_pct': 0.2,
            'topk_k': 5,
            'sparsity_rate': 0.3,
            'scoring_method': 'avg_abs',
        },
        'ckks': {
            'poly_modulus_degree': 8192,
            'coeff_mod_bit_sizes': [40, 20, 40],
            'global_scale': 2**20,
            'slot_packing': True,
            'packing': {
                'strategy': 'crtstack',
                'crt_layers': 4,
                'crt_quant_bits': 8,
            },
            'sparsification': {
                'strategy': 'none',
                'sparsity_rate': 0.1,
                'scoring_method': 'l2_norm',
            },
        },
        'system': {'upload_difference': True},
        'defense': {'aggregation_rule': 'fedavg'},
        'tee': {'enabled': False},
    }
    
    # 构造 mock CKKSManager
    ckks_manager = MagicMock()
    ckks_manager.batch_size = 4096
    
    # 使用真实的 CRTStackPacking
    packing = CRTStackPacking(4096, layers=4, quant_bits=8)
    ckks_manager.packing_strategy = packing
    
    # 构造 server
    server = AggregationServer(model, config, device='cpu', ckks_manager=ckks_manager)
    
    # 构造客户端和更新
    clients = [DummyClient(i) for i in range(5)]
    selected_clients = clients[:3]
    selected_updates = [make_lenet_update() for _ in range(3)]
    
    # 初始化 encrypted_global_state（模拟）
    chunks, metadata = packing.pack(make_lenet_update())
    server.encrypted_global_state = {
        '__sparse__': True,
        'ciphertexts': [],
        'mask': [1] * len(chunks),
        'batch_size': 4096,
        'total_elements': metadata.data['total_elements'],
        'shapes': metadata.data['shapes'],
        'offsets': metadata.data['offsets'],
        'packing_metadata': metadata.data,
    }
    
    # 运行投票
    global_mask = server.run_global_mask_vote(
        all_clients=clients,
        selected_clients=selected_clients,
        selected_updates=selected_updates,
        round_num=0,
        ckks_manager=ckks_manager,
    )
    
    # 验证
    total_params = sum(p.numel() for p in model.parameters())
    values_per_chunk = packing.get_values_per_chunk()  # 16384
    expected_batches = (total_params + values_per_chunk - 1) // values_per_chunk  # 3
    
    print(f"[CRTStack Server Integration]")
    print(f"  total_params={total_params}, values_per_chunk={values_per_chunk}")
    print(f"  packing_chunks={len(chunks)}, expected_batches={expected_batches}")
    print(f"  global_mask_len={len(global_mask)}, active={global_mask.sum()}")
    
    assert len(global_mask) == len(chunks), \
        f"mask_len({len(global_mask)}) != packing_chunks({len(chunks)})"
    assert len(global_mask) == expected_batches, \
        f"mask_len({len(global_mask)}) != expected_batches({expected_batches})"
    
    print("  PASS: server GMV 边界对齐\n")


def test_server_gmv_with_merged():
    """测试 Merged 场景下 server.run_global_mask_vote 的 num_batches 计算"""
    
    class MockModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = torch.nn.Conv2d(1, 6, 5)
            self.conv2 = torch.nn.Conv2d(6, 16, 5)
            self.fc1 = torch.nn.Linear(256, 120)
            self.fc2 = torch.nn.Linear(120, 84)
            self.fc3 = torch.nn.Linear(84, 10)
    
    model = MockModel()
    
    config = {
        'global_mask_vote': {
            'mode': 'union',
            'sparsity_rate': 0.3,
            'scoring_method': 'avg_abs',
        },
        'ckks': {'sparsification': {'strategy': 'none'}},
        'system': {'upload_difference': True},
        'defense': {'aggregation_rule': 'fedavg'},
        'tee': {'enabled': False},
    }
    
    ckks_manager = MagicMock()
    ckks_manager.batch_size = 4096
    
    packing = MergedPacking(4096)
    ckks_manager.packing_strategy = packing
    
    server = AggregationServer(model, config, device='cpu', ckks_manager=ckks_manager)
    
    clients = [DummyClient(i) for i in range(5)]
    selected_clients = clients[:3]
    selected_updates = [make_lenet_update() for _ in range(3)]
    
    chunks, metadata = packing.pack(make_lenet_update())
    server.encrypted_global_state = {
        '__sparse__': True,
        'ciphertexts': [],
        'mask': [1] * len(chunks),
        'batch_size': 4096,
        'total_elements': metadata.data['total_elements'],
        'shapes': metadata.data['shapes'],
        'offsets': metadata.data['offsets'],
    }
    
    global_mask = server.run_global_mask_vote(
        all_clients=clients,
        selected_clients=selected_clients,
        selected_updates=selected_updates,
        round_num=0,
        ckks_manager=ckks_manager,
    )
    
    total_params = sum(p.numel() for p in model.parameters())
    values_per_chunk = packing.get_values_per_chunk()  # 4096
    expected_batches = (total_params + values_per_chunk - 1) // values_per_chunk  # 11
    
    print(f"[Merged Server Integration]")
    print(f"  total_params={total_params}, values_per_chunk={values_per_chunk}")
    print(f"  packing_chunks={len(chunks)}, expected_batches={expected_batches}")
    print(f"  global_mask_len={len(global_mask)}, active={global_mask.sum()}")
    
    assert len(global_mask) == len(chunks), \
        f"mask_len({len(global_mask)}) != packing_chunks({len(chunks)})"
    assert len(global_mask) == expected_batches, \
        f"mask_len({len(global_mask)}) != expected_batches({expected_batches})"
    
    print("  PASS: server GMV 边界对齐\n")


if __name__ == '__main__':
    test_server_gmv_with_crtstack()
    test_server_gmv_with_merged()
    print("=" * 60)
    print("All server integration tests passed!")
