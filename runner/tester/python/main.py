import time
import os
import subprocess
from datetime import datetime
from config import args
from constants import algo_list
from utils import wait_for_pods_ready, apply_algo_yaml, save_timestamped_data
from app_launcher import deploy
from generate_destination_rules import generate_yaml
from process_metrics import process_all_metrics

def main():
    # 生成实验编号（精确时间戳）
    experiment_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"🔖 当前实验编号: {experiment_id}\n")

    # 1. 部署应用
    deploy(args.app)

    # 2. 生成 YAML
    selected_algos = algo_list if args.all_algo else [args.policy]
    generate_yaml(selected_algos, args.namespace, args.app)

    # 3. 等待 Pod 就绪
    if not wait_for_pods_ready(args.namespace):
        return

    # 4. 启动指标采集子进程
    metrics_file = f"pod_resource_usage_{args.app}.csv"
    metrics_proc = subprocess.Popen([
        "python", "kube_metrics_fetcher.py",
        "--namespace", args.namespace,
        "--interval", str(args.interval),
        "--output", metrics_file
    ])

    # 5. 应用策略并记录时间
    for algo in selected_algos:
        print(f"⏸️ 切换策略前等待 {args.pause_seconds} 秒\n")
        time.sleep(args.pause_seconds)

        apply_algo_yaml(algo, args.app)

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

    # 6. 结束指标采集子进程
    metrics_proc.terminate()
    metrics_proc.wait()
    print("📉 资源采集进程已终止")

    # 7. 自动处理所有收集到的数据
    process_all_metrics(args.app, experiment_id)

if __name__ == "__main__":
    main()
