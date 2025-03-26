import subprocess

def get_jaeger_nodeport():
    try:
        result = subprocess.run(
            [
                "kubectl", "get", "svc", "tracing", "-n", "istio-system",
                "-o", "jsonpath={.spec.ports[?(@.name=='http-query')].nodePort}"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        node_port = result.stdout.strip()
        return node_port
    except subprocess.CalledProcessError as e:
        print(f"Error executing kubectl command: {e}")
        return None


def get_service_name_of_span(span):
    # 提取服务名称
    service_name = "unknown"
    for tag in span.get("tags", []):
        if tag["key"] == "istio.canonical_service":
            service_name = tag["value"]
            break
    if service_name == "unknown":
        service_name = span["operationName"].split(":")[0]  # 备用方案

    return service_name

def get_pod_name_of_span(span):
    # 提取 Pod 名称
    IP_INDEX = 1
    POD_NAME_INDEX = 2

    pod_name = "unknown"
    for tag in span.get("tags", []):
        if tag["key"] == "node_id":
            pod_name = tag["value"].split("~")[POD_NAME_INDEX]
            break

    return pod_name

def format_duration(duration):
    if duration < 1e3:
        return f"{duration:.1f}μs"
    elif duration < 1e6:
        return f"{duration / 1e3:.1f}ms"
    else:
        return f"{duration / 1e6:.1f}s"
