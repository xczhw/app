import os
import argparse
import glob
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from utils import safe_parse_time, read_timestamps

# def collect_metrics_paths() -> Dict[str, List[str]]:
#     base_dir = "data"
#     apps = [args.app] if args.app else os.listdir(base_dir)
#     result = {}

#     for app in apps:
#         app_path = os.path.join(base_dir, app)
#         if not os.path.isdir(app_path):
#             continue

#         # 获取所有 experiment_id 并按时间戳排序（降序）
#         experiment_ids = sorted(
#             [d for d in os.listdir(app_path) if os.path.isdir(os.path.join(app_path, d))],
#             reverse=True
#         )

#         # 选取最新的若干 experiment
#         num_experiments = getattr(args, 'num_experiments', 1)
#         selected_experiments = experiment_ids[:num_experiments]

#         for exp_id in selected_experiments:
#             metrics_list = []

#             # 主 metrics.csv
#             main_metrics = os.path.join(app_path, exp_id, "metrics.csv")
#             if os.path.isfile(main_metrics):
#                 metrics_list.append(main_metrics)

#             # 遍历每个算法子目录
#             exp_dir = os.path.join(app_path, exp_id)
#             for algo in os.listdir(exp_dir):
#                 algo_path = os.path.join(exp_dir, algo)
#                 if not os.path.isdir(algo_path):
#                     continue

#                 timestamps_file = os.path.join(algo_path, "timestamps.txt")
#                 if os.path.isfile(timestamps_file):
#                     with open(timestamps_file, "r") as f:
#                         lines = f.readlines()
#                         for i in range(0, len(lines), 2):
#                             if i + 1 >= len(lines):
#                                 break
#                             start_line = lines[i].strip()
#                             end_line = lines[i + 1].strip()

#                             if start_line.startswith("Start:") and end_line.startswith("End:"):
#                                 start = start_line.split("Start:")[1].strip()
#                                 end = end_line.split("End:")[1].strip()
#                                 metrics_path = os.path.join(algo_path, f"{start}_{end}", "metrics.csv")
#                                 if os.path.isfile(metrics_path):
#                                     metrics_list.append(metrics_path)

#             result[f"{app}/{exp_id}"] = metrics_list

#     return result

def parse_resource_value(value: str, resource_type: str) -> float:
    if resource_type == 'cpu':
        return float(value.replace('m', '')) / 1000.0
    elif resource_type == 'memory':
        return float(value.replace('Mi', ''))
    return 0.0

def plot_metrics_csv(metrics_path: str):
    df = pd.read_csv(metrics_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='us')
    df['cpu_usage'] = df['cpu_usage'].apply(lambda x: parse_resource_value(x, 'cpu'))
    df['memory_usage'] = df['memory_usage'].apply(lambda x: parse_resource_value(x, 'memory'))

    os_fig_path = metrics_path.replace("data", "fig")
    os.makedirs(os.path.dirname(os_fig_path), exist_ok=True)

    # CPU usage over time
    plt.figure()
    for pod, pod_df in df.groupby('pod_name'):
        plt.plot(pod_df['timestamp'], pod_df['cpu_usage'], label=pod)
    plt.xlabel("Time")
    plt.ylabel("CPU (cores)")
    plt.title("CPU Usage Over Time")
    plt.legend(fontsize="small", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os_fig_path.replace("metrics.csv", "cpu_time.pdf"))
    plt.close()

    # Memory usage over time
    plt.figure()
    for pod, pod_df in df.groupby('pod_name'):
        plt.plot(pod_df['timestamp'], pod_df['memory_usage'], label=pod)
    plt.xlabel("Time")
    plt.ylabel("Memory (Mi)" )
    plt.title("Memory Usage Over Time")
    plt.legend(fontsize="small", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os_fig_path.replace("metrics.csv", "memory_time.pdf"))
    plt.close()

    # CPU usage boxplot
    plt.figure()
    df.boxplot(column='cpu_usage', by='pod_name', rot=90)
    plt.title("CPU Usage Distribution")
    plt.suptitle("")
    plt.ylabel("CPU (cores)")
    plt.tight_layout()
    plt.savefig(os_fig_path.replace("metrics.csv", "cpu_box.pdf"))
    plt.close()

    # Memory usage boxplot
    plt.figure()
    df.boxplot(column='memory_usage', by='pod_name', rot=90)
    plt.title("Memory Usage Distribution")
    plt.suptitle("")
    plt.ylabel("Memory (Mi)")
    plt.tight_layout()
    plt.savefig(os_fig_path.replace("metrics.csv", "memory_box.pdf"))
    plt.close()

