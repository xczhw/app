# 解析新的 Jaeger JSON 结构并绘制微服务调用关系图
import json
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import requests
import time

end_time = int(time.time() * 1e6)  # 当前时间（微秒）
start_time = end_time - (60 * 60 * 1e6)  # 1小时前

jaeger_base_url = "http://localhost:16686/jaeger/api"
service_name = "frontend.default"
limit = 100

# 获取 Trace ID
response = requests.get(f"{jaeger_base_url}/traces?service={service_name}&limit={limit}")
trace_data = response.json()

# 需要关注的服务
allowed_services = {"frontend", "cartservice", "currencyservice"}

if "data" in trace_data and len(trace_data["data"]) > 0:
    all_traces = []
    for trace in trace_data["data"]:
        trace_id = trace["traceID"]
        print(f"Found trace ID: {trace_id}")
        trace_response = requests.get(f"{jaeger_base_url}/traces/{trace_id}")

        if trace_response.status_code == 200:
            try:
                trace_json = trace_response.json()
                all_traces.append(trace_json)
            except requests.exceptions.JSONDecodeError:
                print(f"Error decoding trace {trace_id}")

    # 保存所有 traces
    with open("trace_results.json", "w") as f:
        json.dump(all_traces, f, indent=4)

    print(f"Downloaded {len(all_traces)} traces.")
else:
    print("No traces found.")

# 读取 JSON 数据
file_path = "trace_results.json"
with open(file_path, "r") as f:
    data = json.load(f)

# 初始化图和统计数据
G = nx.MultiDiGraph()
call_counts = defaultdict(int)
latency_sums = defaultdict(float)
span_services = {}

# 解析数据
for trace_item in data:  # data 是列表
    if "data" not in trace_item:
        continue  # 跳过格式不对的对象

    for trace in trace_item["data"]:  # 遍历 data
        spans = {span["spanID"]: span for span in trace.get("spans", [])}  # 用于查找父子关系
        for span in trace.get("spans", []):
            # 提取服务名称
            service_name = "unknown"
            for tag in span.get("tags", []):
                if tag["key"] == "istio.canonical_service":
                    service_name = tag["value"]
                    break
            if service_name == "unknown":
                service_name = span["operationName"].split(":")[0]  # 备用方案

            span_services[span["spanID"]] = service_name
            duration = span["duration"] / 1e3  # 转换为微秒

            # 只保留关注的服务
            if service_name not in allowed_services:
                continue

            for ref in span.get("references", []):
                if ref["refType"] == "CHILD_OF":
                    parent_span_id = ref["spanID"]
                    if parent_span_id in spans:
                        parent_service = span_services.get(parent_span_id, "unknown")
                        # 只保留符合条件的调用关系
                        if parent_service in allowed_services:
                            edge_label = f"{parent_service} -> {service_name}\n{duration:.1f} µs"
                            G.add_edge(parent_service, service_name, label=edge_label)

# 画微服务调用关系图并标注调用次数和平均时延
plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G, seed=42)

nx.draw(G, pos, with_labels=True, node_size=3000, node_color="lightblue", font_size=10, edge_color="gray")

# 添加边的标签（每次调用的独立时延）
edge_labels = nx.get_edge_attributes(G, "label")
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, label_pos=0.5)

plt.title("Microservices Call Graph (Each Call as Unique Edge)")
plt.show()
plt.savefig("./fig/temp2.png")

# 提取时间戳和响应时间
timestamps = []
durations = []

for trace_item in data:  # data 是一个列表
    if "data" not in trace_item:
        continue  # 跳过无效项

    for trace in trace_item["data"]:
        for span in trace["spans"]:
            timestamps.append(span["startTime"] / 1e6)  # 转换为毫秒
            durations.append(span["duration"] / 1e3)  # 转换为微秒

# 画图
plt.figure(figsize=(10, 5))
plt.plot(timestamps, durations, marker="o", linestyle="-")
plt.xlabel("Timestamp (ms)")
plt.ylabel("Duration (µs)")
plt.title("Request Latency Over Time")
plt.grid()
plt.savefig("./fig/temp.png")
