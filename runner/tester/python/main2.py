import os
import signal
import sys
from config import args

import draw_metrics
import draw_duration
from constants import ALGO_LIST, APP_SERVICE_NAME_MAP
from JaegerDataFetcher import JaegerDataFetcher
from app_launcher import deploy, remove
import generate_destination_rules
from process_metrics import process_all_metrics
from process_trace import split_traces_by_time
from utils import wait_for_pods_ready, wait_for_pods_cleanup, apply_algo_yaml, utc_microtime, sleep_with_progress_bar, read_timestamps
from kube_metrics_fetcher import MetricsCollector  # 线程采集器

def run_algo(algo, experiment_dir):
    algo_dir = os.path.join(experiment_dir, algo)
    os.makedirs(algo_dir, exist_ok=True)

    collector = None

    try:
        # 1. 部署应用
        deploy(args.app, args.replicas)

        # 2. 等待 Pod 就绪
        if not wait_for_pods_ready(args.namespace):
            print("❌ 部分 Pod 未就绪，跳过本轮策略\n")
            return

        # 3. 应用策略
        apply_algo_yaml(algo, args.app)

        print(f"⏸️ 部署完成后等待 {args.pause_seconds} 秒\n")
        sleep_with_progress_bar(args.pause_seconds, "策略切换等待中")

        # 4. 启动指标采集线程
        metrics_file = os.path.join(algo_dir, "metrics.csv")
        collector = MetricsCollector(args.namespace, args.interval, metrics_file)
        collector.start()

        # 5. 策略运行
        start_ts = utc_microtime()
        print(f"🕒 开始时间: {start_ts}")

        sleep_with_progress_bar(args.run_seconds, "策略运行中")

        end_ts = utc_microtime()
        print(f"🕒 结束时间: {end_ts}")

        # 6. 停止采集器
        if collector:
            collector.stop()
            collector.join()
            print("📉 指标采集线程已终止")

        # 7. 保存时间戳
        with open(os.path.join(algo_dir, "timestamps.txt"), "w") as f:
            f.write(f"Start: {start_ts}\nEnd: {end_ts}\n")
        print(f"📁 时间戳保存至: {algo_dir}\n")

        # 8. 清理 Pod
        remove(args.app)
        if not wait_for_pods_cleanup(args.namespace):
            print("❌ Pod 清理失败，请检查！")
            return

        # 9. 拉取 Jaeger trace 数据并保存
        jaeger_fetcher = JaegerDataFetcher(f"{APP_SERVICE_NAME_MAP[args.app]}.{args.namespace}")
        start_ts, end_ts = read_timestamps(os.path.join(algo_dir, "timestamps.txt"))
        trace_data = jaeger_fetcher.fetch_all_traces(start_ts, end_ts)
        jaeger_fetcher.save_traces(trace_data, algo_dir)

    except Exception as e:
        print(f"❌ 主程序出错：{e}")
    finally:
        if collector and collector.is_alive():
            collector.stop()
            collector.join()

def draw(experiment_dir):
    draw_metrics.main(experiment_dir)
    draw_duration.main(experiment_dir)

def runner(experiment_dir, selected_algos):
    generate_destination_rules.main(selected_algos, args.namespace, args.app)

    for algo in selected_algos:
        run_algo(algo, experiment_dir)

    draw(experiment_dir)

def main():
    experiment_id = str(utc_microtime())
    print(f"🔖 当前实验编号: {experiment_id}\n")
    experiment_dir = os.path.join("data", args.app, experiment_id)
    os.makedirs(experiment_dir, exist_ok=True)

    selected_algos = ALGO_LIST if args.all_algo else [args.policy]

    runner(experiment_dir, selected_algos)

if __name__ == "__main__":
    main()
