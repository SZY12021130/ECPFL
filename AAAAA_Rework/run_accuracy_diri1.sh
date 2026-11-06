#!/usr/bin/env bash
# Dirichlet(1) 准确率重跑（修正 IID 控制变量）
# ECPFL: UN/TH/RK x mnist/svhn + UN/TH x fmnist/cifar10 = 10 runs
# ESAFL: mnist + svhn = 2 runs（fmnist/cifar10 由 noniid sweep a1 覆盖）
set -u
cd /e/GithubProjects/ckks_fed_robustness
PY=/d/ProgramData/anaconda3/envs/concrete-env/python.exe

run_ecpfl () {  # $1=config名
  echo "[START] ecpfl $1  $(date +%H:%M:%S)"
  $PY main_ecpfl.py --config AAAAA_Rework/ECPFL/config/accuracy_diri1/$1.yaml \
    --output-dir AAAAA_Rework/ECPFL/result/accuracy_diri1 \
    > AAAAA_Rework/ECPFL/result/accuracy_diri1/log_$1.txt 2>&1 \
    && echo "[OK] ecpfl $1" || echo "[FAIL] ecpfl $1"
}

run_esafl () {  # $1=dataset
  echo "[START] esafl $1  $(date +%H:%M:%S)"
  $PY main.py --config AAAAA_Rework/ESAFL/config/accuracy_diri1/$1.yaml \
    > AAAAA_Rework/ESAFL/result/accuracy_diri1/log_$1.txt 2>&1 \
    && echo "[OK] esafl $1" || echo "[FAIL] esafl $1"
}

echo "===== ECPFL Dirichlet(1) x10 ====="
for j in mnist_un mnist_th mnist_rk svhn_un svhn_th svhn_rk fmnist_un fmnist_th cifar10_un cifar10_th; do
  run_ecpfl $j
done

echo "===== ESAFL Dirichlet(1) x2 ====="
run_esafl mnist
run_esafl svhn

echo "ALL_DIRI1_DONE"
