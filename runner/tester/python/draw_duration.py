import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import gzip
import pickle
from trace_model import Trace
import utils

def load_trace_data_from_dir(algo_dir: str) -> list:
    """
    从某个算法目录加载 trace_data.pkl.gz 文件，并构造 Trace 对象列表
    """
    trace_file = os.path.join(algo_dir, "trace_data.pkl.gz")
    if not os.path.isfile(trace_file):
        print(f"❌ 找不到 trace_data.pkl.gz: {trace_file}")
        return []

    with gzip.open(trace_file, "rb") as f:
        trace_data = pickle.load(f)

    return trace_data

def load_all_traces_from_experiment(experiment_dir: str) -> dict:
    """
    遍历 experiment_dir 下所有子目录（每个子目录是一个算法名），
    使用函数2加载每个子目录的数据，返回 dict：{algo_name: List[Trace]}
    """
    algo_trace_dict = {}

    for algo in os.listdir(experiment_dir):
        algo_path = os.path.join(experiment_dir, algo)
        if not os.path.isdir(algo_path):
            continue

        traces = load_trace_data_from_dir(algo_path)
        if traces:
            algo_trace_dict[algo] = traces

    return algo_trace_dict

def plot_trace_duration_over_time(algo_trace_dict: dict, fig_dir: str):
    """
    横轴是 start_time，纵轴是 total_duration，算法用阴影区分。
    """
    plt.figure(figsize=(12, 6))

    for algo, traces in algo_trace_dict.items():
        data = [(t.start_time, t.total_duration) for t in traces if t.start_time and t.total_duration]
        if not data:
            continue

        data.sort()
        times, durations = zip(*data)
        times = pd.to_datetime(times, unit='us')

        plt.plot(times, durations, label=algo)
        plt.fill_between(times, durations, alpha=0.1, label=f"{algo} (range)")

    plt.xlabel("Start Time")
    plt.ylabel("Total Duration (μs)")
    plt.title("Trace Duration Over Time")
    plt.legend()
    plt.grid()
    os.makedirs(fig_dir, exist_ok=True)
    plt.savefig(os.path.join(fig_dir, "trace_duration_over_time.pdf"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ 持续时间随时间变化的图已保存至: {os.path.join(fig_dir, 'trace_duration_over_time.pdf')}")

def plot_trace_duration_cdf(algo_trace_dict: dict, fig_dir: str):
    """
    每个算法一条线，画 total_duration 的 CDF。
    """
    plt.figure(figsize=(10, 5))

    for algo, traces in algo_trace_dict.items():
        durations = sorted(t.total_duration for t in traces if t.total_duration)
        if not durations:
            continue

        cdf = np.arange(1, len(durations)+1) / len(durations)
        plt.plot(durations, cdf, label=algo)

    plt.xlabel("Total Duration (μs)")
    plt.ylabel("CDF")
    plt.title("CDF of Trace Durations")
    plt.grid()
    plt.legend()
    os.makedirs(fig_dir, exist_ok=True)
    plt.savefig(os.path.join(fig_dir, "trace_duration_cdf.pdf"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ CDF 图已保存至: {os.path.join(fig_dir, 'trace_duration_cdf.pdf')}")

def draw(algo_trace_dict, fig_dir):
    """
    绘制每个 trace 的持续时间分布图
    """
    plot_trace_duration_cdf(algo_trace_dict, fig_dir)
    plot_trace_duration_over_time(algo_trace_dict, fig_dir)

def main(experiment_dir):
    algo_trace_dict = load_all_traces_from_experiment(experiment_dir)

    fig_dir = experiment_dir.replace("data", "fig")
    os.makedirs(fig_dir, exist_ok=True)
    draw(algo_trace_dict, fig_dir)

if __name__ == "__main__":
    experiment_dir = "data/onlineBoutique/1744278530113530"
    main(experiment_dir)