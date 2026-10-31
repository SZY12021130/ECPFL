#!/usr/bin/env python3
"""
跨 baseline 结果收集器
- 读取本项目各 baseline 的 metrics.json
- 读取 FedPHE standalone 的 metrics.json
- 合并为统一的 comparison_results.json
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = PROJECT_ROOT / "results" / "baseline_comparison"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_metrics(results_dir: Path) -> Path:
    """在 results_dir 下查找最新的 experiment_*/metrics.json。"""
    if not results_dir.exists():
        return results_dir / "metrics.json"
    exp_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir() and d.name.startswith("experiment_")])
    if exp_dirs:
        return exp_dirs[-1] / "metrics.json"
    return results_dir / "metrics.json"


def extract_ckks_fed_metrics(metrics: dict, name: str) -> dict:
    """从本项目的 metrics.json 中提取标准化指标。"""
    # 本项目的 metrics 是列表形式，每个 key 对应每轮的值
    rounds = list(range(len(metrics.get("test_acc", []))))
    return {
        "name": name,
        "rounds": rounds,
        "test_acc": metrics.get("test_acc", []),
        "test_loss": metrics.get("test_loss", []),
        "upload_cost": metrics.get("upload_cost", []),
        "download_cost": metrics.get("download_cost", []),
        "total_communication_cost": metrics.get("total_communication_cost", []),
        "time_cost": metrics.get("total_round_time", []),  # 或 total_round_real_time
        "final_acc": metrics.get("test_acc", [0])[-1],
        "final_loss": metrics.get("test_loss", [0])[-1],
        "total_upload": sum(metrics.get("upload_cost", [])),
        "total_download": sum(metrics.get("download_cost", [])),
        "total_comm": sum(metrics.get("total_communication_cost", [])),
    }


def extract_fedphe_metrics(metrics: dict) -> dict:
    """从 FedPHE standalone 的 metrics.json 中提取标准化指标。"""
    return {
        "name": "FedPHE (standalone)",
        "rounds": metrics.get("rounds", []),
        "test_acc": metrics.get("test_acc", []),
        "test_loss": metrics.get("test_loss", []),
        "upload_cost": metrics.get("upload_cost", []),
        "download_cost": metrics.get("download_cost", []),
        "total_communication_cost": metrics.get("total_communication_cost", []),
        "time_cost": metrics.get("time_cost", []),
        "final_acc": metrics.get("final_acc", 0.0),
        "final_loss": metrics.get("final_loss", 0.0),
        "total_upload": metrics.get("total_upload", 0),
        "total_download": metrics.get("total_download", 0),
        "total_comm": metrics.get("total_comm", 0),
    }


def main():
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = BASELINE_DIR / "comparison_results.json"

    results = {}

    # 1. FedAvg+CKKS（本项目）
    ckks_path = find_latest_metrics(PROJECT_ROOT / "results" / "baseline_fedavg_ckks")
    if ckks_path.exists():
        raw = load_json(ckks_path)
        results["fedavg_ckks"] = extract_ckks_fed_metrics(raw, "FedAvg+CKKS")
        print(f"[OK] 加载 FedAvg+CKKS: {ckks_path}")
    else:
        print(f"[WARN] 未找到 FedAvg+CKKS 结果: {ckks_path}")

    # 2. FedPHE internal（本项目 Group B）
    fedphe_int_path = find_latest_metrics(PROJECT_ROOT / "results" / "baseline_fedphe_internal")
    if fedphe_int_path.exists():
        raw = load_json(fedphe_int_path)
        results["fedphe_internal"] = extract_ckks_fed_metrics(raw, "FedPHE (internal)")
        print(f"[OK] 加载 FedPHE internal: {fedphe_int_path}")
    else:
        print(f"[WARN] 未找到 FedPHE internal 结果: {fedphe_int_path}")

    # 3. FedPHE standalone（独立项目）
    fedphe_std_path = PROJECT_ROOT / "results" / "baseline_fedphe_standalone" / "metrics.json"
    if fedphe_std_path.exists():
        raw = load_json(fedphe_std_path)
        results["fedphe_standalone"] = extract_fedphe_metrics(raw)
        print(f"[OK] 加载 FedPHE standalone: {fedphe_std_path}")
    else:
        print(f"[WARN] 未找到 FedPHE standalone 结果: {fedphe_std_path}")

    # 4. ESAFL（预留）
    esafl_path = find_latest_metrics(PROJECT_ROOT / "results" / "baseline_esafl")
    if esafl_path.exists():
        raw = load_json(esafl_path)
        results["esafl"] = extract_ckks_fed_metrics(raw, "ESAFL")
        print(f"[OK] 加载 ESAFL: {esafl_path}")
    else:
        print(f"[WARN] 未找到 ESAFL 结果: {esafl_path}")

    # 5. CipherFetch / FedFetch（预留）
    cipherfetch_path = find_latest_metrics(PROJECT_ROOT / "results" / "baseline_cipherfetch")
    if cipherfetch_path.exists():
        raw = load_json(cipherfetch_path)
        results["cipherfetch"] = extract_ckks_fed_metrics(raw, "CipherFetch (FedFetch+CKKS)")
        print(f"[OK] 加载 CipherFetch: {cipherfetch_path}")
    else:
        print(f"[WARN] 未找到 CipherFetch 结果: {cipherfetch_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[OK] 对比结果已汇总: {output_path}")


if __name__ == "__main__":
    main()
