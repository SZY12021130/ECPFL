"""
MASER mask 计算与参数级稀疏化支持
====================================
基于 MASER 论文的 mask 裁剪逻辑：
  1. 客户端本地计算参数级 mask（保留绝对值最大的 topk_ratio 比例参数）
  2. 提取 mask=1 的参数值及其全局索引，打包加密上传
  3. 服务端聚合索引（union），解密后用 np.zeros 恢复完整模型
"""

import torch
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def compute_maser_mask(model_update: Dict[str, torch.Tensor],
                       topk_ratio: float = 0.5) -> Dict[str, torch.Tensor]:
    """
    计算 MASER 参数级 mask（只考虑权重，偏置全部保留）。

    Returns:
        mask 字典，和 model_update 同 key，值为 0/1 的 float mask tensor
    """
    all_abs_values = []
    for name in sorted(model_update.keys()):
        param = model_update[name]
        if 'bias' in name.lower():
            continue
        all_abs_values.extend(np.abs(param.detach().cpu().numpy()).flatten().tolist())

    if len(all_abs_values) == 0:
        return {name: torch.ones_like(param) for name, param in model_update.items()}

    threshold = np.percentile(all_abs_values, 100 * (1 - topk_ratio))

    masks = {}
    for name in sorted(model_update.keys()):
        param = model_update[name]
        if 'bias' in name.lower():
            masks[name] = torch.ones_like(param)
        else:
            masks[name] = (torch.abs(param) >= threshold).float()

    active = sum(int(m.sum().item()) for m in masks.values())
    total = sum(m.numel() for m in masks.values())
    logger.info(f"[MASER] Mask computed | topk_ratio={topk_ratio} | active={active}/{total} ({active/total:.2%})")
    return masks


