import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
for ds, path in [
    ("MNIST", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/metrics.json"),
    ("FMNIST", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist/metrics.json"),
    ("CIFAR-10", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10/metrics.json"),
    ("SVHN", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_115455_svhn/metrics.json"),
]:
    p = os.path.join(ROOT, path)
    with open(p) as f:
        d = json.load(f)
    stride = len(d["num_ciphertexts"]) // len(d["upload_cost"])
    print(f"\nFedAvg+CKKS | {ds}: num_ciphertexts per client = {d['num_ciphertexts'][0]}")