def plot_overall_with_algorithms(experiment_dir: str):
    fig_cpu, ax_cpu = plt.subplots(figsize=(12, 6))
    fig_mem, ax_mem = plt.subplots(figsize=(12, 6))

    algo_periods = []

    for algo in os.listdir(experiment_dir):
        algo_path = os.path.join(experiment_dir, algo)
        metrics_path = os.path.join(algo_path, "metrics.csv")
        timestamps_path = os.path.join(algo_path, "timestamps.txt")

        if not os.path.isdir(algo_path) or not os.path.isfile(metrics_path) or not os.path.isfile(timestamps_path):
            continue

        # 加载 metrics.csv
        df = pd.read_csv(metrics_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='us')
        df['cpu_usage'] = df['cpu_usage'].apply(lambda x: parse_resource_value(x, 'cpu'))
        df['memory_usage'] = df['memory_usage'].apply(lambda x: parse_resource_value(x, 'memory'))
        df_grouped = df.groupby('timestamp').sum().reset_index()

        # 加载 timestamps.txt
        start, end = read_timestamps(timestamps_path)
        start = pd.to_datetime(start, unit='us')
        end = pd.to_datetime(end, unit='us')
        algo_periods.append((start, end, algo))

        # 画 CPU 图
        ax_cpu.plot(df_grouped['timestamp'], df_grouped['cpu_usage'], label=f'{algo}')
        ax_cpu.axvspan(start, end, alpha=0.15, label=f'{algo} period')

        # 画 Memory 图
        ax_mem.plot(df_grouped['timestamp'], df_grouped['memory_usage'], label=f'{algo}')
        ax_mem.axvspan(start, end, alpha=0.15, label=f'{algo} period')

    # 设置 CPU 图样式
    ax_cpu.set_ylabel("CPU Usage (cores)")
    ax_cpu.set_title("CPU Usage by Algorithm (with Periods)")
    ax_cpu.legend(fontsize=9, loc="upper left")
    ax_cpu.grid(True)
    fig_cpu.autofmt_xdate()
    fig_cpu.tight_layout()

    # 设置 Memory 图样式
    ax_mem.set_ylabel("Memory Usage (Mi)")
    ax_mem.set_title("Memory Usage by Algorithm (with Periods)")
    ax_mem.legend(fontsize=9, loc="upper left")
    ax_mem.grid(True)
    fig_mem.autofmt_xdate()
    fig_mem.tight_layout()

    # 保存图像
    base_fig_path = experiment_dir.replace("data", "fig")
    os.makedirs(base_fig_path, exist_ok=True)
    fig_cpu.savefig(os.path.join(base_fig_path, "overall_cpu_with_algos.pdf"), dpi=300, bbox_inches="tight")
    fig_mem.savefig(os.path.join(base_fig_path, "overall_memory_with_algos.pdf"), dpi=300, bbox_inches="tight")

    plt.close(fig_cpu)
    plt.close(fig_mem)

def main(experiment_dir):
    plot_overall_with_algorithms(experiment_dir)
    for algo in os.listdir(experiment_dir):
        metrics_path = os.path.join(experiment_dir, algo, "metrics.csv")
        plot_metrics_csv(metrics_path)

if __name__ == '__main__':
    experiment_dir = "data/onlineBoutique/1744274328721745"
    main(experiment_dir)
