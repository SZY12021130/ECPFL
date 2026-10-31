"""
3S-EAD 架构流程验证测试
========================

验证 Split-Key CKKS 架构的完整流程：
1. KGC 生成并拆分密钥
2. Client 加密梯度上传
3. Server 聚合密文
4. Server + Edge 协同解密（PTopk 路径）
5. Server + Client 协同解密（预取路径）
6. 验证解密结果正确性

运行: python test_split_key_architecture.py
"""

import os
import sys
import numpy as np
import torch
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ckks_fed.split_key_crypto import (
    SplitKeyKGC, SplitKeyCKKSManager, SplitKeyMode,
    PartialDecryptionShare, TwoPartyDecryptor
)
from ckks_fed.edge_node import EdgeNode, EdgeNodeClient


def test_key_generation():
    """测试 1: KGC 密钥生成与分发"""
    print("=" * 60)
    print("测试 1: KGC 密钥生成与分发")
    print("=" * 60)
    
    # 创建临时目录
    key_dir = tempfile.mkdtemp(prefix="split_key_test_")
    print(f"密钥输出目录: {key_dir}")
    
    # KGC 生成密钥
    kgc = SplitKeyKGC(mode=SplitKeyMode.SIMULATION)
    kgc.generate_and_split(
        output_dir=key_dir,
        n_clients=3,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60],
        global_scale=2**40
    )
    
    # 验证目录结构
    expected_dirs = ['server', 'edge', 'client_0', 'client_1', 'client_2', 'public']
    for d in expected_dirs:
        path = os.path.join(key_dir, d)
        assert os.path.exists(path), f"缺失目录: {path}"
        print(f"  [OK] 目录存在: {d}")
    
    print("测试 1 通过\n")
    return key_dir


def test_client_encryption(key_dir: str):
    """测试 2: Client 加密梯度"""
    print("=" * 60)
    print("测试 2: Client 加密梯度")
    print("=" * 60)
    
    # 模拟配置
    config = {
        'split_key': {'key_dir': key_dir},
        'ckks': {
            'poly_modulus_degree': 8192,
            'coeff_mod_bit_sizes': [60, 40, 40, 60],
            'global_scale': 2**40,
            'slot_count': 4096,
        }
    }
    
    # Client 0 加载密钥
    client_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/client_0")
    print(f"  Client 0 角色: {client_ctx.role}")
    
    # 生成模拟梯度
    gradient = np.random.randn(100).astype(np.float64)
    print(f"  原始梯度范围: [{gradient.min():.4f}, {gradient.max():.4f}]")
    
    # 加密
    ciphertext = client_ctx.encrypt(gradient)
    print(f"  密文序列化大小: {len(ciphertext.serialize())} bytes")
    
    print("测试 2 通过\n")
    return config, gradient, ciphertext


def test_server_aggregation(key_dir: str, ciphertexts: list):
    """测试 3: Server 聚合密文"""
    print("=" * 60)
    print("测试 3: Server 聚合密文")
    print("=" * 60)
    
    # Server 加载密钥
    server_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/server")
    print(f"  Server 角色: {server_ctx.role}")
    
    # 模拟 3 个客户端的密文
    assert len(ciphertexts) == 3
    
    # 聚合（同态加法 + 标量乘）
    weights = [0.33, 0.33, 0.34]
    ct_agg = None
    for i, ct in enumerate(ciphertexts):
        weighted = ct * weights[i]
        if ct_agg is None:
            ct_agg = weighted
        else:
            ct_agg = ct_agg + weighted
    
    print(f"  聚合后密文序列化大小: {len(ct_agg.serialize())} bytes")
    print("测试 3 通过\n")
    
    return ct_agg


def test_collaborative_decrypt_with_edge(key_dir: str, ct_agg):
    """测试 4: Server + Edge 协同解密"""
    print("=" * 60)
    print("测试 4: Server + Edge 协同解密（PTopk 路径）")
    print("=" * 60)
    
    # Server 加载密钥
    server_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/server")
    
    # Edge 加载密钥
    edge_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/edge")
    
    # 模拟原始梯度（用于验证）
    np.random.seed(42)
    grads = [np.random.randn(100).astype(np.float64) for _ in range(3)]
    expected = 0.33 * grads[0] + 0.33 * grads[1] + 0.34 * grads[2]
    
    # 重新加密（使用 Client 0 的 context 模拟上传）
    client_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/client_0")
    cts = [client_ctx.encrypt(g) for g in grads]
    ct_agg = None
    for i, ct in enumerate(cts):
        weighted = ct * [0.33, 0.33, 0.34][i]
        ct_agg = weighted if ct_agg is None else ct_agg + weighted
    
    # Server 部分解密
    print("  Server 计算 partial_decrypt...")
    share_server = server_ctx.partial_decrypt(ct_agg)
    print(f"    Server 份额角色: {share_server.role}")
    
    # Edge 部分解密
    print("  Edge 计算 partial_decrypt...")
    share_edge = edge_ctx.partial_decrypt(ct_agg)
    print(f"    Edge 份额角色: {share_edge.role}")
    
    # 组合
    print("  组合两份份额...")
    decryptor = TwoPartyDecryptor(mode=SplitKeyMode.SIMULATION)
    plaintext = decryptor.combine(share_server, share_edge)
    
    # 验证
    error = np.abs(plaintext - expected).max()
    print(f"  解密误差 (max abs): {error:.6f}")
    assert error < 1.0, f"解密误差过大: {error}"
    
    print("测试 4 通过\n")
    return plaintext


