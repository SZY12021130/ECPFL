#!/usr/bin/env python3
"""
极简深层模型 CKKS 兼容性测试 (1轮快速验证)
Usage:
    python scripts/quick_test_deep_models_minimal.py --model cnn
    python scripts/quick_test_deep_models_minimal.py --model deepcnn --grad-clip
"""

import os
import sys
import yaml
import argparse
import logging
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import CKKSFedExperiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_config(model_name: str, packing: str, grad_clip: bool, update_clip: bool) -> dict:
    return {
        "system": {
            "num_clients": 100,
            "num_rounds": 1,
            "num_epochs": 2,
            "batch_size": 64,
            "learning_rate": 0.0005,
            "device": "cpu",
            "random_seed": 42,
            "run_plaintext_baseline": False,
            "client_sampling_rate": 0.3,
            "upload_difference": True,
            "optimizer": {"name": "adam", "lr": 0.0005, "momentum": 0.9},
            "lr_scheduler": {"enabled": False},
            "gradient_clipping": {"enabled": grad_clip, "max_norm": 1.0},
            "update_clipping": {"enabled": update_clip, "method": "layerwise_mean", "clip_factor": 3.0},
        },
        "data": {"dataset": "cifar10", "data_dir": "./data", "num_classes": 10, "iid": False, "alpha": 0.5},
        "model": {"name": model_name, "dropout": 0.2, "hidden_dims": [256, 128], "width_mult": 1.0, "deepcnn_width": 32},
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
        "ptopk": {"enable": False},
        "blinding_mask": {"enabled": False},
        "global_mask_vote": {"mode": "none"},
        "esafl": {"enabled": False},
        "tee": {"enabled": False},
        "prefetch": {"enable_prefetch": False},
        "bandwidth": {"fedfetch_trace_path": "fedfetch_bandwidth.pkl", "base_dl_bw": 1024.0, "base_ul_bw": 512.0, "variance": 0.3, "distribution": "lognormal"},
        "metrics": {"compute_time": True, "communication_cost": True, "ciphertext_size": True, "expansion_ratio": True, "accuracy": True, "loss": True},
        "visualization": {"enabled": False},
        "output": {"results_dir": "./compare_analysis", "model_dir": "./history_models", "viz_dir": "./visualization", "save_interval": 999},
        "client_selection": {"strategy": "random", "sim_len": 64, "quan_threshold": 0.05, "selection_interval": 0},
    }


def run_test(model_name: str, packing: str, grad_clip: bool, update_clip: bool):
    tag = f"{model_name}_{packing}_gc{int(grad_clip)}_uc{int(update_clip)}"
    logger.info(f"\n[TEST] {tag}")
    cfg = build_config(model_name, packing, grad_clip, update_clip)
    out_dir = os.path.join(project_root, "compare_analysis", "deep_model_test", tag)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)
    cfg["output"]["results_dir"] = out_dir
    cfg_path = os.path.join(out_dir, "config.yaml")
    with open(cfg_path, 'w') as f:
        yaml.dump(cfg, f)
    experiment = CKKSFedExperiment(cfg_path)
    results = experiment.run_experiment(use_encryption=True)
    acc = results.get('final_test_acc', 0)
    loss = results.get('final_test_loss', 999)
    status = "OK" if loss < 100 and acc > 10 else "FAIL"
    logger.info(f"[RESULT] {tag}: acc={acc:.2f}% loss={loss:.4f} -> {status}")
    return {"tag": tag, "acc": acc, "loss": loss, "status": status}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="cnn")
    parser.add_argument("--packing", default="layerwise_quantized")
    parser.add_argument("--grad-clip", action="store_true")
    parser.add_argument("--update-clip", action="store_true")
    parser.add_argument("--matrix", action="store_true", help="Test matrix of all combinations")
    args = parser.parse_args()

    if args.matrix:
        models = ["cnn_cifar", "cnn", "deepcnn"]
        packings = ["merged", "layerwise_quantized"]
        results = []
        for model in models:
            for packing in packings:
                for gc in [False, True]:
                    for uc in [False, True]:
                        try:
                            r = run_test(model, packing, gc, uc)
                            results.append(r)
                        except Exception as e:
                            logger.error(f"FAIL {model}/{packing}/gc{gc}/uc{uc}: {e}")
                            results.append({"tag": f"{model}_{packing}_gc{gc}_uc{uc}", "acc": 0, "loss": 999, "status": "ERROR"})
        logger.info("\n" + "="*80)
        logger.info("SUMMARY")
        logger.info("="*80)
        for r in results:
            logger.info(f"  {r['tag']:<50s} acc={r['acc']:>6.2f}% loss={r['loss']:>8.4f} {r['status']}")
    else:
        run_test(args.model, args.packing, args.grad_clip, args.update_clip)


if __name__ == "__main__":
    main()
