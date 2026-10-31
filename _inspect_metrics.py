import json
for method, path in [
    ("FedAvg+CKKS", "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/metrics.json"),
    ("FedPHE", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/metrics.json"),
    ("ESAFL", "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist/metrics.json"),
    ("MASER", "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json"),
]:
    with open(path) as f:
        d = json.load(f)
    keys = ["upload_cost", "download_cost", "num_ciphertexts", "aggregated_ciphertexts", "selected_clients", "maser_ct_upload", "maser_partial_dec_upload", "plaintext_upload"]
    print(f"\n{method}:")
    for k in keys:
        if k in d:
            print(f"  {k}: len={len(d[k])}, first5={d[k][:5]}")
