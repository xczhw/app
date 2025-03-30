import subprocess
import time
import os

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

def wait_for_pods_ready(namespace, timeout=300):
    print("⏳ 正在等待所有 Pod 就绪...")
    start = time.time()
    while time.time() - start < timeout:
        output = subprocess.getoutput(f"kubectl get pods -n {namespace}")
        lines = output.splitlines()[1:]  # 跳过表头
        all_running = all("Running" in line for line in lines)
        if all_running:
            print("✅ 所有 Pod 已就绪")
            return True
        time.sleep(5)
    print("❌ 等待超时，部分 Pod 未就绪")
    return False

def apply_algo_yaml(policy, app):
    yaml_path = os.path.join("yaml", app, "algo", f"{policy}-{app}.yaml")
    print(f"🚀 应用算法 YAML：{yaml_path}")
    subprocess.run(["kubectl", "apply", "-f", yaml_path], check=True)

def save_timestamped_data(app, policy, start_ts, end_ts):
    dir_path = os.path.join("data", app, policy, f"{start_ts}_{end_ts}")
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, "timestamps.txt"), "w") as f:
        f.write(f"Start: {start_ts}\nEnd: {end_ts}\n")
    print(f"📁 数据保存至: {dir_path}")