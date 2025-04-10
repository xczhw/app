import os
import pandas as pd
from utils import read_timestamps

def process_metrics(app, experiment_id, algo, start_ts, end_ts):
    # 构建目录路径
    data_dir = os.path.join("data", app, experiment_id)
    metrics_file = os.path.join(data_dir, f"metrics.csv")

    # 加载原始数据
    try:
        df = pd.read_csv(metrics_file, dtype={'timestamp': int})
    except FileNotFoundError:
        print(f"❌ 找不到文件 {metrics_file}")
        return

    # 筛选出在指定时间范围内的数据
    filtered_df = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]

    # 保存筛选后的数据到目标文件夹
    output_dir = os.path.join(data_dir, algo, f"{start_ts}_{end_ts}")
    os.makedirs(output_dir, exist_ok=True)
    filtered_df.to_csv(os.path.join(output_dir, "metrics.csv"), index=False)

    print(f"📊 数据已保存到 {output_dir}/metrics.csv")

def process_all_metrics(app, experiment_id):
    # 遍历所有策略和时间戳，调用处理函数
    algo_list = os.listdir(os.path.join("data", app, experiment_id))
    print(algo_list)
    for algo in algo_list:
        algo_dir = os.path.join("data", app, experiment_id, algo)
        if os.path.isdir(algo_dir):
            timestamps_file = os.path.join(algo_dir, "timestamps.txt")
            print(timestamps_file)
            start_ts, end_ts = read_timestamps(timestamps_file)
            process_metrics(app, experiment_id, algo, start_ts, end_ts)

# 单独调试时使用的 main 函数
if __name__ == "__main__":
    # 你可以手动修改 app 和 experiment_id 来进行调试
    app = "onlineBoutique"  # 或其他应用
    experiment_id = "1743993804744946"  # 你想要处理的实验编号
    process_all_metrics(app, experiment_id)
