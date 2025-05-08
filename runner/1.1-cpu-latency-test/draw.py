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
    # 设置全局字体为Times New Roman和字号
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.size'] = 14  # 基本字体大小
    plt.rcParams['axes.titlesize'] = 18  # 标题字体大小
    plt.rcParams['axes.labelsize'] = 16  # 轴标签字体大小
    plt.rcParams['xtick.labelsize'] = 14  # x轴刻度标签字体大小
    plt.rcParams['ytick.labelsize'] = 14  # y轴刻度标签字体大小
    plt.rcParams['legend.fontsize'] = 16  # 图例字体大小

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

    # 创建一个包含三个子图的图表，设置共享X轴
    # fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=True)

    # # 1. CPU使用情况图
    # # 获取所有pod列（排除Time和Elapsed列）
    pod_columns = [col for col in cpu_df.columns if col not in ['Time', 'Elapsed']]

    # # 绘制每个pod的CPU使用率
    # for pod in pod_columns:
    #     ax1.plot(cpu_df['Elapsed'], cpu_df[pod], alpha=0.3, linewidth=1)

    # # 计算并绘制平均CPU使用率
    cpu_df['Average'] = cpu_df[pod_columns].mean(axis=1, skipna=True)
    # ax1.plot(cpu_df['Elapsed'], cpu_df['Average'], color='blue', linewidth=2, label='Average CPU')

    # ax1.set_ylabel('CPU Usage')
    # ax1.set_title('CPU Usage Over Time')
    # ax1.grid(True, linestyle='--', alpha=0.7)
    # ax1.legend()

    # # 2. 延迟图 - 使用限制在2000ms的数据
    # # 绘制限制后的延迟数据
    # ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p50_col],
    #          color='green', label='p50')
    # ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p90_col],
    #          color='orange', label='p90')
    # ax2.plot(latency_df_capped['Elapsed'], latency_df_capped[p99_col],
    #          color='red', label='p99')

    # # 标记超时数据点
    # if p50_timeout.any():
    #     timeouts_x = latency_df.loc[p50_timeout, 'Elapsed']
    #     ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
    #                marker='x', color='green', s=40, label='p50 timeout')

    # if p90_timeout.any():
    #     timeouts_x = latency_df.loc[p90_timeout, 'Elapsed']
    #     ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
    #                marker='x', color='orange', s=40, label='p90 timeout')

    # if p99_timeout.any():
    #     timeouts_x = latency_df.loc[p99_timeout, 'Elapsed']
    #     ax2.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
    #                marker='x', color='red', s=40, label='p99 timeout')

    # # 设置Y轴限制，稍微超过超时阈值，以便能看到超时标记
    # ax2.set_ylim(0, min(2200, timeout_value * 1.1))

    # # 添加超时线
    # ax2.axhline(y=timeout_value, color='r', linestyle='--', alpha=0.5)
    # ax2.text(ax2.get_xlim()[1] * 0.98, timeout_value * 1.02, 'Timeout (2000ms)',
    #          ha='right', va='bottom', color='r', alpha=0.7)

    # ax2.set_ylabel('Latency (ms)')
    # ax2.set_title('Latency Percentiles Over Time')
    # ax2.grid(True, linestyle='--', alpha=0.7)

    # # 处理图例，避免重复
    # handles, labels = ax2.get_legend_handles_labels()
    # by_label = dict(zip(labels, handles))
    # ax2.legend(by_label.values(), by_label.keys())

    # # 3. RPS图 - 使用修正的RPS数据格式
    # # 绘制成功RPS和总RPS
    # ax3.plot(rps_df['Elapsed'], rps_df[success_rps_col], color='green',
    #          label='Successful RPS', linewidth=2)
    # ax3.plot(rps_df['Elapsed'], rps_df[total_rps_col], color='blue',
    #          label='Total RPS', linewidth=2)

    # # 如果两者有差异，填充差异区域
    # if not rps_df[success_rps_col].equals(rps_df[total_rps_col]):
    #     ax3.fill_between(rps_df['Elapsed'], rps_df[total_rps_col], rps_df[success_rps_col],
    #                      color='red', alpha=0.3, label='Failed Requests')

    # ax3.set_xlabel('Time from Experiment Start (minutes)')
    # ax3.set_ylabel('Requests per Second')
    # ax3.set_title('Request Rate Over Time')
    # ax3.grid(True, linestyle='--', alpha=0.7)
    # ax3.legend()

    # # 调整布局
    # plt.tight_layout()

    # # 保存组合图表为PDF
    # fig.savefig(os.path.join(output_dir, 'performance_metrics.pdf'), bbox_inches='tight')

    # 单独保存各个图表为PDF
    # CPU图
    plt.figure(figsize=(8, 4))
    for pod in pod_columns:
        plt.plot(cpu_df['Elapsed'], cpu_df[pod], alpha=0.3, linewidth=1)
    plt.plot(cpu_df['Elapsed'], cpu_df['Average'], color='blue', linewidth=2, label='Average CPU usage')
    plt.xlabel('Time from Experiment Start (minutes)')
    plt.ylabel('CPU Usage (%)')

    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'cpu_usage.pdf'), bbox_inches='tight')

    # 延迟图
    plt.figure(figsize=(8, 4))

    # 绘制限制后的延迟数据
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p50_col],
             color='green', label='p50 latency')
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p90_col],
             color='orange', label='p90 latency')
    plt.plot(latency_df_capped['Elapsed'], latency_df_capped[p99_col],
             color='red', label='p99 latency')

    # 标记超时数据点
    if p50_timeout.any():
        timeouts_x = latency_df.loc[p50_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker='x', color='red', s=40)

    if p90_timeout.any():
        timeouts_x = latency_df.loc[p90_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker='x', color='red', s=40)

    if p99_timeout.any():
        timeouts_x = latency_df.loc[p99_timeout, 'Elapsed']
        plt.scatter(timeouts_x, [timeout_value] * len(timeouts_x),
                   marker='x', color='red', s=40, label='timeout')

    # 设置Y轴限制
    plt.ylim(0, min(2200, timeout_value * 1.1))

    # 添加超时线
    plt.axhline(y=timeout_value, color='r', linestyle='--', alpha=0.5)
    plt.text(plt.xlim()[1] * 0.98, timeout_value * 1.02, 'Timeout (2000ms)',
             ha='right', va='bottom', color='r', alpha=0.7)

    plt.xlabel('Time from Experiment Start (minutes)')
    plt.ylabel('Latency (ms)')

    plt.grid(True, linestyle='--', alpha=0.7)

    # 处理图例，避免重复
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())

    plt.savefig(os.path.join(output_dir, 'latency.pdf'), bbox_inches='tight')

    # RPS图 - 单独绘制
    plt.figure(figsize=(8, 4))
    plt.plot(rps_df['Elapsed'], rps_df[success_rps_col], color='#00B050',
             label='Successful RPS', linewidth=2)
    plt.plot(rps_df['Elapsed'], rps_df[total_rps_col], color='#8064A2',
             label='Total RPS', linewidth=2)

    # 如果两者有差异，填充差异区域
    if not rps_df[success_rps_col].equals(rps_df[total_rps_col]):
        plt.fill_between(rps_df['Elapsed'], rps_df[total_rps_col], rps_df[success_rps_col],
                         color='#FFD6D6', alpha=0.3, label='Failed Requests')

    plt.xlabel('Time from Experiment Start (minutes)')
    plt.ylabel('Requests per Second')

    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'rps.pdf'), bbox_inches='tight')

    print(f"图表已保存到 {output_dir} 目录")

if __name__ == "__main__":
    process_data_and_plot()