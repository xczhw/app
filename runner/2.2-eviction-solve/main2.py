import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from utils import COLOR, LINESTYLE, MARKER, HATCH, save_figures

# 确保输出目录存在
os.makedirs('fig', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Figure size
FIG_WIDTH = 6
FIG_HEIGHT = 4.5

# 数据准备
strategies = ['RR', 'LC', 'RA']

# --------- 图表1: Replica Eviction Rate ---------
eviction_rates = [18, 14, 3]

eviction_df = pd.DataFrame({
    'Strategy': strategies,
    'Eviction_Rate': eviction_rates
})
eviction_df.to_csv('data/eviction_rates.csv', index=False)

# 创建图形和坐标轴
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

# 绘制条形图
for i, strategy in enumerate(strategies):
    ax.bar(i, eviction_rates[i],
          color=COLOR[i],
          hatch=HATCH[i+1],  # 跳过第一个None
          edgecolor='0.1',  # 边缘颜色(灰度0.1)
          linewidth=1,  # 边缘宽度
          clip_on=False)  # 确保图形元素不被裁剪

    # 添加数值标签
    height = eviction_rates[i]
    ax.text(i, height + 0.5, f'{height:.1f}',
           ha='center', va='bottom')

# 设置x刻度和标签
ax.set_xticks(range(len(strategies)))
ax.set_xticklabels(strategies)

# 设置标题和轴标签
ax.set_ylabel('Evictions per Node per Test Run')
ax.set_ylim(0, max(eviction_rates) * 1.2)

# 添加网格线
ax.grid(True, linestyle=':', alpha=0.7)

# 调整布局
plt.tight_layout()

# 保存图形
save_figures(fig, 'fig/eviction_rate')

# --------- 图表2: Cold Start Latency ---------
latencies = [320, 280, 150]

latency_df = pd.DataFrame({
    'Strategy': strategies,
    'Latency_ms': latencies
})
latency_df.to_csv('data/cold_start_latency.csv', index=False)

# 创建图形和坐标轴
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

# 绘制条形图
for i, strategy in enumerate(strategies):
    ax.bar(i, latencies[i],
          color=COLOR[i],
          hatch=HATCH[i+1],  # 跳过第一个None
          edgecolor='0.1',  # 边缘颜色(灰度0.1)
          linewidth=1,  # 边缘宽度
          clip_on=False)  # 确保图形元素不被裁剪

    # 添加数值标签
    height = latencies[i]
    ax.text(i, height + 10, f'{height:.0f} ms',
           ha='center', va='bottom')

# 设置x刻度和标签
ax.set_xticks(range(len(strategies)))
ax.set_xticklabels(strategies)

# 设置标题和轴标签
ax.set_ylabel('Average Request Latency (ms)')
ax.set_ylim(0, max(latencies) * 1.2)

# 添加网格线
ax.grid(True, linestyle=':', alpha=0.7)

# 调整布局
plt.tight_layout()

# 保存图形
save_figures(fig, 'fig/cold_start_latency')

# --------- 图表3: Error Rate Under Pressure ---------
error_rates = [4.8, 3.7, 0.9]

error_df = pd.DataFrame({
    'Strategy': strategies,
    'Error_Rate_Percent': error_rates
})
error_df.to_csv('data/error_rates.csv', index=False)

# 创建图形和坐标轴
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

# 绘制条形图
for i, strategy in enumerate(strategies):
    ax.bar(i, error_rates[i],
          color=COLOR[i],
          hatch=HATCH[i+1],  # 跳过第一个None
          edgecolor='0.1',  # 边缘颜色(灰度0.1)
          linewidth=1,  # 边缘宽度
          clip_on=False)  # 确保图形元素不被裁剪

    # 添加数值标签
    height = error_rates[i]
    ax.text(i, height + 0.2, f'{height:.1f}%',
           ha='center', va='bottom')

# 设置x刻度和标签
ax.set_xticks(range(len(strategies)))
ax.set_xticklabels(strategies)

# 设置标题和轴标签
ax.set_ylabel('Error Rate (%)')
ax.set_ylim(0, max(error_rates) * 1.2)

# 添加网格线
ax.grid(True, linestyle=':', alpha=0.7)

# 调整布局
plt.tight_layout()

# 保存图形
save_figures(fig, 'fig/error_rate_under_pressure')

# --------- 图表4: Routing Stability ---------
route_changes = [42, 35, 12]

routing_df = pd.DataFrame({
    'Strategy': strategies,
    'Route_Changes_Per_Minute': route_changes
})
routing_df.to_csv('data/routing_stability.csv', index=False)

# 创建图形和坐标轴
fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))

# 绘制条形图
for i, strategy in enumerate(strategies):
    ax.bar(i, route_changes[i],
          color=COLOR[i],
          hatch=HATCH[i+1],  # 跳过第一个None
          edgecolor='0.1',  # 边缘颜色(灰度0.1)
          linewidth=1,  # 边缘宽度
          clip_on=False)  # 确保图形元素不被裁剪

    # 添加数值标签
    height = route_changes[i]
    ax.text(i, height + 1.5, f'{height:.0f}',
           ha='center', va='bottom')

# 设置x刻度和标签
ax.set_xticks(range(len(strategies)))
ax.set_xticklabels(strategies)

# 设置标题和轴标签
ax.set_ylabel('Route Changes per Minute')
ax.set_ylim(0, max(route_changes) * 1.2)

# 添加网格线
ax.grid(True, linestyle=':', alpha=0.7)

# 调整布局
plt.tight_layout()

# 保存图形
save_figures(fig, 'fig/routing_stability')

print("Data and charts have been generated successfully.")
print("Data saved to 'data/' directory")
print("Generated 4 charts using the utils style:")
print("1. eviction_rate.svg/pdf/png")
print("2. cold_start_latency.svg/pdf/png")
print("3. error_rate_under_pressure.svg/pdf/png")
print("4. routing_stability.svg/pdf/png")