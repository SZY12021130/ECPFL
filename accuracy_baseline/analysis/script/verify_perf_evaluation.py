"""
Extract raw values from each baseline/ECPFL report.md and document how the
per-round numbers in perf_evaluation.tex are derived.

Output: accuracy_baseline/analysis/perf_evaluation_methodology.md
"""
import re
import json
from pathlib import Path
from collections import OrderedDict

PROJECT_ROOT = Path(r"E:\GithubProjects\ckks_fed_robustness")
OUT_PATH = PROJECT_ROOT / "accuracy_baseline" / "analysis" / "perf_evaluation_methodology.md"


def parse_report(path: Path):
    text = path.read_text(encoding="utf-8")

    def fpat(pattern, default=None):
        m = re.search(pattern, text)
        return float(m.group(1).replace(",", "")) if m else default

    def ipat(pattern, default=None):
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else default

    data = {}
    data["model"] = (re.search(r"Model / 模型\s*\|\s*(\S+)", text).group(1)
                     if re.search(r"Model / 模型\s*\|\s*(\S+)", text) else "unknown")
    data["final_acc"] = fpat(r"Final Test Accuracy.*?\*\*([\d.]+)%")
    data["total_sim_time"] = fpat(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s")
    data["total_sim_comm_time"] = fpat(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s")

    up_m = re.search(r"Total Upload / 总上传量\s*\|\s*([\d.]+)\s*MB\s*/\s*([\d.]+)\s*s", text)
    if up_m:
        data["up_mb"] = float(up_m.group(1))
        data["up_time_sum"] = float(up_m.group(2))

    down_m = re.search(r"Total Download / 总下载量\s*\|\s*([\d.]+)\s*MB\s*/\s*([\d.]+)\s*s", text)
    if down_m:
        data["down_mb"] = float(down_m.group(1))
        data["down_time_sum"] = float(down_m.group(2))

    eff_m = re.search(r"Effective Download / 理论下载责任\s*\|\s*([\d.]+)\s*MB", text)
    if eff_m:
        data["effective_down_mb"] = float(eff_m.group(1))

    data["n_up"] = ipat(r"Total CT Blocks.*?\|\s*([\d,]+)\s*blocks")
    data["n_agg"] = ipat(r"Total Aggregated CTs.*?\|\s*([\d,]+)\s*blocks")
    data["ct_up_time"] = fpat(r"CT Upload Time / 密文上传时间\s*\|\s*([\d.]+)\s*s")
    data["ct_down_time"] = fpat(r"CT Download Time / 密文下载时间\s*\|\s*([\d.]+)\s*s")

    # Read metrics.json for additional per-client/per-round details
    metrics_path = path.parent / "metrics.json"
    data["n_agg_factor"] = 1
    data["num_ciphertexts_list"] = []
    if metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            agg_list = metrics.get("aggregated_ciphertexts", [])
            if len(agg_list) == 2 * ROUNDS and ROUNDS > 0:
                data["n_agg_factor"] = 2
            elif len(agg_list) == ROUNDS:
                data["n_agg_factor"] = 1
            data["num_ciphertexts_list"] = metrics.get("num_ciphertexts", [])
        except Exception:
            pass
    return data


EXPERIMENTS = OrderedDict([
    ("FedAvg+CKKS", {
        "MNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10",
        "SVHN": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn",
    }),
    ("FedPHE", {
        "MNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist",
        "FMNIST": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10",
        "SVHN": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn",
    }),
    ("ESAFL", {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn",
    }),
    ("MASER", {
        "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist",
        "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist",
        "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10",
        "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn",
    }),
    ("ECPFL-RK", {
        "MNIST": "accuracy_baseline/ours/result/mnist_rk",
        "FMNIST": "accuracy_baseline/ours/result/fashion_mnist_rk",
        "CIFAR-10": "accuracy_baseline/ours/result/cifar10_rk",
        "SVHN": "accuracy_baseline/ours/result/svhn_rk",
    }),
])

ROUNDS = 50


def baseline_per_round(r):
    """Baseline methods report CT Upload/Download Time as serial comm latency.
    The aggregated_ciphertexts metric may be double-logged depending on whether
    the main.py bug was fixed before the run. We use n_agg_factor detected from
    metrics.json to correct the raw total.
    """
    n_up = r["n_up"] / ROUNDS
    factor = r.get("n_agg_factor", 2)
    n_agg = (r["n_agg"] / float(factor)) / ROUNDS if r.get("n_agg") is not None else 0.0
    up_mb = r["up_mb"] / ROUNDS
    down_mb = r["down_mb"] / ROUNDS
    # Time columns are reported as 50-round totals; communication/count columns
    # remain per-round averages for consistency with the original table design.
    up_t = r.get("ct_up_time", r["up_time_sum"])
    down_t = r.get("ct_down_time", r["down_time_sum"])
    tt = r["total_sim_time"]
    return n_up, n_agg, up_mb, down_mb, up_t, down_t, tt


def ecpfl_per_round(r):
    """ECPFL-RK reports now include separate CT Upload/CT Download times and
    Total Simulated Time. The server aggregates one global ciphertext per selected
    residual block. The number of such aggregated blocks per round equals the number
    of ciphertext blocks each selected client uploads in that round (all selected
    clients upload the same blocks). We derive it from `num_ciphertexts` in
    metrics.json: average blocks per client per round.
    """
    n_up = r["n_up"] / ROUNDS
    num_list = r.get("num_ciphertexts_list", [])
    # Each entry is blocks uploaded by one selected client in one round.
    n_agg = (sum(num_list) / len(num_list)) if num_list else 1.0
    up_mb = r["up_mb"] / ROUNDS
    down_mb = r["effective_down_mb"] / ROUNDS

    # New reports provide direct per-direction serial wall-clock times.
    ct_up = r.get("ct_up_time")
    ct_down = r.get("ct_down_time")
    if ct_up is not None and ct_down is not None:
        up_t = ct_up
        down_t = ct_down
    else:
        # Fallback for older reports without separate CT times.
        comm = r["total_sim_comm_time"]
        total_mb = r["up_mb"] + r["effective_down_mb"]
        up_t = comm * r["up_mb"] / total_mb if total_mb else 0.0
        down_t = comm * r["effective_down_mb"] / total_mb if total_mb else 0.0

    # TT is the full 50-round Total Simulated Time (training + encryption + comm).
    tt = r["total_sim_time"]
    return n_up, n_agg, up_mb, down_mb, up_t, down_t, tt


def main():
    # Parse everything first
    parsed = OrderedDict()
    for method, datasets in EXPERIMENTS.items():
        parsed[method] = OrderedDict()
        for ds, rel in datasets.items():
            parsed[method][ds] = parse_report(PROJECT_ROOT / rel / "report.md")

    lines = []
    lines.append("# Performance Table Calculation Methodology")
    lines.append("")
    lines.append("This document shows exactly how every number in `perf_evaluation.tex` was derived.")
    lines.append("All source values come from the `report.md` file of each experiment.")
    lines.append("")
    lines.append("## Global settings")
    lines.append("")
    lines.append(f"- Communication rounds: **{ROUNDS}**")
    lines.append("- **Batches** and **Communication (MB)** values are **per-round averages** (raw total / 50).")
    lines.append("- **Time (s)** values are **50-round totals** (raw total, not divided by 50), so that small per-round download times are not rounded to 0.0.")
    lines.append("- Source paths are listed under each method.")
    lines.append("")
    lines.append("## Metric definitions")
    lines.append("")
    lines.append("| Symbol | Meaning | Source / formula |")
    lines.append("|---|---|---|")
    lines.append("| $N_{\\mathrm{up}}$ | Total upload ciphertext batches across all selected clients in all rounds | `Total CT Blocks` line in report.md |")
    lines.append("| $N_{\\mathrm{agg}}$ | Total server-side aggregated ciphertext batches broadcast | Baselines: `Total Aggregated CTs` line in report.md; we inspect `metrics.json` to determine whether it was logged once or twice per round and divide by that factor. ECPFL: the raw `Total Aggregated CTs` line is 0/absent. ECPFL selects `topk` residual blocks each round; the server aggregates one global ciphertext per selected block, so the number of broadcast aggregated blocks equals the average number of ciphertext blocks uploaded by each selected client per round (`num_ciphertexts` in metrics.json). |")
    lines.append("| Up (MB) | Total upload volume | `Total Upload` line, MB value |")
    lines.append("| Down (MB) | Total download volume | Baselines: `Total Download` MB. ECPFL: `Effective Download` MB, i.e. the residual fetch volume a selected client is responsible for after prefetching. |")
    lines.append("| Up (s) | Serial upload latency (50-round total) | Baselines: raw `CT Upload Time`. ECPFL-RK: raw `CT Upload Time` from the report. Older ECPFL reports without this line split `Total Simulated Comm Time` proportionally by upload volume. |")
    lines.append("| Down (s) | Serial download latency (50-round total) | Baselines: raw `CT Download Time`, or `Total Download` time if CT time is missing. ECPFL-RK: raw `CT Download Time` from the report. Older ECPFL reports without this line split `Total Simulated Comm Time` proportionally by effective download volume. |")
    lines.append("| TT (s) | Total simulated wall-clock time (50-round total) | Baselines: raw `Total Simulated Time`. ECPFL-RK: raw `Total Simulated Time` (training + encryption + communication). |")
    lines.append("")
    lines.append("## Method/dataset source paths")
    lines.append("")
    for method, datasets in EXPERIMENTS.items():
        lines.append(f"### {method}")
        for ds, rel in datasets.items():
            data = parsed[method][ds]
            lines.append(f"- **{ds}**: `{rel}`  → model = `{data['model']}`")
        lines.append("")

    lines.append("## Raw totals from reports")
    lines.append("")
    lines.append("| Dataset | Method | Model | $N_{\\mathrm{up}}$ | $N_{\\mathrm{agg}}$ | Up MB | Down MB | CT Up s | CT Down s | Total Comm s | TT s | Acc % |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for method, datasets in EXPERIMENTS.items():
        for ds, rel in datasets.items():
            r = parsed[method][ds]
            is_ecpfl = method.startswith("ECPFL")
            down = r.get("effective_down_mb", r.get("down_mb", 0.0))
            ct_up = r.get("ct_up_time")
            ct_down = r.get("ct_down_time")
            ct_up_str = f"{ct_up:.2f}" if ct_up is not None else "N/A"
            ct_down_str = f"{ct_down:.2f}" if ct_down is not None else "N/A"
            n_agg = r.get("n_agg")
            n_agg_str = str(n_agg) if n_agg is not None else "N/A"
            lines.append(
                f"| {ds} | {method} | `{r['model']}` | {r.get('n_up', 0)} | {n_agg_str} | "
                f"{r.get('up_mb', 0.0):.2f} | {down:.2f} | {ct_up_str} | {ct_down_str} | "
                f"{r['total_sim_comm_time']:.2f} | {r['total_sim_time']:.2f} | {r['final_acc']:.2f} |"
            )
    lines.append("")

    lines.append("## Values used in the table")
    lines.append("")
    lines.append("- **Batches** and **Communication (MB)**: divide raw totals by 50. Baseline $N_{\\mathrm{agg}}$ is divided by the detected logging factor (1 or 2) before averaging.")
    lines.append("- ECPFL $N_{\\mathrm{agg}}$ is the average number of ciphertext blocks uploaded by each selected client per round (`num_ciphertexts` in metrics.json), because the server aggregates one global ciphertext per selected residual block.")
    lines.append("- **Time (s)**: use raw 50-round totals (not divided by 50).")
    lines.append("")
    lines.append("| Dataset | Method | $N_{\\mathrm{up}}/N_{\\mathrm{agg}}$ | Up/Down MB | Up/Down/TT s |")
    lines.append("|---|---|---|---|")
    for method, datasets in EXPERIMENTS.items():
        for ds, rel in datasets.items():
            r = parsed[method][ds]
            if method.startswith("ECPFL"):
                vals = ecpfl_per_round(r)
            else:
                vals = baseline_per_round(r)
            n_up, n_agg, up_mb, down_mb, up_t, down_t, tt = vals
            lines.append(
                f"| {ds} | {method} | {n_up:.1f} / {n_agg:.1f} | "
                f"{up_mb:.1f} / {down_mb:.1f} | {up_t:.1f} / {down_t:.1f} / {tt:.1f} |"
            )
    lines.append("")

    lines.append("## Step-by-step verification per dataset")
    for ds in ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]:
        lines.append(f"\n### {ds}")
        for method, datasets in EXPERIMENTS.items():
            r = parsed[method][ds]
            lines.append(f"\n#### {method} ({r['model']})")
            lines.append(f"- Raw report path: `{datasets[ds]}`")
            lines.append(f"- Final accuracy: {r['final_acc']:.2f}%")
            lines.append(f"- $N_{{\\mathrm{{up}}}}$ total = {r.get('n_up', 0)} → per round = {r.get('n_up', 0)/ROUNDS:.1f}")
            if method.startswith("ECPFL"):
                raw_nagg = r.get('n_agg')
                raw_nagg_str = str(raw_nagg) if raw_nagg is not None else "absent"
                num_list = r.get('num_ciphertexts_list', [])
                blocks_per_client = sum(num_list) / len(num_list) if num_list else 1.0
                lines.append(f"- $N_{{\\mathrm{{agg}}}}$: raw report line is {raw_nagg_str}. ECPFL selects `topk` residual blocks each round; each selected client uploads {blocks_per_client:.1f} blocks. The server aggregates one global ciphertext per selected block, so broadcast aggregated blocks per round = {blocks_per_client:.1f}.")
            else:
                raw_nagg = r.get('n_agg', 0)
                factor = r.get('n_agg_factor', 2)
                lines.append(f"- $N_{{\\mathrm{{agg}}}}$ total = {raw_nagg} → raw per round = {raw_nagg/ROUNDS:.1f}; detected logging factor = {factor}, so unique aggregated batches per round = {raw_nagg/factor/ROUNDS:.1f}")
            if method.startswith("ECPFL"):
                lines.append(f"- Up volume total = {r['up_mb']:.2f} MB → per round = {r['up_mb']/ROUNDS:.1f} MB")
                lines.append(f"- Effective Down volume total = {r['effective_down_mb']:.2f} MB → per round = {r['effective_down_mb']/ROUNDS:.1f} MB")
                ct_up = r.get('ct_up_time')
                ct_down = r.get('ct_down_time')
                if ct_up is not None and ct_down is not None:
                    lines.append(f"- CT Upload Time total = {ct_up:.2f} s (used as 50-round total in table)")
                    lines.append(f"- CT Download Time total = {ct_down:.2f} s (used as 50-round total in table)")
                else:
                    total_mb = r['up_mb'] + r['effective_down_mb']
                    comm = r['total_sim_comm_time']
                    up_t = comm * r['up_mb'] / total_mb
                    down_t = comm * r['effective_down_mb'] / total_mb
                    lines.append(f"- Total simulated comm time = {comm:.2f} s")
                    lines.append(f"- Upload latency = {comm:.2f} × {r['up_mb']:.2f} / {total_mb:.2f} = {up_t:.2f} s (used as 50-round total in table)")
                    lines.append(f"- Download latency = {comm:.2f} × {r['effective_down_mb']:.2f} / {total_mb:.2f} = {down_t:.2f} s (used as 50-round total in table)")
            else:
                lines.append(f"- $N_{{\\mathrm{{agg}}}}$ total = {r.get('n_agg', 0)} → per round = {r.get('n_agg', 0)/ROUNDS:.1f}")
                lines.append(f"- Up volume total = {r['up_mb']:.2f} MB → per round = {r['up_mb']/ROUNDS:.1f} MB")
                lines.append(f"- Down volume total = {r['down_mb']:.2f} MB → per round = {r['down_mb']/ROUNDS:.1f} MB")
                ct_up = r.get('ct_up_time', r.get('up_time_sum', 0.0))
                ct_down = r.get('ct_down_time', r.get('down_time_sum', 0.0))
                lines.append(f"- CT Upload Time total = {ct_up:.2f} s (used as 50-round total in table)")
                lines.append(f"- CT Download Time total = {ct_down:.2f} s (used as 50-round total in table)")
            lines.append(f"- Total Simulated Time = {r['total_sim_time']:.2f} s (used as 50-round TT in the table)")

    lines.append("\n## Known inconsistencies / sanity checks")
    lines.append("")
    lines.append("1. **SVHN model consistency**: All SVHN methods now use `resnet32`. The new FedAvg+CKKS SVHN report (`experiment_20260629_140648_svhn`) supersedes the older `cnn` report (`experiment_20260616_115455_svhn`). All baseline reports currently exhibit double-logging of `aggregated_ciphertexts` (100 entries for 50 rounds), so $N_{\\mathrm{agg}}$ is divided by 2.")
    lines.append("2. **MASER download volume**: MASER reports a smaller downstream volume than FedAvg+CKKS because it broadcasts a plaintext model after server-side decryption; the bulk of its overhead is in server-side multi-key CKKS partial-decryption and is captured in TT, not in the comm-volume columns.")
    lines.append("3. **ECPFL-RK latency split**: The rerun reports contain direct `CT Upload Time` and `CT Download Time` lines, so UT and DT are taken directly from the report. TT is the report's `Total Simulated Time`. Older ECPFL reports without separate CT times estimated upload/download latencies by proportionally splitting `Total Simulated Comm Time` according to upload and effective-download volumes.")
    lines.append("4. **Time column scale**: The `Time (s)` columns (UT/DT/TT) are reported as 50-round totals, while Batches and Communication (MB) remain per-round averages. This avoids rounding very small per-round download times (e.g., ECPFL-RK on MNIST/FMNIST) to 0.0.\n5. **Sparse vs non-sparse upload counts**: On MNIST/FMNIST, FedAvg+CKKS has the largest $N_{\\mathrm{up}}$ (no sparsification), while FedPHE/ECPFL-RK have the smallest (most aggressive sparsification/packing). On CIFAR-10/SVHN the ranking is FedAvg+CKKS > ECPFL-RK > FedPHE/ESAFL/MASER, because ECPFL-RK uses topk=0.7 while the other sparse baselines use roughly 0.5 sparsity. ECPFL-RK's $N_{\\mathrm{agg}}$ equals the number of selected residual blocks (2/3/47/80), not 1.")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
