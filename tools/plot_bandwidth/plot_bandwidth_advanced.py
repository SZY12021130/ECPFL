"""
带宽分布进阶优雅分布图模块（plot_bandwidth_advanced）
========================================================

本模块是对 plot_bandwidth_area.py 的扩展，提供 8 种进阶优雅的
带宽分布可视化模式，使分布形态的展示更直观、更具论文美感。

包含的图表类型：
    split_violin    分裂小提琴图（左右镜像 KDE 对比）
    halfeye         半眼图（半小提琴 + IQR + 中位数点 + 散点）
    ecdf_diff       ECDF 差异曲线（定位上下行分布差异最大的带宽阈值）
    binned_heatmap  二维对数分箱热力图（联合密度矩阵）
    waffle          华夫饼图（按速率档位的占比方块矩阵）
    polar_radar     极坐标分布玫瑰图（封面级形态）
    sina            Sina 图（密度约束抖动散点）
    dot_matrix      点阵热力图（圆点大小+颜色双编码）

设计要点：
    • 所有函数签名与 plot_bandwidth_area.py 中的 plot_xxx 一致：
        func(p, ul, dl, palette, filename, ...)
    • 复用 SciencePlots 样式（通过传入的 Plotter 实例 p）
    • 全部以 Mbps 为单位
    • 同时保存 PNG (300 dpi) + PDF 矢量图

用法（通过主脚本统一调用）：
    python tools/plot_bandwidth/plot_bandwidth_area.py \
        --type split_violin,halfeye,ecdf_diff --palette contrast

    python tools/plot_bandwidth/plot_bandwidth_area.py --type all --palette all
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.stats import gaussian_kde


# ===================================================================
#  1. 分裂小提琴图
# ===================================================================
def plot_split_violin(p, ul, dl, palette, filename):
    """
    分裂小提琴图 (Split Violin) — 同一位置左半为 Upload、右半为 Download。

    这是上下行分布最直观的「镜像对比」形态：左右两条 KDE 直接拼合，
    任意带宽高度上左右宽度的差异即代表两分布的密度差。叠加内部
    mini-boxplot，兼顾形态与统计摘要。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(6, 5))

        pos = 0
        for arr, color, line_color, side in [
            (ul, palette["upload_fill"], palette["upload_line"], "left"),
            (dl, palette["download_fill"], palette["download_line"], "right"),
        ]:
            pos_arr = arr[arr > 0]
            log_arr = np.log10(pos_arr)
            kde = gaussian_kde(log_arr)
            y = np.linspace(log_arr.min() - 0.2, log_arr.max() + 0.2, 400)
            density = kde(y)
            density = density / density.max() * 0.4

            x_curve = pos - density if side == "left" else pos + density
            ax.fill_betweenx(10 ** y, pos, x_curve, color=color, alpha=0.45, linewidth=0)
            ax.plot(x_curve, 10 ** y, color=line_color, linewidth=1.0, alpha=0.85)

        # 内部 mini-boxplot (Q1-Q3 白条 + 中位数黑线)
        for arr, line_color in [
            (ul, palette["upload_line"]),
            (dl, palette["download_line"]),
        ]:
            q1, med, q3 = np.percentile(arr, [25, 50, 75])
            ax.plot([pos - 0.015, pos + 0.015], [med, med], color="black", linewidth=2)
            ax.plot([pos, pos], [q1, q3], color="white", linewidth=3, alpha=0.8)

        ax.set_yscale("log")
        ax.set_xticks([pos])
        ax.set_xticklabels(["Upload  |  Download"])
        ax.set_ylabel("Bandwidth (Mbps, log scale)")
        ax.set_title("Split Violin: Upload (left) vs. Download (right)")
        ax.set_xlim(-0.6, 0.6)
        ax.grid(True, linestyle="--", alpha=0.4, axis="y", which="both")

        ax.legend(
            handles=[
                plt.Line2D([0], [0], color=palette["upload_fill"], lw=8, alpha=0.5, label="Upload"),
                plt.Line2D([0], [0], color=palette["download_fill"], lw=8, alpha=0.5, label="Download"),
            ],
            loc="lower right", fontsize=p.font_size - 2,
        )

        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  2. 半眼图
