#!/usr/bin/env python3
"""
检查 ECPFL 的通信逻辑：
1. upload_cost[r] 的含义
2. download_cost[r] 的含义  
3. 确认 delta_size（每轮服务器下发的密文大小）
4. 对比 upload vs delta_size
"""
import json, os, re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")

EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST":    "20260605_mnist_union",
        "FMNIST":   "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
        "SVHN":     "20260622_svhn_sp0.5_topk0.7",
    },
    "ECPFL-TH": {
        "MNIST":    "20260604_mnist_threshold_pct_0.1",
        "FMNIST":   "20260604_fashion_mnist_threshold_pct_0.3",
        "CIFAR-10": "20260604_cifar10_threshold_pct_0.7",
    },
    "ECPFL-RK": {
        "MNIST":    "20260605_mnist_topk_pct_0.1",
        "FMNIST":   "20260610_fashion_mnist_sp0.3_topk0.3",
        "CIFAR-10": "20260605_cifar10_topk_pct_0.7",
    },
}

def parse_clients(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*kbps\s*\|\s*(\d+)\s*kbps\s*\|'
    clients = []
    for m in re.findall(pattern, content):
        clients.append({
            "cid": int(m[0]),
            "dl_bw": int(m[3]) * 1000 / 8,
            "ul_bw": int(m[4]) * 1000 / 8,
        })
    return clients

def main():
    for method, datasets in EXPERIMENTS.items():
        for ds, exp_dir in datasets.items():
            mpath = os.path.join(OURS_DIR, exp_dir, "metrics.json")
            rpath = os.path.join(OURS_DIR, exp_dir, "report.md")
            
            with open(mpath) as f:
                m = json.load(f)
            
            clients = parse_clients(rpath)
            n_clients = len(clients)
            
            upload_cost = m.get("upload_cost", [])
            download_cost = m.get("download_cost", [])
            ciphertext_size = m.get("ciphertext_size", [])
            plaintext_size = m.get("plaintext_size", [])
            expansion_ratio = m.get("expansion_ratio", [])
            selected_clients = m.get("selected_clients", [])
            num_ciphertexts = m.get("num_ciphertexts", [])
            
            n_rounds = len(upload_cost)
            
            print(f"\n{'='*70}")
            print(f"{method} | {ds} ({exp_dir})")
            print(f"  clients={n_clients}, rounds={n_rounds}")
            
            if selected_clients:
                n_sel_list = [len(sc) for sc in selected_clients]
                print(f"  selected_clients per round: min={min(n_sel_list)}, max={max(n_sel_list)}, avg={sum(n_sel_list)/len(n_sel_list):.1f}")
            else:
                print(f"  selected_clients: NOT RECORDED")
            
            if ciphertext_size:
                print(f"  ciphertext_size[0:5]: {[f'{x/1024/1024:.2f}MB' for x in ciphertext_size[:5]]}")
                print(f"  ciphertext_size avg: {sum(ciphertext_size)/len(ciphertext_size)/1024/1024:.2f} MB")
            
            if num_ciphertexts:
                stride = len(num_ciphertexts) // n_rounds if n_rounds > 0 else 1
                nc_vals = [num_ciphertexts[r*stride] for r in range(n_rounds)]
                print(f"  num_ciphertexts[0:5]: {nc_vals[:5]}")
                print(f"  num_ciphertexts avg: {sum(nc_vals)/len(nc_vals):.1f}")
            
            # upload_cost 分析
            total_ul = sum(upload_cost)
            avg_ul_per_round = total_ul / n_rounds if n_rounds > 0 else 0
            print(f"  upload_cost: total={total_ul/1024**3:.2f}GB, avg/round={avg_ul_per_round/1024**2:.2f}MB")
            
            # download_cost 分析
            total_dl = sum(download_cost)
            avg_dl_per_round = total_dl / n_rounds if n_rounds > 0 else 0
            print(f"  download_cost: total={total_dl/1024**3:.4f}GB, avg/round={avg_dl_per_round/1024**2:.4f}MB")
            
            # delta_size 推算
            # 如果 n_sel 已知，delta_size = upload_cost[r] / n_sel
            if selected_clients:
                for r in [0, 1, 2, 25, 49]:
                    if r < n_rounds:
                        n_sel = len(selected_clients[r])
                        ul_per_client = upload_cost[r] / n_sel
                        dl_per_client = download_cost[r] / n_sel
                        ct_size = ciphertext_size[r] if ciphertext_size and r < len(ciphertext_size) else 0
                        nc = num_ciphertexts[r] if num_ciphertexts and r < len(num_ciphertexts) else 0
                        print(f"  round {r}: n_sel={n_sel}, ul/client={ul_per_client/1024**2:.2f}MB, "
                              f"dl/client={dl_per_client/1024**4:.4f}KB, "
                              f"ct_size={ct_size/1024**2:.2f}MB, n_cts={nc}, "
                              f"n_cts*ct={nc*ct_size/1024**2:.2f}MB")

if __name__ == "__main__":
    main()
