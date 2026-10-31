#!/usr/bin/env python3
"""
为 MNIST / CIFAR-10 / SVHN / Fashion-MNIST 生成 50 轮 adaptive voting 配置文件。

基线配置来源（已验证的 topk 配置）：
  - fashion_mnist: accuracy_baseline/adaptive/configs/config_baseline_fmnist_50r.yaml
  - mnist: accuracy_baseline/ours/result_fix_pro/20260605_mnist_topk_pct_0.1/config.yaml
  - cifar10: accuracy_baseline/ours/result_fix_pro/20260605_cifar10_topk_pct_0.7/config.yaml
  - svhn: accuracy_baseline/ours/result_fix_pro/20260622_svhn_sp0.5_topk0.7/config.yaml

生成策略：
  - baseline (topk): adaptive_vote.enabled = false
  - adaptive_cosine: strategy = cosine
  - adaptive_accuracy: strategy = accuracy
  - adaptive_consensus: strategy = consensus

输出目录：
  accuracy_baseline/adaptive/<dataset>/configs/
"""

import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"

BASE_CONFIGS = {
    "fashion_mnist": ADAPTIVE_DIR / "configs" / "config_baseline_fmnist_50r.yaml",
    "mnist": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260605_mnist_topk_pct_0.1" / "config.yaml",
    "cifar10": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260605_cifar10_topk_pct_0.7" / "config.yaml",
    "svhn": PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260622_svhn_sp0.5_topk0.7" / "config.yaml",
}

STRATEGIES = {
    "baseline": None,  # disabled
    "cosine": "cosine",
    "accuracy": "accuracy",
    "consensus": "consensus",
}

ADAPTIVE_VOTE_BLOCK = {
    "enabled": True,
    "strategy": "cosine",
    "config": {
        "cosine": {"topk_pct_start": 0.5, "topk_pct_end": 0.1},
        "accuracy": {
            "improvement_threshold": 0.005,
            "decay_factor": 0.9,
            "growth_factor": 1.1,
            "min_topk_pct": 0.05,
            "max_topk_pct": 0.9,
        },
        "consensus": {
            "high_consensus_threshold": 0.7,
            "low_consensus_threshold": 0.3,
            "high_threshold_pct": 0.7,
            "low_threshold_pct": 0.3,
        },
    },
}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path, cfg):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def main():
    for dataset, base_path in BASE_CONFIGS.items():
        if not base_path.exists():
            print(f"[WARN] 基线配置不存在，跳过: {base_path}")
            continue

        base_cfg = load_yaml(base_path)
        dataset_dir = ADAPTIVE_DIR / dataset
        configs_dir = dataset_dir / "configs"

        # 统一输出路径到数据集子目录
        base_cfg["output"] = base_cfg.get("output", {})
        base_cfg["output"]["results_dir"] = f"./accuracy_baseline/adaptive/{dataset}"
        base_cfg["output"]["model_dir"] = f"./accuracy_baseline/adaptive/{dataset}/models"
        base_cfg["output"]["viz_dir"] = f"./accuracy_baseline/adaptive/{dataset}/visualization"
        base_cfg["system"]["num_rounds"] = 50

        for name, strategy in STRATEGIES.items():
            cfg = yaml.safe_load(yaml.safe_dump(base_cfg))  # deep copy
            if strategy is None:
                cfg["adaptive_vote"] = {"enabled": False}
            else:
                cfg["adaptive_vote"] = yaml.safe_load(yaml.safe_dump(ADAPTIVE_VOTE_BLOCK))
                cfg["adaptive_vote"]["strategy"] = strategy

            out_path = configs_dir / f"config_{name}_{dataset}_50r.yaml"
            save_yaml(out_path, cfg)
            print(f"[OK] {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
