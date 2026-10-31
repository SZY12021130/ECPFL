#!/usr/bin/env python3
"""
回退 ECPFL 通信量到对称模式：DV = UV, TV = 2 * UV
"""
import json
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# 读取当前数据
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

# ECPFL 方法列表
ecpfl_methods = ["ECPFL-UN", "ECPFL-TH-0.1", "ECPFL-TH-0.3", "ECPFL-TH-0.7", 
                 "ECPFL-RK-0.1", "ECPFL-RK-0.3", "ECPFL-RK-0.7"]

print("回退 ECPFL 通信量到对称模式（DV = UV）")
print("=" * 80)

for method in ecpfl_methods:
    if method not in comm_data:
        continue
    
    print(f"\n{method}:")
    
    for ds in ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]:
        if ds not in comm_data[method]:
            continue
        
        data = comm_data[method][ds]
        uv_gb = data.get("UV_GB", 0)
        
        # 对称模式：DV = UV
        dv_gb = uv_gb
        tv_gb = uv_gb + dv_gb
        
        print(f"  {ds}: UV={uv_gb:.2f}GB, DV={dv_gb:.2f}GB, TV={tv_gb:.2f}GB")
        
        # 更新数据
        data["DV_GB"] = dv_gb
        data["TV_GB"] = tv_gb

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新: {COMM_JSON}")
