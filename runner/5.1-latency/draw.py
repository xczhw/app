import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os

# 确保fig目录存在
if not os.path.exists('fig'):
    os.makedirs('fig')

# 读取CSV文件
def load_data(apps, to_values):
    data = {}
    for app in apps:
        # 从data目录读取文件
        file_path = os.path.join('data', f"{app}.csv")

        # 读取CSV，包含表头
        df = pd.read_csv(file_path)

        # 将TO替换为app对应的to_value
        to_value = to_values.get(app, 2000)  # 默认2000
        df = df.replace('TO', to_value)

        # 确保数据类型为数值
        df['P90'] = pd.to_numeric(df['P90'])
        df['P99'] = pd.to_numeric(df['P99'])

        data[app] = df
    return data

# 设置颜色方案
def get_color_map(algorithms):
    # 定义与参考图类似的颜色
    colors = {
        'Round Robin': '#AA0000',  # 深红色
        'Random': '#885500',       # 棕色
        'Weighted Round Robin': '#DDAA00',  # 金色
        'CPU-P2C': '#AAAA00',      # 黄色
        'Least Loaded': '#008800',  # 绿色
        'LL-P2C': '#0055DD',       # 蓝色
        'YARP-P2C': '#880088',     # 紫色
        'Linear': '#888888',       # 灰色
        'C3': '#008888',           # 青色
        'Prequal': '#AAAAAA',      # 浅灰色
        'Ring Hash': '#DD5500',    # 橙色
        'Maglev': '#00AAAA',       # 浅青色
    }

    # 为没有定义颜色的算法分配颜色
    missing_algs = [alg for alg in algorithms if alg not in colors]
    new_colors = sns.color_palette("husl", len(missing_algs))
    for i, alg in enumerate(missing_algs):
        colors[alg] = new_colors[i]

    return colors

# 为单个应用程序创建图表
def create_app_chart(app, data, color_map, to_values):
    # 获取当前应用的TO值
    to_value = to_values.get(app, 2000)

    # 设置最大延迟显示值和图表最大显示值
    max_display = min(to_value, 2000)  # 显示的最大延迟值
    chart_max = max_display + 200      # 图表的最大X值，留出TO标记空间

    # 创建图表
    fig, ax = plt.figure(figsize=(14, 10)), plt.gca()

    df = data[app]
    algorithms = df['Algorithm'].tolist()

    # 计算条形图位置
    bar_height = 0.7
    y_positions = np.arange(len(algorithms))

    # 绘制P90条形图（主色）
    p90_bars = ax.barh(y_positions, df['P90'], height=bar_height,
                       color=[color_map[alg] for alg in df['Algorithm']], alpha=1.0)

    # 绘制P99条形图（浅色延伸部分）和TO标记
    for j, (alg, p90, p99) in enumerate(zip(df['Algorithm'], df['P90'], df['P99'])):
        # 检查P99是否为TO
        if p99 >= to_value:  # 表示TO
            # 绘制到最大显示值
            p99_bar = ax.barh(y_positions[j], max_display - p90, height=bar_height,
                   left=p90, color=color_map[alg], alpha=0.4)

            # 添加超出指示 - 确保TO标记在合适位置
            ax.text(max_display + 50, y_positions[j],
                   "TO", ha='left', va='center',
                   color='black', fontweight='bold', fontsize=12)
        else:
            # 正常绘制P99延伸部分
            p99_bar = ax.barh(y_positions[j], p99 - p90, height=bar_height,
                   left=p90, color=color_map[alg], alpha=0.4)

            # 添加P99数值标签 - 只在P99延伸部分较长时显示
            if p99 - p90 > 200:
                # 确保P99标签显示在延伸部分的中心
                ax.text(p90 + (p99 - p90)/2, y_positions[j],
                       f"{int(p99)}", ha='center', va='center',
                       color='black', fontweight='bold', fontsize=12)

    # 添加P90数值标签
    for j, bar in enumerate(p90_bars):
        width = bar.get_width()
        if width > 60:  # 只在条形足够宽时添加标签
            # 确保P90标签显示在P90柱形的中心
            ax.text(width / 2, y_positions[j],
                   f"{int(width)}", ha='center', va='center',
                   color='white', fontweight='bold', fontsize=12)

    # 设置Y轴标签
    ax.set_yticks(y_positions)
    ax.set_yticklabels(df['Algorithm'], fontsize=14)

    # 添加网格线
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    # 设置X轴范围和标签
    ax.set_xlim(0, chart_max)

    # X轴刻度 - 根据最大值调整
    tick_step = 200 if max_display <= 1000 else 500
    x_ticks = np.arange(0, chart_max + 1, tick_step)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks], fontsize=12)

    # 添加X轴标签
    ax.set_xlabel("Latency (ms)", fontsize=16)

    # 添加Y轴标签
    ax.set_ylabel("Load Balancing Algorithm", fontsize=16)

    # 创建图例
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color='gray', alpha=1.0, label='P90 Latency'),
        plt.Rectangle((0, 0), 1, 1, color='gray', alpha=0.4, label='P99 Latency')
    ]

    ax.legend(handles=legend_elements, loc='lower right', fontsize=12)

    plt.tight_layout()

    # 保存图表为PDF
    file_path = os.path.join('fig', f"{app}_latency.pdf")
    plt.savefig(file_path, bbox_inches='tight')
    print(f"已保存图表: {file_path}")

    return fig

# 主函数
def main():
    # 应用程序名称
    apps = ["OnlineBoutique", "SocialNetwork", "TrainTicket"]

    # 为每个应用定义TO值（超时阈值，毫秒）
    to_values = {
        "OnlineBoutique": 1000,  # 例如，设置OnlineBoutique的TO值为1000ms
        "SocialNetwork": 1500,   # SocialNetwork的TO值为1500ms
        "TrainTicket": 2000      # TrainTicket的TO值为2000ms
    }

    # 读取数据，传入TO值
    data = load_data(apps, to_values)

    # 获取所有算法名称（从第一个应用的数据中）
    algorithms = data[apps[0]]['Algorithm'].tolist()

    # 创建颜色映射
    color_map = get_color_map(algorithms)

    # 为每个应用程序创建单独的图表
    for app in apps:
        fig = create_app_chart(app, data, color_map, to_values)
        plt.close(fig)

    print("所有图表已生成完毕，保存在fig目录下")

if __name__ == "__main__":
    main()