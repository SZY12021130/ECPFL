"""
MASER xMKCKKS 密文大小变化测试

测试目标：
1. 验证单个密文大小是否固定
2. 验证聚合密文大小是否随客户端数量线性增长
3. 对比实测值 vs 线性插值预测 vs 旧硬编码公式 (n+1)/2
4. 验证部分解密后密文大小是否等于聚合密文大小
"""

import sys
import os
import time
import pickle

# 将 MASER-main 加入路径
maser_dir = os.path.join(os.path.dirname(__file__), 'MASER-main')
if os.path.exists(maser_dir):
    sys.path.insert(0, maser_dir)

try:
    from xmkckks_wrapper import MPHEServer
    XMKCKKS_AVAILABLE = True
except Exception as e:
    print(f"[ERROR] xMKCKKS 库加载失败: {e}")
    sys.exit(1)

# 同时加载修正后的管理器
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ckks_fed'))
from xmkckks_manager import xMKCKKSManager


def test_raw_library(client_counts, slot_size=4096):
    """
    直接调用 MASER 底层库，测试密文大小随客户端数量的变化。
    不经过 xMKCKKSManager，直接操作 MPHEServer。
    """
    results = []
    dummy_data = [0.1] * slot_size  # 固定测试数据

    for n in client_counts:
        print(f"\n[Raw] 测试 {n} 个客户端...")
        t0 = time.time()

        server = MPHEServer(server_id=0)
        clients = [MPHEServer(server_id=i + 1) for i in range(n)]

        # 单个密文
        single_ct = clients[0].encryptFromPk(dummy_data)
        single_size = len(pickle.dumps(single_ct, protocol=2))

        # 聚合密文
        agg_ct = single_ct
        for i in range(1, n):
            local_ct = clients[i].encryptFromPk(dummy_data)
            agg_ct = server.addCTs(agg_ct, local_ct)
        agg_size = len(pickle.dumps(agg_ct, protocol=2))

        # 部分解密（用第一个客户端）
        pd_ct = clients[0].partialDecrypt(agg_ct)
        pd_size = len(pickle.dumps(pd_ct, protocol=2))

        elapsed = time.time() - t0

        results.append({
            'clients': n,
            'single_mb': single_size / (1024 ** 2),
            'agg_mb': agg_size / (1024 ** 2),
            'pd_mb': pd_size / (1024 ** 2),
            'ratio': agg_size / single_size if single_size else 0,
            'time_sec': elapsed,
        })
        print(f"  single={single_size/1024:.1f} KB | agg={agg_size/1024:.1f} KB | "
              f"pd={pd_size/1024:.1f} KB | ratio={results[-1]['ratio']:.2f}x | time={elapsed:.2f}s")

    return results


def test_manager_estimation(raw_results, slot_size=4096):
    """
    使用 xMKCKKSManager（修正后版本）验证估算准确性。
    对每个 raw_results 中的客户端数，创建对应的管理器，
    然后对比实测 agg_size 和 compute_aggregated_ct_size 的返回值。
    """
    print("\n" + "=" * 60)
    print("[Manager] 验证线性插值估算的准确性")
    print("=" * 60)

    # 用一个较大的客户端数作为基准，看对其他数的预测是否准确
    max_clients = max(r['clients'] for r in raw_results)
    print(f"用 {max_clients} 客户端初始化管理器作为基准...")

    t0 = time.time()
    mgr = xMKCKKSManager(num_clients=max_clients, slot_size=slot_size)
    print(f"初始化耗时 {time.time() - t0:.2f}s")
    print(f"  实测 single={mgr.single_ct_size/1024:.1f} KB | "
          f"agg@{max_clients}={mgr.aggregated_ct_size/1024:.1f} KB | "
          f"poly_ratio={mgr.poly_ratio:.2f}x")

    print("\n" + "-" * 60)
    print(f"{'N':>3} | {'实测Agg(MB)':>12} | {'插值预测(MB)':>12} | {'旧公式(n+1)/2':>12} | {'误差率':>8}")
    print("-" * 60)

    for r in raw_results:
        n = r['clients']
        actual_mb = r['agg_mb']
        predicted = mgr.compute_aggregated_ct_size(n)
        predicted_mb = predicted / (1024 ** 2)

        # 旧硬编码公式 (n+1)/2
        old_formula = mgr.single_ct_size * (n + 1) / 2
        old_mb = old_formula / (1024 ** 2)

        err_pct = abs(predicted - actual_mb * (1024**2)) / (actual_mb * (1024**2)) * 100 if actual_mb else 0

        print(f"{n:>3} | {actual_mb:>12.4f} | {predicted_mb:>12.4f} | {old_mb:>12.4f} | {err_pct:>7.2f}%")

    return mgr


def main():
    print("=" * 60)
    print("MASER xMKCKKS 密文大小变化测试")
    print("=" * 60)

    client_counts = [1, 2, 3, 5, 10, 20]
    slot_size = 4096

    print(f"\n测试参数: slot_size={slot_size}, clients={client_counts}")

    # 1. 直接测试底层库
    raw_results = test_raw_library(client_counts, slot_size)

    # 2. 验证管理器估算
    mgr = test_manager_estimation(raw_results, slot_size)

    # 3. 汇总对比表
    print("\n" + "=" * 60)
    print("汇总对比")
    print("=" * 60)
    print(f"{'N':>3} | {'Single(MB)':>10} | {'Agg(MB)':>10} | {'PD(MB)':>10} | "
          f"{'Agg/Single':>10} | {'PD/Agg':>8}")
    print("-" * 60)
    for r in raw_results:
        print(f"{r['clients']:>3} | {r['single_mb']:>10.4f} | {r['agg_mb']:>10.4f} | "
              f"{r['pd_mb']:>10.4f} | {r['ratio']:>10.2f}x | "
              f"{r['pd_mb']/r['agg_mb'] if r['agg_mb'] else 0:>7.2f}x")

    # 4. 线性拟合斜率（验证是否真的线性）
    if len(raw_results) >= 2:
        import numpy as np
        x = [r['clients'] for r in raw_results]
        y = [r['agg_mb'] for r in raw_results]
        slope, intercept = np.polyfit(x, y, 1)
        r_squared = 1 - sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y)) / sum((yi - sum(y)/len(y))**2 for yi in y)
        print(f"\n线性拟合: agg_size = {slope:.4f} * N + {intercept:.4f}")
        print(f"R^2 = {r_squared:.6f} (越接近1越线性)")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
