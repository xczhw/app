import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from datetime import datetime, timedelta
import numpy as np
import matplotlib

# 设置全局字体为Times New Roman和字号
matplotlib.rcParams.update({
    'font.family': 'Times New Roman',
    'font.size': 14,
    'axes.labelsize': 18,
    'axes.titlesize': 20,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 14
})

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
    # 保持原来的比例，但增加整体大小以适应更大的字体
    plt.figure(figsize=(12, 6))

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

    ax = plt.gca()

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

        # 绘制所有数据段，增加线宽以增强可见性
        for segment in cpu_segments:
            if len(segment) > 1:  # 至少需要两个点才能画线
                ax.plot(segment['Minutes'], segment[pod_name], 'b-', linewidth=2.5)

        for segment in mem_segments:
            if len(segment) > 1:  # 至少需要两个点才能画线
                ax.plot(segment['Minutes'], segment[pod_name], 'r-', linewidth=2.5)

        # 添加图例的代表线
        ax.plot([], [], 'b-', linewidth=2.5, label='CPU Usage (%)')
        ax.plot([], [], 'r-', linewidth=2.5, label='Memory Usage (%)')
    else:
        # 没有重启，直接绘制完整数据
        ax.plot(cpu_data['Minutes'], cpu_data[pod_name], 'b-', linewidth=2.5, label='CPU Usage (%)')
        ax.plot(memory_data['Minutes'], memory_data[pod_name], 'r-', linewidth=2.5, label='Memory Usage (%)')

    # 标记重启间隙
    restart_count = 0
    for start_min, end_min in restart_minutes:
        restart_count += 1
        plt.axvspan(start_min, end_min, color='gray', alpha=0.3, label='Pod Restart' if restart_count == 1 else None)

    # 设置标题和标签，使用更大的字体
    plt.title('CPU and Memory Usage', pad=15)
    plt.xlabel('Time from experiment start (minutes)', labelpad=10)
    plt.ylabel('Percentage (%)', labelpad=10)
    plt.grid(True, linestyle='--', alpha=0.7)

    # 创建一个包含所有项目的图例，使用更大的字体
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right', framealpha=0.9)

    # 保存图片，增加DPI以提高质量
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 先使用tight_layout确保所有元素都可见
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # 留出空间给底部的注释

    plt.savefig(os.path.join(output_dir, 'eviction-test.pdf'), format='pdf', dpi=600, bbox_inches='tight')
    # plt.show()

def main():
    parser = argparse.ArgumentParser(description='Plot CPU and Memory usage with restart detection')
    parser.add_argument('--data-dir', default='data/data-2025-4-25', help='Directory containing CSV data files')
    parser.add_argument('--output-dir', default='output', help='Directory for output images')
    args = parser.parse_args()

    try:
        cpu_data, memory_data, restart_times = load_data(args.data_dir)

        print(f"Detected {len(restart_times)} pod restarts from restart.csv")
        for i, (start, end) in enumerate(restart_times):
            print(f"Restart {i+1}: From {start} to {end}")

        plot_usage(cpu_data, memory_data, restart_times, args.output_dir)
        print(f"Plot saved to {args.output_dir}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()