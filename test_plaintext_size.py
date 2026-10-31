"""
明文模型大小验证实验
验证：明文加权平均后，大小是否变化
"""
import torch
import numpy as np
import sys
sys.path.insert(0, '.')

from ckks_fed.models import create_model
import yaml

def fmt_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def get_model_size(params_dict):
    """计算明文参数字典的字节大小"""
    return sum(p.numel() * p.element_size() for p in params_dict.values())

def weighted_average_plaintext(updates, weights):
    """明文加权平均（模拟 FedAvg 聚合）"""
    result = {}
    total_weight = sum(weights)
    for name in updates[0]:
        weighted_sum = torch.zeros_like(updates[0][name])
        for update, w in zip(updates, weights):
            weighted_sum += update[name] * w
        result[name] = weighted_sum / total_weight
    return result

def main():
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model = create_model(config['model']['name'], config)
    params = {name: param.data.clone() for name, param in model.named_parameters()}
    base_size = get_model_size(params)
    print(f"基础模型大小: {fmt_size(base_size)}")

    # 实验1: 10个客户端分别产生不同更新
    print("\n=== 实验1: 10个客户端明文更新大小 ===")
    updates = []
    sizes = []
    for i in range(10):
        # 每个客户端的更新 = 随机梯度
        update = {name: torch.randn_like(p) * 0.01 for name, p in params.items()}
        sz = get_model_size(update)
        updates.append(update)
        sizes.append(sz)
        print(f"  客户端{i} 更新大小: {fmt_size(sz)}")
    print(f"平均: {fmt_size(sum(sizes)//len(sizes))}, min={fmt_size(min(sizes))}, max={fmt_size(max(sizes))}")

    # 实验2: 加权平均后的聚合结果大小
    print("\n=== 实验2: 10个更新加权平均后的大小 ===")
    weights = [1.0] * 10
    agg = weighted_average_plaintext(updates, weights)
    agg_size = get_model_size(agg)
    print(f"聚合后大小: {fmt_size(agg_size)}")
    print(f"与单个更新对比: {agg_size} vs {sizes[0]} → {'相同' if agg_size == sizes[0] else '不同'}")

    # 实验3: 模拟 delta = w_new - w_old 的大小
    print("\n=== 实验3: Delta (w_new - w_old) 的大小 ===")
    delta = {name: params[name] - params[name] + torch.randn_like(p) * 0.01 for name, p in params.items()}
    delta_size = get_model_size(delta)
    print(f"Delta 大小: {fmt_size(delta_size)}")
    print(f"与基础模型对比: {delta_size} vs {base_size} → {'相同' if delta_size == base_size else '不同'}")

    # 实验4: 模拟全局模型累加 delta 后的大小
    print("\n=== 实验4: 全局模型 + Delta 后的大小 ===")
    global_model = {name: p.clone() for name, p in params.items()}
    for name in global_model:
        global_model[name] = global_model[name] + delta[name]
    new_size = get_model_size(global_model)
    print(f"累加后大小: {fmt_size(new_size)}")
    print(f"与基础模型对比: {new_size} vs {base_size} → {'相同' if new_size == base_size else '不同'}")

    # 实验5: 多次累加 deltas 后的大小
    print("\n=== 实验5: 多次累加 deltas 后的大小 ===")
    curr_model = {name: p.clone() for name, p in params.items()}
    for step in range(5):
        d = {name: torch.randn_like(p) * 0.01 for name, p in params.items()}
        for name in curr_model:
            curr_model[name] = curr_model[name] + d[name]
        sz = get_model_size(curr_model)
        print(f"  累加 delta {step+1} 后大小: {fmt_size(sz)} {'(相同)' if sz == base_size else '(变了!)'}")

    print("\n=== 结论 ===")
    print("明文无论怎么操作（加权平均、加减、累加），结果大小始终与原始模型相同。")
    print("因此：每个明文 delta 的大小 = 完整模型大小。")

if __name__ == "__main__":
    main()
