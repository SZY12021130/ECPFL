#!/usr/bin/env python3
"""提取所有实验的通信量数据"""
import re
import os

def extract_comm_from_log(log_path):
    """从日志提取总上传和下载"""
    total_up = 0.0
    total_dl = 0.0
    if not os.path.exists(log_path):
        return 0.0, 0.0
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # 方法1: 匹配 [轮次/ROUND] 行的 comm=XX MB (↑XX MB ↓XX MB)
            # 使用通用模式，不依赖特定字符
            m = re.search(r'comm=([\d.]+)\s*MB\s*\(\D*([\d.]+)\s*MB\s*\D*([\d.]+)\s*(?:MB|B)\)', line)
            if m:
                total_up += float(m.group(2))
                dl_str = m.group(3)
                total_dl += float(dl_str)
            else:
                # 方法2: 通信汇总格式
                m2 = re.search(r'通信汇总:\s*↑([\d.]+)\s*MB.*?effective↓=([\d.]+)\s*MB', line)
                if m2:
                    total_up += float(m2.group(1))
                    total_dl += float(m2.group(2))
    return total_up, total_dl

results = {}

for ds in ['mnist', 'fashion_mnist', 'cifar10']:
    results[ds] = {}
    
    # Union
    log = f"accuracy_topk_v2/20260605_{ds}_union/run.log"
    up, dl = extract_comm_from_log(log)
    results[ds]['union'] = {'upload': up, 'download': dl}
    
    # Threshold
    for pct in [0.1, 0.3, 0.5, 0.7, 0.9]:
        log = f"accuracy_threshold_v2/20260604_{ds}_threshold_pct_{pct}/run.log"
        up, dl = extract_comm_from_log(log)
        results[ds][f'threshold_{pct}'] = {'upload': up, 'download': dl}
    
    # TopK
    for pct in [0.1, 0.3, 0.5, 0.7, 0.9]:
        log = f"accuracy_topk_v2/20260605_{ds}_topk_pct_{pct}/run.log"
        up, dl = extract_comm_from_log(log)
        results[ds][f'topk_{pct}'] = {'upload': up, 'download': dl}

# 打印结果
for ds in ['mnist', 'fashion_mnist', 'cifar10']:
    print(f"\n{ds}:")
    for key, val in results[ds].items():
        print(f"  {key}: upload={val['upload']:.1f} MB, download={val['download']:.1f} MB")

# 保存为JSON
import json
with open('comm_data.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved to comm_data.json")
