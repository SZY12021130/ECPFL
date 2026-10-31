"""
Merge vs CRTStack 打包策略对比实验
控制所有其他变量一致，仅切换 packing.strategy，对比通信量和准确率。
"""

import os
import sys
import yaml
import json
import shutil
import subprocess
import time
from datetime import datetime

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_CONFIG_PATH = "configs/config.yaml"
EXPERIMENT_TAG = "merge_vs_crtstack"


def create_configs():
    """基于 base config 创建两个对比实验的临时配置"""
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        base = yaml.safe_load(f)

    # 统一控制变量：关闭所有可能干扰打包策略对比的功能
    base["prefetch"]["enable_prefetch"] = False
    base["tee"]["enabled"] = False
    base["esafl"]["enabled"] = False
    base["global_mask_vote"]["mode"] = "none"
    base["blinding_mask"]["enabled"] = False
    base["ckks"]["sparsification"]["strategy"] = "none"
    base["ckks"]["ptopk"]["enable"] = False
    base["system"]["run_plaintext_baseline"] = False
    base["system"]["upload_difference"] = True
    # 固定随机种子保证可复现
    base["system"]["random_seed"] = 42

    # 创建 merge 配置
    merge_cfg = base.copy()
    merge_cfg["ckks"] = dict(base["ckks"])
    merge_cfg["ckks"]["packing"] = {"strategy": "merged"}

    # 创建 crtstack 配置
    crt_cfg = base.copy()
    crt_cfg["ckks"] = dict(base["ckks"])
    crt_cfg["ckks"]["packing"] = {
        "strategy": "crtstack",
        "crt_layers": 4,
        "crt_quant_bits": 8,
    }

    os.makedirs("tmp_configs", exist_ok=True)
    merge_path = f"tmp_configs/{EXPERIMENT_TAG}_merge.yaml"
    crt_path = f"tmp_configs/{EXPERIMENT_TAG}_crtstack.yaml"

    with open(merge_path, "w", encoding="utf-8") as f:
        yaml.dump(merge_cfg, f, allow_unicode=True, sort_keys=False)
    with open(crt_path, "w", encoding="utf-8") as f:
        yaml.dump(crt_cfg, f, allow_unicode=True, sort_keys=False)

    return merge_path, crt_path


def run_experiment(config_path: str):
    """运行单个实验，返回结果目录"""
    print(f"\n{'='*60}")
    print(f"启动实验: {config_path}")
    print(f"{'='*60}")

    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    start = time.time()
    proc = subprocess.run(
        [sys.executable, "main.py", "--config", config_path],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=False,
    )
    elapsed = time.time() - start

    print(f"实验完成: {config_path}, 耗时 {elapsed:.1f}s, 返回码 {proc.returncode}")
    return proc.returncode == 0


def find_experiment_in_registry(timestamp_hint: str):
    """从注册表中找到对应时间戳的实验目录"""
    reg_path = "results/experiments_registry.json"
    if not os.path.exists(reg_path):
        return None
    with open(reg_path, "r", encoding="utf-8") as f:
        reg = json.load(f)
    # 找到时间戳匹配的最新条目
    for e in reversed(reg):
        if timestamp_hint in e.get("timestamp", ""):
            return e
    return None


def extract_metrics_from_registry(entry: dict):
    """从注册表条目中提取关键指标"""
    if entry is None:
        return None
    ms = entry.get("metrics_summary", {})
    return {
        "strategy": entry.get("config_summary", {}).get("packing", "?"),
        "timestamp": entry.get("timestamp", ""),
        "result_dir": entry.get("output_dir", ""),
        "final_test_acc": ms.get("final_test_acc", 0.0),
        "final_test_loss": ms.get("final_test_loss", 0.0),
        "total_comm_mb": ms.get("total_communication_mb", 0.0),
        "avg_expansion_ratio": ms.get("avg_expansion_ratio", 0.0),
        "avg_upload_kb": ms.get("avg_upload_kb", 0.0),
        "avg_download_kb": ms.get("avg_download_kb", 0.0),
        "total_time_sec": ms.get("total_time_sec", 0.0),
        "avg_round_time_sec": ms.get("avg_round_time_sec", 0.0),
        "total_ciphertext_blocks": ms.get("total_ciphertext_blocks", 0),
    }


