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
        从 end_time 倒着获取 traces，直到 trace 里出现早于 start_time 的 span（这些 trace 会被丢弃）
        :param start_time: 起始时间戳（微秒）
        :param end_time: 结束时间戳（微秒）
        :return: 所有 trace 数据
        """
        current_end = int(end_time)
        all_traces = []
        seen_trace_ids = set()

        while current_end > start_time:
            params = {
                'service': self.service_name,
                'limit': self.limit,
                'end': current_end
            }

            print(f"🔄 Fetching traces from {start_time} to {current_end}...")
            response = requests.get(self.jaeger_base_url, params=params)

            if response.status_code != 200:
                print(f"❌ 请求失败: {response.status_code}")
                break

            trace_data = response.json().get("data", [])
            if not trace_data:
                print("✅ 没有更多 traces。")
                break

            min_start = float('inf')
            max_end = 0

            found_too_old = False

            for trace in trace_data:
                trace_id = trace["traceID"]
                if trace_id in seen_trace_ids:
                    continue
                seen_trace_ids.add(trace_id)

                spans = trace.get("spans", [])
                if not spans:
                    continue

                first_span = spans[0]
                span_start = first_span.get("startTime", 0)
                span_end = span_start + first_span.get("duration", 0)

                # 检查是否太早，直接跳过这个 trace
                if span_start < start_time:
                    found_too_old = True
                    continue

                min_start = min(min_start, span_start)
                max_end = max(max_end, span_end)

                trace_response = requests.get(f"{self.jaeger_base_url}/{trace_id}")
                if trace_response.status_code == 200:
                    try:
                        trace_json = trace_response.json()
                        all_traces.append(trace_json)
                    except requests.exceptions.JSONDecodeError:
                        print(f"❌ 解码失败 trace: {trace_id}")

            print(f"🕒 当前 batch 最小 start: {min_start}, 最大 end: {max_end}")

            if found_too_old:
                print("⏹️ 遇到早于 start_time 的 trace，停止拉取。")
                break

            # 更新下一次的 end_time（往前挪）
            if min_start == float('inf') or min_start <= start_time:
                print("⛔ 没有更早的 traces，终止。")
                break

            current_end = min_start - 1

        print(f"📦 共获取 {len(all_traces)} 条 traces")
        return all_traces

if __name__ == "__main__":
    # 示例服务名，可以替换为你的服务名
    service_name = "frontend.default"  # 替换为你的 Jaeger 服务名
    global_start_ts_micro = 1743955535688697
    global_end_ts_micro = 1743955840097186

    experiment_dir = "data/onlineBoutique/1743955376367504"

    # 创建 JaegerDataFetcher 实例
    jaeger_fetcher = JaegerDataFetcher(service_name)

    # 获取 Jaeger 数据并保存
    trace_data = jaeger_fetcher.fetch_all_traces(global_start_ts_micro, global_end_ts_micro)

    # 如果抓取到数据，保存它
    if trace_data:
        # 保存 trace 数据到文件
        jaeger_fetcher.save_traces(trace_data, experiment_dir)
    else:
        print("没有找到任何 traces 数据。")