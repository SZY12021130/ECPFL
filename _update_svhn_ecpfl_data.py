#!/usr/bin/env python3
"""
更新 SVHN 上 ECPFL-UN / ECPFL-TH-0.7 的通信与准确率数据，
数据来源：accuracy_baseline/ours/result_fix_pro/ 下的最新实验。
"""
import json, os, re, yaml

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
COMM_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/communication.json")
ACC_JSON = os.path.join(PROJECT_ROOT, "tools/plot_experiment/plot_compare/script/accuracy.json")

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
        "sim_comm_time_s": extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s"),
    }

def read_test_acc(metrics_path):
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [x / 100.0 for x in data["test_acc"]]

EXPERIMENTS = {
    "ECPFL-UN": {
        "dir": "accuracy_baseline/ours/result_fix_pro/experiment_20260624_194053_svhn_union",
        "acc_key": "ECPFL-UN",
    },
    "ECPFL-TH-0.7": {
        "dir": "accuracy_baseline/ours/result_fix_pro/experiment_20260624_204358_svhn_th",
        "acc_key": "ECPFL-TH-0.7",
    },
}

# 读取现有 JSON
with open(COMM_JSON, "r", encoding="utf-8") as f:
    comm_data = json.load(f)
with open(ACC_JSON, "r", encoding="utf-8") as f:
    acc_data = json.load(f)

for comm_key, info in EXPERIMENTS.items():
    exp_dir = os.path.join(PROJECT_ROOT, info["dir"])
    report = parse_report(os.path.join(exp_dir, "report.md"))
    test_acc = read_test_acc(os.path.join(exp_dir, "metrics.json"))

    uv_mb = report["total_upload_mb"]
    dv_mb = report["effective_download_mb"]
    tv_mb = report["total_comm_mb"]
    tt = report["sim_comm_time_s"]

    print(f"[{comm_key}] 从 {info['dir']} 读取:")
    print(f"  UV={uv_mb:.2f}MB ({uv_mb/1024:.2f}GB) DV={dv_mb:.2f}MB ({dv_mb/1024:.2f}GB)")
    print(f"  TV={tv_mb:.2f}MB ({tv_mb/1024:.2f}GB) TT(Comm)={tt:.2f}s")
    print(f"  AC(final)={test_acc[-1]*100:.2f}%")

    # 更新通信 JSON
    comm_data.setdefault(comm_key, {})
    comm_data[comm_key]["SVHN"] = {
        "UV_GB": round(uv_mb / 1024, 2),
        "DV_GB": round(dv_mb / 1024, 2),
        "TV_GB": round(tv_mb / 1024, 2),
        "TT_S": round(tt, 2),
    }

    # 更新准确率 JSON（保留 4 位小数，与现有风格一致）
    acc_key = info["acc_key"]
    acc_data["SVHN"][acc_key] = [round(x, 4) for x in test_acc]

# 写回
with open(COMM_JSON, "w", encoding="utf-8") as f:
    json.dump(comm_data, f, indent=2, ensure_ascii=False)
with open(ACC_JSON, "w", encoding="utf-8") as f:
    json.dump(acc_data, f, indent=2, ensure_ascii=False)

print("\n[OK] 已更新 communication.json 与 accuracy.json")
