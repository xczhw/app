import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.patches import Patch

# 确保输出目录存在
if not os.path.exists('fig'):
    os.makedirs('fig')

# 设置全局默认字体为Times New Roman
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['mathtext.fontset'] = 'stix'  # 数学字体也用近似的Times New Roman效果

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Custom color scheme
colors = {
    'RR': '#FF6666',        # 浅红色
    'LC': '#4472C4',        # 蓝色
    'RA': '#00B050',        # 翠绿色
    'background': '#D9D9D9' # 浅灰色
}

# 定义柱状图的花纹 - 使用更稀疏的花纹
hatches = {
    'RR': '/',      # 稀疏斜线
    'LC': '..',     # 稀疏点
    'RA': 'x'       # 稀疏叉
}

# Figure size with 4:3 ratio
fig_width = 6
fig_height = 4.5

# Increase font sizes
plt.rcParams.update({
    'font.size': 14,
    'axes.titlesize': 22,
    'axes.labelsize': 18,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 16
})

# --------- 图表1: Replica Eviction Rate ---------
strategies = ['RR', 'LC', 'RA']
eviction_rates = [18, 14, 3]

eviction_df = pd.DataFrame({
    'Strategy': strategies,
    'Eviction_Rate': eviction_rates
})
eviction_df.to_csv('data/eviction_rates.csv', index=False)

plt.figure(figsize=(fig_width, fig_height))
ax = plt.gca()
ax.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

bars = plt.bar(strategies, eviction_rates,
               color=[colors['RR'], colors['LC'], colors['RA']],
               width=0.6, edgecolor='black', linewidth=0.5)

# 添加更稀疏的花纹
for i, bar in enumerate(bars):
    bar.set_hatch(hatches[strategies[i]])
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
             f'{height:.1f}', ha='center', va='bottom')

#
plt.ylabel('Evictions per Node per Test Run')
plt.ylim(0, max(eviction_rates) * 1.2)

plt.tight_layout()
plt.savefig('fig/eviction_rate.pdf', dpi=300, bbox_inches='tight')
plt.close()

# --------- 图表2: Cold Start Latency ---------
latencies = [320, 280, 150]

latency_df = pd.DataFrame({
    'Strategy': strategies,
    'Latency_ms': latencies
})
latency_df.to_csv('data/cold_start_latency.csv', index=False)

plt.figure(figsize=(fig_width, fig_height))
ax = plt.gca()
ax.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

bars = plt.bar(strategies, latencies,
               color=[colors['RR'], colors['LC'], colors['RA']],
               width=0.6, edgecolor='black', linewidth=0.5)

# 添加更稀疏的花纹
for i, bar in enumerate(bars):
    bar.set_hatch(hatches[strategies[i]])
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 10,
             f'{height:.0f} ms', ha='center', va='bottom')

#
plt.ylabel('Average Request Latency (ms)')
plt.ylim(0, max(latencies) * 1.2)

plt.tight_layout()
plt.savefig('fig/cold_start_latency.pdf', dpi=300, bbox_inches='tight')
plt.close()

# --------- 图表3: Error Rate Under Pressure ---------
error_rates = [4.8, 3.7, 0.9]

error_df = pd.DataFrame({
    'Strategy': strategies,
    'Error_Rate_Percent': error_rates
})
error_df.to_csv('data/error_rates.csv', index=False)

plt.figure(figsize=(fig_width, fig_height))
ax = plt.gca()
ax.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

bars = plt.bar(strategies, error_rates,
               color=[colors['RR'], colors['LC'], colors['RA']],
               width=0.6, edgecolor='black', linewidth=0.5)

# 添加更稀疏的花纹
for i, bar in enumerate(bars):
    bar.set_hatch(hatches[strategies[i]])
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.2,
             f'{height:.1f}%', ha='center', va='bottom')

#
plt.ylabel('Error Rate (%)')
plt.ylim(0, max(error_rates) * 1.2)

plt.tight_layout()
plt.savefig('fig/error_rate_under_pressure.pdf', dpi=300, bbox_inches='tight')
plt.close()

# --------- 图表4: Routing Stability ---------
route_changes = [42, 35, 12]

routing_df = pd.DataFrame({
    'Strategy': strategies,
    'Route_Changes_Per_Minute': route_changes
})
routing_df.to_csv('data/routing_stability.csv', index=False)

plt.figure(figsize=(fig_width, fig_height))
ax = plt.gca()
ax.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

bars = plt.bar(strategies, route_changes,
               color=[colors['RR'], colors['LC'], colors['RA']],
               width=0.6, edgecolor='black', linewidth=0.5)

# 添加更稀疏的花纹
for i, bar in enumerate(bars):
    bar.set_hatch(hatches[strategies[i]])
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 1.5,
             f'{height:.0f}', ha='center', va='bottom')

#
plt.ylabel('Route Changes per Minute')
plt.ylim(0, max(route_changes) * 1.2)

plt.tight_layout()
plt.savefig('fig/routing_stability.pdf', dpi=300, bbox_inches='tight')
plt.close()

print("Data and charts have been generated successfully.")
print("Data saved to 'data/' directory")
print("Generated 4 charts with 4:3 ratio using Times New Roman font, dashed grid lines, and sparser pattern-filled bars:")
print("1. eviction_rate.pdf")
print("2. cold_start_latency.pdf")
print("3. error_rate_under_pressure.pdf")
print("4. routing_stability.pdf")