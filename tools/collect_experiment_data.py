#!/usr/bin/env python3
"""Collect and unify experiment data from all directories."""

import os
import re
import json
import glob
import pickle
from pathlib import Path

# ---------------------------------------------------------------------------
# Parse size strings like "15.94 MB", "0 B", "459.74 KB"
# ---------------------------------------------------------------------------
def parse_size(s):
    s = s.strip()
    if s.endswith("MB"):
        return float(s[:-2].strip())
    elif s.endswith("KB"):
        return float(s[:-2].strip()) / 1024
    elif s.endswith("B"):
        val = s[:-1].strip()
        if val == "0":
            return 0.0
        return float(val) / (1024 * 1024)
    elif s.endswith("GB"):
        return float(s[:-2].strip()) * 1024
    return 0.0


# ---------------------------------------------------------------------------
# Parse run.log (for accuracy_client_selection, accuracy_threshold_v2, accuracy_topk_v2)
# ---------------------------------------------------------------------------
def parse_runlog(log_path):
    with open(log_path, "rb") as f:
        raw = f.read()

    acc_list = []
    comm_list = []
    ul_list = []
    dl_list = []
    sim_dur_list = []
    vclock_list = []

    # acc=XX.XX%
    acc_pattern = re.compile(rb"acc=([\d.]+)%")
    for m in acc_pattern.finditer(raw):
        acc_list.append(float(m.group(1).decode("ascii")))

    # comm=XX MB (↑YY MB ↓ZZ B)
    comm_pattern = re.compile(
        rb"comm=([\d.]+\s*(?:MB|KB|B|GB))\s*\("
        rb"(?:\xa1\xfc|\xe2\x86\x91)"
        rb"([\d.]+\s*(?:MB|KB|B|GB))\s*"
        rb"(?:\xa1\xfd|\xe2\x86\x93)"
        rb"([\d.]+\s*(?:MB|KB|B|GB))\)"
    )
    for m in comm_pattern.finditer(raw):
        comm_list.append(parse_size(m.group(1).decode("ascii")))
        ul_list.append(parse_size(m.group(2).decode("ascii")))
        dl_list.append(parse_size(m.group(3).decode("ascii")))

    # sim_dur=XX.XXs
    sim_pattern = re.compile(rb"sim_dur=([\d.]+)s")
    for m in sim_pattern.finditer(raw):
        sim_dur_list.append(float(m.group(1).decode("ascii")))

    # vclock=XX.XX s  or  vclock=XX.XX min
    vclock_pattern = re.compile(rb"vclock=([\d.]+)\s*(s|min)")
    for m in vclock_pattern.finditer(raw):
        val = float(m.group(1).decode("ascii"))
        unit = m.group(2).decode("ascii")
        if unit == "min":
            val *= 60
        vclock_list.append(val)

    return {
        "acc": acc_list,
        "comm": comm_list,
        "ul": ul_list,
        "dl": dl_list,
        "sim_dur": sim_dur_list,
        "vclock": vclock_list,
    }


# ---------------------------------------------------------------------------
# Parse metrics.json (for accuracy_niid, accuracy_noprefetch, accuracy)
# ---------------------------------------------------------------------------
def parse_metrics_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    acc_list = data.get("test_acc", [])
    # upload_cost / download_cost are in bytes
    ul_list = [x / (1024 * 1024) for x in data.get("upload_cost", [])]
    dl_list = [x / (1024 * 1024) for x in data.get("download_cost", [])]
    comm_list = [x / (1024 * 1024) for x in data.get("total_communication_cost", [])]
    sim_time_list = data.get("total_round_time_simulated", [])
    # Fallback: if simulated time is all zeros, use total_round_time
    if not sim_time_list or sum(sim_time_list) == 0:
        sim_time_list = data.get("total_round_time", [])

    return {
        "acc": acc_list,
        "comm": comm_list,
        "ul": ul_list,
        "dl": dl_list,
        "sim_dur": sim_time_list,
        "vclock": sim_time_list,
    }


