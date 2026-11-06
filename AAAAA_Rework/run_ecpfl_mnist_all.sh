#!/bin/bash
# ECPFL MNIST 全量实验：先跑扩展性，再跑掉线率（RK-0.1、ζ=0.1）
# 必须在项目根目录执行：cd /e/GithubProjects/ckks_fed_robustness && bash AAAAA_Rework/run_ecpfl_mnist_all.sh
set -e
ROOT="."

bash "$ROOT/AAAAA_Rework/run_scalability_mnist.sh"
bash "$ROOT/AAAAA_Rework/run_dropout_mnist.sh"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] MNIST 扩展性 + 掉线率实验全部完成"
