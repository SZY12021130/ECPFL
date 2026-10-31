"""
xMKCKKS 管理器 - 基于 MASER 底层库实现多密钥同态加密通信量统计

通信量组成（密文部分，不含掩码）：
1. 加密密文上传（Client→Server）：N × S
2. 聚合密文广播（Server→Client）：N × S_agg
3. 解密份额上传（Client→Server）：N × S_agg

其中：
- S = 单个密文大小（2 个多项式）
- S_agg = S × (n+1)/2（聚合密文，n+1 个多项式）

密文通信总量 = N × S + 2 × N × S_agg = N × S × (n+2)
"""

import sys
import os
import pickle
import numpy as np
import torch
from typing import Dict, List, Any, Tuple

# 将 MASER-main 目录加入 Python 路径
maser_dir = os.path.join(os.path.dirname(__file__), '..', 'MASER-main')
if os.path.exists(maser_dir):
    sys.path.insert(0, maser_dir)
    try:
        from xmkckks_wrapper import MPHEServer, Ciphertext
        XMKCKKS_AVAILABLE = True
    except Exception as e:
        print(f"[xMKCKKS] 加载失败: {e}")
        XMKCKKS_AVAILABLE = False
else:
    XMKCKKS_AVAILABLE = False


class xMKCKKSManager:
    """xMKCKKS 管理器 - 封装 MASER 底层库，实现通信量统计"""
    
    def __init__(self, num_clients: int = 5, slot_size: int = 4096, client_ids: List[int] = None):
        """
        初始化 xMKCKKS 管理器
        
        Args:
            num_clients: 客户端数量
            slot_size: 每个 slot 的数据长度（默认 4096，与 MNIST LeNet-5 参数规模接近）
            client_ids: 可选，外部框架使用的客户端 ID 列表（顺序与 self.clients 一一对应）。
                        若提供，则建立 client_id -> client_idx 的映射，方便按框架 client_id 查找。
        """
        if not XMKCKKS_AVAILABLE:
            raise RuntimeError("xMKCKKS 库不可用，请确保 MASER-main/xmkckks_go2py/xmkckks.dll 存在")
        
        self.num_clients = num_clients
        self.slot_size = slot_size
        
        # 初始化服务器和客户端
        self.server = MPHEServer(server_id=0)
        self.clients = [MPHEServer(server_id=i + 1) for i in range(num_clients)]
        
        # 建立外部 client_id 到内部 client_idx 的映射。
        # 默认情况下将外部标识符视为 0-based 内部索引，避免 1-based 映射导致
        # encrypt(1) 被错误解析为 index 0 的歧义。
        if client_ids is not None:
            if len(client_ids) != num_clients:
                raise ValueError("client_ids 长度必须与 num_clients 一致")
            self.client_id_to_idx = {cid: idx for idx, cid in enumerate(client_ids)}
        else:
            self.client_id_to_idx = {i: i for i in range(num_clients)}
        
        # 测试单个密文大小
        dummy_data = np.random.randn(slot_size).tolist()
        test_ct = self.clients[0].encryptFromPk(dummy_data)
        self.single_ct_size = len(pickle.dumps(test_ct, protocol=2))
        
        # 测试聚合密文大小
        test_cts = [c.encryptFromPk(dummy_data) for c in self.clients]
        test_agg = test_cts[0]
        for i in range(1, len(test_cts)):
            test_agg = self.server.addCTs(test_agg, test_cts[i])
        self.aggregated_ct_size = len(pickle.dumps(test_agg, protocol=2))

        # 测试部分解密份额大小（使用第一个客户端对聚合密文做 partial decrypt）
        if num_clients > 1:
            test_pd = self.clients[0].partialDecrypt(test_agg)
            self.partial_dec_size = len(pickle.dumps(test_pd, protocol=2))
        else:
            self.partial_dec_size = self.aggregated_ct_size

        # 计算多项式数量比例
        self.poly_ratio = self.aggregated_ct_size / self.single_ct_size

        print(f"[xMKCKKS] 初始化完成")
        print(f"    - 客户端数量 = {num_clients}")
        print(f"    - 单个密文大小 = {self._fmt_size(self.single_ct_size)}")
        print(f"    - 聚合密文大小 = {self._fmt_size(self.aggregated_ct_size)}")
        print(f"    - 解密份额大小 = {self._fmt_size(self.partial_dec_size)}")
        print(f"    - 多项式比例 = {self.poly_ratio:.2f}x (理论值 {(num_clients+1)/2:.2f}x)")
    
    def _fmt_size(self, size_bytes: int) -> str:
        """格式化字节大小"""
        if size_bytes >= 1024**3:
            return f"{size_bytes / 1024**3:.2f} GB"
        elif size_bytes >= 1024**2:
            return f"{size_bytes / 1024**2:.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} B"
    
    def get_client_idx(self, client_id: int) -> int:
        """将外部框架的 client_id 映射为内部 client_idx"""
        if client_id not in self.client_id_to_idx:
            raise ValueError(f"client_id={client_id} 未在 xMKCKKSManager 的 client_id_to_idx 中注册")
        return self.client_id_to_idx[client_id]

    def compute_single_ct_size(self) -> int:
        """返回单个密文大小（字节）"""
        return self.single_ct_size
    
    def compute_aggregated_ct_size(self, num_participants: int = None) -> int:
        """
        计算聚合密文大小（基于初始化时的实测值做线性插值）

        原理：
        - __init__ 中实测了 1 个客户端的单密文大小 (single_ct_size)
        - __init__ 中实测了 num_clients 个客户端聚合后的密文大小 (aggregated_ct_size)
        - 两个端点之间假设线性增长，据此推算任意参与人数的聚合密文大小

        Args:
            num_participants: 参与聚合的客户端数量（默认使用初始化时的 num_clients）

        Returns:
            聚合密文大小（字节）
        """
        if num_participants is None:
            num_participants = self.num_clients

        if self.num_clients <= 1:
            return self.single_ct_size

        # 基于实测值线性插值：
        # slope = (aggregated - single) / (num_clients - 1)
        # 即每增加 1 个客户端，聚合密文平均增大多少字节
        slope = (self.aggregated_ct_size - self.single_ct_size) / (self.num_clients - 1)
        return int(self.single_ct_size + slope * (num_participants - 1))

    def compute_partial_dec_size(self, num_participants: int = None) -> int:
        """
        计算解密份额大小

        Args:
            num_participants: 参与聚合的客户端数量

        Returns:
            解密份额大小（字节）
        """
        # 使用实测的单个解密份额大小，并按聚合密文的增长比例缩放
        if num_participants is None or num_participants == self.num_clients:
            return self.partial_dec_size
        ratio = self.compute_aggregated_ct_size(num_participants) / max(1, self.aggregated_ct_size)
        return int(self.partial_dec_size * ratio)
    
    def compute_upload_cost(self, num_clients: int, num_batches: int = 1) -> int:
        """
        计算上行通信量（加密密文上传）
        
        Args:
            num_clients: 客户端数量
            num_batches: 密文 batch 数量
        
        Returns:
            上行通信量（字节）
        """
        # 上行：每个客户端上传 num_batches 个密文
        return num_clients * num_batches * self.single_ct_size
    
    def compute_download_cost(self, num_clients: int, num_batches: int = 1) -> int:
        """
        计算下行通信量（聚合密文广播）
        
        Args:
            num_clients: 客户端数量
            num_batches: 密文 batch 数量
        
        Returns:
            下行通信量（字节）
        """
        # 下行：服务器广播聚合密文给所有客户端
        agg_ct_size = self.compute_aggregated_ct_size(num_clients)
        return num_clients * num_batches * agg_ct_size
    
    def compute_key_distribution_cost(self) -> int:
        """
        计算多密钥公钥分发通信量。

        流程：
        - 每个客户端向服务器上传自己的公钥 P
        - 服务器将聚合后的联合公钥 P 广播给所有客户端

        Returns:
            公钥分发总字节数
        """
        if not hasattr(self, 'clients') or len(self.clients) == 0:
            return 0
        # 单个公钥 P 的大小（pickle 序列化）
        single_pk_size = len(pickle.dumps(self.clients[0].pk[0].P, protocol=2))
        # 上行：N 个客户端各传一个 P
        # 下行：服务器广播聚合后的 P 给 N 个客户端
        return 2 * self.num_clients * single_pk_size

    def compute_partial_dec_upload_cost(self, num_clients: int, num_batches: int = 1) -> int:
        """
        计算解密份额上行通信量
        
        Args:
            num_clients: 客户端数量
            num_batches: 密文 batch 数量
        
        Returns:
            解密份额上行通信量（字节）
        """
        # 解密份额上传：每个客户端上传 num_batches 个解密份额
        partial_dec_size = self.compute_partial_dec_size(num_clients)
        return num_clients * num_batches * partial_dec_size
    
    def compute_total_communication_cost(self, num_clients: int, num_batches: int = 1) -> Dict[str, int]:
        """
        计算完整通信量
        
        Args:
            num_clients: 客户端数量
            num_batches: 密文 batch 数量
        
        Returns:
            通信量字典，包含：
            - upload_cost: 加密密文上传
            - download_cost: 聚合密文广播
            - partial_dec_upload: 解密份额上传
            - total: 总通信量
        """
        upload = self.compute_upload_cost(num_clients, num_batches)
        download = self.compute_download_cost(num_clients, num_batches)
        partial_dec_upload = self.compute_partial_dec_upload_cost(num_clients, num_batches)
        total = upload + download + partial_dec_upload
        
        return {
            'upload_cost': upload,
            'download_cost': download,
            'partial_dec_upload': partial_dec_upload,
            'total': total,
            'single_ct_size': self.single_ct_size,
            'aggregated_ct_size': self.compute_aggregated_ct_size(num_clients),
            'partial_dec_size': self.compute_partial_dec_size(num_clients),
            'poly_ratio': self.poly_ratio,
        }
    
    def print_communication_summary(self, num_clients: int, num_batches: int = 1):
        """打印通信量汇总"""
        costs = self.compute_total_communication_cost(num_clients, num_batches)
        
        print("\n" + "=" * 60)
        print("xMKCKKS 通信量汇总（密文部分）")
        print("=" * 60)
        print(f"客户端数量: {num_clients}")
        print(f"密文 batch 数: {num_batches}")
        print("-" * 60)
        print(f"单个密文大小: {self._fmt_size(costs['single_ct_size'])}")
        print(f"聚合密文大小: {self._fmt_size(costs['aggregated_ct_size'])} (比例 {costs['poly_ratio']:.2f}x)")
        print(f"解密份额大小: {self._fmt_size(costs['partial_dec_size'])}")
        print("-" * 60)
        print(f"① 加密密文上传 (Client→Server): {self._fmt_size(costs['upload_cost'])}")
        print(f"② 聚合密文广播 (Server→Client): {self._fmt_size(costs['download_cost'])}")
        print(f"③ 解密份额上传 (Client→Server): {self._fmt_size(costs['partial_dec_upload'])}")
        print("-" * 60)
        print(f"密文通信总量: {self._fmt_size(costs['total'])}")
        print("=" * 60)

    # ===================================================================
    # 以下为实现真实多密钥 MASER 流程扩展的方法
    # ===================================================================

    def setup_key_aggregation(self):
        """
        聚合所有客户端公钥，生成联合公钥并分发给每个客户端。
        在单进程模拟中，所有 client MPHEServer 实例都保存在本管理器内，
        因此可以直接完成聚合，无需 socket 通信。
        """
        if not hasattr(self, 'clients') or len(self.clients) == 0:
            raise RuntimeError("xMKCKKSManager 尚未初始化客户端实例")
        if self.num_clients <= 1:
            raise RuntimeError("多密钥至少需要 2 个客户端")

        # 收集每个客户端公钥的 P 多项式
        ring_p_list = [client.pk[0].P for client in self.clients]

        # 服务器聚合公钥
        aggregated_p = self.server.aggregate_ringPs(ring_p_list)

        # 将联合公钥写回每个客户端
        for client in self.clients:
            client.pk[0].P = aggregated_p

        print(f"[xMKCKKS] 联合公钥聚合完成 | 参与客户端={self.num_clients}")
        return aggregated_p

    def encrypt_for_client(self, values: List[float], client_idx: int) -> Any:
        """
        使用联合公钥为指定客户端加密一个 slice。

        Args:
            values: 明文向量（长度 <= slot_size），不足部分内部补 0
            client_idx: 客户端在 xMKCKKSManager.clients 中的 0-based 索引
                        （对应 server_id = client_idx + 1）

        Returns:
            xMKCKKS Ciphertext 对象
        """
        if client_idx < 0 or client_idx >= len(self.clients):
            raise ValueError(f"client_idx={client_idx} 超出范围 [0, {len(self.clients)-1}]")
        client = self.clients[client_idx]
        # 补 0 到 slot_size
        if len(values) < self.slot_size:
            values = list(values) + [0.0] * (self.slot_size - len(values))
        elif len(values) > self.slot_size:
            raise ValueError(f"values 长度 {len(values)} 超过 slot_size {self.slot_size}")
        return client.encryptFromPk(values)

    def aggregate_ciphertexts(self, cts: List[Any]) -> Any:
        """
        对多个 xMKCKKS 密文执行同态加法聚合。
        所有密文必须由联合公钥加密（不同 client_idx 均可）。
        """
        if len(cts) == 0:
            raise ValueError("密文列表为空")
        result = cts[0]
        for ct in cts[1:]:
            result = self.server.addCTs(result, ct)
        return result

    def partial_decrypt(self, aggregated_ct: Any, client_idx: int) -> Any:
        """
        由指定客户端对聚合密文产生部分解密份额。

        Args:
            aggregated_ct: 聚合后的 xMKCKKS Ciphertext
            client_idx: 客户端 0-based 索引
        """
        if client_idx < 0 or client_idx >= len(self.clients):
            raise ValueError(f"client_idx={client_idx} 超出范围")
        client = self.clients[client_idx]
        return client.partialDecrypt(aggregated_ct)

    def decode_partial_decryptions(self, pd_shares: List[Any], client_indices: List[int]) -> np.ndarray:
        """
        聚合所有客户端的部分解密份额并解码为明文。

        Args:
            pd_shares: 每个客户端的部分解密份额列表（顺序与 client_indices 一致）
            client_indices: 客户端在 xMKCKKSManager.clients 中的 0-based 索引列表

        Returns:
            解码后的明文 numpy 数组
        """
        if len(pd_shares) != len(client_indices):
            raise ValueError("pd_shares 与 client_indices 长度不一致")
        if len(pd_shares) == 0:
            raise ValueError("pd_shares 为空")

        # 转成 MPHEServer 实际的 idx（Go 层密文里的 key）
        server_ids = [self.clients[idx].idx for idx in client_indices]
        aggregated_pd = self.server.aggregate_pds(pd_shares, server_ids)
        decoded = self.server.decodeAfterPartialDecrypt(aggregated_pd)
        # xMK-CKKS 解码返回 2*slot_size 个浮点数，前 slot_size 个为有效明文。
        return np.array(decoded[: self.slot_size], dtype=np.float64)

    def decrypt_maser_compressed(
        self,
        encrypted_update: Dict[str, Any],
        partial_shares: List[Any],
        client_indices: List[int],
    ) -> Dict[str, torch.Tensor]:
        """
        将 MASER 压缩模式的多密钥聚合密文解密并 0 填充恢复完整模型更新。

        Args:
            encrypted_update: 聚合后的加密更新字典（含 ciphertexts/indices/padded_len/num_params/shapes/offsets）
            partial_shares: 每个客户端对该聚合密文的部分解密份额列表
            client_indices: 对应客户端在 xMKCKKSManager.clients 中的 0-based 索引列表

        Returns:
            恢复出的模型更新字典 {name: torch.Tensor}
        """
        from ckks_fed.maser_mask import restore_full_params

        ciphertexts = encrypted_update['ciphertexts']
        indices = np.array(encrypted_update.get('indices', []), dtype=np.int64)
        padded_len = encrypted_update.get('padded_len', 0)
        num_params = encrypted_update.get('num_params', 0)
        shapes = encrypted_update['shapes']
        offsets = encrypted_update['offsets']

        # 逐 slice 聚合解密份额并解码
        all_values = []
        for slice_idx, agg_ct in enumerate(ciphertexts):
            slice_shares = [shares[slice_idx] for shares in partial_shares]
            decoded = self.decode_partial_decryptions(slice_shares, client_indices)
            all_values.extend(decoded.tolist())

        values = np.array(all_values, dtype=np.float64)
        if padded_len > 0 and len(values) > padded_len:
            values = values[:padded_len]

        # 按参与客户端数做平均（MASER-main 原版逻辑）
        values = values / len(client_indices)

        # 0 填充恢复完整参数
        full = restore_full_params(values, indices, num_params)

        result = {}
        for name in sorted(shapes.keys()):
            off, numel = offsets[name]
            shape = shapes[name]
            result[name] = torch.tensor(full[off:off + numel].reshape(shape))
        return result

    def compute_xmkckks_update_size(self, ciphertexts: List[Any]) -> int:
        """计算 xMKCKKS 密文列表的 pickle 序列化大小（字节）"""
        total = 0
        for ct in ciphertexts:
            try:
                total += len(pickle.dumps(ct, protocol=2))
            except Exception:
                total += 0
        return total


def test_xmkckks_communication():
    """测试 xMKCKKS 通信量计算"""
    if not XMKCKKS_AVAILABLE:
        print("[ERROR] xMKCKKS 库不可用")
        return
    
    manager = xMKCKKSManager(num_clients=5, slot_size=4096)
    manager.print_communication_summary(num_clients=5, num_batches=6)


if __name__ == '__main__':
    test_xmkckks_communication()