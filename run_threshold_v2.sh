#!/bin/bash
# Threshold mask vote 批量实验脚本 v2
# 使用 conda 环境直接路径，避免 conda run 并行冲突

export PYTHONIOENCODING=utf-8
export KMP_DUPLICATE_LIB_OK=TRUE
cd /e/GithubProjects/ckks_fed_robustness

PYTHON="D:/ProgramData/anaconda3/envs/concrete-env/python.exe"
DATE=$(date +%Y%m%d)
BASE_DIR="accuracy_threshold_v2"
mkdir -p "$BASE_DIR"

run_exp() {
    local dataset=$1
    local config_template=$2
    local pct=$3
    local out_name="${DATE}_${dataset}_threshold_pct_${pct}"
    local out_dir="${BASE_DIR}/${out_name}"
    local tmp_config="tmp_configs/_auto_${dataset}_threshold_${pct}.yaml"
    
    mkdir -p "$out_dir"
    
    python << PYEOF
import yaml
with open("$config_template", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
cfg["global_mask_vote"]["threshold_pct"] = $pct
cfg["output"]["results_dir"] = "$out_dir"
with open("$tmp_config", "w", encoding="utf-8") as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
PYEOF
    
    echo "[$(date '+%H:%M:%S')] 开始: $out_name"
    "$PYTHON" main.py --config "$tmp_config" --output-dir "$out_dir" > "${out_dir}/run.log" 2>&1
    echo "[$(date '+%H:%M:%S')] 完成: $out_name (exit=$?)"
}

# MNIST
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "mnist" "tmp_configs/config_mnist_threshold.yaml" "$pct"
    done
    echo "MNIST 全部完成"
) &
PID_MNIST=$!

# Fashion-MNIST
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "fashion_mnist" "tmp_configs/config_fashion_threshold.yaml" "$pct"
    done
    echo "Fashion-MNIST 全部完成"
) &
PID_FASHION=$!

# CIFAR-10
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "cifar10" "tmp_configs/config_cifar10_threshold.yaml" "$pct"
    done
    echo "CIFAR-10 全部完成"
) &
PID_CIFAR=$!

echo "三个数据集已并行启动: MNIST=$PID_MNIST Fashion=$PID_FASHION CIFAR=$PID_CIFAR"
wait $PID_MNIST
wait $PID_FASHION
wait $PID_CIFAR
echo "===== 全部 15 个实验已完成 ====="
ls -d ${BASE_DIR}/${DATE}_* | sort
