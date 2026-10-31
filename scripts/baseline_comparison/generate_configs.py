#!/usr/bin/env python3
"""
根据 baseline_params.yaml 为本项目生成各 baseline 的实验配置文件。
"""

import yaml
import os
import sys
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CONFIG_TEMPLATE = os.path.join(PROJECT_ROOT, "configs", "config.yaml")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "tmp_configs")


def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_template(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"[OK] 配置已生成: {path}")


def apply_common_params(config: dict, params: dict):
    """将统一参数应用到本项目的配置结构中。"""
    # system
    sys_cfg = config.setdefault("system", {})
    sys_cfg["num_clients"] = params["num_clients"]
    sys_cfg["num_rounds"] = params["num_rounds"]
    sys_cfg["num_epochs"] = params["local_epochs"]
    sys_cfg["batch_size"] = params["batch_size"]
    sys_cfg["learning_rate"] = params["learning_rate"]
    sys_cfg["device"] = params["device"]
    sys_cfg["random_seed"] = params["random_seed"]
    sys_cfg["client_sampling_rate"] = params["client_sampling_rate"]
    sys_cfg["upload_difference"] = True
    sys_cfg["run_plaintext_baseline"] = False

    # optimizer
    opt_cfg = sys_cfg.setdefault("optimizer", {})
    opt_cfg["name"] = params.get("optimizer", "sgd")
    opt_cfg["lr"] = params["learning_rate"]
    if opt_cfg["name"] == "sgd":
        opt_cfg["momentum"] = params.get("momentum", 0.9)

    # data
    data_cfg = config.setdefault("data", {})
    data_cfg["dataset"] = params["dataset"]
    data_cfg["num_classes"] = params.get("num_classes", 10)
    data_cfg["iid"] = params["iid"]
    data_cfg["alpha"] = params["alpha"]

    # model
    model_cfg = config.setdefault("model", {})
    model_cfg["name"] = params["model"]

    # ckks defaults (保持模板中的加密参数)
    ckks_cfg = config.setdefault("ckks", {})
    ckks_cfg.setdefault("poly_modulus_degree", 8192)
    ckks_cfg.setdefault("coeff_mod_bit_sizes", [60, 40, 40, 60])
    ckks_cfg.setdefault("global_scale", 1099511627776)
    ckks_cfg.setdefault("slot_packing", True)
    pack_cfg = ckks_cfg.setdefault("packing", {})
    pack_cfg.setdefault("strategy", "merged")

    # ptopk defaults
    ptopk_cfg = ckks_cfg.setdefault("ptopk", {})
    ptopk_cfg.setdefault("enable", True)
    ptopk_cfg.setdefault("client_residual", {"enabled": False})
    ptopk_cfg.setdefault("server_accumulator", {"enabled": False, "mode": "none"})

    # global_mask_vote
    gmv_cfg = config.setdefault("global_mask_vote", {})
    gmv_cfg.setdefault("mode", "none")

    # esafl defaults
    esafl_cfg = config.setdefault("esafl", {})
    esafl_cfg.setdefault("enabled", False)
    esafl_cfg.setdefault("mode", "SIMULATION")

    # tee defaults
    tee_cfg = config.setdefault("tee", {})
    tee_cfg.setdefault("enabled", False)

    # prefetch defaults
    prefetch_cfg = config.setdefault("prefetch", {})
    prefetch_cfg.setdefault("enable_prefetch", False)

    # output
    out_cfg = config.setdefault("output", {})
    out_cfg.setdefault("results_dir", "./results")
    out_cfg.setdefault("model_dir", "./history_models")

    return config


def generate_fedavg_ckks(params: dict) -> str:
    """生成 FedAvg+CKKS 基线配置 (Group A 风格)。"""
    config = load_template(CONFIG_TEMPLATE)
    config = apply_common_params(config, params)

    # FedAvg+CKKS 专属：关闭所有优化组件
    ckks_cfg = config.setdefault("ckks", {})
    ckks_cfg["sparsification"] = {
        "strategy": "none"
    }

    config["tee"]["enabled"] = False
    config["prefetch"]["enable_prefetch"] = False
    config["blinding_mask"]["enabled"] = False

    # 结果子目录
    out_cfg = config.setdefault("output", {})
    out_cfg["results_dir"] = "./results/baseline_fedavg_ckks"
    out_cfg["model_dir"] = "./history_models/baseline_fedavg_ckks"

    out_path = os.path.join(OUTPUT_DIR, "baseline_fedavg_ckks.yaml")
    save_config(config, out_path)
    return out_path


