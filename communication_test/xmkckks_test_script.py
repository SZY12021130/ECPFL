"""
MASER xMKCKKS 密文大小测试脚本

测试内容：
1. 单个客户端加密密文的大小
2. 聚合后密文的大小（验证 xMKCKKS 线性增长特性）
3. 对比两者大小比例

运行方式：
    cd MASER-main
    python ../communication_test/xmkckks_test_script.py
"""

import sys
import os

# 将 MASER-main 目录加入 Python 路径
maser_dir = os.path.join(os.path.dirname(__file__), '..', 'MASER-main')
sys.path.insert(0, maser_dir)

import pickle
import numpy as np
from pympler import asizeof
from xmkckks_wrapper import MPHEServer


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
    print("MASER xMKCKKS 密文大小测试")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. 初始化服务器和客户端（模拟多密钥场景）
    # ------------------------------------------------------------------
    server = MPHEServer(server_id=0)
    num_clients = 5
    clients = [MPHEServer(server_id=i + 1) for i in range(num_clients)]

    print(f"\n[1] 初始化完成")
    print(f"    - 服务器 ID = 0")
    print(f"    - 客户端数量 = {num_clients}")

    # ------------------------------------------------------------------
    # 2. 模拟数据加密（单个密文）
    # ------------------------------------------------------------------
    # 使用 4096 个 slots（与 MNIST LeNet-5 参数规模接近）
    slot_size = 4096
    dummy_data = np.random.randn(slot_size).tolist()

    # 客户端 1 加密
    ct_single = clients[0].encryptFromPk(dummy_data)
    ct_single_serialized = pickle.dumps(ct_single, protocol=2)
    single_size = len(ct_single_serialized)

    # 分析密文结构
    single_poly_count = len(ct_single.data)
    single_idxs = ct_single.idxs

    print(f"\n[2] 单个客户端加密完成")
    print(f"    - 数据长度 = {slot_size}")
    print(f"    - 密文多项式数量 = {single_poly_count}")
    print(f"    - 密文索引 (idxs) = {single_idxs}")
    print(f"    - 密文大小（pickle序列化） = {single_size} bytes ({fmt_size(single_size)})")

    # ------------------------------------------------------------------
    # 3. 多客户端加密并聚合（验证线性增长）
    # ------------------------------------------------------------------
    # 所有客户端加密相同数据（模拟联邦学习场景）
    ciphertexts = []
    for i, client in enumerate(clients):
        ct = client.encryptFromPk(dummy_data)
        ciphertexts.append(ct)
        print(f"    - 客户端 {i + 1} 加密完成")

    # 服务器聚合密文
    ct_aggregated = ciphertexts[0]
    for i in range(1, len(ciphertexts)):
        ct_aggregated = server.addCTs(ct_aggregated, ciphertexts[i])
        print(f"    - 聚合客户端 {i + 1} 密文...")

    ct_agg_serialized = pickle.dumps(ct_aggregated, protocol=2)
    aggregated_size = len(ct_agg_serialized)

    # 分析聚合密文结构
    agg_poly_count = len(ct_aggregated.data)
    agg_idxs = ct_aggregated.idxs

    print(f"\n[3] 聚合密文完成")
    print(f"    - 参与客户端数 = {num_clients}")
    print(f"    - 聚合密文多项式数量 = {agg_poly_count}")
    print(f"    - 聚合密文索引 (idxs) = {agg_idxs}")
    print(f"    - 聚合密文大小 = {aggregated_size} bytes ({fmt_size(aggregated_size)})")

    # ------------------------------------------------------------------
    # 4. 对比与结论
    # ------------------------------------------------------------------
    ratio = aggregated_size / single_size
    expected_ratio = num_clients  # xMKCKKS 理论值：线性增长

    print(f"\n[4] 对比结果")
    print(f"    - 单个密文大小     : {fmt_size(single_size)}")
    print(f"    - 聚合密文大小     : {fmt_size(aggregated_size)}")
    print(f"    - 实际大小比例     : {ratio:.2f}x")
    print(f"    - 理论大小比例     : {expected_ratio}x (xMKCKKS 线性增长)")

    if ratio >= expected_ratio * 0.8:  # 允许一定误差
        print(f"    - 结论             : [验证通过] 聚合密文大小随客户端数线性增长")
    else:
        print(f"    - 结论             : [验证失败] 聚合密文大小未达到预期线性增长")

    # ------------------------------------------------------------------
    # 5. 测试不同客户端数量下的密文大小
    # ------------------------------------------------------------------
    print(f"\n[5] 不同客户端数量下的密文大小")
    print(f"    {'客户端数':<10} {'聚合密文大小':<15} {'相对单个比例':<10}")
    print(f"    {'-'*35}")

    for n in [1, 2, 3, 5, 10]:
        # 创建 n 个客户端
        test_clients = [MPHEServer(server_id=i + 100) for i in range(n)]
        test_cts = [c.encryptFromPk(dummy_data) for c in test_clients]

        # 聚合
        test_agg = test_cts[0]
        for i in range(1, len(test_cts)):
            test_agg = server.addCTs(test_agg, test_cts[i])

        test_size = len(pickle.dumps(test_agg, protocol=2))
        test_ratio = test_size / single_size
        print(f"    {n:<10} {fmt_size(test_size):<15} {test_ratio:.2f}x")

    # ------------------------------------------------------------------
    # 6. 测试解密份额大小（关键通信开销）
    # ------------------------------------------------------------------
    print(f"\n[6] 解密份额大小测试")
    print(f"    论文指出：解密份额大小 ≈ 密文的一半（43KB vs 87KB）")

    # 使用 5 个客户端进行完整解密流程测试
    num_test_clients = 5
    test_clients = [MPHEServer(server_id=i + 200) for i in range(num_test_clients)]
    test_cts = [c.encryptFromPk(dummy_data) for c in test_clients]

    # 聚合密文
    test_agg = test_cts[0]
    for i in range(1, len(test_cts)):
        test_agg = server.addCTs(test_agg, test_cts[i])

    agg_size = len(pickle.dumps(test_agg, protocol=2))

    # 每个客户端计算解密份额
    print(f"\n    聚合密文大小 = {fmt_size(agg_size)}")
    print(f"    {'客户端':<10} {'解密份额大小':<15} {'相对聚合密文':<10}")
    print(f"    {'-'*35}")

    partial_sizes = []
    for i, client in enumerate(test_clients):
        partial_ct = client.partialDecrypt(test_agg)
        partial_size = len(pickle.dumps(partial_ct, protocol=2))
        partial_ratio = partial_size / agg_size
        partial_sizes.append(partial_size)
        print(f"    {i+1:<10} {fmt_size(partial_size):<15} {partial_ratio:.2f}x")

    avg_partial_size = sum(partial_sizes) / len(partial_sizes)
    print(f"\n    平均解密份额大小 = {fmt_size(avg_partial_size)}")
    print(f"    聚合密文大小     = {fmt_size(agg_size)}")
    print(f"    比例             = {avg_partial_size/agg_size:.2f}x")

    # ------------------------------------------------------------------
    # 7. 完整通信量汇总（基于论文分析）
    # ------------------------------------------------------------------
    print(f"\n[7] xMK-CKKS 单轮完整通信量汇总")
    print(f"    （假设 N 个客户端，单个密文大小 = S）")
    print(f"    {'-'*60}")
    print(f"    {'项目':<30} {'方向':<10} {'大小公式':<20}")
    print(f"    {'-'*60}")
    print(f"    {'全局模型下发':<30} {'Server→Client':<10} {'明文模型':<20}")
    print(f"    {'加密密文上传':<30} {'Client→Server':<10} {'N × S':<20}")
    print(f"    {'聚合密文分量广播':<30} {'Server→Client':<10} {'N × (S/2)':<20}")
    print(f"    {'解密份额上传':<30} {'Client→Server':<10} {'N × (S/2)':<20}")
    print(f"    {'最终全局模型下发':<30} {'Server→Client':<10} {'明文模型':<20}")
    print(f"    {'-'*60}")
    print(f"    {'密文通信总量':<30} {'':<10} {'N × S + N × S/2 + N × S/2 = 2N × S':<20}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()