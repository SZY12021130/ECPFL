"""
策略对比实验脚本：7 种客户端选择策略横向对比
====================================================
运行 7 种策略（random / sticky / sketch_clustering / poc / tifl / haccs / oort）
在相同带宽条件下各跑 20 轮，开启客户端残差 + CipherFetch 预取。

用法:
    $env:KMP_DUPLICATE_LIB_OK="TRUE"
    python scripts/run_strategy_comparison.py

输出:
    - scripts/strategy_comparison_report.md   (Markdown 对比报告)
    - scripts/strategy_comparison_results.json (原始数据 JSON)
    - results/experiment_*/                   (每组实验的详细结果目录)
"""

import sys
import os
import copy
import yaml
import json
import logging
import argparse
import numpy as np
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import CKKSFedPrefetchExperiment, _get_or_create_bandwidth_simulator


# ==============================================================================
# 策略定义
# ==============================================================================
STRATEGIES = [
    ("random", "纯随机采样 (Random)"),
    ("sticky", "Sticky Sampling (FedFetch)"),
    ("sketch_clustering", "草图聚类 (FedPHE)"),
    ("poc", "Power-of-Choice (AISTATS 2022)"),
    ("tifl", "Tier-based FL (HPDC 2020)"),
    ("haccs", "HACCS (IPDPS 2022)"),
    ("oort", "Oort (OSDI 2021)"),
]


def clear_experiment_log_handlers():
    """清理 FileHandler，避免日志重复。"""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            try:
                handler.close()
            except Exception:
                pass
            root.removeHandler(handler)


def deep_merge(base: dict, diff: dict):
    """递归合并配置。"""
    for key, value in diff.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def extract_round_series(results: list) -> dict:
    """从 results 列表中提取每轮指标序列。"""
    return {
        "round": [r["round"] for r in results],
        "test_acc": [r["test_acc"] for r in results],
        "test_loss": [r["test_loss"] for r in results],
        "round_time": [r.get("round_time", 0.0) for r in results],
    }


