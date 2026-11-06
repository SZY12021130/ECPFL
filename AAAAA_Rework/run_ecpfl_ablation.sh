#!/bin/bash
set -e
cd "$(dirname "$0")/.." || exit 1
for v in esp_only ls_off rf_off prd_off crd_off; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Start ECPFL ablation fmnist $v"
    python main_ecpfl.py --config AAAAA_Rework/ECPFL/config/ablation/fmnist_abl_${v}.yaml --output-dir AAAAA_Rework/ECPFL/result/ablation
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done ECPFL ablation fmnist $v"
done
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALL 5 ABLATION EXPERIMENTS COMPLETE"
