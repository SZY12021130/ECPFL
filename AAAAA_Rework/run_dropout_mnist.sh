#!/bin/bash
# ECPFL MNIST 掉线率敏感性实验：d0/d10/d20/d30/d40，RK-0.1、ζ=0.1
# 必须在项目根目录执行：cd /e/GithubProjects/ckks_fed_robustness && bash AAAAA_Rework/run_dropout_mnist.sh
set -e
ROOT="."
CONFIG_DIR="$ROOT/AAAAA_Rework/ECPFL/config/dropout"
RESULT_DIR="$ROOT/AAAAA_Rework/ECPFL/result/dropout"
PYTHON="/d/ProgramData/anaconda3/envs/concrete-env/python"

mkdir -p "$RESULT_DIR"

for D in 0 10 20 30 40; do
    CONFIG="$CONFIG_DIR/dropout_d${D}.yaml"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 MNIST 掉线率 d$D ..."
    $PYTHON "$ROOT/main_ecpfl.py" --config "$CONFIG" --output-dir "$RESULT_DIR" 2>&1 | tee "$RESULT_DIR/dropout_mnist_d${D}.log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] MNIST 掉线率 d$D 完成"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 全部完成"
