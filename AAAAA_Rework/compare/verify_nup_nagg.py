#!/usr/bin/env python3
"""从准确率实验中统计每轮密文块数 N_up / N_agg，验证 perf_evaluation 表。

口径（与旧表一致）：
- N_up = 每轮全部选中客户端上传的密文块总数（FedPHE 只计入选块；ECPFL 单列投票密文）
- N_agg = 服务器聚合后每个客户端下载的密文块数（= 模型更新块数 / 共识包数 K）
- 所有方法均为单密文结构：一个密文块 = 一个多项式系数序列（a 由 PRPG 再生不传输）
"""
import json
import re
from pathlib import Path

ROOT = Path("E:/GithubProjects/ckks_fed_robustness")
ROUNDS = 50
N_SEL = 25  # 50 clients × 0.5 sampling


def from_report(path: Path):
    text = path.read_text(encoding="utf-8")
    up = re.search(r"Total CT Blocks \(Upload\).*?\| (\d+) blocks", text)
    # 每轮上传块数
    n_up_round = int(up.group(1)) / ROUNDS if up else None
    return n_up_round


def ecpfl_from_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    rounds = data["rounds"]
    n = len(rounds)
    ct = None
    # 反推 ct 字节数：round 里 upload_bytes = (|S| + num_enc + comp) * ct
    r0 = rounds[0]
    Ks = [r["K"] for r in rounds]
    num_sel = len(r0["active_set"])
    # num_enc = num_sel * K (每客户端对每个共识包一个密文)
    num_enc = [len(r["active_set"]) * r["K"] for r in rounds]
    comp = [len(r.get("dropouts", [])) for r in rounds]
    # ct = upload_bytes / (num_sel + num_enc + comp)
    cts = [r["upload_bytes"] / (len(r["active_set"]) + ne + c)
           for r, ne, c in zip(rounds, num_enc, comp)]
    ct = sum(cts) / len(cts)
    n_up_pack = sum(num_enc) / n          # 每轮 pack 密文总数
    n_up_vote = sum(len(r["active_set"]) for r in rounds) / n  # 每轮投票密文
    n_agg = sum(Ks) / n                    # 每轮共识包数 = 下载块数
    uv_mb = data["total_upload_mb"] / ROUNDS
    return dict(n_up_pack=n_up_pack, n_up_vote=n_up_vote, n_agg=n_agg,
                K_list=Ks, ct_bytes=ct, uv_per_round_mb=uv_mb)


def ecpfl_full_upload(path: Path):
    """ECPFL 含投票的总上传密文块/轮。"""
    d = ecpfl_from_json(path)
    return d["n_up_pack"] + d["n_up_vote"]


BASE = {
    "FedAvg+CKKS": {
        "mnist": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10/report.md",
        "svhn": "accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn/report.md",
    },
    "FedPHE": {
        "mnist": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10/report.md",
        "svhn": "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn/report.md",
    },
    "ESAFL": {
        "mnist": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_163033_mnist/report.md",
        "fashion_mnist": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_203351_fashion_mnist/report.md",
        "cifar10": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_210302_cifar10/report.md",
        "svhn": "AAAAA_Rework/ESAFL/result/accuracy_n25_c1/experiment_20261102_221916_svhn/report.md",
    },
    "MASER": {
        "mnist": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/report.md",
        "fashion_mnist": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist/report.md",
        "cifar10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10/report.md",
        "svhn": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn/report.md",
    },
}

ECPFL = {
    "mnist_rk": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_123327_mnist/ecpfl_results.json",
    "fashion_mnist_rk_old_z03": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_192222_fashion_mnist/ecpfl_results.json",
    "cifar10_th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261103_210440_cifar10/ecpfl_results.json",
    "svhn_th": "AAAAA_Rework/ECPFL/result/accuracy/experiment_20261104_011747_svhn/ecpfl_results.json",
}

print("=" * 90)
print("基线方法（report.md）：N_up = 每轮上传块总数，N_agg = N_up / 25（每客户端下载块数）")
print("=" * 90)
for method, ds_map in BASE.items():
    for ds, rel in ds_map.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{method:12s} {ds:14s}  [缺失]")
            continue
        n_up = from_report(p)
        n_agg = n_up / N_SEL if n_up else None
        print(f"{method:12s} {ds:14s}  N_up/round={n_up:8.1f}   N_agg={n_agg:6.2f}")

print()
print("=" * 90)
print("ECPFL（ecpfl_results.json）：N_up 分 pack 密文 与 投票密文 两列")
print("=" * 90)
for label, rel in ECPFL.items():
    p = ROOT / rel
    if not p.exists():
        print(f"{label:28s}  [缺失]")
        continue
    d = ecpfl_from_json(p)
    print(f"{label:28s}  N_up(pack)/r={d['n_up_pack']:7.1f}  N_up(vote)/r={d['n_up_vote']:5.1f}  "
          f"N_agg(K)={d['n_agg']:5.2f}  ct={d['ct_bytes']:.0f}B  UV/r={d['uv_per_round_mb']:.2f}MB")
    print(f"{'':28s}  K per round (first 10): {d['K_list'][:10]}")