def run_single_strategy(strategy_name: str, strategy_desc: str,
                        base_config: dict, shared_bw_sim) -> dict:
    """运行单个策略实验，返回结果摘要。"""
    print(f"\n{'='*72}")
    print(f" 策略: {strategy_name} — {strategy_desc}")
    print(f"{'='*72}")

    # 深拷贝并覆盖策略相关配置
    config = copy.deepcopy(base_config)
    config["client_selection"]["strategy"] = strategy_name

    # 写入临时配置
    ts = datetime.now().strftime("%H%M%S")
    tmp_config_path = os.path.join(PROJECT_ROOT, "scripts", f"tmp_config_{strategy_name}_{ts}.yaml")
    with open(tmp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    try:
        exp = CKKSFedPrefetchExperiment(tmp_config_path, bandwidth_simulator=shared_bw_sim)
        results = exp.run_experiment_prefetch()
    except Exception as e:
        print(f" [ERROR] 策略 {strategy_name} 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        clear_experiment_log_handlers()
        if os.path.exists(tmp_config_path):
            os.remove(tmp_config_path)

    # 提取指标
    pf_results = results.get('results', [])
    final_acc = pf_results[-1]['test_acc'] if pf_results else 0.0
    final_loss = pf_results[-1]['test_loss'] if pf_results else 0.0
    m = results.get('metrics', {})

    total_comm = sum(m.get('total_communication_cost', []))
    total_round_time = sum(m.get('total_round_time', []))
    round_times = m.get('total_round_time', [])
    avg_round_time = total_round_time / len(round_times) if round_times else 0.0

    # 收敛速度：达到最终准确率 90% 的轮次
    accs = [r['test_acc'] for r in pf_results]
    target_acc = final_acc * 0.90 if final_acc > 0 else 0.0
    conv_round = next((i + 1 for i, a in enumerate(accs) if a >= target_acc), len(accs))

    # 策略特有统计
    sel_stats = exp.selection_strategy.get_stats() if hasattr(exp, 'selection_strategy') else {}

    summary = {
        "strategy": strategy_name,
        "description": strategy_desc,
        "output_dir": getattr(exp, 'output_dir', 'unknown'),
        "final_test_acc": final_acc,
        "final_test_loss": final_loss,
        "total_comm_mb": total_comm / (1024 * 1024),
        "total_time_sec": total_round_time,
        "avg_round_time_sec": avg_round_time,
        "convergence_round": conv_round,
        "num_rounds": len(pf_results),
        "round_series": extract_round_series(pf_results),
        "selection_stats": sel_stats,
    }

    # 预取特有指标
    summary["total_prefetch_mb"] = sum(m.get('prefetch_download_cost', [])) / (1024 * 1024)
    summary["total_fetch_mb"] = sum(m.get('fetch_download_cost', [])) / (1024 * 1024)
    summary["avg_prefetch_time_sec"] = (
        sum(m.get('prefetch_time', [])) / len(m.get('prefetch_time', [1]))
        if m.get('prefetch_time') else 0.0
    )
    summary["avg_fetch_time_sec"] = (
        sum(m.get('fetch_time', [])) / len(m.get('fetch_time', [1]))
        if m.get('fetch_time') else 0.0
    )

    print(f" [Result] 准确率: {final_acc:.2f}% | 通信: {summary['total_comm_mb']:.2f} MB | "
          f"总时间: {total_round_time:.1f}s | 收敛轮次: {conv_round}/{len(pf_results)}")
    return summary


def generate_markdown_report(summaries: list, report_path: str, elapsed_sec: float):
    """生成 Markdown 对比报告。"""
    lines = [
        "# 客户端选择策略横向对比报告",
        f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"实验设置: 30 客户端 | 20 轮 | OC=1.3 | 客户端残差=ON | 预取=ON",
        f"总耗时: {elapsed_sec/60:.1f} 分钟 ({elapsed_sec/3600:.2f} 小时)",
        "\n## 一、核心指标总览\n",
        "| 策略 | 最终准确率 | 最终损失 | 总通信(MB) | 总时间(s) | 平均轮时(s) | 收敛轮次 |",
        "|------|-----------|---------|-----------|----------|------------|---------|",
    ]

    best_acc = max(s["final_test_acc"] for s in summaries)
    best_time = min(s["total_time_sec"] for s in summaries)

    for s in summaries:
        acc_mark = " ⭐" if s["final_test_acc"] == best_acc else ""
        time_mark = " 🚀" if s["total_time_sec"] == best_time else ""
        lines.append(
            f"| {s['strategy']:<18} | "
            f"{s['final_test_acc']:.2f}%{acc_mark} | "
            f"{s['final_test_loss']:.4f} | "
            f"{s['total_comm_mb']:.2f} | "
            f"{s['total_time_sec']:.1f}{time_mark} | "
            f"{s['avg_round_time_sec']:.2f} | "
            f"{s['convergence_round']}/{s['num_rounds']} |"
        )

    lines.extend([
        "\n## 二、预取效率对比\n",
        "| 策略 | 预取下载(MB) | Fetch下载(MB) | 平均预取时间(s) | 平均Fetch时间(s) |",
        "|------|-------------|--------------|----------------|-----------------|",
    ])
    for s in summaries:
        lines.append(
            f"| {s['strategy']:<18} | "
            f"{s['total_prefetch_mb']:.2f} | "
            f"{s['total_fetch_mb']:.2f} | "
            f"{s['avg_prefetch_time_sec']:.2f} | "
            f"{s['avg_fetch_time_sec']:.2f} |"
        )

    lines.extend([
        "\n## 三、逐轮准确率曲线\n",
        "```",
        f"{'Round':>6}",
    ])
    # 构造表头
    header = f"{'Round':>6}"
    for s in summaries:
        header += f"  {s['strategy'][:10]:>10}"
    lines.append(header)
    lines.append("-" * (6 + 12 * len(summaries)))

    max_rounds = max(len(s["round_series"]["round"]) for s in summaries)
    for r in range(max_rounds):
        row = f"{r+1:>6}"
        for s in summaries:
            accs = s["round_series"]["test_acc"]
            val = f"{accs[r]:.2f}" if r < len(accs) else "-"
            row += f"  {val:>10}"
        lines.append(row)
    lines.append("```")

    lines.extend([
        "\n## 四、策略特点分析\n",
        "### 1. 收敛速度",
        '- **最快收敛**: 通常 Sticky / Oort / PoC 在预取加持下收敛更快，因为它们倾向于选择"有信息"或"快"的客户端。',
        "- **最慢收敛**: Random 因无选择性，可能包含大量 straggler，导致每轮有效时间拉长。",
        "\n### 2. 最终精度",
        '- **最高精度**: Sticky / Sketch 通常较高，前者利用预取优势，后者利用数据代表性。',
        '- **精度损失**: TiFL 若某层客户端数据分布偏斜，可能导致精度波动；HACCS 依赖聚类质量。',
        "\n### 3. 系统效率（时间）",
        '- **最快**: Sticky（优先快客户端 + 预取命中）→ Oort（效用函数权衡时间）→ TiFL（同 tier 内无 straggler）。',
        '- **最慢**: Random / Sketch（Sketch 的代表性客户端可能包含慢设备）。',
        "\n### 4. 通信开销",
        "- 所有策略在相同 OC=1.3 下预取广播量相同，差异主要来自：",
        "  - 选中客户端的 fetch 量（若快客户端多，fetch 小，因预取命中率高）。",
        "  - 丢弃客户端导致的重复 fetch（Sticky 的 change_num 和 OC 截断会引入额外 fetch）。",
        "\n## 五、详细结果目录",
    ])
    for s in summaries:
        lines.append(f"- **{s['strategy']}**: `{s['output_dir']}`")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n[Report] Markdown 报告已保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="7 种客户端选择策略横向对比")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=[s[0] for s in STRATEGIES],
        help=f"要运行的策略，默认全部。可选: {' '.join(s[0] for s in STRATEGIES)}",
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=30,
        help="客户端数量 (默认 30)",
    )
    parser.add_argument(
        "--num-rounds",
        type=int,
        default=20,
        help="训练轮数 (默认 20)",
    )
    parser.add_argument(
        "--oc",
        type=float,
        default=1.3,
        help="Overcommitment 比例 (默认 1.3)",
    )
    args = parser.parse_args()

    # 加载基础配置
    base_config_path = os.path.join(PROJECT_ROOT, "configs", "config.yaml")
    print(f"[Init] 加载基础配置: {base_config_path}")
    with open(base_config_path, 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)

    # 强制覆盖实验参数
    base_config["system"]["num_clients"] = args.num_clients
    base_config["system"]["num_rounds"] = args.num_rounds
    base_config["prefetch"]["overcommitment"] = args.oc
    # 确保开启客户端残差 + 预取
    base_config["prefetch"]["enable_prefetch"] = True
    deep_merge(base_config, {
        "ckks": {
            "ptopk": {
                "client_residual": {"enabled": True},
            }
        }
    })
    # 关闭 TEE 以简化实验（策略对比聚焦选择策略本身）
    base_config["tee"]["enabled"] = False

    print(f"[Config] 客户端={args.num_clients} | 轮数={args.num_rounds} | OC={args.oc} | 残差=ON | 预取=ON | TEE=OFF")

    # 统一生成带宽模拟器（所有策略共享相同带宽条件）
    shared_bw_sim = _get_or_create_bandwidth_simulator(base_config)

    # 运行策略实验
    summaries = []
    start_all = datetime.now()
    strategy_map = dict(STRATEGIES)

    for s_name in args.strategies:
        if s_name not in strategy_map:
            print(f"[Warning] 未知策略 '{s_name}'，跳过。可用: {list(strategy_map.keys())}")
            continue
        summary = run_single_strategy(s_name, strategy_map[s_name], base_config, shared_bw_sim)
        if summary:
            summaries.append(summary)

    elapsed = (datetime.now() - start_all).total_seconds()
    print(f"\n{'='*72}")
    print(f" 全部策略实验完成！总耗时: {elapsed/60:.1f} 分钟 ({elapsed/3600:.2f} 小时)")
    print(f"{'='*72}")

    if not summaries:
        print("[Warning] 没有成功收集到任何实验结果。")
        return

    # 保存 JSON
    os.makedirs(os.path.join(PROJECT_ROOT, "scripts"), exist_ok=True)
    json_path = os.path.join(PROJECT_ROOT, "scripts", "strategy_comparison_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "config": {
                "num_clients": args.num_clients,
                "num_rounds": args.num_rounds,
                "oc": args.oc,
            },
            "total_elapsed_sec": elapsed,
            "strategies": summaries,
        }, f, indent=2, ensure_ascii=False)
    print(f"[Save] 结果 JSON: {json_path}")

    # 生成 Markdown 报告
    report_path = os.path.join(PROJECT_ROOT, "scripts", "strategy_comparison_report.md")
    generate_markdown_report(summaries, report_path, elapsed)

    # 终端简表
    print("\n" + "-" * 110)
    print(f"{'Strategy':<18} {'Acc(%)':<10} {'Loss':<10} {'Comm(MB)':<12} {'Time(s)':<12} {'AvgRound(s)':<14} {'Conv/Rounds':<12}")
    print("-" * 110)
    for s in summaries:
        print(f"{s['strategy']:<18} {s['final_test_acc']:<10.2f} {s['final_test_loss']:<10.4f} "
              f"{s['total_comm_mb']:<12.2f} {s['total_time_sec']:<12.1f} "
              f"{s['avg_round_time_sec']:<14.2f} {s['convergence_round']}/{s['num_rounds']}")
    print("-" * 110)


if __name__ == "__main__":
    main()
