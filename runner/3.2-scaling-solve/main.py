import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd

# 创建目录
os.makedirs('data', exist_ok=True)
os.makedirs('fig', exist_ok=True)

# 设置全局字体为Times New Roman
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'  # 数学字体设置
# Figure size with 4:3 ratio
fig_width = 6
fig_height = 4.5

# 集中定义所有字体大小相关设置
FONT_SIZES = {
    'base': 20,                # 基础字体大小
    'title': 20,               # 标题字体大小
    'axes_label': 20,          # 轴标签字体大小
    'tick_label': 20,          # 刻度标签字体大小
    'legend': 14,              # 图例字体大小
    'annotation': 20,          # 注释文本字体大小
}

# 应用全局字体大小设置
plt.rcParams.update({
    'font.size': FONT_SIZES['base'],
    'axes.titlesize': FONT_SIZES['title'],
    'axes.labelsize': FONT_SIZES['axes_label'],
    'xtick.labelsize': FONT_SIZES['tick_label'],
    'ytick.labelsize': FONT_SIZES['tick_label'],
    'legend.fontsize': FONT_SIZES['legend']
})

# 定义颜色方案
colors = {
    'cpu_pod': '#D9D9D9',  # 浅灰色
    'cpu_avg': '#4472C4',  # 蓝色
    'p90': '#00B0F0',      # 青蓝色
    'p99': '#FF6666',      # 浅红色
    'timeout': '#FF6666',  # 浅红色
    'success_rps': '#00B050',  # 翠绿色
    'total_rps': '#8064A2',    # 淡紫色
    'failed_area': '#FFE6E6'   # 极浅粉色
}

# 模拟时间 - 每个数据点约15秒，总时长25分钟
points_per_minute = 4  # 每分钟4个点 (每点15秒)
total_minutes = 25
total_points = total_minutes * points_per_minute

# 创建时间数组，单位为分钟
time_points = np.linspace(0, total_minutes, total_points)

# 添加适当的X轴标签位置
time_ticks = np.arange(0, total_minutes + 1, 5)  # 每5分钟一个主刻度

# 简单流量模式：逐渐上升然后下降
traffic = np.concatenate([
    np.linspace(10, 100, int(total_points * 0.4)),  # 上升
    np.ones(int(total_points * 0.2)) * 100,         # 稳定高峰
    np.linspace(100, 20, int(total_points * 0.4))   # 下降
])

# 确保traffic长度与time_points一致
if len(traffic) < len(time_points):
    traffic = np.pad(traffic, (0, len(time_points) - len(traffic)), 'edge')
elif len(traffic) > len(time_points):
    traffic = traffic[:len(time_points)]

# 给流量添加一些随机波动
np.random.seed(42)  # 设置随机种子以保证结果可复现
traffic += np.random.normal(0, 5, len(traffic))
traffic = np.maximum(traffic, 0)  # 确保非负

# 模拟延迟
def simulate_latency(traffic, replicas, scaling_events):
    # 基础延迟与流量/副本数成正比
    base_latency = np.minimum(100, traffic / replicas * 5)

    # 添加一些随机波动
    base_latency += np.random.normal(0, 2, len(base_latency))

    # 冷启动延迟惩罚
    cold_start_penalty = np.zeros_like(base_latency)
    for event in scaling_events:
        time_idx, old_replicas, new_replicas, action = event
        if action == "scale-up":
            # 冷启动后的20个时间单位内延迟较高（约5分钟）
            for i in range(time_idx, min(time_idx + points_per_minute, len(cold_start_penalty))):
                cold_start_penalty[i] += 30 * (new_replicas - old_replicas) / new_replicas  # 新副本的冷启动惩罚

    # 总延迟 = 基础延迟 + 冷启动惩罚
    latency = base_latency + cold_start_penalty

    # 计算p90, p99延迟 (之前的p50改为p90)
    p90_latency = np.zeros_like(latency)
    p99_latency = np.zeros_like(latency)

    window_size = points_per_minute * 2  # 计算百分位数的窗口大小（约2分钟）
    for i in range(len(latency)):
        start_idx = max(0, i - window_size)
        window = latency[start_idx:i+1]
        p90_latency[i] = np.percentile(window, 90)  # 改为p90
        p99_latency[i] = np.percentile(window, 99)

    return latency, p90_latency, p99_latency

