"""
Experiment Plotter — 基于 SciencePlots 的实验结果绘图工具
===========================================================

用法极简，三行代码出图：
    from tools.plotter import Plotter
    p = Plotter()
    p.line(data={"FedAvg": {"x": rounds, "y": acc}}, xlabel="Round", ylabel="Accuracy")

支持图表类型：
    • line()        — 折线图（多系列对比）
    • bar()         — 分组柱状图
    • stacked_bar() — 堆叠柱状图
    • scatter()     — 散点图
    • multi_subplot() — 多子图拼接

输出格式：
    默认同时保存 PNG (300 dpi) + PDF（矢量图，适合论文插入）
    保存路径：tools/pic/（自动创建）

样式切换：
    p = Plotter(style="science")          # 基础学术风格
    p = Plotter(style=["science", "ieee"]) # IEEE 双栏风格
    p = Plotter(style=["science", "grid"]) # 带网格线
    p = Plotter(use_latex=False)          # 禁用 LaTeX（无 LaTeX 环境时用）
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# 尝试导入 SciencePlots；若未安装则给出友好提示
# ---------------------------------------------------------------------------
try:
    import scienceplots  # noqa: F401
    _HAS_SCIENCEPLOTS = True
except ImportError:
    _HAS_SCIENCEPLOTS = False


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def _detect_latex() -> bool:
    """检测系统是否安装了 LaTeX（用于 SciencePlots 的 latex 渲染）。"""
    return shutil.which("latex") is not None or shutil.which("pdflatex") is not None


def _resolve_style(style: Union[str, List[str], None], use_latex: bool) -> List[str]:
    """根据用户配置和系统环境，解析最终应用的 matplotlib 样式列表。"""
    if style is None:
        style = ["science"]
    elif isinstance(style, str):
        style = [style]
    else:
        style = list(style)

    # 若用户未显式指定 use_latex，且系统没有 LaTeX，则追加 no-latex 避免报错
    if not use_latex and "no-latex" not in style:
        style.append("no-latex")

    return style


def _resolve_formats(formats: Optional[List[str]]) -> List[str]:
    """默认同时输出 png + pdf。"""
    if formats is None:
        return ["png", "pdf"]
    return [f.lower().lstrip(".") for f in formats]


def _ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在，返回 Path 对象。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# 默认输出目录（基于本文件位置，避免因工作目录不同导致路径嵌套）
_DEFAULT_OUTPUT_DIR = str(Path(__file__).parent / "pic")


def _build_palette(n: int, colors: Optional[List[str]] = None) -> List[str]:
    """生成颜色列表；若用户未提供，则使用 matplotlib 默认 tab10。"""
    if colors is not None and len(colors) >= n:
        return colors[:n]
    cmap = matplotlib.colormaps["tab10"]
    return [matplotlib.colors.to_hex(cmap(i)) for i in range(n)]


# ---------------------------------------------------------------------------
# 颜色主题预设
# ---------------------------------------------------------------------------
COLOR_THEMES = {
    "default": None,
    "paper":   ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
    "contrast":["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"],
    "soft":    ["#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#253494", "#081d58"],
    "nature":  ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4"],
}


def _resolve_theme(theme: Optional[str], n: int) -> Optional[List[str]]:
    """根据主题名返回预设颜色列表。"""
    if theme is None or theme == "default":
        return None
    palette = COLOR_THEMES.get(theme, COLOR_THEMES["default"])
    return palette[:n] if palette else None


# ---------------------------------------------------------------------------
# 核心绘图类
# ---------------------------------------------------------------------------
class Plotter:
    """
    实验结果统一绘图器。

    Parameters
    ----------
    style : str or list of str, optional
        SciencePlots / matplotlib 样式名。
        常用: "science", ["science", "ieee"], ["science", "grid"], ["science", "nature"]
    output_dir : str or Path
        图片保存根目录，默认为 "tools/pic"。
    figsize : tuple
        画布尺寸 (宽, 高)，单位英寸。默认 (6, 4)。
    dpi : int
        PNG 分辨率。默认 300。
    use_latex : bool or None
        True  = 强制使用 LaTeX 渲染（需系统已安装 LaTeX）。
        False = 禁用 LaTeX，避免无环境时报错。
        None  = 自动检测（默认）。
    font_size : int
        全局基础字号。默认 12。
    theme : str, optional
        预设颜色主题。可选: "default", "paper", "contrast", "soft", "nature"
    """

    def __init__(
        self,
        style: Union[str, List[str], None] = None,
        output_dir: Union[str, Path] = None,
        figsize: Tuple[float, float] = (6, 4),
        dpi: int = 300,
        use_latex: Optional[bool] = None,
        font_size: int = 12,
        theme: Optional[str] = "default",
    ):
        self.output_dir = _ensure_dir(output_dir if output_dir is not None else _DEFAULT_OUTPUT_DIR)
        self.figsize = figsize
        self.dpi = dpi
        self.font_size = font_size
        self.theme = theme

        # LaTeX 检测
        if use_latex is None:
            use_latex = _detect_latex()
        self.use_latex = use_latex

        # 样式解析
        self.style = _resolve_style(style, use_latex)

        if not _HAS_SCIENCEPLOTS:
            print("[Warning] SciencePlots 未安装，回退到原生 matplotlib 样式。")
            print("          安装命令: pip install SciencePlots")
            self.style = []

        # 全局字体设置（兼容中文）
        plt.rcParams.update({
            "font.size": font_size,
            "axes.labelsize": font_size,
            "legend.fontsize": font_size - 1,
            "xtick.labelsize": font_size - 1,
            "ytick.labelsize": font_size - 1,
        })

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _save(self, filename: str, formats: Optional[List[str]] = None) -> List[Path]:
        """保存图片到 output_dir，返回保存的文件路径列表。"""
        fmts = _resolve_formats(formats)
        saved = []
        for fmt in fmts:
            fname = f"{filename}.{fmt}"
            fpath = self.output_dir / fname
            kwargs = {"bbox_inches": "tight"}
            if fmt == "png":
                kwargs["dpi"] = self.dpi
            plt.savefig(fpath, **kwargs)
            saved.append(fpath)
            print(f"[Saved] {fpath}")
        return saved

    def _apply_labels(self, ax, xlabel: str, ylabel: str, title: str):
        """统一设置坐标轴标签和标题。"""
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)

    # ------------------------------------------------------------------
    # 1. 折线图
    # ------------------------------------------------------------------
    def line(
        self,
        data: Dict[str, Dict[str, List[float]]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        markers: Optional[Dict[str, str]] = None,
        linestyles: Optional[Dict[str, str]] = None,
        linewidth: float = 1.5,
        marker_size: float = 4,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        legend_fontsize: Optional[float] = None,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        filename: str = "line",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        绘制折线图，支持多系列对比。

        Parameters
        ----------
        data : dict
            格式: {"系列名": {"x": [...], "y": [...]}, ...}
            若某系列省略 "x"，则默认用 range(len(y))。
        colors : dict, optional
            {"系列名": "颜色", ...}，如 {"FedAvg": "C0", "Ours": "C1"}
        markers : dict, optional
            {"系列名": "标记符号", ...}，如 {"FedAvg": "o", "Ours": "s"}
        linestyles : dict, optional
            {"系列名": "线型", ...}，如 {"FedAvg": "-", "Ours": "--"}

        Example
        -------
        p.line(
            data={
                "FedAvg": {"x": [1,2,3,4,5], "y": [0.50,0.60,0.68,0.72,0.75]},
                "Ours":   {"x": [1,2,3,4,5], "y": [0.55,0.66,0.73,0.78,0.82]},
            },
            xlabel="Communication Round",
            ylabel="Test Accuracy",
            title="Accuracy vs. Round",
            colors={"FedAvg": "#d62728", "Ours": "#1f77b4"},
            markers={"FedAvg": "o", "Ours": "s"},
            linestyles={"FedAvg": "--", "Ours": "-"},
            filename="accuracy",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)

            for label, series in data.items():
                x = series.get("x", list(range(len(series["y"]))))
                y = series["y"]
                c = colors.get(label) if colors else None
                m = markers.get(label) if markers else None
                ls = linestyles.get(label) if linestyles else None
                ax.plot(
                    x, y,
                    label=label,
                    color=c,
                    marker=m,
                    linestyle=ls,
                    linewidth=linewidth,
                    markersize=marker_size,
                )

            self._apply_labels(ax, xlabel, ylabel, title)
            legend_kwargs = {"loc": legend_loc, "ncol": legend_ncol}
            if legend_fontsize is not None:
                legend_kwargs["fontsize"] = legend_fontsize
            ax.legend(**legend_kwargs)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 1b. 带误差阴影的折线图
    # ------------------------------------------------------------------
    def line_with_shade(
        self,
        data: Dict[str, Dict[str, Any]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        linestyles: Optional[Dict[str, str]] = None,
        linewidth: float = 1.5,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        annotate_max: bool = False,
        filename: str = "line_shade",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        带误差阴影的折线图（适合展示 mean ± std / min-max）。

        Parameters
        ----------
        data : dict
            格式: {
                "Method": {
                    "x": [...],
                    "y": [...],           # mean 曲线
                    "y_low": [...],       # 下界 (可选)
                    "y_high": [...],      # 上界 (可选)
                    "std": [...],         # 标准差 (与 y_low/y_high 二选一)
                }, ...
            }
            若提供 "std"，则自动计算 y ± std 作为阴影边界。
            若提供 "y_low" / "y_high"，则直接使用。
        annotate_max : bool
            是否在每条曲线的最高点旁标注数值。

        Example
        -------
        p.line_with_shade(
            data={
                "FedAvg": {
                    "x": rounds,
                    "y": [0.50, 0.55, 0.60, ...],
                    "std": [0.02, 0.015, 0.01, ...],
                },
                "Ours": {
                    "x": rounds,
                    "y": [0.52, 0.58, 0.65, ...],
                    "std": [0.015, 0.01, 0.008, ...],
                },
            },
            xlabel="Round", ylabel="Accuracy",
            title="Accuracy (mean ± std)",
            annotate_max=True,
            filename="acc_shade",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)
            theme_colors = _resolve_theme(self.theme, len(data))

            for idx, (label, series) in enumerate(data.items()):
                x = np.array(series.get("x", list(range(len(series["y"])))))
                y = np.array(series["y"])
                c = colors.get(label) if colors else (theme_colors[idx] if theme_colors else None)
                ls = linestyles.get(label) if linestyles else None

                ax.plot(x, y, label=label, color=c, linestyle=ls, linewidth=linewidth, zorder=3)

                # 绘制阴影
                if "y_low" in series and "y_high" in series:
                    y_low, y_high = np.array(series["y_low"]), np.array(series["y_high"])
                elif "std" in series:
                    std = np.array(series["std"])
                    y_low, y_high = y - std, y + std
                else:
                    y_low = y_high = None

                if y_low is not None and y_high is not None:
                    ax.fill_between(x, y_low, y_high, color=c, alpha=0.2, linewidth=0)

                # 自动标注最高点
                if annotate_max:
                    max_idx = np.argmax(y)
                    ax.annotate(
                        f"{y[max_idx]:.3f}",
                        xy=(x[max_idx], y[max_idx]),
                        xytext=(5, 5), textcoords="offset points",
                        fontsize=self.font_size - 2,
                        color=c,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor=c, alpha=0.8),
                    )

            self._apply_labels(ax, xlabel, ylabel, title)
            ax.legend(loc=legend_loc, ncol=legend_ncol)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 1c. 双 Y 轴折线图
    # ------------------------------------------------------------------
    def twinx_line(
        self,
        left_data: Dict[str, Dict[str, List[float]]],
        right_data: Dict[str, Dict[str, List[float]]],
        xlabel: str = "",
        left_ylabel: str = "",
        right_ylabel: str = "",
        title: str = "",
        left_colors: Optional[Dict[str, str]] = None,
        right_colors: Optional[Dict[str, str]] = None,
        linewidth: float = 1.5,
        legend_loc: str = "upper left",
        right_legend_loc: str = "upper right",
        grid: bool = True,
        filename: str = "twinx",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        双 Y 轴折线图（左侧一条/多条 + 右侧一条/多条，共用 X 轴）。
        经典用法：左侧 Accuracy，右侧 Loss，同时随 Round 变化。

        Parameters
        ----------
        left_data : dict
            左轴数据，格式同 line(): {"Acc": {"x": [...], "y": [...]}}
        right_data : dict
            右轴数据，格式同 line(): {"Loss": {"x": [...], "y": [...]}}
        left_colors / right_colors : dict, optional
            分别控制左右轴颜色。

        Example
        -------
        p.twinx_line(
            left_data={"Accuracy": {"x": rounds, "y": acc}},
            right_data={"Loss": {"x": rounds, "y": loss}},
            xlabel="Round", left_ylabel="Accuracy", right_ylabel="Loss",
            title="Accuracy and Loss vs. Round",
            filename="acc_loss",
        )
        """
        with plt.style.context(self.style):
            fig, ax1 = plt.subplots(figsize=self.figsize)
            ax2 = ax1.twinx()

            theme_colors = _resolve_theme(self.theme, len(left_data) + len(right_data))
            tidx = 0

            # 左轴
            for label, series in left_data.items():
                x = series.get("x", list(range(len(series["y"]))))
                y = series["y"]
                c = left_colors.get(label) if left_colors else (theme_colors[tidx] if theme_colors else None)
                tidx += 1
                ax1.plot(x, y, label=label, color=c, linewidth=linewidth, linestyle="-")

            # 右轴
            for label, series in right_data.items():
                x = series.get("x", list(range(len(series["y"]))))
                y = series["y"]
                c = right_colors.get(label) if right_colors else (theme_colors[tidx] if theme_colors else None)
                tidx += 1
                ax2.plot(x, y, label=label, color=c, linewidth=linewidth, linestyle="--")

            ax1.set_xlabel(xlabel)
            ax1.set_ylabel(left_ylabel)
            ax2.set_ylabel(right_ylabel)
            if title:
                ax1.set_title(title)

            # 合并图例
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc=legend_loc)

            if grid:
                ax1.grid(True, linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 2. 分组柱状图
    # ------------------------------------------------------------------
    def bar(
        self,
        data: Dict[str, Dict[str, Any]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        width: float = 0.25,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        filename: str = "bar",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        分组柱状图（多系列并列）。

        Parameters
        ----------
        data : dict
            格式: {
                "categories": ["A", "B", "C"],
                "series": {
                    "Method1": [0.5, 0.6, 0.7],
                    "Method2": [0.55, 0.65, 0.75],
                }
            }

        Example
        -------
        p.bar(
            data={
                "categories": ["MNIST", "FMNIST", "CIFAR-10"],
                "series": {
                    "FedAvg": [0.92, 0.85, 0.68],
                    "Ours":   [0.94, 0.88, 0.75],
                },
            },
            xlabel="Dataset",
            ylabel="Accuracy",
            title="Accuracy Comparison",
            filename="dataset_acc",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)

            categories = data["categories"]
            series = data["series"]
            n_series = len(series)
            n_cats = len(categories)
            x = np.arange(n_cats)

            palette = _build_palette(n_series)
            for idx, (label, values) in enumerate(series.items()):
                offset = width * (idx - (n_series - 1) / 2)
                c = colors.get(label) if colors else palette[idx]
                ax.bar(x + offset, values, width, label=label, color=c, edgecolor="black", linewidth=0.5)

            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            self._apply_labels(ax, xlabel, ylabel, title)
            ax.legend(loc=legend_loc, ncol=legend_ncol)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, axis="y", linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 3. 堆叠柱状图
    # ------------------------------------------------------------------
    def stacked_bar(
        self,
        data: Dict[str, Dict[str, Any]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        width: float = 0.5,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        filename: str = "stacked_bar",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        堆叠柱状图（多系列上下叠加）。

        Parameters
        ----------
        data : dict
            格式与 bar() 相同：
            {
                "categories": ["A", "B", "C"],
                "series": {
                    "Layer1": [10, 15, 20],
                    "Layer2": [20, 25, 30],
                    "Layer3": [30, 35, 40],
                }
            }

        Example
        -------
        p.stacked_bar(
            data={
                "categories": ["Client 1", "Client 2", "Client 3"],
                "series": {
                    "Upload":   [12.5, 10.2, 15.8],
                    "Download": [8.3,  7.1,  9.4],
                },
            },
            xlabel="Client ID",
            ylabel="Communication Cost (MB)",
            title="Per-Client Communication Breakdown",
            filename="comm_cost",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)

            categories = data["categories"]
            series = data["series"]
            n_series = len(series)
            x = np.arange(len(categories))

            palette = _build_palette(n_series)
            bottom = np.zeros(len(categories))

            for idx, (label, values) in enumerate(series.items()):
                c = colors.get(label) if colors else palette[idx]
                ax.bar(x, values, width, bottom=bottom, label=label, color=c, edgecolor="black", linewidth=0.5)
                bottom += np.array(values)

            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            self._apply_labels(ax, xlabel, ylabel, title)
            ax.legend(loc=legend_loc, ncol=legend_ncol)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, axis="y", linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 4. 散点图
    # ------------------------------------------------------------------
    def scatter(
        self,
        data: Dict[str, Dict[str, List[float]]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        markers: Optional[Dict[str, str]] = None,
        sizes: Optional[Dict[str, float]] = None,
        alpha: float = 0.7,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        filename: str = "scatter",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        散点图。

        Parameters
        ----------
        data : dict
            格式: {"系列名": {"x": [...], "y": [...]}, ...}
            可选附加键 "size" 控制每个点的大小。

        Example
        -------
        p.scatter(
            data={
                "Sparse 10%": {"x": [1,2,3], "y": [0.5,0.6,0.7]},
                "Sparse 50%": {"x": [1,2,3], "y": [0.6,0.7,0.8]},
            },
            xlabel="Round",
            ylabel="Accuracy",
            filename="scatter_demo",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)

            for label, series in data.items():
                x = series["x"]
                y = series["y"]
                c = colors.get(label) if colors else None
                m = markers.get(label) if markers else "o"
                s = sizes.get(label) if sizes else 40
                ax.scatter(x, y, label=label, color=c, marker=m, s=s, alpha=alpha, edgecolors="black", linewidth=0.5)

            self._apply_labels(ax, xlabel, ylabel, title)
            ax.legend(loc=legend_loc, ncol=legend_ncol)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 5. 堆叠面积图
    # ------------------------------------------------------------------
    def stacked_area(
        self,
        data: Dict[str, Dict[str, Any]],
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        colors: Optional[Dict[str, str]] = None,
        alpha: float = 0.85,
        legend_loc: str = "best",
        legend_ncol: int = 1,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        grid: bool = True,
        filename: str = "stacked_area",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        堆叠面积图（适合观察通信量、时间开销等随轮次的累积变化）。

        Parameters
        ----------
        data : dict
            格式: {
                "x": [1, 2, 3, ...],
                "series": {
                    "Upload":   [10, 12, 11, ...],
                    "Download": [8,  9,  8,  ...],
                }
            }
            所有 series 的 y 值会在同一 x 位置上堆叠。

        Example
        -------
        p.stacked_area(
            data={
                "x": list(range(1, 51)),
                "series": {
                    "Upload":   [np.random.uniform(8, 12) for _ in range(50)],
                    "Download": [np.random.uniform(6, 10) for _ in range(50)],
                },
            },
            xlabel="Round",
            ylabel="Communication Cost (MB)",
            title="Per-Round Communication",
            filename="comm_area",
        )
        """
        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)

            x = data["x"]
            series = data["series"]
            n_series = len(series)
            palette = _build_palette(n_series)

            labels = list(series.keys())
            y_stack = np.vstack([series[label] for label in labels])
            c_list = [colors.get(label) if colors else palette[idx] for idx, label in enumerate(labels)]

            ax.stackplot(x, y_stack, labels=labels, colors=c_list, alpha=alpha, edgecolor="black", linewidth=0.3)

            self._apply_labels(ax, xlabel, ylabel, title)
            ax.legend(loc=legend_loc, ncol=legend_ncol)
            if xlim:
                ax.set_xlim(xlim)
            if ylim:
                ax.set_ylim(ylim)
            if grid:
                ax.grid(True, linestyle="--", alpha=0.5)

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 6. 多子图拼接
    # ------------------------------------------------------------------
    def multi_subplot(
        self,
        plot_configs: List[Dict[str, Any]],
        nrows: int = 1,
        ncols: int = 2,
        figsize: Optional[Tuple[float, float]] = None,
        filename: str = "multi_subplot",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        将多个子图拼成一张大图。

        Parameters
        ----------
        plot_configs : list of dict
            每个 dict 描述一个子图，支持以下键：
                - "type": "line" | "bar" | "stacked_bar" | "scatter" | "stacked_area"
                - "data": 数据（格式与对应函数一致）
                - "xlabel", "ylabel", "title": 标签
                - "colors", "legend_loc", ...: 其他绘图参数
        nrows, ncols : int
            子图行列数。
        figsize : tuple, optional
            整体画布尺寸；默认按子图数量自动放大。

        Example
        -------
        p.multi_subplot(
            plot_configs=[
                {
                    "type": "line",
                    "data": {"FedAvg": {"x": [1,2,3], "y": [0.5,0.6,0.7]}},
                    "xlabel": "Round", "ylabel": "Acc", "title": "(a) Accuracy",
                },
                {
                    "type": "bar",
                    "data": {
                        "categories": ["A", "B"],
                        "series": {"M1": [0.5, 0.6], "M2": [0.55, 0.65]},
                    },
                    "xlabel": "Dataset", "ylabel": "Acc", "title": "(b) Comparison",
                },
            ],
            nrows=1, ncols=2,
            filename="combined",
        )
        """
        with plt.style.context(self.style):
            if figsize is None:
                figsize = (self.figsize[0] * ncols, self.figsize[1] * nrows)
            fig, axes = plt.subplots(nrows, ncols, figsize=figsize, constrained_layout=True)
            if nrows * ncols == 1:
                axes = [axes]
            else:
                axes = axes.flatten()

            for ax, cfg in zip(axes, plot_configs):
                plot_type = cfg.get("type", "line")
                data = cfg["data"]
                xlabel = cfg.get("xlabel", "")
                ylabel = cfg.get("ylabel", "")
                title = cfg.get("title", "")
                colors = cfg.get("colors")
                grid = cfg.get("grid", True)

                if plot_type == "line":
                    for label, series in data.items():
                        x = series.get("x", list(range(len(series["y"]))))
                        y = series["y"]
                        c = colors.get(label) if colors else None
                        ax.plot(x, y, label=label, color=c, linewidth=1.5)
                    ax.legend(loc=cfg.get("legend_loc", "best"))

                elif plot_type == "bar":
                    categories = data["categories"]
                    series = data["series"]
                    n_series = len(series)
                    x = np.arange(len(categories))
                    w = cfg.get("width", 0.25)
                    palette = _build_palette(n_series)
                    for idx, (lab, vals) in enumerate(series.items()):
                        offset = w * (idx - (n_series - 1) / 2)
                        c = colors.get(lab) if colors else palette[idx]
                        ax.bar(x + offset, vals, w, label=lab, color=c, edgecolor="black", linewidth=0.5)
                    ax.set_xticks(x)
                    ax.set_xticklabels(categories)
                    ax.legend(loc=cfg.get("legend_loc", "best"))

                elif plot_type == "stacked_bar":
                    categories = data["categories"]
                    series = data["series"]
                    x = np.arange(len(categories))
                    w = cfg.get("width", 0.5)
                    palette = _build_palette(len(series))
                    bottom = np.zeros(len(categories))
                    for idx, (lab, vals) in enumerate(series.items()):
                        c = colors.get(lab) if colors else palette[idx]
                        ax.bar(x, vals, w, bottom=bottom, label=lab, color=c, edgecolor="black", linewidth=0.5)
                        bottom += np.array(vals)
                    ax.set_xticks(x)
                    ax.set_xticklabels(categories)
                    ax.legend(loc=cfg.get("legend_loc", "best"))

                elif plot_type == "scatter":
                    for label, series in data.items():
                        c = colors.get(label) if colors else None
                        ax.scatter(series["x"], series["y"], label=label, color=c, s=40, alpha=0.7, edgecolors="black", linewidth=0.5)
                    ax.legend(loc=cfg.get("legend_loc", "best"))

                elif plot_type == "stacked_area":
                    x = data["x"]
                    series = data["series"]
                    palette = _build_palette(len(series))
                    labels = list(series.keys())
                    y_stack = np.vstack([series[label] for label in labels])
                    c_list = [colors.get(lab) if colors else palette[idx] for idx, lab in enumerate(labels)]
                    ax.stackplot(x, y_stack, labels=labels, colors=c_list, alpha=0.85, edgecolor="black", linewidth=0.3)
                    ax.legend(loc=cfg.get("legend_loc", "best"), ncol=cfg.get("legend_ncol", 1))

                self._apply_labels(ax, xlabel, ylabel, title)
                if grid:
                    ax.grid(True, linestyle="--", alpha=0.5)

            # 隐藏多余的子图
            for ax in axes[len(plot_configs):]:
                ax.axis("off")

            saved = self._save(filename, formats)
            plt.close(fig)
            return saved

    # ------------------------------------------------------------------
    # 7. 热力图
    # ------------------------------------------------------------------
    def heatmap(
        self,
        data: Union[np.ndarray, List[List[float]]],
        xlabels: Optional[List[str]] = None,
        ylabels: Optional[List[str]] = None,
        xlabel: str = "",
        ylabel: str = "",
        title: str = "",
        cmap: str = "YlOrRd",
        annot: bool = True,
        fmt: str = ".2f",
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        cbar_label: str = "",
        filename: str = "heatmap",
        formats: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        热力图（适合混淆矩阵、相关性矩阵、客户端-数据分布等）。

        Parameters
        ----------
        data : array-like
            2D 数组或嵌套列表。
        xlabels / ylabels : list of str, optional
            横纵坐标的刻度标签。
        cmap : str
            matplotlib 颜色映射名。推荐:
            - "YlOrRd" / "Reds" — 数值越大越红（经典）
            - "Blues" / "YlGnBu" — 蓝色系
            - "coolwarm" / "RdBu_r" — 正负对比（适合相关性矩阵）
        annot : bool
            是否在格子里显示数值。
        fmt : str
            数值格式，如 ".2f"（保留两位小数）、".0f"（整数）、".1%"（百分比）。
        vmin / vmax : float, optional
            颜色映射的最小/最大值。
        cbar_label : str
            颜色条标签。

        Example
        -------
        p.heatmap(
            data=[[0.9, 0.05, 0.05],
                  [0.1, 0.8,  0.1],
                  [0.05, 0.15, 0.8]],
            xlabels=["Pred A", "Pred B", "Pred C"],
            ylabels=["True A", "True B", "True C"],
            title="Confusion Matrix",
            cmap="Blues",
            fmt=".0%",
            filename="confusion",
        )
        """
        import seaborn as sns

        with plt.style.context(self.style):
            fig, ax = plt.subplots(figsize=self.figsize)
            data_arr = np.array(data)

            sns.heatmap(
                data_arr,
                annot=annot,
                fmt=fmt,
                cmap=cmap,
                xticklabels=xlabels if xlabels else "auto",
                yticklabels=ylabels if ylabels else "auto",
                vmin=vmin,
                vmax=vmax,
                linewidths=0.5,
                linecolor="gray",
                cbar_kws={"label": cbar_label} if cbar_label else {},
                ax=ax,
            )

            self._apply_labels(ax, xlabel, ylabel, title)
            saved = self._save(filename, formats)
            plt.close(fig)
            return saved


# ---------------------------------------------------------------------------
# 配置文件驱动绘图
# ---------------------------------------------------------------------------
def plot_from_config(config_path: Union[str, Path]) -> List[Path]:
    """
    从 JSON 配置文件批量出图，无需写 Python 代码。

    配置文件格式见 tools/plot_config.json 示例。

    Example
    -------
    python -c "from tools.plotter import plot_from_config; plot_from_config('tools/plot_config.json')"
    """
    import json

    config_path = Path(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    global_cfg = cfg.get("global", {})
    p = Plotter(**global_cfg)

    all_saved = []
    for plot_cfg in cfg.get("plots", []):
        plot_type = plot_cfg.pop("type", "line")
        filename = plot_cfg.pop("filename", "plot")
        formats = plot_cfg.pop("formats", None)

        if plot_type == "line":
            all_saved.extend(p.line(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "line_with_shade":
            all_saved.extend(p.line_with_shade(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "bar":
            all_saved.extend(p.bar(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "stacked_bar":
            all_saved.extend(p.stacked_bar(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "stacked_area":
            all_saved.extend(p.stacked_area(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "scatter":
            all_saved.extend(p.scatter(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "heatmap":
            all_saved.extend(p.heatmap(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "multi_subplot":
            all_saved.extend(p.multi_subplot(filename=filename, formats=formats, **plot_cfg))
        elif plot_type == "twinx_line":
            all_saved.extend(p.twinx_line(filename=filename, formats=formats, **plot_cfg))
        else:
            raise ValueError(f"不支持的图表类型: {plot_type}")

    return all_saved


# ---------------------------------------------------------------------------
# 便捷函数：一键绘制常见实验图
# ---------------------------------------------------------------------------
def plot_accuracy_curve(
    data: Dict[str, Dict[str, List[float]]],
    xlabel: str = "Communication Round",
    ylabel: str = "Test Accuracy",
    title: str = "Accuracy vs. Communication Round",
    filename: str = "accuracy",
    output_dir: str = "tools/pic",
    **kwargs,
) -> List[Path]:
    """
    快速绘制「准确率-轮次」折线图（联邦学习最常用）。

    Example
    -------
    plot_accuracy_curve({
        "FedAvg": {"x": list(range(1, 101)), "y": [0.5+0.003*i for i in range(100)]},
        "Ours":   {"x": list(range(1, 101)), "y": [0.55+0.0035*i for i in range(100)]},
    })
    """
    p = Plotter(output_dir=output_dir)
    return p.line(data, xlabel=xlabel, ylabel=ylabel, title=title, filename=filename, **kwargs)


def plot_loss_curve(
    data: Dict[str, Dict[str, List[float]]],
    xlabel: str = "Communication Round",
    ylabel: str = "Training Loss",
    title: str = "Loss vs. Communication Round",
    filename: str = "loss",
    output_dir: str = "tools/pic",
    **kwargs,
) -> List[Path]:
    """快速绘制「损失-轮次」折线图。"""
    p = Plotter(output_dir=output_dir)
    return p.line(data, xlabel=xlabel, ylabel=ylabel, title=title, filename=filename, **kwargs)


# ---------------------------------------------------------------------------
# 自测入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Experiment Plotter 自测脚本")
    print("=" * 60)

    # 1. 折线图 — 模拟联邦学习准确率曲线
    print("\n[1/5] 折线图: Accuracy vs. Round")
    p = Plotter(style=["science", "grid"], output_dir="tools/pic")
    rounds = list(range(1, 51))
    p.line(
        data={
            "FedAvg": {
                "x": rounds,
                "y": [0.50 + 0.28 * (1 - np.exp(-0.08 * r)) + np.random.normal(0, 0.01) for r in rounds],
            },
            "FedProx": {
                "x": rounds,
                "y": [0.52 + 0.27 * (1 - np.exp(-0.07 * r)) + np.random.normal(0, 0.01) for r in rounds],
            },
            "Ours": {
                "x": rounds,
                "y": [0.55 + 0.26 * (1 - np.exp(-0.06 * r)) + np.random.normal(0, 0.008) for r in rounds],
            },
        },
        xlabel="Communication Round",
        ylabel="Test Accuracy",
        title="Accuracy Comparison on CIFAR-10",
        colors={"FedAvg": "#d62728", "FedProx": "#ff7f0e", "Ours": "#1f77b4"},
        markers={"FedAvg": "o", "FedProx": "s", "Ours": "D"},
        linestyles={"FedAvg": "--", "FedProx": "-.", "Ours": "-"},
        legend_ncol=3,
        filename="demo_line",
    )

    # 2. 分组柱状图
    print("\n[2/5] 分组柱状图: Dataset Comparison")
    p.bar(
        data={
            "categories": ["MNIST", "FMNIST", "CIFAR-10", "CIFAR-100"],
            "series": {
                "FedAvg": [0.92, 0.85, 0.68, 0.42],
                "FedProx": [0.93, 0.86, 0.70, 0.45],
                "Ours": [0.94, 0.88, 0.75, 0.50],
            },
        },
        xlabel="Dataset",
        ylabel="Test Accuracy",
        title="Final Accuracy Comparison",
        colors={"FedAvg": "#d62728", "FedProx": "#ff7f0e", "Ours": "#1f77b4"},
        width=0.25,
        legend_ncol=3,
        filename="demo_bar",
    )

    # 3. 堆叠柱状图
    print("\n[3/5] 堆叠柱状图: Communication Cost Breakdown")
    p.stacked_bar(
        data={
            "categories": ["Client 1", "Client 2", "Client 3", "Client 4", "Client 5"],
            "series": {
                "Upload": [12.5, 10.2, 15.8, 9.6, 11.3],
                "Download": [8.3, 7.1, 9.4, 6.5, 7.8],
                "Overhead": [2.1, 1.8, 2.5, 1.5, 2.0],
            },
        },
        xlabel="Client ID",
        ylabel="Communication Cost (MB)",
        title="Per-Round Communication Breakdown",
        filename="demo_stacked_bar",
    )

    # 4. 散点图
    print("\n[4/5] 散点图: Latency vs. Accuracy")
    np.random.seed(42)
    p.scatter(
        data={
            "Sparse 10%": {
                "x": np.random.normal(0.75, 0.05, 20),
                "y": np.random.normal(120, 15, 20),
            },
            "Sparse 50%": {
                "x": np.random.normal(0.78, 0.04, 20),
                "y": np.random.normal(180, 20, 20),
            },
            "Full": {
                "x": np.random.normal(0.80, 0.03, 20),
                "y": np.random.normal(350, 30, 20),
            },
        },
        xlabel="Test Accuracy",
        ylabel="Latency (s)",
        title="Accuracy-Latency Trade-off",
        filename="demo_scatter",
    )

    # 5. 带误差阴影的折线图 + 自动标注最值
    print("\n[5/9] 带误差阴影折线图: mean ± std")
    np.random.seed(3)
    rounds_30 = list(range(1, 31))
    p_shade = Plotter(style=["science", "grid"], theme="contrast")
    p_shade.line_with_shade(
        data={
            "FedAvg": {
                "x": rounds_30,
                "y": [0.50 + 0.28*(1-np.exp(-0.08*r)) for r in rounds_30],
                "std": [0.02 + 0.001*r for r in rounds_30],
            },
            "Ours": {
                "x": rounds_30,
                "y": [0.55 + 0.26*(1-np.exp(-0.06*r)) for r in rounds_30],
                "std": [0.015 + 0.0008*r for r in rounds_30],
            },
        },
        xlabel="Round",
        ylabel="Test Accuracy",
        title="Accuracy with Confidence Band",
        annotate_max=True,
        filename="demo_line_shade",
    )

    # 6. 双 Y 轴图
    print("\n[6/9] 双 Y 轴图: Accuracy + Loss")
    p_twin = Plotter(style=["science", "grid"])
    p_twin.twinx_line(
        left_data={
            "Accuracy": {"x": rounds_30, "y": [0.50 + 0.28*(1-np.exp(-0.08*r)) for r in rounds_30]},
        },
        right_data={
            "Loss": {"x": rounds_30, "y": [2.0 * np.exp(-0.05*r) + 0.3 for r in rounds_30]},
        },
        xlabel="Round",
        left_ylabel="Accuracy",
        right_ylabel="Loss",
        title="Accuracy and Loss vs. Round",
        filename="demo_twinx",
    )

    # 7. 堆叠面积图 — 单图
    print("\n[7/9] 堆叠面积图: Communication Over Rounds")
    np.random.seed(7)
    p.stacked_area(
        data={
            "x": rounds_30,
            "series": {
                "Upload":   [10 + np.random.normal(0, 0.8) for _ in rounds_30],
                "Download": [8  + np.random.normal(0, 0.6) for _ in rounds_30],
            },
        },
        xlabel="Round",
        ylabel="Communication Cost (MB)",
        title="Per-Round Communication (Single)",
        colors={"Upload": "#3498db", "Download": "#e74c3c"},
        filename="demo_stacked_area",
    )

    # 8. 多子图堆叠面积图 — 2×3 通信量对比
    print("\n[8/9] 多子图堆叠面积图: 2×3 Communication Comparison")
    np.random.seed(42)

    def _make_comm_series(base_up, base_down, noise=0.5):
        up = [base_up + np.random.normal(0, noise) + 0.02 * r for r in rounds_30]
        down = [base_down + np.random.normal(0, noise) + 0.015 * r for r in rounds_30]
        return {"Upload": up, "Download": down}

    configs = [
        {"title": "(a) MNIST",       "series": _make_comm_series(8.0, 6.0, 0.3)},
        {"title": "(b) FMNIST",      "series": _make_comm_series(10.0, 7.5, 0.5)},
        {"title": "(c) CIFAR-10",    "series": _make_comm_series(15.0, 12.0, 0.8)},
        {"title": "(d) CIFAR-100",   "series": _make_comm_series(18.0, 14.0, 1.0)},
        {"title": "(e) Shakespeare", "series": _make_comm_series(5.0, 4.0, 0.2)},
        {"title": "(f) Google Speech","series": _make_comm_series(12.0, 9.0, 0.6)},
    ]

    plot_configs = []
    for cfg in configs:
        plot_configs.append({
            "type": "stacked_area",
            "data": {"x": rounds_30, "series": cfg["series"]},
            "xlabel": "Round",
            "ylabel": "Cost (MB)",
            "title": cfg["title"],
            "colors": {"Upload": "#3498db", "Download": "#e74c3c"},
            "legend_ncol": 1,
            "grid": True,
        })

    p2 = Plotter(style=["science", "grid"], figsize=(4.5, 3.2))
    p2.multi_subplot(
        plot_configs=plot_configs,
        nrows=2, ncols=3,
        figsize=(13, 8),
        filename="demo_comm_grid",
    )

    # 9. 热力图 — 混淆矩阵
    print("\n[9/10] 热力图: Confusion Matrix")
    p.heatmap(
        data=[
            [0.85, 0.08, 0.07],
            [0.10, 0.80, 0.10],
            [0.05, 0.12, 0.83],
        ],
        xlabels=["Pred A", "Pred B", "Pred C"],
        ylabels=["True A", "True B", "True C"],
        title="Confusion Matrix",
        xlabel="Predicted",
        ylabel="True",
        cmap="Blues",
        fmt=".0%",
        cbar_label="Proportion",
        filename="demo_heatmap",
    )

    # 10. 从 JSON 配置文件批量出图
    print("\n[10/10] 配置文件驱动绘图: plot_from_config()")
    cfg_path = Path("tools/plot_config.json")
    if cfg_path.exists():
        plot_from_config(cfg_path)
    else:
        print("  (跳过: tools/plot_config.json 不存在)")

    print("\n" + "=" * 60)
    print("自测完成，所有图片已保存到: tools/pic/")
    print("=" * 60)
