import json
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import time
import os
from collections import defaultdict
from utils import safe_parse_time

import utils
from JaegerDataFetcher import JaegerDataFetcher

class CallGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.service_graph = nx.DiGraph()
        self.span_services = {}

    def build_graph(self, traces):
        for trace_item in traces:
            if "data" not in trace_item:
                continue

            for trace in trace_item["data"]:
                spans = {span["spanID"]: span for span in trace.get("spans", [])}

                for span in trace.get("spans", []):
                    service_name = utils.get_service_name_of_span(span)
                    self.span_services[span["spanID"]] = service_name
                    duration = span["duration"]

                    for ref in span.get("references", []):
                        if ref["refType"] == "CHILD_OF":
                            parent_span_id = ref["spanID"]
                            if parent_span_id in spans:
                                parent_service = self.span_services.get(parent_span_id, "unknown")
                                pod = utils.get_pod_name_of_span(span)
                                parent_pod = utils.get_pod_name_of_span(spans[parent_span_id])
                                if self.graph.has_edge(parent_pod, pod):
                                    self.graph[parent_pod][pod]['durations'].append(duration)
                                else:
                                    self.graph.add_edge(parent_pod, pod, durations=[duration], service=service_name, parent_service=parent_service)

                                # 构建 service 级别的图
                                if self.service_graph.has_edge(parent_service, service_name):
                                    self.service_graph[parent_service][service_name]['durations'].append(duration)
                                else:
                                    self.service_graph.add_edge(parent_service, service_name, durations=[duration])
        return self.graph, self.service_graph

class TraceCategorizer:
    def __init__(self):
        self.trace_categories = defaultdict(list)

    def categorize_traces(self, traces):
        for trace_item in traces:
            if "data" not in trace_item:
                continue

            unique_services = set()
            total_duration = 0
            timestamp = None

            for trace in trace_item["data"]:
                for span in trace.get("spans", []):
                    service_name = utils.get_service_name_of_span(span)
                    unique_services.add(service_name)
                    total_duration += span["duration"]
                    if timestamp is None:
                        timestamp = span["startTime"] / 1e6  # Convert to milliseconds

            category_key = tuple(sorted(unique_services))
            self.trace_categories[category_key].append((timestamp, total_duration))

        return self.trace_categories

class GraphVisualizer:
    @staticmethod
    def draw_graph(graph, allowed_services, output_dir="fig"):
        filtered_graph = nx.DiGraph()
        for u, v, d in graph.edges(data=True):
            if d["service"] in allowed_services and d["parent_service"] in allowed_services:
                avg_duration = sum(d["durations"]) / len(d["durations"])
                duration_label = utils.format_duration(avg_duration)
                filtered_graph.add_edge(u, v, label=duration_label)

        plt.figure(figsize=(14, 10))
        pos = nx.shell_layout(filtered_graph)
        nx.draw(filtered_graph, pos, with_labels=True, node_size=3500, node_color="skyblue", font_size=12, edge_color="gray", width=2, alpha=0.8)
        edge_labels = nx.get_edge_attributes(filtered_graph, "label")
        nx.draw_networkx_edge_labels(filtered_graph, pos, edge_labels=edge_labels, font_size=10, label_pos=0.5)
        plt.title("Pod-to-Pod Call Graph", fontsize=14)
        plt.savefig(f"{output_dir}/pod_call_graph.pdf", dpi=300, bbox_inches="tight")
        # plt.show()

    @staticmethod
    def draw_service_graph(service_graph, output_dir="fig/"):
        plt.figure(figsize=(12, 8))
        pos = nx.shell_layout(service_graph)

        edge_labels = {}
        for u, v, d in service_graph.edges(data=True):
            avg_duration = sum(d["durations"]) / len(d["durations"])
            edge_labels[(u, v)] = utils.format_duration(avg_duration)

        nx.draw(service_graph, pos, with_labels=True, node_size=3000, node_color="lightcoral", font_size=10, edge_color="gray", width=2, alpha=0.8)
        nx.draw_networkx_edge_labels(service_graph, pos, edge_labels=edge_labels, font_size=9, label_pos=0.5)
        plt.title("Service-to-Service Call Graph", fontsize=14)
        plt.savefig(f"{output_dir}/service_call_graph.pdf", dpi=300, bbox_inches="tight")
        # plt.show()

    @staticmethod
    def plot_duration_trends(trace_categories, base_folder="fig/"):
        output_folder = os.path.join(base_folder, "/duration_trends")
        os.makedirs(output_folder, exist_ok=True)

        for category, traces in trace_categories.items():
            category_name = "_".join(category)
            traces.sort()  # Sort by timestamp
            timestamps, durations = zip(*traces)

            plt.figure(figsize=(10, 5))
            plt.plot(timestamps, durations, marker="o", linestyle="-", label=category_name)
            plt.xlabel("Timestamp (ms)")
            plt.ylabel("Total Duration (μs)")
            plt.title(f"Duration Trend for {category_name}")
            plt.legend()
            plt.grid()
            plt.savefig(os.path.join(output_folder, f"{category_name}_trend.pdf"), dpi=300, bbox_inches="tight")
            plt.close()

    @staticmethod
    def plot_duration_comparison(trace_categories, output_dir="fig"):
        categories = ["_".join(category) for category in trace_categories.keys()]
        avg_durations = [sum(duration for _, duration in traces) / len(traces) for traces in trace_categories.values()]

        plt.figure(figsize=(12, 6))
        plt.bar(categories, avg_durations, color="skyblue")
        plt.xlabel("Trace Category")
        plt.ylabel("Average Total Duration (μs)")
        plt.title("Comparison of Average Durations Across Trace Categories")
        plt.xticks(rotation=45, ha="right")
        plt.grid(axis="y")
        plt.savefig(f"{output_dir}/duration_comparison.pdf", dpi=300, bbox_inches="tight")
        plt.close()

