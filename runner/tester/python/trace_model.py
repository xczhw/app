__all__ = ["Trace", "Span"]

class Span:
    def __init__(self, span_json: dict, service_name: str):
        self.span_id = span_json["spanID"]
        self.parent_id = span_json["references"][0]["spanID"] if span_json.get("references") else None
        self.start_time = span_json["startTime"]
        self.duration = span_json["duration"]
        self.end_time = self.start_time + self.duration
        self.pod_id = self._extract_pod_id(span_json.get("tags", []))
        self.service_name = service_name
        self.children = []

    def _extract_pod_id(self, tags):
        for tag in tags:
            if tag.get("key") == "node_id":
                parts = tag["value"].split("~")
                return parts[2] if len(parts) > 2 else "unknown"
        return "unknown"

    def add_child(self, child: 'Span'):
        self.children.append(child)

    def to_dict(self):
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "duration": self.duration,
            "pod_id": self.pod_id,
            "service_name": self.service_name,
            "children": [child.span_id for child in self.children]
        }

class Trace:
    def __init__(self, trace_wrapper: dict):
        trace_data = trace_wrapper["data"][0]
        self.trace_id = trace_data["traceID"]
        self.service_map = {pid: info.get("serviceName", "unknown") for pid, info in trace_data["processes"].items()}

        self.spans = []
        self.span_map = {}

        self._parse_spans(trace_data["spans"])
        self.root_spans = [s for s in self.spans if s.parent_id is None]

        self.total_duration = self._get_total_duration()
        self.start_time = min(s.start_time for s in self.spans) if self.spans else 0

    def _parse_spans(self, span_data_list):
        # 解析 spans
        for span_json in span_data_list:
            svc_name = self.service_map[span_json["processID"]]
            span = Span(span_json, svc_name)
            self.spans.append(span)
            self.span_map[span.span_id] = span

        # 处理 spans 的父子关系
        for span in self.spans:
            if span.parent_id and span.parent_id in self.span_map:
                self.span_map[span.parent_id].add_child(span)

    def _get_total_duration(self):
        if not self.spans:
            return 0
        return max(s.end_time for s in self.spans) - min(s.start_time for s in self.spans)

    def get_upstream_downstream_latencies(self):
        result = []
        for s in self.spans:
            for c in s.children:
                result.append({
                    "from": s.span_id,
                    "to": c.span_id,
                    "from_service": s.service_name,
                    "to_service": c.service_name,
                    "from_pod": s.pod_id,
                    "to_pod": c.pod_id,
                    "latency": c.start_time - s.start_time
                })
        return result

    def get_pod_sequence(self):
        seq = []

        def dfs(s):
            seq.append(s.pod_id)
            for c in s.children:
                dfs(c)

        for root in self.root_spans:
            dfs(root)

        return seq

    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "total_duration": self._get_total_duration(),
            "pod_sequence": self.get_pod_sequence(),
            "spans": [s.to_dict() for s in self.spans],
            "service_names": list(self.service_map.values()),
        }

if __name__ == "__main__":
    import json
    with open("trace_example.json", "r") as f:
        trace_data = json.load(f)
    traces = []
    for item in trace_data:
        traces.append(Trace(item))
    for trace in traces:
        print(trace.to_dict())
