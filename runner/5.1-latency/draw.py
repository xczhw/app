import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os

# 确保fig目录存在
if not os.path.exists('fig'):
    os.makedirs('fig')

# 读取CSV文件
def load_data(apps):
    data = {}
    for app in apps:
        # 从data目录读取文件
        file_path = os.path.join('data', f"{app}.csv")
        
        # 读取CSV，包含表头
        df = pd.read_csv(file_path)
        
        # 将TO替换为一个大数字，用于绘图
        df = df.replace('TO', 2000)
        
        # 确保数据类型为数值
        df['P90'] = pd.to_numeric(df['P90'])
        df['P99'] = pd.to_numeric(df['P99'])
        
        data[app] = df
    return data

# 设置颜色方案
def get_color_map(algorithms):
    # 定义与参考图类似的颜色
    colors = {
        'Round Robin': '#AA0000',  # 深红色
        'Random': '#885500',       # 棕色
        'Weighted Round Robin': '#DDAA00',  # 金色
        'CPU-P2C': '#AAAA00',      # 黄色
        'Least Loaded': '#008800',  # 绿色
        'LL-P2C': '#0055DD',       # 蓝色
        'YARP-P2C': '#880088',     # 紫色
        'Linear': '#888888',       # 灰色
        'C3': '#008888',           # 青色
        'Prequal': '#AAAAAA',      # 浅灰色
        'Ring Hash': '#DD5500',    # 橙色
        'Maglev': '#00AAAA',       # 浅青色
    }
    
    # 为没有定义颜色的算法分配颜色
    missing_algs = [alg for alg in algorithms if alg not in colors]
    new_colors = sns.color_palette("husl", len(missing_algs))
    for i, alg in enumerate(missing_algs):
        colors[alg] = new_colors[i]
    
    return colors

# # 添加应用程序描述
# def add_app_description(fig, app, x_pos, y_pos):
#     descriptions = {
#         "OnlineBoutique": "Lightweight e-commerce app with 10 microservices.\nShort request paths (2-3 services).",
#         "SocialNetwork": "Moderately complex app with 28 microservices\nincluding ML components. Medium request paths (4-6 services).",
#         "TrainTicket": "Complex ticket booking system with 68 microservices.\nLong request chains (>10 services) with high concurrency."
#     }
    
#     fig.text(x_pos, y_pos, descriptions[app], fontsize=12, 
#              bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.5'),
#              ha='left', va='top')

# 为单个应用程序创建图表
def create_app_chart(app, data, color_map, max_latency=1500):
    # 创建图表
    fig, ax = plt.figure(figsize=(14, 10)), plt.gca()
    
    df = data[app]
    algorithms = df['Algorithm'].tolist()
    
    # 计算条形图位置
    bar_height = 0.7
    y_positions = np.arange(len(algorithms))
    
    # 绘制P90条形图（主色）
    p90_bars = ax.barh(y_positions, df['P90'], height=bar_height, 
                       color=[color_map[alg] for alg in df['Algorithm']], alpha=1.0)
    
    # 绘制P99条形图（浅色延伸部分）
    for j, (alg, p90, p99) in enumerate(zip(df['Algorithm'], df['P90'], df['P99'])):
        # 检查P99是否超过阈值
        if p99 >= 2000:  # 表示TO
            # 绘制到最大值
            ax.barh(y_positions[j], max_latency - p90, height=bar_height,
                   left=p90, color=color_map[alg], alpha=0.4)
            
            # 添加超出指示
            ax.text(max_latency + 20, y_positions[j] + bar_height/2 - 0.1, 
                   "TO", ha='left', va='center', 
                   color='black', fontweight='bold', fontsize=12)
        else:
            # 正常绘制P99延伸部分
            ax.barh(y_positions[j], p99 - p90, height=bar_height,
                   left=p90, color=color_map[alg], alpha=0.4)
    
    # 添加P90数值标签
    for j, bar in enumerate(p90_bars):
        width = bar.get_width()
        if width > 60:  # 只在条形足够宽时添加标签
            ax.text(width / 2, bar.get_y() + bar.get_height()/2, 
                   f"{int(width)}", ha='center', va='center', 
                   color='white', fontweight='bold', fontsize=12)
    
    # 添加P99数值标签
    for j, (alg, p90, p99) in enumerate(zip(df['Algorithm'], df['P90'], df['P99'])):
        if p99 < 2000 and p99 - p90 > 200:  # 只有当有足够空间且不是TO时
            ax.text(p90 + (p99 - p90)/2, y_positions[j] + bar_height/2, 
                   f"{int(p99)}", ha='center', va='center', 
                   color='black', fontweight='bold', fontsize=12)
    
    # 设置Y轴标签
    ax.set_yticks(y_positions)
    ax.set_yticklabels(df['Algorithm'], fontsize=14)
    
    # 设置图表标题
    ax.set_title(f"{app}", fontsize=20, pad=20)
    
    # 添加网格线
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # 设置X轴范围和标签
    ax.set_xlim(0, max_latency + 100)
    
    # X轴刻度
    x_ticks = np.arange(0, max_latency + 200, 200)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks], fontsize=12)
    
    # 添加X轴标签
    ax.set_xlabel("Latency (ms)", fontsize=16)
    
    # 添加Y轴标签
    ax.set_ylabel("Load Balancing Algorithm", fontsize=16)
    
    # # 添加应用程序描述
    # add_app_description(fig, app, 0.65, 0.95)
    
    # 创建图例
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color='gray', alpha=1.0, label='P90 Latency'),
        plt.Rectangle((0, 0), 1, 1, color='gray', alpha=0.4, label='P99 Latency')
    ]
    
    ax.legend(handles=legend_elements, loc='lower right', fontsize=12)
    
    # 添加说明注释
    fig.text(0.02, 0.01, "TO = Timeout (exceeds measurement threshold)", 
             fontsize=10, style='italic', ha='left')
    
    plt.tight_layout()
    
    # 保存图表为PDF
    file_path = os.path.join('fig', f"{app}_latency.pdf")
    plt.savefig(file_path, bbox_inches='tight')
    print(f"已保存图表: {file_path}")
    
    return fig

# 主函数
def main():
    # 应用程序名称
    apps = ["OnlineBoutique", "SocialNetwork", "TrainTicket"]
    
    # 读取数据
    data = load_data(apps)
    
    # 获取所有算法名称（从第一个应用的数据中）
    algorithms = data[apps[0]]['Algorithm'].tolist()
    
    # 创建颜色映射
    color_map = get_color_map(algorithms)
    
    # 为每个应用程序创建单独的图表
    for app in apps:
        fig = create_app_chart(app, data, color_map)
        plt.close(fig)
    
    print("所有图表已生成完毕，保存在fig目录下")

if __name__ == "__main__":
    main()