"""Run all MASER multi-key baseline experiments sequentially (one dataset at a time) in GPU conda env."""
import subprocess
import sys
import os
import yaml

os.chdir(r"E:\GithubProjects\ckks_fed_robustness")

# Fix Windows joblib wmic compatibility issue
os.environ['LOKY_MAX_CPU_COUNT'] = '8'

# GPU conda environment Python (concrete-env)
PYTHON = [r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe"]
MAIN_PY = "main.py"

PROJECT_ROOT = r"E:\GithubProjects\ckks_fed_robustness"

baselines = [
    {
        "name": "MASER-SK-SimMK",
        "config_dir": "accuracy_baseline/maser/config",
        "output_dir": "accuracy_baseline/maser/result_fix_pro",
        "datasets": ["mnist", "fashionmnist", "cifar10", "svhn"],
        "num_rounds": 50,
    },
]


def make_temp_config(src_config_path: str, output_dir: str, num_rounds: int) -> str:
    """复制配置并覆盖 num_rounds，返回临时配置文件路径。"""
    with open(src_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['system']['num_rounds'] = num_rounds

    # 确保 fedfetch 带宽 trace 使用绝对路径
    bw_cfg = config.get('bandwidth', {})
    trace_path = bw_cfg.get('fedfetch_trace_path')
    if trace_path and not os.path.isabs(trace_path):
        abs_trace = os.path.join(PROJECT_ROOT, trace_path)
        if os.path.exists(abs_trace):
            bw_cfg['fedfetch_trace_path'] = abs_trace

    os.makedirs(output_dir, exist_ok=True)
    tmp_path = os.path.join(output_dir, f"tmp_{os.path.basename(src_config_path)}")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    return tmp_path


for baseline in baselines:
    for ds in baseline["datasets"]:
        src_config = os.path.join(baseline["config_dir"], f"config_{ds}.yaml")
        output_dir = baseline["output_dir"]
        num_rounds = baseline.get("num_rounds", 5)

        if not os.path.exists(src_config):
            print(f"WARNING: config not found: {src_config}")
            continue

        tmp_config = make_temp_config(src_config, output_dir, num_rounds)

        print(f"\n{'='*60}")
        print(f"Running {baseline['name']} - {ds}")
        print(f"Config: {src_config}")
        print(f"Temp Config: {tmp_config}")
        print(f"Output: {output_dir}")
        print(f"Rounds: {num_rounds}")
        print(f"Python: {PYTHON[0]}")
        print(f"{'='*60}\n")
        sys.stdout.flush()

        result = subprocess.run(
            PYTHON + [MAIN_PY, "--config", tmp_config, "--output-dir", output_dir],
            cwd=PROJECT_ROOT,
        )

        if result.returncode != 0:
            print(f"WARNING: {baseline['name']} - {ds} exited with code {result.returncode}")
        else:
            print(f"DONE: {baseline['name']} - {ds}")

print("\nAll experiments completed!")
