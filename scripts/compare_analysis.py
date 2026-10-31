"""
Compare Analysis: Merged vs CRTStack × Voting Modes
====================================================

Experiments:
  - Dataset: MNIST
  - Model: LeNet
  - Rounds: 30
  - Clients: 100
  - Sampling Rate: 0.3
  - OC: 1.3
  - Packing: merged | crtstack
  - Voting: none | union | threshold

Outputs:
  - compare_analysis/
    ├── experiment_YYYYMMDD_HHMMSS_merged_none/
    ├── experiment_YYYYMMDD_HHMMSS_merged_union/
    ├── experiment_YYYYMMDD_HHMMSS_merged_threshold/
    ├── experiment_YYYYMMDD_HHMMSS_crtstack_none/
    ├── experiment_YYYYMMDD_HHMMSS_crtstack_union/
    ├── experiment_YYYYMMDD_HHMMSS_crtstack_threshold/
    └── summary_plots/
        ├── accuracy_comparison.pdf
        ├── loss_comparison.pdf
        ├── communication_comparison.pdf
        └── summary_table.md
"""

import os
import sys
import yaml
import json
import time
import shutil
import logging
from datetime import datetime
from typing import Dict, List

import numpy as np

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Must import after path setup
from main import CKKSFedExperiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Experiment Matrix
# ------------------------------------------------------------------
PACKING_STRATEGIES = ["merged", "crtstack"]
VOTE_MODES = ["none", "union", "threshold"]

BASE_CONFIG = {
    "system": {
        "num_clients": 100,
        "num_rounds": 30,
        "num_epochs": 3,
        "batch_size": 64,
        "learning_rate": 0.001,
        "device": "cuda",
        "random_seed": 42,
        "run_plaintext_baseline": False,
        "client_sampling_rate": 0.3,
        "upload_difference": True,
        "optimizer": {"name": "adam", "lr": 0.001, "momentum": 0.9},
        "lr_scheduler": {"enabled": False, "name": "step", "step_size": 10, "gamma": 0.5, "T_max": 30, "eta_min": 0.0},
    },
    "data": {
        "dataset": "mnist",
        "data_dir": "./data",
        "num_classes": 10,
        "iid": False,
        "alpha": 1,
    },
    "model": {
        "name": "lenet",
        "hidden_dims": [256, 128],
        "dropout": 0.2,
        "width_mult": 1.0,
        "growth_rate": 12,
        "block_config": [6, 6, 6],
        "num_init_features": 24,
        "bn_size": 4,
        "drop_rate": 0.0,
    },
    "ckks": {
        "poly_modulus_degree": 8192,
        "coeff_mod_bit_sizes": [60, 40, 40, 60],
        "global_scale": 1099511627776,
        "slot_packing": True,
        "packing": {"strategy": "merged", "quant_bits": 16},
        "sparsification": {
            "strategy": "none",
            "sparsity_rate": 0.1,
            "batch_size": 4096,
            "seed": 42,
            "scoring_method": "l2_norm",
            "use_warmup_skip_sparse": False,
            "warmup_rounds": 2,
            "local_completion": {"enabled": False},
        },
        "ptopk": {
            "enable": False,
            "client_residual": {"enabled": False, "stale_gamma": 0.9, "decay_gamma": 0.5, "clip_tau": 0.0},
            "server_accumulator": {"enabled": False, "mode": "none", "sync_interval": 1, "momentum_beta": 0.9},
        },
    },
    "blinding_mask": {"enabled": False, "mask_range": 1.0, "compensation_mode": "auto", "apply_mode": "post_topk"},
    "global_mask_vote": {"mode": "none", "union_threshold": 1, "threshold_pct": 0.05, "topk_count_k": 5},
    "esafl": {"enabled": False, "mode": "SIMULATION", "prpg_seed": 42},
    "tee": {"enabled": False, "compression": {"enabled": False, "sparsity_rate": 0.8}, "residual_strategy": {"mode": "decay", "decay_gamma": 0.9, "clip_tau": 0.0, "clip_window": 4}},
    "prefetch": {
        "enable_prefetch": True,
        "max_prefetch_round": 3,
        "warmup_round": 1,
        "scheduler_beta": 1.0,
        "overcommitment": 1.3,
    },
    "bandwidth": {
        "fedfetch_trace_path": "fedfetch_bandwidth.pkl",
        "base_dl_bw": 1024.0,
        "base_ul_bw": 512.0,
        "variance": 0.3,
        "distribution": "lognormal",
    },
    "metrics": {
        "compute_time": True,
        "communication_cost": True,
        "ciphertext_size": True,
        "expansion_ratio": True,
        "accuracy": True,
        "loss": True,
        "communication_rounds": True,
        "dropout_rate": True,
        "cpu_utilization": True,
        "key_distribution_cost": True,
        "memory_usage": True,
    },
    "visualization": {"enabled": True, "save_format": "png", "dpi": 300, "figure_size": [10, 6], "style": "seaborn-v0_8-whitegrid"},
    "output": {
        "results_dir": "./compare_analysis",
        "model_dir": "./history_models",
        "viz_dir": "./visualization",
        "save_interval": 999,
    },
    "client_selection": {
        "strategy": "sticky",
        "sim_len": 64,
        "quan_threshold": 0.05,
        "selection_interval": 0,
        "max_k": None,
        "sticky": {"group_size": None, "change_num_base": 3, "enable_score": False, "score_decay": 0.9},
        "poc": {"d": None},
        "tifl": {"num_tiers": None},
        "haccs": {"num_clusters": None, "recluster_interval": 0},
        "oort": {"exploration_factor": 0.1, "util_time_alpha": 1.0},
        "fairness": {"enabled": False, "min_participation_ratio": 0.3},
    },
}


