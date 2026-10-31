"""
CKKS-Fed 超参数调优批量实验脚本
===============================
支持多数据集、多模型、多策略组合的自动化实验。

用法:
    export KMP_DUPLICATE_LIB_OK="TRUE"
    python scripts/hyperparameter_tuning.py --dataset cifar10 --model resnet20 --rounds 20
"""

import sys
import os
import copy
import yaml
import json
import time
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import CKKSFedPrefetchExperiment


def deep_merge(base: dict, diff: dict):
    """递归合并 diff 到 base"""
    for key, value in diff.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def generate_experiment_matrix(dataset: str, model: str, rounds: int = 20):
    """
    生成实验矩阵。
    返回列表，每个元素是 (exp_id, config_diff) 元组。
    """
    experiments = []

    # 基础固定参数
    base_diff = {
        "data": {"dataset": dataset},
        "model": {"name": model},
        "system": {
            "num_rounds": rounds,
            "num_epochs": 3,
            "num_clients": 10,
        },
        "prefetch": {"enable_prefetch": True},
        "ckks": {
            "sparsification": {
                "use_warmup_skip_sparse": True,
                "warmup_rounds": 2,
            }
        },
        "bandwidth": {
            "fedfetch_trace_path": os.path.join(PROJECT_ROOT, "fedfetch_bandwidth.pkl"),
            "filter_low_bandwidth": False,
            "base_dl_bw": 1024.0,
            "base_ul_bw": 512.0,
            "variance": 0.3,
            "distribution": "lognormal",
        },
    }

    # 客户端选择策略列表
    selection_strategies = ["sticky", "random", "oort"]

    # 投票方式列表
    vote_modes = ["union", "topk", "threshold", "none"]

    # 稀疏率列表
    sparsity_rates = [0.5, 0.3]

    exp_counter = 0

    # 1) 无稀疏化基线 (sticky + none + sparsity=1.0)
    for sel in selection_strategies:
        exp_counter += 1
        diff = copy.deepcopy(base_diff)
        diff["client_selection"] = {"strategy": sel}
        diff["global_mask_vote"] = {"mode": "none"}
        diff["ckks"]["sparsification"]["strategy"] = "none"
        experiments.append((
            f"{exp_counter:03d}_{dataset}_{model}_{sel}_none_nosparse",
            diff,
            f"基线: {sel}选择 + 无稀疏化"
        ))

    # 2) sticky + 各种投票方式 + sparsity=0.5
    for mode in vote_modes:
        exp_counter += 1
        diff = copy.deepcopy(base_diff)
        diff["client_selection"] = {"strategy": "sticky"}
        diff["global_mask_vote"] = {"mode": mode}
        diff["ckks"]["sparsification"]["strategy"] = "topk"
        diff["ckks"]["sparsification"]["sparsity_rate"] = 0.5
        if mode == "topk":
            diff["global_mask_vote"]["topk_k"] = 20
        if mode == "threshold":
            diff["global_mask_vote"]["threshold_pct"] = 0.3
        experiments.append((
            f"{exp_counter:03d}_{dataset}_{model}_sticky_{mode}_s0.5",
            diff,
            f"Sticky + {mode}投票 + 稀疏率0.5"
        ))

    # 3) sticky + union + 不同稀疏率
    for rate in sparsity_rates:
        if rate == 0.5:
            continue  # 已在上一步包含
        exp_counter += 1
        diff = copy.deepcopy(base_diff)
        diff["client_selection"] = {"strategy": "sticky"}
        diff["global_mask_vote"] = {"mode": "union"}
        diff["ckks"]["sparsification"]["strategy"] = "topk"
        diff["ckks"]["sparsification"]["sparsity_rate"] = rate
        experiments.append((
            f"{exp_counter:03d}_{dataset}_{model}_sticky_union_s{rate}",
            diff,
            f"Sticky + union + 稀疏率{rate}"
        ))

    # 4) 不同选择策略 + union + sparsity=0.5
    for sel in ["random", "oort"]:
        exp_counter += 1
        diff = copy.deepcopy(base_diff)
        diff["client_selection"] = {"strategy": sel}
        diff["global_mask_vote"] = {"mode": "union"}
        diff["ckks"]["sparsification"]["strategy"] = "topk"
        diff["ckks"]["sparsification"]["sparsity_rate"] = 0.5
        experiments.append((
            f"{exp_counter:03d}_{dataset}_{model}_{sel}_union_s0.5",
            diff,
            f"{sel} + union + 稀疏率0.5"
        ))

    # 5) sticky + union + sparsity=0.5 + prefetch=off (对照)
    exp_counter += 1
    diff = copy.deepcopy(base_diff)
    diff["client_selection"] = {"strategy": "sticky"}
    diff["global_mask_vote"] = {"mode": "union"}
    diff["ckks"]["sparsification"]["strategy"] = "topk"
    diff["ckks"]["sparsification"]["sparsity_rate"] = 0.5
    diff["prefetch"]["enable_prefetch"] = False
    experiments.append((
        f"{exp_counter:03d}_{dataset}_{model}_sticky_union_s0.5_nopf",
        diff,
        f"Sticky + union + 稀疏率0.5 + 无预取"
    ))

    return experiments


