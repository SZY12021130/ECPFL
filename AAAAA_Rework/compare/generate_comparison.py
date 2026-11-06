#!/usr/bin/env python3
"""汇总五基线（FedAvg+CKKS, FedPHE, ESAFL, MASER, ECPFL）在四数据集上的对比数据。

输出：
- AAAAA_Rework/compare/comparison.yaml
- AAAAA_Rework/compare/comparison.json
- AAAAA_Rework/compare/comparison.md
"""
import json
import os
import re
import yaml
from pathlib import Path

ROOT = Path("E:/GithubProjects/ckks_fed_robustness")
OUT_DIR = ROOT / "AAAAA_Rework" / "compare"

DATASET_ORDER = ["mnist", "fashion_mnist", "cifar10", "svhn"]
DATASET_LABEL = {
    "mnist": "MNIST (LeNet)",
    "fashion_mnist": "FMNIST (CNN)",
    "cifar10": "CIFAR-10 (ResNet-20)",
    "svhn": "SVHN (ResNet-32)",
}

METHOD_ORDER = [
    "FedAvg+CKKS",
    "FedPHE (Top-$\\zeta$)",
    "ESAFL",
    "MASER",
    "ECPFL-UN",
    "ECPFL-TH-$\\theta$",
    "ECPFL-RK-$\\theta$",
]

# 基线实验路径映射（report.md）
BASELINE_PATHS = {
    "FedAvg+CKKS": {
        "mnist": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10/report.md",
        "svhn": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn/report.md",
    },
    "FedPHE (Top-$\\zeta$)": {
        "mnist": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10/report.md",
        "svhn": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn/report.md",
    },
    "ESAFL": {
        "mnist": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_163033_mnist/report.md",
        "fashion_mnist": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_203351_fashion_mnist/report.md",
        "cifar10": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_210302_cifar10/report.md",
        "svhn": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_221916_svhn/report.md",
    },
    "MASER": {
        "mnist": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10/report.md",
        "svhn": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn/report.md",
    },
}

# ECPFL 实验路径映射（ecpfl_results.json）。FMNIST 已统一改为 ζ=0.3。
ECPFL_PATHS = {
    "mnist": {
        "un": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_113644_mnist/ecpfl_results.json",
        "th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_120541_mnist/ecpfl_results.json",
        "rk": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_123327_mnist/ecpfl_results.json",
    },
    "fashion_mnist": {
        # ζ=0.3；脚本会优先按 (dataset, vote_rule) 自动发现最新实验
        "un": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_182301_fashion_mnist/ecpfl_results.json",
        "th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_185237_fashion_mnist/ecpfl_results.json",
        "rk": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_192222_fashion_mnist/ecpfl_results.json",
    },
    "cifar10": {
        "un": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_202239_cifar10/ecpfl_results.json",
        "th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_210440_cifar10/ecpfl_results.json",
        "rk": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_215202_cifar10/ecpfl_results.json",
    },
    "svhn": {
        "un": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_233648_svhn/ecpfl_results.json",
        "th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261104_011747_svhn/ecpfl_results.json",
        "rk": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261104_031237_svhn/ecpfl_results.json",
    },
}

