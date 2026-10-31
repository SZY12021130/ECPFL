#!/usr/bin/env python3
"""
FedPHE 独立项目运行助手
- 统一参数映射，生成可直接运行的命令行
- 轻量 hook server.py 以记录下行通信量
- 实验完成后解析日志并输出结构化 metrics.json

Usage:
    # 1. 生成命令并提示用户手动运行（推荐，避免 Windows 多进程残留问题）
    python scripts/baseline_comparison/run_fedphe_standalone.py

    # 2. 实验跑完后，解析已有日志
    python scripts/baseline_comparison/run_fedphe_standalone.py --parse-only
"""

import os
import sys
import re
import yaml
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEDPHE_ROOT = PROJECT_ROOT / "FedPHE-main"
SERVER_PY = FEDPHE_ROOT / "server.py"
PARAMS_PATH = PROJECT_ROOT / "scripts" / "baseline_comparison" / "baseline_params.yaml"
RESULTS_DIR = PROJECT_ROOT / "results" / "baseline_fedphe_standalone"

# ---------------------------------------------------------------------------
# 1. 轻量 hook：在 server.py 中插入下行通信量统计（最小侵入）
# ---------------------------------------------------------------------------
HOOK_MARKER = "# [BASELINE_HOOK] download size logging"
HOOK_CODE = '''
        # [BASELINE_HOOK] download size logging
        if args.enc and args.cipher_count:
            import pickle
            dl_size = 0
            if isinstance(agg_res, list):
                for c in agg_res:
                    if isinstance(c, bytes):
                        dl_size += len(c)
                    else:
                        dl_size += len(pickle.dumps(c))
            logging('server send: download size:{} bytes'.format(dl_size), args)
'''


