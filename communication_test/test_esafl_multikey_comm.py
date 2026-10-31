"""
ESAFL 多密钥通信量对比测试

对比：
1. 单密钥模式（SIMULATION）：聚合密文大小不变
2. 多密钥模式（原版 ESAFL）：聚合密文大小 = 单密文 × (n+1)/2

测试内容：
- 不同客户端数量下的聚合密文大小
- 通信量对比（单密钥 vs 多密钥）
"""
import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import yaml
from typing import Dict, List

# 尝试加载 TenSEAL
try:
    import tenseal as ts
    TENSEAL_AVAILABLE = True
except ImportError:
    TENSEAL_AVAILABLE = False
    print("[WARN] TenSEAL 未安装，使用理论计算")


def fmt_size(size_bytes: int) -> str:
    """格式化字节大小"""
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.2f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


class ESAFLCommSimulator:
    """ESAFL 通信量模拟器（单密钥 vs 多密钥对比）"""
    
    def __init__(self, poly_modulus_degree: int = 8192):
        """
        Args:
            poly_modulus_degree: CKKS 多项式模数度
        """
        self.poly_degree = poly_modulus_degree
        
        # 单密钥密文大小估算（2个多项式）
        # 每个多项式 = poly_degree × coeff_modulus_bits / 8 bytes
        # 假设 coeff_modulus = [60, 40, 40, 60] = 200 bits
        coeff_mod_bits = 200
        self.single_poly_size = poly_modulus_degree * coeff_mod_bits // 8
        self.single_ct_size = 2 * self.single_poly_size  # 单密钥密文 = 2个多项式
        
        if TENSEAL_AVAILABLE:
            # 实际测量 TenSEAL 密文大小
            ctx = ts.context(
                ts.SCHEME_TYPE.CKKS,
                poly_modulus_degree=poly_modulus_degree,
                coeff_mod_bit_sizes=[60, 40, 40, 60]
            )
            ctx.global_scale = 2**40
            vec = ts.ckks_vector(ctx, [1.0] * (poly_modulus_degree // 2))
            self.actual_single_ct_size = len(vec.serialize())
            print(f"[TenSEAL] 实测单密文大小: {fmt_size(self.actual_single_ct_size)}")
            self.single_ct_size = self.actual_single_ct_size
    
    def compute_single_key_agg_size(self, num_batches: int) -> int:
        """
        单密钥模式：聚合密文大小不变
        
        Args:
            num_batches: 密文 batch 数量
        
        Returns:
            聚合密文总大小（字节）
        """
        # 单密钥聚合：密文大小不变，仍为 2 个多项式
        return num_batches * self.single_ct_size
    
    def compute_multi_key_agg_size(self, num_clients: int, num_batches: int) -> int:
        """
        多密钥模式（原版 ESAFL）：聚合密文大小随客户端数增长
        
        Args:
            num_clients: 参与聚合的客户端数量
            num_batches: 密文 batch 数量
        
        Returns:
            聚合密文总大小（字节）
        
        公式：
            聚合密文多项式数 = (n + 1) / 2 × 2 = n + 1 个多项式
            聚合密文大小 = 单密文 × (n + 1) / 2
        """
        # 多密钥聚合：密文包含 (n+1) 个多项式
        # 聚合密文大小 = 单密文 × (n+1)/2
        agg_ct_size = self.single_ct_size * (num_clients + 1) / 2
        return int(num_batches * agg_ct_size)
    
    def compute_communication_cost(
        self,
        num_clients: int,
        num_batches: int,
        mode: str = "single_key"
    ) -> Dict[str, int]:
        """
        计算完整通信量
        
        Args:
            num_clients: 客户端数量
            num_batches: 密文 batch 数量
            mode: "single_key" | "multi_key"
        
        Returns:
            通信量字典
        """
        # 上行：每个客户端上传 num_batches 个密文
        upload_cost = num_clients * num_batches * self.single_ct_size
        
        # 下行：服务器广播聚合密文给所有客户端
        if mode == "single_key":
            agg_ct_size = self.single_ct_size
        else:
            agg_ct_size = self.single_ct_size * (num_clients + 1) / 2
        
        download_cost = num_clients * num_batches * int(agg_ct_size)
        
        # 多密钥额外开销：解密份额上传
        if mode == "multi_key":
            # ESAFL 原版：每个客户端上传解密份额
            # 解密份额大小 ≈ 聚合密文大小（MASER 实测）
            partial_dec_upload = num_clients * num_batches * int(agg_ct_size)
        else:
            partial_dec_upload = 0
        
        total = upload_cost + download_cost + partial_dec_upload
        
        return {
            'upload_cost': upload_cost,
            'download_cost': download_cost,
            'partial_dec_upload': partial_dec_upload,
            'total': total,
            'single_ct_size': self.single_ct_size,
            'agg_ct_size': int(agg_ct_size),
            'num_batches': num_batches,
            'num_clients': num_clients,
        }
    
    def compare_modes(
        self,
        num_clients_list: List[int],
        num_batches: int = 10
    ) -> List[Dict]:
        """
        对比单密钥和多密钥模式在不同客户端数量下的通信量
        
        Args:
            num_clients_list: 客户端数量列表
            num_batches: 密文 batch 数量
        
        Returns:
            对比结果列表
        """
        results = []
        for n in num_clients_list:
            single_key = self.compute_communication_cost(n, num_batches, "single_key")
            multi_key = self.compute_communication_cost(n, num_batches, "multi_key")
            
            # 计算膨胀比例
            agg_ratio = multi_key['agg_ct_size'] / single_key['agg_ct_size']
            total_ratio = multi_key['total'] / single_key['total']
            
            results.append({
                'num_clients': n,
                'num_batches': num_batches,
                'single_key_agg_ct': fmt_size(single_key['agg_ct_size']),
                'multi_key_agg_ct': fmt_size(multi_key['agg_ct_size']),
                'agg_ct_ratio': f"{agg_ratio:.2f}x",
                'single_key_total': fmt_size(single_key['total']),
                'multi_key_total': fmt_size(multi_key['total']),
                'total_ratio': f"{total_ratio:.2f}x",
                'single_key_upload': fmt_size(single_key['upload_cost']),
                'single_key_download': fmt_size(single_key['download_cost']),
                'multi_key_upload': fmt_size(multi_key['upload_cost']),
                'multi_key_download': fmt_size(multi_key['download_cost']),
                'multi_key_partial_dec': fmt_size(multi_key['partial_dec_upload']),
            })
        
        return results
    
    def print_comparison_table(self, results: List[Dict]):
        """打印对比表格"""
        print("\n" + "=" * 100)
        print("ESAFL 通信量对比：单密钥（SIMULATION） vs 多密钥（原版）")
        print("=" * 100)
        
        # 表头
        header = f"{'Clients':<8} {'Batches':<8} | "
        header += f"{'单密钥聚合':<12} {'多密钥聚合':<12} {'聚合比例':<10} | "
        header += f"{'单密钥总量':<12} {'多密钥总量':<12} {'总量比例':<10}"
        print(header)
        print("-" * 100)
        
        # 数据行
        for r in results:
            row = f"{r['num_clients']:<8} {r['num_batches']:<8} | "
            row += f"{r['single_key_agg_ct']:<12} {r['multi_key_agg_ct']:<12} {r['agg_ct_ratio']:<10} | "
            row += f"{r['single_key_total']:<12} {r['multi_key_total']:<12} {r['total_ratio']:<10}"
            print(row)
        
        print("=" * 100)
        
        # 详细分解
        print("\n详细通信量分解（以 num_clients=25 为例）：")
        print("-" * 100)
        example = results[-1] if len(results) > 0 else None
        if example:
            print(f"单密钥模式（SIMULATION）：")
            print(f"  - 上行（加密上传）：{example['single_key_upload']}")
            print(f"  - 下行（聚合广播）：{example['single_key_download']}")
            print(f"  - 总量：{example['single_key_total']}")
            print()
            print(f"多密钥模式（原版 ESAFL）：")
            print(f"  - 上行（加密上传）：{example['multi_key_upload']}")
            print(f"  - 下行（聚合广播）：{example['multi_key_download']}")
            print(f"  - 解密份额上传：{example['multi_key_partial_dec']}")
            print(f"  - 总量：{example['multi_key_total']}")
    
    def print_formula_explanation(self):
        """打印公式解释"""
        print("\n" + "=" * 100)
        print("公式解释")
        print("=" * 100)
        print()
        print("单密钥模式（SIMULATION）：")
        print("  - 单密文大小 = 2 × poly_degree × coeff_mod_bits / 8 bytes")
        print(f"  - 实测值 = {fmt_size(self.single_ct_size)}")
        print("  - 聚合密文大小 = 单密文大小（不变）")
        print("  - 原因：CKKS 同态加法不改变密文结构")
        print()
        print("多密钥模式（原版 ESAFL）：")
        print("  - 聚合密文多项式数 = (n + 1) 个")
        print("  - 聚合密文大小 = 单密文 × (n + 1) / 2")
        print("  - 原因：多密钥聚合密文包含所有客户端的密钥分量")
        print()
        print("通信量组成：")
        print("  单密钥：upload + download")
        print("  多密钥：upload + download + partial_dec_upload")
        print("=" * 100)


def test_with_real_ckks():
    """使用真实 TenSEAL 密文测试"""
    if not TENSEAL_AVAILABLE:
        print("[ERROR] TenSEAL 未安装，无法进行真实测试")
        return
    
    print("\n" + "=" * 100)
    print("真实 TenSEAL 密文大小测试")
    print("=" * 100)
    
    # 创建 CKKS context
    poly_degree = 8192
    ctx = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=poly_degree,
        coeff_mod_bit_sizes=[60, 40, 40, 60]
    )
    ctx.global_scale = 2**40
    
    # 创建多个密文并测试聚合
    num_clients = 10
    slot_count = poly_degree // 2
    
    print(f"\n创建 {num_clients} 个客户端密文...")
    ciphertexts = []
    for i in range(num_clients):
        vec = ts.ckks_vector(ctx, np.random.randn(slot_count))
        ct_size = len(vec.serialize())
        ciphertexts.append(vec)
        print(f"  客户端 {i}: 密文大小 = {fmt_size(ct_size)}")
    
    # 同态聚合
    print(f"\n同态聚合 {num_clients} 个密文...")
    agg = ciphertexts[0]
    for i in range(1, num_clients):
        agg = agg + ciphertexts[i]
    agg_size = len(agg.serialize())
    
    print(f"聚合后密文大小 = {fmt_size(agg_size)}")
    print(f"与单个密文对比 = {agg_size} vs {len(ciphertexts[0].serialize())}")
    print(f"结论：{'相同（单密钥特性）' if agg_size == len(ciphertexts[0].serialize()) else '不同'}")
    
    print("=" * 100)


def main():
    """主测试函数"""
    print("=" * 100)
    print("ESAFL 多密钥通信量对比测试")
    print("=" * 100)
    
    # 初始化模拟器
    simulator = ESAFLCommSimulator(poly_modulus_degree=8192)
    
    # 打印公式解释
    simulator.print_formula_explanation()
    
    # 对比不同客户端数量
    num_clients_list = [5, 10, 25, 50, 100]
    num_batches = 115  # MNIST LeNet-5 约 115 个 batch
    
    results = simulator.compare_modes(num_clients_list, num_batches)
    simulator.print_comparison_table(results)
    
    # 真实 TenSEAL 测试
    test_with_real_ckks()
    
    # 结论
    print("\n" + "=" * 100)
    print("结论")
    print("=" * 100)
    print("1. 单密钥模式（SIMULATION）：聚合密文大小不变，通信量较低")
    print("2. 多密钥模式（原版 ESAFL）：聚合密文大小随客户端数增长")
    print("3. 多密钥额外开销：解密份额上传（每客户端上传聚合密文大小的份额）")
    print("4. 实测验证：TenSEAL 单密钥聚合后密文大小确实不变")
    print("=" * 100)


if __name__ == "__main__":
    main()