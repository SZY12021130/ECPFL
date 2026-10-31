"""
CKKS-Fed 联邦学习主程序
协调多客户端、聚合服务器和辅助节点
"""

import torch
import torch.nn as nn
import numpy as np
import yaml
import time
import os
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List
import psutil

# 导入自定义模块
from ckks_fed.models import create_model, print_model_summary
from ckks_fed.data import create_client_dataloaders, evaluate, get_dataset_num_classes
from ckks_fed.client import FederatedClient, SimpleClient, PrefetchFederatedClient
from ckks_fed.server import AggregationServer, PrefetchAggregationServer
from ckks_fed.crypto import CKKSManager

# 设置日志 — 简洁、对齐的格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 导入日志工具
from ckks_fed.log_utils import (
    banner, separator, blank_line, section, kv, tree, table,
    LogTag, tag_info, tag_warn,
    fmt_size, fmt_time, fmt_pct, fmt_bw,
    log_round_header, log_client_selection, log_training_result,
    log_encryption_result, log_aggregation_result, log_evaluation_result,
    log_experiment_summary, log_round_client_status,
    safe_mean,
)


class MetricsCollector:
    """实验指标收集器"""
    
    def __init__(self):
        self.metrics = {
            # 计算时间指标
            'local_train_time': [],
            'encryption_time': [],
            'aggregation_time': [],
            'total_round_time': [],              # 模拟 wall-clock 时间（含网络传输）
            'total_round_real_time': [],         # 真实 CPU 执行时间（不含网络等待）
            'total_round_time_simulated': [],    # 非预取实验的模拟 wall-clock 时间
            
            # 通信开销指标
            'upload_cost': [],
            'download_cost': [],
            'total_communication_cost': [],
            'upload_time': [],                    # 每轮最慢客户端上传时间（模拟 wall-clock）
            'download_time': [],                  # 每轮最慢客户端下载时间（模拟 wall-clock）
            
            # 加密相关大小指标
            'plaintext_size': [],
            'ciphertext_size': [],
            'expansion_ratio': [],
            
            # 模型性能指标
            'train_loss': [],
            'train_acc': [],
            'test_loss': [],
            'test_acc': [],
            
            # 系统指标
            'cpu_utilization': [],
            'memory_usage': [],
            'communication_rounds': [],
            'dropout_rate': [],
            
            # 加密相关指标
            'key_distribution_time': [],
            'key_distribution_cost': [],
            'num_ciphertexts': [],
            'aggregated_ciphertexts': [],       # 聚合密文数量（服务器聚合后）
            
            # 预取相关指标 (FedFetch论文评价指标)
            'prefetch_time': [],                 # 客户端侧：同态累加密文增量耗时
            'fetch_time': [],                    # 客户端侧：Fetch下载剩余密文耗时
            'apply_time': [],                    # 客户端侧：解密并应用预取状态耗时
            'prefetch_download_cost': [],        # 每客户端本轮预取下载量
            'fetch_download_cost': [],           # 每客户端本轮Fetch下载量
            'prefetch_broadcast_cost': [],       # 服务器本轮向未选中客户端广播的预取量
            'prefetch_server_encrypt_time': [],  # 服务器侧：加密增量耗时（单次加密复用）
            
            # TEE 时间指标（ESAFL 模拟模式：不记录服务器重加密开销）
            'tee_total_time': [],
            'tee_decrypt_time': [],
            'tee_aggregate_time': [],
            'tee_compensate_time': [],
            'tee_compress_time': [],
            # 'tee_reencrypt_time': [],  # 已移除：ESAFL 客户端本地解密，无服务器重加密
        }
        self.start_time = time.time()
    
    def record(self, key: str, value):
        """记录指标"""
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(value)
    
    def get_metrics(self) -> Dict:
        """获取所有指标"""
        return self.metrics.copy()
    
    def save_to_file(self, filepath: str):
        """保存指标到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        logger.info(f"指标已保存到: {filepath}")


class CKKSFedExperiment:
    """CKKS-Fed实验类"""
    
    def __init__(self, config_path: str = "configs/config.yaml",
                 bandwidth_simulator=None, output_dir: str = None):
        """
        初始化实验
        
        Args:
            config_path: 配置文件路径
            bandwidth_simulator: 外部传入的 BandwidthSimulator 实例（用于对比实验共享带宽）
            output_dir: 自定义输出目录（覆盖配置文件中的 results_dir）
        """
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 自动推断 num_classes，避免配置与数据集不匹配导致 CUDA assert
        dataset_name = self.config.get('data', {}).get('dataset', 'cifar10')
        inferred_classes = get_dataset_num_classes(dataset_name)
        config_classes = self.config.get('data', {}).get('num_classes', inferred_classes)
        if config_classes != inferred_classes:
            logger.warning(
                f"[AutoFix] 配置中 num_classes={config_classes} 与数据集 '{dataset_name}' "
                f"不匹配，自动修正为 {inferred_classes}"
            )
            self.config['data']['num_classes'] = inferred_classes
        
        # 设置随机种子
        seed = self.config['system']['random_seed']
        torch.manual_seed(seed)
        np.random.seed(seed)
        
        # 设备
        self.device = self.config['system']['device']
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA不可用，切换到CPU")
            self.device = "cpu"
        
        # 创建输出目录
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = self.config['data']['dataset']
        if output_dir:
            # 使用自定义输出目录作为父目录，在其下生成 时间+数据集 子目录
            base_dir = output_dir
        else:
            base_dir = self.config['output']['results_dir']
        self.output_dir = os.path.join(
            base_dir,
            f"experiment_{self.timestamp}_{dataset_name}"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 保存配置文件副本，便于后续追踪和对比
        self.config_path = config_path
        import shutil
        shutil.copy(config_path, os.path.join(self.output_dir, "config.yaml"))
        
        # 配置实验日志文件（同时保留终端输出）
        self._setup_experiment_logger()
        
        # 指标收集器
        self.metrics = MetricsCollector()
        
        # 带宽模拟器（支持外部传入，确保对比实验使用相同带宽）
        self.bandwidth_simulator = bandwidth_simulator
        
        # 初始化组件
        self._init_components()
        
        tag_info(LogTag.INIT, f"Experiment output dir: {self.output_dir}")
    
    def _log_batch_indices(self, round_num, selected_clients, client_masks, global_mask):
        """记录每轮每个客户端的 batch 索引和聚合后的索引（PrefetchExperiment 会覆盖）"""
        pass

    def _setup_experiment_logger(self):
        """
        配置实验日志文件处理器，将终端输出同时写入到结果目录的 experiment.log。
        该方法确保每次实验运行都有完整的终端日志留存，便于后续分析和论文复现。
        """
        log_file = os.path.join(self.output_dir, "experiment.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        # 使用与终端一致的格式
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-7s %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        # 添加到 root logger，捕获所有模块的日志
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        # 记录日志文件位置
        logger.info(f"实验日志已配置: {log_file}")
    
    def _init_components(self):
        """初始化实验组件"""
        section("Initialization", emoji="📦")

        self.client_loaders, self.test_loader = create_client_dataloaders(
            dataset_name=self.config['data']['dataset'],
            num_clients=self.config['system']['num_clients'],
            batch_size=self.config['system']['batch_size'],
            data_dir=self.config['data']['data_dir'],
            iid=self.config['data']['iid'],
            alpha=self.config['data']['alpha']
        )
        tree([
            ("🗂️ ", f"Dataset: {self.config['data']['dataset']}  |  "
                     f"Clients: {self.config['system']['num_clients']}  |  "
                     f"IID={self.config['data']['iid']}"),
        ], indent=1)

        self.global_model = create_model(self.config['model']['name'], self.config)
        dataset = self.config['data']['dataset']
        dummy_input = (1, 1, 28, 28) if dataset in ["mnist", "fashion_mnist", "emnist"] else (1, 3, 32, 32)
        print_model_summary(self.global_model, dummy_input)

        ckks_cfg = self.config['ckks'].copy()
        ckks_cfg['maser'] = self.config.get('maser', {})
        ckks_cfg['esafl'] = self.config.get('esafl', {})
        self.ckks_manager = CKKSManager(ckks_cfg)
        ckks = self.config['ckks']
        tree([
            ("🔐", f"CKKS  N={ckks.get('poly_modulus_degree')}  |  "
                   f"scale=2^{ckks.get('global_scale', 0).bit_length()-1}  |  "
                   f"mod={ckks.get('coeff_mod_bit_sizes')}  |  "
                   f"packing={'ON' if ckks.get('slot_packing', True) else 'OFF'}"),
        ], indent=1)

        # ---- 可插拔：ESAFL 适配器 ----
        from ckks_fed.esafl_crypto import ESAFLAdapter
        esafl_cfg = self.config.get('esafl', {})
        self.esafl_adapter = None
        if esafl_cfg.get('enabled', False):
            self.esafl_adapter = ESAFLAdapter(
                self.ckks_manager,
                mode=esafl_cfg.get('mode', 'SIMULATION'),
                prpg_seed=esafl_cfg.get('prpg_seed', 42),
            )
            tree([
                ("🔑", f"ESAFL Adapter  |  mode={esafl_cfg.get('mode', 'SIMULATION')}  |  prpg_seed={esafl_cfg.get('prpg_seed', 42)}"),
            ], indent=1)
        
        self.server = AggregationServer(self.global_model, self.config, self.device, self.ckks_manager)

        # MASER 压缩模式（原版 MASER）：服务器维护明文全局模型，不需要加密全局状态
        maser_cfg = self.config.get('maser', {})
        maser_compressed_mode = (
            maser_cfg.get('enable', False) and
            maser_cfg.get('mode', 'compressed') == 'compressed'
        )
        if maser_compressed_mode:
            tree([
                ("🖥️ ", f"Aggregation Server  |  rule={self.config.get('defense', {}).get('aggregation_rule', 'fedavg')}  |  plaintext_state=MASER-compressed"),
            ], indent=1)
        else:
            # ESAFL NATIVE 多密钥模式下服务器不下发加密全局模型（使用明文下发）
            esafl_native = (
                self.config.get('esafl', {}).get('enabled', False)
                and self.config.get('esafl', {}).get('mode', 'SIMULATION') == 'NATIVE'
            )
            if esafl_native:
                tree([
                    ("🖥️ ", f"Aggregation Server  |  rule={self.config.get('defense', {}).get('aggregation_rule', 'fedavg')}  |  plaintext_state=ESAFL-NATIVE"),
                ], indent=1)
            else:
                self.server.init_encrypted_global_state(self.ckks_manager)
                tree([
                    ("🖥️ ", f"Aggregation Server  |  rule={self.config.get('defense', {}).get('aggregation_rule', 'fedavg')}  |  encrypted_state=initialized"),
                ], indent=1)

        self.clients = []
        for i in range(self.config['system']['num_clients']):
            client_model = create_model(self.config['model']['name'], self.config)
            client = FederatedClient(
                client_id=i, model=client_model,
                train_loader=self.client_loaders[i],
                config=self.config, device=self.device
            )
            # 统一 CKKS 上下文：从服务器序列化上下文反序列化
            from ckks_fed.crypto import CKKSContext
            poly_degree = self.config['ckks'].get('poly_modulus_degree', 8192)
            context = CKKSContext.from_full_bytes(
                self.ckks_manager.context.get_full_context_bytes(),
                poly_modulus_degree=poly_degree)
            ckks_cfg = self.config['ckks'].copy()
            ckks_cfg['maser'] = self.config.get('maser', {})
            ckks_cfg['esafl'] = self.config.get('esafl', {})
            client.ckks_manager = CKKSManager(ckks_cfg, context=context)
            self.clients.append(client)
        tree([
            ("👤", f"Created {len(self.clients)} clients  |  "
                   f"sampling_rate={self.config['system'].get('client_sampling_rate', 1.0)}"),
        ], indent=1)
        
        # 初始化客户端参与统计
        self.client_participation = {i: 0 for i in range(len(self.clients))}
        self.client_total_ciphertexts = {i: 0 for i in range(len(self.clients))}

        # 多密钥 MASER：实验级单例 xMKCKKSManager，避免每轮重复创建 Go 对象
        self.xmkckks_manager = None
        self.xmkckks_manager_client_ids = None

        # ESAFL NATIVE 多密钥：实验级单例 ESHEManager
        self.eshe_manager = None
        self.eshe_manager_client_ids = None

        # 可插拔客户端选择策略
        from ckks_fed.client_selection import create_client_selection_strategy
        self.selection_strategy = create_client_selection_strategy(
            self.config, num_clients=len(self.clients))

        # 带宽模拟器（确保基线实验也能使用配置的异构带宽）
        from ckks_fed.bandwidth_simulator import BandwidthSimulator
        bw_cfg = self.config.get('bandwidth', {})
        self.bandwidth_simulator = BandwidthSimulator(
            num_clients=self.config['system']['num_clients'],
            base_dl_bw=bw_cfg.get('base_dl_bw', 1024.0),
            base_ul_bw=bw_cfg.get('base_ul_bw', 512.0),
            variance=bw_cfg.get('variance', 0.3),
            distribution=bw_cfg.get('distribution', 'uniform'),
            seed=self.config.get('random_seed', 42),
            fedfetch_trace_path=bw_cfg.get('fedfetch_trace_path'),
            filter_low_bandwidth=bw_cfg.get('filter_low_bandwidth', False),
            min_dl_bw_kbps=bw_cfg.get('min_dl_bw_kbps', 10240.0),
            min_ul_bw_kbps=bw_cfg.get('min_ul_bw_kbps', 10240.0),
            max_dl_bw_kbps=bw_cfg.get('max_dl_bw_kbps', float('inf')),
            max_ul_bw_kbps=bw_cfg.get('max_ul_bw_kbps', float('inf')),
        )
        bw_stats = self.bandwidth_simulator.get_stats()
        tree([
            ("🌐", f"Bandwidth Simulator  |  DL={fmt_bw(bw_stats.get('dl_bw_mean_kbps', 0))}  |  "
                     f"UL={fmt_bw(bw_stats.get('ul_bw_mean_kbps', 0))}  |  "
                     f"dist={bw_cfg.get('distribution', 'uniform')}"),
        ], indent=1)
    
    def _select_clients(self, context: str = "Current") -> List:
        """使用可插拔策略选择参与本轮训练的客户端子集"""
        num_clients = len(self.clients)
        rate = self.config['system'].get('client_sampling_rate', 1.0)
        num_selected = max(1, int(num_clients * rate))

        # 收集策略所需的额外上下文
        kwargs = {}
        if hasattr(self, 'client_loaders') and self.client_loaders:
            kwargs['train_weights'] = [len(self.client_loaders[i].dataset) for i in range(num_clients)]
        if hasattr(self, 'server') and self.server:
            kwargs['global_state'] = self.server.get_global_params()
            kwargs['client_states'] = {c.client_id: c.model.state_dict() for c in self.clients}

        selected_ids = self.selection_strategy.select(
            self.clients, num_selected, round_num=getattr(self.server, 'round_num', 0),
            **kwargs)
        selected = [self.clients[cid] for cid in selected_ids]
        strategy_name = self.config.get('client_selection', {}).get('strategy', 'random')
        bandwidth_info = getattr(self, 'bandwidth_info', None)
        log_client_selection(selected_ids, num_clients, context=context,
                             strategy_name=strategy_name, bandwidth_info=bandwidth_info)
        return selected

    def _ensure_xmkckks_manager(self, selected_clients):
        """
        实验级单例 xMKCKKSManager：只在客户端集合发生变化时重建，
        避免每轮重复创建 Go 端 MPHEServer/MPHEClient 对象导致内存泄漏。
        """
        from ckks_fed.xmkckks_manager import xMKCKKSManager, XMKCKKS_AVAILABLE
        if not XMKCKKS_AVAILABLE:
            raise RuntimeError("maser.multi_key=true 但 xMKCKKS 库不可用，请检查 MASER-main/xmkckks_go2py/xmkckks.dll")

        selected_ids = sorted([c.client_id for c in selected_clients])
        if (self.xmkckks_manager is not None and
                self.xmkckks_manager_client_ids == selected_ids):
            return

        # 重建：按 client_id 顺序创建，保证与后续加密/解密时索引一致
        xmkckks = xMKCKKSManager(
            num_clients=len(selected_clients),
            slot_size=self.ckks_manager.batch_size,
            client_ids=selected_ids,
        )
        xmkckks.setup_key_aggregation()

        self.ckks_manager.xmkckks = xmkckks
        for client in self.clients:
            client.ckks_manager.xmkckks = xmkckks

        self.xmkckks_manager = xmkckks
        self.xmkckks_manager_client_ids = selected_ids

        key_dist_cost = xmkckks.compute_key_distribution_cost()
        self.metrics.record('key_distribution_cost', key_dist_cost)
        tag_info(LogTag.INIT,
                 f"xMKCKKS manager initialized/reused | clients={len(selected_clients)} | "
                 f"slot_size={self.ckks_manager.batch_size} | key_dist={fmt_size(key_dist_cost)}")

    def _ensure_eshe_manager(self, selected_clients):
        """
        实验级单例 ESHEManager：只在客户端集合发生变化时重建，
        避免每轮重复创建 Go 端 MPHEServer 对象导致内存泄漏。
        """
        from esafl_eshe import ESHEManager, ESAFL_ESHE_AVAILABLE
        if not ESAFL_ESHE_AVAILABLE:
            raise RuntimeError("esafl_eshe 后端不可用，请检查 MASER-main/xmkckks_go2py/xmkckks.dll")

        selected_ids = sorted([c.client_id for c in selected_clients])
        if (self.eshe_manager is not None and
                self.eshe_manager_client_ids == selected_ids):
            return

        eshe = ESHEManager(
            num_clients=len(selected_clients),
            slot_size=self.ckks_manager.batch_size,
            client_ids=selected_ids,
        )
        eshe.setup()

        self.ckks_manager.eshe = eshe
        for client in self.clients:
            client.ckks_manager.eshe = eshe

        self.eshe_manager = eshe
        self.eshe_manager_client_ids = selected_ids

        tag_info(LogTag.INIT,
                 f"ESHE manager initialized/reused | clients={len(selected_clients)} | "
                 f"slot_size={self.ckks_manager.batch_size}")

    def _cleanup_xmkckks_round(self):
        """
        每轮结束后显式释放多密钥密文对象引用并触发 GC，减缓 Go 堆内存增长。
        """
        import gc
        # 清除 CKKSManager 中可能缓存的本轮密文引用
        if hasattr(self.ckks_manager, '_last_aggregated_update'):
            self.ckks_manager._last_aggregated_update = None
        # 触发 Python 与 Go 侧对象回收
        gc.collect()

    def run_round_plain(self, round_num: int) -> Dict:
        """
        运行一轮明文联邦学习（用于对比）
        
        Args:
            round_num: 当前轮次
        
        Returns:
            本轮统计信息
        """
        log_round_header(round_num + 1, self.config['system']['num_rounds'], mode="Plaintext")
        round_start = time.time()

        selected_clients = self._select_clients()
        global_params = self.server.get_global_params()

        client_updates, client_weights, train_losses, train_accs = [], [], [], []
        client_upload_sizes = []
        for client in selected_clients:
            update, loss, acc = client.local_train(global_params, round_num=round_num)
            client_updates.append(update)
            client_weights.append(client.get_weight())
            train_losses.append(loss)
            train_accs.append(acc)
            self.metrics.record('local_train_time', client.local_train_time)
            client_upload_sizes.append(client.plaintext_size)
            self.metrics.record('plaintext_size', client.plaintext_size)
            self.client_participation[client.client_id] += 1

        aggregated_update = self.server.aggregate_plain_updates(
            client_updates, client_weights, client_upload_sizes)
        self.server.update_global_model(aggregated_update)

        criterion = nn.CrossEntropyLoss()
        test_loss, test_acc = self.server.evaluate(self.test_loader, criterion)

        self.metrics.record('train_loss', np.mean(train_losses))
        self.metrics.record('train_acc', np.mean(train_accs))
        self.metrics.record('test_loss', test_loss)
        self.metrics.record('test_acc', test_acc)
        self.metrics.record('aggregation_time', self.server.aggregation_time)
        self.metrics.record('upload_cost', self.server.upload_cost)
        self.metrics.record('download_cost', self.server.download_cost)
        self.metrics.record('total_communication_cost', self.server.communication_cost)
        self.metrics.record('communication_rounds', 1)
        self.metrics.record('cpu_utilization', psutil.cpu_percent())
        self.metrics.record('memory_usage', psutil.virtual_memory().percent)

        round_time = time.time() - round_start
        self.metrics.record('total_round_time', round_time)

        # 计算模拟 wall-clock 时间（使用与预取实验相同的带宽配置，用于横向对比）
        simulated_download_time = 0.0
        simulated_upload_time = 0.0
        simulated_compute_time = 0.0
        simulated_round_duration = 0.0
        for client in selected_clients:
            model_size_bits = self.server.compute_download_cost() * 8
            ciphertext_size_bits = client.ciphertext_size * 8
            if self.bandwidth_simulator:
                # 使用共享的 BandwidthSimulator（与预取实验完全相同的带宽）
                client_dl = self.bandwidth_simulator.estimate_download_time(
                    client.client_id, model_size_bits)
                client_ul = self.bandwidth_simulator.estimate_upload_time(
                    client.client_id, ciphertext_size_bits)
            else:
                # 回退到默认固定带宽（不推荐，仅兼容旧代码）
                dl_bw_bits = 1024 * 1000
                ul_bw_bits = 512 * 1000
                client_dl = model_size_bits / dl_bw_bits if dl_bw_bits > 0 else 0.0
                client_ul = ciphertext_size_bits / ul_bw_bits if ul_bw_bits > 0 else 0.0
            client_total = client.local_train_time + client_dl + client_ul
            simulated_round_duration = max(simulated_round_duration, client_total)
            simulated_download_time = max(simulated_download_time, client_dl)
            simulated_upload_time = max(simulated_upload_time, client_ul)
            simulated_compute_time = max(simulated_compute_time, client.local_train_time)
        # 加上服务器聚合时间
        simulated_round_duration += 0.0  # 聚合时间已包含在真实时间中，这里暂不额外添加
        self.metrics.record('total_round_time_simulated', simulated_round_duration)
        self.metrics.record('upload_time', simulated_upload_time)
        self.metrics.record('download_time', simulated_download_time)

        tag_info(LogTag.ROUND,
                 f"#{round_num + 1} done  |  acc={test_acc:.2f}%  |  "
                 f"real_time={round_time:.2f}s  |  sim_dur={simulated_round_duration:.2f}s  |  "
                 f"comm={fmt_size(self.server.communication_cost)} "
                 f"(↑{fmt_size(self.server.upload_cost)} ↓{fmt_size(self.server.download_cost)})")
        
        return {
            'round': round_num + 1,
            'test_acc': test_acc,
            'test_loss': test_loss,
            'round_time': round_time,
            'simulated_round_duration': simulated_round_duration,
        }
    
    def run_round_encrypted(self, round_num: int) -> Dict:
        """
        运行一轮加密联邦学习（CKKS-Fed）
        架构：服务器加密全局模型下发 → 客户端解密 → 本地训练 → 客户端加密上传
              → 服务器同态聚合 → 服务器本地解密 → 更新全局模型
        
        Args:
            round_num: 当前轮次
        
        Returns:
            本轮统计信息
        """
        log_round_header(round_num + 1, self.config['system']['num_rounds'], mode="CKKS-Encrypted")
        round_start = time.time()

        selected_clients = self._select_clients()

        # MASER 压缩模式（原版 MASER）：服务器维护明文全局模型，直接下发明文给客户端
        maser_cfg = self.config.get('maser', {})
        maser_compressed_mode = (
            maser_cfg.get('enable', False) and
            maser_cfg.get('mode', 'compressed') == 'compressed'
        )
        maser_multi_key = (
            maser_cfg.get('enable', False) and
            maser_cfg.get('multi_key', False)
        )

        # ESAFL NATIVE 多密钥模式：服务器下发明文全局模型，客户端用多密钥 CKKS 加密上传
        esafl_cfg = self.config.get('esafl', {})
        esafl_native_mode = (
            esafl_cfg.get('enabled', False) and
            esafl_cfg.get('mode', 'SIMULATION') == 'NATIVE'
        )

        # ================================================================
        # MASER：实验级单例 xMKCKKS 后端（用于多密钥计算或通信量模拟）
        # ================================================================
        if maser_compressed_mode:
            self._ensure_xmkckks_manager(selected_clients)

        # ================================================================
        # ESAFL NATIVE：实验级单例 ESHEManager
        # ================================================================
        if esafl_native_mode:
            self._ensure_eshe_manager(selected_clients)

        client_updates, client_weights, train_losses, train_accs = [], [], [], []
        if maser_compressed_mode or esafl_native_mode:
            plain_global = self.server.get_global_params()
            for client in selected_clients:
                update, loss, acc = client.local_train(global_params=plain_global, round_num=round_num)
                client_updates.append(update)
                client_weights.append(client.get_weight())
                train_losses.append(loss)
                train_accs.append(acc)
                self.metrics.record('local_train_time', client.local_train_time)
        else:
            encrypted_global = self.server.get_encrypted_global_params()
            for client in selected_clients:
                update, loss, acc = client.local_train(encrypted_global_params=encrypted_global, round_num=round_num)
                client_updates.append(update)
                client_weights.append(client.get_weight())
                train_losses.append(loss)
                train_accs.append(acc)
                self.metrics.record('local_train_time', client.local_train_time)

        # ==== 全局掩码投票（隐私安全：客户端本地算 mask，只上传 mask）====
        gmv_mode = self.config.get('global_mask_vote', {}).get('mode', 'none')
        sparsity_cfg = self.config.get('ckks', {}).get('sparsification', {})
        maser_enabled = self.config.get('maser', {}).get('enable', False)
        maser_cfg = self.config.get('maser', {})
        sparsity_enabled = sparsity_cfg.get('strategy', 'none') not in ('none', None) or maser_enabled
        
        # 1) 客户端本地计算 mask（不上传明文梯度）
        client_masks = []
        if sparsity_enabled:
            for client, update in zip(selected_clients, client_updates):
                mask = client.compute_local_mask(update, self.ckks_manager, round_num)
                client_masks.append(mask)
        
        # 2a) ESAFL 全局 batch 级 mask 投票
        global_mask = None
        if gmv_mode != 'none' and client_masks:
            packing = self.ckks_manager.packing_strategy if self.ckks_manager else None
            values_per_chunk = packing.get_values_per_chunk() if packing else 8192
            total_params = sum(p.numel() for p in self.server.model.parameters())
            num_batches = (total_params + values_per_chunk - 1) // values_per_chunk
            global_mask = self.server.run_global_mask_vote(
                client_masks=client_masks,
                num_batches=num_batches,
                round_num=round_num,
            )
            
            # 记录每轮 batch 索引详情（用于分析通信开销）
            self._log_batch_indices(round_num, selected_clients, client_masks, global_mask)
        
        # 2b) MASER 全局参数级 mask 投票
        global_maser_indices = None
        if maser_enabled and client_masks:
            # 与 client.get_model_params() 保持一致：包含可训练参数 + BN 的 running_mean/running_var
            total_params = sum(p.numel() for p in self.server.model.parameters())
            for name, buf in self.server.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    total_params += buf.numel()
            # MASER 返回的是参数级 mask，长度为 total_params
            maser_client_masks = [m for m in client_masks
                                  if m is not None and len(m) == total_params]
            if maser_client_masks:
                use_threshold = maser_cfg.get('use_server_threshold', True)
                voting_threshold = maser_cfg.get('voting_threshold', 0.5)
                topk_ratio = maser_cfg.get('topk_ratio', 0.5)
                global_maser_indices = self.server.run_maser_global_vote(
                    client_masks=maser_client_masks,
                    total_elements=total_params,
                    voting_threshold=voting_threshold,
                    topk_ratio=None if use_threshold else topk_ratio,
                    round_num=round_num,
                )

        encrypted_updates, client_upload_sizes = [], []
        total_plaintext_size, total_ciphertext_size = 0, 0
        for client, update in zip(selected_clients, client_updates):
            encrypted = client.encrypt_update(
                update, self.ckks_manager, round_num=round_num,
                global_mask=global_mask,
                global_maser_indices=global_maser_indices,
            )
            encrypted_updates.append(encrypted)
            self.metrics.record('encryption_time', client.encryption_time)
            self.metrics.record('plaintext_size', client.plaintext_size)
            self.metrics.record('ciphertext_size', client.ciphertext_size)
            self.metrics.record('num_ciphertexts', client.num_ciphertexts)
            total_plaintext_size += client.plaintext_size
            total_ciphertext_size += client.ciphertext_size
            client_upload_sizes.append(client.ciphertext_size)
            self.client_participation[client.client_id] += 1
            self.client_total_ciphertexts[client.client_id] += client.num_ciphertexts

        # 记录聚合密文数量（xMK-CKKS 中 = num_ciphertexts，每 batch 聚合为一个）
        if selected_clients:
            self.metrics.record('aggregated_ciphertexts', selected_clients[0].num_ciphertexts)

        if total_plaintext_size > 0:
            expansion_ratio = total_ciphertext_size / total_plaintext_size
            self.metrics.record('expansion_ratio', expansion_ratio)
            tag_info(LogTag.ENCRYPT, f"Expansion ratio: {expansion_ratio:.2f}x  |  "
                     f"total_plain={fmt_size(total_plaintext_size)}  |  "
                     f"total_cipher={fmt_size(total_ciphertext_size)}")

        if self.config.get('tee', {}).get('enabled', False):
            # 方案①：TEE 路径
            delta_enc = self.server.process_encrypted_round_via_tee(
                encrypted_updates, client_weights, client_upload_sizes)
            # TEE 路径已内部更新 encrypted_global_state
            # delta_enc 存入历史供 Prefetch 客户端使用（如果启用 Prefetch）
            if hasattr(self.server, 'encrypted_deltas_history'):
                self.server.encrypted_deltas_history.append({
                    'delta': delta_enc,
                    'size': self.ckks_manager.compute_encrypted_update_size(delta_enc),
                    'from_round': self.server.round_num,
                })
        else:
            # 标准路径：同态聚合 + 更新全局模型
            aggregated_update = self.server.aggregate_encrypted_updates(
                encrypted_updates, client_weights, self.ckks_manager, client_upload_sizes)

            if maser_multi_key:
                # 多密钥 MASER：需要客户端上传 partial decrypt 份额后才能解码
                partial_shares = []
                for client in selected_clients:
                    shares = self.ckks_manager.partial_decrypt_maser_update(
                        aggregated_update, client.client_id)
                    partial_shares.append(shares)
                selected_ids = [c.client_id for c in selected_clients]
                self.server.update_global_model_maser_multikey(
                    aggregated_update, partial_shares, selected_ids)
            elif esafl_native_mode:
                # ESAFL NATIVE：需要客户端上传 partial decrypt 份额后才能解码
                partial_shares = []
                for client in selected_clients:
                    shares = [
                        self.ckks_manager.eshe.partial_decrypt(client.client_id, agg_ct)
                        for agg_ct in aggregated_update['ciphertexts']
                    ]
                    partial_shares.append(shares)
                selected_ids = [c.client_id for c in selected_clients]
                self.server.update_global_model_esafl_native_multikey(
                    aggregated_update, partial_shares, selected_ids)
            else:
                self.server.update_global_model(aggregated_update)

        # ==== MASER xMKCKKS 完整通信量模拟（密文部分，不含掩码）====
        # 通信量组成：
        # ① 加密密文上传（Client→Server）：N × S × num_batches
        # ② 聚合密文广播（Server→Client）：N × S_agg × num_batches
        # ③ 解密份额上传（Client→Server）：N × S_agg × num_batches
        # ④ 明文全局模型下发（Server→Client）
        # 其中 S_agg = S × (n+1)/2（聚合密文随客户端数增长）
        maser_costs = None
        if self.config.get('maser', {}).get('enable', False):
            num_selected = len(selected_clients)

            # 获取密文 batch 数量
            if encrypted_updates and len(encrypted_updates) > 0:
                first_update = encrypted_updates[0]
                if '__sparse__' in first_update:
                    num_batches = len(first_update.get('ciphertexts', []))
                else:
                    num_batches = len(first_update.get('ciphertexts', []))
            else:
                num_batches = 1

            # 使用 xMKCKKS 管理器计算通信量
            try:
                from ckks_fed.xmkckks_manager import XMKCKKS_AVAILABLE
                if XMKCKKS_AVAILABLE and self.xmkckks_manager is not None:
                    costs = self.xmkckks_manager.compute_total_communication_cost(num_selected, num_batches)
                    maser_costs = costs

                    # 优先使用实际测得的客户端密文上传大小
                    actual_upload = sum(client_upload_sizes) if client_upload_sizes else costs['upload_cost']
                    plain_model_size = self.server.compute_download_cost() * num_selected

                    # 统一按多密钥通信结构计算：
                    # ① 客户端密文上传
                    # ② 聚合密文广播给所有客户端做 partial decrypt
                    # ③ 各客户端上传 partial decrypt 份额
                    # ④ 服务器解密后下发更新后的明文全局模型
                    maser_upload = actual_upload + costs['partial_dec_upload']
                    maser_download = costs['download_cost'] + plain_model_size
                    log_tag = "MASER-MK通信" if maser_multi_key else "MASER-SK通信(模拟MK)"

                    self.server.upload_cost = maser_upload
                    self.server.download_cost = maser_download
                    self.server.communication_cost = maser_upload + maser_download

                    # 保存 MASER 通信结构四个分量，用于报告细化
                    self._maser_ct_upload = actual_upload
                    self._maser_agg_ct_download = costs['download_cost']
                    self._maser_partial_dec_upload = costs['partial_dec_upload']
                    self._maser_plaintext_download = plain_model_size

                    # 同时直接记录到 metrics，避免后续 getattr 依赖
                    self.metrics.record('maser_ct_upload', actual_upload)
                    self.metrics.record('maser_agg_ct_download', costs['download_cost'])
                    self.metrics.record('maser_partial_dec_upload', costs['partial_dec_upload'])
                    self.metrics.record('maser_plaintext_download', plain_model_size)

                    tag_info(LogTag.ROUND,
                             f"{log_tag} | batches={num_batches} | "
                             f"①加密上传={fmt_size(actual_upload)} | "
                             f"②聚合广播={fmt_size(costs['download_cost'])} | "
                             f"③解密份额={fmt_size(costs['partial_dec_upload'])} | "
                             f"④明文模型↓={fmt_size(plain_model_size)} | "
                             f"total={fmt_size(self.server.communication_cost)}")
                else:
                    # xMKCKKS 库不可用，使用简化模拟
                    # 单密钥 MASER 下行：明文全局模型
                    plain_download = self.server.compute_download_cost() * num_selected
                    self.server.download_cost += plain_download
                    self.server.communication_cost += plain_download
                    tag_info(LogTag.ROUND,
                             f"MASER通信模拟（简化）| 明文模型↓{fmt_size(plain_download)} | "
                             f"xMKCKKS库不可用")
            except Exception as e:
                tag_info(LogTag.ROUND, f"MASER通信模拟失败: {e}")

        criterion = nn.CrossEntropyLoss()
        test_loss, test_acc = self.server.evaluate(self.test_loader, criterion)

        self.metrics.record('train_loss', np.mean(train_losses))
        self.metrics.record('train_acc', np.mean(train_accs))
        self.metrics.record('test_loss', test_loss)
        self.metrics.record('test_acc', test_acc)
        self.metrics.record('aggregation_time', self.server.aggregation_time)
        self.metrics.record('upload_cost', self.server.upload_cost)
        self.metrics.record('download_cost', self.server.download_cost)
        self.metrics.record('total_communication_cost', self.server.communication_cost)
        self.metrics.record('communication_rounds', 1)
        self.metrics.record('cpu_utilization', psutil.cpu_percent())
        self.metrics.record('memory_usage', psutil.virtual_memory().percent)

        round_time = time.time() - round_start
        self.metrics.record('total_round_time', round_time)

        # 计算模拟 wall-clock 时间（使用 bandwidth_simulator 确保与预取实验公平对比）
        simulated_download_time = 0.0
        simulated_upload_time = 0.0
        simulated_compute_time = 0.0
        simulated_round_duration = 0.0
        for client in selected_clients:
            if maser_compressed_mode:
                # MASER compressed：服务器下发明文全局模型，客户端上传密文更新
                client_dl_bits = self.server.compute_download_cost() * 8
                client_ul_bits = client.ciphertext_size * 8
                if maser_costs is not None:
                    # 多密钥额外：聚合密文广播 + partial decrypt 份额上传
                    client_dl_bits += maser_costs['aggregated_ct_size'] * 8 * num_batches
                    client_ul_bits += maser_costs['partial_dec_size'] * 8 * num_batches
            elif self.server.encrypted_global_state is not None:
                client_dl_bits = self.ckks_manager.compute_encrypted_update_size(self.server.encrypted_global_state) * 8
                client_ul_bits = client.ciphertext_size * 8
            else:
                client_dl_bits = self.server.compute_download_cost() * 8
                client_ul_bits = client.ciphertext_size * 8

            if self.bandwidth_simulator is not None:
                # 使用异构带宽（与预取实验一致）
                client_dl = self.bandwidth_simulator.estimate_download_time(client.client_id, client_dl_bits)
                client_ul = self.bandwidth_simulator.estimate_upload_time(client.client_id, client_ul_bits)
            else:
                # fallback 到固定带宽
                dl_bw_bits = 1024 * 1000
                ul_bw_bits = 512 * 1000
                client_dl = client_dl_bits / dl_bw_bits if dl_bw_bits > 0 else 0.0
                client_ul = client_ul_bits / ul_bw_bits if ul_bw_bits > 0 else 0.0
            client_total = client.local_train_time + client_dl + client_ul
            simulated_round_duration = max(simulated_round_duration, client_total)
            simulated_download_time = max(simulated_download_time, client_dl)
            simulated_upload_time = max(simulated_upload_time, client_ul)
            simulated_compute_time = max(simulated_compute_time, client.local_train_time)
        # 加上服务器聚合时间（已包含在真实时间中，暂不额外添加）
        simulated_round_duration += 0.0
        self.metrics.record('total_round_time_simulated', simulated_round_duration)
        self.metrics.record('upload_time', simulated_upload_time)
        self.metrics.record('download_time', simulated_download_time)

        # 多密钥 MASER：每轮结束后显式清理 Go 密文对象引用，减缓内存增长
        if maser_multi_key:
            self._cleanup_xmkckks_round()

        tag_info(LogTag.ROUND,
                 f"#{round_num + 1} done  |  acc={test_acc:.2f}%  |  "
                 f"real_time={round_time:.2f}s  |  sim_dur={simulated_round_duration:.2f}s  |  "
                 f"comm={fmt_size(self.server.communication_cost)}")

        return {
            'round': round_num + 1,
            'test_acc': test_acc,
            'test_loss': test_loss,
            'round_time': round_time,
            'simulated_round_duration': simulated_round_duration,
        }
    
    def run_experiment(self, use_encryption: bool = True) -> Dict:
        """
        运行完整实验
        
        Args:
            use_encryption: 是否使用加密
        
        Returns:
            实验结果
        """
        upload_mode = "Δ" if self.config['system'].get('upload_difference', True) else "Full"
        blank_line()
        banner("Experiment Start", width=72)
        kv("Mode", "Encrypted" if use_encryption else "Plaintext", indent=1)
        kv("Rounds", self.config['system']['num_rounds'], indent=1)
        kv("Upload", upload_mode, indent=1)
        separator(width=72)

        num_rounds = self.config['system']['num_rounds']
        results = []

        if use_encryption:
            key_dist_time = 0.0
            self.metrics.record('key_distribution_time', key_dist_time)
            num_clients = self.config['system']['num_clients']
            maser_cfg = self.config.get('maser', {})
            maser_multi_key = maser_cfg.get('enable', False) and maser_cfg.get('multi_key', False)
            esafl_native_mode = (
                self.config.get('esafl', {}).get('enabled', False)
                and self.config.get('esafl', {}).get('mode', 'SIMULATION') == 'NATIVE'
            )
            if maser_multi_key or esafl_native_mode:
                # 多密钥：密钥分发按轮次在 run_round_encrypted 中统计，此处记 0
                self.metrics.record('key_distribution_cost', 0)
                backend = "xMKCKKS" if maser_multi_key else "ESAFL-NATIVE"
                tag_info(LogTag.INIT, f"{backend} multi-key: per-round key distribution will be recorded")
            else:
                key_size_per_client = self.ckks_manager.get_key_distribution_size()
                self.metrics.record('key_distribution_cost', key_size_per_client * num_clients)
                tag_info(LogTag.INIT, "Unified CKKS key distributed to all clients")
        
        try:
            for round_num in range(num_rounds):
                if use_encryption:
                    result = self.run_round_encrypted(round_num)
                else:
                    result = self.run_round_plain(round_num)
                results.append(result)
                
                # 每5轮保存一次模型
                if (round_num + 1) % self.config['output']['save_interval'] == 0:
                    self._save_model(round_num + 1)
        except KeyboardInterrupt:
            tag_warn(LogTag.SUMMARY, "实验被用户中断")
        except Exception as e:
            tag_warn(LogTag.SUMMARY, f"实验异常中断: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 无论是否完成，都保存已产生的中间结果
            self._save_results()
            if results:
                self._save_model(len(results))
            tag_info(LogTag.SUMMARY, f"实验结果已保存至: {self.output_dir}")
        
        # 终端打印客户端参与统计（表格形式）
        blank_line()
        banner("Client Participation", width=72)
        headers = ["Client", "Participated", "Total CTs"]
        rows = []
        for cid in sorted(self.client_participation.keys()):
            ct_count = self.client_total_ciphertexts.get(cid, 0) if use_encryption else 0
            rows.append([cid, self.client_participation[cid], ct_count])
        table(headers, rows, col_widths=[8, 14, 12])

        if use_encryption:
            blank_line()
            section("Communication & Ciphertext Formulas", emoji="📐")
            tree([
                "plaintext_size  = Σ(v.numel() × 4)",
                "ciphertext_size = Σ(len(ct.serialize()))",
                "num_ciphertexts = Σ(len(v) for v in encrypted_update.values())",
                "upload_cost     = Σ(ciphertext_size of selected)",
                "download_cost   = global_model_size × 4 × num_selected",
                "total_comm      = upload_cost + download_cost",
                "expansion_ratio = total_ciphertext_size / total_plaintext_size",
            ], indent=1)

        blank_line()
        banner("Experiment Complete", width=72)
        
        return {
            'results': results,
            'metrics': self.metrics.get_metrics()
        }
    
    def _update_experiment_registry(self):
        """将当前实验摘要追加到 results/experiments_registry.json"""
        registry_path = os.path.join(self.config['output']['results_dir'], "experiments_registry.json")
        entries = []
        if os.path.exists(registry_path):
            with open(registry_path, 'r', encoding='utf-8') as f:
                try:
                    entries = json.load(f)
                except json.JSONDecodeError:
                    entries = []
        
        m = self.metrics.get_metrics()
        is_encrypted = len(m.get('ciphertext_size', [])) > 0
        mode = "encrypted" if is_encrypted else "plain"
        
        entry = {
            "timestamp": self.timestamp,
            "output_dir": self.output_dir,
            "mode": mode,
            "config_summary": {
                "dataset": self.config['data']['dataset'],
                "model": self.config['model']['name'],
                "num_clients": self.config['system']['num_clients'],
                "num_rounds": self.config['system']['num_rounds'],
                "client_sampling_rate": self.config['system'].get('client_sampling_rate', 1.0),
                "local_epochs": self.config['system']['num_epochs'],
                "batch_size": self.config['system']['batch_size'],
                "learning_rate": self.config['system']['learning_rate'],
                "iid": self.config['data']['iid'],
                "device": self.config['system']['device'],
                "upload_difference": self.config['system'].get('upload_difference', True),
                "slot_packing": self.config.get('ckks', {}).get('slot_packing', True) if is_encrypted else None,
                "poly_modulus_degree": self.config.get('ckks', {}).get('poly_modulus_degree') if is_encrypted else None,
                "adaptive_vote": {
                    "enabled": self.config.get('adaptive_vote', {}).get('enabled', False),
                    "strategy": self.config.get('adaptive_vote', {}).get('strategy', 'none'),
                },
            },
            "metrics_summary": {
                "final_test_acc": m['test_acc'][-1] if m['test_acc'] else 0.0,
                "final_test_loss": m['test_loss'][-1] if m['test_loss'] else 0.0,
                "total_time_sec": sum(m.get('total_round_time', [])),
                "total_communication_mb": sum(m.get('total_communication_cost', [])) / (1024 * 1024),
                "avg_round_time_sec": safe_mean(m.get('total_round_time', [])),
                "avg_upload_kb": safe_mean(m.get('upload_cost', [])) / 1024,
                "avg_download_kb": safe_mean(m.get('download_cost', [])) / 1024,
            }
        }
        if is_encrypted:
            entry["metrics_summary"]["avg_expansion_ratio"] = safe_mean(m.get('expansion_ratio', []))
            entry["metrics_summary"]["avg_encryption_time_sec"] = safe_mean(m.get('encryption_time', []))
            # decryption_time 指标已废弃（HelperNode 已删除，服务器本地解密不计入此指标）
            entry["metrics_summary"]["avg_decryption_time_sec"] = 0.0
            entry["metrics_summary"]["key_distribution_mb"] = sum(m.get('key_distribution_cost', [])) / (1024 * 1024)
            entry["metrics_summary"]["total_ciphertext_blocks"] = int(sum(m.get('num_ciphertexts', [])))
            
            # 预取指标 (FedFetch论文评价指标)
            has_prefetch = hasattr(self, 'clients') and len(self.clients) > 0 and hasattr(self.clients[0], 'get_prefetch_stats')
            if has_prefetch:
                entry["metrics_summary"]["prefetch_enabled"] = True
                entry["metrics_summary"]["avg_prefetch_time_sec"] = float(np.mean(m.get('prefetch_time', [0]))) if m.get('prefetch_time') else 0.0
                entry["metrics_summary"]["avg_fetch_time_sec"] = float(np.mean(m.get('fetch_time', [0]))) if m.get('fetch_time') else 0.0
                entry["metrics_summary"]["avg_apply_time_sec"] = float(np.mean(m.get('apply_time', [0]))) if m.get('apply_time') else 0.0
                # 从客户端最终统计计算总下载量（metrics中只记录了被选中客户端的）
                total_pf_dl = sum(c.get_prefetch_stats().get('total_prefetch_download_cost', 0) for c in self.clients)
                total_fetch_dl = sum(c.get_prefetch_stats().get('total_fetch_download_cost', 0) for c in self.clients)
                entry["metrics_summary"]["total_prefetch_download_kb"] = float(total_pf_dl) / 1024
                entry["metrics_summary"]["total_fetch_download_kb"] = float(total_fetch_dl) / 1024
            else:
                entry["metrics_summary"]["prefetch_enabled"] = False
            
            # TEE 时间指标（ESAFL 模拟：去除服务器重加密指标）
            if len(m.get('tee_total_time', [])) > 0:
                entry["metrics_summary"]["tee_total_time_sec"] = sum(m.get('tee_total_time', []))
                entry["metrics_summary"]["tee_decrypt_time_sec"] = sum(m.get('tee_decrypt_time', []))
                entry["metrics_summary"]["tee_aggregate_time_sec"] = sum(m.get('tee_aggregate_time', []))
                entry["metrics_summary"]["tee_compensate_time_sec"] = sum(m.get('tee_compensate_time', []))
                entry["metrics_summary"]["tee_compress_time_sec"] = sum(m.get('tee_compress_time', []))
                # entry["metrics_summary"]["tee_reencrypt_time_sec"] = 0.0  # ESAFL 模拟：客户端本地解密，无服务器重加密
        
        # 去重：同一 timestamp 只保留最新记录
        entries = [e for e in entries if e['timestamp'] != self.timestamp]
        entries.append(entry)
        
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        
        logger.info(f"实验注册表已更新: {registry_path}")
    
    def _save_model(self, round_num: int):
        """保存模型到按实验时间戳分组的子目录中"""
        model_dir = os.path.join(
            self.config['output']['model_dir'],
            f"models_{self.timestamp}"
        )
        os.makedirs(model_dir, exist_ok=True)
        
        # 服务器可解密：保存明文模型
        model_path = os.path.join(model_dir, f"model_round_{round_num}.pth")
        torch.save(self.server.model.state_dict(), model_path)
        logger.info(f"明文模型已保存: {model_path}")
    
    def _save_results(self):
        """保存实验结果（JSON + Markdown报告）"""
        # 保留metrics.json供可视化使用
        metrics_path = os.path.join(self.output_dir, "metrics.json")
        self.metrics.save_to_file(metrics_path)
        
        # 生成可读的Markdown报告
        self._save_markdown_report()
        
        # 更新实验注册表
        self._update_experiment_registry()
        
        logger.info(f"结果已保存到: {self.output_dir}")
    
    def _save_markdown_report(self):
        """生成人类可读的Markdown实验报告（中英双语 + 详细数据）"""
        m = self.metrics.get_metrics()
        num_rounds = len(m.get('test_acc', []))
        is_encrypted = len(m.get('ciphertext_size', [])) > 0
        mode = "CKKS-Fed (Encrypted) / 加密模式" if is_encrypted else "FedAvg (Plaintext) / 明文模式"
        
        lines = []
        lines.append(f"# CKKS-Fed Experiment Report / 实验报告")
        lines.append(f"")
        lines.append(f"**Experiment Mode / 实验模式:** {mode}  ")
        lines.append(f"**Timestamp / 时间戳:** {self.timestamp}  ")
        lines.append(f"**Output Directory / 输出目录:** `{self.output_dir}`  ")
        lines.append(f"")
        
        # 配置摘要
        lines.append(f"## 1. Configuration Summary / 配置摘要")
        lines.append(f"")
        lines.append(f"| Parameter / 参数 | Value / 值 | Description / 说明 |")
        lines.append(f"|------------------|-----------|-------------------|")
        lines.append(f"| Dataset / 数据集 | {self.config['data']['dataset']} | 训练数据集名称 |")
        lines.append(f"| Model / 模型 | {self.config['model']['name']} | 神经网络架构 |")
        lines.append(f"| Num Clients / 客户端数 | {self.config['system']['num_clients']} | 参与联邦学习的总客户端数 |")
        lines.append(f"| Num Rounds / 轮数 | {self.config['system']['num_rounds']} | 联邦学习总轮数 |")
        lines.append(f"| Local Epochs / 本地轮数 | {self.config['system']['num_epochs']} | 每轮本地训练epoch数 |")
        lines.append(f"| Batch Size / 批次大小 | {self.config['system']['batch_size']} | 本地训练批次大小 |")
        lines.append(f"| Learning Rate / 学习率 | {self.config['system']['learning_rate']} | SGD优化器学习率 |")
        lines.append(f"| Client Sampling Rate / 采样率 | {self.config['system'].get('client_sampling_rate', 1.0)} | 每轮参与训练的客户端比例 |")
        lines.append(f"| IID / 独立同分布 | {self.config['data']['iid']} | 数据分布是否IID |")
        lines.append(f"| Device / 设备 | {self.config['system']['device']} | 训练设备(CPU/CUDA) |")
        lines.append(f"| Upload Difference / 上传差值 | {self.config['system'].get('upload_difference', True)} | 是否上传模型差值而非完整权重 |")
        lines.append(f"")
        
        # CKKS 配置（仅加密实验）
        if is_encrypted:
            lines.append(f"### 1.1 CKKS Parameters / CKKS加密参数")
            lines.append(f"")
            ckks = self.config['ckks']
            lines.append(f"| Parameter / 参数 | Value / 值 | Description / 说明 |")
            lines.append(f"|------------------|-----------|-------------------|")
            lines.append(f"| Poly Modulus Degree / 多项式模数度 | {ckks.get('poly_modulus_degree')} | CKKS多项式环的维度 |")
            lines.append(f"| Coeff Mod Bit Sizes / 系数模数位宽 | {ckks.get('coeff_mod_bit_sizes')} | 系数模数的位宽序列 |")
            lines.append(f"| Global Scale / 全局缩放因子 | {ckks.get('global_scale')} | CKKS编码缩放因子 |")
            lines.append(f"| Slot Packing / 槽打包 | {ckks.get('slot_packing', True)} | 是否启用SIMD槽打包 |")
            lines.append(f"")
        
        # Prefetch 配置
        has_prefetch = hasattr(self, 'clients') and len(self.clients) > 0 and hasattr(self.clients[0], 'get_prefetch_stats')
        if has_prefetch:
            lines.append(f"### 1.2 Prefetch Configuration / 预取配置")
            lines.append(f"")
            pf = self.config.get('prefetch', {})
            lines.append(f"| Parameter / 参数 | Value / 值 | Description / 说明 |")
            lines.append(f"|------------------|-----------|-------------------|")
            lines.append(f"| Enable Prefetch / 启用预取 | {pf.get('enable_prefetch', False)} | 是否启用CipherFetch预取 |")
            lines.append(f"| Max Prefetch Round / 最大预取轮数 | {pf.get('max_prefetch_round', 3)} | 预取窗口大小R |")
            lines.append(f"| Warmup Round / 预热轮数 | {pf.get('warmup_round', 2)} | 预取预热轮数 |")
            lines.append(f"| Overcommitment / 过承诺比例 | {pf.get('overcommitment', 1.0)} | 预采样倍数OC |")
            sel = self.config.get('client_selection', {})
            st = sel.get('sticky', {})
            lines.append(f"| Strategy / 策略 | {sel.get('strategy', 'random')} | 客户端选择策略 |")
            lines.append(f"| Sticky Group Size / 粘性组大小 | {st.get('group_size', 'auto')} | FedFetch中的k |")
            lines.append(f"| Sticky Change Base / 替换基数 | {st.get('change_num_base', 1)} | change_num = base × OC |")
            lines.append(f"| Scheduler Beta / 调度器松弛系数 | {pf.get('scheduler_beta', 0.5)} | T_percentile松弛系数 |")
            lines.append(f"")
        
        # 关键指标汇总
        lines.append(f"## 2. Key Metrics Summary / 关键指标汇总")
        lines.append(f"")
        
        final_test_acc = m['test_acc'][-1] if m['test_acc'] else 0.0
        final_test_loss = m['test_loss'][-1] if m['test_loss'] else 0.0
        total_time = sum(m.get('total_round_time', []))
        total_comm = sum(m.get('total_communication_cost', [])) / (1024 * 1024)
        
        # 判断实验类型：预取实验有 total_round_real_time，非预取实验有 total_round_time_simulated
        has_prefetch_metrics = len(m.get('total_round_real_time', [])) > 0
        has_simulated_metrics = len(m.get('total_round_time_simulated', [])) > 0
        
        total_upload_time = sum(m.get('upload_time', []))
        total_download_time = sum(m.get('download_time', []))
        total_sim_comm_time = total_upload_time + total_download_time
        
        lines.append(f"| Metric / 指标 | Value / 数值 | Description / 含义 |")
        lines.append(f"|---------------|-------------|-------------------|")
        lines.append(f"| Final Test Accuracy / 最终测试准确率 | **{final_test_acc:.2f}%** | 全局模型在测试集上的最终精度 |")
        lines.append(f"| Final Test Loss / 最终测试损失 | {final_test_loss:.4f} | 全局模型在测试集上的交叉熵损失 |")
        
        if has_prefetch_metrics:
            # 预取实验：total_round_time 是模拟 wall-clock，total_round_real_time 是真实 CPU
            total_sim_time = sum(m.get('total_round_time', []))
            total_real_time = sum(m.get('total_round_real_time', []))
            lines.append(f"| Total Simulated Time / 总模拟时间 | {total_sim_time:.2f} s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |")
            lines.append(f"| Total Simulated Comm Time / 总模拟通信时间 | {total_sim_comm_time:.2f} s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |")
            lines.append(f"| Total Real CPU Time / 总真实CPU时间 | {total_real_time:.2f} s | 单机串行执行的实际耗时 |")
            lines.append(f"| Avg Sim Round Time / 平均模拟轮次时间 | {safe_mean(m.get('total_round_time', [])):.2f} s | 模拟 wall-clock 平均每轮耗时 |")
            lines.append(f"| Avg Real Round Time / 平均真实轮次时间 | {safe_mean(m.get('total_round_real_time', [])):.2f} s | 真实 CPU 平均每轮耗时 |")
        elif has_simulated_metrics:
            # 非预取实验：total_round_time 是真实 CPU，total_round_time_simulated 是模拟 wall-clock
            total_real_time = sum(m.get('total_round_time', []))
            total_sim_time = sum(m.get('total_round_time_simulated', []))
            lines.append(f"| Total Real CPU Time / 总真实CPU时间 | {total_real_time:.2f} s | 单机串行执行的实际耗时 |")
            lines.append(f"| Total Simulated Time / 总模拟时间 | {total_sim_time:.2f} s | 含计算与网络传输的模拟 wall-clock 时间（可横向对比） |")
            lines.append(f"| Total Simulated Comm Time / 总模拟通信时间 | {total_sim_comm_time:.2f} s | 纯网络传输时间 = Σ max(client_upload) + Σ max(client_download) |")
            lines.append(f"| Avg Real Round Time / 平均真实轮次时间 | {safe_mean(m.get('total_round_time', [])):.2f} s | 真实 CPU 平均每轮耗时 |")
            lines.append(f"| Avg Sim Round Time / 平均模拟轮次时间 | {safe_mean(m.get('total_round_time_simulated', [])):.2f} s | 模拟 wall-clock 平均每轮耗时 |")
        else:
            lines.append(f"| Total Training Time / 总训练时间 | {total_time:.2f} s | 整个实验从头到尾的总耗时 |")
            lines.append(f"| Total Simulated Comm Time / 总模拟通信时间 | {total_sim_comm_time:.2f} s | 纯网络传输时间 |")
            lines.append(f"| Avg Round Time / 平均每轮时间 | {safe_mean(m.get('total_round_time', [])):.2f} s | 从模型下发到聚合完成的平均耗时 |")
        
        total_upload = sum(m.get('upload_cost', []))
        total_download = sum(m.get('download_cost', []))
        total_fetch_download = sum(m.get('fetch_download_cost', []))
        total_prefetch_download = sum(m.get('prefetch_download_cost', []))
        total_upload_time = sum(m.get('upload_time', []))
        total_download_time = sum(m.get('download_time', []))

        if has_prefetch:
            total_actual_download = total_fetch_download + total_prefetch_download
            lines.append(f"| Total Communication / 总通信量 | {total_comm:.2f} MB | 训练通信 TV = upload + FV（选中客户端实际 fetch 下载量） |")
            lines.append(f"| Total Upload / 总上传量 | {total_upload/(1024*1024):.2f} MB / {total_upload_time:.2f} s | 所有选中客户端密文上传累计 |")
            lines.append(f"| Total Download (Fetch) / 实际补下载 | {total_fetch_download/(1024*1024):.2f} MB | 选中客户端实际 fetch 的密文增量 |")
            lines.append(f"| Total Download (Prefetch) / 后台预取 | {total_prefetch_download/(1024*1024):.2f} MB | 未选中客户端后台预取的密文增量 |")
            lines.append(f"| Total Actual Download / 总实际下载 | {total_actual_download/(1024*1024):.2f} MB | Fetch + Prefetch 物理下载总量 |")
            lines.append(f"| Effective Download / 理论下载责任 | {total_download/(1024*1024):.2f} MB | delta_size × 选中客户端数（用于 TV 计算） |")
        else:
            lines.append(f"| Total Communication / 总通信量 | {total_comm:.2f} MB | 所有轮次上传+下载之和 |")
            lines.append(f"| Total Upload / 总上传量 | {total_upload/(1024*1024):.2f} MB / {total_upload_time:.2f} s | 所有轮次上传开销+时间之和 |")
            lines.append(f"| Total Download / 总下载量 | {total_download/(1024*1024):.2f} MB / {total_download_time:.2f} s | 所有轮次下载开销+时间之和 |")
            # MASER 通信结构明细
            if self.config.get('maser', {}).get('enable', False):
                total_ct_upload = sum(m.get('maser_ct_upload', []))
                total_agg_download = sum(m.get('maser_agg_ct_download', []))
                total_pd_upload = sum(m.get('maser_partial_dec_upload', []))
                total_plain_download = sum(m.get('maser_plaintext_download', []))
                lines.append(f"| MASER ① 加密上传 | {total_ct_upload/(1024*1024):.2f} MB | 客户端原始密文更新上传累计 |")
                lines.append(f"| MASER ② 聚合密文广播 | {total_agg_download/(1024*1024):.2f} MB | 服务器聚合后密文下发给客户端做 partial decrypt |")
                lines.append(f"| MASER ③ 解密份额上传 | {total_pd_upload/(1024*1024):.2f} MB | 客户端 partial decrypt 份额回传累计 |")
                lines.append(f"| MASER ④ 明文模型下发 | {total_plain_download/(1024*1024):.2f} MB | 服务器解密后下发明文全局模型累计 |")
        lines.append(f"| Avg Upload Cost / 平均上传开销 | {safe_mean(m.get('upload_cost', [])) / (1024*1024):.2f} MB | mean(upload_cost)/2^20 |")
        if has_prefetch:
            lines.append(f"| Avg Effective Download / 平均理论下载 | {safe_mean(m.get('download_cost', [])) / (1024*1024):.2f} MB | mean(download_cost)/2^20 |")
        else:
            lines.append(f"| Avg Download Cost / 平均下载开销 | {safe_mean(m.get('download_cost', [])) / (1024*1024):.2f} MB | mean(download_cost)/2^20 |")
        
        if is_encrypted:
            avg_expansion = safe_mean(m.get('expansion_ratio', []))
            avg_enc_time = safe_mean(m.get('encryption_time', []))
            total_ct_blocks = sum(m.get('num_ciphertexts', []))
            total_agg_cts = sum(m.get('aggregated_ciphertexts', []))
            total_plain = sum(m.get('plaintext_size', []))
            total_cipher = sum(m.get('ciphertext_size', []))
            avg_single_ct = total_cipher / total_ct_blocks if total_ct_blocks > 0 else 0

            # 聚合密文大小：标准 CKKS 聚合不改变密文大小；xMK-CKKS 聚合密文会增长
            avg_agg_ct_size = avg_single_ct  # 默认：标准 CKKS（聚合不改变大小）
            avg_selected = 1
            if hasattr(self, 'ckks_manager') and self.ckks_manager and total_agg_cts > 0:
                if self.ckks_manager.xmkckks is not None:
                    # xMK-CKKS：使用线性插值计算聚合密文大小
                    avg_selected = total_ct_blocks / len(m.get('num_ciphertexts', [1])) if m.get('num_ciphertexts') else 1
                    avg_agg_ct_size = self.ckks_manager.compute_aggregated_ct_size(int(avg_selected))
                else:
                    # 标准 CKKS：使用服务器当前加密全局状态的大小
                    try:
                        if hasattr(self.server, 'encrypted_global_state') and self.server.encrypted_global_state is not None:
                            avg_agg_ct_size = self.ckks_manager.compute_encrypted_update_size(self.server.encrypted_global_state) / total_agg_cts if total_agg_cts > 0 else avg_single_ct
                    except Exception:
                        avg_agg_ct_size = avg_single_ct

            lines.append(f"| Avg Expansion Ratio / 平均密文膨胀率 | {avg_expansion:.2f}x | 密文大小相对明文的平均倍数 |")
            lines.append(f"| Avg Encryption Time / 平均加密时间 | {avg_enc_time:.3f} s/client | 每个客户端加密模型更新的平均耗时 |")
            lines.append(f"| Total CT Blocks (Upload) / 总密文上传块数 | {total_ct_blocks} blocks | 所有客户端所有轮次上传的密文块总数 |")
            lines.append(f"| Total Aggregated CTs (Download) / 总聚合密文下载数 | {total_agg_cts} blocks | 服务器聚合后广播的密文块总数 |")
            lines.append(f"| Avg Single Ciphertext Size / 平均单密文大小 | {avg_single_ct:.0f} bytes | 单个客户端密文块的平均大小 |")
            lines.append(f"| Avg Aggregated CT Size / 平均聚合密文大小 | {avg_agg_ct_size:.0f} bytes | 服务器聚合后密文块的平均大小 |")
            lines.append(f"| Key Distribution Cost / 密钥分发开销 | {sum(m.get('key_distribution_cost', [])) / (1024*1024):.2f} MB | CKKS公钥/Galois密钥分发总字节数 |")
            lines.append(f"| CT Upload Time / 密文上传时间 | {total_upload_time:.2f} s | 最慢客户端上传密文的模拟 wall-clock 时间之和 |")
            lines.append(f"| CT Download Time / 密文下载时间 | {total_download_time:.2f} s | 最慢客户端下载密文的模拟 wall-clock 时间之和 |")
            
            if has_prefetch:
                avg_pf_time = safe_mean(m.get('prefetch_time', []))
                avg_fetch_time = safe_mean(m.get('fetch_time', []))
                avg_apply_time = safe_mean(m.get('apply_time', []))
                total_pf_download = sum(c.get_prefetch_stats().get('total_prefetch_download_cost', 0) for c in self.clients)
                total_fetch_download = sum(c.get_prefetch_stats().get('total_fetch_download_cost', 0) for c in self.clients)
                total_broadcast = sum(m.get('prefetch_broadcast_cost', []))
                lines.append(f"| Avg Prefetch Accum Time / 平均预取累加时间 | {avg_pf_time:.3f} s/client | 客户端同态累加密文增量的平均耗时 |")
                lines.append(f"| Avg Fetch Time / 平均Fetch时间 | {avg_fetch_time:.3f} s/client | 客户端下载剩余密文增量的平均耗时 |")
                lines.append(f"| Avg Apply Time / 平均应用时间 | {avg_apply_time:.3f} s/client | 客户端解密并应用预取状态的平均耗时 |")
                lines.append(f"| Total Prefetch Download / 预取下载总量 | {total_pf_download/(1024*1024):.2f} MB | 所有客户端接收的密文增量之和 |")
                lines.append(f"| Total Fetch Download / Fetch下载总量 | {total_fetch_download/(1024*1024):.2f} MB | 所有客户端下载的剩余密文增量之和 |")
                lines.append(f"| Total Prefetch Broadcast / 预取广播总量 | {total_broadcast/(1024*1024):.2f} MB | 服务器向未选中客户端广播的密文增量之和 |")
            
            # TEE 时间开销明细（ESAFL 模拟：去除重加密指标）
            if len(m.get('tee_total_time', [])) > 0:
                lines.append(f"")
                lines.append(f"### 1.3 TEE Time Breakdown / TEE 时间开销明细")
                lines.append(f"")
                lines.append(f"| Stage / 阶段 | Avg Time / 平均耗时 | Total / 累计 | Description / 说明 |")
                lines.append(f"|--------------|---------------------|--------------|-------------------|")
                tee_total = sum(m.get('tee_total_time', []))
                tee_decrypt = sum(m.get('tee_decrypt_time', []))
                tee_aggregate = sum(m.get('tee_aggregate_time', []))
                tee_compensate = sum(m.get('tee_compensate_time', []))
                tee_compress = sum(m.get('tee_compress_time', []))
                lines.append(f"| TEE Total / TEE 总耗时 | {safe_mean(m.get('tee_total_time', [])):.4f} s | {tee_total:.4f} s | ESAFL模拟：解密+聚合+补偿+压缩（无重加密） |")
                lines.append(f"| TEE Decrypt / TEE 解密 | {safe_mean(m.get('tee_decrypt_time', [])):.4f} s | {tee_decrypt:.4f} s | CKKS 密文解密（主要瓶颈） |")
                lines.append(f"| TEE Aggregate / TEE 聚合 | {safe_mean(m.get('tee_aggregate_time', [])):.4f} s | {tee_aggregate:.4f} s | 明文域加权平均+标量除法 |")
                lines.append(f"| TEE Compensate / TEE 补偿 | {safe_mean(m.get('tee_compensate_time', [])):.4f} s | {tee_compensate:.4f} s | 盲化掩码补偿计算 |")
                lines.append(f"| TEE Compress / TEE 压缩 | {safe_mean(m.get('tee_compress_time', [])):.4f} s | {tee_compress:.4f} s | TopK 二次压缩+残差更新 |")
                # lines.append(f"| TEE Re-encrypt / TEE 重加密 | 0.0000 s | 0.0000 s | ESAFL模拟：客户端本地解密，无服务器重加密 |")
        
        lines.append(f"")
        
        # 客户端参与统计（增强版）
        lines.append(f"## 3. Client Participation & Statistics / 客户端参与统计与详情")
        lines.append(f"")
        if has_prefetch:
            lines.append(f"| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 | Prefetch ↓ / 预取下载 | Fetch ↓ / 补下载 | Total ↓ / 总下载 | Score / 粘性分 |")
            lines.append(f"|-----|----------------|--------------|------------------|------------------|----------------------|------------------|------------------|---------------|")
            for cid in sorted(self.client_participation.keys()):
                ct_count = self.client_total_ciphertexts.get(cid, 0) if is_encrypted else 0
                pf_stat = self.clients[cid].get_prefetch_stats() if hasattr(self, 'clients') and cid < len(self.clients) else {}
                dl_bw = pf_stat.get('dl_bw_kbps', 0)
                ul_bw = pf_stat.get('ul_bw_kbps', 0)
                pf_dl = pf_stat.get('total_prefetch_download_cost', 0)
                fetch_dl = pf_stat.get('total_fetch_download_cost', 0)
                total_dl = pf_stat.get('total_download_cost_cumulative', 0)
                score = "-"
                if self.sticky_manager and hasattr(self.sticky_manager, 'sticky_scores'):
                    score = f"{self.sticky_manager.sticky_scores.get(cid, 0):.2f}"
                lines.append(f"| {cid} | {self.client_participation[cid]} | {ct_count} | {dl_bw:.0f} kbps | {ul_bw:.0f} kbps | {pf_dl/(1024*1024):.2f} MB | {fetch_dl/(1024*1024):.2f} MB | {total_dl/(1024*1024):.2f} MB | {score} |")
        else:
            lines.append(f"| CID | Part / 参与轮次 | CTs / 密文数 | DL BW / 下行带宽 | UL BW / 上行带宽 |")
            lines.append(f"|-----|----------------|--------------|------------------|------------------|")
            for cid in sorted(self.client_participation.keys()):
                ct_count = self.client_total_ciphertexts.get(cid, 0) if is_encrypted else 0
                dl_bw = "-"
                ul_bw = "-"
                if self.bandwidth_simulator is not None:
                    dl_bw = f"{self.bandwidth_simulator.get_dl_bw_kbps(cid):.0f} kbps"
                    ul_bw = f"{self.bandwidth_simulator.get_ul_bw_kbps(cid):.0f} kbps"
                lines.append(f"| {cid} | {self.client_participation[cid]} | {ct_count} | {dl_bw} | {ul_bw} |")
        lines.append(f"")
        
        # 每轮详细结果
        lines.append(f"## 4. Per-Round Results / 每轮详细结果")
        lines.append(f"")
        has_tee = len(m.get('tee_total_time', [])) > 0
        header = "| Round / 轮次 | Test Acc / 测试准确率 | Test Loss / 测试损失 | Round Time / 轮次耗时 | Upload Time / 上传时间 | Download Time / 下载时间 | Comm / 通信量 | CT Uploads / 密文上传数 | CT Downloads / 聚合密文数 |"
        if is_encrypted:
            header += " Encrypt / 加密耗时 | Expansion / 膨胀率 |"
        if has_tee:
            header += " TEE Time / TEE耗时 |"
        lines.append(header)
        
        sep = "|--------------|----------------------|---------------------|----------------------|----------------------|-----------------------|---------------|--------------------------|--------------------------|"
        if is_encrypted:
            sep += "---------------------|---------------------|"
        if has_tee:
            sep += "---------------------|"
        lines.append(sep)
        
        for r in range(num_rounds):
            acc = m['test_acc'][r] if r < len(m['test_acc']) else 0.0
            loss = m['test_loss'][r] if r < len(m['test_loss']) else 0.0
            # 统一使用模拟 wall-clock 时间作为 Round Time，确保预取/非预取实验可公平对比
            if has_prefetch_metrics:
                rt = m['total_round_time'][r] if r < len(m['total_round_time']) else 0.0
            elif has_simulated_metrics:
                rt = m['total_round_time_simulated'][r] if r < len(m.get('total_round_time_simulated', [])) else 0.0
            else:
                rt = m['total_round_time'][r] if r < len(m['total_round_time']) else 0.0
            ul_t = m['upload_time'][r] if r < len(m.get('upload_time', [])) else 0.0
            dl_t = m['download_time'][r] if r < len(m.get('download_time', [])) else 0.0
            comm = m['total_communication_cost'][r] / (1024*1024) if r < len(m['total_communication_cost']) else 0.0
            ct_up = m['num_ciphertexts'][r] if r < len(m.get('num_ciphertexts', [])) else 0
            ct_down = m['aggregated_ciphertexts'][r] if r < len(m.get('aggregated_ciphertexts', [])) else 0
            row = f"| {r+1} | {acc:.2f}% | {loss:.4f} | {rt:.2f}s | {ul_t:.2f}s | {dl_t:.2f}s | {comm:.2f} MB | {ct_up} | {ct_down} |"
            
            if is_encrypted:
                enc_t = m['encryption_time'][r] if r < len(m['encryption_time']) else 0.0
                exp = m['expansion_ratio'][r] if r < len(m['expansion_ratio']) else 0.0
                row += f" {enc_t:.3f}s | {exp:.2f}x |"
            
            if has_tee:
                tee_t = m['tee_total_time'][r] if r < len(m['tee_total_time']) else 0.0
                row += f" {tee_t:.3f}s |"
            
            lines.append(row)
        
        lines.append(f"")
        
        # 通信开销与密文块数计算详情（带数值代入）
        lines.append(f"## 5. Communication & Ciphertext Details / 通信与密文计算详情")
        lines.append(f"")
        
        total_plain = sum(m.get('plaintext_size', []))
        total_upload = sum(m.get('upload_cost', []))
        total_download = sum(m.get('download_cost', []))
        total_fetch_download = sum(m.get('fetch_download_cost', []))
        total_prefetch_download = sum(m.get('prefetch_download_cost', []))
        total_comm = sum(m.get('total_communication_cost', []))
        global_model_size_bytes = self.server.compute_download_cost() if hasattr(self, 'server') else 0
        # total_selected_clients = sum of all client participations (more accurate than total_download / model_size)
        total_selected_clients = sum(self.client_participation.values()) if hasattr(self, 'client_participation') else 0
        effective_download = global_model_size_bytes * total_selected_clients
        
        lines.append(f"### 5.1 Formula Definitions / 公式定义")
        lines.append(f"")
        lines.append(f"| # | Metric / 指标 | Formula / 公式 |")
        lines.append(f"|---|---------------|----------------|")
        if is_encrypted:
            lines.append(f"| 1 | Plaintext Size / 明文大小 | `sum(v.numel() * 4 for v in model_update.values())` |")
            lines.append(f"| 2 | Ciphertext Size / 密文大小 | `sum(len(ct.serialize()) for ct in encrypted_update.values())` |")
            lines.append(f"| 3 | Ciphertext Blocks / 密文块数 | `sum(len(v) for v in encrypted_update.values())` |")
            lines.append(f"| 4 | Upload Cost / 上传开销 | `sum(ciphertext_size of selected clients)` |")
            if has_prefetch:
                lines.append(f"| 5 | Fetch Volume (FV) / 补下载量 | `sum(fetch_download_cost)` |")
                lines.append(f"| 6 | Effective Download / 理论下载责任 | `delta_size * num_selected_clients per round` |")
                lines.append(f"| 7 | Total Communication (TV) / 训练通信 | `upload_cost + fetch_download_cost` |")
            else:
                lines.append(f"| 5 | Download Cost / 下载开销 | `global_model_size_bytes * num_selected_clients` |")
                lines.append(f"| 6 | Total Communication / 总通信 | `upload_cost + download_cost` |")
                if self.config.get('maser', {}).get('enable', False):
                    lines.append(f"| 8 | MASER ① 加密上传 | `sum(client ciphertext sizes)` |")
                    lines.append(f"| 9 | MASER ② 聚合密文广播 | `num_selected * num_batches * agg_ct_size` |")
                    lines.append(f"| 10 | MASER ③ 解密份额上传 | `num_selected * num_batches * agg_ct_size` |")
                    lines.append(f"| 11 | MASER ④ 明文模型下发 | `global_model_size_bytes * num_selected_clients` |")
            lines.append(f"| 7 | Expansion Ratio / 膨胀率 | `total_ciphertext_size / total_plaintext_size` |")
        else:
            lines.append(f"| 1 | Plaintext Size / 明文大小 | `sum(v.numel() * 4 for v in model_update.values())` |")
            lines.append(f"| 2 | Upload Cost / 上传开销 | `sum(plaintext_size of selected clients)` |")
            if has_prefetch:
                lines.append(f"| 3 | Download Cost / 下载开销 | `sum(fetch_download_cost of selected clients)` |")
            else:
                lines.append(f"| 3 | Download Cost / 下载开销 | `global_model_size_bytes * num_selected_clients` |")
            lines.append(f"| 4 | Total Communication / 总通信 | `upload_cost + download_cost` |")
        lines.append(f"")
        
        lines.append(f"### 5.2 Substituted Values / 数值代入")
        lines.append(f"")
        lines.append(f"| # | Metric / 指标 | Formula / 代入公式 | Result / 结果 |")
        lines.append(f"|---|---------------|-------------------|---------------|")
        if is_encrypted:
            total_cipher = sum(m.get('ciphertext_size', []))
            total_blocks = sum(m.get('num_ciphertexts', []))
            total_agg_cts = sum(m.get('aggregated_ciphertexts', []))
            avg_exp = safe_mean(m.get('expansion_ratio', [0]))
            avg_single_ct = total_cipher / total_blocks if total_blocks > 0 else 0
            # 聚合密文大小：标准 CKKS 聚合不改变密文大小；xMK-CKKS 聚合密文会增长
            avg_agg_ct_size = avg_single_ct  # 默认：标准 CKKS（聚合不改变大小）
            avg_selected = 1
            if hasattr(self, 'ckks_manager') and self.ckks_manager and total_agg_cts > 0:
                if hasattr(self.ckks_manager, 'compute_aggregated_ct_size'):
                    # xMK-CKKS：使用线性插值计算聚合密文大小
                    avg_selected = total_blocks / len(m.get('num_ciphertexts', [1])) if m.get('num_ciphertexts') else 1
                    avg_agg_ct_size = self.ckks_manager.compute_aggregated_ct_size(int(avg_selected))
                # 标准 CKKS：聚合密文大小 = 单密文大小（同态相加不改变密文大小）
            lines.append(f"| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = {total_plain}` | {total_plain/(1024*1024):.2f} MB |")
            lines.append(f"| 2 | Total Ciphertext / 总密文 | `sum(ciphertext_size) = {total_cipher}` | {total_cipher/(1024*1024):.2f} MB |")
            lines.append(f"| 3 | Total CT Blocks (Upload) / 总密文上传块 | `sum(num_ciphertexts) = {total_blocks}` | {total_blocks} blocks |")
            lines.append(f"| 4 | Total Aggregated CTs (Download) / 总聚合密文 | `sum(aggregated_ciphertexts) = {total_agg_cts}` | {total_agg_cts} blocks |")
            lines.append(f"| 5 | Avg Single CT Size / 平均单密文大小 | `{total_cipher}/{total_blocks} = {avg_single_ct:.0f}` | {avg_single_ct/(1024):.2f} KB |")
            lines.append(f"| 6 | Avg Aggregated CT Size / 平均聚合密文大小 | `xMKCKKS.compute_aggregated_ct_size({int(avg_selected) if total_blocks > 0 else 0})` | {avg_agg_ct_size/(1024):.2f} KB |")
            lines.append(f"| 7 | Total Upload / 总上传 | `sum(upload_cost) = {total_upload}` | {total_upload/(1024*1024):.2f} MB |")
            if has_prefetch:
                lines.append(f"| 8 | Total Download (Fetch) / 实际补下载 | `sum(fetch_download_cost) = {total_download}` | {total_download/(1024*1024):.2f} MB |")
            else:
                lines.append(f"| 8 | Total Download / 总下载 | `model_size({global_model_size_bytes}) * selected({total_selected_clients}) = {total_download}` | {total_download/(1024*1024):.2f} MB |")
            lines.append(f"| 9 | Total Communication / 总通信 | `{total_upload} + {total_download} = {total_comm}` | {total_comm/(1024*1024):.2f} MB |")
            lines.append(f"| 10 | Avg Expansion / 平均膨胀率 | `mean(expansion_ratio) = {avg_exp:.4f}` | {avg_exp:.2f}x |")
            if self.config.get('maser', {}).get('enable', False):
                m_ct = sum(m.get('maser_ct_upload', []))
                m_agg = sum(m.get('maser_agg_ct_download', []))
                m_pd = sum(m.get('maser_partial_dec_upload', []))
                m_plain = sum(m.get('maser_plaintext_download', []))
                lines.append(f"| 11 | MASER ① 加密上传 | `sum(maser_ct_upload) = {m_ct}` | {m_ct/(1024*1024):.2f} MB |")
                lines.append(f"| 12 | MASER ② 聚合密文广播 | `sum(maser_agg_ct_download) = {m_agg}` | {m_agg/(1024*1024):.2f} MB |")
                lines.append(f"| 13 | MASER ③ 解密份额上传 | `sum(maser_partial_dec_upload) = {m_pd}` | {m_pd/(1024*1024):.2f} MB |")
                lines.append(f"| 14 | MASER ④ 明文模型下发 | `sum(maser_plaintext_download) = {m_plain}` | {m_plain/(1024*1024):.2f} MB |")
        else:
            lines.append(f"| 1 | Total Plaintext / 总明文 | `sum(plaintext_size) = {total_plain}` | {total_plain} B ({total_plain/1024:.2f} KB) |")
            lines.append(f"| 2 | Total Upload / 总上传 | `sum(upload_cost) = {total_upload}` | {total_upload} B ({total_upload/1024:.2f} KB) |")
            if has_prefetch:
                lines.append(f"| 3 | Fetch Volume (FV) / 补下载量 | `sum(download_cost) = {total_download}` | {total_download} B ({total_download/1024:.2f} KB) |")
                lines.append(f"| 4 | Effective Download / 理论下载责任 | `delta_size * selected_clients = {effective_download}` | {effective_download} B ({effective_download/1024:.2f} KB) |")
                lines.append(f"| 5 | Total Communication (TV) / 训练通信 | `{total_upload} + {total_download} = {total_comm}` | {total_comm} B ({total_comm/1024:.2f} KB) |")
            else:
                lines.append(f"| 3 | Total Download / 总下载 | `model_size({global_model_size_bytes}) * selected({total_selected_clients}) = {total_download}` | {total_download} B ({total_download/1024:.2f} KB) |")
                lines.append(f"| 4 | Total Communication / 总通信 | `{total_upload} + {total_download} = {total_comm}` | {total_comm} B ({total_comm/1024:.2f} KB) |")
        lines.append(f"")

        # MASER 通信结构专项说明
        if self.config.get('maser', {}).get('enable', False):
            lines.append(f"### 5.2.1 MASER Communication Structure / MASER 通信结构")
            lines.append(f"")
            m_ct = sum(m.get('maser_ct_upload', []))
            m_agg = sum(m.get('maser_agg_ct_download', []))
            m_pd = sum(m.get('maser_partial_dec_upload', []))
            m_plain = sum(m.get('maser_plaintext_download', []))
            calc_upload = m_ct + m_pd
            calc_download = m_agg + m_plain
            lines.append(f"- **① Encrypted Upload / 加密上传:** {m_ct/(1024*1024):.2f} MB — 客户端本地 mask 裁剪后用 TenSEAL 加密的稀疏更新")
            lines.append(f"- **② Aggregated CT Broadcast / 聚合密文广播:** {m_agg/(1024*1024):.2f} MB — 服务器聚合后的密文下发给所有客户端（模拟 xMK-CKKS 多密钥结构）")
            lines.append(f"- **③ Partial Decryption Upload / 解密份额上传:** {m_pd/(1024*1024):.2f} MB — 客户端 partial decrypt 份额回传（模拟量）")
            lines.append(f"- **④ Plaintext Model Download / 明文模型下发:** {m_plain/(1024*1024):.2f} MB — 服务器解密后下发明文全局模型")
            lines.append(f"- **Total Upload / 总上传:** {calc_upload/(1024*1024):.2f} MB = ① + ③")
            lines.append(f"- **Total Download / 总下载:** {calc_download/(1024*1024):.2f} MB = ② + ④")
            lines.append(f"- **Total Communication / 总通信:** {(calc_upload+calc_download)/(1024*1024):.2f} MB = ① + ② + ③ + ④")
            if abs(calc_upload - total_upload) > 1 or abs(calc_download - total_download) > 1:
                lines.append(f"  ⚠️ 验证提示：分量加总与 total upload/download 存在舍入差异（upload diff={abs(calc_upload-total_upload):.0f} B, download diff={abs(calc_download-total_download):.0f} B）")
            else:
                lines.append(f"  ✅ 验证通过：分量加总与总上传/总下载一致")
            lines.append(f"")

        # 新增：预取通信分析
        if has_prefetch:
            lines.append(f"### 5.3 Prefetch Communication Analysis / 预取通信分析")
            lines.append(f"")
            total_pf = sum(c.get_prefetch_stats().get('total_prefetch_download_cost', 0) for c in self.clients)
            total_fetch = sum(c.get_prefetch_stats().get('total_fetch_download_cost', 0) for c in self.clients)
            total_broadcast = sum(m.get('prefetch_broadcast_cost', []))
            total_all = total_pf + total_fetch + total_broadcast
            # 计算理论下载责任（用于预取节省率）
            effective_download = global_model_size_bytes * total_selected_clients
            saved_by_prefetch = max(0, effective_download - total_download)
            
            lines.append(f"- **Total Upload / 总上传开销:** {total_upload/(1024*1024):.2f} MB — 所有选中客户端密文上传的累计量")
            lines.append(f"- **Fetch Volume (FV) / 补下载量:** {total_download/(1024*1024):.2f} MB — 选中客户端实际 fetch 下载量（已扣除预取覆盖部分）")
            lines.append(f"- **Training Communication (TV) / 训练通信:** {total_comm/(1024*1024):.2f} MB = Upload({total_upload/(1024*1024):.2f} MB) + FV({total_download/(1024*1024):.2f} MB)")
            # 验证等式
            calc_total = total_upload + total_download
            if abs(calc_total - total_comm) > 1:
                lines.append(f"  ⚠️ 验证失败: Upload + FV = {calc_total/(1024*1024):.2f} MB ≠ Total Communication = {total_comm/(1024*1024):.2f} MB (diff={abs(calc_total-total_comm):.0f} B)")
            else:
                lines.append(f"  ✅ 验证通过: Upload({total_upload/(1024*1024):.2f} MB) + FV({total_download/(1024*1024):.2f} MB) = TV({total_comm/(1024*1024):.2f} MB)")
            lines.append(f"  — TV 对齐 FedFetch 论文定义：TV = Upload + FV（不含后台预取）")
            lines.append(f"- **Prefetch Broadcast / 预取广播:** {total_broadcast/(1024*1024):.2f} MB — 服务器向未选中客户端后台广播的密文增量")
            lines.append(f"- **Prefetch Download / 预取下载:** {total_pf/(1024*1024):.2f} MB — 未选中客户端后台接收的密文增量")
            lines.append(f"- **Prefetch + Fetch + Broadcast / 后台总流量:** {total_all/(1024*1024):.2f} MB = Prefetch DL({total_pf/(1024*1024):.2f}) + Fetch DL({total_fetch/(1024*1024):.2f}) + Broadcast({total_broadcast/(1024*1024):.2f})")
            lines.append(f"- **Effective Download / 理论下载责任:** {effective_download/(1024*1024):.2f} MB — 每轮 delta_size × 选中客户端数（预取节省率计算基准）")
            lines.append(f"- **Prefetch Savings / 预取节省:** {saved_by_prefetch/(1024*1024):.2f} MB — Effective Download 与实际 FV 的差值")
            lines.append(f"- **Baseline (no prefetch) / 无预取基线:** {global_model_size_bytes * total_selected_clients / (1024*1024):.2f} MB — 完整模型下载({global_model_size_bytes/(1024*1024):.2f} MB × {total_selected_clients} 次)")
            lines.append(f"")
            lines.append(f"> **Note / 说明:**")
            lines.append(f"> 1. **FV** = 选中客户端实际 fetch 下载量。TV = Upload + FV（FedFetch 论文定义）。")
            lines.append(f"> 2. **Effective Download** = delta_size × 选中客户端数，是理论下载责任，仅用于计算预取节省率。")
            lines.append(f"> 3. **Prefetch** = 后台/空闲时流量，不计入 TV，但计入物理总下行带宽。")
            lines.append(f"> 4. 预取的核心优势是**将训练前的同步下载变为后台增量推送**，降低 wall-clock 延迟。")
            
            lines.append(f"")
            lines.append(f"### 5.4 FedFetch Key Metrics (TT / FT / TV / FV) / FedFetch 核心指标")
            lines.append(f"")
            lines.append(f"以下指标对齐 FedFetch 论文定义，用于量化预取机制的时序与通信优势：")
            lines.append(f"")
            lines.append(f"| Metric / 指标 | Symbol / 符号 | Formula / 公式 | Substitution / 代入 | Value / 数值 | Description / 说明 |")
            lines.append(f"|---------------|---------------|----------------|---------------------|--------------|-------------------|")
            # TT: Training Time = mean(total_round_time)
            _tt_vals = m.get('total_round_time', [0])
            _tt_sum = sum(_tt_vals)
            _tt_n = len(_tt_vals)
            avg_tt = safe_mean(_tt_vals)
            lines.append(f"| Training Time / 训练时间 | **TT** | `mean(total_round_time)` | `{_tt_sum:.2f}/{_tt_n}` | {avg_tt:.2f} s/轮 | 每轮 wall-clock 延迟（最慢客户端完成时间） |")
            # FT: Fetch Time = mean(fetch_time)
            _ft_vals = m.get('fetch_time', [0])
            _ft_sum = sum(_ft_vals)
            _ft_n = len(_ft_vals)
            avg_ft = safe_mean(_ft_vals)
            lines.append(f"| Fetch Time / 补下载时间 | **FT** | `mean(fetch_time)` | `{_ft_sum:.2f}/{_ft_n}` | {avg_ft:.2f} s/轮 | 选中客户端下载剩余密文增量的时间 |")
            # TV: Training Volume = mean(total_communication_cost)
            _tv_vals = m.get('total_communication_cost', [0])
            _tv_sum = sum(_tv_vals)
            _tv_n = len(_tv_vals)
            avg_tv = safe_mean(_tv_vals) / (1024*1024)
            lines.append(f"| Training Volume / 训练通信 | **TV** | `mean(total_communication_cost)/2^20` | `{_tv_sum:.2f}/{_tv_n}/1048576` | {avg_tv:.2f} MB/轮 | 每轮训练产生的总通信量（不含后台预取） |")
            # FV: Fetch Volume = mean(download_cost)
            _fv_vals = m.get('download_cost', [0])
            _fv_sum = sum(_fv_vals)
            _fv_n = len(_fv_vals)
            avg_fv = safe_mean(_fv_vals) / (1024*1024)
            lines.append(f"| Fetch Volume / 补下载量 | **FV** | `mean(download_cost)/2^20` | `{_fv_sum:.2f}/{_fv_n}/1048576` | {avg_fv:.2f} MB/轮 | 选中客户端补充下载的密文增量 |")
            # PV: Prefetch Volume = mean(prefetch_broadcast_cost)
            _pv_vals = m.get('prefetch_broadcast_cost', [0])
            _pv_sum = sum(_pv_vals)
            _pv_n = len(_pv_vals)
            avg_pv = safe_mean(_pv_vals) / (1024*1024) if _pv_vals else 0.0
            lines.append(f"| Prefetch Volume / 预取量 | **PV** | `mean(prefetch_broadcast_cost)/2^20` | `{_pv_sum:.2f}/{_pv_n}/1048576` | {avg_pv:.2f} MB/轮 | 服务器后台广播的密文增量（不计入 TV） |")
            lines.append(f"")
            lines.append(f"> **Parallelism / 并行性说明:** 当前实现中，预取广播在每轮训练完成后、下一轮开始前进行，")
            lines.append(f"> 属于**串行调度**。预取通信量不计入 TV（训练通信），因此总通信对比是公平的；")
            lines.append(f"> 预取节省的是选中客户端训练前的 fetch 等待时间，这是 FedFetch 降低 wall-clock 延迟的核心机制。")
            lines.append(f"")
            lines.append(f"### 5.5 EMA Round Duration Analysis / EMA 轮次持续时间分析")
            lines.append(f"")
            lines.append(f"以下指标记录每轮结束后指数移动平均（EMA）估计的轮次持续时间，用于预取调度的带宽预算计算。")
            lines.append(f"")
            # Per-round EMA prediction vs real time table
            _round_times = m.get('total_round_time', [])
            _alpha = getattr(self.server.prefetch_scheduler, 'avg_alpha', 0.125) if hasattr(self, 'server') and hasattr(self.server, 'prefetch_scheduler') else 0.125
            if _round_times:
                lines.append(f"**EMA平滑系数 alpha = {_alpha}**")
                lines.append(f"")
                lines.append(f"| Round / 轮次 | " + " | ".join(str(i+1) for i in range(len(_round_times))) + " |")
                lines.append(f"|--------------|" + "|".join(["----------"] * len(_round_times)) + "|")
                # EMA prediction row: prediction for round t = EMA after round t-1
                _ema = 0.0
                _preds = []
                for idx, rt in enumerate(_round_times):
                    if idx == 0:
                        _preds.append("N/A")
                    else:
                        _preds.append(f"{_ema:.2f}")
                    # Update EMA after using it as prediction
                    if _ema <= 0:
                        _ema = rt
                    else:
                        _ema = _alpha * rt + (1.0 - _alpha) * _ema
                lines.append(f"| EMA Pred(s)  | " + " | ".join(_preds) + " |")
                _reals = [f"{v:.2f}" for v in _round_times]
                lines.append(f"| Real Time(s)| " + " | ".join(_reals) + " |")
                lines.append(f"")
            ema_value = getattr(self.server, 'exp_mov_avg_dur', 0.0) if hasattr(self, 'server') else 0.0
            lines.append(f"| Metric / 指标 | Value / 数值 | Description / 含义 |")
            lines.append(f"|---------------|-------------|-------------------|")
            lines.append(f"| Final EMA Duration / 最终 EMA 持续时间 | {ema_value:.2f} s | 实验结束时 EMA 估计的单轮持续时间 |")
            lines.append(f"")
        
        # 结论
        lines.append(f"## 6. Conclusion / 结论")
        lines.append(f"")
        if is_encrypted:
            lines.append(f"- **Privacy / 隐私性:** 本实验采用 **CKKS 同态加密** 实现隐私保护联邦学习，服务器始终无法访问客户端原始模型更新。")
            lines.append(f"- **Accuracy / 准确率:** 经过 **{num_rounds}** 轮训练，最终测试准确率达到 **{final_test_acc:.2f}%**，测试损失为 **{final_test_loss:.4f}**。")
            lines.append(f"- **Communication Overhead / 通信开销:** CKKS 密文引入 **{avg_expansion:.2f}x** 的通信膨胀率。")
            lines.append(f"- **Encryption Cost / 加密开销:** 平均每轮每个客户端加密耗时 **{avg_enc_time:.3f}s**。")

            if has_prefetch:
                total_broadcast = sum(m.get('prefetch_broadcast_cost', []))
                baseline_download = global_model_size_bytes * total_selected_clients
                saved = max(0, baseline_download - total_download)
                lines.append(f"- **Prefetch / 预取优化:** 启用 **CipherFetch (FedFetch-style)** 密文预取机制。")
                lines.append(f"- **Training Communication / 训练通信:** 总训练通信 **{total_comm/1024:.2f} KB**（上传 {total_upload/1024:.2f} KB + 下载 {total_download/1024:.2f} KB）。")
                lines.append(f"- **Download Saved / 节省下载:** 选中客户端避免完整模型下载，共节省 **{saved/1024:.2f} KB**.")
        else:
            lines.append(f"- **Baseline / 基线:** 本实验作为标准 FedAvg 明文基线。")
            lines.append(f"- **Accuracy / 准确率:** 经过 **{num_rounds}** 轮训练，最终测试准确率达到 **{final_test_acc:.2f}%**。")
            lines.append(f"- **Communication / 通信量:** 总通信开销为 **{total_comm:.2f} MB**。")
        lines.append(f"")
        
        report_path = os.path.join(self.output_dir, "report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        logger.info(f"Markdown报告已保存: {report_path}")


class CKKSFedPrefetchExperiment(CKKSFedExperiment):
    """
    CKKS-Fed 密文预取实验类（CipherFetch）。

    核心流程（每轮 R）：
    --------------------------------------------------------------------
    1. 选择参与者（selected_clients）
    2. 调度预取：为 future_round = R + max_prefetch_round 的客户端
       由 PrefetchScheduler 决定每个客户端从哪一轮开始预取
    3. 向【未被选中】的客户端广播本轮密文增量（Prefetch 阶段）
    4. 【被选中的客户端】训练：
       a) Fetch 剩余密文（没能预取到的部分）
       b) Apply（单次解密 prefetch + fetch 的全部密文）
       c) Compute（本地训练）
       d) Upload（上传加密更新）
    5. 服务器聚合，更新全局模型
    6. 加密本轮增量，准备下一轮广播
    7. 计算轮次耗时，推进虚拟时钟
    """

    def __init__(self, config_path: str = "configs/config.yaml",
                 bandwidth_simulator=None, output_dir: str = None):
        """
        Args:
            config_path: 配置文件路径
            bandwidth_simulator: 外部传入的 BandwidthSimulator 实例（用于对比实验共享带宽）
            output_dir: 自定义输出目录
        """
        self._external_bandwidth_simulator = bandwidth_simulator
        super().__init__(config_path, output_dir=output_dir)

    def _init_components(self):
        """初始化实验组件：带宽模拟器、预取调度器、预取客户端/服务器"""
        section("Prefetch Experiment Initialization", emoji="📦")

        self.client_loaders, self.test_loader = create_client_dataloaders(
            dataset_name=self.config['data']['dataset'],
            num_clients=self.config['system']['num_clients'],
            batch_size=self.config['system']['batch_size'],
            data_dir=self.config['data']['data_dir'],
            iid=self.config['data']['iid'],
            alpha=self.config['data']['alpha']
        )
        tree([
            ("🗂️ ", f"Dataset: {self.config['data']['dataset']}  |  "
                     f"Clients: {self.config['system']['num_clients']}  |  IID={self.config['data']['iid']}"),
        ], indent=1)

        self.global_model = create_model(self.config['model']['name'], self.config)
        dataset = self.config['data']['dataset']
        dummy_input = (1, 1, 28, 28) if dataset in ["mnist", "fashion_mnist", "emnist"] else (1, 3, 32, 32)
        print_model_summary(self.global_model, dummy_input)

        # CKKS 管理器（统一密钥）
        ckks_cfg = self.config['ckks'].copy()
        ckks_cfg['maser'] = self.config.get('maser', {})
        ckks_cfg['esafl'] = self.config.get('esafl', {})
        self.ckks_manager = CKKSManager(ckks_cfg)
        self.full_context_bytes = self.ckks_manager.context.get_full_context_bytes()
        ckks = self.config['ckks']
        tree([
            ("🔐", f"CKKS unified context  |  N={ckks.get('poly_modulus_degree')}  |  "
                   f"scale=2^{ckks.get('global_scale', 0).bit_length()-1}  |  "
                   f"serialized={fmt_size(len(self.full_context_bytes))}"),
        ], indent=1)

        # 带宽模拟器（支持外部传入，确保对比实验使用相同带宽）
        from ckks_fed.bandwidth_simulator import BandwidthSimulator
        if self._external_bandwidth_simulator is not None:
            self.bandwidth_simulator = self._external_bandwidth_simulator
            source = "loaded"
        else:
            bw_cfg = self.config.get('bandwidth', {})
            self.bandwidth_simulator = BandwidthSimulator(
                num_clients=self.config['system']['num_clients'],
                base_dl_bw=bw_cfg.get('base_dl_bw', 1024.0),
                base_ul_bw=bw_cfg.get('base_ul_bw', 512.0),
                variance=bw_cfg.get('variance', 0.3),
                distribution=bw_cfg.get('distribution', 'uniform'),
                seed=self.config['system']['random_seed'],
                filter_low_bandwidth=bw_cfg.get('filter_low_bandwidth', False),
                min_dl_bw_kbps=bw_cfg.get('min_dl_bw_kbps', 10240.0),
                min_ul_bw_kbps=bw_cfg.get('min_ul_bw_kbps', 10240.0),
                max_dl_bw_kbps=bw_cfg.get('max_dl_bw_kbps', float('inf')),
                max_ul_bw_kbps=bw_cfg.get('max_ul_bw_kbps', float('inf')),
            )
            source = "generated"
        bw_stats = self.bandwidth_simulator.get_stats()
        tree([
            ("🌐", f"Bandwidth Simulator ({source})  |  DL={fmt_bw(bw_stats.get('avg_dl_bw_kbps', 0))}  |  "
                   f"UL={fmt_bw(bw_stats.get('avg_ul_bw_kbps', 0))}  |  dist={self.config.get('bandwidth', {}).get('distribution', 'uniform')}"),
        ], indent=1)

        # 预取调度器
        from ckks_fed.prefetch_scheduler import PrefetchScheduler, CKKSSizeEvaluator
        self.size_evaluator = CKKSSizeEvaluator(self.ckks_manager, config=self.config)
        prefetch_cfg = self.config.get('prefetch', {})
        self.prefetch_scheduler = PrefetchScheduler(
            max_prefetch_round=prefetch_cfg.get('max_prefetch_round', 3),
            warmup_round=prefetch_cfg.get('warmup_round', 2),
            bandwidth_simulator=self.bandwidth_simulator,
            size_evaluator=self.size_evaluator,
            scheduler_beta=prefetch_cfg.get('scheduler_beta', 0.5),
            overcommitment=prefetch_cfg.get('overcommitment', 1.0),
        )
        tree([
            ("📅", f"Prefetch Scheduler  |  window={prefetch_cfg.get('max_prefetch_round', 3)}  |  "
                   f"warmup={prefetch_cfg.get('warmup_round', 2)}  |  "
                   f"β={prefetch_cfg.get('scheduler_beta', 0.5)}  |  "
                   f"OC={prefetch_cfg.get('overcommitment', 1.0)}"),
        ], indent=1)

        # ---- 可插拔：零和盲化掩码（KGC 初始化）----
        from ckks_fed.blinding_mask import PairwiseBlindingMask
        mask_cfg = self.config.get('blinding_mask', {})
        self.blinding_mask = PairwiseBlindingMask(mask_cfg)
        self.client_masks = None  # List[mask_dict]，按 client_id 索引
        
        if self.blinding_mask.enabled:
            # 计算模型参数总元素数（与 CKKS 打包对齐）
            shapes = {name: param.shape for name, param in self.global_model.named_parameters()}
            for name, buf in self.global_model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    shapes[name] = buf.shape
            total_elements = sum(np.prod(s) for s in shapes.values())
            
            num_clients = self.config['system']['num_clients']
            # 权重 = 各客户端 data_size（与 FedAvg 对齐）
            weights = [len(self.client_loaders[i].dataset) for i in range(num_clients)]
            batch_size = self.ckks_manager.batch_size
            
            self.client_masks = self.blinding_mask.generate_masks(
                num_clients=num_clients,
                weights=weights,
                shapes=shapes,
                total_elements=int(total_elements),
                batch_size=batch_size,
            )
            tree([
                ("🎭", f"Zero-Sum Blinding Mask  |  clients={num_clients}  |  "
                       f"range=[-{self.blinding_mask.mask_range:.0e}, {self.blinding_mask.mask_range:.0e}]  |  "
                       f"compensation={self.blinding_mask.compensation_mode}"),
            ], indent=1)
        
        # ---- 可插拔：ESAFL 适配器 ----
        from ckks_fed.esafl_crypto import ESAFLAdapter
        esafl_cfg = self.config.get('esafl', {})
        self.esafl_adapter = None
        if esafl_cfg.get('enabled', False):
            self.esafl_adapter = ESAFLAdapter(
                self.ckks_manager,
                mode=esafl_cfg.get('mode', 'SIMULATION'),
                prpg_seed=esafl_cfg.get('prpg_seed', 42),
            )
            tree([
                ("🔑", f"ESAFL Adapter  |  mode={esafl_cfg.get('mode', 'SIMULATION')}  |  prpg_seed={esafl_cfg.get('prpg_seed', 42)}"),
            ], indent=1)
        
        # 预取聚合服务器
        self.server = PrefetchAggregationServer(
            self.global_model, self.config, self.device, self.ckks_manager,
            blinding_mask=self.blinding_mask, esafl_adapter=self.esafl_adapter)
        self.server.init_encrypted_global_state(self.ckks_manager)
        self.server.bandwidth_simulator = self.bandwidth_simulator
        self.server.prefetch_scheduler = self.prefetch_scheduler
        tree([
            ("🖥️ ", "Prefetch Aggregation Server"),
        ], indent=1)

        # 预取客户端
        self.clients = []
        global_params = self.server.get_global_params()
        for i in range(self.config['system']['num_clients']):
            client_model = create_model(self.config['model']['name'], self.config)
            client_mask = self.client_masks[i] if self.client_masks else None
            client = PrefetchFederatedClient(
                client_id=i, model=client_model,
                train_loader=self.client_loaders[i],
                config=self.config, device=self.device,
                blinding_mask=self.blinding_mask,
                client_mask=client_mask,
                esafl_adapter=self.esafl_adapter,
            )
            from ckks_fed.crypto import CKKSContext
            poly_degree = self.config['ckks'].get('poly_modulus_degree', 8192)
            context = CKKSContext.from_full_bytes(self.full_context_bytes, poly_modulus_degree=poly_degree)
            ckks_cfg = self.config['ckks'].copy()
            ckks_cfg['maser'] = self.config.get('maser', {})
            ckks_cfg['esafl'] = self.config.get('esafl', {})
            client.ckks_manager = CKKSManager(ckks_cfg, context=context)
            client.dl_bandwidth_kbps = self.bandwidth_simulator.get_dl_bw_kbps(i)
            client.ul_bandwidth_kbps = self.bandwidth_simulator.get_ul_bw_kbps(i)
            # 初始化 base model：所有客户端从同一全局模型开始
            client.set_model_params(global_params)
            client.base_model_state = {k: v.cpu().clone() for k, v in global_params.items()}
            self.clients.append(client)
        tree([
            ("👤", f"Created {len(self.clients)} prefetch clients"),
        ], indent=1)
        self.client_participation = {i: 0 for i in range(len(self.clients))}
        self.client_total_ciphertexts = {i: 0 for i in range(len(self.clients))}

        # Sticky Sampling / Uniform Presampling
        prefetch_cfg = self.config.get('prefetch', {})
        sel_cfg = self.config.get('client_selection', {})
        sticky_cfg = sel_cfg.get('sticky', {})
        strategy_name = sel_cfg.get('strategy', 'sticky')
        
        # 构建带宽信息字典 {client_id: dl_bw_kbps}
        bandwidth_info = {}
        if self.bandwidth_simulator:
            for cid in range(self.config['system']['num_clients']):
                bandwidth_info[cid] = self.bandwidth_simulator.get_dl_bw_kbps(cid)
        self.bandwidth_info = bandwidth_info
        
        # 计算 FedFetch 风格的 change_num
        oc = prefetch_cfg.get('overcommitment', 1.0)
        change_num_base = sticky_cfg.get('change_num_base', 1)
        change_num = max(1, round(change_num_base * oc))
        
        from ckks_fed.sticky_sampling import StickySamplingManager
        self.sticky_manager = StickySamplingManager(
            num_clients=self.config['system']['num_clients'],
            overcommitment=oc,
            decay_factor=sticky_cfg.get('score_decay', 0.9),
            seed=self.config['system']['random_seed'],
            use_sticky=(strategy_name == 'sticky'),
            sticky_group_size=sticky_cfg.get('group_size', None),
            change_num=change_num,
            bandwidth_info=bandwidth_info,
        )
        mode_label = "STICKY" if strategy_name == 'sticky' else "UNIFORM"
        tree([
            ("🎲" if strategy_name != 'sticky' else "🍬",
             f"Presampling ({mode_label})  |  OC={oc}  |  "
             f"group_size={sticky_cfg.get('group_size', 'auto')}  |  "
             f"change_num_base={change_num_base}→change_num={change_num}  |  "
             f"score={'on' if sticky_cfg.get('enable_score', False) else 'off'}"),
        ], indent=1)

        # 可插拔客户端选择策略（优先于 sticky_manager 的默认行为）
        from ckks_fed.client_selection import create_client_selection_strategy, PrefetchPoolManager
        self.selection_strategy = create_client_selection_strategy(
            self.config, num_clients=len(self.clients),
            sticky_manager=self.sticky_manager,
            bandwidth_info=bandwidth_info,
        )

        # 通用预采样池管理器（与策略解耦，任何策略都可复用预取机制）
        self.pool_manager = PrefetchPoolManager(
            num_clients=len(self.clients),
            overcommitment=prefetch_cfg.get('overcommitment', 1.0),
        )

        self.global_virtual_clock = 0.0

    def _oc_truncate(self, pool_ids: List[int], num_needed: int, target_round: int) -> List[int]:
        """OC 截断：从候选池中按预测完成时间保留最快的 num_needed 个客户端。

        Returns:
            被保留的客户端 ID 列表（长度 <= num_needed）
        """
        if len(pool_ids) <= num_needed or not self.bandwidth_simulator:
            return pool_ids[:num_needed]

        predicted_times = []
        for cid in pool_ids:
            client = self.clients[cid]
            fetch_time = 0.0
            fetch_info = self.server.get_remaining_fetch_info(cid, target_round)
            if fetch_info:
                fetch_time = self.bandwidth_simulator.estimate_download_time(
                    cid, fetch_info['total_size'] * 8)
            compute_time = getattr(client, 'local_train_time', 5.0)
            upload_time = 0.0
            ciphertext_size_bits = getattr(client, 'ciphertext_size', 0) * 8
            if ciphertext_size_bits > 0:
                upload_time = self.bandwidth_simulator.estimate_upload_time(
                    cid, ciphertext_size_bits)
            predicted_times.append((cid, fetch_time + compute_time + upload_time))

        predicted_times.sort(key=lambda x: x[1])
        selected_ids = [cid for cid, _ in predicted_times[:num_needed]]

        dropped_ids = [cid for cid, _ in predicted_times[num_needed:]]
        if dropped_ids:
            threshold_time = predicted_times[num_needed - 1][1]
            tag_info(LogTag.STICKY,
                     f"OC截断: 池{len(pool_ids)}人→训练{num_needed}人 | "
                     f"门槛={threshold_time:.1f}s | 保留{selected_ids} | 丢弃{dropped_ids}")
        return selected_ids

    def _select_clients(self, context: str = "Current"):
        """客户端选择入口（策略无关）。

        流程：
        1. 如果有预采样池且当前轮次 >= warmup + max_prefetch，从池子中 OC 截断选择。
        2. 否则，调用当前选择策略的 select() 进行现场选择。
        3. 调用策略的 on_round_end() 更新状态（如 sticky score、sketch 签名等）。
        """
        num_clients = len(self.clients)
        rate = self.config['system'].get('client_sampling_rate', 1.0)
        num_needed = max(1, int(num_clients * rate))
        target_round = self.server.round_num if hasattr(self.server, 'round_num') else 0

        strategy = self.selection_strategy
        strategy_name = strategy.__class__.__name__

        warmup_round = getattr(self.server, 'warmup_round', 1)
        max_prefetch_round = getattr(self.server, 'max_prefetch_round', 3)

        # 场景 1：复用预采样池（warmup + R 轮之后）
        if (self.pool_manager is not None and
            target_round >= warmup_round + max_prefetch_round):
            pool_ids = self.pool_manager.get_pool(target_round)
            if pool_ids:
                selected_ids = self._oc_truncate(pool_ids, num_needed, target_round)
                dropped_ids = [cid for cid in pool_ids if cid not in selected_ids]

                # 策略回调（传入被丢弃者，供 sticky 等策略惩罚慢客户端）
                strategy.on_round_end(selected_ids, target_round, dropped_ids=dropped_ids)

                selected = [self.clients[cid] for cid in selected_ids if cid < len(self.clients)]
                bandwidth_info = getattr(self, 'bandwidth_info', None)
                log_client_selection(selected_ids, num_clients,
                                     context=f"{strategy_name}-Presampled-{context}",
                                     strategy_name=strategy_name,
                                     bandwidth_info=bandwidth_info)
                tag_info(LogTag.PREFETCH,
                         f"Reuse presampled clients for round {target_round}: {selected_ids}")
                return selected

        # 场景 2：现场选择（warmup 期间或池子为空）
        kwargs = {}
        if hasattr(self, 'client_loaders') and self.client_loaders:
            kwargs['train_weights'] = [len(self.client_loaders[i].dataset) for i in range(num_clients)]
        if hasattr(self, 'server') and self.server:
            kwargs['global_state'] = self.server.get_global_params()
            kwargs['client_states'] = {c.client_id: c.model.state_dict() for c in self.clients}

        selected_ids = strategy.select(self.clients, num_needed, round_num=target_round, **kwargs)
        selected_ids = selected_ids[:num_needed]  # 安全截断

        # 现场选择没有 OC 截断丢弃者
        strategy.on_round_end(selected_ids, target_round, dropped_ids=None)

        selected = [self.clients[cid] for cid in selected_ids if cid < len(self.clients)]
        bandwidth_info = getattr(self, 'bandwidth_info', None)
        log_client_selection(selected_ids, num_clients, context=f"{strategy_name}-{context}",
                             strategy_name=strategy_name, bandwidth_info=bandwidth_info)
        return selected

    # ==================================================================
    # 单轮预取训练
    # ==================================================================
    def _log_batch_indices(self, round_num, selected_clients, client_masks, global_mask):
        """记录每轮每个客户端的 batch 索引和聚合后的索引"""
        import json, os
        log_dir = os.path.join(self.output_dir, 'batch_indices')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f'round_{round_num}.json')
        
        data = {
            'round': round_num,
            'mode': self.config.get('global_mask_vote', {}).get('mode', 'none'),
            'clients': [],
            'global': {
                'active_indices': [],
                'active_count': 0,
            }
        }
        
        for cid, (client, mask) in enumerate(zip(selected_clients, client_masks)):
            if mask is not None:
                indices = [int(i) for i in np.where(mask == 1)[0]]
                data['clients'].append({
                    'client_id': client.client_id,
                    'selected_indices': indices,
                    'selected_count': len(indices),
                })
        
        if global_mask is not None:
            data['global']['active_indices'] = [int(i) for i in np.where(global_mask == 1)[0]]
            data['global']['active_count'] = int(global_mask.sum())
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 同时输出到日志
        tag_info(LogTag.SERVER, f"Batch indices logged: {log_path}")
    
    def run_round_prefetch(self, round_num: int) -> Dict:
        log_round_header(round_num + 1, self.config['system']['num_rounds'], mode="CipherFetch")
        round_start = time.time()
        self.server.round_num = round_num

        # 1) 选择参与者
        selected_clients = self._select_clients()
        selected_ids = [c.client_id for c in selected_clients]
        all_ids = [c.client_id for c in self.clients]
        unselected_ids = [cid for cid in all_ids if cid not in selected_ids]

        # 判断是否在 warmup 阶段
        is_warmup = round_num < self.server.warmup_round

        # 2) 调度预取（FedFetch 对齐：warmup 轮次内不预采样）
        # 使用通用 PrefetchPoolManager 替代 sticky_manager 的预采样池管理，
        # 任何客户端选择策略（random / sticky / sketch_clustering）都可复用预取机制。
        future_ids = []
        target_round = None
        if self.pool_manager and round_num >= self.server.warmup_round:
            rate = self.config['system'].get('client_sampling_rate', 1.0)
            num_needed = max(1, int(len(self.clients) * rate))
            target_round = round_num + self.server.max_prefetch_round
            section(f"🔮 预取调度：为第 {target_round + 1} 轮提前安排下载计划", emoji="")

            oc = self.config.get('prefetch', {}).get('overcommitment', 1.0)
            num_to_sample = max(num_needed, int(num_needed * oc))
            num_to_sample = min(num_to_sample, len(self.clients))

            kwargs = {}
            if hasattr(self, 'client_loaders') and self.client_loaders:
                kwargs['train_weights'] = [len(self.client_loaders[i].dataset) for i in range(len(self.clients))]
            if hasattr(self, 'server') and self.server:
                kwargs['global_state'] = self.server.get_global_params()
                kwargs['client_states'] = {c.client_id: c.model.state_dict() for c in self.clients}

            # 策略感知的预采样：让当前策略决定候选池组成
            new_future_ids = self.selection_strategy.presample_for_target(
                target_round, num_needed, clients=self.clients, **kwargs)

            # 安全补足：如果策略返回的数量不足，用均匀随机补足到 num_to_sample
            if len(new_future_ids) < num_to_sample:
                remaining = [c for c in range(len(self.clients)) if c not in new_future_ids]
                rng = np.random.RandomState(target_round + 999)
                extra_count = min(num_to_sample - len(new_future_ids), len(remaining))
                extra = rng.choice(remaining, extra_count, replace=False).tolist()
                new_future_ids = new_future_ids + extra
            new_future_ids = new_future_ids[:num_to_sample]

            # 存入 pool_manager 预采样池
            self.pool_manager.presample_pool[target_round] = new_future_ids
            tag_info(LogTag.PREFETCH,
                     f"PoolManager presample  |  target={target_round}  |  "
                     f"sampled={len(new_future_ids)} (need={num_needed}, OC={oc})  |  "
                     f"ids={new_future_ids}")

            last_update = {cid: self.server.last_update_index.get(cid, 0) for cid in all_ids}
            prefetch_schedule, min_p = self.prefetch_scheduler.schedule_prefetch(
                new_future_ids, round_num, last_update)
            self.server.prefetch_schedules[target_round] = prefetch_schedule
            self.server.min_prefetch_round[target_round] = min_p

            # 收集所有活跃预采样池中的客户端
            num_rounds = self.config['system']['num_rounds']
            future_ids = self.pool_manager.get_all_future_ids(round_num, num_rounds)

        # 3) 预取广播将在步骤 10（calculate_round_duration）之后执行，
        # 使用本轮实际的 round_duration 作为时间预算，替代 EMA 预测值。
        round_prefetch_cost = 0
        prefetch_targets = []
        
        # 4) 选中的客户端执行：Fetch → Apply → Compute → Upload
        client_updates, client_weights, train_losses, train_accs = [], [], [], []
        client_upload_sizes = []
        client_dict = {c.client_id: c for c in self.clients}

        # 收集本轮 fetch 信息用于摘要
        round_fetch_info = []
        for client in selected_clients:
            fetch_info = self.server.get_remaining_fetch_info(
                client.client_id, round_num, is_warmup=is_warmup)
            client._current_server_round = round_num
            update, loss, acc = client.local_train(
                current_round=round_num,
                fetch_info=fetch_info,
                bandwidth_simulator=self.bandwidth_simulator,
                is_warmup=is_warmup)
            client_updates.append(update)
            client_weights.append(client.get_weight())
            train_losses.append(loss)
            train_accs.append(acc)
            self.metrics.record('local_train_time', client.local_train_time)
            self.client_participation[client.client_id] += 1

            pf_stats = client.get_prefetch_stats()
            self.metrics.record('prefetch_download_cost', pf_stats['prefetch_download_cost'])
            self.metrics.record('fetch_download_cost', pf_stats['fetch_download_cost'])
            self.metrics.record('prefetch_time', pf_stats['prefetch_time'])
            self.metrics.record('prefetch_download_time', pf_stats['prefetch_download_time'])
            self.metrics.record('fetch_time', pf_stats['fetch_time'])
            self.metrics.record('apply_time', pf_stats['apply_time'])
            
            # 记录 fetch 摘要信息（reset 前）
            has_fetch = pf_stats['fetch_download_cost'] > 0
            round_fetch_info.append({
                'cid': client.client_id,
                'has_fetch': has_fetch,
                'fetch_size': pf_stats['fetch_download_cost'],
                'fetch_time': pf_stats['fetch_time'],
            })
            
            client.reset_round_stats()

        # Fetch 摘要
        fetch_clients = [r['cid'] for r in round_fetch_info if r['has_fetch']]
        no_fetch_clients = [r['cid'] for r in round_fetch_info if not r['has_fetch']]
        total_fetch_size = sum(r['fetch_size'] for r in round_fetch_info)
        if is_warmup:
            tag_info(LogTag.SERVER, f"warmup-sync: {len(no_fetch_clients)}/{len(selected_clients)}已同步")
        else:
            fetch_desc = f"需fetch={fetch_clients}" if len(fetch_clients) <= 5 else f"需fetch={len(fetch_clients)}个"
            tag_info(LogTag.SERVER, 
                     f"Fetch摘要: {len(no_fetch_clients)}/{len(selected_clients)}预取已覆盖"
                     f" | {fetch_desc}"
                     f" | 总fetch={fmt_size(total_fetch_size)}")

        # ==== 全局掩码投票（隐私安全：客户端本地算 mask，只上传 mask）====
        gmv_mode = self.config.get('global_mask_vote', {}).get('mode', 'none')
        sparsity_cfg = self.config.get('ckks', {}).get('sparsification', {})
        maser_enabled = self.config.get('maser', {}).get('enable', False)
        maser_cfg = self.config.get('maser', {})
        sparsity_enabled = sparsity_cfg.get('strategy', 'none') not in ('none', None) or maser_enabled
        
        # 1) 客户端本地计算 mask（不上传明文梯度）
        client_masks = []
        if sparsity_enabled:
            for client, update in zip(selected_clients, client_updates):
                mask = client.compute_local_mask(update, self.ckks_manager, round_num)
                client_masks.append(mask)
        
        # 2a) ESAFL 全局 batch 级 mask 投票
        global_mask = None
        if gmv_mode != 'none' and client_masks:
            packing = self.ckks_manager.packing_strategy if self.ckks_manager else None
            values_per_chunk = packing.get_values_per_chunk() if packing else 8192
            total_params = sum(p.numel() for p in self.server.model.parameters())
            num_batches = (total_params + values_per_chunk - 1) // values_per_chunk
            global_mask = self.server.run_global_mask_vote(
                client_masks=client_masks,
                num_batches=num_batches,
                round_num=round_num,
            )
            
            # 记录每轮 batch 索引详情（用于分析通信开销）
            self._log_batch_indices(round_num, selected_clients, client_masks, global_mask)
        
        # 2b) MASER 全局参数级 mask 投票
        global_maser_indices = None
        if maser_enabled and client_masks:
            # 与 client.get_model_params() 保持一致：包含可训练参数 + BN 的 running_mean/running_var
            total_params = sum(p.numel() for p in self.server.model.parameters())
            for name, buf in self.server.model.named_buffers():
                if 'running_mean' in name or 'running_var' in name:
                    total_params += buf.numel()
            maser_client_masks = [m for m in client_masks
                                  if m is not None and len(m) == total_params]
            if maser_client_masks:
                use_threshold = maser_cfg.get('use_server_threshold', True)
                voting_threshold = maser_cfg.get('voting_threshold', 0.5)
                topk_ratio = maser_cfg.get('topk_ratio', 0.5)
                global_maser_indices = self.server.run_maser_global_vote(
                    client_masks=maser_client_masks,
                    total_elements=total_params,
                    voting_threshold=voting_threshold,
                    topk_ratio=None if use_threshold else topk_ratio,
                    round_num=round_num,
                )

        # 5) 加密上传
        # warmup 轮次跳过 global_mask，让客户端上传完整梯度（对齐 skip_sparsification）
        sparsity_cfg = self.config.get('ckks', {}).get('sparsification', {})
        use_warmup = sparsity_cfg.get('use_warmup_skip_sparse', False)
        warmup_rounds = sparsity_cfg.get('warmup_rounds', 0)
        skip_sparse = use_warmup and (round_num < warmup_rounds)
        effective_global_mask = None if skip_sparse else global_mask

        maser_multi_key = (
            maser_cfg.get('enable', False) and
            maser_cfg.get('multi_key', False)
        )
        if maser_multi_key:
            raise NotImplementedError(
                "MASER multi_key 当前仅支持 CKKSFedExperiment 标准路径，"
                "暂不支持 CKKSFedPrefetchExperiment 预取路径。"
            )
        
        encrypted_updates, total_plaintext_size, total_ciphertext_size = [], 0, 0
        for client, update in zip(selected_clients, client_updates):
            encrypted = client.encrypt_update(
                update, self.ckks_manager, round_num=round_num,
                global_mask=effective_global_mask,
                global_maser_indices=global_maser_indices,
            )
            encrypted_updates.append(encrypted)
            self.metrics.record('encryption_time', client.encryption_time)
            self.metrics.record('plaintext_size', client.plaintext_size)
            self.metrics.record('ciphertext_size', client.ciphertext_size)
            self.metrics.record('num_ciphertexts', client.num_ciphertexts)
            total_plaintext_size += client.plaintext_size
            total_ciphertext_size += client.ciphertext_size
            client_upload_sizes.append(client.ciphertext_size)
            self.client_total_ciphertexts[client.client_id] += client.num_ciphertexts

        if total_plaintext_size > 0:
            expansion_ratio = total_ciphertext_size / total_plaintext_size
            self.metrics.record('expansion_ratio', expansion_ratio)
            tag_info(LogTag.ENCRYPT,
                     f"Expansion {expansion_ratio:.2f}x  |  "
                     f"plain={fmt_size(total_plaintext_size)}  |  "
                     f"cipher={fmt_size(total_ciphertext_size)}")

        # 6) 聚合
        if self.config.get('tee', {}).get('enabled', False):
            # 方案①：TEE 路径
            # 构造选中客户端的掩码列表（与 encrypted_updates 顺序对齐）
            selected_client_masks = None
            if self.client_masks is not None:
                selected_client_masks = [self.client_masks[c.client_id] for c in selected_clients]
            
            delta_enc = self.server.process_encrypted_round_via_tee(
                encrypted_updates, client_weights, client_upload_sizes,
                client_masks=selected_client_masks)
            # 同步明文模型（用于评估和后续明文操作）
            self.server._sync_model_from_encrypted_state()
            # 直接设置密文 delta 供预取广播使用（TEE 内已加密，无需额外加密）
            delta_size = self.ckks_manager.compute_encrypted_update_size(delta_enc)
            self.server.current_delta_encrypted = {
                'delta': delta_enc,
                'size': delta_size,
                'from_round': round_num,
                'encrypt_time': 0.0,
            }
            self.server.encrypted_deltas_history.append(self.server.current_delta_encrypted)
            # Prefetch 路径实际下行通信量 = 稀疏 delta 大小
            self.server.download_cost = delta_size
            self.metrics.record('prefetch_server_encrypt_time', 0.0)
            
            # ---- TEE 时间开销统计 ----
            if self.server.tee_processor is not None:
                tp = self.server.tee_processor
                self.metrics.record('tee_decrypt_time', tp.tee_decrypt_time)
                self.metrics.record('tee_aggregate_time', tp.tee_aggregate_time)
                self.metrics.record('tee_compensate_time', tp.tee_compensate_time)
                self.metrics.record('tee_compress_time', tp.tee_compress_time)
                # self.metrics.record('tee_reencrypt_time', tp.tee_reencrypt_time)  # ESAFL模拟：客户端本地解密，无服务器重加密
                self.metrics.record('tee_total_time', tp.tee_total_time)
        else:
            # 标准路径：同态聚合 + 更新全局模型
            aggregated_update = self.server.aggregate_encrypted_updates(
                encrypted_updates, client_weights,
                self.ckks_manager, client_upload_sizes)
            self.server.update_global_model(aggregated_update)

            # 8) 加密增量（用于下一轮预取广播）
            enc_info = self.server.encrypt_and_stage_prefetch(self.ckks_manager)
            if enc_info:
                self.metrics.record('prefetch_server_encrypt_time', enc_info.get('encrypt_time', 0.0))

        # 9) 评估
        criterion = nn.CrossEntropyLoss()
        test_loss, test_acc = self.server.evaluate(self.test_loader, criterion)

        # 10) 虚拟时钟
        # 注意：calculate_round_duration 必须在 record_client_sync 之前调用，
        # 使 get_remaining_fetch_info 看到训练前的状态（对齐 FedFetch 的 dl_size 计算时机）
        round_duration = self.server.calculate_round_duration(
            selected_ids, client_dict, current_round=round_num)
        self.server.advance_virtual_clock(round_duration)
        self.global_virtual_clock = self.server.global_virtual_clock
        # 模拟 wall-clock 时间（含网络传输延迟，用于与 FedFetch 对比）
        self.metrics.record('total_round_time', round_duration)
        # 真实 CPU 执行时间（单机串行执行的实际耗时）
        round_real_time = time.time() - round_start
        self.metrics.record('total_round_real_time', round_real_time)
        self.metrics.record('virtual_clock', self.global_virtual_clock)

        # record_client_sync 在 calculate_round_duration 之后，确保虚拟时钟基于训练前状态
        for client in selected_clients:
            self.server.record_client_sync(client.client_id, round_num)

        # 关键修复：选中客户端训练后也接收本轮 delta 预取，为下一轮做准备。
        # 使用 client_prefetched_batch_mask 判断客户端是否还有未收到的 batch，
        # 避免基于不准确的 client_prefetch_counts 导致重复发送或遗漏。
        if not is_warmup and self.server.current_delta_encrypted:
            delta_info = self.server.current_delta_encrypted
            for client in selected_clients:
                cid = client.client_id
                sent_mask = self.server.client_prefetched_batch_mask.get(
                    cid, [0] * len(delta_info['delta']['mask']))
                if len(sent_mask) != len(delta_info['delta']['mask']):
                    sent_mask = [0] * len(delta_info['delta']['mask'])
                # 如果还有 batch 未发送，给客户端发送本轮 delta
                remaining_mask = [1 if b == 1 and s == 0 else 0
                                  for b, s in zip(delta_info['delta']['mask'], sent_mask)]
                if sum(remaining_mask) > 0:
                    client.receive_prefetch_delta(
                        delta_info['delta'], delta_info['size'], delta_info['from_round'])
                    # 更新 sent_mask，标记本轮 delta 的所有 batch 已发送
                    new_sent_mask = [1 if s == 1 or b == 1 else 0
                                     for s, b in zip(sent_mask, delta_info['delta']['mask'])]
                    self.server.client_prefetched_batch_mask[cid] = new_sent_mask
                    round_prefetch_cost += delta_info['size']
            if round_prefetch_cost > 0:
                tag_info(LogTag.PREFETCH,
                         f"选中客户端补预取: {len(selected_clients)}人各1个Δ="
                         f"{fmt_size(delta_info['size'] * len(selected_clients))}")

        # ===== 优化：预取广播移到 calculate_round_duration 之后 =====
        # 使用本轮实际的 round_duration 作为时间预算，替代 EMA 预测值
        if not is_warmup:
            prefetch_targets = [cid for cid in unselected_ids
                                if not future_ids or cid in future_ids]
            # 传入实际 round_duration 替代 EMA
            round_prefetch_cost += self.server.broadcast_prefetch_to_unselected(
                unselected_ids, {c.client_id: c for c in self.clients},
                target_pool_ids=future_ids if future_ids else None,
                time_budget=round_duration)
            # Sticky 特有的预取加分（仅 sticky 策略需要）
            sel_cfg = self.config.get('client_selection', {})
            if sel_cfg.get('strategy', 'sticky') == 'sticky' and self.sticky_manager and prefetch_targets:
                self.sticky_manager.update_on_prefetch(prefetch_targets)

        # 清理过期池子
        if self.pool_manager:
            self.pool_manager.cleanup(round_num, self.config['system']['num_rounds'])
        if self.sticky_manager:
            self.sticky_manager.cleanup(round_num, self.config['system']['num_rounds'])

        # 预取模式通信统计（对齐 FedFetch 论文定义）：
        #   TV (Training Volume) = upload + FV (Fetch Volume)
        #   FV = 选中客户端实际 fetch 下载量（已扣除 prefetch 覆盖部分）
        #   PV (Prefetch Volume) = 后台预取量（不计入 TV）
        # 
        # 注：effective_download = delta_size * len(selected) 是"理论下载责任"，
        # 仅用于计算预取节省率，不用于 TV/FV。
        actual_fetch = total_fetch_size
        actual_prefetch = round_prefetch_cost

        # 训练通信 TV = upload + actual fetch download（FedFetch 论文定义）
        self.server.download_cost = actual_fetch
        self.server.communication_cost = self.server.upload_cost + actual_fetch

        # 理论下载责任（用于预取效率分析）
        delta_size = self.server.current_delta_encrypted['size'] if self.server.current_delta_encrypted else 0
        effective_download = delta_size * len(selected_clients)

        tag_info(LogTag.AGG,
                 f"通信汇总: ↑{fmt_size(self.server.upload_cost)}"
                 f" | FV(fetch↓)={fmt_size(actual_fetch)}"
                 f" | effective↓={fmt_size(effective_download)}(每客户端1个Δ)"
                 f" | PV(prefetch↓)={fmt_size(actual_prefetch)}"
                 f" | TV={fmt_size(self.server.communication_cost)}")

        # 计算本轮上传/下载 wall-clock 时间（最慢客户端）
        round_upload_time = 0.0
        for client in selected_clients:
            ciphertext_size_bits = client.ciphertext_size * 8
            if self.bandwidth_simulator is not None:
                client_ul = self.bandwidth_simulator.estimate_upload_time(client.client_id, ciphertext_size_bits)
            else:
                ul_bw_bits = 512 * 1000
                client_ul = ciphertext_size_bits / ul_bw_bits if ul_bw_bits > 0 else 0.0
            round_upload_time = max(round_upload_time, client_ul)
        round_download_time = max((r['fetch_time'] for r in round_fetch_info), default=0.0)

        self.metrics.record('train_loss', np.mean(train_losses))
        self.metrics.record('train_acc', np.mean(train_accs))
        self.metrics.record('test_loss', test_loss)
        self.metrics.record('test_acc', test_acc)
        self.metrics.record('aggregation_time', self.server.aggregation_time)
        self.metrics.record('upload_cost', self.server.upload_cost)
        self.metrics.record('download_cost', self.server.download_cost)
        self.metrics.record('prefetch_broadcast_cost', actual_prefetch)
        self.metrics.record('total_communication_cost', self.server.communication_cost)
        self.metrics.record('upload_time', round_upload_time)
        self.metrics.record('download_time', round_download_time)
        self.metrics.record('communication_rounds', 1)
        self.metrics.record('cpu_utilization', psutil.cpu_percent())
        self.metrics.record('memory_usage', psutil.virtual_memory().percent)

        tag_info(LogTag.ROUND,
                 f"#{round_num + 1} done  |  acc={test_acc:.2f}%  |  "
                 f"sim_dur={round_duration:.2f}s  |  "
                 f"vclock={fmt_time(self.global_virtual_clock)}  |  "
                 f"comm={fmt_size(self.server.communication_cost)} "
                 f"(↑{fmt_size(self.server.upload_cost)} ↓{fmt_size(self.server.download_cost)})")

        # 轮次结束：打印所有客户端状态
        log_round_client_status(
            round_num, self.clients, selected_ids, future_ids,
            self.sticky_manager, self.server, phase="结束",
            is_warmup=is_warmup)

        return {
            'round': round_num + 1,
            'test_acc': test_acc,
            'test_loss': test_loss,
            'round_time': round_duration,
            'round_real_time': round_real_time,
            'virtual_clock': self.global_virtual_clock,
        }

    # ==================================================================
    # 完整实验
    # ==================================================================
    def run_experiment_prefetch(self):
        upload_mode = "Δ" if self.config['system'].get('upload_difference', True) else "Full"
        blank_line()
        banner("CipherFetch 密文预取实验启动", width=72)
        kv("总轮数", self.config['system']['num_rounds'], indent=1)
        kv("上传模式", "差值(Δ)" if self.config['system'].get('upload_difference', True) else "完整权重(Full)", indent=1)
        separator(width=72)

        num_rounds = self.config['system']['num_rounds']
        results = []

        key_dist_time = 0.0
        self.metrics.record('key_distribution_time', key_dist_time)
        num_clients = self.config['system']['num_clients']
        key_size_per_client = len(self.full_context_bytes)
        self.metrics.record('key_distribution_cost', key_size_per_client * num_clients)
        tag_info(LogTag.INIT, f"统一 CKKS 密钥已分发给 {num_clients} 个客户端（含私钥，用于本地解密）")

        try:
            for round_num in range(num_rounds):
                result = self.run_round_prefetch(round_num)
                results.append(result)
                if (round_num + 1) % self.config['output']['save_interval'] == 0:
                    self._save_model(round_num + 1)
        except KeyboardInterrupt:
            tag_warn(LogTag.SUMMARY, "实验被用户中断 (Ctrl+C)")
        except Exception as e:
            tag_warn(LogTag.SUMMARY, f"实验异常中断: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 无论是否完成，都保存已产生的中间结果
            self._save_results()
            if results:
                self._save_model(len(results))
            tag_info(LogTag.SUMMARY, f"实验结果已保存至: {self.output_dir}")

        # 终端统计打印
        blank_line()
        banner("客户端参与统计与带宽/下载量", width=72)
        headers = ["Client", "Part", "CTs", "DL BW", "UL BW", "Prefetch ↓", "Fetch ↓", "Total ↓"]
        rows = []
        for cid in sorted(self.client_participation.keys()):
            ct_count = self.client_total_ciphertexts.get(cid, 0)
            pf = self.clients[cid].get_prefetch_stats()
            rows.append([
                cid,
                self.client_participation[cid],
                ct_count,
                fmt_bw(pf.get('dl_bw_kbps', 0)),
                fmt_bw(pf.get('ul_bw_kbps', 0)),
                fmt_size(pf['total_prefetch_download_cost']),
                fmt_size(pf['total_fetch_download_cost']),
                fmt_size(pf['total_download_cost_cumulative']),
            ])
        table(headers, rows, col_widths=[8, 6, 6, 10, 10, 14, 12, 12])

        # EMA Round Duration 表格
        _m = self.metrics.get_metrics()
        _round_times = _m.get('total_round_time', [])
        if _round_times:
            blank_line()
            banner("EMA Round Duration / EMA 轮次持续时间", width=72)
            _alpha = 0.125
            if hasattr(self, 'server') and hasattr(self.server, 'prefetch_scheduler'):
                _alpha = getattr(self.server.prefetch_scheduler, 'avg_alpha', 0.125)
            _ema = 0.0
            _preds = []
            for idx, rt in enumerate(_round_times):
                if idx == 0:
                    _preds.append("N/A")
                else:
                    _preds.append(f"{_ema:.1f}")
                if _ema <= 0:
                    _ema = rt
                else:
                    _ema = _alpha * rt + (1.0 - _alpha) * _ema
            _reals = [f"{v:.1f}" for v in _round_times]
            # Build wide table with round numbers as columns
            ema_headers = ["Type"] + [str(i+1) for i in range(len(_round_times))]
            ema_rows = [
                ["EMA(s)"] + _preds,
                ["Real(s)"] + _reals,
            ]
            # Auto column widths
            table(ema_headers, ema_rows)
            ema_final = getattr(self.server, 'exp_mov_avg_dur', 0.0) if hasattr(self, 'server') else 0.0
            logging.info(f"Final EMA = {ema_final:.2f} s")

        blank_line()
        section("虚拟时钟说明", emoji="")
        tree([
            "round_duration = 最慢选中客户端的 (补下载时间 + 训练时间 + 上传时间)",
            "virtual_clock  = 所有轮次 round_duration 的累加（模拟真实 wall-clock 训练时间）",
        ], indent=1)
        blank_line()
        banner("实验结束", width=72)

        return {'results': results, 'metrics': self.metrics.get_metrics()}


def _get_or_create_bandwidth_simulator(config: Dict) -> "BandwidthSimulator":
    """
    统一带宽配置管理：确保对比实验使用完全相同的客户端带宽。
    
    策略：
    1. 如果配置中启用了 FedFetch 真实带宽，优先从 FedFetch trace 加载
    2. 否则按客户端数量 + 关键带宽参数区分配置文件
    3. 支持动态客户端数量：切换 num_clients 时会自动创建/加载对应的配置。
    """
    from ckks_fed.bandwidth_simulator import BandwidthSimulator
    
    num_clients = config['system']['num_clients']
    bw_cfg = config.get('bandwidth', {})
    
    # 优先使用 FedFetch 真实带宽 trace
    fedfetch_path = bw_cfg.get('fedfetch_trace_path')
    if fedfetch_path and os.path.exists(fedfetch_path):
        bw_sim = BandwidthSimulator(
            num_clients=num_clients,
            seed=config['system']['random_seed'],
            fedfetch_trace_path=fedfetch_path,
            filter_low_bandwidth=bw_cfg.get('filter_low_bandwidth', False),
            min_dl_bw_kbps=bw_cfg.get('min_dl_bw_kbps', 10240.0),
            min_ul_bw_kbps=bw_cfg.get('min_ul_bw_kbps', 10240.0),
            max_dl_bw_kbps=bw_cfg.get('max_dl_bw_kbps', float('inf')),
            max_ul_bw_kbps=bw_cfg.get('max_ul_bw_kbps', float('inf')),
        )
        tag_info(LogTag.INIT, f"加载 FedFetch 真实带宽: {fedfetch_path} ({num_clients} clients)")
        return bw_sim
    
    base_dl = bw_cfg.get('base_dl_bw', 1024.0)
    base_ul = bw_cfg.get('base_ul_bw', 512.0)
    var = bw_cfg.get('variance', 0.3)
    dist = bw_cfg.get('distribution', 'uniform')
    
    # 将关键参数纳入文件名，避免修改参数后仍加载旧配置
    bw_config_path = (
        f"configs/bandwidth_config_{num_clients}_"
        f"{base_dl:g}_{base_ul:g}_{var}_{dist}.json"
    )
    
    if os.path.exists(bw_config_path):
        try:
            bw_sim = BandwidthSimulator.load(bw_config_path, expected_num_clients=num_clients)
            tag_info(LogTag.INIT, f"加载共享带宽配置: {bw_config_path} ({num_clients} clients)")
            return bw_sim
        except ValueError as e:
            tag_warn(LogTag.INIT, f"带宽配置不匹配，将重新生成: {e}")
            # 继续执行生成逻辑
    
    bw_sim = BandwidthSimulator(
        num_clients=num_clients,
        base_dl_bw=base_dl,
        base_ul_bw=base_ul,
        variance=var,
        distribution=dist,
        seed=config['system']['random_seed'],
        filter_low_bandwidth=bw_cfg.get('filter_low_bandwidth', False),
        min_dl_bw_kbps=bw_cfg.get('min_dl_bw_kbps', 10240.0),
        min_ul_bw_kbps=bw_cfg.get('min_ul_bw_kbps', 10240.0),
        max_dl_bw_kbps=bw_cfg.get('max_dl_bw_kbps', float('inf')),
        max_ul_bw_kbps=bw_cfg.get('max_ul_bw_kbps', float('inf')),
    )
    bw_sim.save(bw_config_path)
    tag_info(LogTag.INIT, f"生成并保存共享带宽配置: {bw_config_path} ({num_clients} clients)")
    return bw_sim


def _get_device_info() -> str:
    """检测并返回GPU/设备信息字符串"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return f"CUDA available: True | Device: {gpu_name} | Memory: {gpu_mem:.1f} GB"
    else:
        return "CUDA available: False | Device: CPU"


