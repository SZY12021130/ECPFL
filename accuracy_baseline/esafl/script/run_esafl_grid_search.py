#!/usr/bin/env python3
"""
ESAFL 多配置批量测试脚本
为 CIFAR-10 / SVHN / Fashion-MNIST 测试不同 quant_bits + slots2 组合
MNIST 结果已很好，不再测试
"""
import os
import sys
import subprocess
import shutil
import re
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
MAIN_PY = os.path.join(PROJECT_ROOT, "main.py")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/esafl/config")
RESULT_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/esafl/test")

# 实验配置列表: (config_file, label)
EXPERIMENTS = [
    ("config_cifar10.yaml",     "cifar10"),
    ("config_fashionmnist.yaml", "fashionmnist"),
    ("config_svhn.yaml",         "svhn"),
]


def extract_final_acc(log_path):
    """从 experiment.log 提取最终测试准确率"""
    if not os.path.exists(log_path):
        return None
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # 找最后一行含 "测试准确率" 的
        matches = re.findall(r'测试准确率.*?([\d.]+)%', content)
        if matches:
            return float(matches[-1])
        matches = re.findall(r'准确率=([\d.]+)%', content)
        if matches:
            return float(matches[-1])
    except Exception:
        pass
    return None


def run_experiment(config_name, label):
    config_path = os.path.join(CONFIG_DIR, config_name)
    if not os.path.exists(config_path):
        print(f"[SKIP] Config not found: {config_path}")
        return False, None

    # 读取并修改配置：num_rounds = 5
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    original_rounds = cfg.get('system', {}).get('num_rounds', 50)
    cfg['system']['num_rounds'] = 5
    cfg['system']['save_interval'] = 1  # 每轮都保存以便查看

    # 写临时配置
    tmp_config = os.path.join(RESULT_DIR, f"_tmp_{label}.yaml")
    with open(tmp_config, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    print(f"\n{'='*70}")
    print(f"[START] {label}  (5 rounds)")
    print(f"{'='*70}")
    print(f"Config: {config_path}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    cmd = [
        sys.executable, MAIN_PY,
        "--config", tmp_config,
        "--output-dir", RESULT_DIR
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 清理临时配置
    if os.path.exists(tmp_config):
        os.remove(tmp_config)

    if result.returncode == 0:
        # 移动结果到带标签的子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        subdir = os.path.join(RESULT_DIR, f"experiment_{timestamp}_{label}")
        os.makedirs(subdir, exist_ok=True)
        for fname in ["config.yaml", "metrics.json", "experiment.log", "report.md"]:
            src = os.path.join(RESULT_DIR, fname)
            if os.path.exists(src):
                shutil.move(src, os.path.join(subdir, fname))
        # 提取最终准确率
        acc = extract_final_acc(os.path.join(subdir, "experiment.log"))
        print(f"[OK] {label} completed! Final acc: {acc}%")
        print(f"Results: {subdir}")
        print(f"Finished at: {end_time}")
        return True, acc
    else:
        print(f"[FAIL] {label} failed with exit code {result.returncode}")
        print(f"Finished at: {end_time}")
        return False, None


def main():
    print("=" * 70)
    print("ESAFL 多配置批量测试")
    print("=" * 70)
    print(f"共 {len(EXPERIMENTS)} 个实验，预计总耗时 ~{len(EXPERIMENTS)*1.5:.0f} 小时")
    print("=" * 70)

    os.makedirs(RESULT_DIR, exist_ok=True)
    results = []

    for i, (config_name, label) in enumerate(EXPERIMENTS, 1):
        print(f"\n\n>>> [{i}/{len(EXPERIMENTS)}] Running: {label}")
        ok, acc = run_experiment(config_name, label)
        results.append((label, ok, acc))

    # 汇总
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for label, ok, acc in results:
        status = "OK" if ok else "FAIL"
        acc_str = f"{acc:.2f}%" if acc is not None else "N/A"
        print(f"  [{status}] {label:30s} -> {acc_str}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
