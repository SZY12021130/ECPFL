"""
Visualization module for CKKS-Fed experiments.
Supports both overview multi-subplots and separated single-figure plots for IEEE papers.
Requires: scienceplots (pip install SciencePlots)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict

import numpy as np
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401

# Use IEEE style without requiring a local LaTeX installation
plt.style.use(['science', 'ieee', 'no-latex'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultVisualizer:
    """Visualizer for CKKS-Fed experimental results."""

    def __init__(self, output_dir: str = None):
        """
        Args:
            output_dir: 可视化输出根目录。默认自动定位到项目根目录下的 visualization/ 文件夹。
        """
        if output_dir is None:
            # 自动定位项目根目录：ckks_fed/ckks_fed/plotting.py -> ckks_fed/
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(pkg_dir)
            output_dir = os.path.join(project_root, "visualization")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, f"viz_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)
        self.single_dir = os.path.join(self.output_dir, "single")
        os.makedirs(self.single_dir, exist_ok=True)
        logger.info(f"Visualization output directory: {self.output_dir}")

        self.colors = {
            'ckks_fed': '#0173B2',
            'plain': '#DE8F05',
            'train': '#029E73',
            'test': '#D55E00',
            'primary': '#000000',
            'secondary': '#CC78BC',
            'tertiary': '#CA9161'
        }

    @staticmethod
    def _save_both(save_path: str):
        """Save current figure as both PDF and PNG."""
        plt.savefig(save_path, bbox_inches='tight')
        png_path = os.path.splitext(save_path)[0] + '.png'
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {save_path} + {png_path}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def load_metrics(metrics_path: str) -> Dict:
        with open(metrics_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _get_rounds(metrics_list):
        return np.arange(1, len(metrics_list) + 1)

    # ------------------------------------------------------------------
    # Single-figure plots (recommended for IEEE papers)
    # ------------------------------------------------------------------
    def plot_accuracy_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                             save_path: str = None):
        """Single figure: Test Accuracy vs. Rounds."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        rounds = self._get_rounds(enc_metrics['test_acc'])
        ax.plot(rounds, enc_metrics['test_acc'], marker='o',
                label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['test_acc'], marker='s',
                    label='FedAvg', color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Test Accuracy (%)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "accuracy_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_loss_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                         save_path: str = None):
        """Single figure: Test Loss vs. Rounds."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        rounds = self._get_rounds(enc_metrics['test_loss'])
        ax.plot(rounds, enc_metrics['test_loss'], marker='o',
                label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['test_loss'], marker='s',
                    label='FedAvg', color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Test Loss')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "loss_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_communication_total_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                                        save_path: str = None):
        """Single figure: Total communication cost per round."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        rounds = self._get_rounds(enc_metrics['total_communication_cost'])
        enc_mb = np.array(enc_metrics['total_communication_cost']) / (1024 * 1024)
        ax.plot(rounds, enc_mb, marker='o', label='CKKS-Fed',
                color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            plain_mb = np.array(plain_metrics['total_communication_cost']) / (1024 * 1024)
            ax.plot(rounds, plain_mb, marker='s', label='FedAvg',
                    color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Total Comm. Cost (MB)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "communication_total_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_communication_upload_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                                         save_path: str = None):
        """Single figure: Client upload cost per round."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        rounds = self._get_rounds(enc_metrics['upload_cost'])
        enc_mb = np.array(enc_metrics['upload_cost']) / (1024 * 1024)
        ax.plot(rounds, enc_mb, marker='o', label='CKKS-Fed Upload',
                color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            plain_mb = np.array(plain_metrics['upload_cost']) / (1024 * 1024)
            ax.plot(rounds, plain_mb, marker='s', label='FedAvg Upload',
                    color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Upload Cost (MB)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "communication_upload_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_expansion_ratio_single(self, enc_metrics: Dict, save_path: str = None):
        """Single figure: Ciphertext expansion ratio."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        rounds = self._get_rounds(enc_metrics['expansion_ratio'])
        ax.plot(rounds, enc_metrics['expansion_ratio'], marker='d',
                color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.8, label='Plaintext baseline')
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Expansion Ratio ($\\times$)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "expansion_ratio_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_ciphertext_vs_plaintext_single(self, enc_metrics: Dict, save_path: str = None):
        """Single figure: Ciphertext vs. plaintext size per round."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        num_rounds = len(enc_metrics.get('ciphertext_size', []))
        rounds = self._get_rounds(enc_metrics['ciphertext_size'])
        num_clients = max(1, len(enc_metrics['ciphertext_size']) // num_rounds)
        ct_per_round = [sum(enc_metrics['ciphertext_size'][i * num_clients:(i + 1) * num_clients]) / (1024 * 1024)
                        for i in range(num_rounds)]
        pt_per_round = [sum(enc_metrics['plaintext_size'][i * num_clients:(i + 1) * num_clients]) / (1024 * 1024)
                        for i in range(num_rounds)]
        ax.plot(rounds, ct_per_round, marker='o', label='Ciphertext',
                color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        ax.plot(rounds, pt_per_round, marker='s', label='Plaintext',
                color=self.colors['secondary'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Upload Size (MB)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "ciphertext_vs_plaintext_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_time_breakdown_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                                   save_path: str = None):
        """Single figure: Computation time breakdown per round."""
        fig, ax = plt.subplots(figsize=(3.5, 2.5))
        num_rounds = len(enc_metrics.get('total_round_time', []))
        rounds = self._get_rounds(enc_metrics['total_round_time'])
        num_clients = max(1, len(enc_metrics.get('encryption_time', [])) // num_rounds)

        enc_per_round = [sum(enc_metrics['encryption_time'][i * num_clients:(i + 1) * num_clients])
                         for i in range(num_rounds)] if enc_metrics.get('encryption_time') else [0] * num_rounds
        dec_per_round = enc_metrics['decryption_time'][:num_rounds] if enc_metrics.get('decryption_time') else [0] * num_rounds
        agg_per_round = enc_metrics['aggregation_time'][:num_rounds] if enc_metrics.get('aggregation_time') else [0] * num_rounds

        width = 0.35
        x = np.arange(1, num_rounds + 1)
        if plain_metrics and plain_metrics.get('local_train_time'):
            lt_plain = [sum(plain_metrics['local_train_time'][i * num_clients:(i + 1) * num_clients])
                        for i in range(num_rounds)]
            ax.bar(x - width / 2, enc_per_round, width, label='Encryption', color=self.colors['ckks_fed'])
            ax.bar(x - width / 2, dec_per_round, width, bottom=enc_per_round, label='Decryption', color=self.colors['secondary'])
            ax.bar(x - width / 2, agg_per_round, width,
                   bottom=np.array(enc_per_round) + np.array(dec_per_round), label='Aggregation', color=self.colors['tertiary'])
            ax.bar(x + width / 2, lt_plain, width, label='Local Training (FedAvg)', color=self.colors['plain'])
        else:
            ax.bar(x - width / 2, enc_per_round, width, label='Encryption', color=self.colors['ckks_fed'])
            ax.bar(x - width / 2, dec_per_round, width, bottom=enc_per_round, label='Decryption', color=self.colors['secondary'])
            ax.bar(x - width / 2, agg_per_round, width,
                   bottom=np.array(enc_per_round) + np.array(dec_per_round), label='Aggregation', color=self.colors['tertiary'])
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Time (s)')
        ax.set_xticks(x)
        ax.legend(frameon=True, fontsize=7)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "time_breakdown_single.pdf")
        self._save_both(sp)
        plt.close()

    def plot_cpu_memory_single(self, enc_metrics: Dict, plain_metrics: Dict = None,
                               save_path: str = None):
        """Single figure with 2 subplots: CPU and Memory usage."""
        fig, axes = plt.subplots(1, 2, figsize=(7, 2.5))
        rounds = self._get_rounds(enc_metrics['cpu_utilization'])

        # CPU
        ax = axes[0]
        ax.plot(rounds, enc_metrics['cpu_utilization'], marker='o',
                label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['cpu_utilization'], marker='s',
                    label='FedAvg', color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('CPU Utilization (%)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)

        # Memory
        ax = axes[1]
        ax.plot(rounds, enc_metrics['memory_usage'], marker='o',
                label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2, markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['memory_usage'], marker='s',
                    label='FedAvg', color=self.colors['plain'], linewidth=1.2, markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Memory Usage (%)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        sp = save_path or os.path.join(self.single_dir, "cpu_memory_single.pdf")
        self._save_both(sp)
        plt.close()

    # ------------------------------------------------------------------
    # Overview multi-subplot plots (for quick report)
    # ------------------------------------------------------------------
    def plot_accuracy_comparison(self, enc_metrics: Dict, plain_metrics: Dict = None,
                                  save_path: str = None):
        fig, ax = plt.subplots(figsize=(5, 3))
        rounds = self._get_rounds(enc_metrics['test_acc'])
        ax.plot(rounds, enc_metrics['test_acc'], label='CKKS-Fed',
                color=self.colors['ckks_fed'], linewidth=1.5, marker='o', markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['test_acc'], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.5, marker='s', markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Test Accuracy (%)')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "accuracy_comparison.pdf")
        self._save_both(sp)
        plt.close()

    def plot_loss_comparison(self, enc_metrics: Dict, plain_metrics: Dict = None,
                            save_path: str = None):
        fig, ax = plt.subplots(figsize=(5, 3))
        rounds = self._get_rounds(enc_metrics['test_loss'])
        ax.plot(rounds, enc_metrics['test_loss'], label='CKKS-Fed',
                color=self.colors['ckks_fed'], linewidth=1.5, marker='o', markersize=3)
        if plain_metrics:
            ax.plot(rounds, plain_metrics['test_loss'], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.5, marker='s', markersize=3)
        ax.set_xlabel('Communication Round')
        ax.set_ylabel('Test Loss')
        ax.legend(frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "loss_comparison.pdf")
        self._save_both(sp)
        plt.close()

    def plot_computation_time(self, enc_metrics: Dict, plain_metrics: Dict = None,
                             save_path: str = None):
        fig, axes = plt.subplots(2, 2, figsize=(7, 5))
        num_rounds = len(enc_metrics.get('total_round_time', []))
        rounds = self._get_rounds(enc_metrics['total_round_time'])
        num_clients = max(1, len(enc_metrics.get('local_train_time', [])) // num_rounds)

        if enc_metrics.get('total_round_time') and plain_metrics and plain_metrics.get('total_round_time'):
            ax = axes[0, 0]
            ax.plot(rounds, enc_metrics['total_round_time'], label='CKKS-Fed',
                    color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_metrics['total_round_time'], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Time (s)')
            ax.set_title('Total Round Time')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        if enc_metrics.get('local_train_time') and plain_metrics and plain_metrics.get('local_train_time'):
            ax = axes[0, 1]
            enc_lt = [sum(enc_metrics['local_train_time'][i * num_clients:(i + 1) * num_clients])
                      for i in range(num_rounds)]
            plain_lt = [sum(plain_metrics['local_train_time'][i * num_clients:(i + 1) * num_clients])
                        for i in range(num_rounds)]
            ax.plot(rounds, enc_lt, label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_lt, label='FedAvg', color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Time (s)')
            ax.set_title('Local Training Time')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        if enc_metrics.get('encryption_time'):
            ax = axes[1, 0]
            enc_et = [sum(enc_metrics['encryption_time'][i * num_clients:(i + 1) * num_clients])
                      for i in range(num_rounds)]
            ax.plot(rounds, enc_et, color=self.colors['ckks_fed'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Time (s)')
            ax.set_title('CKKS Encryption Time')
            ax.grid(True, alpha=0.3)

        if enc_metrics.get('aggregation_time') and plain_metrics and plain_metrics.get('aggregation_time'):
            ax = axes[1, 1]
            ax.plot(rounds, enc_metrics['aggregation_time'][:num_rounds], label='CKKS-Fed',
                    color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_metrics['aggregation_time'][:num_rounds], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Time (s)')
            ax.set_title('Aggregation Time')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "computation_time.pdf")
        self._save_both(sp)
        plt.close()

    def plot_communication_cost(self, enc_metrics: Dict, plain_metrics: Dict = None,
                               save_path: str = None):
        fig, axes = plt.subplots(2, 2, figsize=(7, 5))
        num_rounds = len(enc_metrics.get('total_communication_cost', []))
        rounds = self._get_rounds(enc_metrics['total_communication_cost'])

        ax = axes[0, 0]
        if enc_metrics.get('total_communication_cost') and plain_metrics and plain_metrics.get('total_communication_cost'):
            enc_mb = np.array(enc_metrics['total_communication_cost']) / (1024 * 1024)
            plain_mb = np.array(plain_metrics['total_communication_cost']) / (1024 * 1024)
            ax.plot(rounds, enc_mb, label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_mb, label='FedAvg', color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Cost (MB)')
            ax.set_title('Per-Round Total Communication Cost')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        if enc_metrics.get('total_communication_cost') and plain_metrics and plain_metrics.get('total_communication_cost'):
            enc_cum = np.cumsum(enc_mb)
            plain_cum = np.cumsum(plain_mb)
            ax.plot(rounds, enc_cum, label='CKKS-Fed', color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_cum, label='FedAvg', color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Cost (MB)')
            ax.set_title('Cumulative Communication Cost')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[1, 0]
        if enc_metrics.get('upload_cost') and plain_metrics and plain_metrics.get('upload_cost'):
            ax.plot(rounds, np.array(enc_metrics['upload_cost']) / (1024 * 1024),
                    label='CKKS-Fed Upload', color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, np.array(plain_metrics['upload_cost']) / (1024 * 1024),
                    label='FedAvg Upload', color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Cost (MB)')
            ax.set_title('Client Upload Cost')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[1, 1]
        if enc_metrics.get('download_cost') and plain_metrics and plain_metrics.get('download_cost'):
            ax.plot(rounds, np.array(enc_metrics['download_cost']) / (1024 * 1024),
                    label='CKKS-Fed Download', color=self.colors['ckks_fed'], linewidth=1.2, marker='o', markersize=3)
            ax.plot(rounds, np.array(plain_metrics['download_cost']) / (1024 * 1024),
                    label='FedAvg Download', color=self.colors['plain'], linewidth=1.2, marker='s', markersize=3)
            ax.set_xlabel('Round')
            ax.set_ylabel('Cost (MB)')
            ax.set_title('Server Download Cost')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "communication_cost.pdf")
        self._save_both(sp)
        plt.close()

    def plot_system_metrics(self, enc_metrics: Dict, plain_metrics: Dict = None,
                           save_path: str = None):
        fig, axes = plt.subplots(1, 2, figsize=(7, 2.8))
        rounds = self._get_rounds(enc_metrics['cpu_utilization'])

        ax = axes[0]
        if enc_metrics.get('cpu_utilization') and plain_metrics and plain_metrics.get('cpu_utilization'):
            ax.plot(rounds, enc_metrics['cpu_utilization'], label='CKKS-Fed',
                    color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_metrics['cpu_utilization'], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('CPU Utilization (%)')
            ax.set_title('CPU Utilization')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[1]
        if enc_metrics.get('memory_usage') and plain_metrics and plain_metrics.get('memory_usage'):
            ax.plot(rounds, enc_metrics['memory_usage'], label='CKKS-Fed',
                    color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, plain_metrics['memory_usage'], label='FedAvg',
                    color=self.colors['plain'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Memory Usage (%)')
            ax.set_title('Memory Usage')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "system_metrics.pdf")
        self._save_both(sp)
        plt.close()

    def plot_encryption_metrics(self, enc_metrics: Dict, save_path: str = None):
        fig, axes = plt.subplots(2, 2, figsize=(7, 5))
        num_rounds = len(enc_metrics.get('expansion_ratio', [])) or len(enc_metrics.get('decryption_time', [])) or 1
        rounds = self._get_rounds(enc_metrics.get('expansion_ratio', [0] * num_rounds))

        ax = axes[0, 0]
        if enc_metrics.get('ciphertext_size') and enc_metrics.get('plaintext_size'):
            num_clients = max(1, len(enc_metrics['ciphertext_size']) // num_rounds)
            ct_per_round = [sum(enc_metrics['ciphertext_size'][i * num_clients:(i + 1) * num_clients]) / (1024 * 1024)
                            for i in range(num_rounds)]
            pt_per_round = [sum(enc_metrics['plaintext_size'][i * num_clients:(i + 1) * num_clients]) / (1024 * 1024)
                            for i in range(num_rounds)]
            ax.plot(rounds, ct_per_round, label='Ciphertext', color=self.colors['ckks_fed'], linewidth=1.2, marker='o', markersize=3)
            ax.plot(rounds, pt_per_round, label='Plaintext', color=self.colors['secondary'], linewidth=1.2, marker='s', markersize=3)
            ax.set_xlabel('Round')
            ax.set_ylabel('Size (MB)')
            ax.set_title('Ciphertext vs. Plaintext Size')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[0, 1]
        if enc_metrics.get('expansion_ratio'):
            ax.plot(rounds, enc_metrics['expansion_ratio'], color=self.colors['ckks_fed'], linewidth=1.2, marker='d', markersize=3)
            ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.8, label='Plaintext baseline')
            ax.set_xlabel('Round')
            ax.set_ylabel('Expansion Ratio ($\\times$)')
            ax.set_title('CKKS Expansion Ratio')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[1, 0]
        if enc_metrics.get('encryption_time') and enc_metrics.get('decryption_time') and enc_metrics.get('aggregation_time'):
            num_clients = max(1, len(enc_metrics['encryption_time']) // num_rounds)
            enc_per_round = [sum(enc_metrics['encryption_time'][i * num_clients:(i + 1) * num_clients])
                             for i in range(num_rounds)]
            dec_per_round = enc_metrics['decryption_time'][:num_rounds]
            agg_per_round = enc_metrics['aggregation_time'][:num_rounds]
            ax.plot(rounds, enc_per_round, label='Encryption', color=self.colors['ckks_fed'], linewidth=1.2)
            ax.plot(rounds, dec_per_round, label='Decryption', color=self.colors['secondary'], linewidth=1.2)
            ax.plot(rounds, agg_per_round, label='Aggregation', color=self.colors['train'], linewidth=1.2)
            ax.set_xlabel('Round')
            ax.set_ylabel('Time (s)')
            ax.set_title('CKKS Computation Breakdown')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        ax = axes[1, 1]
        if enc_metrics.get('noise_budget'):
            nb_rounds = self._get_rounds(enc_metrics['noise_budget'])
            ax.plot(nb_rounds, enc_metrics['noise_budget'], color=self.colors['ckks_fed'], linewidth=1.2, marker='o', markersize=3)
            ax.axhline(y=20, color='r', linestyle='--', linewidth=0.8, label='Critical threshold')
            ax.set_xlabel('Round')
            ax.set_ylabel('Noise Budget (bits)')
            ax.set_title('CKKS Noise Budget')
            ax.legend(frameon=True)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        sp = save_path or os.path.join(self.output_dir, "encryption_metrics.pdf")
        self._save_both(sp)
        plt.close()

    def plot_summary_table(self, enc_metrics: Dict, plain_metrics: Dict = None,
                          save_path: str = None):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.axis('off')

        def calc_stats(metrics, is_enc=False):
            stats = {
                'Final Test Acc (%)': f"{metrics['test_acc'][-1]:.2f}" if metrics.get('test_acc') else 'N/A',
                'Avg Test Loss': f"{np.mean(metrics['test_loss']):.4f}" if metrics.get('test_loss') else 'N/A',
                'Avg Round Time (s)': f"{np.mean(metrics['total_round_time']):.2f}" if metrics.get('total_round_time') else 'N/A',
                'Total Comm (MB)': f"{sum(metrics['total_communication_cost']) / (1024 * 1024):.2f}" if metrics.get('total_communication_cost') else 'N/A',
                'Total Upload (MB)': f"{sum(metrics['upload_cost']) / (1024 * 1024):.2f}" if metrics.get('upload_cost') else 'N/A',
                'Total Download (MB)': f"{sum(metrics['download_cost']) / (1024 * 1024):.2f}" if metrics.get('download_cost') else 'N/A',
                'Avg CPU (%)': f"{np.mean(metrics['cpu_utilization']):.1f}" if metrics.get('cpu_utilization') else 'N/A',
                'Avg Memory (%)': f"{np.mean(metrics['memory_usage']):.1f}" if metrics.get('memory_usage') else 'N/A',
            }
            if is_enc:
                stats['Avg Expansion ($\\times$)'] = f"{np.mean(metrics['expansion_ratio']):.1f}" if metrics.get('expansion_ratio') else 'N/A'
                stats['Avg Encrypt (s)'] = f"{np.mean(metrics['encryption_time']):.3f}" if metrics.get('encryption_time') else 'N/A'
                stats['Avg Decrypt (s)'] = f"{np.mean(metrics['decryption_time']):.3f}" if metrics.get('decryption_time') else 'N/A'
            return stats

        enc_stats = calc_stats(enc_metrics, is_enc=True)
        if plain_metrics:
            plain_stats = calc_stats(plain_metrics, is_enc=False)
            all_keys = list(plain_stats.keys()) + [k for k in enc_stats.keys() if k not in plain_stats]
            table_data = [[k, plain_stats.get(k, 'N/A'), enc_stats.get(k, 'N/A')] for k in all_keys]
            col_labels = ['Metric', 'FedAvg (Plain)', 'CKKS-Fed (Encrypted)']
            col_colors = ['#E8E8E8'] * 3
        else:
            all_keys = list(enc_stats.keys())
            table_data = [[k, enc_stats.get(k, 'N/A')] for k in all_keys]
            col_labels = ['Metric', 'CKKS-Fed (Encrypted)']
            col_colors = ['#E8E8E8'] * 2

        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            loc='center',
            cellLoc='center',
            colColours=col_colors
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.1, 1.6)
        for i in range(len(col_colors)):
            table[(0, i)].set_text_props(fontweight='bold')
        plt.title('Experimental Results Summary', fontsize=12, fontweight='bold', pad=10)

        sp = save_path or os.path.join(self.output_dir, "summary_table.pdf")
        self._save_both(sp)
        plt.close()

    # ------------------------------------------------------------------
    # Master generation
    # ------------------------------------------------------------------
    def generate_all_visualizations(self, enc_metrics_path: str, plain_metrics_path: str = None):
        logger.info("Start generating visualizations...")
        enc_metrics = self.load_metrics(enc_metrics_path)
        plain_metrics = self.load_metrics(plain_metrics_path) if plain_metrics_path else None

        # Overview multi-subplots (quick look)
        self.plot_accuracy_comparison(enc_metrics, plain_metrics)
        self.plot_loss_comparison(enc_metrics, plain_metrics)
        self.plot_computation_time(enc_metrics, plain_metrics)
        self.plot_communication_cost(enc_metrics, plain_metrics)
        self.plot_system_metrics(enc_metrics, plain_metrics)
        self.plot_encryption_metrics(enc_metrics)
        self.plot_summary_table(enc_metrics, plain_metrics)

        # Separated single figures (ideal for IEEE papers)
        self.plot_accuracy_single(enc_metrics, plain_metrics)
        self.plot_loss_single(enc_metrics, plain_metrics)
        self.plot_communication_total_single(enc_metrics, plain_metrics)
        self.plot_communication_upload_single(enc_metrics, plain_metrics)
        self.plot_expansion_ratio_single(enc_metrics)
        self.plot_ciphertext_vs_plaintext_single(enc_metrics)
        self.plot_time_breakdown_single(enc_metrics, plain_metrics)
        self.plot_cpu_memory_single(enc_metrics, plain_metrics)

        logger.info(f"All figures saved to: {self.output_dir}")


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m ckks_fed.plotting <encrypted_metrics.json> [plain_metrics.json]")
        print("Example: python -m ckks_fed.plotting results/exp_enc/metrics.json results/exp_plain/metrics.json")
        return
    enc_metrics_path = sys.argv[1]
    plain_metrics_path = sys.argv[2] if len(sys.argv) >= 3 else None
    visualizer = ResultVisualizer()
    visualizer.generate_all_visualizations(enc_metrics_path, plain_metrics_path)


if __name__ == "__main__":
    main()
