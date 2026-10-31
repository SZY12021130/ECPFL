"""
串行执行 FMNIST 15 轮自适应投票实验。
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "accuracy_baseline" / "adaptive" / "configs"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
PYTHON = sys.executable

EXPERIMENTS = [
    {"name": "baseline_fmnist_15r",        "desc": "静态 topk=0.3 基线（15轮）"},
    {"name": "adaptive_cosine_fmnist_15r", "desc": "余弦退火自适应 topk（15轮）"},
    {"name": "adaptive_accuracy_fmnist_15r", "desc": "准确率触发自适应 topk（15轮）"},
    {"name": "adaptive_consensus_fmnist_15r", "desc": "投票共识度自适应 threshold（15轮）"},
]


def run_experiment(exp: dict) -> bool:
    config_path = CONFIG_DIR / f"config_{exp['name']}.yaml"
    print("\n" + "=" * 70)
    print(f"[START] {exp['name']}: {exp['desc']}")
    print(f"[CONFIG] {config_path}")
    print("=" * 70)

    env = os.environ.copy()
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    cmd = [PYTHON, str(MAIN_SCRIPT), "--config", str(config_path)]
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, env=env)
        print(f"[SUCCESS] {exp['name']} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {exp['name']} 失败: {e}")
        return False


def main():
    if not MAIN_SCRIPT.exists():
        raise FileNotFoundError(f"找不到主程序: {MAIN_SCRIPT}")

    results = []
    for exp in EXPERIMENTS:
        success = run_experiment(exp)
        results.append((exp["name"], success))

    print("\n" + "=" * 70)
    print("[SUMMARY] 自适应投票实验执行汇总")
    print("=" * 70)
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"  {name:<40s} {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