# ---------------------------------------------------------------------------
# Experiment directory definitions
# ---------------------------------------------------------------------------
EXPERIMENTS = [
    # (directory, parse_func, file_name, naming_pattern_func)
    ("accuracy_client_selection", parse_runlog, "run.log", None),
    ("accuracy_threshold_v2", parse_runlog, "run.log", None),
    ("accuracy_topk_v2", parse_runlog, "run.log", None),
    ("accuracy_niid", parse_metrics_json, "metrics.json", None),
    ("accuracy_noprefetch", parse_metrics_json, "metrics.json", None),
    ("accuracy", parse_metrics_json, "metrics.json", None),
]


def infer_dataset_method(dir_name):
    """Infer dataset and method from directory name."""
    d = dir_name.lower()
    dataset = None
    method = None

    # Dataset
    if "cifar10" in d:
        dataset = "cifar10"
    elif "fashion_mnist" in d:
        dataset = "fashion_mnist"
    elif "mnist" in d:
        dataset = "mnist"

    # Method / configuration
    if "_cs_" in d:
        method = d.split("_cs_")[-1].split("/")[0]
    elif "threshold_pct_" in d:
        method = "threshold_" + d.split("threshold_pct_")[-1].split("/")[0]
    elif "topk_pct_" in d:
        method = "topk_" + d.split("topk_pct_")[-1].split("/")[0]
    elif "_union" in d:
        method = "union"
    elif "niid" in d or "accuracy_niid" in d:
        method = "niid"
    elif "noprefetch" in d or "accuracy_noprefetch" in d:
        method = "noprefetch"
    elif "accuracy/" in d or d.startswith("accuracy"):
        # Try to infer from parent path for accuracy/
        method = "baseline"

    return dataset, method


def main():
    results = []

    for dirname, parse_func, filename, _ in EXPERIMENTS:
        base = Path(dirname)
        if not base.exists():
            print(f"SKIP: {dirname} does not exist")
            continue

        # Find all experiment directories
        exp_dirs = []
        for root, dirs, files in os.walk(base):
            if filename in files:
                exp_dirs.append(root)

        print(f"{dirname}: found {len(exp_dirs)} experiments")

        for exp_dir in exp_dirs:
            file_path = Path(exp_dir) / filename
            try:
                data = parse_func(str(file_path))
            except Exception as e:
                print(f"  ERROR parsing {file_path}: {e}")
                continue

            dataset, method = infer_dataset_method(exp_dir)
            if dataset is None:
                continue

            n = len(data["acc"])
            if n == 0:
                continue

            # Also try to get config for more context
            config_path = Path(exp_dir) / "config.yaml"
            vote_mode = None
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        import yaml
                        cfg = yaml.safe_load(f)
                        if cfg and "global_mask_vote" in cfg:
                            vote_cfg = cfg["global_mask_vote"]
                            if isinstance(vote_cfg, dict):
                                vote_mode = vote_cfg.get("mode", "none")
                except Exception:
                    pass

            record = {
                "dir": dirname,
                "exp_dir": exp_dir,
                "dataset": dataset,
                "method": method,
                "vote_mode": vote_mode,
                "rounds": list(range(1, n + 1)),
                "acc": data["acc"],
                "final_acc": data["acc"][-1] if data["acc"] else 0,
                "total_upload": sum(data["ul"]),
                "total_download": sum(data["dl"]),
                "total_comm": sum(data["comm"]) if data["comm"] else sum(data["ul"]) + sum(data["dl"]),
                "total_sim_time": sum(data["sim_dur"]) if data["sim_dur"] else sum(data["vclock"]),
            }
            results.append(record)

    # Save
    output_dir = Path("accuracy_result")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "experiment_data.pkl", "wb") as f:
        pickle.dump(results, f)

    with open(output_dir / "experiment_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nSaved {len(results)} experiments to accuracy_result/experiment_data.pkl and .json")

    # Quick summary
    datasets = set(r["dataset"] for r in results)
    for ds in sorted(datasets):
        ds_results = [r for r in results if r["dataset"] == ds]
        methods = set(r["method"] for r in ds_results)
        print(f"  {ds}: {len(ds_results)} experiments, methods={sorted(methods)}")


if __name__ == "__main__":
    main()
