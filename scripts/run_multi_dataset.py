#!/usr/bin/env python3
"""
Multi-Dataset Comparison Experiments
=====================================

Run the same 6-config matrix (Merged/CRTStack × None/Union/Threshold)
across multiple datasets.  Results for each dataset are isolated under

    compare_analysis/<dataset_name>/
        ├── experiment_YYYYMMDD_HHMMSS_*/
        ├── all_results.json
        └── summary_plots/

Usage:
    python scripts/run_multi_dataset.py --datasets fashion_mnist cifar10
    python scripts/run_multi_dataset.py --datasets fashion_mnist
    python scripts/run_multi_dataset.py --all
"""

import os
import sys
import yaml
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List

import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import CKKSFedExperiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PACKING_STRATEGIES = ["merged", "crtstack", "layerwise_quantized"]
VOTE_MODES = ["none", "union", "threshold"]

# ------------------------------------------------------------------
# Per-dataset configurations (model + data hyper-parameters)
# ------------------------------------------------------------------
DATASET_PRESETS = {
    "mnist": {
        "data": {"dataset": "mnist", "num_classes": 10, "iid": False, "alpha": 1},
        "model": {"name": "lenet"},
    },
    "fashion_mnist": {
        "data": {"dataset": "fashion_mnist", "num_classes": 10, "iid": False, "alpha": 1},
        "model": {"name": "cnn_fmnist"},
    },
    "cifar10": {
        "data": {"dataset": "cifar10", "num_classes": 10, "iid": False, "alpha": 0.5},
        "model": {"name": "cnn_cifar"},
    },
    "cifar100": {
        "data": {"dataset": "cifar100", "num_classes": 100, "iid": False, "alpha": 0.5},
        "model": {"name": "mobilenetv2", "width_mult": 1.0},
    },
    "svhn": {
        "data": {"dataset": "svhn", "num_classes": 10, "iid": False, "alpha": 0.5},
        "model": {"name": "lenet"},
    },
    "emnist": {
        "data": {"dataset": "emnist", "num_classes": 47, "iid": False, "alpha": 1},
        "model": {"name": "lenet"},
    },
    "femnist": {
        "data": {"dataset": "femnist", "num_classes": 62, "iid": False, "alpha": 1},
        "model": {"name": "lenet"},
    },
}

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


def build_config(dataset_key: str, packing: str, vote_mode: str) -> Dict:
    """Build a config for a specific dataset + packing + vote_mode."""
    cfg = json.loads(json.dumps(BASE_CONFIG))
    preset = DATASET_PRESETS.get(dataset_key, {})

    # Apply dataset-specific overrides
    if "data" in preset:
        cfg["data"].update(preset["data"])
    if "model" in preset:
        cfg["model"].update(preset["model"])

    # Redirect output to dataset-specific subdirectory
    cfg["output"]["results_dir"] = f"./compare_analysis/{dataset_key}"

    # Set packing strategy
    if packing == "crtstack":
        cfg["ckks"]["packing"] = {
            "strategy": "crtstack",
            "crt_layers": 4,
            "crt_quant_bits": 8,
        }
    elif packing == "layerwise_quantized":
        cfg["ckks"]["packing"] = {
            "strategy": "layerwise_quantized",
            "quant_bits": 16,
        }
    else:
        cfg["ckks"]["packing"] = {"strategy": "merged", "quant_bits": 16}

    # Set voting mode
    cfg["global_mask_vote"]["mode"] = vote_mode

    return cfg


