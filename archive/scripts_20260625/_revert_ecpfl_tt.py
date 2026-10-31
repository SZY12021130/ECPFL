#!/usr/bin/env python3
"""
恢复 ECPFL 的原始 TT 值
TT 来自 report.md 中的 Total Simulated Time
"""
import json
import os

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# 原始的 TT 值（从 report.md 读取）
ORIGINAL_TT = {
    "ECPFL-UN": {
        "MNIST": 1759.44,
        "FMNIST": 1292.68,
        "CIFAR-10": 6259.40,
        "SVHN": 801.28,
    },
    "ECPFL-TH-0.1": {
        "MNIST": 1689.80,
    },
    "ECPFL-TH-0.3": {
        "FMNIST": 1039.12,
    },
    "ECPFL-TH-0.7": {
        "CIFAR-10": 2756.68,
        "SVHN": 801.28,
    },
    "ECPFL-RK-0.1": {
        "MNIST": 482.16,
    },
    "ECPFL-RK-0.3": {
        "FMNIST": 654.36,
    },
    "ECPFL-RK-0.7": {
        "CIFAR-10": 5797.88,
        "SVHN": 801.28,
    },
}

# 读取当前 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

print("=" * 80)
print("恢复 ECPFL 原始 TT 值")
print("=" * 80)

for method, datasets in ORIGINAL_TT.items():
    for ds, tt_value in datasets.items():
        if method in comm_data and ds in comm_data[method]:
            old_tt = comm_data[method][ds].get("TT_S", 0)
            comm_data[method][ds]["TT_S"] = tt_value
            print(f"  {method} | {ds}: {old_tt:.2f} s -> {tt_value:.2f} s")

# 保存更新后的数据
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已恢复原始 TT 值: {COMM_JSON}")
