import threading
import time
import subprocess
import pandas as pd
from utils import utc_microtime

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
                timestamp = utc_microtime()

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


class MetricsCollector(threading.Thread):
    def __init__(self, namespace, interval, output_file):
        super().__init__()
        self.namespace = namespace
        self.interval = interval
        self.output_file = output_file
        self._stop_flag = threading.Event()
        self.data = []

    def stop(self):
        self._stop_flag.set()

    def run(self):
        print("🟢 开始采集指标")
        while not self._stop_flag.is_set():
            pod_data = get_pod_resource_usage(self.namespace)
            if pod_data:
                self.data.extend(pod_data)
                # print(f"📊 采样 {len(pod_data)} 条")
            time.sleep(self.interval)

        print("📴 停止采集，正在保存数据...")
        if self.data:
            df = pd.DataFrame(self.data)
            df.to_csv(self.output_file, index=False)
            print(f"✅ 指标保存至 {self.output_file}")
        else:
            print("⚠️ 没有数据，未生成文件")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="default", help="Kubernetes 命名空间")
    parser.add_argument("--interval", type=int, default=5, help="采样间隔（秒）")
    parser.add_argument("--output", default="test_metrics.csv", help="输出 CSV 文件路径")
    parser.add_argument("--duration", type=int, default=30, help="总采集时长（秒）")
    args = parser.parse_args()

    print(f"🧪 启动测试采集器：namespace={args.namespace}, interval={args.interval}s, duration={args.duration}s")
    collector = MetricsCollector(args.namespace, args.interval, args.output)
    collector.start()

    try:
        for remaining in range(args.duration, 0, -1):
            print(f"⏳ 采集中...剩余 {remaining} 秒", end="\r")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 收到 Ctrl+C，提前终止采集")

    collector.stop()
    collector.join()
    print("✅ 采集完成，退出测试")