def run_single_experiment(exp_id: str, config_diff: dict, base_config: dict, description: str):
    """运行单个实验，返回结果摘要"""
    print(f"\n{'='*70}")
    print(f" [{datetime.now().strftime('%H:%M:%S')}] 开始: {exp_id}")
    print(f" 说明: {description}")
    print(f" {'='*70}")

    config = copy.deepcopy(base_config)
    deep_merge(config, config_diff)

    # 写入临时配置
    tmp_dir = os.path.join(PROJECT_ROOT, "tmp_configs")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_config_path = os.path.join(tmp_dir, f"{exp_id}.yaml")
    with open(tmp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    start_time = time.time()
    try:
        exp = CKKSFedPrefetchExperiment(tmp_config_path)
        results = exp.run_experiment_prefetch()
    except Exception as e:
        print(f" [ERROR] {exp_id} 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(tmp_config_path):
            os.remove(tmp_config_path)

    elapsed = time.time() - start_time

    # 提取结果
    pf_results = results.get('results', [])
    metrics = results.get('metrics', {})

    rounds_data = []
    for r in pf_results:
        rounds_data.append({
            'round': r.get('round', 0),
            'test_acc': r.get('test_acc', 0.0),
            'test_loss': r.get('test_loss', 0.0),
            'round_time': r.get('round_time', 0.0),
        })

    final_acc = rounds_data[-1]['test_acc'] if rounds_data else 0.0
    final_loss = rounds_data[-1]['test_loss'] if rounds_data else 0.0

    total_comm = sum(metrics.get('total_communication_cost', []))
    avg_round_time = sum(metrics.get('total_round_time', [])) / len(metrics.get('total_round_time', [1]))
    avg_real_time = sum(metrics.get('total_round_real_time', [])) / len(metrics.get('total_round_real_time', [1]))

    summary = {
        'exp_id': exp_id,
        'description': description,
        'dataset': config_diff.get('data', {}).get('dataset', 'unknown'),
        'model': config_diff.get('model', {}).get('name', 'unknown'),
        'selection_strategy': config_diff.get('client_selection', {}).get('strategy', 'unknown'),
        'vote_mode': config_diff.get('global_mask_vote', {}).get('mode', 'none'),
        'sparsity_rate': config_diff.get('ckks', {}).get('sparsification', {}).get('sparsity_rate', 1.0),
        'prefetch_enabled': config_diff.get('prefetch', {}).get('enable_prefetch', True),
        'final_test_acc': final_acc,
        'final_test_loss': final_loss,
        'total_comm_mb': total_comm / (1024 * 1024),
        'avg_round_time_sec': avg_round_time,
        'avg_real_time_sec': avg_real_time,
        'elapsed_min': elapsed / 60,
        'rounds_data': rounds_data,
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    }

    print(f" [Result] 最终准确率: {final_acc:.2f}% | 总通信: {summary['total_comm_mb']:.2f} MB | 耗时: {elapsed/60:.1f} min")
    return summary


def save_results(summaries: list, dataset: str, model: str):
    """保存结果到 compare_analysis/{dataset}/ 目录"""
    out_dir = os.path.join(PROJECT_ROOT, "compare_analysis", dataset)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"tuning_{dataset}_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    print(f"\n[Save] 结果已保存: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="CKKS-Fed 超参数调优")
    parser.add_argument("--dataset", type=str, default="cifar10", choices=["mnist", "fashion_mnist", "cifar10"])
    parser.add_argument("--model", type=str, default="resnet20")
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--start_from", type=int, default=0, help="从第N个实验开始（用于中断恢复）")
    args = parser.parse_args()

    base_config_path = os.path.join(PROJECT_ROOT, "configs", "config.yaml")
    print(f"[Init] 加载基础配置: {base_config_path}")
    with open(base_config_path, 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)

    experiments = generate_experiment_matrix(args.dataset, args.model, args.rounds)
    print(f"\n{'='*70}")
    print(f" 实验矩阵: {args.dataset} + {args.model} | {args.rounds}轮")
    print(f" 总实验数: {len(experiments)}")
    print(f" {'='*70}")
    for i, (exp_id, diff, desc) in enumerate(experiments):
        status = "待运行" if i >= args.start_from else "跳过"
        print(f"  [{i+1:2d}/{len(experiments)}] {status}: {exp_id}")

    summaries = []
    start_all = time.time()

    for i, (exp_id, config_diff, description) in enumerate(experiments):
        if i < args.start_from:
            continue
        print(f"\n{'='*70}")
        print(f" 进度: {i+1}/{len(experiments)} | 已耗时: {(time.time()-start_all)/60:.1f} min")
        print(f" {'='*70}")

        summary = run_single_experiment(exp_id, config_diff, base_config, description)
        if summary:
            summaries.append(summary)
            # 每完成一个实验就保存一次（防中断丢失）
            save_results(summaries, args.dataset, args.model)

    elapsed = (time.time() - start_all) / 60
    print(f"\n{'='*70}")
    print(f" 全部实验完成！总耗时: {elapsed:.1f} 分钟")
    print(f" 成功: {len(summaries)}/{len(experiments)}")
    print(f" {'='*70}")

    # 打印汇总表
    print(f"\n{'ExpID':<40} {'Acc':<8} {'Comm(MB)':<10} {'Time(s)':<10} {'Desc':<30}")
    print("-" * 100)
    for s in summaries:
        print(f"{s['exp_id']:<40} {s['final_test_acc']:<8.2f} {s['total_comm_mb']:<10.2f} {s['avg_round_time_sec']:<10.2f} {s['description']:<30}")


if __name__ == "__main__":
    main()
