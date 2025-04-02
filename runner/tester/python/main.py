import time
import os
import subprocess
from datetime import datetime
from config import args

import draw_metrics
import draw_jaeger
from constants import ALGO_LIST, APP_SERVICE_NAME_MAP
from JaegerDataFetcher import JaegerDataFetcher
from utils import wait_for_pods_ready, apply_algo_yaml
from app_launcher import deploy
from generate_destination_rules import generate_yaml
from process_metrics import process_all_metrics
from process_trace import split_traces_by_time

def main():
    # 生成实验编号（精确时间戳）
    experiment_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"🔖 当前实验编号: {experiment_id}\n")

    # 1. 部署应用
    deploy(args.app, args.replicas)

    # 2. 生成 YAML
    selected_algos = ALGO_LIST if args.all_algo else [args.policy]
    generate_yaml(selected_algos, args.namespace, args.app)

    # 3. 等待 Pod 就绪
    if not wait_for_pods_ready(args.namespace):
        return

    # 4. 启动指标采集子进程
    experiment_dir = os.path.join("data", args.app, experiment_id)
    os.makedirs(experiment_dir, exist_ok=True)
    metrics_file = os.path.join(experiment_dir, f"metrics.csv")
    metrics_proc = subprocess.Popen([
        "python", "kube_metrics_fetcher.py",
        "--namespace", args.namespace,
        "--interval", str(args.interval),
        "--output", metrics_file
    ])

    # 5. 处理所有策略并记录时间
    global_start_ts_micro = int(datetime.now().timestamp() * 1e6)
    timestamps = []
    for algo in selected_algos:
        apply_algo_yaml(algo, args.app)

        print(f"⏸️ 切换策略后等待 {args.pause_seconds} 秒\n")
        time.sleep(args.pause_seconds)

        start_ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
        print(f"🕒 开始时间: {start_ts}")

        time.sleep(args.run_seconds)

        end_ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
        print(f"🕒 结束时间: {end_ts}")

        output_dir = os.path.join("data", args.app, experiment_id, algo)
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "timestamps.txt"), "w") as f:
            f.write(f"Start: {start_ts}\nEnd: {end_ts}\n")
        print(f"📁 时间戳保存至: {output_dir}\n")

        timestamps.append((start_ts, end_ts, output_dir))
    global_end_ts_micro = int(datetime.now().timestamp() * 1e6)
    with open(os.path.join("data", args.app, experiment_id, "timestamps.txt"), "w") as f:
        f.write(f"Start: {global_start_ts_micro}\nEND:{global_end_ts_micro}\n")
    print(f"📁 总时间戳已保存")

    # 6. 结束指标采集子进程
    metrics_proc.terminate()
    metrics_proc.wait()
    print("📉 资源采集进程已终止")

    # 7. 拉取 Jaeger trace 数据并保存
    jaeger_fetcher = JaegerDataFetcher(f"{APP_SERVICE_NAME_MAP[args.app]}.{args.namespace}")

    # 获取 Jaeger 数据并保存
    trace_data = jaeger_fetcher.fetch_all_traces(global_start_ts_micro, global_end_ts_micro)
    jaeger_fetcher.save_traces(trace_data, experiment_dir)

    # 8. 拆分和保存 Jaeger 数据
    trace_file = os.path.join(experiment_dir, "trace_results.json")
    for start_ts, end_ts, algo_dir in timestamps:
        print(start_ts, end_ts)
        split_traces_by_time(trace_file, start_ts, end_ts, algo_dir)

    # 9. 处理所有收集到的数据
    process_all_metrics(args.app, experiment_id)

    # 10. 画CPU和Memery的图
    draw_metrics.main()

    # 11. 画jaeger的图
    draw_jaeger.main(trace_data, experiment_dir.replace("data", "fig"))

if __name__ == "__main__":
    main()
