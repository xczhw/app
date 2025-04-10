import json
import os
from utils import read_timestamps

def split_traces_by_time(trace_file, start_ts, end_ts, output_dir):
    # 读取 trace 文件
    try:
        with open(trace_file, 'r') as f:
            trace_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 找不到文件 {trace_file}")
        return

    # 存储筛选后的 traces
    filter_traces = []

    # 遍历每个 trace 和其中的 spans，筛选符合时间范围的 spans
    for trace in trace_data:  # 假设根数据是一个包含 'data' 键的列表
        is_in_time_span = False
        for span in trace['data'][0]['spans']:
            span_start_time = int(span['startTime'])
            # 筛选出在指定时间范围内的 spans
            if start_ts <= span_start_time <= end_ts:
                is_in_time_span = True
                break
        if (is_in_time_span):
            filter_traces.append(trace)

    # 如果没有找到符合条件的 spans，提前退出
    if not filter_traces:
        print(f"❌ 没有找到符合时间范围的 trace 数据")
        return

    # 将拆分后的数据保存到目标文件夹
    output_file = os.path.join(output_dir, "trace_results.json")
    with open(output_file, 'w') as f:
        json.dump(filter_traces, f, indent=4)

    print(f"📊 {len(filter_traces)} 条数据已保存到 {output_file}")

def process_all_traces(app, experiment_id):
    # 遍历所有策略和时间戳，调用处理函数
    base_dir = os.path.join("data", app, str(experiment_id))
    algo_list = os.listdir(base_dir)
    trace_file = base_dir.join("trace_results.json")
    for algo in algo_list:
        algo_dir = base_dir.join(algo)
        if os.path.isdir(algo_dir):
            timestamps_file = os.path.join(algo_dir, "timestamps.txt")
            start_ts, end_ts = read_timestamps(timestamps_file)
            split_traces_by_time(trace_file, start_ts, end_ts, algo_dir)

if __name__ == '__main__':
    process_all_traces("onlineBoutique", 1743993804744946)
