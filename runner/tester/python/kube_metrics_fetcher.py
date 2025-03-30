import argparse
import time
import signal
import subprocess
import pandas as pd
from datetime import datetime

# 使用kubectl命令获取Pod的CPU和内存使用情况
def get_pod_resource_usage(namespace="default"):
    try:
        result = subprocess.run(
            ["kubectl", "top", "pod", "-n", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        lines = result.stdout.splitlines()
        pod_data = []

        for line in lines[1:]:  # 跳过表头
            parts = line.split()
            if len(parts) >= 3:
                pod_name = parts[0]
                cpu_usage = parts[1]
                memory_usage = parts[2]
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                pod_data.append({
                    "timestamp": timestamp,
                    "pod_name": pod_name,
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage
                })

        return pod_data

    except subprocess.CalledProcessError as e:
        print(f"获取Pod资源使用情况失败: {e}")
        return []

def collect_data(namespace="default", interval=10, output_file="pod_resource_usage.csv"):
    data = []
    stop_flag = {"stop": False}

    def handle_signal(signum, frame):
        print("📴 收到停止信号，停止抓取数据...")
        stop_flag["stop"] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while not stop_flag["stop"]:
        print(f"📊 抓取 {namespace} 下的Pod资源使用情况...")
        pod_data = get_pod_resource_usage(namespace)
        if pod_data:
            data.extend(pod_data)
        time.sleep(interval)

    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    print(f"✅ 数据已保存至 {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--interval", type=int, default=1)
    parser.add_argument("--output", default="pod_resource_usage.csv")
    args = parser.parse_args()

    collect_data(namespace=args.namespace, interval=args.interval, output_file=args.output)
