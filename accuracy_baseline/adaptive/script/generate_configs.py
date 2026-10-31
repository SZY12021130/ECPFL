"""
生成 FMNIST 15 轮自适应投票实验配置。
"""
import os
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BASE_CONFIG_PATH = PROJECT_ROOT / "accuracy_baseline" / "ours" / "result_fix_pro" / "20260610_fashion_mnist_sp0.3_topk0.3" / "config.yaml"
OUT_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive" / "configs"


def make_base():
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 统一改为 15 轮
    cfg["system"]["num_rounds"] = 15

    # 输出目录改到 adaptive 下
    cfg["output"]["results_dir"] = "./accuracy_baseline/adaptive"
    cfg["output"]["model_dir"] = "./accuracy_baseline/adaptive/models"
    cfg["output"]["viz_dir"] = "./accuracy_baseline/adaptive/visualization"

    # 关闭可视化加快速度
    cfg["visualization"]["enabled"] = False

    return cfg


def dump(cfg, name):
    path = OUT_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, sort_keys=False, allow_unicode=True)
    print(f"[Saved] {path}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 静态 baseline（与原 ECPFL 相同，仅 15 轮）
    baseline = make_base()
    baseline["global_mask_vote"]["mode"] = "topk"
    baseline["global_mask_vote"]["topk_pct"] = 0.3
    baseline["adaptive_vote"] = {"enabled": False}
    dump(baseline, "config_baseline_fmnist_15r.yaml")

    # 2) 自适应：cosine
    cosine = make_base()
    cosine["global_mask_vote"]["mode"] = "topk"
    cosine["global_mask_vote"]["topk_pct"] = 0.3  # 起始值会被覆盖
    cosine["adaptive_vote"] = {
        "enabled": True,
        "strategy": "cosine",
        "config": {
            "cosine": {
                "topk_pct_start": 0.5,
                "topk_pct_end": 0.1,
            }
        },
    }
    dump(cosine, "config_adaptive_cosine_fmnist_15r.yaml")

    # 3) 自适应：accuracy
    accuracy = make_base()
    accuracy["global_mask_vote"]["mode"] = "topk"
    accuracy["global_mask_vote"]["topk_pct"] = 0.3
    accuracy["adaptive_vote"] = {
        "enabled": True,
        "strategy": "accuracy",
        "config": {
            "accuracy": {
                "improvement_threshold": 0.005,
                "decay_factor": 0.9,
                "growth_factor": 1.1,
                "min_topk_pct": 0.05,
                "max_topk_pct": 0.9,
            }
        },
    }
    dump(accuracy, "config_adaptive_accuracy_fmnist_15r.yaml")

    # 4) 自适应：consensus
    consensus = make_base()
    consensus["global_mask_vote"]["mode"] = "topk"  # 会被强制覆盖为 threshold
    consensus["global_mask_vote"]["topk_pct"] = 0.3
    consensus["adaptive_vote"] = {
        "enabled": True,
        "strategy": "consensus",
        "config": {
            "consensus": {
                "high_consensus_threshold": 0.7,
                "low_consensus_threshold": 0.3,
                "high_threshold_pct": 0.7,
                "low_threshold_pct": 0.3,
            }
        },
    }
    dump(consensus, "config_adaptive_consensus_fmnist_15r.yaml")


if __name__ == "__main__":
    main()
