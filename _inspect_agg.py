import json
for method, path in [
    ("FedAvg+CKKS", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/metrics.json"),
    ("FedPHE", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/metrics.json"),
    ("ESAFL", "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist/metrics.json"),
    ("MASER", "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json"),
]:
    with open(path) as f:
        d = json.load(f)
    print(f"\n{method}:")
    print(f"  num_ciphertexts unique: {sorted(set(d['num_ciphertexts']))}")
    print(f"  aggregated_ciphertexts unique: {sorted(set(d.get('aggregated_ciphertexts', [])))}")
    if "aggregated_ciphertexts" in d:
        print(f"  aggregated_ciphertexts first 20: {d['aggregated_ciphertexts'][:20]}")
        print(f"  aggregated_ciphertexts last 20: {d['aggregated_ciphertexts'][-20:]}")