def patch_server_py():
    """在 server.py 的 queue.put 之后插入下行统计代码。"""
    with open(SERVER_PY, "r", encoding="utf-8") as f:
        content = f.read()

    if HOOK_MARKER in content:
        print("[INFO] server.py 已包含 hook，跳过 patch")
        return

    target = "        # The aggregated content has been sent and can be read by the client\n        e.set()"
    if target not in content:
        print("[WARN] 无法在 server.py 中定位 hook 插入点，跳过下行统计（上行仍可用）")
        return

    new_content = content.replace(target, HOOK_CODE + "\n" + target)
    backup = SERVER_PY.with_suffix(".py.bak")
    if not backup.exists():
        shutil.copy2(SERVER_PY, backup)
    with open(SERVER_PY, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("[INFO] 已 patch server.py 添加下行通信量统计")


def restore_server_py():
    """恢复原 server.py。"""
    backup = SERVER_PY.with_suffix(".py.bak")
    if backup.exists():
        shutil.copy2(backup, SERVER_PY)
        print("[INFO] 已恢复 server.py")


# ---------------------------------------------------------------------------
# 2. 参数映射与命令行构造
# ---------------------------------------------------------------------------
def build_cmd(params: dict) -> list:
    """将统一参数映射到 FedPHE-main/main.py 的命令行参数。"""
    fp = params.get("fedphe", {})

    dataset_map = {
        "mnist": "MNIST",
        "fashion_mnist": "FashionMNIST",
        "cifar10": "CIFAR10",
        "cifar100": "CIFAR100",
    }
    fedphe_dataset = dataset_map.get(params["dataset"].lower(), params["dataset"])

    cmd = [
        sys.executable, str(FEDPHE_ROOT / "main.py"),
        "--dataset", fedphe_dataset,
        "--batch-size", str(params["batch_size"]),
        "--epochs", str(params["num_rounds"]),
        "--local_epochs", str(params["local_epochs"]),
        "--lr", str(params["learning_rate"]),
        "--n_clients", str(params["num_clients"]),
        "--momentum", str(params.get("momentum", 0.9)),
        "--alpha", str(params["alpha"]),
        "--split", "noniid" if not params["iid"] else "iid",
        "--noniid_method", "dirichlet",
        "--seed", str(params["random_seed"]),
        "--isSpars", fp.get("isSpars", "topk"),
        "--topk", str(fp.get("topk", 0.1)),
        "--enc", "True" if fp.get("enc", True) else "False",
        "--isSelection", "True" if fp.get("isSelection", False) else "False",
        "--isBatch", "True" if fp.get("isBatch", True) else "False",
        "--cipher_count", "True" if fp.get("cipher_count", True) else "False",
        "--algorithm", fp.get("algorithm", "ckks"),
        "--quan_bits", str(fp.get("quan_bits", 16)),
        "--enc_batch_size", str(fp.get("enc_batch_size", 4096)),
        "--sim_len", str(fp.get("sim_len", 200)),
        "--sgm", str(fp.get("sgm", 0.3)),
        "--n_shards", str(fp.get("n_shards", 5)),
    ]
    return cmd


def print_run_command(cmd: list, env_vars: dict):
    """打印可直接复制运行的命令（含环境变量）。"""
    print("\n" + "=" * 70)
    print("[FedPHE 独立项目运行命令]")
    print("=" * 70)
    env_str = " ".join(f"set {k}={v}" for k, v in env_vars.items())
    cmd_str = " ".join(str(c) for c in cmd)
    if env_str:
        print(f"{env_str} && {cmd_str}")
    else:
        print(cmd_str)
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# 3. 日志解析
# ---------------------------------------------------------------------------
def parse_log(log_path: Path) -> dict:
    """解析 FedPHE-main 的日志文件，提取每轮指标。"""
    if not log_path.exists():
        raise FileNotFoundError(f"日志文件不存在: {log_path}")

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    metrics = {
        "rounds": [],
        "test_acc": [],
        "test_loss": [],
        "upload_cost": [],
        "download_cost": [],
        "total_communication_cost": [],
        "time_cost": [],
    }

    ul_pattern = re.compile(r"server receive: ciphertext size:(\d+) bytes")
    dl_pattern = re.compile(r"server send: download size:(\d+) bytes")
    acc_pattern = re.compile(r"Server epoch (\d+), Clients accuracy:.*?([\d.]+).*?, loss:.*?([\d.]+).*?%")
    time_pattern = re.compile(r"time\s*[:=]\s*([\d.]+)s")
    time_list_pattern = re.compile(r"time list:\[.*?([\d.]+).*?\]s")

    ul_matches = ul_pattern.findall(text)
    dl_matches = dl_pattern.findall(text)
    acc_matches = acc_pattern.findall(text)
    time_matches = time_pattern.findall(text)
    time_list_matches = time_list_pattern.findall(text)

    n_rounds = len(acc_matches)
    for i in range(n_rounds):
        epoch, acc, loss = acc_matches[i]
        metrics["rounds"].append(int(epoch))
        metrics["test_acc"].append(float(acc))
        metrics["test_loss"].append(float(loss))

        ul = int(ul_matches[i]) if i < len(ul_matches) else 0
        dl = int(dl_matches[i]) if i < len(dl_matches) else 0
        metrics["upload_cost"].append(ul)
        metrics["download_cost"].append(dl)
        metrics["total_communication_cost"].append(ul + dl)

        if i < len(time_matches):
            t = float(time_matches[i])
        elif i < len(time_list_matches):
            t = float(time_list_matches[i])
        else:
            t = 0.0
        metrics["time_cost"].append(t)

    metrics["final_acc"] = metrics["test_acc"][-1] if metrics["test_acc"] else 0.0
    metrics["final_loss"] = metrics["test_loss"][-1] if metrics["test_loss"] else 0.0
    metrics["total_upload"] = sum(metrics["upload_cost"])
    metrics["total_download"] = sum(metrics["download_cost"])
    metrics["total_comm"] = metrics["total_upload"] + metrics["total_download"]

    return metrics


# ---------------------------------------------------------------------------
# 4. 主流程
# ---------------------------------------------------------------------------
def main():
    parse_only = "--parse-only" in sys.argv

    params_path = PARAMS_PATH
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            params_path = Path(arg)
            break

    with open(params_path, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)

    dataset = params["dataset"]
    log_file = PROJECT_ROOT / "log" / f"{dataset.upper()}.log"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if parse_only:
        print(f"[INFO] 解析已有日志: {log_file}")
        if not log_file.exists():
            print(f"[ERROR] 日志文件不存在: {log_file}")
            return 1
        try:
            metrics = parse_log(log_file)
        except Exception as e:
            print(f"[ERROR] 日志解析失败: {e}")
            return 1
        out_json = RESULTS_DIR / "metrics.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"[OK] 指标已保存: {out_json}")
        return 0

    # 正常模式：patch + 生成命令 + 提示用户手动运行
    patch_server_py()

    cmd = build_cmd(params)
    env_vars = {"LOKY_MAX_CPU_COUNT": "4", "NUMBER_OF_PROCESSORS": "16"}
    if params.get("device", "cpu") == "cpu":
        env_vars["CUDA_VISIBLE_DEVICES"] = ""

    # 清理旧日志
    if log_file.exists():
        log_file.unlink()
        print(f"[INFO] 已清理旧日志: {log_file}")

    print("\n[FedPHE standalone 已准备就绪]")
    print("请复制并执行以下命令来运行 FedPHE 实验：\n")
    print_run_command(cmd, env_vars)

    print("[提示] 实验完成后，运行以下命令解析结果：")
    print(f"  python {Path(__file__).relative_to(PROJECT_ROOT)} --parse-only\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
