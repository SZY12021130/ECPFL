#!/usr/bin/env python3
"""
修正 ECPFL-RK-0.7 的 SVHN 数据
从 report.md 中读取正确的预取模式数据
"""
import json, os, re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")

# ECPFL-RK-0.7 的 SVHN 实验目录
SVHN_EXP = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7")

def parse_report(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    def extract(pattern):
        m = re.search(pattern, content)
        return float(m.group(1)) if m else None
    
    return {
        "total_upload_mb": extract(r"Total Upload.*?\|\s*([\d.]+)\s*MB"),
        "effective_download_mb": extract(r"Effective Download.*?\|\s*([\d.]+)\s*MB"),
        "total_comm_mb": extract(r"Total Communication.*?\|\s*([\d.]+)\s*MB"),
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
    }

# 读取 report.md
report_path = os.path.join(SVHN_EXP, "report.md")
data = parse_report(report_path)

uv_mb = data["total_upload_mb"]
dv_mb = data["effective_download_mb"]
tv_mb = data["total_comm_mb"]
tt = data["sim_time_s"]

print(f"从 report.md 读取的数据:")
print(f"  UV (Upload)  = {uv_mb:.2f} MB = {uv_mb/1024:.2f} GB")
print(f"  DV (Fetch)   = {dv_mb:.2f} MB = {dv_mb/1024:.2f} GB")
print(f"  TV (UV+DV)   = {tv_mb:.2f} MB = {tv_mb/1024:.2f} GB")
print(f"  TT           = {tt:.2f} s")

# 更新 communication.json
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)

# 更新 ECPFL-RK-0.7 的 SVHN 数据
comm_data["ECPFL-RK-0.7"]["SVHN"] = {
    "UV_GB": round(uv_mb / 1024, 2),
    "DV_GB": round(dv_mb / 1024, 2),
    "TV_GB": round(tv_mb / 1024, 2),
    "TT_S": round(tt, 2),
}

with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)

print(f"\n[OK] 已更新 communication.json")
