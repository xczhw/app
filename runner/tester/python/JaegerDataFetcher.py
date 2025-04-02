import requests
import json
import os
from utils import get_jaeger_nodeport

class JaegerDataFetcher:
    def __init__(self, service_name, limit=1000):
        # 获取 Jaeger 服务的 NodePort
        self.port = get_jaeger_nodeport()
        self.jaeger_base_url = f"http://localhost:{self.port}/jaeger/api/traces"
        self.service_name = service_name
        self.limit = limit

    def fetch_all_traces(self, start_time, end_time):
        """
        获取时间段内所有 Jaeger traces
        :param start_time: 起始时间戳（微秒）
        :param end_time: 结束时间戳（微秒）
        :return: 所有 trace 数据
        """
        current_start = int(start_time)
        all_traces = []
        seen_trace_ids = set()

        while current_start < end_time:
            params = {
                'service': self.service_name,
                'limit': self.limit,
                'start': current_start,
                'end': end_time
            }

            print(f"Fetching traces from {current_start} to {end_time}...")
            response = requests.get(self.jaeger_base_url, params=params)

            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code}")
                break

            trace_data = response.json().get("data", [])
            if not trace_data:
                print("✅ 已获取全部 traces。")
                break

            max_start_time_in_batch = current_start

            for trace in trace_data:
                trace_id = trace["traceID"]
                if trace_id in seen_trace_ids:
                    continue  # 避免重复
                seen_trace_ids.add(trace_id)

                # 更新当前最大 start time
                for span in trace.get("spans", []):
                    span_start = span.get("startTime", 0)
                    if span_start > max_start_time_in_batch:
                        max_start_time_in_batch = span_start

                trace_response = requests.get(f"{self.jaeger_base_url}/{trace_id}")
                if trace_response.status_code == 200:
                    try:
                        trace_json = trace_response.json()
                        all_traces.append(trace_json)
                    except requests.exceptions.JSONDecodeError:
                        print(f"❌ 解码失败 trace: {trace_id}")

            # 更新下一次的 start_time，+1 防止重复
            if max_start_time_in_batch == current_start:
                # 防止死循环
                print("⚠️ 没有新的时间进展，终止")
                break
            current_start = max_start_time_in_batch + 1

        print(f"📦 共获取 {len(all_traces)} 条 traces")
        return all_traces

    def save_traces(self, traces, folder="./", filename="trace_results.json"):
        """
        将 Jaeger trace 数据保存为 JSON 文件
        :param traces: trace 数据
        :param filename: 保存文件名
        """
        save_path = os.path.join(folder, filename)
        if traces:
            with open(save_path, "w") as f:
                json.dump(traces, f, indent=4)
            print(f"📁 下载了 {len(traces)} 条 traces，并保存到 {save_path}.")
        else:
            print("❌ 没有有效的 trace 数据可保存")

if __name__ == "__main__":
    # 示例服务名，可以替换为你的服务名
    service_name = "frontend.default"  # 替换为你的 Jaeger 服务名

    # 创建 JaegerDataFetcher 实例
    jaeger_fetcher = JaegerDataFetcher(service_name, limit=20)

    traces = jaeger_fetcher.fetch_traces()

    # 或者，你可以提供自定义的时间范围：
    # start_time = 1633046400000000  # 示例起始时间（微秒）
    # end_time = 1633050000000000    # 示例结束时间（微秒）
    # traces = jaeger_fetcher.fetch_traces(start_time, end_time)

    # 如果抓取到数据，保存它
    if traces:
        # 保存 trace 数据到文件
        jaeger_fetcher.save_traces(traces)
    else:
        print("没有找到任何 traces 数据。")