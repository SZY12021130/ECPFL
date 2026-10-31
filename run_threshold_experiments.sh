#!/bin/bash
# Threshold mask vote 批量实验脚本
# 3数据集 × 5 threshold = 15个实验

export PYTHONIOENCODING=utf-8
export KMP_DUPLICATE_LIB_OK=TRUE
cd /e/GithubProjects/ckks_fed_robustness

DATE=$(date +%Y%m%d)
BASE_DIR="accuracy_threshold"
mkdir -p "$BASE_DIR"

# 通用带宽配置（共享）
BW_CONFIG="configs/bandwidth_config_50_8192_4096_0.2_uniform.json"

# 函数：运行单个实验
run_exp() {
    local dataset=$1
    local config_template=$2
    local pct=$3
    local out_name="${DATE}_${dataset}_threshold_pct_${pct}"
    local out_dir="${BASE_DIR}/${out_name}"
    local tmp_config="tmp_configs/_auto_${dataset}_threshold_${pct}.yaml"
    
    mkdir -p "$out_dir"
    
    # 动态修改配置文件
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
    
    if [ "$dataset" = "cifar10" ]; then
        conda run -n concrete-env python main.py --config "$tmp_config" --output-dir "$out_dir" > "${out_dir}/run.log" 2>&1
    else
        conda run -n concrete-env python main.py --config "$tmp_config" --output-dir "$out_dir" > "${out_dir}/run.log" 2>&1
    fi
    
    echo "[$(date '+%H:%M:%S')] 完成: $out_name"
}

# ===== MNIST 后台 =====
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "mnist" "tmp_configs/config_mnist_threshold.yaml" "$pct"
    done
    echo "MNIST 全部完成"
) &
PID_MNIST=$!

# ===== Fashion-MNIST 后台 =====
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "fashion_mnist" "tmp_configs/config_fashion_threshold.yaml" "$pct"
    done
    echo "Fashion-MNIST 全部完成"
) &
PID_FASHION=$!

# ===== CIFAR-10 后台 =====
(
    for pct in 0.1 0.3 0.5 0.7 0.9; do
        run_exp "cifar10" "tmp_configs/config_cifar10_threshold.yaml" "$pct"
    done
    echo "CIFAR-10 全部完成"
) &
PID_CIFAR=$!

echo "三个数据集实验已并行启动:"
echo "  MNIST PID: $PID_MNIST"
echo "  Fashion PID: $PID_FASHION"
echo "  CIFAR PID: $PID_CIFAR"
echo ""
echo "等待全部完成..."
wait $PID_MNIST
wait $PID_FASHION
wait $PID_CIFAR

echo ""
echo "===== 全部 15 个实验已完成 ====="
echo "结果目录:"
ls -d ${BASE_DIR}/${DATE}_* | sort