# ===================================================================
def plot_halfeye(p, ul, dl, palette, filename, max_points=500):
    """
    半眼图 (Half-Eye) — 半小提琴 + 中位数点 + 分位数区间 + 抖动散点。

    来自 ggdist / tidyverse 的优雅分布范式：单条水平分布带，向上半密度、
    向下散点、中央高亮 50% 区间与中位数点，信息密度极高。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(8, 3.5))

        for i, (arr, color, line_color, label) in enumerate([
            (ul, palette["upload_fill"], palette["upload_line"], "Upload"),
            (dl, palette["download_fill"], palette["download_line"], "Download"),
        ]):
            y_pos = i
            pos_arr = arr[arr > 0]
            log_arr = np.log10(pos_arr)
            kde = gaussian_kde(log_arr)
            x = np.linspace(log_arr.min() - 0.2, log_arr.max() + 0.2, 400)
            density = kde(x)
            density = density / density.max() * 0.32

            # 向上半小提琴
            ax.fill_between(10 ** x, y_pos, y_pos + density, color=color, alpha=0.4, linewidth=0)
            ax.plot(10 ** x, y_pos + density, color=line_color, linewidth=1.0)

            # 中央 IQR 条 + 中位数点
            q1, med, q3 = np.percentile(arr, [25, 50, 75])
            ax.plot([q1, q3], [y_pos, y_pos], color=line_color, linewidth=4, alpha=0.7, solid_capstyle="round")
            ax.scatter([med], [y_pos], color="white", edgecolors=line_color, s=60, zorder=5, linewidth=1.5)

            # 向下抖动散点
            if len(arr) > max_points:
                idx = np.random.choice(len(arr), max_points, replace=False)
                arr_s = arr[idx]
            else:
                arr_s = arr
            jitter = np.random.uniform(-0.12, -0.02, len(arr_s))
            ax.scatter(arr_s, y_pos + jitter, s=3, alpha=0.3, color=color, edgecolors="none")

            ax.text(med, y_pos + 0.4, f"median = {med:.1f}", ha="center",
                    fontsize=p.font_size - 3, color=line_color)

        ax.set_xscale("log")
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Upload", "Download"])
        ax.set_xlabel("Bandwidth (Mbps, log scale)")
        ax.set_title("Half-Eye Plots: Distribution with Median & IQR")
        ax.grid(True, linestyle="--", alpha=0.4, axis="x", which="both")
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  3. ECDF 差异曲线
# ===================================================================
def plot_ecdf_diff(p, ul, dl, palette, filename):
    """
    ECDF 差异曲线 — F_DL(x) - F_UL(x) 随带宽变化。

    正值表示在该带宽处 Download 的累积占比高于 Upload（即更多客户端
    的下行带宽 ≤ x），峰值位置揭示两分布差异最大的带宽阈值，
    是「分布差异在哪」的最直观回答。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=p.figsize)

        grid = np.linspace(0, max(ul.max(), dl.max()) * 0.6, 1000)
        cdf_ul = np.searchsorted(np.sort(ul), grid, side="right") / len(ul)
        cdf_dl = np.searchsorted(np.sort(dl), grid, side="right") / len(dl)
        diff = cdf_dl - cdf_ul

        ax.axhline(0, color="black", linewidth=0.8)
        ax.fill_between(grid, 0, diff, where=diff >= 0, color=palette["download_fill"],
                        alpha=0.4, linewidth=0, label="DL cumulative > UL")
        ax.fill_between(grid, 0, diff, where=diff < 0, color=palette["upload_fill"],
                        alpha=0.4, linewidth=0, label="DL cumulative < UL")
        ax.plot(grid, diff, color="black", linewidth=1.5)

        # 标注最大差异点
        peak_idx = int(np.argmax(np.abs(diff)))
        peak_x, peak_y = grid[peak_idx], diff[peak_idx]
        ax.scatter([peak_x], [peak_y], color="black", s=40, zorder=5)
        ax.annotate(
            f"max |diff| = {abs(peak_y):.3f}\nat {peak_x:.1f} Mbps",
            xy=(peak_x, peak_y),
            xytext=(peak_x + 30, peak_y + (0.03 if peak_y > 0 else -0.03)),
            fontsize=p.font_size - 2,
            arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.85),
        )

        ax.set_xlabel("Bandwidth (Mbps)")
        ax.set_ylabel("F$_{DL}$(x) - F$_{UL}$(x)")
        ax.set_title("ECDF Difference: Where Upload & Download Diverge")
        ax.legend(loc="upper right", fontsize=p.font_size - 2)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.set_xlim(left=0)
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  4. 二维分箱热力图
# ===================================================================
def plot_binned_heatmap(p, ul, dl, palette, filename, n_bins=30):
    """
    二维分箱热力图 — UL × DL 联合分布矩阵。

    对数分箱 + viridis 配色 + 色阶条，每格代表落入该 (UL, DL) 区间的
    客户端数量。叠加 y=x 参考线，直击联合密度结构。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(7, 6))

        mask = (ul > 0) & (dl > 0)
        log_u = np.log10(ul[mask])
        log_d = np.log10(dl[mask])

        H, xe, ye = np.histogram2d(log_u, log_d, bins=n_bins)
        H = np.ma.masked_where(H == 0, H)

        im = ax.pcolormesh(10 ** xe, 10 ** ye, H.T, cmap="viridis",
                           norm=mcolors.LogNorm(vmin=1, vmax=H.max()),
                           shading="auto")
        fig.colorbar(im, ax=ax, label="Client count (log)")

        ax.set_xscale("log")
        ax.set_yscale("log")
        lim_lo = 10 ** min(log_u.min(), log_d.min())
        lim_hi = 10 ** max(log_u.max(), log_d.max())
        ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], "w--",
                linewidth=1.0, alpha=0.7, label="y = x")

        ax.set_xlabel("Upload Bandwidth (Mbps, log)")
        ax.set_ylabel("Download Bandwidth (Mbps, log)")
        ax.set_title("2D Binned Heatmap of Joint Distribution")
        ax.legend(loc="upper left", fontsize=p.font_size - 2)
        ax.grid(True, linestyle=":", alpha=0.3, which="both")
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  5. 华夫饼图
# ===================================================================
def plot_waffle(p, ul, dl, palette, filename, n_grid=10):
    """
    华夫饼图 (Waffle) — 每格代表 1/(n_grid²) 的客户端占比。

    将 Upload / Download 按低/中/高三档着色，方块矩阵比饼图更易精确
    估算比例。左右两块分别对应 Upload 与 Download。
    """
    thresholds = [0, 10, 50, np.inf]
    tier_names = ["Low", "Medium", "High"]
    tier_colors = [palette["upload_fill"], "#f4d03f", palette["download_fill"]]

    def tier_fractions(arr):
        fracs = []
        for lo, hi in zip(thresholds[:-1], thresholds[1:]):
            fracs.append(np.mean((arr > lo) & (arr <= hi)))
        return fracs

    ul_f = tier_fractions(ul)
    dl_f = tier_fractions(dl)

    with plt.style.context(p.style):
        fig, axes = plt.subplots(1, 2, figsize=(9, 5), constrained_layout=True)

        for ax, fracs, title in zip(axes, [ul_f, dl_f],
                                    ["Upload Tiers", "Download Tiers"]):
            cells = [int(round(f * n_grid * n_grid)) for f in fracs]
            diff_cells = n_grid * n_grid - sum(cells)
            cells[int(np.argmax(fracs))] += diff_cells

            color_seq = []
            for c, col in zip(cells, tier_colors):
                color_seq.extend([col] * c)
            grid = np.array(color_seq[:n_grid * n_grid]).reshape((n_grid, n_grid))

            ax.imshow(grid, aspect="equal", extent=[0, n_grid, 0, n_grid])
            for v in range(n_grid + 1):
                ax.axhline(v, color="white", linewidth=1.5)
                ax.axvline(v, color="white", linewidth=1.5)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlim(0, n_grid)
            ax.set_ylim(0, n_grid)
            ax.set_title(title, fontsize=p.font_size)
            legend_handles = [
                plt.Rectangle((0, 0), 1, 1, color=col,
                              label=f"{name}: {f*100:.1f}%")
                for name, col, f in zip(tier_names, tier_colors, fracs)
            ]
            ax.legend(handles=legend_handles, loc="upper center",
                      bbox_to_anchor=(0.5, -0.02), ncol=3,
                      fontsize=p.font_size - 3, frameon=False)

        fig.suptitle("Bandwidth Tier Waffle Chart (per cell = 1%)",
                     fontsize=p.font_size + 1)
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  6. 极坐标分布玫瑰图
# ===================================================================
def plot_polar_radar(p, ul, dl, palette, filename, n_sectors=16):
    """
    极坐标雷达图 — 将带宽范围分成 n_sectors 个对数等宽扇区，每个扇区
    径向高度 = 该带宽区间内的客户端比例。UL 与 DL 两条闭合多边形叠加。

    极坐标下的「分布玫瑰图」，形态优美，方向无关，适合做封面级图示。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": "polar"})

        edges = np.logspace(np.log10(0.1), np.log10(max(ul.max(), dl.max())),
                            n_sectors + 1)
        counts_ul, _ = np.histogram(ul, bins=edges)
        counts_dl, _ = np.histogram(dl, bins=edges)
        freq_ul = counts_ul / counts_ul.sum()
        freq_dl = counts_dl / counts_dl.sum()

        theta = np.linspace(0, 2 * np.pi, n_sectors, endpoint=False)
        theta_pad = np.append(theta, theta[0])
        freq_ul_pad = np.append(freq_ul, freq_ul[0])
        freq_dl_pad = np.append(freq_dl, freq_dl[0])

        ax.plot(theta_pad, freq_ul_pad, color=palette["upload_line"],
                linewidth=1.8, label="Upload")
        ax.fill(theta_pad, freq_ul_pad, color=palette["upload_fill"], alpha=0.35)
        ax.plot(theta_pad, freq_dl_pad, color=palette["download_line"],
                linewidth=1.8, label="Download")
        ax.fill(theta_pad, freq_dl_pad, color=palette["download_fill"], alpha=0.25)

        ax.set_xticks(theta)
        labels = [f"{e0:.0f}-\n{e1:.0f}" for e0, e1 in zip(edges[:-1], edges[1:])]
        ax.set_xticklabels(labels, fontsize=p.font_size - 4)
        ax.set_rlabel_position(90)
        ax.tick_params(axis="y", labelsize=p.font_size - 3)
        ax.set_title("Polar Radar: Bandwidth Frequency Rose",
                     fontsize=p.font_size, pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.10),
                  fontsize=p.font_size - 2)
        ax.grid(True, alpha=0.4)

        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  7. Sina 图
