#!/usr/bin/env python3
"""
Quick test: CIFAR-10 with resnet20 + Merged + None
"""
import os
import sys
import yaml
import json
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import CKKSFedExperiment

def main():
    print("="*70)
    print("Quick Test: CIFAR-10 + ResNet20 + Merged + None")
    print("="*70)

    # Load base config
    with open("configs/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Override for CIFAR-10 with resnet20
    config["data"]["dataset"] = "cifar10"
    config["data"]["num_classes"] = 10
    config["data"]["iid"] = False
    config["data"]["alpha"] = 0.5
    config["model"]["name"] = "cnn"

    # System settings
    config["system"]["num_clients"] = 100
    config["system"]["num_rounds"] = 30
    config["system"]["num_epochs"] = 3
    config["system"]["batch_size"] = 64
    config["system"]["learning_rate"] = 0.001
    config["system"]["device"] = "cuda"
    config["system"]["client_sampling_rate"] = 0.3
    config["system"]["upload_difference"] = True

    # CKKS crypto
    config["ckks"]["poly_modulus_degree"] = 8192
    config["ckks"]["coeff_mod_bit_sizes"] = [60, 40, 40, 60]
    config["ckks"]["global_scale"] = 40
    config["ckks"]["slot_packing"] = True

    # Packing: Merged
    config["ckks"]["packing"]["strategy"] = "merged"
    config["ckks"]["packing"]["quant_bits"] = 16

    # No sparsification
    config["ckks"]["sparsification"]["strategy"] = "none"

    # No global mask vote
    config["global_mask_vote"]["mode"] = "none"

    # TEE disabled
    config["tee"]["enabled"] = False

    # Sticky client selection
    config["client_selection"]["strategy"] = "sticky"
    config["client_selection"]["sticky"]["group_size"] = None
    config["client_selection"]["sticky"]["change_num_base"] = 3

    # Output dir
    output_dir = "./compare_analysis/cifar10_resnet20_test"
    os.makedirs(output_dir, exist_ok=True)
    config["output"]["output_dir"] = output_dir

    # Save config to temp file (CKKSFedExperiment expects a path)
    config_path = os.path.join(output_dir, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"Config saved to: {config_path}")
    print(f"Model: {config['model']['name']}")
    print(f"Dataset: {config['data']['dataset']}")
    print(f"Packing: {config['ckks']['packing']['strategy']}")
    print(f"Vote mode: {config['global_mask_vote']['mode']}")
    print(f"Rounds: {config['system']['num_rounds']}")
    print("="*70)

    # Run experiment (pass config path)
    start = time.time()
    experiment = CKKSFedExperiment(config_path)
    results = experiment.run_experiment(use_encryption=True)
    elapsed = time.time() - start

    # Summary
    test_accs = results.get("test_accuracies", [])
    final_acc = test_accs[-1] if test_accs else 0
    comm_mb = results.get("total_communication_mb", 0)
    cts = results.get("total_ciphertexts", 0)

    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"Final Test Accuracy: {final_acc:.2f}%")
    print(f"Total Communication: {comm_mb:.1f} MB")
    print(f"Total Ciphertexts:   {cts}")
    print(f"Total Time:          {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("="*70)

    # Save results
    summary = {
        "model": "resnet20",
        "dataset": "cifar10",
        "packing": "merged",
        "vote_mode": "none",
        "final_test_acc": final_acc,
        "total_comm_mb": comm_mb,
        "total_ciphertexts": cts,
        "elapsed_sec": elapsed,
        "test_accuracies": test_accs,
    }
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to: {output_dir}/summary.json")

if __name__ == "__main__":
    main()
