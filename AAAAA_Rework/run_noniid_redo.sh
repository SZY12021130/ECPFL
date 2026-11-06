#!/usr/bin/env bash
# Non-IID 重跑：
#  (a) 并发事故 OOM 崩溃的 6 个 ESAFL run
#  (b) 数据集名 bug 秒败的 5 个 ECPFL-RK fmnist run（已修复 fashion_mnist）
set -u
cd /e/GithubProjects/ckks_fed_robustness
PY=/d/ProgramData/anaconda3/envs/concrete-env/python.exe

esafl () {  # $1=数据集 $2=alpha名
  echo "[START] esafl $1 $2  $(date +%H:%M:%S)"
  $PY main.py --config AAAAA_Rework/ESAFL/config/noniid/noniid_$1_$2.yaml \
    > AAAAA_Rework/ESAFL/result/noniid/log_$1_$2.txt 2>&1 \
    && echo "[OK] esafl $1 $2" || echo "[FAIL] esafl $1 $2"
}

ecpfl () {  # $1=数据集 $2=alpha名
  echo "[START] ecpfl $1 rk $2  $(date +%H:%M:%S)"
  $PY main_ecpfl.py --config AAAAA_Rework/ECPFL/config/noniid/noniid_$1_rk_$2.yaml \
    --output-dir AAAAA_Rework/ECPFL/result/noniid \
    > AAAAA_Rework/ECPFL/result/noniid/log_$1_rk_$2.txt 2>&1 \
    && echo "[OK] ecpfl $1 rk $2" || echo "[FAIL] ecpfl $1 rk $2"
}

echo "===== Non-IID redo: ESAFL x6 ====="
esafl fmnist a1
esafl fmnist a5
esafl fmnist a10
esafl cifar10 a0.1
esafl cifar10 a0.5
esafl cifar10 a1

echo "===== Non-IID redo: ECPFL-RK fmnist x5 ====="
ecpfl fmnist a0.1
ecpfl fmnist a0.5
ecpfl fmnist a1
ecpfl fmnist a5
ecpfl fmnist a10

echo "ALL_NONIID_REDO_DONE"
