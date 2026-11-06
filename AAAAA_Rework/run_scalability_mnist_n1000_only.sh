#!/bin/bash
# ECPFL MNIST 扩展性实验：仅 N=1000（logp=45 修复参数超限），RK-0.1、ζ=0.1
# 必须在项目根目录执行：cd /e/GithubProjects/ckks_fed_robustness && bash AAAAA_Rework/run_scalability_mnist_n1000_only.sh
set -e
ROOT="."
CONFIG_DIR="$ROOT/AAAAA_Rework/ECPFL/config/scalability"
RESULT_DIR="$ROOT/AAAAA_Rework/ECPFL/result/scalability"
PYTHON="/d/ProgramData/anaconda3/envs/concrete-env/python"

mkdir -p "$RESULT_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始 MNIST N=1000 ..."
$PYTHON "$ROOT/main_ecpfl.py" --config "$CONFIG_DIR/scalability_N1000.yaml" --output-dir "$RESULT_DIR" 2>&1 | tee "$RESULT_DIR/scalability_mnist_N1000.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MNIST N=1000 完成"
