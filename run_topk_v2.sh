#!/usr/bin/env bash
# TopK 参数敏感性实验 v2
# 三个数据集并行，每个数据集内串行运行 5 个 topk_pct

PYTHON="D:/ProgramData/anaconda3/envs/concrete-env/python.exe"
OUTPUT_BASE="accuracy_topk_v2"
mkdir -p "$OUTPUT_BASE"

# topk_pct 取值
topk_pcts=(0.1 0.3 0.5 0.7 0.9)

# 数据集配置
declare -A datasets
datasets[mnist]="mnist"
datasets[fashion_mnist]="fashion_mnist"
datasets[cifar10]="cifar10"

# 每个数据集一个后台进程，内部串行
for ds_key in mnist fashion_mnist cifar10; do
  ds_name="${datasets[$ds_key]}"
  (
    for pct in "${topk_pcts[@]}"; do
      name="$(date +%Y%m%d)_${ds_name}_topk_pct_${pct}"
      cfg="tmp_configs/_auto_${ds_key}_topk_${pct}.yaml"
      logfile="$OUTPUT_BASE/${name}/run.log"
      
      echo "[$(date +%H:%M:%S)] Starting $ds_name topk_pct=$pct"
      mkdir -p "$OUTPUT_BASE/${name}"
      
      $PYTHON main.py --config "$cfg" --output-dir "$OUTPUT_BASE/${name}" > "$logfile" 2>&1
      
      echo "[$(date +%H:%M:%S)] Finished $ds_name topk_pct=$pct"
    done
  ) &
done

wait
echo "All topk experiments completed!"