# ===================================================================
def plot_sina(p, ul, dl, palette, filename, max_points=1500):
    """
    Sina 图 — 小提琴形状约束下的抖动散点 (Sina = Swarm + Violin + jitter)。

    散点被限制在小提琴轮廓内部，按局部密度自适应展开，既保留单点
    颗粒度又呈现整体密度形态，是 violin + strip_swarm 的优雅融合。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(6, 5))

        for i, (arr, color, line_color, label) in enumerate([
            (ul, palette["upload_fill"], palette["upload_line"], "Upload"),
            (dl, palette["download_fill"], palette["download_line"], "Download"),
        ]):
            pos = i
            pos_arr = arr[arr > 0]
            log_arr = np.log10(pos_arr)
            kde = gaussian_kde(log_arr)
            y_grid = np.linspace(log_arr.min() - 0.2, log_arr.max() + 0.2, 300)
            density = kde(y_grid)
            density_norm = density / density.max() * 0.35

            # 包络轮廓
            ax.plot(pos + density_norm, 10 ** y_grid, color=line_color,
                    linewidth=0.8, alpha=0.5)
            ax.plot(pos - density_norm, 10 ** y_grid, color=line_color,
                    linewidth=0.8, alpha=0.5)

            # 降采样散点，按局部密度限制横向展开
            if len(arr) > max_points:
                idx = np.random.choice(len(arr), max_points, replace=False)
                arr_s = arr[idx]
            else:
                arr_s = arr

            for v in arr_s:
                local_d = float(np.interp(np.log10(max(v, 1e-3)), y_grid, density_norm))
                jitter = np.random.uniform(-local_d, local_d)
                ax.scatter(pos + jitter, v, s=3, alpha=0.3, color=color, edgecolors="none")

            med = np.median(arr)
            ax.scatter(pos, med, marker="_", color="black", s=120, linewidth=2, zorder=5)

        ax.set_yscale("log")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Upload", "Download"])
        ax.set_ylabel("Bandwidth (Mbps, log scale)")
        ax.set_title("Sina Plot: Density-Constrained Scatter")
        ax.grid(True, linestyle="--", alpha=0.4, axis="y", which="both")
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  8. 点阵热力图
# ===================================================================
def plot_dot_matrix(p, ul, dl, palette, filename, n_bins=20):
    """
    点阵热力图 (Dot Matrix) — 二维网格，每格画一个圆点，
    圆点大小与颜色共同编码该 (UL, DL) 区间的客户端数。

    比 hexbin 更「轻」、更优雅，留白多，适合论文展示。
    """
    with plt.style.context(p.style):
        fig, ax = plt.subplots(figsize=(7, 6))

        mask = (ul > 0) & (dl > 0)
        log_u = np.log10(ul[mask])
        log_d = np.log10(dl[mask])

        H, xe, ye = np.histogram2d(log_u, log_d, bins=n_bins)
        cx = np.sqrt(xe[:-1] * xe[1:])
        cy = np.sqrt(ye[:-1] * ye[1:])

        xs, ys, sizes = [], [], []
        for i in range(n_bins):
            for j in range(n_bins):
                c = H[i, j]
                if c > 0:
                    xs.append(cx[i])
                    ys.append(cy[j])
                    sizes.append(c)

        sizes_arr = np.array(sizes, dtype=float)
        sizes_scaled = sizes_arr / sizes_arr.max() * 400 + 8

        sc = ax.scatter(xs, ys, s=sizes_scaled, c=sizes_arr, cmap="plasma",
                        alpha=0.75, edgecolors="white", linewidth=0.4,
                        norm=mcolors.LogNorm(vmin=1, vmax=sizes_arr.max()))
        fig.colorbar(sc, ax=ax, label="Client count (log)")

        ax.set_xscale("log")
        ax.set_yscale("log")
        lim_lo = 10 ** min(log_u.min(), log_d.min())
        lim_hi = 10 ** max(log_u.max(), log_d.max())
        ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], "k--",
                linewidth=0.8, alpha=0.5, label="y = x")

        ax.set_xlabel("Upload Bandwidth (Mbps, log)")
        ax.set_ylabel("Download Bandwidth (Mbps, log)")
        ax.set_title("Dot Matrix Heatmap (size & color = count)")
        ax.legend(loc="upper left", fontsize=p.font_size - 2)
        ax.grid(True, linestyle=":", alpha=0.3, which="both")
        p._save(filename, formats=["png", "pdf"])
        plt.close(fig)


# ===================================================================
#  注册表：供主脚本 merge 时使用
# ===================================================================
ADVANCED_PLOTS = {
    "split_violin":   ("bandwidth_split_violin", plot_split_violin),
    "halfeye":        ("bandwidth_halfeye",      plot_halfeye),
    "ecdf_diff":      ("bandwidth_ecdf_diff",    plot_ecdf_diff),
    "binned_heatmap": ("bandwidth_binned_heatmap", plot_binned_heatmap),
    "waffle":         ("bandwidth_waffle",       plot_waffle),
    "polar_radar":    ("bandwidth_polar_radar",  plot_polar_radar),
    "sina":           ("bandwidth_sina",         plot_sina),
    "dot_matrix":     ("bandwidth_dot_matrix",   plot_dot_matrix),
}
