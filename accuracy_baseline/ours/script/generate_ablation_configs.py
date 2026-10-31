"""
生成 ESP 模块消融实验的 6 个配置文件（CIFAR-10, RK=0.7）。
实验配置：
  ① 仅稀疏化 (sparsity=0.5)
  ② + 残差补偿
  ③ + 单轮衰减 (decay_gamma=0.3)
  ④ + 跨轮衰减 (stale_gamma=0.5)
  ⑤ + 投票机制 (RK=0.7)
  ⑥ 无稀疏化 baseline
所有实验关闭预取，带宽配置保持一致。
"""
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BASE_CONFIG_PATH = PROJECT_ROOT / "accuracy_baseline" / "ours" / "config_svhn_sp0.5_topk0.7.yaml"
OUTPUT_DIR = PROJECT_ROOT / "accuracy_baseline" / "ours" / "script" / "ablation_configs"


def load_base_config() -> dict:
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def sync_ckks_ptopk(cfg: dict) -> None:
    """保持 ckks.ptopk 与顶层 ptopk 一致，避免配置文件中出现冲突。"""
    top = cfg.get("ptopk", {})
    if "ptopk" in cfg.get("ckks", {}):
        cfg["ckks"]["ptopk"] = top


def make_base_ablation_config(cfg: dict) -> dict:
    """公共基础：CIFAR-10 + ResNet-20 + 关闭预取 + 固定 RK=0.7 投票参数。"""
    cfg["data"]["dataset"] = "cifar10"
    cfg["data"]["alpha"] = 1.0
    cfg["model"]["name"] = "resnet20"

    # 固定稀疏化参数（除⑥外均使用 topk 0.5）
    cfg["ckks"]["sparsification"]["strategy"] = "topk"
    cfg["ckks"]["sparsification"]["sparsity_rate"] = 0.5

    # 投票参数固定为 RK=0.7，具体开关由 mode 控制
    cfg["global_mask_vote"]["mode"] = "none"
    cfg["global_mask_vote"]["threshold_pct"] = 0.5
    cfg["global_mask_vote"]["topk_count_k"] = 20
    cfg["global_mask_vote"]["topk_pct"] = 0.7

    # 关闭预取
    cfg["prefetch"]["enable_prefetch"] = False
    cfg["prefetch"]["max_prefetch_round"] = 0
    cfg["prefetch"]["warmup_round"] = 0

    # 统一输出目录前缀，后续会按实验覆盖
    cfg["output"]["results_dir"] = "accuracy_baseline/ours/result_fix_pro/ablation_cifar10_rk0.7"

    sync_ckks_ptopk(cfg)
    return cfg


def build_experiments():
    experiments = []

    # ① 仅稀疏化
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ptopk"]["enable"] = False
    cfg["ptopk"]["client_residual"]["enabled"] = False
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 1.0
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 1.0
    cfg["ckks"]["sparsification"]["strategy"] = "topk"
    experiments.append({"name": "01_sparse_only", "desc": "仅本地稀疏化 (sparsity=0.5)", "cfg": cfg})

    # ② + 残差补偿
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ptopk"]["enable"] = True
    cfg["ptopk"]["client_residual"]["enabled"] = True
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 1.0
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 1.0
    experiments.append({"name": "02_sparse_residual", "desc": "稀疏化 + 残差补偿", "cfg": cfg})

    # ③ + 单轮衰减 decay_gamma=0.3
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ptopk"]["enable"] = True
    cfg["ptopk"]["client_residual"]["enabled"] = True
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 0.3
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 1.0
    experiments.append({"name": "03_sparse_residual_decay", "desc": "稀疏化 + 残差补偿 + 单轮衰减", "cfg": cfg})

    # ④ + 跨轮衰减 stale_gamma=0.5
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ptopk"]["enable"] = True
    cfg["ptopk"]["client_residual"]["enabled"] = True
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 0.3
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 0.5
    experiments.append({"name": "04_sparse_residual_decay_stale", "desc": "稀疏化 + 残差补偿 + 单轮衰减 + 跨轮衰减", "cfg": cfg})

    # ⑤ + 投票机制 RK=0.7
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ptopk"]["enable"] = True
    cfg["ptopk"]["client_residual"]["enabled"] = True
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 0.3
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 0.5
    cfg["global_mask_vote"]["mode"] = "topk"
    experiments.append({"name": "05_esp_full", "desc": "完整 ESP (含投票 RK=0.7)", "cfg": cfg})

    # ⑥ 无稀疏化 baseline
    cfg = load_base_config()
    cfg = make_base_ablation_config(cfg)
    cfg["ckks"]["sparsification"]["strategy"] = "none"
    cfg["ptopk"]["enable"] = False
    cfg["ptopk"]["client_residual"]["enabled"] = False
    cfg["ptopk"]["client_residual"]["decay_gamma"] = 1.0
    cfg["ptopk"]["client_residual"]["stale_gamma"] = 1.0
    experiments.append({"name": "06_no_sparse", "desc": "无稀疏化 baseline", "cfg": cfg})

    return experiments


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    experiments = build_experiments()

    for exp in experiments:
        cfg = exp["cfg"]
        cfg["output"]["results_dir"] = f"accuracy_baseline/ours/result_fix_pro/ablation_cifar10_rk0.7/{exp['name']}"
        sync_ckks_ptopk(cfg)  # 确保 ckks.ptopk 与顶层 ptopk 一致
        out_path = OUTPUT_DIR / f"config_{exp['name']}.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"[Generated] {out_path}  --  {exp['desc']}")

    print(f"\n[DONE] 共生成 {len(experiments)} 个配置文件 -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