def build_config(packing: str, vote_mode: str) -> Dict:
    """Build experiment config for given packing strategy and voting mode."""
    cfg = json.loads(json.dumps(BASE_CONFIG))  # Deep copy

    # Set packing strategy
    if packing == "crtstack":
        cfg["ckks"]["packing"] = {
            "strategy": "crtstack",
            "crt_layers": 4,
            "crt_quant_bits": 8,
        }
    else:
        cfg["ckks"]["packing"] = {"strategy": "merged", "quant_bits": 16}

    # Set voting mode
    cfg["global_mask_vote"]["mode"] = vote_mode

    return cfg


def run_single_experiment(packing: str, vote_mode: str, idx: int, total: int) -> Dict:
    """Run a single experiment and return summary."""
    tag = f"{packing}_{vote_mode}"
    logger.info(f"\n{'='*70}")
    logger.info(f"[{idx}/{total}] Running experiment: {tag}")
    logger.info(f"{'='*70}")

    # Build config
    cfg = build_config(packing, vote_mode)

    # Write temp config
    tmp_dir = os.path.join(project_root, "tmp_configs")
    os.makedirs(tmp_dir, exist_ok=True)
    cfg_path = os.path.join(tmp_dir, f"compare_analysis_{tag}.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)

    # Run experiment
    start = time.time()
    experiment = CKKSFedExperiment(config_path=cfg_path)
    result = experiment.run_experiment(use_encryption=True)
    elapsed = time.time() - start

    # Extract key metrics
    m = experiment.metrics.get_metrics()
    summary = {
        "tag": tag,
        "packing": packing,
        "vote_mode": vote_mode,
        "output_dir": experiment.output_dir,
        "elapsed_sec": elapsed,
        "final_test_acc": m["test_acc"][-1] if m.get("test_acc") else 0.0,
        "final_test_loss": m["test_loss"][-1] if m.get("test_loss") else 0.0,
        "test_acc": m.get("test_acc", []),
        "test_loss": m.get("test_loss", []),
        "train_acc": m.get("train_acc", []),
        "train_loss": m.get("train_loss", []),
        "total_comm_mb": sum(m.get("total_communication_cost", [])) / (1024 * 1024),
        "upload_mb": sum(m.get("upload_cost", [])) / (1024 * 1024),
        "download_mb": sum(m.get("download_cost", [])) / (1024 * 1024),
        "avg_round_time": float(np.mean(m.get("total_round_time", [0]))),
        "num_ciphertexts": int(sum(m.get("num_ciphertexts", []))),
        "expansion_ratio": float(np.mean(m.get("expansion_ratio", [0]))),
    }

    logger.info(f"Experiment {tag} completed in {elapsed:.1f}s")
    logger.info(f"  Final Acc: {summary['final_test_acc']:.2f}%")
    logger.info(f"  Total Comm: {summary['total_comm_mb']:.2f} MB")
    logger.info(f"  Output: {summary['output_dir']}")

    return summary


def generate_summary_plots(all_results: List[Dict], output_dir: str):
    """Generate dark-theme neon-styled PDF plots comparing all experiments."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
    except ImportError:
        logger.warning("matplotlib not available, skipping plot generation")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Neon color palette for dark background
    colors = [
        '#FF0080', '#00FF80', '#00FFFF', '#FF8000',
        '#FF4040', '#8080FF', '#FFFF00', '#FF00FF',
        '#40FF40', '#FF8080', '#80FFFF', '#FF80FF',
    ]

    linestyles = {
        'merged_none': ('-', 'o'),
        'merged_union': ('-', 's'),
        'merged_threshold': ('-', '^'),
        'crtstack_none': ('--', 'D'),
        'crtstack_union': ('--', 'v'),
        'crtstack_threshold': ('--', 'p'),
    }

    # Helper to setup dark theme axes
    def setup_dark_axes(ax, title, xlabel, ylabel):
        ax.set_facecolor('#0d1117')
        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold', color='#c9d1d9')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold', color='#c9d1d9')
        ax.set_title(title, fontsize=13, fontweight='bold', color='#f0f6fc', pad=12)
        ax.tick_params(colors='#8b949e', labelsize=10)
        for spine in ax.spines.values():
            spine.set_color('#30363d')
            spine.set_linewidth(1.2)
        ax.grid(True, alpha=0.15, linestyle='--', color='#8b949e')

    # Compact legend inside plot with translucent background
    legend_kwargs = {
        'fontsize': 8.5,
        'frameon': True,
        'fancybox': True,
        'framealpha': 0.75,
        'facecolor': '#0d1117',
        'edgecolor': '#30363d',
        'labelcolor': '#c9d1d9',
        'ncol': 2,
        'columnspacing': 0.8,
        'handlelength': 2.0,
    }

    # --- Plot 1: Test Accuracy ---
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
    setup_dark_axes(ax, 'Test Accuracy Comparison\n(MNIST + LeNet, 100 Clients, 30R, C=0.3)',
                    'Communication Round', 'Test Accuracy (%)')
    for i, res in enumerate(all_results):
        tag = res["tag"]
        rounds = np.arange(1, len(res["test_acc"]) + 1)
        ls, marker = linestyles.get(tag, ('-', None))
        ax.plot(rounds, res["test_acc"],
                label=tag.replace('_', ' ').title(),
                color=colors[i % len(colors)], linestyle=ls, linewidth=2.2,
                marker=marker, markersize=5, markevery=3, alpha=0.95,
                markeredgecolor='#0d1117', markeredgewidth=0.8)
    ax.legend(loc='lower right', **legend_kwargs)
    ax.set_xlim(1, 30)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "accuracy_comparison.pdf"), format='pdf', dpi=300, facecolor='#0d1117')
    plt.savefig(os.path.join(output_dir, "accuracy_comparison.png"), dpi=300, facecolor='#0d1117')
    plt.close()
    logger.info(f"Saved accuracy_comparison.pdf")

    # --- Plot 2: Test Loss ---
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
    setup_dark_axes(ax, 'Test Loss Comparison\n(MNIST + LeNet, 100 Clients, 30R, C=0.3)',
                    'Communication Round', 'Test Loss')
    for i, res in enumerate(all_results):
        tag = res["tag"]
        rounds = np.arange(1, len(res["test_loss"]) + 1)
        ls, marker = linestyles.get(tag, ('-', None))
        ax.plot(rounds, res["test_loss"],
                label=tag.replace('_', ' ').title(),
                color=colors[i % len(colors)], linestyle=ls, linewidth=2.2,
                marker=marker, markersize=5, markevery=3, alpha=0.95,
                markeredgecolor='#0d1117', markeredgewidth=0.8)
    ax.legend(loc='upper right', **legend_kwargs)
    ax.set_xlim(1, 30)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "loss_comparison.pdf"), format='pdf', dpi=300, facecolor='#0d1117')
    plt.savefig(os.path.join(output_dir, "loss_comparison.png"), dpi=300, facecolor='#0d1117')
    plt.close()
    logger.info(f"Saved loss_comparison.pdf")

    # --- Plot 3: Communication Breakdown (Horizontal Bar with Glow) ---
    fig, ax = plt.subplots(figsize=(11, 6), facecolor='#0d1117')
    setup_dark_axes(ax, 'Total Communication Breakdown\n(MNIST + LeNet, 100 Clients, 30 Rounds)',
                    'Communication (MB)', '')

    tags = [r["tag"].replace('_', ' ').title() for r in all_results]
    upload_vals = [r["upload_mb"] for r in all_results]
    download_vals = [r["download_mb"] for r in all_results]
    y = np.arange(len(tags))
    height = 0.35

    bars1 = ax.barh(y - height/2, upload_vals, height, label='Upload',
                    color='#FF0080', alpha=0.85, edgecolor='none')
    bars2 = ax.barh(y + height/2, download_vals, height, label='Download',
                    color='#00FFFF', alpha=0.85, edgecolor='none')

    ax.set_yticks(y)
    ax.set_yticklabels(tags, fontsize=10, color='#c9d1d9')
    ax.invert_yaxis()
    ax.legend(fontsize=10, frameon=True, fancybox=True, framealpha=0.8,
              facecolor='#0d1117', edgecolor='#30363d', labelcolor='#c9d1d9',
              loc='lower right')

    for bar in bars1:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}', xy=(width, bar.get_y() + bar.get_height()/2),
                    xytext=(5, 0), textcoords="offset points", ha='left', va='center',
                    fontsize=9, color='#FF0080', fontweight='bold')
    for bar in bars2:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}', xy=(width, bar.get_y() + bar.get_height()/2),
                    xytext=(5, 0), textcoords="offset points", ha='left', va='center',
                    fontsize=9, color='#00FFFF', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "communication_comparison.pdf"), format='pdf', dpi=300, facecolor='#0d1117')
    plt.savefig(os.path.join(output_dir, "communication_comparison.png"), dpi=300, facecolor='#0d1117')
    plt.close()
    logger.info(f"Saved communication_comparison.pdf")

    # --- Plot 4: Accuracy vs Communication Trade-off ---
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
    setup_dark_axes(ax, 'Accuracy vs Communication Trade-off\n(MNIST + LeNet, 100 Clients, 30 Rounds)',
                    'Total Communication (MB)', 'Final Test Accuracy (%)')
    for i, res in enumerate(all_results):
        tag = res["tag"]
        ls, marker = linestyles.get(tag, ('-', None))
        ax.scatter(res["total_comm_mb"], res["final_test_acc"],
                   color=colors[i % len(colors)], s=220, marker=marker,
                   edgecolors='#0d1117', linewidths=2, zorder=5, alpha=0.95)
        ax.annotate(tag.replace('_', ' ').title(),
                    (res["total_comm_mb"], res["final_test_acc"]),
                    textcoords="offset points", xytext=(10, 5), fontsize=9,
                    fontweight='bold', color=colors[i % len(colors)])
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "accuracy_vs_communication.pdf"), format='pdf', dpi=300, facecolor='#0d1117')
    plt.savefig(os.path.join(output_dir, "accuracy_vs_communication.png"), dpi=300, facecolor='#0d1117')
    plt.close()
    logger.info(f"Saved accuracy_vs_communication.pdf")

    # --- Plot 5: Ciphertext Count (Dot+Lollipop Style) ---
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
    setup_dark_axes(ax, 'Total Ciphertext Count Comparison\n(30 Rounds, 100 Clients, Sampling 0.3)',
                    'Total Ciphertext Count', '')

    ct_counts = [r["num_ciphertexts"] for r in all_results]
    y_pos = np.arange(len(tags))
    ax.invert_yaxis()

    for i, (tag, count) in enumerate(zip(tags, ct_counts)):
        ax.plot([0, count], [i, i], color='#30363d', linewidth=2, zorder=1)
        ax.scatter(count, i, s=200, color=colors[i % len(colors)],
                   edgecolors='#0d1117', linewidths=2, zorder=3, alpha=0.95)
        ax.annotate(f'{int(count)}', xy=(count, i), xytext=(12, 0),
                    textcoords="offset points", ha='left', va='center',
                    fontsize=11, fontweight='bold', color=colors[i % len(colors)])

    ax.set_yticks(y_pos)
    ax.set_yticklabels(tags, fontsize=10, color='#c9d1d9')
    ax.set_xlim(0, max(ct_counts) * 1.25)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "ciphertext_count_comparison.pdf"), format='pdf', dpi=300, facecolor='#0d1117')
    plt.savefig(os.path.join(output_dir, "ciphertext_count_comparison.png"), dpi=300, facecolor='#0d1117')
    plt.close()
    logger.info(f"Saved ciphertext_count_comparison.pdf")


def generate_summary_table(all_results: List[Dict], output_dir: str):
    """Generate Markdown summary table."""
    lines = []
    lines.append("# Compare Analysis Summary: Merged vs CRTStack × Voting Modes")
    lines.append("")
    lines.append("## Experiment Settings")
    lines.append("- **Dataset**: MNIST")
    lines.append("- **Model**: LeNet")
    lines.append("- **Rounds**: 30")
    lines.append("- **Clients**: 100")
    lines.append("- **Sampling Rate**: 0.3")
    lines.append("- **Overcommitment (OC)**: 1.3")
    lines.append("- **Strategy**: Sticky Sampling")
    lines.append("")
    lines.append("## Results Summary")
    lines.append("")
    lines.append("| Config | Final Acc | Final Loss | Total Comm (MB) | Upload (MB) | Download (MB) | CT Count | Avg Round (s) | Time (s) |")
    lines.append("|--------|-----------|------------|-----------------|-------------|---------------|----------|---------------|----------|")

    for res in all_results:
        lines.append(
            f"| {res['tag'].replace('_', ' ').title()} | "
            f"{res['final_test_acc']:.2f}% | {res['final_test_loss']:.4f} | "
            f"{res['total_comm_mb']:.2f} | {res['upload_mb']:.2f} | {res['download_mb']:.2f} | "
            f"{res['num_ciphertexts']} | {res['avg_round_time']:.2f} | {res['elapsed_sec']:.1f} |"
        )

    lines.append("")
    lines.append("## Key Observations")
    lines.append("")

    # Find best accuracy
    best_acc = max(all_results, key=lambda x: x["final_test_acc"])
    lines.append(f"1. **Best Accuracy**: {best_acc['tag'].replace('_', ' ').title()} with {best_acc['final_test_acc']:.2f}%")

    # Find lowest communication
    best_comm = min(all_results, key=lambda x: x["total_comm_mb"])
    lines.append(f"2. **Lowest Communication**: {best_comm['tag'].replace('_', ' ').title()} with {best_comm['total_comm_mb']:.2f} MB")

    # Compare merged vs crtstack
    merged_results = [r for r in all_results if r["packing"] == "merged"]
    crt_results = [r for r in all_results if r["packing"] == "crtstack"]

    if merged_results and crt_results:
        avg_merged_comm = np.mean([r["total_comm_mb"] for r in merged_results])
        avg_crt_comm = np.mean([r["total_comm_mb"] for r in crt_results])
        savings = (avg_merged_comm - avg_crt_comm) / avg_merged_comm * 100
        lines.append(f"3. **CRTStack Communication Savings**: {savings:.1f}% (avg across voting modes)")

        avg_merged_acc = np.mean([r["final_test_acc"] for r in merged_results])
        avg_crt_acc = np.mean([r["final_test_acc"] for r in crt_results])
        acc_diff = avg_crt_acc - avg_merged_acc
        lines.append(f"4. **CRTStack Accuracy Impact**: {acc_diff:+.2f}pp (avg across voting modes)")

    lines.append("")
    lines.append("## Note")
    lines.append("This is an ESAFL simulation experiment. The server-side decrypt-re-encrypt overhead is not counted in the metrics. "
                 "The communication and accuracy data reflect the actual protocol behavior.")

    table_path = os.path.join(output_dir, "summary_table.md")
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Saved summary_table.md")


def main():
    logger.info("=" * 70)
    logger.info("Compare Analysis: Merged vs CRTStack × Voting Modes")
    logger.info("=" * 70)

    # Ensure compare_analysis directory exists
    compare_dir = os.path.join(project_root, "compare_analysis")
    os.makedirs(compare_dir, exist_ok=True)

    # Build experiment list
    experiments = []
    for packing in PACKING_STRATEGIES:
        for vote in VOTE_MODES:
            experiments.append((packing, vote))

    total = len(experiments)
    all_results = []

    for idx, (packing, vote) in enumerate(experiments, 1):
        try:
            result = run_single_experiment(packing, vote, idx, total)
            all_results.append(result)
        except Exception as e:
            logger.error(f"Experiment {packing}_{vote} failed: {e}")
            import traceback
            traceback.print_exc()

    # Save raw results JSON
    results_path = os.path.join(compare_dir, "all_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved all_results.json")

    # Generate summary plots
    plot_dir = os.path.join(compare_dir, "summary_plots")
    if all_results:
        generate_summary_plots(all_results, plot_dir)
        generate_summary_table(all_results, plot_dir)

    logger.info("\n" + "=" * 70)
    logger.info("All experiments completed!")
    logger.info(f"Results saved to: {compare_dir}")
    logger.info(f"Summary plots: {plot_dir}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
