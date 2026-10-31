#!/usr/bin/env python3
"""
为 ablation_result_pro 生成 6 组 ESP 消融实验配置。

- 数据集：SVHN
- 本地稀疏率 LS：0.5
- 01-04：global_mask_vote = union
- 05：global_mask_vote = topk (RK=0.7)
- 06：无稀疏 baseline
"""

from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "accuracy_baseline" / "ours" / "ablation_result"
DST_DIR = PROJECT_ROOT / "accuracy_baseline" / "ours" / "ablation_result_pro" / "configs"
DST_DIR.mkdir(parents=True, exist_ok=True)

EXPERIMENTS = [
    ("01_sparse_only",                 "01_sparse_only_fix",  "仅本地稀疏化 (sparsity=0.1) + union 投票"),
    ("02_sparse_residual",             "02_sparse_residual_fix", "稀疏化 + 残差补偿 + union 投票"),
    ("03_sparse_residual_decay",       "03_sparse_residual_decay_fix", "稀疏化 + 残差补偿 + 单轮衰减 + union 投票"),
    ("04_sparse_residual_decay_stale", "04_sparse_residual_decay_stale_fix", "稀疏化 + 残差补偿 + 单轮衰减 + 跨轮衰减 + union 投票"),
    ("05_esp_full",                    "05_esp_full", "完整 ESP (含投票 RK=0.7)"),
    ("06_no_sparse",                   "06_no_sparse", "无稀疏化 baseline"),
]


def find_config(exp_name: str) -> Path:
    exp_dir = SRC_DIR / exp_name
    candidates = list(exp_dir.glob("*/config.yaml"))
    if not candidates:
        raise FileNotFoundError(f"{exp_dir} 下没有 config.yaml")
    return candidates[0]


def main():
    for new_name, src_name, desc in EXPERIMENTS:
        src_cfg_path = find_config(src_name)
        with open(src_cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # 修改数据集
        cfg["data"]["dataset"] = "svhn"

        # 修改本地稀疏率
        if new_name != "06_no_sparse":
            cfg["ckks"]["sparsification"]["sparsity_rate"] = 0.5

        # 修改输出目录
        cfg["output"]["results_dir"] = f"accuracy_baseline/ours/ablation_result_pro/{new_name}"

        dst_path = DST_DIR / f"config_{new_name}.yaml"
        with open(dst_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"[Generated] {dst_path}  <- {src_cfg_path}")

    print("\n所有配置已生成到:", DST_DIR)


if __name__ == "__main__":
    main()
