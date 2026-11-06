#!/bin/bash
# ECPFL MNIST 扩展性实验：N=50/100/500/1000，RK-0.1、ζ=0.1
# 必须在项目根目录执行：cd /e/GithubProjects/ckks_fed_robustness && bash AAAAA_Rework/run_scalability_mnist.sh
set -e
ROOT="."
CONFIG_DIR="$ROOT/AAAAA_Rework/ECPFL/config/scalability"
RESULT_DIR="$ROOT/AAAAA_Rework/ECPFL/result/scalability"
PYTHON="/d/ProgramData/anaconda3/envs/concrete-env/python"

mkdir -p "$RESULT_DIR"

for N in 50 100 500 1000; do
    CONFIG="$CONFIG_DIR/scalability_N${N}.yaml"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 MNIST N=$N ..."
    $PYTHON "$ROOT/main_ecpfl.py" --config "$CONFIG" --output-dir "$RESULT_DIR" 2>&1 | tee "$RESULT_DIR/scalability_mnist_N${N}.log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] MNIST N=$N 完成"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 全部完成"