# 基准配置：立即响应的自动缩放
def baseline_scaling(traffic):
    replicas = np.zeros_like(traffic)
    replicas[0] = 2  # 初始副本数
    scaling_events = []
    cpu_usage = np.zeros_like(traffic)

    for i in range(1, len(traffic)):
        # 计算当前CPU使用率
        cpu_usage[i-1] = min(100, traffic[i-1] / replicas[i-1] * 10)

        # 简单逻辑：当负载每增加10，增加一个副本；当负载每减少10，减少一个副本
        new_replicas = max(2, int(traffic[i] / 20))
        if new_replicas != replicas[i-1]:
            scaling_events.append((i, replicas[i-1], new_replicas,
                                  "scale-up" if new_replicas > replicas[i-1] else "scale-down"))
        replicas[i] = new_replicas

    # 计算最后一个时间点的CPU使用率
    cpu_usage[-1] = min(100, traffic[-1] / replicas[-1] * 10)

    # 计算延迟
    latency, p90, p99 = simulate_latency(traffic, replicas, scaling_events)

    return replicas, scaling_events, cpu_usage, latency, p90, p99

# 解耦设计：滞后响应的自动缩放
def decoupled_scaling(traffic):
    replicas = np.zeros_like(traffic)
    replicas[0] = 2  # 初始副本数
    scaling_events = []
    cpu_usage = np.zeros_like(traffic)

    # 使用滑动窗口平均来平滑流量
    window_size = points_per_minute  # 1分钟窗口
    smoothed_traffic = np.copy(traffic)
    for i in range(window_size, len(traffic)):
        smoothed_traffic[i] = np.mean(traffic[i-window_size:i+1])

    for i in range(1, len(traffic)):
        # 计算CPU使用率
        cpu_usage[i-1] = min(100, traffic[i-1] / replicas[i-1] * 10)

        # 只有当平滑后的流量变化足够大时才缩放
        if i >= window_size:
            new_replicas = max(2, int(smoothed_traffic[i] / 25))
            if new_replicas != replicas[i-1]:
                scaling_events.append((i, replicas[i-1], new_replicas,
                                      "scale-up" if new_replicas > replicas[i-1] else "scale-down"))
            replicas[i] = new_replicas
        else:
            replicas[i] = replicas[i-1]

    # 计算最后一个时间点的CPU使用率
    cpu_usage[-1] = min(100, traffic[-1] / replicas[-1] * 10)

    # 计算延迟
    latency, p90, p99 = simulate_latency(traffic, replicas, scaling_events)

    return replicas, scaling_events, cpu_usage, latency, p90, p99

# 运行模拟
baseline_replicas, baseline_events, baseline_cpu, baseline_latency, baseline_p90, baseline_p99 = baseline_scaling(traffic)
decoupled_replicas, decoupled_events, decoupled_cpu, decoupled_latency, decoupled_p90, decoupled_p99 = decoupled_scaling(traffic)

# 计算减少百分比
scaling_actions_reduction = (len(baseline_events) - len(decoupled_events)) / len(baseline_events) * 100

# 保存数据
results = {
    'Time (min)': time_points,
    'Traffic': traffic,
    'Baseline_Replicas': baseline_replicas,
    'Baseline_CPU': baseline_cpu,
    'Baseline_Latency': baseline_latency,
    'Baseline_p90': baseline_p90,
    'Baseline_p99': baseline_p99,
    'Decoupled_Replicas': decoupled_replicas,
    'Decoupled_CPU': decoupled_cpu,
    'Decoupled_Latency': decoupled_latency,
    'Decoupled_p90': decoupled_p90,
    'Decoupled_p99': decoupled_p99
}
df = pd.DataFrame(results)
df.to_csv('data/scaling_results.csv', index=False)

# 保存摘要
summary = {
    'Metric': ['Scaling Events', 'p90 Latency (avg)', 'p99 Latency (avg)'],
    'Baseline': [len(baseline_events), np.mean(baseline_p90), np.mean(baseline_p99)],
    'Decoupled': [len(decoupled_events), np.mean(decoupled_p90), np.mean(decoupled_p99)],
    'Reduction_Percentage': [
        scaling_actions_reduction,
        (np.mean(baseline_p90) - np.mean(decoupled_p90)) / np.mean(baseline_p90) * 100,
        (np.mean(baseline_p99) - np.mean(decoupled_p99)) / np.mean(baseline_p99) * 100
    ]
}
summary_df = pd.DataFrame(summary)
summary_df.to_csv('data/summary.csv', index=False)

# 设置X轴标签函数
def set_time_axis(ax):
    ax.set_xticks(time_ticks)
    ax.set_xlim(0, total_minutes)
    ax.set_xlabel('Time (min)')

# 图1：流量模式
plt.figure(figsize=(fig_width, fig_height))
plt.plot(time_points, traffic, color=colors['total_rps'], linewidth=3)