def find_latest_ecpfl_experiment(dataset: str, vote_rule: str):
    """在 ECPFL result 目录中按修改时间找最新、匹配 dataset 与 vote_rule 的实验 JSON。"""
    base = ROOT / "AAAAA_Rework" / "ECPFL" / "result" / "accuracy"
    candidates = []
    for exp_dir in base.glob("experiment_*"):
        if not exp_dir.is_dir():
            continue
        json_path = exp_dir / "ecpfl_results.json"
        if not json_path.exists():
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        cfg = data.get("config", {})
        if cfg.get("data", {}).get("dataset") != dataset:
            continue
        if cfg.get("ecpfl", {}).get("vote_rule") != vote_rule:
            continue
        candidates.append((json_path.stat().st_mtime, json_path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def find_latest_baseline_report(base_dir: Path, dataset: str):
    """在 baseline result 目录中按修改时间找最新、匹配 dataset 的 report.md。"""
    candidates = []
    for exp_dir in base_dir.glob("experiment_*"):
        if not exp_dir.is_dir():
            continue
        report_path = exp_dir / "report.md"
        if not report_path.exists():
            continue
        try:
            text = report_path.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"\| Dataset / 数据集 \| (\w+) ", text)
        if not m or m.group(1) != dataset:
            continue
        candidates.append((report_path.stat().st_mtime, report_path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def parse_report_md(path: Path):
    """从 report.md 中提取 AC、通信量、时间。"""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")

    def find(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    # 准确率
    ac_str = find(r"\| Final Test Accuracy / 最终测试准确率 \| \*\*([0-9.]+)%\*\*")
    ac = float(ac_str) if ac_str else None

    # 总通信量 (MB) -> TV (GB)
    total_comm_str = find(r"\| Total Communication / 总通信量 \| ([0-9.]+) MB")
    tv_gb = float(total_comm_str) / 1024 if total_comm_str else None

    # 总上传 / 时间
    upload_str = find(r"\| Total Upload / 总上传量 \| ([0-9.]+) MB / ([0-9.]+) s")
    if upload_str:
        # re.search 的 group(1) 已在上面的 find 中返回，需要完整匹配
        m = re.search(r"\| Total Upload / 总上传量 \| ([0-9.]+) MB / ([0-9.]+) s", text)
        uv_gb = float(m.group(1)) / 1024
        ut_s = float(m.group(2))
    else:
        uv_gb = ut_s = None

    # 总下载 / 时间
    m = re.search(r"\| Total Download / 总下载量 \| ([0-9.]+) MB / ([0-9.]+) s", text)
    if m:
        dv_gb = float(m.group(1)) / 1024
        dt_s = float(m.group(2))
    else:
        dv_gb = dt_s = None

    # 总模拟时间 (TT)
    tt_str = find(r"\| Total Simulated Time / 总模拟时间 \| ([0-9.]+) s")
    tt_s = float(tt_str) if tt_str else None

    return {
        "AC": ac,
        "TV_GB": tv_gb,
        "UV_GB": uv_gb,
        "DV_GB": dv_gb,
        "PV_GB": 0.0,
        "FV_GB": dv_gb,
        "UT_s": ut_s,
        "DT_s": dt_s,
        "TT_s": tt_s,
    }


def parse_ecpfl_json(path: Path):
    """从 ecpfl_results.json 中提取指标。"""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    rounds = data.get("rounds", [])
    return {
        "AC": data.get("final_test_acc"),
        "TV_GB": data.get("total_tv_mb", 0) / 1024,
        "UV_GB": data.get("total_upload_mb", 0) / 1024,
        "DV_GB": data.get("total_download_mb", 0) / 1024,
        "PV_GB": data.get("total_prefetch_mb", 0) / 1024,
        "FV_GB": (data.get("total_download_mb", 0) + data.get("total_prefetch_mb", 0)) / 1024,
        "UT_s": sum(r.get("enc_time", 0) for r in rounds),
        "DT_s": sum(r.get("dec_time", 0) for r in rounds),
        "TT_s": sum(r.get("round_time", 0) for r in rounds),
    }


def gather():
    results = {m: {} for m in METHOD_ORDER}

    # 基线：FedPHE FMNIST 优先用 AAAAA_Rework/FedPHE/result 下的新实验
    for method, ds_map in BASELINE_PATHS.items():
        for ds, rel in ds_map.items():
            path = ROOT / rel
            if method == "FedPHE (Top-$\\zeta$)" and ds == "fashion_mnist":
                new_path = find_latest_baseline_report(
                    ROOT / "AAAAA_Rework" / "FedPHE" / "result", ds)
                if new_path is not None:
                    path = new_path
            results[method][ds] = parse_report_md(path)

    # ECPFL：优先按 (dataset, vote_rule) 自动发现最新实验；找不到再回退硬编码路径
    for ds, variants in ECPFL_PATHS.items():
        for variant, rel in variants.items():
            method_name = {
                "un": "ECPFL-UN",
                "th": "ECPFL-TH-$\\theta$",
                "rk": "ECPFL-RK-$\\theta$",
            }[variant]
            path = find_latest_ecpfl_experiment(ds, variant)
            if path is None:
                path = ROOT / rel
            results[method_name][ds] = parse_ecpfl_json(path)

    return results


def fmt(x, decimals=2):
    if x is None:
        return ""
    return f"{x:.{decimals}f}"


def build_tables(results):
    # 准确率表
    ac_rows = []
    ac_rows.append(["Method"] + [DATASET_LABEL[d] for d in DATASET_ORDER])
    for m in METHOD_ORDER:
        row = [m]
        for d in DATASET_ORDER:
            row.append(fmt(results[m].get(d, {}).get("AC"), 2))
        ac_rows.append(row)

    # 通信量表（GB）
    comm_header = []
    for d in DATASET_ORDER:
        comm_header.extend([f"{DATASET_LABEL[d]} DV", "PV", "FV", "TV"])
    comm_rows = [["Method"] + comm_header]
    for m in METHOD_ORDER:
        row = [m]
        for d in DATASET_ORDER:
            r = results[m].get(d) or {}
            row.extend([
                fmt(r.get("DV_GB"), 2),
                fmt(r.get("PV_GB"), 2),
                fmt(r.get("FV_GB"), 2),
                fmt(r.get("TV_GB"), 2),
            ])
        comm_rows.append(row)

    # 时间表（秒）
    time_header = []
    for d in DATASET_ORDER:
        time_header.extend([f"{DATASET_LABEL[d]} UT", "DT", "TT"])
    time_rows = [["Method"] + time_header]
    for m in METHOD_ORDER:
        row = [m]
        for d in DATASET_ORDER:
            r = results[m].get(d) or {}
            row.extend([
                fmt(r.get("UT_s"), 1),
                fmt(r.get("DT_s"), 1),
                fmt(r.get("TT_s"), 1),
            ])
        time_rows.append(row)

    return {"accuracy": ac_rows, "communication": comm_rows, "time": time_rows}


def markdown_table(rows):
    lines = []
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("|" + "|".join(["---"] * len(rows[0])) + "|")
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = gather()
    tables = build_tables(results)

    # YAML / JSON
    payload = {
        "note": "DV=下行, PV=预取, FV=DV+PV, TV=UV+DV+PV; UT=加密/上传, DT=解密/下载, TT=总 wall-clock。空值表示实验尚未完成。",
        "results": results,
    }
    with open(OUT_DIR / "comparison.yaml", "w", encoding="utf-8") as f:
        yaml.dump(payload, f, allow_unicode=True, sort_keys=False)
    with open(OUT_DIR / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Markdown
    md = []
    md.append("# 五基线对比汇总表（FedAvg+CKKS / FedPHE / ESAFL / MASER / ECPFL）")
    md.append("")
    md.append("> **口径**：DV=Downstream Volume，PV=Prefetch Volume，FV=DV+PV，TV=UV+DV+PV；")
    md.append("> UT=Upload/Encryption time，DT=Download/Decryption time，TT=Total wall-clock time。")
    md.append("> 通信量单位 GB（1 GB = 1024 MB），时间单位秒。空单元格表示实验尚未完成。")
    md.append("")
    md.append("## 1. 最终测试准确率 AC (%)")
    md.append("")
    md.append(markdown_table(tables["accuracy"]))
    md.append("")
    md.append("## 2. 通信量 (GB)")
    md.append("")
    md.append(markdown_table(tables["communication"]))
    md.append("")
    md.append("## 3. 时间开销 (s)")
    md.append("")
    md.append(markdown_table(tables["time"]))
    md.append("")

    with open(OUT_DIR / "comparison.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Generated: {OUT_DIR / 'comparison.yaml'}")
    print(f"Generated: {OUT_DIR / 'comparison.json'}")
    print(f"Generated: {OUT_DIR / 'comparison.md'}")


if __name__ == "__main__":
    main()
