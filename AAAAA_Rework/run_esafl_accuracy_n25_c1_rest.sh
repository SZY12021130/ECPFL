#!/bin/bash
set -e
cd "$(dirname "$0")/.." || exit 1
for ds in fmnist cifar10 svhn; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Start ESAFL $ds n=4096 25clients sampling=1.0"
    python main.py --config AAAAA_Rework/ESAFL/config/accuracy_n25_c1/${ds}.yaml
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done ESAFL $ds"
done
