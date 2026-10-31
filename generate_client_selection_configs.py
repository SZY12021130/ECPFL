#!/usr/bin/env python3
"""生成客户端选择策略实验的配置文件"""
import yaml
import os

# 最佳投票机制配置
VOTE_CONFIG = {
    "mnist": {"mode": "topk", "topk_pct": 0.1},
    "fashion_mnist": {"mode": "topk", "topk_pct": 0.3},
    "cifar10": {"mode": "topk", "topk_pct": 0.7},
}

# 客户端选择策略
STRATEGIES = [
    "random",
    "sticky",
    "sketch_clustering",
    "poc",
    "tifl",
    "haccs",
    "oort",
]

# 基础配置模板（基于最佳 topk 配置）
def generate_config(ds, strategy):
    base_cfg = f"tmp_configs/_auto_{ds}_topk_{VOTE_CONFIG[ds]['topk_pct']}.yaml"
    with open(base_cfg, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    
    # 修改客户端选择策略
    cfg['client_selection']['strategy'] = strategy
    
    # 确保 fairness 关闭（保持对比公平）
    cfg['client_selection']['fairness']['enabled'] = False
    
    return cfg

os.makedirs('tmp_configs', exist_ok=True)

count = 0
for ds in ["mnist", "fashion_mnist", "cifar10"]:
    for strategy in STRATEGIES:
        cfg = generate_config(ds, strategy)
        out_path = f"tmp_configs/_auto_{ds}_vote_{VOTE_CONFIG[ds]['topk_pct']}_cs_{strategy}.yaml"
        with open(out_path, 'w', encoding='utf-8') as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        count += 1
        print(f"Generated: {out_path}")

print(f"\nDone! Total {count} configs generated.")