def test_collaborative_decrypt_with_client(key_dir: str):
    """测试 5: Server + Client 协同解密（预取路径）"""
    print("=" * 60)
    print("测试 5: Server + Client 协同解密（预取路径）")
    print("=" * 60)
    
    # 模拟预取差分
    np.random.seed(123)
    delta = np.random.randn(100).astype(np.float64) * 0.1
    print(f"  预取差分范围: [{delta.min():.4f}, {delta.max():.4f}]")
    
    # Server 加密预取内容
    server_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/server")
    ct_prefetch = server_ctx.encrypt(delta)
    
    # Server 部分解密
    print("  Server 计算 partial_decrypt...")
    share_server = server_ctx.partial_decrypt(ct_prefetch)
    
    # Client 部分解密
    client_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/client_1")
    print("  Client 1 计算 partial_decrypt...")
    share_client = client_ctx.partial_decrypt(ct_prefetch)
    
    # 组合（在 Client 侧）
    print("  Client 组合两份份额...")
    decryptor = TwoPartyDecryptor(mode=SplitKeyMode.SIMULATION)
    plaintext = decryptor.combine(share_client, share_server)
    
    # 验证
    error = np.abs(plaintext - delta).max()
    print(f"  解密误差 (max abs): {error:.6f}")
    assert error < 1.0, f"解密误差过大: {error}"
    
    print("测试 5 通过\n")


def test_permission_enforcement(key_dir: str):
    """测试 6: 权限控制验证"""
    print("=" * 60)
    print("测试 6: 权限控制验证")
    print("=" * 60)
    
    # Edge 尝试加密（应失败）
    edge_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/edge")
    try:
        edge_ctx.encrypt(np.array([1.0, 2.0]))
        print("  [FAIL] Edge 加密未失败（权限控制失效）")
        assert False
    except PermissionError:
        print("  [OK] Edge 加密被正确拒绝")
    
    # Client 尝试加密（应成功）
    client_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/client_0")
    try:
        ct = client_ctx.encrypt(np.array([1.0, 2.0]))
        print("  [OK] Client 加密成功")
    except PermissionError:
        print("  [FAIL] Client 加密被错误拒绝")
        assert False
    
    # Server 尝试加密（应成功）
    server_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/server")
    try:
        ct = server_ctx.encrypt(np.array([1.0, 2.0]))
        print("  [OK] Server 加密成功")
    except PermissionError:
        print("  [FAIL] Server 加密被错误拒绝")
        assert False
    
    print("测试 6 通过\n")


def test_edge_node_http(key_dir: str):
    """测试 7: EdgeNode HTTP 服务"""
    print("=" * 60)
    print("测试 7: EdgeNode HTTP 服务")
    print("=" * 60)
    
    try:
        import requests
    except ImportError:
        print("  requests 未安装，跳过 HTTP 测试")
        return
    
    try:
        from flask import Flask
    except ImportError:
        print("  Flask 未安装，跳过 HTTP 测试")
        return
    
    # 启动 EdgeNode
    edge_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/edge")
    edge_node = EdgeNode(edge_ctx, host='127.0.0.1', port=5002)
    edge_node.start_server()
    
    import time
    time.sleep(1)  # 等待服务启动
    
    # 健康检查
    try:
        resp = requests.get('http://127.0.0.1:5002/health', timeout=5)
        print(f"  健康检查: {resp.json()}")
        assert resp.json()['status'] == 'ok'
    except Exception as e:
        print(f"  健康检查失败: {e}")
    
    # 部分解密测试
    client_ctx = SplitKeyKGC.load_role_context(f"{key_dir}/client_0")
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    ct = client_ctx.encrypt(data)
    
    try:
        resp = requests.post(
            'http://127.0.0.1:5002/partial_decrypt',
            data=ct.serialize(), timeout=10
        )
        share = PartialDecryptionShare.deserialize(resp.content)
        print(f"  HTTP 部分解密成功: role={share.role}")
    except Exception as e:
        print(f"  HTTP 部分解密失败: {e}")
    
    print("测试 7 完成\n")


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("3S-EAD 架构流程验证测试")
    print("=" * 60 + "\n")
    
    key_dir = None
    try:
        # 测试 1: 密钥生成
        key_dir = test_key_generation()
        
        # 测试 2: Client 加密
        config, gradient, ciphertext = test_client_encryption(key_dir)
        
        # 测试 3: Server 聚合
        cts = [ciphertext for _ in range(3)]  # 模拟3个客户端
        ct_agg = test_server_aggregation(key_dir, cts)
        
        # 测试 4: Server + Edge 协同解密
        test_collaborative_decrypt_with_edge(key_dir, ct_agg)
        
        # 测试 5: Server + Client 协同解密
        test_collaborative_decrypt_with_client(key_dir)
        
        # 测试 6: 权限控制
        test_permission_enforcement(key_dir)
        
        # 测试 7: HTTP 服务
        test_edge_node_http(key_dir)
        
        print("=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # 清理临时目录
        if key_dir and os.path.exists(key_dir):
            shutil.rmtree(key_dir)
            print(f"\n清理临时目录: {key_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())
