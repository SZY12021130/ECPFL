import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"

# 检查 FedPHE 各数据集的 download_cost 与 upload_cost 比例
for ds, path in [
    ("MNIST", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/metrics.json"),
    ("FMNIST", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist/metrics.json"),
    ("CIFAR-10", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10/metrics.json"),
    ("SVHN", "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn/metrics.json"),
]:
    p = os.path.join(ROOT, path)
    with open(p) as f:
        d = json.load(f)
    
    # 从 report 获取 full_batch_num
    report_path = os.path.join(ROOT, path.replace("metrics.json", "report.md"))
    with open(report_path) as f:
        content = f.read()
    
    import re
    # 查找 Total CT Blocks (Upload) 和 Total Aggregated CTs (Download)
    m1 = re.search(r"Total CT Blocks \(Upload\).*?\|\s*(\d+)\s*blocks", content)
    m2 = re.search(r"Total Aggregated CTs \(Download\).*?\|\s*(\d+)\s*blocks", content)
    
    upload_blocks = int(m1.group(1)) if m1 else 0
    download_blocks = int(m2.group(1)) if m2 else 0
    
    # 计算每轮的并集大小
    n_rounds = len(d["upload_cost"])
    n_clients = 50  # 从 report 看
    
    print(f"\nFedPHE | {ds}:")
    print(f"  upload_cost[0] = {d['upload_cost'][0]}")
    print(f"  download_cost[0] = {d['download_cost'][0]}")
    print(f"  ratio = {d['download_cost'][0] / d['upload_cost'][0]:.2f}")
    print(f"  num_ciphertexts[0] = {d['num_ciphertexts'][0]} (per client)")
    print(f"  Total Upload Blocks = {upload_blocks}")
    print(f"  Total Download Blocks = {download_blocks}")
    print(f"  Download blocks per round = {download_blocks / n_rounds:.1f}")
    
    # 计算 single_ct
    n_sel = 25  # 假设每轮选 25 个客户端
    single_ct = d['upload_cost'][0] / n_sel / d['num_ciphertexts'][0]
    print(f"  single_ct = {single_ct:.0f} bytes")
    
    # 计算并集大小
    union_blocks = d['download_cost'][0] / single_ct / n_sel
    print(f"  并集大小 = {union_blocks:.1f} blocks")
