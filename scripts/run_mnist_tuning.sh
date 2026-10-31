#!/bin/bash
# MNIST 批量调优实验
# 用法: bash scripts/run_mnist_tuning.sh

export KMP_DUPLICATE_LIB_OK="TRUE"
cd "$(dirname "$0")/.."

# 使用 lenet 模型，20轮
python scripts/hyperparameter_tuning.py \
    --dataset mnist \
    --model lenet \
    --rounds 20 \
    2>&1 | tee scripts/tuning_results/mnist_run.log

echo "MNIST 实验完成!"
