#!/bin/bash
# FMNIST 批量调优实验
# 用法: bash scripts/run_fmnist_tuning.sh

export KMP_DUPLICATE_LIB_OK="TRUE"
cd "$(dirname "$0")/.."

# 使用 cnn_fmnist 模型，20轮
python scripts/hyperparameter_tuning.py \
    --dataset fashion_mnist \
    --model cnn_fmnist \
    --rounds 20 \
    2>&1 | tee scripts/tuning_results/fmnist_run.log

echo "FMNIST 实验完成!"
