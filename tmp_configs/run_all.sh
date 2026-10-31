#!/bin/bash
set -e
PY="/d/ProgramData/anaconda3/envs/concrete-env/python.exe"

echo "========================================"
echo "1/8: CIFAR-10 alpha=5 Mutual"
echo "========================================"
$PY main.py --config tmp_configs/cifar10_a5_mutual.yaml

echo ""
echo "========================================"
echo "2/8: CIFAR-10 alpha=5 Non-Mutual"
echo "========================================"
$PY main.py --config tmp_configs/cifar10_a5_nonmutual.yaml

echo ""
echo "========================================"
echo "3/8: CIFAR-10 alpha=10 Mutual"
echo "========================================"
$PY main.py --config tmp_configs/cifar10_a10_mutual.yaml

echo ""
echo "========================================"
echo "4/8: CIFAR-10 alpha=10 Non-Mutual"
echo "========================================"
$PY main.py --config tmp_configs/cifar10_a10_nonmutual.yaml

echo ""
echo "========================================"
echo "5/8: MNIST alpha=5"
echo "========================================"
$PY main.py --config tmp_configs/mnist_a5.yaml

echo ""
echo "========================================"
echo "6/8: MNIST alpha=10"
echo "========================================"
$PY main.py --config tmp_configs/mnist_a10.yaml

echo ""
echo "========================================"
echo "7/8: Fashion-MNIST alpha=5"
echo "========================================"
$PY main.py --config tmp_configs/fmnist_a5.yaml

echo ""
echo "========================================"
echo "8/8: Fashion-MNIST alpha=10"
echo "========================================"
$PY main.py --config tmp_configs/fmnist_a10.yaml

echo ""
echo "=== ALL 8 EXPERIMENTS COMPLETED ==="
