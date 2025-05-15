import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os
sns.set_palette('deep')  # 或 'muted', 'colorblind'

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
    # 导入 seaborn 设置色彩方案

    colors = {
        'Round Robin': 'C0',       # '#4c72b0' 蓝色
        'Random': 'C1',            # '#dd8452' 橙色
        'Weighted RR': 'C2', # '#55a868' 绿色
        'CPU-P2C': 'C3',           # '#c44e52' 红色
        'Least Loaded': 'C4',      # '#8172b3' 紫色
        'LL-P2C': 'C5',            # '#937860' 棕色
        'YARP-P2C': 'C6',          # '#da8bc3' 粉色
        'Linear': 'C7',            # '#8c8c8c' 灰色
        'C3': 'C8',                # '#ccb974' 黄色
        'Prequal': 'C9',           # '#64b5cd' 青色
        'Ring Hash': 'C0',         # '#4c72b0' 蓝色(重复使用)
        'Maglev': 'C1',            # '#dd8452' 橙色(重复使用)
        'Ours': 'C2',              # '#55a868' 绿色(重复使用)
    }
    # 为没有定义颜色的算法分配颜色
    missing_algs = [alg for alg in algorithms if alg not in colors]
    new_colors = sns.color_palette("husl", len(missing_algs))
    for i, alg in enumerate(missing_algs):
        colors[alg] = new_colors[i]

    return colors

def get_hatch_map(algorithms):
    hatches = {
        'Round Robin': None,      # 无填充
        'Random': '/',            # 正斜线
        'Weighted RR': '\\', # 反斜线
        'CPU-P2C': '.',           # 点状图案
        'Least Loaded': 'x',      # 交叉图案
        'LL-P2C': '-',            # 水平线
        'YARP-P2C': 'o',          # 小圆圈
        'Linear': '+',            # 加号
        'C3': '//',               # 密集正斜线
        'Prequal': '\\\\',        # 密集反斜线
        'Ring Hash': None,        # 无填充(重复使用)
        'Maglev': '/',            # 正斜线(重复使用)
        'Ours': '\\',             # 反斜线(重复使用)
    }
    return hatches

# 为单个应用程序创建图表
def create_app_chart(app, data, color_map, hatch_map, to_values):
    # 获取当前应用的TO值
    to_value = to_values.get(app, 2000)

    # 设置最大延迟显示值和图表最大显示值
    max_display = min(to_value, 2000)  # 显示的最大延迟值
    chart_max = max_display + 200      # 图表的最大X值，留出TO标记空间

    # 创建图表
    fig, ax = plt.figure(figsize=(7, 5)), plt.gca()

    df = data[app]
    algorithms = df['Algorithm'].tolist()

    # 计算条形图位置 - 使用完全连续的位置
    y_positions = np.arange(len(algorithms))
    bar_height = 1.0  # 增加高度填满空间

    # 绘制P90条形图（主色）
    p90_bars = ax.barh(y_positions, df['P90'], height=bar_height,
                       color=[color_map[alg] for alg in df['Algorithm']],
                       hatch=[hatch_map[alg] for alg in df['Algorithm']],
                       alpha=1.0)

    # 绘制P99条形图（浅色延伸部分）和TO标记
    for j, (alg, p90, p99) in enumerate(zip(df['Algorithm'], df['P90'], df['P99'])):
        # 检查P99是否为TO
        if p99 >= to_value:  # 表示TO
            # 绘制到最大显示值
            p99_bar = ax.barh(y_positions[j], max_display - p90, height=bar_height,
                   left=p90, color=color_map[alg], hatch=hatch_map[alg], alpha=0.4)

            # 添加超出指示 - 确保TO标记在合适位置
            ax.text(max_display + 50, y_positions[j],
                   "TO", ha='left', va='center',
                   color='black', fontweight='bold', fontsize=12)
        else:
            # 正常绘制P99延伸部分
            p99_bar = ax.barh(y_positions[j], p99 - p90, height=bar_height,
                   left=p90, color=color_map[alg], hatch=hatch_map[alg], alpha=0.4)

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

    # 设置Y轴标签位置和标签
    ax.set_yticks(y_positions)
    ax.set_yticklabels(df['Algorithm'], fontsize=14)

    # 设置X轴范围和标签
    ax.set_xlim(0, chart_max)

    # 消除Y轴两端的空白
    ax.set_ylim(-0.5, len(algorithms) - 0.5)

    # X轴刻度 - 根据最大值调整
    tick_step = 200 if max_display <= 1000 else 500
    x_ticks = np.arange(0, chart_max + 1, tick_step)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks], fontsize=12)

    # 添加X轴标签
    ax.set_xlabel("Latency (ms)", fontsize=16)

    # 添加Y轴标签
    ax.set_ylabel("Load Balancing Algorithm", fontsize=16)

    # 创建图例，包含填充样式
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color='gray', hatch=None, alpha=1.0, label='P90 Latency'),
        plt.Rectangle((0, 0), 1, 1, color='gray', hatch=None, alpha=0.4, label='P99 Latency')
    ]

    # ax.legend(handles=legend_elements, loc='lower right', fontsize=12)

    # 移除柱状图之间的空白
    plt.tight_layout()

    # 移除图表中的上下边框以减少视觉干扰
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

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
    hatch_map = get_hatch_map(algorithms)

    # 为每个应用程序创建单独的图表
    for app in apps:
        fig = create_app_chart(app, data, color_map, hatch_map, to_values)
        plt.close(fig)

    print("所有图表已生成完毕，保存在fig目录下")

if __name__ == "__main__":
    main()