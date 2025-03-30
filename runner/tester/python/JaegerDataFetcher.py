# JaegerDataFetcher.py
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
