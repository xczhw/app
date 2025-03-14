import requests
import time
import json

def get_traces():
    end_time = int(time.time() * 1e6)  # 当前时间（微秒）
    start_time = end_time - (60 * 60 * 1e6)  # 1小时前

    jaeger_base_url = "http://localhost:16686/jaeger/api"
    service_name = "frontend.default"

    # 获取 Trace ID
    response = requests.get(f"{jaeger_base_url}/traces?service={service_name}&limit=10")
    trace_data = response.json()
    if "data" in trace_data and len(trace_data["data"]) > 0:
        all_traces = []
        for trace in trace_data["data"]:
            trace_id = trace["traceID"]
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

if __name__ == "__main__":
    get_traces()