def plot_latency_cdf_for_traces(trace_categories, output_dir="fig"):
    plt.figure(figsize=(10, 5))

    for category, traces in trace_categories.items():
        durations = sorted([duration for _, duration in traces])
        cdf = np.arange(1, len(durations) + 1) / len(durations)
        plt.plot(durations, cdf, marker=".", linestyle="-", label="_".join(category))

    plt.xlabel("Latency (μs)")
    plt.ylabel("CDF")
    plt.title("Cumulative Distribution Function of Latency")
    plt.legend()
    plt.grid()
    plt.savefig(f"{output_dir}/latency_cdf.pdf", dpi=300, bbox_inches="tight")
    plt.close()

def plot_latency_with_algorithms(base_dir: str):
    trace_path = os.path.join(base_dir, "trace_results.json")
    with open(trace_path, "r") as f:
        traces = json.load(f)

    timestamps = []
    latencies = []
    print("traces len", len(traces))
    for trace in traces:
        duration_us = trace["data"][0]["spans"][0]["duration"]
        latency_ms = duration_us / 1000  # 转为毫秒
        ts = pd.to_datetime(trace["data"][0]["spans"][0]["startTime"], unit='us')
        timestamps.append(ts)
        latencies.append(latency_ms)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "latency_ms": latencies
    })

    df = df.sort_values("timestamp")

    # 获取算法使用时间段
    algo_periods = []
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

    # 绘图
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df['timestamp'], df['latency_ms'], label='Latency (ms)', color='orange')
    ax.set_ylabel('Latency (ms)')
    ax.set_xlabel('Time')
    ax.set_title("Latency Over Time with Algorithm Periods")

    # for start, end, algo in algo_periods:
    #     ax.axvspan(start, end, alpha=0.3, label=algo)

    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()

    fig_path = os.path.join(base_dir.replace("data", "fig"), "latency_with_algos.pdf")
    os.makedirs(os.path.dirname(fig_path), exist_ok=True)
    plt.savefig(fig_path)
    plt.close()

def plot_latency_and_cdf_for_algos(base_dir: str):
    for algo in os.listdir(base_dir):
        algo_path = os.path.join(base_dir, algo)
        trace_file = os.path.join(algo_path, "trace_results.json")
        if not os.path.isdir(algo_path) or not os.path.isfile(trace_file):
            continue

        # 解析 trace
        with open(trace_file, "r") as f:
            traces = json.load(f)

        timestamps = []
        latencies_ms = []

        for trace in traces:
            try:
                span = trace["data"][0]["spans"][0]
                start_time = pd.to_datetime(span["startTime"], unit='us')
                latency = span["duration"] / 1000  # microseconds → milliseconds
                timestamps.append(start_time)
                latencies_ms.append(latency)
            except (KeyError, IndexError):
                continue

        if not timestamps:
            print(f"⚠️ No valid data for {algo}, skipping.")
            continue

        df = pd.DataFrame({
            "timestamp": timestamps,
            "latency_ms": latencies_ms
        }).sort_values("timestamp")

        # 创建图路径
        fig_path_base = algo_path.replace("data", "fig")
        os.makedirs(fig_path_base, exist_ok=True)

        # ---- 图 1: Latency over time ----
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(df["timestamp"], df["latency_ms"], label="Latency (ms)", color='orange')
        ax1.set_title(f"Latency Over Time - {algo}")
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Latency (ms)")
        fig1.autofmt_xdate()
        plt.tight_layout()
        plt.savefig(os.path.join(fig_path_base, "latency_over_time.pdf"))
        plt.close(fig1)

        # ---- 图 2: CDF ----
        sorted_latencies = sorted(latencies_ms)
        cdf_y = [i / len(sorted_latencies) for i in range(len(sorted_latencies))]

        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.plot(sorted_latencies, cdf_y, label="CDF", color='blue')
        ax2.set_title(f"Latency CDF - {algo}")
        ax2.set_xlabel("Latency (ms)")
        ax2.set_ylabel("Cumulative Probability")
        ax2.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_path_base, "latency_cdf.pdf"))
        plt.close(fig2)

        print(f"✅ 绘图完成: {algo}")

def main(traces, base_dir="fig"):
    allowed_services = {"frontend", "cartservice"}

    # 构建调用图
    builder = CallGraphBuilder()
    graph, service_graph = builder.build_graph(traces)
    categorizer = TraceCategorizer()
    trace_categories = categorizer.categorize_traces(traces)

    # 画图并保存
    GraphVisualizer.draw_graph(graph, allowed_services, base_dir)
    GraphVisualizer.draw_service_graph(service_graph, base_dir)
    GraphVisualizer.plot_duration_trends(trace_categories, base_dir)
    GraphVisualizer.plot_duration_comparison(trace_categories, base_dir)
    plot_latency_cdf_for_traces(trace_categories, base_dir)

if __name__ == "__main__":
    # service_name = "frontend.default"

    # 获取数据
    # fetcher = JaegerDataFetcher(service_name)
    # traces = fetcher.fetch_traces()
    # fetcher.save_traces(traces)
    # main(traces)
    exp_id = "20250402-093711"
    plot_latency_with_algorithms(f"data/onlineBoutique/{exp_id}")
    plot_latency_and_cdf_for_algos(f"data/onlineBoutique/{exp_id}")
