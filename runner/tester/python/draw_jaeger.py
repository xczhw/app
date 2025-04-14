import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from collections import defaultdict
from trace_model import Trace, Span
import utils

class CallGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.service_graph = nx.DiGraph()

    def build_graph(self, trace_objects):
        for trace in trace_objects:
            for span in trace.spans:
                for child in span.children:
                    # Pod-level graph
                    if self.graph.has_edge(span.pod_id, child.pod_id):
                        self.graph[span.pod_id][child.pod_id]['durations'].append(child.duration)
                    else:
                        self.graph.add_edge(
                            span.pod_id,
                            child.pod_id,
                            durations=[child.duration],
                            service=child.service_name,
                            parent_service=span.service_name
                        )

                    # Service-level graph
                    if self.service_graph.has_edge(span.service_name, child.service_name):
                        self.service_graph[span.service_name][child.service_name]['durations'].append(child.duration)
                    else:
                        self.service_graph.add_edge(
                            span.service_name,
                            child.service_name,
                            durations=[child.duration]
                        )
        return self.graph, self.service_graph


class TraceCategorizer:
    def __init__(self):
        self.trace_categories = defaultdict(list)

    def categorize_traces(self, trace_objects):
        for trace in trace_objects:
            services = set(span.service_name for span in trace.spans)
            timestamp = trace.spans[0].start_time if trace.spans else None
            total_duration = trace.get_total_duration()

            if timestamp is not None:
                category_key = tuple(sorted(services))
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
        nx.draw(filtered_graph, pos, with_labels=True, node_size=3500, node_color="skyblue",
                font_size=12, edge_color="gray", width=2, alpha=0.8)
        edge_labels = nx.get_edge_attributes(filtered_graph, "label")
        nx.draw_networkx_edge_labels(filtered_graph, pos, edge_labels=edge_labels,
                                     font_size=10, label_pos=0.5)
        plt.title("Pod-to-Pod Call Graph", fontsize=14)
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/pod_call_graph.pdf", dpi=300, bbox_inches="tight")
        plt.close()

    @staticmethod
    def draw_service_graph(service_graph, output_dir="fig"):
        plt.figure(figsize=(12, 8))
        pos = nx.shell_layout(service_graph)
        edge_labels = {}

        for u, v, d in service_graph.edges(data=True):
            avg_duration = sum(d["durations"]) / len(d["durations"])
            edge_labels[(u, v)] = f"{avg_duration / 1000:.2f} ms"

        nx.draw(service_graph, pos, with_labels=True, node_size=3000, node_color="lightcoral",
                font_size=10, edge_color="gray", width=2, alpha=0.8)
        nx.draw_networkx_edge_labels(service_graph, pos, edge_labels=edge_labels,
                                     font_size=9, label_pos=0.5)
        plt.title("Service-to-Service Call Graph", fontsize=14)
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/service_call_graph.pdf", dpi=300, bbox_inches="tight")
        plt.close()

    @staticmethod
    def plot_duration_trends(trace_categories, base_folder="fig"):
        output_folder = os.path.join(base_folder, "duration_trends")
        os.makedirs(output_folder, exist_ok=True)

        for category, traces in trace_categories.items():
            category_name = "_".join(category)
            traces.sort()
            timestamps, durations = zip(*traces)

            plt.figure(figsize=(10, 5))
            plt.plot(timestamps, durations, marker="o", linestyle="-", label=category_name)
            plt.xlabel("Timestamp (μs)")
            plt.ylabel("Total Duration (μs)")
            plt.title(f"Duration Trend for {category_name}")
            plt.legend()
            plt.grid()
            plt.savefig(os.path.join(output_folder, f"{category_name}_trend.pdf"), dpi=300, bbox_inches="tight")
            plt.close()

    @staticmethod
    def plot_duration_comparison(trace_categories, output_dir="fig"):
        categories = ["_".join(category) for category in trace_categories.keys()]
        avg_durations = [sum(duration for _, duration in traces) / len(traces)
                         for traces in trace_categories.values()]

        plt.figure(figsize=(12, 6))
        plt.bar(categories, avg_durations, color="skyblue")
        plt.xlabel("Trace Category")
        plt.ylabel("Average Total Duration (μs)")
        plt.title("Comparison of Average Durations Across Trace Categories")
        plt.xticks(rotation=45, ha="right")
        plt.grid(axis="y")
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/duration_comparison.pdf", dpi=300, bbox_inches="tight")
        plt.close()


def main(data_dir):

    allowed_services = {"frontend", "cartservice"}

    builder = CallGraphBuilder()
    graph, service_graph = builder.build_graph(trace_objects)

    categorizer = TraceCategorizer()
    trace_categories = categorizer.categorize_traces(trace_objects)

    GraphVisualizer.draw_graph(graph, allowed_services, fig_dir)
    GraphVisualizer.draw_service_graph(service_graph, fig_dir)
    GraphVisualizer.plot_duration_trends(trace_categories, fig_dir)
    GraphVisualizer.plot_duration_comparison(trace_categories, fig_dir)

if __name__ == "__main__":
    import json
    from trace_model import Trace

    trace_dir = "data/onlineBoutique/1744278530113530"
    main(trace_dir)
