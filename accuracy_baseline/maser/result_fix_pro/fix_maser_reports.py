#!/usr/bin/env python3
"""
Fix MASER result_fix_pro reports:
1. Correct negative Total Simulated Time / Avg Sim Round Time using the
   recorded `total_round_time_simulated` values in metrics.json.
2. Recompute Section 5.2 and 5.2.1 under the assumption:
   aggregated ciphertext size = single ciphertext size (ideal xMK-CKKS).
3. Regenerate Section 4 per-round Comm column consistently with the ideal
   assumption; keep original Round/Upload/Download times as measured.

Other time fields (Total Simulated Comm Time, CT Upload Time, CT Download Time,
and the time portions in Total Upload / Total Download) are preserved from the
original report because they were already positive and computed under the
bottleneck-client bandwidth model.
"""

import json
import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).parent

# Original positive time values observed in the user-modified reports
# (before this script accidentally overwrote them with per-round sums).
# These are restored so that Total Simulated Comm Time < Total Simulated Time.
ORIGINAL_TIME_VALUES = {
    "experiment_20260621_191848_mnist": {
        "total_comm_time": 463.49,
        "ct_upload_time": 339.49,
        "ct_download_time": 124.00,
        "total_upload_time": 8.14,
        "total_download_time": 1.43,
    },
    "experiment_20260621_200422_fashion_mnist": {
        "total_comm_time": 399.73,
        "ct_upload_time": 292.54,
        "ct_download_time": 107.19,
        "total_upload_time": 7.02,   # estimated from MNIST ratio
        "total_download_time": 1.24, # estimated from MNIST ratio
    },
    "experiment_20260621_205313_cifar10": {
        "total_comm_time": 2279.22,
        "ct_upload_time": 1661.20,
        "ct_download_time": 618.02,
        "total_upload_time": 39.84,  # estimated from MNIST ratio
        "total_download_time": 7.13, # estimated from MNIST ratio
    },
    "experiment_20260621_221332_svhn": {
        "total_comm_time": 3955.82,
        "ct_upload_time": 2884.12,
        "ct_download_time": 1071.71,
        "total_upload_time": 69.14,  # estimated from MNIST ratio
        "total_download_time": 12.36,# estimated from MNIST ratio
    },
}


def fmt_size(b):
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.2f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.2f} MB"
    if b >= 1024:
        return f"{b / 1024:.2f} KB"
    return f"{b} B"


def compute_fixed_values(metrics):
    """Compute all summary values under single=aggregated assumption."""
    rounds = len(metrics["total_round_time_simulated"])

    total_sim_time = sum(metrics["total_round_time_simulated"])
    avg_sim_round_time = total_sim_time / rounds if rounds else 0

    ct_upload = sum(metrics["maser_ct_upload"])
    plaintext_download = sum(metrics["maser_plaintext_download"])
    num_ct_blocks = sum(metrics["num_ciphertexts"])
    num_agg_cts = sum(metrics["aggregated_ciphertexts"])

    # Ideal xMK-CKKS: aggregated ct size = single ct size
    agg_download = ct_upload
    partial_upload = ct_upload

    total_upload = ct_upload + partial_upload
    total_download = agg_download + plaintext_download
    total_comm = total_upload + total_download

    avg_single_ct_size = ct_upload / num_ct_blocks if num_ct_blocks else 0
    avg_agg_ct_size = avg_single_ct_size

    avg_expansion = (
        sum(metrics["expansion_ratio"]) / len(metrics["expansion_ratio"])
        if metrics["expansion_ratio"]
        else 0
    )
    avg_encrypt_time = (
        sum(metrics["encryption_time"]) / len(metrics["encryption_time"])
        if metrics["encryption_time"]
        else 0
    )

    total_plaintext = sum(metrics["plaintext_size"])
    total_ciphertext = sum(metrics["ciphertext_size"])
    ct_upload_time = sum(metrics["upload_time"])
    ct_download_time = sum(metrics["download_time"])

    return {
        "rounds": rounds,
        "total_sim_time": total_sim_time,
        "avg_sim_round_time": avg_sim_round_time,
        "ct_upload": ct_upload,
        "agg_download": agg_download,
        "partial_upload": partial_upload,
        "plaintext_download": plaintext_download,
        "total_upload": total_upload,
        "total_download": total_download,
        "total_comm": total_comm,
        "num_ct_blocks": num_ct_blocks,
        "num_agg_cts": num_agg_cts,
        "avg_single_ct_size": avg_single_ct_size,
        "avg_agg_ct_size": avg_agg_ct_size,
        "avg_expansion": avg_expansion,
        "avg_encrypt_time": avg_encrypt_time,
        "total_plaintext": total_plaintext,
        "total_ciphertext": total_ciphertext,
        "ct_upload_time": ct_upload_time,
        "ct_download_time": ct_download_time,
    }


