import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from utils import COLOR, LINESTYLE, MARKER, HATCH, save_figures

# 设置全局字体和字号
plt.rcParams.update({
    'text.usetex': False,
    'font.family': 'serif',
    'font.serif': 'Times New Roman',
    'font.size': 16,
    'legend.fontsize': 16,
    'axes.labelsize': 16,
    'axes.spines.top': False,
    'axes.spines.right': True,  # 启用右侧轴线用于第二个Y轴
    'lines.linewidth': 2,
    'lines.markersize': 10,
    'svg.fonttype': 'none',
})

# 图例样式 - 黑色边框不透明
legend_props = {
    'frameon': True,      # 显示边框
    'framealpha': 1.0,    # 完全不透明
    'edgecolor': 'black', # 黑色边框
    'facecolor': 'white'  # 白色背景
}

# 确保输出目录存在
os.makedirs('fig', exist_ok=True)

# 图表尺寸
fig_width = 9
fig_height = 4.5

def plot_cpu_memory_usage():
    # 读取CSV数据
    try:
        cpu_data = pd.read_csv('data/cpu.csv')
        mem_data = pd.read_csv('data/mem.csv')
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保data/cpu.csv和data/mem.csv文件存在")
        return

    # 检查数据列
    if 'Time' not in cpu_data.columns or len(cpu_data.columns) < 2:
        print("错误: CPU数据文件格式不正确，应包含'Time'列和至少一个数据列")
        return

    if 'Time' not in mem_data.columns or len(mem_data.columns) < 3:
        print("错误: 内存数据文件格式不正确，应包含'Time'列，内存使用列和Replicas列")
        return

    # 获取列名
    cpu_column = cpu_data.columns[1]
    mem_column = mem_data.columns[1]
    replica_column = mem_data.columns[2]  # 假设第三列是Replicas

    # 确保replica列存在
    if replica_column not in mem_data.columns:
        print(f"错误: 找不到Replicas列: {replica_column}")
        return

    # 转换时间字符串为datetime格式
    cpu_data['Time'] = pd.to_datetime(cpu_data['Time'])
    mem_data['Time'] = pd.to_datetime(mem_data['Time'])

    # 找到最早的时间点
    start_time = min(cpu_data['Time'].min(), mem_data['Time'].min())

    # 计算每个时间点距离开始时间的分钟数
    cpu_data['Minutes'] = (cpu_data['Time'] - start_time).dt.total_seconds() / 60
    mem_data['Minutes'] = (mem_data['Time'] - start_time).dt.total_seconds() / 60

    # 将CPU数据从millicores转换为cores (除以1000)
    cpu_data[cpu_column] = cpu_data[cpu_column] / 1000

    # 创建图表
    fig, ax1 = plt.subplots(figsize=(fig_width, fig_height))

    # 找出replica变化的点
    replica_changes = []
    prev_replica = None

    for i, row in mem_data.iterrows():
        current_replica = row[replica_column]
        if prev_replica is None or current_replica != prev_replica:
            replica_changes.append((row['Minutes'], current_replica))
            prev_replica = current_replica

    # 添加最后一个时间点，确保覆盖整个时间范围
    if len(replica_changes) > 0:
        replica_changes.append((mem_data['Minutes'].max(), replica_changes[-1][1]))

    # 只为1和5个replicas的区域添加灰色背景
    highlight_replicas = [1, 5]
    for i in range(len(replica_changes) - 1):
        start_x = replica_changes[i][0]
        end_x = replica_changes[i+1][0]
        replica_count = replica_changes[i][1]

        if replica_count in highlight_replicas:
            ax1.axvspan(start_x, end_x, alpha=0.2, color='gray', zorder=0)

    # 第一个Y轴 - CPU使用率
    ax1.set_xlabel('Elapsed Time')
    ax1.set_ylabel('CPU Usage (cores)', color=COLOR[0])
    ax1.plot(cpu_data['Minutes'], cpu_data[cpu_column],
             color=COLOR[0], linestyle=LINESTYLE[0], linewidth=2,
             label='CPU Usage (cores)')
    ax1.tick_params(axis='y', labelcolor=COLOR[0])

    # 第二个Y轴 - 内存使用
    ax2 = ax1.twinx()
    ax2.set_ylabel('Memory Usage (MiB)', color=COLOR[1])
    ax2.plot(mem_data['Minutes'], mem_data[mem_column],
             color=COLOR[1], linestyle=LINESTYLE[1], linewidth=2,
             label='Memory Usage (MiB)')
    ax2.tick_params(axis='y', labelcolor=COLOR[1])

    # 添加网格线到底层 (只在左侧Y轴上)
    ax1.grid(True, linestyle='--', alpha=0.7, zorder=0)

    # 将两个图例放在右下角
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(lines1 + lines2, labels1 + labels2,
              loc='lower right', **legend_props)

    # 调整布局
    fig.tight_layout()

    # 保存图表
    save_figures(fig, 'fig/cpu_memory_usage')

    print("CPU和内存使用图表已保存到 fig/cpu_memory_usage.pdf, .png 和 .svg")

if __name__ == "__main__":
    plot_cpu_memory_usage()