import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib as mpl
from matplotlib import font_manager

# ========== 关键改动部分 ==========
# 指定Times New Roman字体路径
font_path = '/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf'
font_prop = font_manager.FontProperties(fname=font_path)

# 设置全局默认字体
# mpl.rcParams['font.family'] = font_prop.get_name()
mpl.rcParams['mathtext.fontset'] = 'stix'  # 数学字体也用Times New Roman
# ====================================

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

# Figure size with 4:3 ratio
fig_width = 10
fig_height = 7.5

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

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
             f'{height:.1f}', ha='center', va='bottom', fontsize=16,
             fontproperties=font_prop)

plt.title('Replica Eviction Rate', fontsize=22)
plt.ylabel('Evictions per Node per Test Run', fontsize=18)
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

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 10,
             f'{height:.0f} ms', ha='center', va='bottom', fontsize=16,
             fontproperties=font_prop)

plt.title('Cold Start Latency', fontsize=22)
plt.ylabel('Average Request Latency (ms)', fontsize=18)
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

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 0.2,
             f'{height:.1f}%', ha='center', va='bottom', fontsize=16,
             fontproperties=font_prop)

plt.title('Error Rate Under Pressure', fontsize=22)
plt.ylabel('Error Rate (%)', fontsize=18)
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

for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 1.5,
             f'{height:.0f}', ha='center', va='bottom', fontsize=16,
             fontproperties=font_prop)

plt.title('Routing Stability', fontsize=22)
plt.ylabel('Route Changes per Minute', fontsize=18)
plt.ylim(0, max(route_changes) * 1.2)

plt.tight_layout()
plt.savefig('fig/routing_stability.pdf', dpi=300, bbox_inches='tight')
plt.close()

print("Data and charts have been generated successfully.")
print("Data saved to 'data/' directory")
print("Generated 4 charts with 4:3 ratio using Times New Roman font and dashed grid lines:")
print("1. eviction_rate.pdf")
print("2. cold_start_latency.pdf")
print("3. error_rate_under_pressure.pdf")
print("4. routing_stability.pdf")
