import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime
import matplotlib.dates as mdates

def process_data_and_plot(input_dir='./data/Prefect', output_dir='./fig/Prefect'):
    """
    处理数据并创建三个对齐的图表：CPU使用率、延迟和RPS

    参数:
    input_dir (str): 输入数据目录路径
    output_dir (str): 输出图像目录路径
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 读取CSV文件
    cpu_file = os.path.join(input_dir, 'CPU-usage.csv')
    latency_file = os.path.join(input_dir, 'Latency(ms).csv')
    rps_file = os.path.join(input_dir, 'RPS.csv')

    # 读取数据
    cpu_df = pd.read_csv(cpu_file)
    latency_df = pd.read_csv(latency_file)
    rps_df = pd.read_csv(rps_file)

    # 将时间列转换为datetime格式
    cpu_df['Time'] = pd.to_datetime(cpu_df['Time'])
    latency_df['Time'] = pd.to_datetime(latency_df['Time'])
    rps_df['Time'] = pd.to_datetime(rps_df['Time'])

    # 确定实验开始时间（使用所有CSV中最早的时间点）
    start_times = [
        cpu_df['Time'].min(),
        latency_df['Time'].min(),
        rps_df['Time'].min()
    ]
    experiment_start_time = min(start_times)

    # 计算与实验开始时间的差异（以分钟为单位）
    cpu_df['Elapsed'] = (cpu_df['Time'] - experiment_start_time).dt.total_seconds() / 60
    latency_df['Elapsed'] = (latency_df['Time'] - experiment_start_time).dt.total_seconds() / 60
    rps_df['Elapsed'] = (rps_df['Time'] - experiment_start_time).dt.total_seconds() / 60

    # 处理超过2000ms的延迟值 - 标记并限制为2000ms
    timeout_value = 2000  # 2000ms作为超时阈值

    # 获取延迟分位数列
    p50_col = latency_df.columns[4]  # p50列
    p90_col = latency_df.columns[3]  # p90列
    p99_col = latency_df.columns[1]  # p99列

    # 创建超时掩码（用于稍后标记超时点）
    p50_timeout = latency_df[p50_col] >= timeout_value
    p90_timeout = latency_df[p90_col] >= timeout_value
    p99_timeout = latency_df[p99_col] >= timeout_value

    # 创建处理后的延迟数据副本
    latency_df_capped = latency_df.copy()

    # 限制超过阈值的值为阈值值，同时保留原始数据用于标记
    latency_df_capped[p50_col] = latency_df[p50_col].clip(upper=timeout_value)
    latency_df_capped[p90_col] = latency_df[p90_col].clip(upper=timeout_value)
    latency_df_capped[p99_col] = latency_df[p99_col].clip(upper=timeout_value)

    # 获取RPS列 - 第二列是成功RPS，第三列是总RPS
    success_rps_col = rps_df.columns[1]  # 成功的RPS列
    total_rps_col = rps_df.columns[2]  # 总发送的RPS列

    # 设置漂亮的颜色和风格
    plt.style.use('seaborn-v0_8-whitegrid')

    # 定义美观的颜色方案
    colors = {
        'cpu_pod': '#CCCCCC',  # 浅灰色
        'cpu_avg': '#1F77B4',  # 蓝色
        'p50': '#2CA02C',      # 绿色
        'p90': '#FF7F0E',      # 橙色
        'p99': '#D62728',      # 红色
        'timeout': '#D62728',  # 红色
        'success_rps': '#2CA02C',  # 绿色
        'total_rps': '#1F77B4',    # 蓝色
        'failed_area': '#FFCCCC'   # 浅红色
    }

    # 创建一个包含三个子图的图表，设置共享X轴
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=True, dpi=300)

    # 1. CPU使用情况图
    # 获取所有pod列（排除Time和Elapsed列）
    pod_columns = [col for col in cpu_df.columns if col not in ['Time', 'Elapsed']]

    # 绘制每个pod的CPU使用率，使用半透明效果
    for pod in pod_columns:
        ax1.plot(cpu_df['Elapsed'], cpu_df[pod], color=colors['cpu_pod'], alpha=0.3, linewidth=1)

    # 计算并绘制平均CPU使用率，使用更粗的线条
    cpu_df['Average'] = cpu_df[pod_columns].mean(axis=1, skipna=True)
    ax1.plot(cpu_df['Elapsed'], cpu_df['Average'], color=colors['cpu_avg'],
             linewidth=2.5, label='Average CPU')

    ax1.set_ylabel('CPU Usage', fontsize=12)
    ax1.set_title('CPU Usage Over Time', fontsize=14, fontweight='bold')
    ax1.grid(True, linestyle='-', alpha=0.2)
    ax1.spines['top'].set_visible(False)  # 移除顶部边框
    ax1.spines['right'].set_visible(False)  # 移除右侧边框
    ax1.legend(frameon=True, framealpha=0.9)

    # 2. 延迟图 - 使用限制在2000ms的数据和更美观的风格
    # 绘制限制后的延迟数据
    ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p50_col],
             color=colors['p50'], label='p50', linewidth=2)
    ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p90_col],
             color=colors['p90'], label='p90', linewidth=2)
    ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p99_col],
             color=colors['p99'], label='p99', linewidth=2)

    # 使用优雅的方式标记超时数据点
    timeout_markers = {'p50': 'o', 'p90': 's', 'p99': '^'}

    if p50_timeout.any():
        timeouts_x = latency_df.loc[p50_timeout, 'Elapsed']
        ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p50'], color=colors['p50'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p50 timeout')

    if p90_timeout.any():
        timeouts_x = latency_df.loc[p90_timeout, 'Elapsed']
        ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p90'], color=colors['p90'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p90 timeout')

    if p99_timeout.any():
        timeouts_x = latency_df.loc[p99_timeout, 'Elapsed']
        ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p99'], color=colors['p99'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p99 timeout')

    # 设置Y轴限制，稍微超过超时阈值
    ax2.set_ylim(0, min(2200, timeout_value * 1.1))

    # 添加优雅的超时线
    ax2.axhline(y=timeout_value, color=colors['timeout'], linestyle='--', alpha=0.5, linewidth=1.5)
    ax2.text(ax2.get_xlim()[1] * 0.98, timeout_value * 1.02, 'Timeout (2000ms)',
             ha='right', va='bottom', color=colors['timeout'], alpha=0.7, fontsize=10)

    ax2.set_ylabel('Latency (ms)', fontsize=12)
    ax2.set_title('Latency Percentiles Over Time', fontsize=14, fontweight='bold')
    ax2.grid(True, linestyle='-', alpha=0.2)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # 处理图例，避免重复，并设置美观的图例样式
    handles, labels = ax2.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax2.legend(by_label.values(), by_label.keys(), frameon=True, framealpha=0.9)

    # 3. RPS图 - 使用修正的RPS数据格式
    # 绘制成功RPS
    ax3.plot(rps_df['Elapsed'], rps_df[success_rps_col], color=colors['success_rps'],
             label='Successful RPS', linewidth=2)

    # 如果总RPS和成功RPS不同，则绘制总RPS和填充失败区域
    if not rps_df[success_rps_col].equals(rps_df[total_rps_col]):
        # 绘制总RPS
        ax3.plot(rps_df['Elapsed'], rps_df[total_rps_col], color=colors['total_rps'],
                 label='Total RPS', linewidth=2)

        # 填充失败区域
        ax3.fill_between(rps_df['Elapsed'], rps_df[success_rps_col], rps_df[total_rps_col],
                         color=colors['failed_area'], alpha=0.7, label='Failed Requests')

    ax3.set_xlabel('Time from Experiment Start (minutes)', fontsize=12)
    ax3.set_ylabel('Requests per Second', fontsize=12)
    ax3.set_title('Request Rate Over Time', fontsize=14, fontweight='bold')
    ax3.grid(True, linestyle='-', alpha=0.2)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.legend(frameon=True, framealpha=0.9)

    # 整体调整布局和间距
    plt.subplots_adjust(hspace=0.3)  # 增加子图之间的空间
    fig.tight_layout()

    # 保存组合图表为PDF，高质量
    fig.savefig(os.path.join(output_dir, 'performance_metrics.pdf'),
                bbox_inches='tight', dpi=300)

    # 单独保存各个图表为PDF，同样采用美观的风格
    # CPU图
    plt.figure(figsize=(12, 5), dpi=300)
    for pod in pod_columns:
        plt.plot(cpu_df['Elapsed'], cpu_df[pod], color=colors['cpu_pod'], alpha=0.3, linewidth=1)
    plt.plot(cpu_df['Elapsed'], cpu_df['Average'], color=colors['cpu_avg'],
             linewidth=2.5, label='Average CPU')

    plt.xlabel('Time from Experiment Start (minutes)', fontsize=12)
    plt.ylabel('CPU Usage', fontsize=12)
    plt.title('CPU Usage Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='-', alpha=0.2)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.legend(frameon=True, framealpha=0.9)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'cpu_usage.pdf'), bbox_inches='tight', dpi=300)

    # 延迟图
    plt.figure(figsize=(12, 5), dpi=300)

    # 绘制限制后的延迟数据
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p50_col],
             color=colors['p50'], label='p50', linewidth=2)
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p90_col],
             color=colors['p90'], label='p90', linewidth=2)
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p99_col],
             color=colors['p99'], label='p99', linewidth=2)

    # 使用优雅的方式标记超时数据点
    if p50_timeout.any():
        timeouts_x = latency_df.loc[p50_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p50'], color=colors['p50'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p50 timeout')

    if p90_timeout.any():
        timeouts_x = latency_df.loc[p90_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p90'], color=colors['p90'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p90 timeout')

    if p99_timeout.any():
        timeouts_x = latency_df.loc[p99_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker=timeout_markers['p99'], color=colors['p99'], s=60,
                   alpha=0.8, edgecolor='white', linewidth=1, label='p99 timeout')

    # 设置Y轴限制
    plt.ylim(0, min(2200, timeout_value * 1.1))

    # 添加超时线
    plt.axhline(y=timeout_value, color=colors['timeout'], linestyle='--', alpha=0.5, linewidth=1.5)
    plt.text(plt.xlim()[1] * 0.98, timeout_value * 1.02, 'Timeout (2000ms)',
             ha='right', va='bottom', color=colors['timeout'], alpha=0.7, fontsize=10)

    plt.xlabel('Time from Experiment Start (minutes)', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency Percentiles Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='-', alpha=0.2)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)

    # 处理图例，避免重复
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), frameon=True, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'latency.pdf'), bbox_inches='tight', dpi=300)

    # RPS图 - 单独绘制
    plt.figure(figsize=(12, 5), dpi=300)

    # 绘制成功RPS
    plt.plot(rps_df['Elapsed'], rps_df[success_rps_col], color=colors['success_rps'],
             label='Successful RPS', linewidth=2)

    # 如果总RPS和成功RPS不同，则绘制总RPS和填充失败区域
    if not rps_df[success_rps_col].equals(rps_df[total_rps_col]):
        # 绘制总RPS
        plt.plot(rps_df['Elapsed'], rps_df[total_rps_col], color=colors['total_rps'],
                 label='Total RPS', linewidth=2)

        # 填充失败区域
        plt.fill_between(rps_df['Elapsed'], rps_df[success_rps_col], rps_df[total_rps_col],
                         color=colors['failed_area'], alpha=0.7, label='Failed Requests')

    plt.xlabel('Time from Experiment Start (minutes)', fontsize=12)
    plt.ylabel('Requests per Second', fontsize=12)
    plt.title('Request Rate Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='-', alpha=0.2)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.legend(frameon=True, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'rps.pdf'), bbox_inches='tight', dpi=300)

    print(f"图表已保存到 {output_dir} 目录")

if __name__ == "__main__":
    process_data_and_plot()