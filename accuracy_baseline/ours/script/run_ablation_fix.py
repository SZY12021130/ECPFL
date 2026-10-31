#!/usr/bin/env python3
"""
串行重新运行 ESP 消融实验 01-06（SVHN 版本）。

- 读取 accuracy_baseline/ours/ablation_result_pro/configs/config_<name>.yaml 作为模板
- 01-04 的 global_mask_vote.mode 改为 union
- 05 保持 topk（RK=0.7），06 保持 none（无稀疏化）
- 所有实验强制关闭预取
- 输出目录固定为 accuracy_baseline/ours/ablation_result_pro/<name>_fix
"""

import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ABLATION_RESULT_PRO = PROJECT_ROOT / "accuracy_baseline" / "ours" / "ablation_result_pro"
CONFIG_FIX_DIR = Path(__file__).resolve().parent / "ablation_configs_fix"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
PYTHON = sys.executable

UNION_EXPERIMENTS = {"01_sparse_only", "02_sparse_residual", "03_sparse_residual_decay", "04_sparse_residual_decay_stale"}

EXPERIMENTS = [
    {"name": "01_sparse_only",                 "desc": "仅本地稀疏化 (sparsity=0.5) + union 投票"},
    {"name": "02_sparse_residual",             "desc": "稀疏化 + 残差补偿 + union 投票"},
    {"name": "03_sparse_residual_decay",       "desc": "稀疏化 + 残差补偿 + 单轮衰减 + union 投票"},
    {"name": "04_sparse_residual_decay_stale", "desc": "稀疏化 + 残差补偿 + 单轮衰减 + 跨轮衰减 + union 投票"},
    {"name": "05_esp_full",                    "desc": "完整 ESP (含投票 RK=0.7)"},
    {"name": "06_no_sparse",                   "desc": "无稀疏化 baseline"},
]


def find_existing_config(exp_name: str) -> Path:
    cfg_path = ABLATION_RESULT_PRO / "configs" / f"config_{exp_name}.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {cfg_path}")
    return cfg_path


def make_fixed_config(exp_name: str) -> Path:
    src_cfg = find_existing_config(exp_name)
    with open(src_cfg, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 01-04 使用 union 全局掩码投票；05/06 保持原有 mode
    gmv = cfg.setdefault("global_mask_vote", {})
    old_mode = gmv.get("mode", "none")
    if exp_name in UNION_EXPERIMENTS:
        gmv["mode"] = "union"
        print(f"[FIX] {exp_name}: global_mask_vote.mode {old_mode} -> union")
    else:
        print(f"[KEEP] {exp_name}: global_mask_vote.mode = {old_mode}")

    # 强制关闭预取
    prefetch = cfg.setdefault("prefetch", {})
    prefetch["enable_prefetch"] = False
    prefetch["max_prefetch_round"] = 0
    prefetch["warmup_round"] = 0
    print(f"[FIX] {exp_name}: prefetch 已强制关闭")

    # 同步更新配置文件里的 results_dir（虽然 --output-dir 会覆盖）
    cfg["output"]["results_dir"] = f"accuracy_baseline/ours/ablation_result_pro/{exp_name}_fix"

    CONFIG_FIX_DIR.mkdir(parents=True, exist_ok=True)
    fix_cfg_path = CONFIG_FIX_DIR / f"config_{exp_name}.yaml"
    with open(fix_cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"[SAVED] {fix_cfg_path}")
    return fix_cfg_path


def run_experiment(exp: dict) -> bool:
    exp_name = exp["name"]
    fix_cfg_path = make_fixed_config(exp_name)
    output_dir = ABLATION_RESULT_PRO / f"{exp_name}_fix"

    print("\n" + "=" * 70)
    print(f"[START] {exp_name}: {exp['desc']}")
    print(f"[CONFIG] {fix_cfg_path}")
    print(f"[OUTPUT] {output_dir}")
    print("=" * 70)

    cmd = [
        PYTHON, str(MAIN_SCRIPT),
        "--config", str(fix_cfg_path),
        "--output-dir", str(output_dir),
    ]
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print(f"[SUCCESS] {exp_name} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {exp_name} 失败: {e}")
        return False


def main():
    if not MAIN_SCRIPT.exists():
        raise FileNotFoundError(f"找不到主程序: {MAIN_SCRIPT}")

    results = []
    for exp in EXPERIMENTS:
        success = run_experiment(exp)
        results.append((exp["name"], success))

    print("\n" + "=" * 70)
    print("[SUMMARY] 消融实验修复执行汇总")
    print("=" * 70)
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {name:<35s} {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