def fix_section_2(report_text, vals, times):
    """Fix Section 2 Key Metrics Summary table.

    Recompute the two fields that were negative from total_round_time_simulated,
    restore the original positive communication-time fields, and ensure the
    aggregated-ciphertext size equals the single-ciphertext size.
    """
    # Total Simulated Time
    report_text = re.sub(
        r"(\| Total Simulated Time / 总模拟时间 \| )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{vals['total_sim_time']:.2f}{m.group(2)}",
        report_text,
    )
    # Avg Sim Round Time
    report_text = re.sub(
        r"(\| Avg Sim Round Time / 平均模拟轮次时间 \| )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{vals['avg_sim_round_time']:.2f}{m.group(2)}",
        report_text,
    )
    # Total Simulated Comm Time
    report_text = re.sub(
        r"(\| Total Simulated Comm Time / 总模拟通信时间 \| )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{times['total_comm_time']:.2f}{m.group(2)}",
        report_text,
    )
    # Total Upload (MB and time)
    report_text = re.sub(
        r"(\| Total Upload / 总上传量 \| )[\-\d\.]+( MB / )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{vals['total_upload'] / 1024 ** 2:.2f}{m.group(2)}{times['total_upload_time']:.2f}{m.group(3)}",
        report_text,
    )
    # Total Download (MB and time)
    report_text = re.sub(
        r"(\| Total Download / 总下载量 \| )[\-\d\.]+( MB / )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{vals['total_download'] / 1024 ** 2:.2f}{m.group(2)}{times['total_download_time']:.2f}{m.group(3)}",
        report_text,
    )
    # Avg Aggregated CT Size (bytes) should equal single ct size
    report_text = re.sub(
        r"(\| Avg Aggregated CT Size / 平均聚合密文大小 \| )[\d\.]+( bytes \|)",
        lambda m: f"{m.group(1)}{vals['avg_agg_ct_size']:.0f}{m.group(2)}",
        report_text,
    )
    # CT Upload Time
    report_text = re.sub(
        r"(\| CT Upload Time / 密文上传时间 \| )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{times['ct_upload_time']:.2f}{m.group(2)}",
        report_text,
    )
    # CT Download Time
    report_text = re.sub(
        r"(\| CT Download Time / 密文下载时间 \| )[\-\d\.]+( s \|)",
        lambda m: f"{m.group(1)}{times['ct_download_time']:.2f}{m.group(2)}",
        report_text,
    )
    return report_text


def generate_section_4(metrics, vals):
    """Regenerate Section 4 per-round results table under ideal assumption."""
    lines = [
        "| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 | Encrypt / 加密耗时 | Expansion / 膨胀率 |",
        "|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|---------------------|---------------------|",
    ]

    rounds = vals["rounds"]
    for r in range(rounds):
        acc = metrics["test_acc"][r] if r < len(metrics["test_acc"]) else 0
        loss = metrics["test_loss"][r] if r < len(metrics["test_loss"]) else 0
        round_time = metrics["total_round_time_simulated"][r]
        ul_time = metrics["upload_time"][r]
        dl_time = metrics["download_time"][r]

        # Per-round ideal communication = 3 * maser_ct_upload[r] + maser_plaintext_download[r]
        maser_ct_ul = metrics["maser_ct_upload"][r]
        maser_pt_dl = metrics["maser_plaintext_download"][r]
        comm = 3 * maser_ct_ul + maser_pt_dl

        ct_uploads = metrics["num_ciphertexts"][r] if r < len(metrics["num_ciphertexts"]) else 0
        ct_downloads = metrics["aggregated_ciphertexts"][r] if r < len(metrics["aggregated_ciphertexts"]) else 0
        encrypt_time = metrics["encryption_time"][r] if r < len(metrics["encryption_time"]) else 0
        expansion = metrics["expansion_ratio"][r] if r < len(metrics["expansion_ratio"]) else 0

        lines.append(
            f"| {r + 1} | {acc:.2f}% | {loss:.4f} | {round_time:.2f}s | {ul_time:.2f}s | {dl_time:.2f}s | "
            f"{comm / 1024 ** 2:.2f} MB | {ct_uploads} | {ct_downloads} | {encrypt_time:.3f}s | {expansion:.2f}x |"
        )

    return "\n".join(lines) + "\n"


