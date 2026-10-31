#!/usr/bin/env python3
"""
整理 ESP 消融实验结果（SVHN, LS=0.5, RK=0.7）。

- 从 6 个 *_fix 实验目录的 metrics.json 中提取最终准确率、总上传量、总训练时间
- 生成 esp_ablation_data.json
- 生成 esp_ablation_table.tex
- 调用 plot_esp_ablation.py 更新 pic/esp_ablation.{png,pdf}
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

EXPERIMENT_ORDER = [
    ("06_no_sparse",       "w/o ESP",             {"LS": False, "RF": False, "PRD": False, "CRD": False, "RK": False}),
    ("01_sparse_only",     "+ LS",                {"LS": True,  "RF": False, "PRD": False, "CRD": False, "RK": False}),
    ("02_sparse_residual", "+ LS + RF",           {"LS": True,  "RF": True,  "PRD": False, "CRD": False, "RK": False}),
    ("03_sparse_residual_decay", "+ LS + RF + PRD", {"LS": True, "RF": True, "PRD": True,  "CRD": False, "RK": False}),
    ("04_sparse_residual_decay_stale", "+ LS + RF + PRD + CRD", {"LS": True, "RF": True, "PRD": True, "CRD": True, "RK": False}),
    ("05_esp_full",        "ESP (full)",          {"LS": True,  "RF": True,  "PRD": True,  "CRD": True, "RK": True}),
]


def find_metrics_path(exp_name: str) -> Path:
    exp_dir = SCRIPT_DIR / f"{exp_name}_fix"
    if not exp_dir.exists():
        raise FileNotFoundError(f"找不到实验目录: {exp_dir}")
    candidates = sorted(exp_dir.glob("experiment_*/metrics.json"))
    if not candidates:
        raise FileNotFoundError(f"{exp_dir} 下没有 metrics.json")
    return candidates[-1]


def find_config_path(exp_name: str) -> Path:
    exp_dir = SCRIPT_DIR / f"{exp_name}_fix"
    candidates = sorted(exp_dir.glob("experiment_*/config.yaml"))
    if not candidates:
        return None
    return candidates[-1]


def extract_metrics(exp_name: str) -> dict:
    metrics_path = find_metrics_path(exp_name)
    with open(metrics_path, encoding="utf-8") as f:
        m = json.load(f)

    final_acc = float(m["test_acc"][-1])
    total_upload_mb = sum(m.get("upload_cost", [])) / (1024 ** 2)
    total_train_h = sum(m.get("local_train_time", [])) / 3600.0

    return {
        "AC": round(final_acc, 2),
        "UV_MB": round(total_upload_mb, 2),
        "TT_H": round(total_train_h, 2),
    }


def build_data() -> dict:
    data = {
        "dataset": "SVHN",
        "model": "ResNet20",
        "note": "LS = 0.5, RK = 0.7",
        "components": {
            "LS": {"enabled": True, "param": 0.5, "description": "Local Sparsification"},
            "RF": {"enabled": True, "description": "Residual Feedback"},
            "PRD": {"enabled": True, "param": 0.3, "description": "Partial Residual Decay"},
            "CRD": {"enabled": True, "param": 0.5, "description": "Client Residual Decay (stale)"},
            "RK": {"enabled": True, "param": 0.7, "description": "Ranking-based Knowledge aggregation"},
        },
        "experiments": [],
    }

    for exp_name, label, comps in EXPERIMENT_ORDER:
        metrics = extract_metrics(exp_name)
        exp = {
            "id": exp_name,
            "label": label,
            **comps,
            **metrics,
        }
        data["experiments"].append(exp)

    return data


def backup_old_files():
    """如果存在旧文件，备份为 *_ls0.1.* 或带时间戳版本。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for fname in ["esp_ablation_data.json", "esp_ablation_table.tex"]:
        src = SCRIPT_DIR / fname
        if src.exists():
            stem = src.stem
            dst = SCRIPT_DIR / f"{stem}_backup_{timestamp}{src.suffix}"
            shutil.copy2(src, dst)
            print(f"[BACKUP] {src.name} -> {dst.name}")


def save_data(data: dict):
    data_path = SCRIPT_DIR / "esp_ablation_data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[SAVED] {data_path}")


def generate_table(data: dict) -> str:
    note = data["note"]
    exps = data["experiments"]

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{Ablation Study of the ESP Module Components ({data['dataset']}, {note})}}",
        rf"\label{{tab:esp_ablation_{data['dataset'].lower()}}}",
        r"\resizebox{\linewidth}{!}{",
        r"\begin{tabular}{ccccc ccc}",
        r"\toprule",
        r"\multicolumn{5}{c}{\textbf{\textit{ESP Components}}} & \multicolumn{3}{c}{\textbf{\textit{Performance Metrics}}} \\",
        r"\cmidrule(lr){1-5} \cmidrule(lr){6-8}",
        r"\scriptsize \textbf{LS (0.5)} & \scriptsize \textbf{RF} & \scriptsize \textbf{PRD (0.3)} & \scriptsize \textbf{CRD (0.5)} & \scriptsize \textbf{RK (0.7)} &",
        r"\scriptsize \textbf{AC (\%)} & \scriptsize \textbf{UV (MB)} & \scriptsize \textbf{TT (H)} \\",
        r"\midrule",
    ]

    for i, exp in enumerate(exps):
        sym = lambda key: r"$\checkmark$" if exp[key] else r"$\times$"
        ac_str = f"{exp['AC']:.2f}"
        uv_str = f"{exp['UV_MB']:.1f}"
        tt_str = f"{exp['TT_H']:.2f}"
        if exp["id"] == "05_esp_full":
            ac_str = r"\textbf{" + ac_str + r"}"
            uv_str = r"\textbf{" + uv_str + r"}"
            tt_str = r"\textbf{" + tt_str + r"}"
        row_fields = [sym("LS"), sym("RF"), sym("PRD"), sym("CRD"), sym("RK"), ac_str, uv_str, tt_str]
        row = " & ".join(row_fields) + " \\\\"
        if exp["id"] == "05_esp_full":
            row = r"\rowcolor{gray!15}" + "\n" + row
        lines.append(row)

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def save_table(tex: str):
    tex_path = SCRIPT_DIR / "esp_ablation_table.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tex)
    print(f"[SAVED] {tex_path}")


def run_plot():
    plot_script = SCRIPT_DIR / "plot_esp_ablation.py"
    if not plot_script.exists():
        print(f"[WARN] 绘图脚本不存在: {plot_script}")
        return
    try:
        subprocess.run([PYTHON, str(plot_script)], cwd=SCRIPT_DIR, check=True)
        print("[PLOT] 图表已更新")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 绘图失败: {e}")


def main():
    backup_old_files()
    data = build_data()
    save_data(data)
    tex = generate_table(data)
    save_table(tex)
    run_plot()
    print("\n[DONE] 实验数据整理完成")


if __name__ == "__main__":
    main()