def run_single_experiment(dataset_key: str, packing: str, vote_mode: str, idx: int, total: int) -> Dict:
    """Run one experiment and return summary dict."""
    tag = f"{packing}_{vote_mode}"
    logger.info(f"\n{'='*70}")
    logger.info(f"[{idx}/{total}] Dataset={dataset_key} | Config={tag}")
    logger.info(f"{'='*70}")

    cfg = build_config(dataset_key, packing, vote_mode)

    # Write temp config
    tmp_dir = os.path.join(project_root, "tmp_configs")
    os.makedirs(tmp_dir, exist_ok=True)
    cfg_path = os.path.join(tmp_dir, f"multi_ds_{dataset_key}_{tag}.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)

    start = time.time()
    experiment = CKKSFedExperiment(config_path=cfg_path)
    result = experiment.run_experiment(use_encryption=True)
    elapsed = time.time() - start

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

    logger.info(f"Experiment {dataset_key}/{tag} completed in {elapsed:.1f}s")
    logger.info(f"  Final Acc: {summary['final_test_acc']:.2f}%")
    logger.info(f"  Total Comm: {summary['total_comm_mb']:.2f} MB")
    logger.info(f"  Output: {summary['output_dir']}")

    return summary


def run_dataset(dataset_key: str) -> List[Dict]:
    """Run the full 6-config matrix for one dataset."""
    experiments = [(p, v) for p in PACKING_STRATEGIES for v in VOTE_MODES]
    total = len(experiments)
    results = []

    for idx, (packing, vote) in enumerate(experiments, 1):
        try:
            result = run_single_experiment(dataset_key, packing, vote, idx, total)
            results.append(result)
        except Exception as e:
            logger.error(f"Experiment {dataset_key}/{packing}_{vote} failed: {e}")
            import traceback
            traceback.print_exc()

    # Save per-dataset results
    ds_dir = os.path.join(project_root, "compare_analysis", dataset_key)
    os.makedirs(ds_dir, exist_ok=True)
    results_path = os.path.join(ds_dir, "all_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {results_path}")

    return results


def generate_plots_for_dataset(dataset_key: str):
    """Call regenerate_plots logic for a specific dataset directory."""
    ds_dir = os.path.join(project_root, "compare_analysis", dataset_key)
    results_path = os.path.join(ds_dir, "all_results.json")

    if not os.path.exists(results_path):
        logger.warning(f"No results found for {dataset_key}, skipping plots.")
        return

    with open(results_path, "r") as f:
        all_results = json.load(f)

    if not all_results:
        logger.warning(f"Empty results for {dataset_key}, skipping plots.")
        return

    # Import plotting functions from regenerate_plots
    sys.path.insert(0, os.path.join(project_root, "scripts"))
    from regenerate_plots import (
        load_per_round,
        plot_accuracy_comparison,
        plot_train_loss_comparison,
        plot_communication_stacked_bar,
        plot_communication_per_round,
        plot_time_breakdown_per_round,
        plot_accuracy_vs_communication,
        plot_ciphertext_count,
        plot_summary_table_figure,
    )

    out_dir = os.path.join(ds_dir, "summary_plots")
    os.makedirs(out_dir, exist_ok=True)

    logger.info(f"Generating plots for {dataset_key} …")
    per_round = {}
    for res in all_results:
        per_round[res["tag"]] = load_per_round(res["output_dir"])

    plot_accuracy_comparison(all_results, per_round, out_dir)
    plot_train_loss_comparison(all_results, per_round, out_dir)
    plot_communication_stacked_bar(all_results, out_dir)
    plot_communication_per_round(all_results, per_round, out_dir)
    plot_time_breakdown_per_round(all_results, per_round, out_dir)
    plot_accuracy_vs_communication(all_results, per_round, out_dir)
    plot_ciphertext_count(all_results, out_dir)
    plot_summary_table_figure(all_results, out_dir)

    logger.info(f"Plots saved to {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run multi-dataset comparison experiments")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(DATASET_PRESETS.keys()),
        help="Which datasets to run (space-separated).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all supported datasets.",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Skip plot generation after experiments.",
    )
    args = parser.parse_args()

    if args.all:
        datasets = list(DATASET_PRESETS.keys())
    elif args.datasets:
        datasets = args.datasets
    else:
        parser.print_help()
        print("\nExample: python scripts/run_multi_dataset.py --datasets fashion_mnist")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("Multi-Dataset Comparison Experiments")
    logger.info(f"Datasets: {', '.join(datasets)}")
    logger.info("=" * 70)

    for ds in datasets:
        logger.info(f"\n{'#'*70}")
        logger.info(f"# DATASET: {ds}")
        logger.info(f"{'#'*70}")
        run_dataset(ds)
        if not args.skip_plots:
            generate_plots_for_dataset(ds)

    logger.info("\n" + "=" * 70)
    logger.info("All dataset experiments completed!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
