import glob

for f in sorted(glob.glob('accuracy_baseline/fedphe/config/config_*.yaml')):
    with open(f, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()

    cleaned = [line for line in lines if 'num_selected_clients' not in line]

    with open(f, 'w', encoding='utf-8') as fh:
        fh.writelines(cleaned)
    print(f"Cleaned: {f}")

print("\nDone. FedPHE 已恢复自动聚类模式 (max_k=num_clients=50).")
