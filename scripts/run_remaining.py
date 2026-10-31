"""
Run remaining experiments (crtstack_union, crtstack_threshold) after bug fix,
merge with existing 4 results, and regenerate summary plots.
"""
import os
import sys
import json
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.compare_analysis import (
    run_single_experiment, generate_summary_plots, generate_summary_table,
    logger, project_root
)
import numpy as np

# Mapping from experiments_registry.json (known good results)
REGISTRY_MAP = {
    "merged_none": "compare_analysis/experiment_20260519_141932",
    "merged_union": "compare_analysis/experiment_20260519_142623",
    "merged_threshold": "compare_analysis/experiment_20260519_143247",
    "crtstack_none": "compare_analysis/experiment_20260519_143844",
}


def load_existing_summary(tag: str, output_dir: str) -> dict:
    """Load summary from existing experiment metrics.json."""
    metrics_path = os.path.join(project_root, output_dir, "metrics.json")
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)

    packing, vote_mode = tag.split("_", 1)
    summary = {
        "tag": tag,
        "packing": packing,
        "vote_mode": vote_mode,
        "output_dir": os.path.join(project_root, output_dir),
        "elapsed_sec": 0.0,  # not needed for plots
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
    return summary


def main():
    logger.info("=" * 70)
    logger.info("Resuming Compare Analysis: load 4 existing + run 2 remaining")
    logger.info("=" * 70)

    compare_dir = os.path.join(project_root, "compare_analysis")
    os.makedirs(compare_dir, exist_ok=True)

    # Load existing 4 results
    all_results = []
    for tag, rel_dir in REGISTRY_MAP.items():
        summary = load_existing_summary(tag, rel_dir)
        all_results.append(summary)
        logger.info(f"Loaded existing: {tag} | acc={summary['final_test_acc']:.2f}%")

    # Run missing 2 experiments
    remaining = [("crtstack", "union"), ("crtstack", "threshold")]
    total = 6
    current = 5

    for packing, vote in remaining:
        try:
            result = run_single_experiment(packing, vote, current, total)
            all_results.append(result)
            current += 1
        except Exception as e:
            logger.error(f"Experiment {packing}_{vote} failed: {e}")
            import traceback
            traceback.print_exc()

    # Save raw results
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