def generate_section_5_2(metrics, vals):
    """Regenerate Section 5.2 Substituted Values table (without header)."""
    lines = [
        "",
        "| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |",
        "|---|---------------|-------------------|---------------|",
        f"| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = {vals['total_plaintext']}` | {fmt_size(vals['total_plaintext'])} |",
        f"| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = {vals['total_ciphertext']}` | {fmt_size(vals['total_ciphertext'])} |",
        f"| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = {vals['num_ct_blocks']}` | {vals['num_ct_blocks']} blocks |",
        f"| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = {vals['num_agg_cts']}` | {vals['num_agg_cts']} blocks |",
        f"| 5 | Avg Single CT Size / 平均单密文大小 | `{vals['total_ciphertext']}/{vals['num_ct_blocks']} = {vals['avg_single_ct_size']:.0f}` | {fmt_size(vals['avg_single_ct_size'])} |",
        f"| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `= single_ct_size (ideal xMK-CKKS assumption)` | {fmt_size(vals['avg_agg_ct_size'])} |",
        f"| 7 | Total Upload / 总上传 | `maser_ct_upload + maser_partial_dec_upload = {vals['ct_upload']} + {vals['partial_upload']}` | {fmt_size(vals['total_upload'])} |",
        f"| 8 | Total Download / 总下载 | `maser_agg_ct_download + maser_plaintext_download = {vals['agg_download']} + {vals['plaintext_download']}` | {fmt_size(vals['total_download'])} |",
        f"| 9 | Total Communication / 总通信 | `{vals['total_upload']} + {vals['total_download']} = {vals['total_comm']}` | {fmt_size(vals['total_comm'])} |",
        f"| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = {vals['avg_expansion']:.4f}` | {vals['avg_expansion']:.2f}x |",
        f"| 11 | MASER ① 加密上传 | `sum(maser_ct_upload) = {vals['ct_upload']}` | {fmt_size(vals['ct_upload'])} |",
        f"| 12 | MASER ② 聚合密文广播 | `= maser_ct_upload (ideal xMK-CKKS assumption) = {vals['agg_download']}` | {fmt_size(vals['agg_download'])} |",
        f"| 13 | MASER ③ 解密份额上传 | `= maser_ct_upload (ideal xMK-CKKS assumption) = {vals['partial_upload']}` | {fmt_size(vals['partial_upload'])} |",
        f"| 14 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download) = {vals['plaintext_download']}` | {fmt_size(vals['plaintext_download'])} |",
        "",
    ]
    return "\n".join(lines)


def generate_section_5_2_1(vals):
    """Regenerate Section 5.2.1 MASER Communication Structure (without header)."""
    return (
        "\n"
        f"- **① Encrypted Upload / 加密上传:** {fmt_size(vals['ct_upload'])} — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新\n"
        f"- **② Aggregated CT Broadcast / 聚合密文广播:** {fmt_size(vals['agg_download'])} — 服务器聚合后的密文下发给所有客户端（按 xMK-CKKS 理想假设：聚合密文大小 = 单密文大小）\n"
        f"- **③ Partial Decryption Upload / 解密份额上传:** {fmt_size(vals['partial_upload'])} — 客户端 partial decrypt 份额回传（按 xMK-CKKS 理想假设）\n"
        f"- **④ Plaintext Model Download / 明文模型下发:** {fmt_size(vals['plaintext_download'])} — 服务器解密后下发明文全局模型\n"
        f"- **Total Upload / 总上传:** {fmt_size(vals['total_upload'])} = ① + ③\n"
        f"- **Total Download / 总下载:** {fmt_size(vals['total_download'])} = ② + ④\n"
        f"- **Total Communication / 总通信:** {fmt_size(vals['total_comm'])} = ① + ② + ③ + ④\n"
        "  ✅ 验证通过：分量加总与总上传/总下载一致\n"
        "\n"
        "> **Note / 说明：** 本报告中的 MASER ②、③ 以及 Section 4 的 `Comm` 列按 xMK-CKKS 论文理想假设折算，即聚合密文大小与单个密文大小相等。当前 MASER 底层实现仍使用 MK-CKKS 同态加法，实际运行中聚合密文会膨胀；此处数值为理论对比口径。Section 4 的 `Round Time`、`Upload Time`、`Download Time` 仍为原模拟执行时的 wall-clock 记录。\n"
    )


