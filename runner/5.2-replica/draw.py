import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import COLOR, LINESTYLE, MARKER, HATCH, save_figures

def create_sample_data():
    """Create sample data."""
    data = {
        "strategy": ["Random", "RoundRobin", "WeightRR", "CPU-P2C", "LL", "LL-P2C", "YARP-P2C",
                     "Linear", "C3", "Prequal", "RingHash", "Maglev", "Ours"],
        "online_boutique_replicas": [8.7, 8.5, 6.4, 6.2, 6.5, 6.3, 5.9, 5.7, 5.4, 5.2, 5.8, 5.7, 3.9],
        "online_boutique_std": [0.4, 0.3, 0.3, 0.2, 0.3, 0.2, 0.3, 0.2, 0.2, 0.3, 0.3, 0.2, 0.1],
        "social_network_replicas": [12.3, 12.1, 9.8, 9.5, 9.9, 9.6, 8.8, 8.4, 8.1, 7.9, 8.6, 8.5, 5.7],
        "social_network_std": [0.5, 0.4, 0.4, 0.3, 0.4, 0.3, 0.4, 0.3, 0.3, 0.4, 0.4, 0.3, 0.2],
        "train_ticket_replicas": [18.5, 18.2, 14.2, 13.8, 14.5, 14.0, 12.7, 12.1, 11.5, 11.2, 12.5, 12.3, 8.1],
        "train_ticket_std": [0.7, 0.6, 0.5, 0.5, 0.6, 0.5, 0.6, 0.4, 0.4, 0.5, 0.5, 0.4, 0.3]
    }
    return pd.DataFrame(data)

def plot_resource_usage():
    """Plot resource usage metrics for different load balancing strategies across applications."""
    # 创建样本数据
    data = create_sample_data()

    # 确保输出目录存在
    os.makedirs('fig', exist_ok=True)

    fontsize = 16
    # 设置全局字体和字号
    plt.rcParams.update({
        'text.usetex': False,
        'font.family': 'serif',
        'font.serif': 'Times New Roman',
        'font.size': fontsize,
        'legend.fontsize': fontsize,
        'axes.labelsize': fontsize,
        'axes.titlesize': fontsize,
        'xtick.labelsize': fontsize,
        'ytick.labelsize': fontsize,
        'lines.linewidth': 2,
        'lines.markersize': fontsize,
        'svg.fonttype': 'none',
    })

    # 定义应用
    apps = ["online_boutique", "social_network", "train_ticket"]
    app_labels = ["Online Boutique", "Social Network", "Train Ticket"]

    # 提取策略名称
    strategies = data["strategy"].tolist()

    # "Ours"策略的索引
    our_approach_idx = strategies.index("Ours")

    # 创建三个独立的图
    fig_width = 6
    fig_height = 5

    for i, app in enumerate(apps):
        # 创建一个新的图
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        # 准备数据
        values = data[f"{app}_replicas"].tolist()
        errors = data[f"{app}_std"].tolist()

        # 获取基准线（除我们方法外的最佳表现策略）
        other_values = [v for j, v in enumerate(values) if j != our_approach_idx]
        best_baseline = min(other_values)
        our_value = values[our_approach_idx]
        reduction_pct = 100 * (best_baseline - our_value) / best_baseline

        # 使用COLOR数组中的颜色
        bar_colors = [COLOR[j % len(COLOR)] for j in range(len(strategies))]

        bar_hatchs = [HATCH[j % len(HATCH)] for j in range(len(strategies))]

        # 创建条形图（去掉间隔）
        bars = ax.bar(np.arange(len(strategies)), values, width=1.0,
                     color=bar_colors, hatch=bar_hatchs, yerr=errors, capsize=4, edgecolor='black', linewidth=0.5)

        # # 突出显示我们的方法
        # bars[our_approach_idx].set_edgecolor('black')
        # bars[our_approach_idx].set_linewidth(2)

        # # 添加减少百分比标注
        # ax.annotate(f"-{reduction_pct:.1f}%",
        #            xy=(our_approach_idx, our_value),
        #            xytext=(0, -25),
        #            textcoords="offset points",
        #            ha='center', va='top',
        #            fontweight='bold',
        #            color='red',
        #            fontsize=14)

        # 设置标题和标签
        # ax.set_title(app_labels[i], fontsize=18)
        ax.set_ylabel('Average Number of Active Replicas', fontsize=16)
        ax.set_xticks(np.arange(len(strategies)))
        ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=16)

        # 添加网格线
        ax.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)

        # 确保Y轴从0开始
        ax.set_ylim(bottom=0)

        # 调整布局
        plt.tight_layout()

        # 保存图表
        save_figures(fig, f'fig/resource_usage_{app}')

    print("Figures saved to fig/resource_usage_*.pdf, .png, and .svg")

if __name__ == "__main__":
    plot_resource_usage()