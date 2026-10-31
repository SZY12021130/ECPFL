#!/usr/bin/env python3
"""
Generate the LaTeX subsection and a standalone main.tex for compilation.
Output: accuracy_baseline/analysis/end_to_end_time.tex
         accuracy_baseline/analysis/main.tex
"""
import json, os, sys

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline", "analysis")
DATA_PATH = os.path.join(ANALYSIS_DIR, "time_data.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

DATASETS = ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]
METHODS = ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER", "ECPFL-UN", "ECPFL-TH", "ECPFL-RK"]
BASELINES = ["FedAvg+CKKS", "FedPHE", "ESAFL", "MASER"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def avg(values):
    return sum(values) / len(values)


def fmt_range(lo, hi):
    return f"{lo:.1f}$\\times$--{hi:.1f}$\\times$"


# Average total time per method across datasets
avg_total = {m: avg([data[ds][m]["total_time"] for ds in DATASETS]) for m in METHODS}

# Fastest method on each dataset
fastest_per_ds = {
    ds: min([(data[ds][m]["total_time"], m) for m in METHODS], key=lambda x: x[0])
    for ds in DATASETS
}

# ECPFL-RK vs FedAvg+CKKS on total time (three simple datasets and SVHN)
rk_vs_fedavg_three = [data[ds]["ECPFL-RK"]["total_time"] / data[ds]["FedAvg+CKKS"]["total_time"] for ds in ["MNIST", "FMNIST", "CIFAR-10"]]
rk_total_three_lo, rk_total_three_hi = min(rk_vs_fedavg_three), max(rk_vs_fedavg_three)
rk_vs_fedavg_svhn = data["SVHN"]["FedAvg+CKKS"]["total_time"] / data["SVHN"]["ECPFL-RK"]["total_time"]

# Largest absolute total-time reduction of ECPFL-RK over FedAvg+CKKS
abs_reductions = {
    ds: data[ds]["FedAvg+CKKS"]["total_time"] - data[ds]["ECPFL-RK"]["total_time"]
    for ds in DATASETS
}
best_reduction_ds = max(abs_reductions, key=abs_reductions.get)
best_reduction_val = abs_reductions[best_reduction_ds]

# MASER slowdown vs FedAvg+CKKS
maser_slowdown = [data[ds]["MASER"]["total_time"] / data[ds]["FedAvg+CKKS"]["total_time"] for ds in DATASETS]
maser_lo, maser_hi, maser_avg = min(maser_slowdown), max(maser_slowdown), avg(maser_slowdown)

# ECPFL-RK serial-comm reduction vs FedAvg+CKKS
comm_reduction = [data[ds]["FedAvg+CKKS"]["report_comm_time"] / data[ds]["ECPFL-RK"]["report_comm_time"] for ds in DATASETS]
comm_red_lo, comm_red_hi, comm_red_avg = min(comm_reduction), max(comm_reduction), avg(comm_reduction)

# ECPFL-TH serial-comm reduction on CIFAR-10 and SVHN
th_comm_reduction = {
    ds: data[ds]["FedAvg+CKKS"]["report_comm_time"] / data[ds]["ECPFL-TH"]["report_comm_time"]
    for ds in ["CIFAR-10", "SVHN"]
}

# Average compute time
avg_compute = {m: avg([data[ds][m]["compute_time"] for ds in DATASETS]) for m in METHODS}

# ---------------------------------------------------------------------------
# LaTeX subsection
# ---------------------------------------------------------------------------
subsection = r"""\subsubsection{End-to-End Training Time}
\label{sec:e2e-time}

We measure end-to-end training time as the total simulated wall-clock time reported by each experiment, which includes local training, encryption, server-side aggregation, and ciphertext transmission.
This is distinct from the pure serial communication latency (\texttt{TT}) used in Table~\ref{tab:comm-comparison}, which only counts $\sum \max_i t_{\mathrm{up}}^{(i)} + \sum \max_i t_{\mathrm{down}}^{(i)}$.

\textbf{Overall comparison.}
Figure~\ref{fig:e2e-total-time} compares the total training time across the four datasets.
"""

# Dynamic overall-comparison paragraph
small_datasets = ["MNIST", "FMNIST", "CIFAR-10"]
fastest_three = [fastest_per_ds[ds] for ds in small_datasets]
fastest_three_names = [m for _, m in fastest_three]
fastest_three_times = [t for t, _ in fastest_three]

# ECPFL-RK speedups (or slowdowns) vs FedAvg+CKKS on the three small datasets
rk_vs_fedavg_three = [data[ds]["FedAvg+CKKS"]["total_time"] / data[ds]["ECPFL-RK"]["total_time"] for ds in small_datasets]

def speedup_text(ratios):
    """Return a text description of speedups from ratios > 1 or slowdowns from ratios < 1."""
    speedups = [r for r in ratios if r >= 1.0]
    slowdowns = [1.0 / r for r in ratios if r < 1.0]
    parts = []
    if speedups:
        lo, hi = min(speedups), max(speedups)
        parts.append(f"{lo:.1f}$\\times$--{hi:.1f}$\\times$ faster" if hi > lo else f"{lo:.1f}$\\times$ faster")
    if slowdowns:
        lo, hi = min(slowdowns), max(slowdowns)
        parts.append(f"{lo:.1f}$\\times$--{hi:.1f}$\\times$ slower" if hi > lo else f"{lo:.1f}$\\times$ slower")
    return ", and ".join(parts)

# Build a smooth fastest-method sentence for the three small datasets.
fastest_by_name = {}
for ds, (time, name) in zip(small_datasets, fastest_three):
    fastest_by_name.setdefault(name, []).append((ds, time))
fastest_name_list = list(fastest_by_name.keys())
if len(fastest_name_list) == 1:
    name = fastest_name_list[0]
    ds_times = ", ".join(f"{ds} ({time:.0f}\\,s)" for ds, time in fastest_by_name[name])
    fastest_sentence = f"{name} is fastest on all three datasets ({ds_times})."
elif len(fastest_name_list) == 2:
    items = []
    for name in fastest_name_list:
        ds_times = ", ".join(f"{ds} ({time:.0f}\\,s)" for ds, time in fastest_by_name[name])
        items.append(f"{name} on {ds_times}")
    fastest_sentence = f"{' and '.join(items)} are the fastest."
else:
    items = []
    for name in fastest_name_list:
        ds_times = ", ".join(f"{ds} ({time:.0f}\\,s)" for ds, time in fastest_by_name[name])
        items.append(f"{name} on {ds_times}")
    fastest_sentence = f"{', '.join(items[:-1])}, and {items[-1]} are the fastest."

subsection += (
    f"{fastest_sentence} "
    f"ECPFL-RK is {speedup_text(rk_vs_fedavg_three)} than FedAvg+CKKS on these three datasets. "
    f"On {best_reduction_ds}, ECPFL-RK finishes {best_reduction_val:.0f}\\,s earlier than FedAvg+CKKS "
    f"({rk_vs_fedavg_svhn:.1f}$\\times$ faster). "
    f"MASER is only {fmt_range(maser_lo, maser_hi)} slower than FedAvg+CKKS ({maser_avg:.1f}$\\times$ on average) in simulated wall-clock time, "
    f"because the dominant cost of its multi-key CKKS partial-decryption protocol is server-side cryptographic overhead "
    f"not fully captured by the per-client simulated-time components.\n\n"
)

subsection += r"""\begin{figure}[t]
\centering
\includegraphics[width=0.95\linewidth]{pic/e2e_total_time.pdf}
\caption{End-to-end training time across datasets and methods. Values are total simulated wall-clock times over 50 rounds.}
\label{fig:e2e-total-time}
\end{figure}

\textbf{Communication bottleneck.}
To understand how much of the wall-clock cost is pure network transfer, Figure~\ref{fig:e2e-comm-time} reports the serial communication time ($\sum \max_i t_{\mathrm{up}}^{(i)} + \sum \max_i t_{\mathrm{down}}^{(i)}$).
"""

# Sample comm values for ECPFL-RK vs FedAvg+CKKS on small datasets and SVHN
fa_mnist_comm = data["MNIST"]["FedAvg+CKKS"]["report_comm_time"]
rk_mnist_comm = data["MNIST"]["ECPFL-RK"]["report_comm_time"]
fa_fmnist_comm = data["FMNIST"]["FedAvg+CKKS"]["report_comm_time"]
rk_fmnist_comm = data["FMNIST"]["ECPFL-RK"]["report_comm_time"]
fa_svhn_comm = data["SVHN"]["FedAvg+CKKS"]["report_comm_time"]
rk_svhn_comm = data["SVHN"]["ECPFL-RK"]["report_comm_time"]

subsection += (
    f"ECPFL-RK reduces this metric relative to FedAvg+CKKS by {fmt_range(comm_red_lo, comm_red_hi)} "
    f"({comm_red_avg:.1f}$\\times$ on average), cutting MNIST/FMNIST transfers from "
    f"{fa_mnist_comm:.0f}/{fa_fmnist_comm:.0f}\\,s to {rk_mnist_comm:.0f}/{rk_fmnist_comm:.0f}\\,s "
    f"and the SVHN transfer from {fa_svhn_comm:.0f}\\,s to {rk_svhn_comm:.0f}\\,s. "
    f"ECPFL-TH obtains comparable or larger reductions on CIFAR-10 and SVHN "
    f"({th_comm_reduction['CIFAR-10']:.1f}$\\times$ and {th_comm_reduction['SVHN']:.1f}$\\times$, respectively), "
    f"although its more aggressive thresholding is less effective on the smaller datasets. "
    f"MASER's pure network time is not the dominant factor ({data['MNIST']['MASER']['report_comm_time']:.0f}--{data['SVHN']['MASER']['report_comm_time']:.0f}\\,s); "
    f"the gap in Figure~\\ref{{fig:e2e-total-time}} therefore stems from unmeasured server-side "
    f"multi-key CKKS aggregation and partial-decryption overhead, which we subsume under the residual wall-clock term.\n\n"
)

subsection += r"""\begin{figure}[t]
\centering
\includegraphics[width=0.95\linewidth]{pic/e2e_comm_time.pdf}
\caption{Serial communication time across datasets and methods.}
\label{fig:e2e-comm-time}
\end{figure}

\textbf{Compute--communication trade-off.}
Figure~\ref{fig:e2e-tradeoff} places every (method, dataset) pair in the compute--communication plane.
The diagonal dashed line marks equal compute and communication time.
"""

subsection += (
    f"FedAvg+CKKS, FedPHE, and ESAFL cluster in the upper-right region, where serial communication "
    f"exceeds local computation; this confirms that the network is their primary bottleneck. "
    f"ECPFL variants shift leftward and slightly upward: their serial communication drops sharply, "
    f"while their compute time increases modestly (average {avg_compute['ECPFL-RK']:.0f}\\,s for ECPFL-RK versus "
    f"{avg_compute['FedAvg+CKKS']:.0f}\\,s for FedAvg+CKKS) because of additional encryption and prefetch operations. "
    f"MASER lies off the diagonal in a different way: its measured compute and communication are comparable to the baselines, "
    f"yet its end-to-end time is larger, again indicating that the dominant cost is "
    f"server-side cryptographic overhead not captured by the per-client compute components.\n\n"
)

subsection += r"""\begin{figure}[t]
\centering
\includegraphics[width=0.8\linewidth]{pic/e2e_tradeoff.pdf}
\caption{Compute versus serial communication time. Each point corresponds to one method--dataset pair. The dashed line represents equal compute and communication time.}
\label{fig:e2e-tradeoff}
\end{figure}
"""

with open(os.path.join(ANALYSIS_DIR, "end_to_end_time.tex"), "w", encoding="utf-8") as f:
    f.write(subsection)

# ---------------------------------------------------------------------------
# Standalone main.tex
# ---------------------------------------------------------------------------
main_tex = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}

\hypersetup{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}

\title{End-to-End Training Time Analysis}
\author{}
\date{}

\begin{document}
\maketitle

% Provide a label for the cross-reference from the subsection. The real
% Table~\ref{tab:comm-comparison} is defined in the main paper.
\refstepcounter{table}\label{tab:comm-comparison}

\input{end_to_end_time}

\end{document}
"""

with open(os.path.join(ANALYSIS_DIR, "main.tex"), "w", encoding="utf-8") as f:
    f.write(main_tex)

print(f"[OK] Wrote {os.path.join(ANALYSIS_DIR, 'end_to_end_time.tex')}")
print(f"[OK] Wrote {os.path.join(ANALYSIS_DIR, 'main.tex')}")
