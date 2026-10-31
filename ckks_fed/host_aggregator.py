"""
Host 侧同态预聚合模块
========================

在 TEE 解密之前，Host 侧先对同一 batch 位置的客户端密文执行同态预聚合：
  agg_ct_j = Σ_{i∈S_j} w_i · ct_{i,j}

核心收益：
  - TEE 解密量从 O(n·J) 降到 O(J)
  - 聚合后的密文解密得到 Σ w_i·(g_i + b_i)，TEE 内只需一次标量除法即可得加权平均

安全边界：
  - Host 不持有私钥，所有运算在同态域完成
  - TEE 仍然负责最终解密、掩码补偿和重加密
"""

import numpy as np
import tenseal as ts
from typing import List, Dict, Tuple, Optional, Any
import logging
import time

logger = logging.getLogger(__name__)


def host_homomorphic_aggregate(
    client_uploads: List[Dict[str, Any]],
    client_weights: List[float],
    ckks_manager,
) -> Tuple[Dict[str, Any], List[float], List[List[int]], float]:
    """
    Host 侧同态预聚合。

    对每个 batch 位置 j：
      1. 收集所有上传了 batch j 的客户端密文
      2. 反序列化 bytes → CKKSVector（如需要）
      3. 对每个密文执行同态标量乘 w_i
      4. 同态加法聚合：agg_ct_j = Σ w_i · ct_{i,j}
      5. 记录聚合权重 W_j = Σ w_i

    Args:
        client_uploads: List[Dict]，每个客户端上传的稀疏密文包
        client_weights: List[float]，每个客户端的聚合权重
        ckks_manager: CKKSManager 实例（提供 TenSEAL context）

    Returns:
        (aggregated_upload, agg_weights, client_upload_masks, host_agg_time)
        - aggregated_upload: Dict，格式同客户端上传，但每个 batch 只有一个聚合密文
        - agg_weights: List[float]，长度 J，每个 batch 的聚合权重 W_j
        - client_upload_masks: List[List[int]]，每个客户端的上传 mask（TEE 补偿用）
        - host_agg_time: float，Host 侧同态聚合耗时（秒）
    """
    if not client_uploads:
        return {}, [], [], 0.0

    num_batches = len(client_uploads[0]['mask'])
    batch_size = client_uploads[0]['batch_size']
    total_elements = client_uploads[0]['total_elements']
    shapes = client_uploads[0]['shapes']
    offsets = client_uploads[0]['offsets']

    ctx = ckks_manager.context.context

    # 初始化每个 batch 的聚合状态
    aggregated_cts: List[Optional[ts.CKKSVector]] = [None] * num_batches
    agg_weights = [0.0] * num_batches
    client_upload_masks = []

    start_time = time.time()

    for upload, w in zip(client_uploads, client_weights):
        mask = upload['mask']
        client_upload_masks.append(list(mask))
        ciphertexts = upload['ciphertexts']

        # 反序列化 bytes → CKKSVector
        if ciphertexts and isinstance(ciphertexts[0], bytes):
            cts = [ts.CKKSVector.load(ctx, c) for c in ciphertexts]
        else:
            cts = list(ciphertexts)

        # 按 mask 遍历，将密文对齐到对应的 batch 位置
        ct_idx = 0
        for j, is_selected in enumerate(mask):
            if is_selected == 1:
                ct = cts[ct_idx]
                # 同态标量乘权重
                weighted_ct = ct * w

                # 同态加法聚合
                if aggregated_cts[j] is None:
                    aggregated_cts[j] = weighted_ct
                else:
                    aggregated_cts[j] = aggregated_cts[j] + weighted_ct

                agg_weights[j] += w
                ct_idx += 1

    # 序列化聚合密文（None 表示该 batch 无人上传）
    serialized_cts = []
    agg_mask = []
    for j in range(num_batches):
        if aggregated_cts[j] is not None:
            serialized_cts.append(aggregated_cts[j].serialize())
            agg_mask.append(1)
        else:
            serialized_cts.append(None)
            agg_mask.append(0)

    host_agg_time = time.time() - start_time

    aggregated_upload = {
        '__sparse__': True,
        'ciphertexts': serialized_cts,
        'mask': agg_mask,
        'batch_size': batch_size,
        'total_elements': total_elements,
        'shapes': shapes,
        'offsets': offsets,
        '__aggregated__': True,
    }

    logger.info(
        f"Host homomorphic aggregation | clients={len(client_uploads)} | "
        f"batches={num_batches} | active_batches={sum(agg_mask)} | "
        f"host_agg_time={host_agg_time:.4f}s"
    )

    return aggregated_upload, agg_weights, client_upload_masks, host_agg_time
