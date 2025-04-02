import json
import os
from datetime import datetime, timezone

def split_traces_by_time(trace_file, start_ts, end_ts, output_dir):
    # 读取 trace 文件
    try:
        with open(trace_file, 'r') as f:
            trace_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 找不到文件 {trace_file}")
        return

    # 转换时间戳为 datetime 对象，方便比对
    start_dt = datetime.strptime(start_ts, "%Y%m%d%H%M%S%f")
    end_dt = datetime.strptime(end_ts, "%Y%m%d%H%M%S%f")

    # 存储筛选后的 traces
    filter_traces = []

    # 遍历每个 trace 和其中的 spans，筛选符合时间范围的 spans
    for trace in trace_data:  # 假设根数据是一个包含 'data' 键的列表
        is_in_time_span = False
        for span in trace['data'][0]['spans']:
            span_start_time = span['startTime']
            span_start_dt = datetime.fromtimestamp(span_start_time / 1e6)
            # 筛选出在指定时间范围内的 spans
            if start_dt <= span_start_dt <= end_dt:
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

if __name__ == '__main__':
    split_traces_by_time("data/onlineBoutique/20250330-101115/trace_results.json",
                         "20250330101124047152", "20250330101234057470", "data/onlineBoutique/20250330-101115/RANDOM")
