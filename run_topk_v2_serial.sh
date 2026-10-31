#!/usr/bin/env bash
# TopK 参数敏感性实验 v2 - 串行版本（避免内存不足）

PYTHON="D:/ProgramData/anaconda3/envs/concrete-env/python.exe"
OUTPUT_BASE="accuracy_topk_v2"
mkdir -p "$OUTPUT_BASE"

topk_pcts=(0.1 0.3 0.5 0.7 0.9)
datasets=("mnist" "fashion_mnist" "cifar10")

for ds in "${datasets[@]}"; do
  for pct in "${topk_pcts[@]}"; do
    name="$(date +%Y%m%d)_${ds}_topk_pct_${pct}"
    cfg="tmp_configs/_auto_${ds}_topk_${pct}.yaml"
    logfile="$OUTPUT_BASE/${name}/run.log"
    
    # 如果已完成则跳过
    if [ -f "$logfile" ]; then
      rounds=$(grep -c "通信汇总" "$logfile" 2>/dev/null)
      if [ "$rounds" -ge 50 ]; then
        echo "SKIP $ds topk_pct=$pct (already done)"
        continue
      fi
    fi
    
    echo "[$(date +%H:%M:%S)] Starting $ds topk_pct=$pct"
    mkdir -p "$OUTPUT_BASE/${name}"
    
    $PYTHON main.py --config "$cfg" --output-dir "$OUTPUT_BASE/${name}" > "$logfile" 2>&1
    
    echo "[$(date +%H:%M:%S)] Finished $ds topk_pct=$pct"
  done
done

echo "All topk experiments completed!"