def main():
    """主函数：支持标准加密实验和密文预取实验"""
    parser = argparse.ArgumentParser(description="CKKS-Fed 联邦学习实验")
    parser.add_argument(
        "--config", type=str, default="configs/config.yaml",
        help="配置文件路径 (默认: configs/config.yaml)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="自定义实验输出目录 (默认: 使用配置文件中的 results_dir)"
    )
    args = parser.parse_args()

    blank_line()
    banner("CKKS-Fed: 基于CKKS同态加密的联邦学习框架", width=72)
    tag_info(LogTag.INIT, _get_device_info())

    with open(args.config, "r", encoding="utf-8") as f:
        main_config = yaml.safe_load(f)
    
    # 自动推断 num_classes
    dataset_name = main_config.get('data', {}).get('dataset', 'cifar10')
    inferred_classes = get_dataset_num_classes(dataset_name)
    config_classes = main_config.get('data', {}).get('num_classes', inferred_classes)
    if config_classes != inferred_classes:
        logger.warning(
            f"[AutoFix] 配置中 num_classes={config_classes} 与数据集 '{dataset_name}' "
            f"不匹配，自动修正为 {inferred_classes}"
        )
        main_config['data']['num_classes'] = inferred_classes

    run_prefetch = main_config.get("prefetch", {}).get("enable_prefetch", False)
    
    # 统一生成/加载带宽配置，确保对比实验使用完全相同的带宽
    shared_bandwidth_simulator = _get_or_create_bandwidth_simulator(main_config)

    if run_prefetch:
        blank_line()
        section("🚀 启动 CipherFetch 密文预取实验（FedFetch 风格）", emoji="")
        experiment_prefetch = CKKSFedPrefetchExperiment(
            args.config,
            bandwidth_simulator=shared_bandwidth_simulator,
            output_dir=args.output_dir)
        results_prefetch = experiment_prefetch.run_experiment_prefetch()

        pf_metrics = results_prefetch['metrics']
        pf_results = results_prefetch.get('results', [])
        final_acc = pf_results[-1]['test_acc'] if pf_results else 0.0
        exp_ratio = np.mean(pf_metrics['expansion_ratio']) if pf_metrics.get('expansion_ratio') else None
        log_experiment_summary(
            final_acc=final_acc,
            total_time=sum(pf_metrics.get('total_round_time', [])),
            total_comm=sum(pf_metrics.get('total_communication_cost', [])),
            expansion_ratio=exp_ratio,
        )
        tag_info(LogTag.SUMMARY, f"实验结果已保存至: {experiment_prefetch.output_dir}")
        return

    blank_line()
    section("🚀 启动标准 CKKS-Fed 加密实验", emoji="")
    experiment_enc = CKKSFedExperiment(
        args.config,
        bandwidth_simulator=shared_bandwidth_simulator,
        output_dir=args.output_dir)
    results_enc = experiment_enc.run_experiment(use_encryption=True)

    blank_line()
    banner("所有实验已完成", width=72)

    enc_results = results_enc.get('results', [])
    enc_acc = enc_results[-1]['test_acc'] if enc_results else 0.0
    enc_metrics = results_enc['metrics']
    kv("最终测试准确率", fmt_pct(enc_acc), indent=1)
    kv("结果目录", experiment_enc.output_dir, indent=1)

    if enc_metrics.get('expansion_ratio'):
        blank_line()
        section("🔐 CKKS 加密指标汇总", emoji="")
        kv("密文膨胀率", f"{safe_mean(enc_metrics.get('expansion_ratio', [])):.2f}x", indent=1)
        kv("平均加密时间", f"{safe_mean(enc_metrics.get('encryption_time', [])):.3f} s/客户端", indent=1)
        # 解密时间已废弃（服务器本地解密，不单独计时）


if __name__ == '__main__':
    main()
