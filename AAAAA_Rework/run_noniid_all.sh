#!/usr/bin/env bash
# Non-IID 批量实验：ESAFL (fmnist+cifar10 x a{0.1,0.5,1,5,10}) + ECPFL-RK (fmnist+cifar10 x 5)
# 串行执行（单 GPU），日志与配置同目录。
set -u
cd /e/GithubProjects/ckks_fed_robustness
PY=/d/ProgramData/anaconda3/envs/concrete-env/python.exe
A="a0.1 a0.5 a1 a5 a10"

echo "===== ESAFL Non-IID: fmnist x 5 ====="
for a in $A; do
  echo "[START] esafl fmnist $a  $(date +%H:%M:%S)"
  $PY main.py --config AAAAA_Rework/ESAFL/config/noniid/noniid_fmnist_$a.yaml \
    > AAAAA_Rework/ESAFL/result/noniid/log_fmnist_$a.txt 2>&1 \
    && echo "[OK] esafl fmnist $a" || echo "[FAIL] esafl fmnist $a"
done

echo "===== ESAFL Non-IID: cifar10 x 5 ====="
for a in $A; do
  echo "[START] esafl cifar10 $a  $(date +%H:%M:%S)"
  $PY main.py --config AAAAA_Rework/ESAFL/config/noniid/noniid_cifar10_$a.yaml \
    > AAAAA_Rework/ESAFL/result/noniid/log_cifar10_$a.txt 2>&1 \
    && echo "[OK] esafl cifar10 $a" || echo "[FAIL] esafl cifar10 $a"
done

echo "===== ECPFL-RK Non-IID: fmnist x 5 ====="
for a in $A; do
  echo "[START] ecpfl fmnist rk $a  $(date +%H:%M:%S)"
  $PY main_ecpfl.py --config AAAAA_Rework/ECPFL/config/noniid/noniid_fmnist_rk_$a.yaml \
    --output-dir AAAAA_Rework/ECPFL/result/noniid \
    > AAAAA_Rework/ECPFL/result/noniid/log_fmnist_rk_$a.txt 2>&1 \
    && echo "[OK] ecpfl fmnist rk $a" || echo "[FAIL] ecpfl fmnist rk $a"
done

echo "===== ECPFL-RK Non-IID: cifar10 x 5 ====="
for a in $A; do
  echo "[START] ecpfl cifar10 rk $a  $(date +%H:%M:%S)"
  $PY main_ecpfl.py --config AAAAA_Rework/ECPFL/config/noniid/noniid_cifar10_rk_$a.yaml \
    --output-dir AAAAA_Rework/ECPFL/result/noniid \
    > AAAAA_Rework/ECPFL/result/noniid/log_cifar10_rk_$a.txt 2>&1 \
    && echo "[OK] ecpfl cifar10 rk $a" || echo "[FAIL] ecpfl cifar10 rk $a"
done

echo "ALL_NONIID_DONE"
