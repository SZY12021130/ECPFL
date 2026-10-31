"""Extract test_acc from all result_fix_pro metrics.json and format for plotting."""
import json
import os
import glob

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "accuracy_baseline")

methods = {
    "FedAvg+CKKS": os.path.join(BASE, "fedavg+ckks", "result_fix_pro"),
    "FedPHE": os.path.join(BASE, "fedphe", "result_fix_pro"),
    "MASER": os.path.join(BASE, "maser", "result_fix_pro"),
    "ESAFL": os.path.join(BASE, "esafl", "result_fix_pro"),
    "Ours": os.path.join(BASE, "ours", "result_fix_pro"),
}

dataset_keys = {
    "MNIST": ["mnist"],
    "FMNIST": ["fashion_mnist", "fmnist", "fashionmnist"],
    "CIFAR-10": ["cifar10", "cifar-10", "cifar"],
    "SVHN": ["svhn"],
}

result = {}

for method, base_dir in methods.items():
    result[method] = {}
    for ds_name, keys in dataset_keys.items():
        found = False
        for key in keys:
            pattern = os.path.join(base_dir, f"*{key}*", "metrics.json")
            files = glob.glob(pattern)
            if files:
                with open(files[0], "r") as f:
                    data = json.load(f)
                acc = data.get("test_acc", [])
                if acc:
                    # Normalize: if max > 1, it's already percentage; else multiply by 100
                    max_val = max(acc)
                    if max_val > 1.0:
                        # Already percentage (0-100)
                        acc_pct = [round(a, 2) for a in acc]
                    else:
                        # Decimal (0-1), convert to percentage
                        acc_pct = [round(a * 100, 2) for a in acc]
                    result[method][ds_name] = acc_pct
                    print(f"{method:15s} | {ds_name:8s} | len={len(acc):3d} | final={acc_pct[-1]:.2f}%")
                    found = True
                    break
        if not found:
            # For Ours, try scanning all subdirs
            if method == "Ours":
                all_files = glob.glob(os.path.join(base_dir, "*", "metrics.json"))
                for f in all_files:
                    try:
                        with open(f, "r") as fj:
                            d = json.load(fj)
                        cfg = d.get("config", {})
                        data_cfg = cfg.get("data", {}) if cfg else {}
                        ds = data_cfg.get("dataset", "")
                        acc = d.get("test_acc", [])
                        if acc and ds:
                            for ds_name2, keys2 in dataset_keys.items():
                                if ds in keys2 or any(k in ds for k in keys2):
                                    if ds_name2 not in result[method]:
                                        max_val = max(acc)
                                        if max_val > 1.0:
                                            acc_pct = [round(a, 2) for a in acc]
                                        else:
                                            acc_pct = [round(a * 100, 2) for a in acc]
                                        result[method][ds_name2] = acc_pct
                                        print(f"{method:15s} | {ds_name2:8s} | len={len(acc):3d} | final={acc_pct[-1]:.2f}% (from {os.path.basename(f)})")
                    except Exception as e:
                        print(f"Error reading {f}: {e}")
            else:
                print(f"{method:15s} | {ds_name:8s} | MISSING")

# Output in Python dict format for copy-paste
print("\n\n=== PYTHON DICT FORMAT ===\n")
print("DATASET_PARAMS = {")
for ds_name in dataset_keys:
    print(f'    "{ds_name}": {{')
    for method in methods:
        if ds_name in result.get(method, {}):
            acc = result[method][ds_name]
            print(f'        "{method}": {acc},')
        else:
            print(f'        "{method}": None,  # MISSING')
    print("    },")
print("}")
