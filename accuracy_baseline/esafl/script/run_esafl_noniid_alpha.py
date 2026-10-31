#!/usr/bin/env python3
"""
ESAFL Non-IID 实验脚本
在 FMNIST 和 CIFAR-10 上运行 alpha = 0.1, 0.5, 5, 10 的实验
（alpha=1 已运行完毕）
配置从已有 alpha=1 实验复制，仅修改 alpha 值。
结果保存到 noneiid_result 目录，命名格式: experiment_{timestamp}_{dataset}_alpha_{alpha}
"""
import os
import sys
import subprocess
import shutil
import yaml
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")

# 已有 alpha=1 实验的 config 路径（作为模板）
ALPHA1_CONFIGS = {
    "fashion_mnist": os.path.join(
        PROJECT_ROOT,
        "accuracy_baseline/esafl/noneiid_result/experiment_20260622_111118_fashion_mnist_alpha_1/config.yaml"
    ),
    "cifar10": os.path.join(
        PROJECT_ROOT,
        "accuracy_baseline/esafl/noneiid_result/experiment_20260622_114557_cifar10_alpha_1/config.yaml"
    ),
}

RESULT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/esafl/noneiid_result")

# 需要补充的 alpha 值
ALPHA_VALUES = [0.1, 0.5, 5, 10]


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


def run_single_experiment(dataset, alpha):
    """运行单个实验：复制 alpha=1 配置，修改 alpha，运行并保存结果"""
    template_path = ALPHA1_CONFIGS[dataset]
    cfg = load_config(template_path)

    # 修改 alpha
    cfg["data"]["alpha"] = alpha

    # 修改输出目录（指向 noneiid_result）
    cfg["output"]["results_dir"] = "accuracy_baseline/esafl/noneiid_result"

    # 生成临时配置文件
    alpha_str = str(alpha).replace(".", "_") if "." in str(alpha) else str(alpha)
    temp_config_name = f"temp_{dataset}_alpha_{alpha_str}.yaml"
    temp_config_path = os.path.join(RESULT_DIR, temp_config_name)
    save_config(cfg, temp_config_path)

    print(f"\n{'='*70}")
    print(f"[START] ESAFL | {dataset} | alpha={alpha}")
    print(f"{'='*70}")

    cmd = [
        sys.executable, MAIN_PY,
        "--config", temp_config_path,
        "--output-dir", RESULT_DIR,
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        # 将结果文件移动到带时间戳的子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        subdir = os.path.join(RESULT_DIR, f"experiment_{timestamp}_{dataset}_alpha_{alpha_str}")
        os.makedirs(subdir, exist_ok=True)
        for fname in ["config.yaml", "metrics.json", "experiment.log", "report.md"]:
            src = os.path.join(RESULT_DIR, fname)
            if os.path.exists(src):
                shutil.move(src, os.path.join(subdir, fname))
        print(f"\n[OK] ESAFL | {dataset} | alpha={alpha} -> {subdir}")
        # 清理临时配置
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)
        return True
    else:
        print(f"\n[FAIL] ESAFL | {dataset} | alpha={alpha} exit_code={result.returncode}")
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)
        return False


def main():
    print("=" * 70)
    print("ESAFL Non-IID Alpha Experiment Runner")
    print(f"Datasets: fashion_mnist, cifar10")
    print(f"Alpha values: {ALPHA_VALUES}")
    print(f"Result dir: {RESULT_DIR}")
    print("=" * 70)

    os.makedirs(RESULT_DIR, exist_ok=True)

    results = []
    for dataset in ["fashion_mnist", "cifar10"]:
        for alpha in ALPHA_VALUES:
            success = run_single_experiment(dataset, alpha)
            results.append((dataset, alpha, success))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for dataset, alpha, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {dataset} | alpha={alpha}")

    all_ok = all(s for _, _, s in results)
    print(f"\nOverall: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
