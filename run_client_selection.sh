#!/usr/bin/env bash
# 客户端选择策略对比实验
# 串行运行，避免内存不足

PYTHON="D:/ProgramData/anaconda3/envs/concrete-env/python.exe"
OUTPUT_BASE="accuracy_client_selection"
mkdir -p "$OUTPUT_BASE"

STRATEGIES=(random sticky sketch_clustering poc tifl haccs oort)
VOTE_PCTS=(mnist:0.1 fashion_mnist:0.3 cifar10:0.7)

for entry in "${VOTE_PCTS[@]}"; do
  ds="${entry%%:*}"
  vote_pct="${entry##*:}"
  
  echo "========================================"
  echo "Dataset: $ds | Vote: topk($vote_pct)"
  echo "========================================"
  
  for strategy in "${STRATEGIES[@]}"; do
    name="$(date +%Y%m%d)_${ds}_vote_${vote_pct}_cs_${strategy}"
    cfg="tmp_configs/_auto_${ds}_vote_${vote_pct}_cs_${strategy}.yaml"
    logfile="$OUTPUT_BASE/${name}/run.log"
    
    echo "[$(date +%H:%M:%S)] Starting $ds + $strategy"
    mkdir -p "$OUTPUT_BASE/${name}"
    
    $PYTHON main.py --config "$cfg" --output-dir "$OUTPUT_BASE/${name}" > "$logfile" 2>&1
    
    # 提取结果
    rounds=$(grep -c "acc=" "$logfile" 2>/dev/null)
    acc=$(grep "acc=" "$logfile" 2>/dev/null | tail -1 | sed -n 's/.*acc=\([0-9.]*\)%.*/\1/p')
    echo "[$(date +%H:%M:%S)] Finished $ds + $strategy | rounds=$rounds/50 | acc=${acc:-N/A}"
  done
done

echo ""
echo "All client selection experiments completed!"