def generate_fedphe_internal(params: dict) -> str:
    """生成本项目内置 FedPHE 风格配置 (Group B)。"""
    config = load_template(CONFIG_TEMPLATE)
    config = apply_common_params(config, params)

    ckks_cfg = config.setdefault("ckks", {})
    ckks_cfg["sparsification"] = {
        "strategy": "topk",
        "sparsity_rate": 0.5,
        "batch_size": 4096,
        "scoring_method": "magnitude",
        "warmup_rounds": 0,
        "local_completion": False
    }
    ckks_cfg["ptopk"] = {
        "enable": True,
        "client_residual": {"enabled": False},
        "server_accumulator": {"enabled": False, "mode": "none"}
    }

    # 客户端选择策略改为 sketch_clustering（FedPHE 风格）
    cs_cfg = config.setdefault("client_selection", {})
    cs_cfg["strategy"] = "sketch_clustering"

    config["tee"]["enabled"] = False
    config["prefetch"]["enable_prefetch"] = False

    out_cfg = config.setdefault("output", {})
    out_cfg["results_dir"] = "./results/baseline_fedphe_internal"
    out_cfg["model_dir"] = "./history_models/baseline_fedphe_internal"

    out_path = os.path.join(OUTPUT_DIR, "baseline_fedphe_internal.yaml")
    save_config(config, out_path)
    return out_path


def generate_esafl(params: dict) -> str:
    """生成 ESAFL 模拟配置。"""
    config = load_template(CONFIG_TEMPLATE)
    config = apply_common_params(config, params)

    ckks_cfg = config.setdefault("ckks", {})
    ckks_cfg["sparsification"] = {"strategy": "none"}

    config["esafl"]["enabled"] = True
    config["esafl"]["mode"] = "SIMULATION"

    config["tee"]["enabled"] = False
    config["prefetch"]["enable_prefetch"] = False

    out_cfg = config.setdefault("output", {})
    out_cfg["results_dir"] = "./results/baseline_esafl"
    out_cfg["model_dir"] = "./history_models/baseline_esafl"

    out_path = os.path.join(OUTPUT_DIR, "baseline_esafl.yaml")
    save_config(config, out_path)
    return out_path


def generate_cipherfetch(params: dict) -> str:
    """生成 CipherFetch 完整方案配置 (Group F)。"""
    config = load_template(CONFIG_TEMPLATE)
    config = apply_common_params(config, params)

    ckks_cfg = config.setdefault("ckks", {})
    ckks_cfg["sparsification"] = {
        "strategy": "topk",
        "sparsity_rate": 0.5,
        "batch_size": 4096,
        "scoring_method": "magnitude",
        "warmup_rounds": 0,
        "local_completion": False
    }
    ckks_cfg["ptopk"] = {
        "enable": True,
        "client_residual": {"enabled": True},
        "server_accumulator": {"enabled": False, "mode": "none"}
    }

    config["tee"]["enabled"] = True
    config["tee"]["compression"] = {"enabled": True, "sparsity_rate": 0.5}

    config["prefetch"]["enable_prefetch"] = True
    config["prefetch"]["max_prefetch_round"] = 3
    config["prefetch"]["warmup_round"] = 1
    config["prefetch"]["scheduler_beta"] = 0.5
    config["prefetch"]["overcommitment"] = 1.0
    config["prefetch"]["use_sticky_sampling"] = True
    config["prefetch"]["sticky_decay"] = 0.9

    cs_cfg = config.setdefault("client_selection", {})
    cs_cfg["strategy"] = "sticky"

    out_cfg = config.setdefault("output", {})
    out_cfg["results_dir"] = "./results/baseline_cipherfetch"
    out_cfg["model_dir"] = "./history_models/baseline_cipherfetch"

    out_path = os.path.join(OUTPUT_DIR, "baseline_cipherfetch.yaml")
    save_config(config, out_path)
    return out_path


def main():
    params_path = os.path.join(os.path.dirname(__file__), "baseline_params.yaml")
    if len(sys.argv) > 1:
        params_path = sys.argv[1]

    params = load_params(params_path)
    print(f"[INFO] 加载统一参数: {params_path}")

    # 阶段一：FedAvg+CKKS + FedPHE internal
    generate_fedavg_ckks(params)
    generate_fedphe_internal(params)

    # 阶段二：ESAFL + CipherFetch（预留）
    generate_esafl(params)
    generate_cipherfetch(params)

    print("[DONE] 所有 baseline 配置已生成到 tmp_configs/")


if __name__ == "__main__":
    main()
