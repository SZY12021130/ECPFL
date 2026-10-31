#!/usr/bin/env python3
"""
验证 ECPFL-UN / TH / RK 各数据集的通信量和通信时间
从 metrics.json 和 report.md 中提取数据对比
"""
import json, os, re

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"
OURS_DIR = os.path.join(PROJECT_ROOT, "accuracy_baseline/ours/result_fix_pro")

# 所有实验目录
EXPERIMENTS = {
    "ECPFL-UN": {
        "MNIST":    "20260605_mnist_union",
        "FMNIST":   "20260605_fashion_mnist_union",
        "CIFAR-10": "20260605_cifar10_union",
        "SVHN":     "20260622_svhn_sp0.5_topk0.7",  # 只有 topk 实验
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

def parse_report(report_path):
    """从 report.md 提取关键指标"""
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    def extract(pattern):
        m = re.search(pattern, content)
        return float(m.group(1)) if m else None
    
    return {
        "accuracy": extract(r"Final Test Accuracy.*?\*\*([\d.]+)%\*\*"),
        "total_comm_mb": extract(r"Total Communication.*?\|\s*([\d.]+)\s*MB"),
        "total_upload_mb": extract(r"Total Upload.*?\|\s*([\d.]+)\s*MB"),
        "effective_download_mb": extract(r"Effective Download.*?\|\s*([\d.]+)\s*MB"),
        "total_fetch_mb": extract(r"Total Download \(Fetch\).*?\|\s*([\d.]+)\s*MB"),
        "total_prefetch_mb": extract(r"Total Download \(Prefetch\).*?\|\s*([\d.]+)\s*MB"),
        "total_actual_dl_mb": extract(r"Total Actual Download.*?\|\s*([\d.]+)\s*MB"),
        "sim_time_s": extract(r"Total Simulated Time.*?\|\s*([\d.]+)\s*s"),
        "sim_comm_time_s": extract(r"Total Simulated Comm Time.*?\|\s*([\d.]+)\s*s"),
        "avg_upload_mb": extract(r"Avg Upload Cost.*?\|\s*([\d.]+)\s*MB"),
        "avg_dl_mb": extract(r"Avg Effective Download.*?\|\s*([\d.]+)\s*MB"),
        "num_clients": extract(r"Num Clients.*?\|\s*(\d+)"),
        "num_rounds": extract(r"Num Rounds.*?\|\s*(\d+)"),
        "sample_rate": extract(r"Client Sampling Rate.*?\|\s*([\d.]+)"),
    }

def compute_from_metrics(metrics_path, report_data):
    """从 metrics.json 计算通信量和时间"""
    with open(metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    
    upload_cost = m.get("upload_cost", [])
    download_cost = m.get("download_cost", [])
    prefetch_download_cost = m.get("prefetch_download_cost", [])
    fetch_download_cost = m.get("fetch_download_cost", [])
    local_train_time = m.get("local_train_time", [])
    num_rounds = len(upload_cost)
    
    # 通信量
    total_upload = sum(upload_cost)
    total_dl_effective = sum(download_cost)  # effective download
    total_dl_fetch = sum(fetch_download_cost) if fetch_download_cost else 0
    total_dl_prefetch = sum(prefetch_download_cost) if prefetch_download_cost else 0
    total_dl_actual = total_dl_fetch + total_dl_prefetch
    
    # 通信时间：每轮取最慢客户端
    n_clients = int(report_data.get("num_clients", 50))
    sample_rate = report_data.get("sample_rate", 0.5)
    n_sel = int(n_clients * sample_rate)
    
    # 从 report 提取客户端带宽
    report_path = metrics_path.replace("metrics.json", "report.md")
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 解析客户端带宽表
    clients = []
    for line in content.split("\n"):
        if re.match(r"\|\s*\d+\s*\|", line) and "CID" not in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                try:
                    cid = int(parts[1])
                    dl_bw_mbps = float(parts[4].replace("kbps", "").strip())
                    ul_bw_mbps = float(parts[5].replace("kbps", "").strip())
                    clients.append({
                        "cid": cid,
                        "dl_bw": dl_bw_mbps * 1024 * 1024 / 8,  # bytes/s
                        "ul_bw": ul_bw_mbps * 1024 * 1024 / 8,
                    })
                except (ValueError, IndexError):
                    pass
    
    if not clients:
        print(f"  [WARN] 无法解析客户端带宽")
        return None
    
    # 计算每轮通信时间
    total_ul_time = 0.0
    total_dl_time = 0.0
    total_comm_time = 0.0
    
    for r in range(num_rounds):
        ul_this = upload_cost[r] if r < len(upload_cost) else 0
        dl_this = download_cost[r] if r < len(download_cost) else 0
        
        if ul_this > 0 or dl_this > 0:
            # 每轮上传时间 = max(ul_this / ul_bw) for all selected clients
            # 但 upload_cost 是每轮的总上传量，需要除以 n_sel 得到每客户端量
            ul_per_client = ul_this / n_sel if n_sel > 0 else ul_this
            dl_per_client = dl_this / n_sel if n_sel > 0 else dl_this
            
            max_ul_t = max(ul_per_client / c["ul_bw"] for c in clients)
            max_dl_t = max(dl_per_client / c["dl_bw"] for c in clients)
            
            total_ul_time += max_ul_t
            total_dl_time += max_dl_t
            total_comm_time += max_ul_t + max_dl_t
    
    return {
        "total_upload_bytes": total_upload,
        "total_dl_effective_bytes": total_dl_effective,
        "total_dl_fetch_bytes": total_dl_fetch,
        "total_dl_prefetch_bytes": total_dl_prefetch,
        "total_dl_actual_bytes": total_dl_actual,
        "tv_bytes": total_upload + total_dl_effective,  # TV = upload + effective download
        "tt_comm_time": total_comm_time,
        "tt_ul_time": total_ul_time,
        "tt_dl_time": total_dl_time,
        "num_rounds": num_rounds,
    }

def main():
    for method, datasets in EXPERIMENTS.items():
        print(f"\n{'='*70}")
        print(f"{method}")
        print(f"{'='*70}")
        
        for ds, exp_dir in datasets.items():
            report_path = os.path.join(OURS_DIR, exp_dir, "report.md")
            metrics_path = os.path.join(OURS_DIR, exp_dir, "metrics.json")
            
            if not os.path.exists(report_path):
                print(f"\n  {ds}: [SKIP] report.md 不存在")
                continue
            
            report_data = parse_report(report_path)
            calc_data = compute_from_metrics(metrics_path, report_data)
            
            print(f"\n  {ds} (dir: {exp_dir}):")
            print(f"    Report 数据:")
            print(f"      Accuracy: {report_data['accuracy']}%")
            print(f"      Total Communication: {report_data['total_comm_mb']:.2f} MB ({report_data['total_comm_mb']/1024:.2f} GB)")
            print(f"      Total Upload: {report_data['total_upload_mb']:.2f} MB")
            print(f"      Effective Download: {report_data['effective_download_mb']:.2f} MB")
            print(f"      Total Fetch: {report_data['total_fetch_mb']:.2f} MB")
            print(f"      Total Prefetch: {report_data['total_prefetch_mb']:.2f} MB")
            print(f"      Total Actual DL: {report_data['total_actual_dl_mb']:.2f} MB")
            print(f"      Simulated Time: {report_data['sim_time_s']:.2f} s")
            if report_data['sim_comm_time_s']:
                print(f"      Simulated Comm Time: {report_data['sim_comm_time_s']:.2f} s")
            print(f"      Num Clients: {report_data['num_clients']}, Rounds: {report_data['num_rounds']}, Sample Rate: {report_data['sample_rate']}")
            
            if calc_data:
                print(f"\n    Metrics 计算:")
                print(f"      TV = Upload + Effective DL = {calc_data['tv_bytes']/1024/1024/1024:.2f} GB")
                print(f"      Upload = {calc_data['total_upload_bytes']/1024/1024/1024:.2f} GB")
                print(f"      Effective DL = {calc_data['total_dl_effective_bytes']/1024/1024/1024:.2f} GB")
                print(f"      Fetch DL = {calc_data['total_dl_fetch_bytes']/1024/1024/1024:.2f} GB")
                print(f"      Prefetch DL = {calc_data['total_dl_prefetch_bytes']/1024/1024/1024:.2f} GB")
                print(f"      Actual DL = {calc_data['total_dl_actual_bytes']/1024/1024/1024:.2f} GB")
                print(f"      TT (Comm Time) = {calc_data['tt_comm_time']:.2f} s")
                print(f"        Upload Time = {calc_data['tt_ul_time']:.2f} s")
                print(f"        Download Time = {calc_data['tt_dl_time']:.2f} s")
                print(f"      Num Rounds = {calc_data['num_rounds']}")
                
                # 对比
                print(f"\n    对比:")
                report_tv_gb = report_data['total_comm_mb'] / 1024
                calc_tv_gb = calc_data['tv_bytes'] / 1024 / 1024 / 1024
                print(f"      TV: Report={report_tv_gb:.2f} GB vs Calc={calc_tv_gb:.2f} GB, diff={abs(report_tv_gb-calc_tv_gb):.2f} GB")
                
                if report_data['sim_comm_time_s']:
                    report_tt = report_data['sim_comm_time_s']
                    print(f"      TT: Report={report_tt:.2f} s vs Calc={calc_data['tt_comm_time']:.2f} s, diff={abs(report_tt-calc_data['tt_comm_time']):.2f} s")
                else:
                    report_tt = report_data['sim_time_s']
                    print(f"      TT: Report(Sim Time)={report_tt:.2f} s vs Calc(Comm Time)={calc_data['tt_comm_time']:.2f} s")

if __name__ == "__main__":
    main()