def print_comparison(merge_metrics, crt_metrics):
    """打印对比表格"""
    print("\n" + "=" * 80)
    print("Merge vs CRTStack 打包策略对比结果")
    print("=" * 80)

    fields = [
        ("最终测试准确率", "final_test_acc", "%.2f%%", lambda x: x * 100),
        ("最终测试损失", "final_test_loss", "%.4f", lambda x: x),
        ("总通信量 (MB)", "total_comm_mb", "%.2f", lambda x: x),
        ("平均上传量 (KB)", "avg_upload_kb", "%.2f", lambda x: x),
        ("平均下载量 (KB)", "avg_download_kb", "%.2f", lambda x: x),
        ("平均密文膨胀率", "avg_expansion_ratio", "%.2fx", lambda x: x),
        ("总密文块数", "total_ciphertext_blocks", "%d", lambda x: int(x)),
        ("总实验时间 (sec)", "total_time_sec", "%.1f", lambda x: x),
        ("平均每轮时间 (sec)", "avg_round_time_sec", "%.1f", lambda x: x),
    ]

    print(f"{'指标':<22} {'Merged':>18} {'CRTStack':>18} {'变化':>18}")
    print("-" * 80)
    for label, key, fmt, transform in fields:
        m_val = transform(merge_metrics.get(key, 0))
        c_val = transform(crt_metrics.get(key, 0))
        if key in ["final_test_acc"]:
            delta = c_val - m_val
            delta_str = f"{delta:+.2f}pp"
        elif key == "final_test_loss":
            delta = c_val - m_val
            delta_str = f"{delta:+.4f}"
        else:
            if m_val != 0:
                pct = (c_val - m_val) / m_val * 100
                delta_str = f"{pct:+.1f}%"
            else:
                delta_str = "N/A"
        print(f"{label:<22} {fmt % m_val:>18} {fmt % c_val:>18} {delta_str:>18}")

    # 通信量节省
    if merge_metrics.get("total_comm_mb", 0) > 0:
        comm_saved = (merge_metrics["total_comm_mb"] - crt_metrics["total_comm_mb"]) / merge_metrics["total_comm_mb"] * 100
        print("-" * 80)
        print(f"通信量节省: {comm_saved:.1f}%")
    print("=" * 80)


def main():
    print("=" * 80)
    print("Merge vs CRTStack 打包策略对比实验")
    print("=" * 80)

    # 1. 创建配置
    merge_cfg, crt_cfg = create_configs()
    print(f"配置已生成:\n  - {merge_cfg}\n  - {crt_cfg}")

    # 2. 运行 merged 实验
    merge_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    merge_success = run_experiment(merge_cfg)
    merge_entry = find_experiment_in_registry(merge_ts[:8])
    merge_metrics = extract_metrics_from_registry(merge_entry)

    # 3. 运行 crtstack 实验
    crt_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    crt_success = run_experiment(crt_cfg)
    crt_entry = find_experiment_in_registry(crt_ts[:8])
    crt_metrics = extract_metrics_from_registry(crt_entry)

    # 4. 打印对比
    if merge_metrics and crt_metrics:
        print_comparison(merge_metrics, crt_metrics)

        # 保存对比结果
        comparison = {
            "merge": merge_metrics,
            "crtstack": crt_metrics,
            "timestamp": datetime.now().isoformat(),
        }
        out_path = f"results/{EXPERIMENT_TAG}_comparison.json"
        os.makedirs("results", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"\n对比结果已保存至: {out_path}")
    else:
        print("\n实验结果提取失败")
        if merge_entry:
            print(f"  merge: {merge_entry.get('output_dir')}")
        if crt_entry:
            print(f"  crtstack: {crt_entry.get('output_dir')}")


if __name__ == "__main__":
    main()
