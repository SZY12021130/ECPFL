"""
实验对比工具
支持从 experiments_registry.json 中选择两次实验并生成 side-by-side 对比报告
"""

import json
import os
import sys
from datetime import datetime


REGISTRY_PATH = "results/experiments_registry.json"


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        print(f"注册表不存在: {REGISTRY_PATH}")
        sys.exit(1)
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_experiments(registry):
    print(f"\n{'Index':<6} {'Timestamp':<20} {'Mode':<10} {'Dataset':<10} {'Model':<12} {'Packing':<8} {'Sampling':<8} {'Acc(%)':<8} {'Time(s)':<10}")
    print("-" * 100)
    for i, entry in enumerate(registry):
        cfg = entry['config_summary']
        met = entry['metrics_summary']
        packing = "ON" if cfg.get('slot_packing') else "OFF"
        print(f"{i:<6} {entry['timestamp']:<20} {entry['mode']:<10} {cfg['dataset']:<10} {cfg['model']:<12} {packing:<8} {cfg.get('client_sampling_rate', 1.0):<8.2f} {met['final_test_acc']:<8.2f} {met['total_time_sec']:<10.2f}")


def generate_comparison_report(exp1, exp2, output_path):
    lines = []
    lines.append("# Experiment Configuration Comparison Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y%m%d_%H%M%S')}  ")
    lines.append("")
    
    # Config comparison table
    lines.append("## 1. Configuration Comparison")
    lines.append("")
    lines.append("| Parameter | Exp 1 | Exp 2 | Diff |")
    lines.append("|-----------|-------|-------|------|")
    cfg1 = exp1['config_summary']
    cfg2 = exp2['config_summary']
    keys = sorted(set(cfg1.keys()) | set(cfg2.keys()))
    for k in keys:
        v1 = cfg1.get(k, '-')
        v2 = cfg2.get(k, '-')
        diff = "⚠️" if v1 != v2 else "✅"
        lines.append(f"| {k} | {v1} | {v2} | {diff} |")
    lines.append("")
    
    # Metrics comparison table
    METRIC_DESC = {
        "final_test_acc": "最终测试准确率（全局模型在测试集上的精度）",
        "final_test_loss": "最终测试损失（全局模型在测试集上的交叉熵损失）",
        "total_time_sec": "总训练时间（整个实验从头到尾的总耗时）",
        "total_communication_mb": "总通信量（所有轮次上传+下载之和）",
        "avg_round_time_sec": "平均每轮时间（从模型下发到聚合完成的平均耗时）",
        "avg_upload_kb": "平均上传开销（每轮所有被选中客户端上传量的平均值）",
        "avg_download_kb": "平均下载开销（每轮服务器下发模型数据量的平均值）",
        "avg_expansion_ratio": "平均密文膨胀率（密文大小相对明文的平均倍数）",
        "avg_encryption_time_sec": "平均加密时间（每个客户端加密模型更新的平均耗时）",
        "avg_decryption_time_sec": "平均解密时间（HelperNode每轮解密聚合结果平均耗时）",
        "key_distribution_mb": "密钥分发总开销（CKKS公钥/Galois密钥分发给所有客户端的总字节数）",
        "total_ciphertext_blocks": "密文块总数（所有客户端上传的CKKS密文向量块总数）",
    }
    lines.append("## 2. Metrics Comparison")
    lines.append("")
    lines.append("| 指标 | 含义 | Exp 1 | Exp 2 | Diff |")
    lines.append("|------|------|-------|-------|------|")
    m1 = exp1['metrics_summary']
    m2 = exp2['metrics_summary']
    for k in sorted(set(m1.keys()) | set(m2.keys())):
        desc = METRIC_DESC.get(k, '-')
        v1 = m1.get(k, '-')
        v2 = m2.get(k, '-')
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            lines.append(f"| {k} | {desc} | {v1:.4f} | {v2:.4f} | {v1 - v2:+.4f} |")
        else:
            lines.append(f"| {k} | {desc} | {v1} | {v2} | - |")
    lines.append("")
    
    # Paths
    lines.append("## 3. Experiment Paths")
    lines.append("")
    lines.append(f"- **Exp 1 ({exp1['timestamp']}):** `{exp1['output_dir']}`")
    lines.append(f"- **Exp 2 ({exp2['timestamp']}):** `{exp2['output_dir']}`")
    lines.append("")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"对比报告已保存: {output_path}")


def main():
    registry = load_registry()
    if len(registry) < 2:
        print("注册表中实验数量不足 2 个，无法对比")
        sys.exit(1)
    
    print_experiments(registry)
    print("\n请选择要对比的两个实验索引（例如: 0 1）：")
    try:
        user_input = input("> ").strip()
        idx1, idx2 = map(int, user_input.split())
        exp1 = registry[idx1]
        exp2 = registry[idx2]
    except (ValueError, IndexError):
        print("输入无效")
        sys.exit(1)
    
    output_path = f"results/comparison_config_{exp1['timestamp']}_vs_{exp2['timestamp']}.md"
    generate_comparison_report(exp1, exp2, output_path)


if __name__ == "__main__":
    main()
