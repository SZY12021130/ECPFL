#!/bin/bash
# 等待当前 accuracy 批量（python 进程）全部退出后，自动启动 ESP 消融批量
cd "$(dirname "$0")/.." || exit 1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] watcher: waiting for current batch to finish..."
while tasklist //FI "IMAGENAME eq python.exe" 2>/dev/null | grep -qi "python.exe"; do
    sleep 60
done
echo "[$(date '+%Y-%m-%d %H:%M:%S')] watcher: batch finished, starting ablation in 30s..."
sleep 30
export KMP_DUPLICATE_LIB_OK=TRUE
bash AAAAA_Rework/run_ecpfl_ablation.sh
