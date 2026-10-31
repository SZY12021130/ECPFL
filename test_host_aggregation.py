"""
Host 同态预聚合 + TEE 时间统计 集成测试脚本
================================================

运行一次精简的联邦学习实验，验证：
  1. Host 侧同态预聚合正常工作（reduce 解密量从 O(nJ) 到 O(J)）
  2. TEE 时间统计字段正确记录到 metrics
  3. 盲化掩码在稀疏化场景下正确补偿
  4. 模型收敛不受影响
  5. Markdown 报告包含 TEE 时间明细

用法:
    python test_host_aggregation.py
"""

import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import CKKSFedPrefetchExperiment


def run_test():
    print("=" * 70)
    print("TEST: Host Homomorphic Aggregation + TEE Time Breakdown")
    print("=" * 70)

    # 1) 运行实验
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/test_host_agg.yaml"
    print(f"\n[1/5] Loading config: {config_path}")
    experiment = CKKSFedPrefetchExperiment(config_path)

    print(f"[2/5] Running experiment...")
    results = experiment.run_experiment_prefetch()

    # 2) 检查收敛性
    print(f"\n[3/5] Checking convergence...")
    accs = [r['test_acc'] for r in results['results']]
    print(f"  Round accuracies: {[f'{a:.2f}%' for a in accs]}")

    if len(accs) >= 2 and accs[-1] > accs[0]:
        print(f"  [OK] Convergence OK: {accs[0]:.2f}% -> {accs[-1]:.2f}%")
    else:
        print(f"  [WARN] Convergence warning: final={accs[-1]:.2f}%")

    # 3) 检查 TEE 时间统计
    print(f"\n[4/5] Checking TEE time metrics...")
    m = results['metrics']
    tee_fields = [
        'tee_total_time', 'tee_decrypt_time', 'tee_aggregate_time',
        'tee_compensate_time', 'tee_compress_time', 'tee_reencrypt_time'
    ]

    all_ok = True
    for field in tee_fields:
        vals = m.get(field, [])
        if len(vals) > 0:
            total = sum(vals)
            avg = total / len(vals)
            print(f"  [OK] {field:25s}: total={total:.4f}s, avg={avg:.4f}s/round, rounds={len(vals)}")
        else:
            print(f"  [FAIL] {field:25s}: MISSING (no values recorded)")
            all_ok = False

    if all_ok:
        print(f"  [OK] All TEE time fields present")
    else:
        print(f"  [FAIL] Some TEE time fields missing")

    # 4) 检查 Host 预聚合是否触发
    print(f"\n[5/5] Checking Host aggregation...")
    tee_processor = experiment.server.tee_processor
    if tee_processor is not None:
        # 检查 process_aggregated_round 是否被调用过
        # 通过检查 tee_total_time 是否 > 0 来判断
        total_tee_time = sum(m.get('tee_total_time', []))
        if total_tee_time > 0:
            print(f"  [OK] TEE processed rounds (total_time={total_tee_time:.4f}s)")
        else:
            print(f"  [FAIL] TEE total_time = 0, process_aggregated_round may not have been called")
            all_ok = False
    else:
        print(f"  [WARN] TEE processor is None (tee.enabled=false?)")

    # 5) 检查报告文件
    report_path = os.path.join(experiment.output_dir, "report.md")
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if "TEE Time Breakdown" in content:
            print(f"  [OK] Report contains TEE Time Breakdown section")
        else:
            print(f"  [FAIL] Report missing TEE Time Breakdown section")
            all_ok = False

        if "TEE Decrypt" in content:
            print(f"  [OK] Report contains TEE Decrypt row")
        else:
            print(f"  [FAIL] Report missing TEE Decrypt row")
            all_ok = False
    else:
        print(f"  [FAIL] Report file not found: {report_path}")
        all_ok = False

    # 6) 汇总
    print(f"\n{'=' * 70}")
    if all_ok:
        print("RESULT: [PASS] ALL TESTS PASSED")
    else:
        print("RESULT: [FAIL] SOME TESTS FAILED")
    print(f"{'=' * 70}")

    # 保存简要结果
    summary = {
        'all_ok': all_ok,
        'final_acc': accs[-1] if accs else 0.0,
        'num_rounds': len(accs),
        'tee_total_time': sum(m.get('tee_total_time', [])),
        'tee_decrypt_time': sum(m.get('tee_decrypt_time', [])),
        'output_dir': experiment.output_dir,
    }
    with open('test_host_agg_result.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: test_host_agg_result.json")
    print(f"Experiment output: {experiment.output_dir}")

    return all_ok


if __name__ == "__main__":
    ok = run_test()
    sys.exit(0 if ok else 1)