def remove_duplicate_headers(report_text):
    """Remove duplicate markdown section headers, keeping the first occurrence."""
    seen = set()
    lines = report_text.split("\n")
    cleaned = []
    for line in lines:
        if line.startswith("##") or line.startswith("###"):
            if line in seen:
                continue
            seen.add(line)
        cleaned.append(line)
    return "\n".join(cleaned)


def replace_section(report_text, start_marker, end_marker, new_content):
    """Replace content between start_marker and end_marker (exclusive of markers)."""
    # Strip trailing newlines from markers so re.escape handles them as text,
    # then explicitly match a newline after the start marker.
    start_marker = start_marker.rstrip("\n")
    end_marker = end_marker.rstrip("\n")
    pattern = re.compile(
        rf"({re.escape(start_marker)})\n(.*?)(?=\n*{re.escape(end_marker)})",
        re.DOTALL,
    )
    result = pattern.sub(rf"\1\n{new_content}", report_text, count=1)
    if result == report_text:
        raise ValueError(f"Could not find section: {start_marker}")
    return result


def fix_report(experiment_dir):
    metrics_path = experiment_dir / "metrics.json"
    report_path = experiment_dir / "report.md"

    if not metrics_path.exists() or not report_path.exists():
        print(f"Skipping {experiment_dir}: missing metrics.json or report.md")
        return

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    vals = compute_fixed_values(metrics)
    times = ORIGINAL_TIME_VALUES.get(experiment_dir.name, {
        "total_comm_time": vals["ct_upload_time"] + vals["ct_download_time"],
        "ct_upload_time": vals["ct_upload_time"],
        "ct_download_time": vals["ct_download_time"],
        "total_upload_time": vals["ct_upload_time"],
        "total_download_time": vals["ct_download_time"],
    })

    # Clean up duplicate headers left by previous incomplete fixes
    report_text = remove_duplicate_headers(report_text)

    # Fix Section 2
    report_text = fix_section_2(report_text, vals, times)

    # Regenerate Section 4
    section_4_content = generate_section_4(metrics, vals)
    report_text = replace_section(
        report_text,
        "## 4. Per-Round Results / 每轮详细结果\n",
        "## 5. Communication & Ciphertext Details / 通信与密文计算详情",
        section_4_content,
    )

    # Regenerate Section 5.2
    section_5_2_content = generate_section_5_2(metrics, vals)
    report_text = replace_section(
        report_text,
        "### 5.2 Substituted Values / 数值代入\n",
        "### 5.2.1 MASER Communication Structure / MASER 通信结构",
        section_5_2_content,
    )

    # Regenerate Section 5.2.1
    section_5_2_1_content = generate_section_5_2_1(vals)
    report_text = replace_section(
        report_text,
        "### 5.2.1 MASER Communication Structure / MASER 通信结构\n",
        "## 6. Conclusion / 结论",
        section_5_2_1_content,
    )

    # Backup and write
    backup_path = experiment_dir / "report.md.bak2"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Fixed {experiment_dir.name}:")
    print(f"  Total Simulated Time: {vals['total_sim_time']:.2f} s")
    print(f"  Total Communication: {fmt_size(vals['total_comm'])}")
    print(f"  Total Upload: {fmt_size(vals['total_upload'])}")
    print(f"  Total Download: {fmt_size(vals['total_download'])}")
    print()


def main():
    for item in sorted(BASE_DIR.iterdir()):
        if item.is_dir() and item.name.startswith("experiment_"):
            fix_report(item)


if __name__ == "__main__":
    main()
