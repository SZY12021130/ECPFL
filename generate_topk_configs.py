#!/usr/bin/env python3
"""生成 TopK sweep 实验的配置文件"""
import yaml
import os

def load_base_config(ds):
    """加载对应数据集的基础配置"""
    path = f"tmp_configs/_auto_{ds}_threshold_0.5.yaml"
    if not os.path.exists(path):
        # 回退查找任何该数据集的配置
        import glob
        candidates = glob.glob(f"tmp_configs/_auto_{ds}_threshold_*.yaml")
        if candidates:
            path = candidates[0]
        else:
            raise FileNotFoundError(f"No base config found for {ds}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_config(ds, pct):
    """生成 topk 配置"""
    cfg = load_base_config(ds)
    
    # 修改 global_mask_vote
    cfg['global_mask_vote']['mode'] = 'topk'
    cfg['global_mask_vote']['topk_pct'] = float(pct)
    # 保留 topk_count_k 作为fallback
    if 'topk_count_k' not in cfg['global_mask_vote']:
        cfg['global_mask_vote']['topk_count_k'] = 20
    
    # 移除 threshold_pct（避免混淆）
    if 'threshold_pct' in cfg['global_mask_vote']:
        del cfg['global_mask_vote']['threshold_pct']
    
    return cfg

datasets = {
    'mnist': 'mnist',
    'fashion_mnist': 'fashion_mnist', 
    'cifar10': 'cifar10'
}
topk_pcts = [0.1, 0.3, 0.5, 0.7, 0.9]

os.makedirs('tmp_configs', exist_ok=True)

for ds_key, ds_name in datasets.items():
    for pct in topk_pcts:
        cfg = generate_config(ds_key, pct)
        out_path = f"tmp_configs/_auto_{ds_key}_topk_{pct}.yaml"
        with open(out_path, 'w', encoding='utf-8') as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"Generated: {out_path}")

print("Done!")
