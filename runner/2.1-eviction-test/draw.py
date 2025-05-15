import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from datetime import datetime, timedelta
import numpy as np
from utils import COLOR, LINESTYLE, MARKER, HATCH, save_figures

def load_data(data_dir='data/data-2025-4-25'):
    # 读取CPU使用率数据
    cpu_file = os.path.join(data_dir, 'CPU-usage.csv')
    cpu_data = pd.read_csv(cpu_file)
    cpu_data['Time'] = pd.to_datetime(cpu_data['Time'])

    # 读取内存使用率数据
    memory_file = os.path.join(data_dir, 'Memery-Usage.csv')
    memory_data = pd.read_csv(memory_file)
    memory_data['Time'] = pd.to_datetime(memory_data['Time'])

    # 计算内存使用百分比（除以150Mi）
    memory_data.iloc[:, 1] = memory_data.iloc[:, 1] / 150 * 100

    # 尝试读取重启数据
    restart_times = []
    restart_file = os.path.join(data_dir, 'restart.csv')
    if os.path.exists(restart_file):
        restart_data = pd.read_csv(restart_file)
        restart_data.columns = ['StartTime', 'EndTime'] if len(restart_data.columns) >= 2 else ['StartTime']

        # 转换日期时间
        restart_data['StartTime'] = pd.to_datetime(restart_data['StartTime'])
        if 'EndTime' in restart_data.columns:
            restart_data['EndTime'] = pd.to_datetime(restart_data['EndTime'])
        else:
            # 如果没有结束时间，假设重启持续5分钟
            restart_data['EndTime'] = restart_data['StartTime'] + timedelta(minutes=5)

        # 获取重启时间
        restart_times = list(zip(restart_data['StartTime'], restart_data['EndTime']))

    return cpu_data, memory_data, restart_times

def plot_usage(cpu_data, memory_data, restart_times, output_dir='output'):
    # 创建图形和坐标轴
    fig, ax = plt.subplots(figsize=(8, 4.5))

    pod_name = cpu_data.columns[1]  # 获取Pod名称

    # 获取实验开始时间（以数据中的最早时间为准）
    start_time = min(cpu_data['Time'].min(), memory_data['Time'].min())

    # 转换数据的时间为"距离开始的分钟数"
    cpu_data['Minutes'] = (cpu_data['Time'] - start_time).dt.total_seconds() / 60
    memory_data['Minutes'] = (memory_data['Time'] - start_time).dt.total_seconds() / 60

    # 转换重启时间为分钟
    restart_minutes = []
    for start, end in restart_times:
        start_min = (start - start_time).total_seconds() / 60
        end_min = (end - start_time).total_seconds() / 60
        restart_minutes.append((start_min, end_min))

    # 创建分段数据
    if restart_times:
        # 将所有时间点转换为分钟
        all_time_minutes = []
        for t in cpu_data['Time']:
            all_time_minutes.append((t - start_time).total_seconds() / 60)
        for t in memory_data['Time']:
            all_time_minutes.append((t - start_time).total_seconds() / 60)
        for start, end in restart_times:
            all_time_minutes.append((start - start_time).total_seconds() / 60)
            all_time_minutes.append((end - start_time).total_seconds() / 60)

        # 去重并排序
        all_time_minutes = sorted(list(set(all_time_minutes)))

        # 根据重启时间分段
        cpu_segments = []
        mem_segments = []

        for i in range(len(all_time_minutes) - 1):
            current_min = all_time_minutes[i]
            next_min = all_time_minutes[i+1]

            # 检查这个窗口是否在重启期间
            is_restart = False
            for start_min, end_min in restart_minutes:
                # 检查是否有重叠
                if max(current_min, start_min) < min(next_min, end_min):
                    is_restart = True
                    break

            if not is_restart:
                # 提取这个时间段的数据
                cpu_segment = cpu_data[(cpu_data['Minutes'] >= current_min) & (cpu_data['Minutes'] <= next_min)]
                mem_segment = memory_data[(memory_data['Minutes'] >= current_min) & (memory_data['Minutes'] <= next_min)]

                if not cpu_segment.empty:
                    cpu_segments.append(cpu_segment)
                if not mem_segment.empty:
                    mem_segments.append(mem_segment)

        # 绘制所有数据段
        for segment in cpu_segments:
            if len(segment) > 1:  # 至少需要两个点才能画线
                ax.plot(segment['Minutes'], segment[pod_name],
                       color=COLOR[0],
                       linestyle=LINESTYLE[0],
                       linewidth=2,
                       clip_on=False)

        for segment in mem_segments:
            if len(segment) > 1:  # 至少需要两个点才能画线
                ax.plot(segment['Minutes'], segment[pod_name],
                       color=COLOR[1],
                       linestyle=LINESTYLE[1],
                       linewidth=2,
                       clip_on=False)

        # 添加图例的代表线
        ax.plot([], [], color=COLOR[0], linestyle=LINESTYLE[0], linewidth=2, label='CPU Usage (%)')
        ax.plot([], [], color=COLOR[1], linestyle=LINESTYLE[1], linewidth=2, label='Memory Usage (%)')
    else:
        # 没有重启，直接绘制完整数据
        ax.plot(cpu_data['Minutes'], cpu_data[pod_name],
               color=COLOR[0],
               linestyle=LINESTYLE[0],
               linewidth=2,
               label='CPU Usage (%)',
               clip_on=False)
        ax.plot(memory_data['Minutes'], memory_data[pod_name],
               color=COLOR[1],
               linestyle=LINESTYLE[1],
               linewidth=2,
               label='Memory Usage (%)',
               clip_on=False)

    # 标记重启间隙
    restart_count = 0
    for start_min, end_min in restart_minutes:
        restart_count += 1
        ax.axvspan(start_min, end_min,
                  color='gray',
                  alpha=0.3,
                  hatch=HATCH[1],  # 使用utils中定义的阴影样式
                  edgecolor='0.2',
                  linewidth=0.5,
                  label='Pod Restart' if restart_count == 1 else None)

    # 设置坐标轴标签
    ax.set_xlabel('Time from experiment start (minutes)')
    ax.set_ylabel('Percentage (%)')

    # 添加网格线 (与utils风格一致，使用点状网格线)
    ax.grid(True, linestyle=':', alpha=0.7)

    # 处理图例
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))

    # 将图例放在图外，如果空间不足 (与utils中的风格一致)
    ax.legend(by_label.values(), by_label.keys(),
             loc='center left',
             bbox_to_anchor=(1, 0.5))

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 调整布局，确保所有元素都可见
    plt.tight_layout()

    # 使用utils中的save_figures函数保存为多种格式
    save_figures(fig, os.path.join(output_dir, 'eviction-test'))

def main():
    parser = argparse.ArgumentParser(description='Plot CPU and Memory usage with restart detection')
    parser.add_argument('--data-dir', default='data/data-2025-4-25', help='Directory containing CSV data files')
    parser.add_argument('--output-dir', default='output', help='Directory for output images')
    args = parser.parse_args()

    try:
        # 确保输入和输出目录存在
        os.makedirs(args.data_dir, exist_ok=True)
        os.makedirs(args.output_dir, exist_ok=True)

        cpu_data, memory_data, restart_times = load_data(args.data_dir)

        print(f"Detected {len(restart_times)} pod restarts from restart.csv")
        for i, (start, end) in enumerate(restart_times):
            print(f"Restart {i+1}: From {start} to {end}")

        plot_usage(cpu_data, memory_data, restart_times, args.output_dir)
        print(f"Plots saved to {args.output_dir} in SVG, PDF, and PNG formats")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()