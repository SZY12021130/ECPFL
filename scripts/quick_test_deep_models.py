#!/usr/bin/env python3
"""
快速测试深层模型在 CKKS 下的兼容性
验证梯度裁剪 + LayerwiseQuantizedPacking 是否能解决深层网络发散问题

Usage:
    python scripts/quick_test_deep_models.py --model cnn
    python scripts/quick_test_deep_models.py --model deepcnn
    python scripts/quick_test_deep_models.py --model vggnobn --rounds 5
"""

import os
import sys
import yaml
import argparse
import logging
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import CKKSFedExperiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_config(model_name: str, packing: str, rounds: int = 10,
                 grad_clip: bool = False, update_clip: bool = False,
                 num_epochs: int = 3, lr: float = 0.001) -> dict:
    """Build config for quick deep model test."""

    cfg = {
        "system": {
            "num_clients": 100,
            "num_rounds": rounds,
            "num_epochs": num_epochs,
            "batch_size": 64,
            "learning_rate": lr,
            "device": "cuda",
            "random_seed": 42,
            "run_plaintext_baseline": True,  # 同时跑明文基线对比
            "client_sampling_rate": 0.3,
            "upload_difference": True,
            "optimizer": {"name": "adam", "lr": lr, "momentum": 0.9},
            "lr_scheduler": {"enabled": False, "name": "step", "step_size": 10, "gamma": 0.5, "T_max": 30, "eta_min": 0.0},
            # ---- 梯度裁剪配置 ----
            "gradient_clipping": {
                "enabled": grad_clip,
                "max_norm": 1.0,
            },
            # ---- 更新裁剪配置 ----
            "update_clipping": {
                "enabled": update_clip,
                "method": "layerwise_mean",
                "clip_factor": 3.0,
            },
        },
        "data": {
            "dataset": "cifar10",
            "data_dir": "./data",
            "num_classes": 10,
            "iid": False,
            "alpha": 0.5,
        },
        "model": {
            "name": model_name,
            "dropout": 0.2,
            "hidden_dims": [256, 128],
            "width_mult": 1.0,
            "deepcnn_width": 32,
        },
        "ckks": {
            "poly_modulus_degree": 8192,
            "coeff_mod_bit_sizes": [60, 40, 40, 60],
            "global_scale": 1099511627776,
            "slot_packing": True,
            "packing": {"strategy": packing, "quant_bits": 16},
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
        },
        "ptopk": {
            "enable": False,
            "client_residual": {"enabled": False, "stale_gamma": 0.9, "decay_gamma": 0.5, "clip_tau": 0.0},
            "server_accumulator": {"enabled": False, "mode": "none", "sync_interval": 1, "momentum_beta": 0.9},
        },
        "blinding_mask": {"enabled": False, "mask_range": 1.0, "compensation_mode": "auto", "apply_mode": "post_topk"},
        "global_mask_vote": {"mode": "none", "union_threshold": 1, "threshold_pct": 0.05, "topk_count_k": 5},
        "esafl": {"enabled": False, "mode": "SIMULATION", "prpg_seed": 42},
        "tee": {"enabled": False, "compression": {"enabled": False, "sparsity_rate": 0.8}, "residual_strategy": {"mode": "decay", "decay_gamma": 0.9, "clip_tau": 0.0, "clip_window": 4}},
        "prefetch": {
            "enable_prefetch": False,
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
            "strategy": "random",
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
    return cfg


def run_test(model_name: str, packing: str, rounds: int,
             grad_clip: bool, update_clip: bool,
             num_epochs: int, lr: float):
    """Run a single quick test."""
    tag = f"{model_name}_{packing}_gc{int(grad_clip)}_uc{int(update_clip)}"
    logger.info(f"\n{'='*70}")
    logger.info(f"Quick Test: model={model_name} | packing={packing}")
    logger.info(f"  grad_clip={grad_clip} | update_clip={update_clip}")
    logger.info(f"  epochs={num_epochs} | lr={lr} | rounds={rounds}")
    logger.info(f"{'='*70}")

    cfg = build_config(model_name, packing, rounds, grad_clip, update_clip, num_epochs, lr)

    output_dir = os.path.join(project_root, "compare_analysis", "deep_model_test",
                              f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(output_dir, exist_ok=True)
    cfg["output"]["results_dir"] = output_dir

    config_path = os.path.join(output_dir, "config.yaml")
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    experiment = CKKSFedExperiment(config_path)

    # Run plaintext baseline first
    logger.info("Running plaintext baseline...")
    plain_results = experiment.run_experiment(use_encryption=False)

    # Run CKKS encrypted
    logger.info("Running CKKS encrypted...")
    ckks_results = experiment.run_experiment(use_encryption=True)

    # Compare
    plain_acc = plain_results.get('final_test_acc', 0)
    ckks_acc = ckks_results.get('final_test_acc', 0)
    plain_loss = plain_results.get('final_test_loss', 999)
    ckks_loss = ckks_results.get('final_test_loss', 999)

    logger.info(f"\n{'='*70}")
    logger.info(f"RESULTS: {tag}")
    logger.info(f"  Plaintext: acc={plain_acc:.2f}% | loss={plain_loss:.4f}")
    logger.info(f"  CKKS:      acc={ckks_acc:.2f}% | loss={ckks_loss:.4f}")
    logger.info(f"  Gap:       acc_diff={plain_acc - ckks_acc:.2f}% | loss_diff={ckks_loss - plain_loss:.4f}")

    if ckks_loss > 100 or ckks_acc < 15:
        logger.warning(f"  [DIVERGED] CKKS training diverged!")
    elif plain_acc - ckks_acc < 5:
        logger.info(f"  [SUCCESS] CKKS training stable with minimal accuracy loss!")
    else:
        logger.info(f"  [PARTIAL] CKKS training stable but with noticeable accuracy loss.")

    logger.info(f"{'='*70}\n")
    return {
        "tag": tag,
        "model": model_name,
        "packing": packing,
        "grad_clip": grad_clip,
        "update_clip": update_clip,
        "plain_acc": plain_acc,
        "plain_loss": plain_loss,
        "ckks_acc": ckks_acc,
        "ckks_loss": ckks_loss,
    }


def main():
    parser = argparse.ArgumentParser(description="Quick test deep models under CKKS")
    parser.add_argument("--model", default="cnn", choices=["cnn", "deepcnn", "vggnobn", "resnet20", "cnn_cifar"])
    parser.add_argument("--packing", default="layerwise_quantized", choices=["merged", "layerwise", "layerwise_quantized", "twotier", "crtstack"])
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--grad-clip", action="store_true", help="Enable gradient clipping")
    parser.add_argument("--update-clip", action="store_true", help="Enable update clipping")
    parser.add_argument("--all-combos", action="store_true", help="Test all (clip x packing) combinations")
    args = parser.parse_args()

    if args.all_combos:
        # Test matrix: 2 grad_clip x 2 update_clip x 2 packing
        results = []
        for grad_clip in [False, True]:
            for update_clip in [False, True]:
                for packing in ["merged", "layerwise_quantized"]:
                    try:
                        r = run_test(args.model, packing, args.rounds,
                                     grad_clip, update_clip, args.epochs, args.lr)
                        results.append(r)
                    except Exception as e:
                        logger.error(f"Test failed: {e}")
                        import traceback
                        traceback.print_exc()

        # Print summary table
        logger.info("\n" + "="*90)
        logger.info("SUMMARY TABLE")
        logger.info("="*90)
        logger.info(f"{'Model':<12} {'Packing':<20} {'GClip':<6} {'UClip':<6} {'Plain Acc':<10} {'CKKS Acc':<10} {'Status':<10}")
        logger.info("-"*90)
        for r in results:
            status = "OK" if r['ckks_acc'] > 15 and r['ckks_loss'] < 100 else "FAIL"
            logger.info(f"{r['model']:<12} {r['packing']:<20} {str(r['grad_clip']):<6} {str(r['update_clip']):<6} "
                       f"{r['plain_acc']:>8.2f}% {r['ckks_acc']:>8.2f}% {status:<10}")
        logger.info("="*90)
    else:
        run_test(args.model, args.packing, args.rounds,
                 args.grad_clip, args.update_clip, args.epochs, args.lr)


if __name__ == "__main__":
    main()
