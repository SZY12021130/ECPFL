#!/usr/bin/env python
"""
FedPHE 批量实验运行脚本
支持 MNIST, Fashion-MNIST, CIFAR-10
配置：50轮，50客户端，25参与，NON-IID(alpha=1)
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

# 配置
EXPERIMENTS = [
    {"dataset": "MNIST", "model": "lenet"},
    {"dataset": "FashionMNIST", "model": "cnn_fmnist"},
    {"dataset": "CIFAR10", "model": "resnet20"},
]

COMMON_ARGS = [
    "--epochs", "50",
    "--n_clients", "50",
    "--num_selected_clients", "25",
    "--split", "noniid",
    "--noniid_method", "dirichlet",
    "--alpha", "1",
    "--local_epochs", "3",
    "--batch-size", "64",
    "--lr", "0.001",
    "--seed", "42",
    "--enc", "True",
    "--algorithm", "ckks",
    "--isBatch", "True",
    "--cipher_count", "True",
    "--isSpars", "topk",
    "--topk", "0.1",
    "--isSelection", "True",
]

def run_experiment(dataset, model_name, date_str):
    print(f"\n{'='*60}")
    print(f"Starting experiment: {dataset} + {model_name}")
    print(f"{'='*60}\n")

    # 清理旧的数据缓存，确保重新生成数据划分
    data_dir = "data_dir"
    for fname in [f"{dataset}_train", f"{dataset}_test", f"{dataset}selected"]:
        fpath = os.path.join(data_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"Removed old cache: {fpath}")

    # 清理旧的日志
    log_dir = "log"
    log_file = os.path.join(log_dir, f"{dataset}.log")
    if os.path.exists(log_file):
        os.remove(log_file)

    result_dir = os.path.join("result", f"{date_str}_{dataset.lower()}_{model_name}")
    os.makedirs(result_dir, exist_ok=True)

    cmd = [
        sys.executable, "main.py",
        "--dataset", dataset,
        "--result_dir", result_dir,
    ] + COMMON_ARGS

    print(f"Command: {' '.join(cmd)}\n")
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd() + os.pathsep + env.get('PYTHONPATH', '')
    
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Experiment failed for {dataset}: {e}")
        return False

    print(f"\nExperiment completed for {dataset}. Results saved to {result_dir}\n")
    return True


def main():
    date_str = datetime.now().strftime('%Y%m%d')
    for exp in EXPERIMENTS:
        success = run_experiment(exp["dataset"], exp["model"], date_str)
        if not success:
            print(f"Skipping remaining experiments due to failure.")
            break

    print("\nAll experiments completed!")
    print(f"Results are in: result/")


if __name__ == "__main__":
    main()