set_time_axis(plt.gca())
plt.ylabel('Requests Per Seconds')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('fig/traffic_pattern.pdf')
plt.close()

# 图2：副本数对比
plt.figure(figsize=(fig_width, fig_height))
plt.plot(time_points, baseline_replicas, color=colors['p99'], linewidth=3, label='Baseline')
plt.plot(time_points, decoupled_replicas, color=colors['cpu_avg'], linewidth=3, label='Decoupled')

set_time_axis(plt.gca())
plt.ylabel('Number of Replicas')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig('fig/replicas_comparison.pdf')
plt.close()

# # 图3：CPU使用率对比
# plt.figure(figsize=(fig_width, fig_height))
# plt.plot(time_points, baseline_cpu, color=colors['p99'], linewidth=3, label='Baseline')
# plt.plot(time_points, decoupled_cpu, color=colors['cpu_avg'], linewidth=3, label='Decoupled')
# plt.axhline(y=50, color=colors['p90'], linestyle='--', linewidth=2, label='Threshold')
#
# set_time_axis(plt.gca())
# plt.ylabel('CPU Utilization (%)')
# plt.grid(True, alpha=0.3)
# plt.legend()
# plt.tight_layout()
# plt.savefig('fig/cpu_comparison.pdf')
# plt.close()

# 图4：合并p90和p99延迟对比到一张图
plt.figure(figsize=(fig_width, fig_height))

# 绘制p90延迟
plt.plot(time_points, baseline_p90, color=colors['p90'], linewidth=3,
         linestyle='-', label='Baseline p90')
plt.plot(time_points, decoupled_p90, color=colors['p90'], linewidth=3,
         linestyle='--', label='Decoupled p90')

# 绘制p99延迟
plt.plot(time_points, baseline_p99, color=colors['p99'], linewidth=3,
         linestyle='-', label='Baseline p99')
plt.plot(time_points, decoupled_p99, color=colors['p99'], linewidth=3,
         linestyle='--', label='Decoupled p99')


set_time_axis(plt.gca())
plt.ylabel('Latency (ms)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig('fig/latency_percentiles_comparison.pdf')
plt.close()

# 图5：性能指标对比（条形图，带稀疏花纹）
plt.figure(figsize=(fig_width, fig_height))
plt.grid(True, alpha=0.3, zorder=0)
metrics = ['Scaling', 'p90(ms)', 'p99(ms)']
baseline_values = [len(baseline_events), np.mean(baseline_p90), np.mean(baseline_p99)]
decoupled_values = [len(decoupled_events), np.mean(decoupled_p90), np.mean(decoupled_p99)]

x = np.arange(len(metrics))
width = 0.35

# 带稀疏花纹但保留颜色的柱状图
baseline_bars = plt.bar(x - width/2, baseline_values, width,
                       label='Baseline', color=colors['p99'],
                       edgecolor='black', linewidth=1.5,
                       hatch='/', zorder=2)  # 更稀疏的斜线图案
decoupled_bars = plt.bar(x + width/2, decoupled_values, width,
                        label='Decoupled', color=colors['cpu_avg'],
                        edgecolor='black', linewidth=1.5,
                        hatch='.', zorder=2)  # 更稀疏的点状图案

# 添加数值标签
for i, v in enumerate(baseline_values):
    plt.text(i - width/2, v, f"{v:.1f}",
             ha='center', va='bottom', fontsize=FONT_SIZES['annotation'], zorder=3)
for i, v in enumerate(decoupled_values):
    plt.text(i + width/2, v, f"{v:.1f}",
             ha='center', va='bottom', fontsize=FONT_SIZES['annotation'], zorder=3)

plt.ylim(0, max(max(baseline_values), max(decoupled_values)) * 1.2)
plt.xticks(x, metrics)
plt.ylabel('Value')

plt.legend()
plt.tight_layout()
plt.savefig('fig/metrics_comparison.pdf')
plt.close()

# 打印结果
print("模拟完成！数据已保存到data/目录，图表已保存到fig/目录。")
print(f"\n基准配置扩缩容事件: {len(baseline_events)}")
print(f"解耦设计扩缩容事件: {len(decoupled_events)}")
print(f"扩缩容事件减少: {scaling_actions_reduction:.1f}%")
print(f"\np90延迟对比:")
print(f"基准配置: {np.mean(baseline_p90):.2f} ms")
print(f"解耦设计: {np.mean(decoupled_p90):.2f} ms")
print(f"\np99延迟对比:")
print(f"基准配置: {np.mean(baseline_p99):.2f} ms")
print(f"解耦设计: {np.mean(decoupled_p99):.2f} ms")