import json
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import requests
import time
import os
from collections import defaultdict
import utils

class JaegerDataFetcher:
    def __init__(self, service_name, limit=1000):
        self.port = utils.get_jaeger_nodeport()
        self.jaeger_base_url = f"http://localhost:{self.port}/jaeger/api"
        self.service_name = service_name
        self.limit = limit

    def fetch_traces(self):
        end_time = int(time.time() * 1e6)
        start_time = end_time - (60 * 60 * 1e6)
        response = requests.get(f"{self.jaeger_base_url}/traces?service={self.service_name}&limit={self.limit}")
        trace_data = response.json()

        if "data" not in trace_data or not trace_data["data"]:
            print("No traces found.")
            return []

        all_traces = []
        for trace in trace_data["data"]:
            trace_id = trace["traceID"]
            print(f"Found trace ID: {trace_id}")
            trace_response = requests.get(f"{self.jaeger_base_url}/traces/{trace_id}")

            if trace_response.status_code == 200:
                try:
                    trace_json = trace_response.json()
                    all_traces.append(trace_json)
                except requests.exceptions.JSONDecodeError:
                    print(f"Error decoding trace {trace_id}")

        return all_traces

    def save_traces(self, traces, filename="trace_results.json"):
        with open(filename, "w") as f:
            json.dump(traces, f, indent=4)
        print(f"Downloaded {len(traces)} traces.")

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
    def draw_graph(graph, allowed_services, output_path="fig/pod_call_graph.png"):
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
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.show()

    @staticmethod
    def draw_service_graph(service_graph, output_path="fig/service_call_graph.png"):
        plt.figure(figsize=(12, 8))
        pos = nx.shell_layout(service_graph)

        edge_labels = {}
        for u, v, d in service_graph.edges(data=True):
            avg_duration = sum(d["durations"]) / len(d["durations"])
            edge_labels[(u, v)] = utils.format_duration(avg_duration)

        nx.draw(service_graph, pos, with_labels=True, node_size=3000, node_color="lightcoral", font_size=10, edge_color="gray", width=2, alpha=0.8)
        nx.draw_networkx_edge_labels(service_graph, pos, edge_labels=edge_labels, font_size=9, label_pos=0.5)
        plt.title("Service-to-Service Call Graph", fontsize=14)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.show()

    @staticmethod
    def plot_duration_trends(trace_categories, output_folder="fig/duration_trends/"):
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
            plt.savefig(os.path.join(output_folder, f"{category_name}_trend.png"), dpi=300, bbox_inches="tight")
            plt.close()

    @staticmethod
    def plot_duration_comparison(trace_categories, output_path="fig/duration_comparison.png"):
        categories = ["_".join(category) for category in trace_categories.keys()]
        avg_durations = [sum(duration for _, duration in traces) / len(traces) for traces in trace_categories.values()]

        plt.figure(figsize=(12, 6))
        plt.bar(categories, avg_durations, color="skyblue")
        plt.xlabel("Trace Category")
        plt.ylabel("Average Total Duration (μs)")
        plt.title("Comparison of Average Durations Across Trace Categories")
        plt.xticks(rotation=45, ha="right")
        plt.grid(axis="y")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

class LatencyCDFPlotter:
    @staticmethod
    def plot_latency_cdf(trace_categories, output_path="fig/latency_cdf.png"):
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
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

if __name__ == "__main__":
    service_name = "frontend.default"
    allowed_services = {"frontend", "cartservice"}

    # 获取数据
    fetcher = JaegerDataFetcher(service_name)
    traces = fetcher.fetch_traces()
    fetcher.save_traces(traces)

    # 构建调用图
    builder = CallGraphBuilder()
    graph, service_graph = builder.build_graph(traces)
    categorizer = TraceCategorizer()
    trace_categories = categorizer.categorize_traces(traces)

    # 画图并保存
    GraphVisualizer.draw_graph(graph, allowed_services)
    GraphVisualizer.draw_service_graph(service_graph)
    GraphVisualizer.plot_duration_trends(trace_categories)
    GraphVisualizer.plot_duration_comparison(trace_categories)
    LatencyCDFPlotter.plot_latency_cdf(trace_categories)
