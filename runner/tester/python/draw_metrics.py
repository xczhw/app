import os
import argparse
import glob
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict
from config import args
from utils import safe_parse_time

def collect_metrics_paths() -> Dict[str, List[str]]:
    base_dir = "data"
    apps = [args.app] if args.app else os.listdir(base_dir)
    result = {}

    for app in apps:
        app_path = os.path.join(base_dir, app)
        if not os.path.isdir(app_path):
            continue

        # 获取所有 experiment_id 并按时间戳排序（降序）
        experiment_ids = sorted(
            [d for d in os.listdir(app_path) if os.path.isdir(os.path.join(app_path, d))],
            reverse=True
        )

        # 选取最新的若干 experiment
        num_experiments = getattr(args, 'num_experiments', 1)
        selected_experiments = experiment_ids[:num_experiments]

        for exp_id in selected_experiments:
            metrics_list = []

            # 主 metrics.csv
            main_metrics = os.path.join(app_path, exp_id, "metrics.csv")
            if os.path.isfile(main_metrics):
                metrics_list.append(main_metrics)

            # 遍历每个算法子目录
            exp_dir = os.path.join(app_path, exp_id)
            for algo in os.listdir(exp_dir):
                algo_path = os.path.join(exp_dir, algo)
                if not os.path.isdir(algo_path):
                    continue

                timestamps_file = os.path.join(algo_path, "timestamps.txt")
                if os.path.isfile(timestamps_file):
                    with open(timestamps_file, "r") as f:
                        lines = f.readlines()
                        for i in range(0, len(lines), 2):
                            if i + 1 >= len(lines):
                                break
                            start_line = lines[i].strip()
                            end_line = lines[i + 1].strip()

                            if start_line.startswith("Start:") and end_line.startswith("End:"):
                                start = start_line.split("Start:")[1].strip()
                                end = end_line.split("End:")[1].strip()
                                metrics_path = os.path.join(algo_path, f"{start}_{end}", "metrics.csv")
                                if os.path.isfile(metrics_path):
                                    metrics_list.append(metrics_path)

            result[f"{app}/{exp_id}"] = metrics_list

    return result

def parse_resource_value(value: str, resource_type: str) -> float:
    if resource_type == 'cpu':
        return float(value.replace('m', '')) / 1000.0
    elif resource_type == 'memory':
        return float(value.replace('Mi', ''))
    return 0.0

def plot_metrics_csv(metrics_path: str):
    df = pd.read_csv(metrics_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
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

def plot_overall_with_algorithms(app: str, experiment_id: str):
    metrics_path = os.path.join("data", app, experiment_id, "metrics.csv")
    df = pd.read_csv(metrics_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['cpu_usage'] = df['cpu_usage'].apply(lambda x: parse_resource_value(x, 'cpu'))
    df['memory_usage'] = df['memory_usage'].apply(lambda x: parse_resource_value(x, 'memory'))

    algo_periods = []
    base_dir = os.path.join("data", app, experiment_id)
    for algo in os.listdir(base_dir):
        algo_path = os.path.join(base_dir, algo)
        if not os.path.isdir(algo_path):
            continue

        timestamps_file = os.path.join(algo_path, "timestamps.txt")
        if os.path.isfile(timestamps_file):
            with open(timestamps_file, "r") as f:
                lines = f.readlines()
                for i in range(0, len(lines), 2):
                    if i + 1 >= len(lines):
                        break
                    start_line = lines[i].strip()
                    end_line = lines[i + 1].strip()

                    if start_line.startswith("Start:") and end_line.startswith("End:"):
                        start = safe_parse_time(start_line.split("Start:")[1].strip())
                        end = safe_parse_time(end_line.split("End:")[1].strip())
                        algo_periods.append((start, end, algo))

    os_fig_path = metrics_path.replace("data", "fig")
    os.makedirs(os.path.dirname(os_fig_path), exist_ok=True)

    # CPU + Memory overlay with algo periods
    fig, ax1 = plt.subplots()
    df_grouped = df.groupby('timestamp').sum().reset_index()
    ax1.plot(df_grouped['timestamp'], df_grouped['cpu_usage'], label='Total CPU', color='blue')
    ax1.set_ylabel('CPU (cores)', color='blue')
    ax2 = ax1.twinx()
    ax2.plot(df_grouped['timestamp'], df_grouped['memory_usage'], label='Total Memory', color='green')
    ax2.set_ylabel('Memory (Mi)', color='green')

    for start, end, algo in algo_periods:
        ax1.axvspan(start, end, alpha=0.3, label=algo)

    ax1.set_title("Overall CPU and Memory Usage with Algorithm Periods")
    fig.autofmt_xdate()
    ax1.legend(loc='upper left')
    plt.tight_layout()
    plt.savefig(os_fig_path.replace("metrics.csv", "overall_with_algos.pdf"))
    plt.close()

def main():
    collected_paths = collect_metrics_paths()
    for k, v in collected_paths.items():
        print(f"{k}:")
        app, exp_id = k.split("/")
        plot_overall_with_algorithms(app, exp_id)
        for path in v:
            print(f"  {path}")
            plot_metrics_csv(path)

if __name__ == '__main__':
    main()