def apply_maser_mask(model_update: Dict[str, torch.Tensor],
                     mask: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """将 MASER mask 应用到模型更新上（mask=0 的位置置 0）。"""
    result = {}
    for name in sorted(model_update.keys()):
        result[name] = model_update[name] * mask.get(name, torch.ones_like(model_update[name]))
    return result


def extract_important_params(model_update: Dict[str, torch.Tensor],
                             topk_ratio: float = 0.5) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    提取 MASER 重要参数及其全局索引。

    Returns:
        values:  mask=1 的参数值（一维 numpy 数组）
        indices: 对应的全局索引（一维 numpy 数组）
        total_elements: 总参数数量
    """
    masks = compute_maser_mask(model_update, topk_ratio)
    masked_update = apply_maser_mask(model_update, masks)

    all_values = []
    for name in sorted(masked_update.keys()):
        all_values.extend(masked_update[name].detach().cpu().numpy().flatten().tolist())
    total_elements = len(all_values)
    all_values = np.array(all_values, dtype=np.float64)

    # 提取非 0 索引（mask=1 的位置）
    nonzero_indices = np.nonzero(all_values != 0)[0]
    important_values = all_values[nonzero_indices]

    logger.info(f"[MASER] Extract | important={len(nonzero_indices)}/{total_elements} ({len(nonzero_indices)/max(1,total_elements):.2%})")
    return important_values, nonzero_indices, total_elements


def pack_important_values(values: np.ndarray, batch_size: int) -> Tuple[List[np.ndarray], int]:
    """将重要参数值切分为 batch，不足 batch_size 的部分补 0。"""
    if len(values) == 0:
        return [np.zeros(batch_size, dtype=np.float64)], 0

    # pad to multiple of batch_size
    pad_len = (batch_size - (len(values) % batch_size)) % batch_size
    if pad_len > 0:
        values = np.concatenate([values, np.zeros(pad_len, dtype=np.float64)])

    batches = []
    for i in range(0, len(values), batch_size):
        batches.append(values[i:i + batch_size])

    return batches, len(values)  # 返回实际 pad 后的长度（用于服务端知道有多少有效值）


def restore_full_params(values: np.ndarray, indices: np.ndarray, total_elements: int) -> np.ndarray:
    """用 np.zeros 恢复完整参数向量，并按索引填入 values。"""
    full = np.zeros(total_elements, dtype=np.float64)
    if len(indices) > 0:
        # 确保 values 和 indices 长度一致（取前 len(indices) 个）
        values = values[:len(indices)]
        # 防止 indices 超出范围（取交集）
        valid = indices < total_elements
        full[indices[valid]] = values[valid]
    return full


def flatten_model_update(model_update: Dict[str, torch.Tensor]) -> np.ndarray:
    """将模型更新按固定顺序展平为一维 numpy 数组。"""
    all_values = []
    for name in sorted(model_update.keys()):
        all_values.extend(model_update[name].detach().cpu().numpy().flatten().tolist())
    return np.array(all_values, dtype=np.float64)


def extract_values_by_indices(model_update: Dict[str, torch.Tensor],
                              indices: np.ndarray) -> np.ndarray:
    """按全局索引从模型更新中提取参数值。"""
    flat = flatten_model_update(model_update)
    indices = np.asarray(indices, dtype=np.int64)
    valid = (indices >= 0) & (indices < len(flat))
    return flat[indices[valid]]


def apply_values_to_model_update(model_update: Dict[str, torch.Tensor],
                                 values: np.ndarray,
                                 indices: np.ndarray) -> Dict[str, torch.Tensor]:
    """将 values 按全局索引放回到模型更新中（其他位置置 0）。"""
    shapes = {name: list(param.shape) for name, param in model_update.items()}
    offsets = {}
    offset = 0
    for name in sorted(shapes.keys()):
        numel = np.prod(shapes[name])
        offsets[name] = (offset, numel)
        offset += numel

    flat = np.zeros(offset, dtype=np.float64)
    indices = np.asarray(indices, dtype=np.int64)
    values = np.asarray(values, dtype=np.float64)
    valid = (indices >= 0) & (indices < len(flat)) & (np.arange(len(indices)) < len(values))
    flat[indices[valid]] = values[valid]

    result = {}
    for name in sorted(shapes.keys()):
        off, numel = offsets[name]
        result[name] = torch.tensor(flat[off:off + numel].reshape(shapes[name]))
    return result


def aggregate_maser_masks(client_masks: List[np.ndarray],
                          total_elements: int,
                          voting_threshold: float = 0.5,
                          topk_ratio: float = None) -> np.ndarray:
    """
    聚合多个客户端的参数级 mask，生成全局 mask。

    Args:
        client_masks: 客户端 mask 列表，每个元素 shape=(total_elements,) 的 0/1 数组
        total_elements: 总参数数量
        voting_threshold: 阈值，参数被选中需要超过该比例的客户端投票
        topk_ratio: 如果指定，则按投票数取 top-k 比例的参数（覆盖 threshold）

    Returns:
        全局 mask，shape=(total_elements,) 的 0/1 数组
    """
    votes = np.zeros(total_elements, dtype=np.int32)
    valid_count = 0
    for mask in client_masks:
        mask_arr = np.asarray(mask, dtype=np.int8)
        if mask_arr.size == 0:
            continue
        # 对齐长度
        if len(mask_arr) != total_elements:
            aligned = np.zeros(total_elements, dtype=np.int8)
            copy_len = min(len(mask_arr), total_elements)
            aligned[:copy_len] = mask_arr[:copy_len]
            mask_arr = aligned
        votes += mask_arr.astype(np.int32)
        valid_count += 1

    if valid_count == 0:
        return np.ones(total_elements, dtype=np.int8)

    vote_ratio = votes / valid_count

    if topk_ratio is not None and 0 < topk_ratio < 1:
        # 按投票比例取 top-k
        k = max(1, int(total_elements * topk_ratio))
        threshold_value = np.partition(vote_ratio, -k)[-k]
        global_mask = (vote_ratio >= threshold_value).astype(np.int8)
    else:
        # 使用阈值筛选
        global_mask = (vote_ratio > voting_threshold).astype(np.int8)

    active = int(np.sum(global_mask))
    logger.info(
        f"[MASER] Global mask vote | clients={valid_count} | "
        f"active={active}/{total_elements} ({active / max(1, total_elements):.2%}) | "
        f"threshold={voting_threshold if topk_ratio is None else f'topk={topk_ratio}'}"
    )
    return global_mask


def get_indices_from_mask(global_mask: np.ndarray) -> np.ndarray:
    """从全局 mask 中提取选中的全局索引。"""
    return np.nonzero(np.asarray(global_mask, dtype=np.int8))[0].astype(np.int64)


def pack_maser_global_values(model_update: Dict[str, torch.Tensor],
                             indices: np.ndarray,
                             batch_size: int) -> Tuple[List[np.ndarray], np.ndarray]:
    """
    按全局索引构造 MASER 稀疏 batch 向量（对齐原始参数位置）。

    每个 value 被放到其全局索引对应的 batch/slot 位置，保证服务器密文加法
    更新时不会错位。只返回包含非零值的 batch 及其 mask。

    Returns:
        batches: 非零 batch 列表，每个 batch 长度为 batch_size
        mask: 0/1 数组，标记哪些 batch 被选中
    """
    flat = flatten_model_update(model_update)
    total_elements = len(flat)
    indices = np.asarray(indices, dtype=np.int64)
    values = flat[indices]

    num_batches = (total_elements + batch_size - 1) // batch_size
    mask = np.zeros(num_batches, dtype=np.int8)
    batch_dict = {}

    for idx, val in zip(indices, values):
        batch_idx = int(idx // batch_size)
        slot_idx = int(idx % batch_size)
        if batch_idx not in batch_dict:
            batch_dict[batch_idx] = np.zeros(batch_size, dtype=np.float64)
        batch_dict[batch_idx][slot_idx] = val
        mask[batch_idx] = 1

    # 按 batch_idx 排序，保证顺序确定性
    batches = [batch_dict[i] for i in sorted(batch_dict.keys())]
    return batches, mask


def pack_maser_compressed_values(model_update: Dict[str, torch.Tensor],
                                 indices: np.ndarray,
                                 batch_size: int) -> Tuple[List[np.ndarray], int]:
    """
    将 MASER 选中参数按全局索引顺序压缩打包（原版 MASER 风格）。

    不按原始 batch/slot 位置放回，而是把 values 连续排列，切分为
    ceil(k / batch_size) 个 slice，最后一个 slice 补 0。这样可以显著减少
    上传 batch 数量（尤其是选中参数较小时）。

    Returns:
        batches: 压缩后的 batch 列表
        padded_len: 补 0 后的总长度（用于服务端知道有效值数量）
    """
    values = extract_values_by_indices(model_update, indices)
    batches, padded_len = pack_important_values(values, batch_size)
    return batches, padded_len
