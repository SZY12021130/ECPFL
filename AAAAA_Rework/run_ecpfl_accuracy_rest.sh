#!/bin/bash
set -e
cd "$(dirname "$0")/.." || exit 1
for ds in fmnist cifar10 svhn; do
  for rule in un th rk; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Start ECPFL $ds $rule (sync-fixed)"
    python main_ecpfl.py --config AAAAA_Rework/ECPFL/config/accuracy/${ds}_${rule}.yaml --output-dir AAAAA_Rework/ECPFL/result/accuracy
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done ECPFL $ds $rule"
  done
done
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALL 9 EXPERIMENTS COMPLETE"
