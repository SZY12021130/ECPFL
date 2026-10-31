import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"

for method, ds, path in [
    ("FedAvg+CKKS", "MNIST", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/metrics.json"),
    ("FedPHE", "MNIST", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/metrics.json"),
    ("FedPHE", "FMNIST", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist/metrics.json"),
    ("FedPHE", "CIFAR-10", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10/metrics.json"),
    ("FedPHE", "SVHN", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn/metrics.json"),
    ("ESAFL", "MNIST", "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist/metrics.json"),
]:
    p = os.path.join(ROOT, path)
    with open(p) as f:
        d = json.load(f)
    print(f"\n{method} | {ds}:")
    print(f"  upload_cost[0] = {d['upload_cost'][0]}")
    print(f"  download_cost[0] = {d['download_cost'][0]}")
    print(f"  num_ciphertexts first 5 = {d['num_ciphertexts'][:5]}")
    if "aggregated_ciphertexts" in d:
        print(f"  aggregated_ciphertexts first 5 = {d['aggregated_ciphertexts'][:5]}")
    if "download_cost" in d:
        print(f"  ratio download/upload = {d['download_cost'][0] / d['upload_cost'][0]:.2f}")
