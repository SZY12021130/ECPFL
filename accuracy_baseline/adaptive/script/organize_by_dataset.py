#!/usr/bin/env python3
"""
将 accuracy_baseline/adaptive/ 下的 FMNIST 实验按数据集分类整理到
accuracy_baseline/adaptive/fashion_mnist/ 子目录中，并更新注册表路径。
同时删除未注册/未完成的测试目录。
"""

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ADAPTIVE_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive"

# 已注册实验的时间戳集合
REGISTRY_PATH = ADAPTIVE_DIR / "experiments_registry.json"


def load_registry(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_registry(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def main():
    entries = load_registry(REGISTRY_PATH)
    registered_timestamps = {e["timestamp"] for e in entries}

    dataset_dir = ADAPTIVE_DIR / "fashion_mnist"
    dataset_dir.mkdir(exist_ok=True)

    # 1) 删除未注册且无 metrics.json 的实验目录
    removed = []
    for exp_dir in sorted(ADAPTIVE_DIR.glob("experiment_*")):
        if exp_dir.is_dir():
            # experiment_YYYYMMDD_HHMMSS_<dataset>
        parts = exp_dir.name.split("_")
        ts = "_".join(parts[1:3]) if len(parts) >= 3 else ""
            if ts not in registered_timestamps or not (exp_dir / "metrics.json").exists():
                shutil.rmtree(exp_dir)
                removed.append(exp_dir.name)
    if removed:
        print(f"已删除 {len(removed)} 个未注册/未完成的目录:")
        for name in removed:
            print(f"  - {name}")

    # 2) 移动已注册的 FMNIST 实验目录到 fashion_mnist/
    moved_exps = []
    for entry in entries:
        old_output = Path(entry["output_dir"])
        # 可能已经是相对路径或绝对路径
        if not old_output.is_absolute():
            old_output = PROJECT_ROOT / old_output
        if old_output.exists() and old_output.parent == ADAPTIVE_DIR:
            new_output = dataset_dir / old_output.name
            shutil.move(str(old_output), str(new_output))
            entry["output_dir"] = str(new_output.relative_to(PROJECT_ROOT))
            moved_exps.append(old_output.name)

    # 3) 移动模型目录
    old_model_dir = ADAPTIVE_DIR / "models"
    new_model_dir = dataset_dir / "models"
    if old_model_dir.exists():
        if new_model_dir.exists():
            # 合并：将旧模型子目录移入
            for sub in old_model_dir.iterdir():
                dest = new_model_dir / sub.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(sub), str(dest))
            # 如果旧目录为空则删除
            try:
                old_model_dir.rmdir()
            except OSError:
                pass
        else:
            shutil.move(str(old_model_dir), str(new_model_dir))

    # 4) 移动 FMNIST 对比图表
    for fname in [
        "adaptive_comparison.md",
        "adaptive_comparison.png",
        "adaptive_comparison_15r.png",
        "adaptive_comparison_50r.png",
        "adaptive_15v50_accuracy.png",
    ]:
        src = ADAPTIVE_DIR / fname
        if src.exists():
            shutil.move(str(src), str(dataset_dir / fname))

    # 5) 保存更新后的注册表到 fashion_mnist/，并清空旧注册表
    if entries:
        save_registry(dataset_dir / "experiments_registry.json", entries)
        REGISTRY_PATH.write_text("[]", encoding="utf-8")
        print(f"已移动 {len(moved_exps)} 个实验到 {dataset_dir.relative_to(PROJECT_ROOT)}")
        print(f"注册表已更新: {dataset_dir / 'experiments_registry.json'}")


if __name__ == "__main__":
    main()
