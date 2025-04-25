import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import random
import pandas as pd
import os
import datetime
import copy

# 创建结果文件夹
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
results_dir = f"load_balancing_results_{timestamp}"
os.makedirs(results_dir, exist_ok=True)

class Replica:
    def __init__(self, id):
        self.id = id
        self.cpu_usage = 0
        self.requests_handled = 0
        self.history = deque(maxlen=100)  # 存储最近的延迟记录

    def handle_request(self, request_id):
        # 使用请求ID来生成确定性的随机数，确保不同算法对相同请求有相同的波动
        random.seed(request_id)

        # 每个请求增加0.5%的CPU使用率，但有一些自然波动 (±20%)
        cpu_increase = 0.5 * random.uniform(0.8, 1.2)
        self.cpu_usage += cpu_increase
        self.requests_handled += 1

        # 计算延迟：当CPU使用率低于阈值时，延迟在基准值附近波动
        # 当CPU使用率超过阈值时，延迟会增加
        base_latency = 10
        safe_threshold = 70  # 安全阈值为60%

        if self.cpu_usage <= safe_threshold:
            # 基本延迟有±15%的自然波动
            latency = base_latency * random.uniform(0.85, 1.15)
        else:
            # 超过阈值后延迟非线性增加
            over_ratio = (self.cpu_usage - safe_threshold) / 15
            # 使用sigmoid函数使延迟增长更自然
            growth_factor = 1 + 0.5 * (1 / (1 + np.exp(-over_ratio)))
            latency = base_latency * growth_factor * random.uniform(0.9, 1.1)

            # 当CPU超过75%，延迟急剧增加
            if self.cpu_usage > 75:
                latency *= 1.5 + (self.cpu_usage - 75) / 10

        self.history.append(latency)
        return latency

    # def cool_down(self, time_step):
    #     # 使用时间步来生成确定性的随机数
    #     random.seed(time_step * 1000 + self.id)

    #     # 每个时间单位CPU使用率自然下降，增加一些波动
    #     cool_amount = 2.0 * random.uniform(0.9, 1.1)
    #     self.cpu_usage = max(0, self.cpu_usage - cool_amount)

    def get_avg_latency(self):
        if not self.history:
            return 0
        return np.mean(self.history)

    def get_p95_latency(self):
        if len(self.history) < 20:
            return 0
        return np.percentile(list(self.history), 95)

    def get_p99_latency(self):
        if len(self.history) < 100:
            return 0
        return np.percentile(list(self.history), 99)


class LoadBalancer:
    def __init__(self, num_replicas, strategy="rr"):
        self.replicas = [Replica(i) for i in range(num_replicas)]
        self.strategy = strategy
        self.next_replica = 0  # 用于RR策略
        self.total_requests = 0
        self.route_changes = 0
        self.last_used_replica = None
        self.request_distribution = [0] * num_replicas  # 追踪请求分布
        self.safe_threshold = 60  # CILB安全阈值

    def route_request(self, request_id):
        self.total_requests += 1

        if self.strategy == "rr":  # Round Robin
            replica = self.replicas[self.next_replica]
            self.next_replica = (self.next_replica + 1) % len(self.replicas)

        elif self.strategy == "lc":  # Least CPU
            replica = min(self.replicas, key=lambda r: r.cpu_usage)

        elif self.strategy == "cilb":  # Controlled Imbalance Load Balancing
            # 找出CPU使用率低于阈值的replica
            safe_replicas = [r for r in self.replicas if r.cpu_usage <= self.safe_threshold]

            if safe_replicas:
                # 选择使用率最高但仍在安全范围内的replica
                replica = max(safe_replicas, key=lambda r: r.cpu_usage)
            else:
                # 如果没有安全的replica，选择CPU使用率最低的
                replica = min(self.replicas, key=lambda r: r.cpu_usage)

        # 追踪路由变化
        if self.last_used_replica is not None and self.last_used_replica.id != replica.id:
            self.route_changes += 1
        self.last_used_replica = replica

        # 更新请求分布
        self.request_distribution[replica.id] += 1

        # 处理请求
        latency = replica.handle_request(request_id)
        return replica.id, latency

    # def cool_down_all(self, time_step):
    #     for replica in self.replicas:
    #         replica.cool_down(time_step)

    def get_active_replicas(self, threshold=0.5):
        # 计算活跃的副本数量（至少处理了0.5%的CPU使用率）
        return sum(1 for r in self.replicas if r.cpu_usage > threshold)

    def get_cpu_hours(self):
        # 计算总CPU使用时间（单位：百分比-小时）
        return sum(r.cpu_usage for r in self.replicas) / 100

    def get_avg_latency(self):
        handled = sum(r.requests_handled for r in self.replicas)
        if handled == 0:
            return 0
        total_latency = sum(r.get_avg_latency() * r.requests_handled for r in self.replicas)
        return total_latency / handled

    def get_p95_latency(self):
        all_latencies = []
        for r in self.replicas:
            all_latencies.extend(r.history)
        if not all_latencies:
            return 0
        return np.percentile(all_latencies, 95)

    def get_p99_latency(self):
        all_latencies = []
        for r in self.replicas:
            all_latencies.extend(r.history)
        if not all_latencies:
            return 0
        return np.percentile(all_latencies, 99)

    def get_request_distribution(self):
        # 返回请求分布的百分比
        total = sum(self.request_distribution)
        if total == 0:
            return [0] * len(self.request_distribution)
        return [count / total * 100 for count in self.request_distribution]

    def get_total_cpu_usage(self):
        # 计算所有replica的总CPU使用率
        return sum(r.cpu_usage for r in self.replicas)


def generate_request_sequence(pattern, time_steps, seed=42):
    """生成确定性的请求序列，确保所有算法使用相同的请求模式"""
    random.seed(seed)
    np.random.seed(seed)

    requests_per_step = []
    request_ids = []  # 追踪每个请求的唯一ID

    # 不同的请求模式
    if pattern == "stable":
        # 稳定负载，每个时间步有30个请求，添加小波动
        for t in range(time_steps):
            random.seed(seed + t)
            rps = int(15 * random.uniform(0.9, 1.1))
            requests_per_step.append(rps)
            # 为每个请求生成唯一ID
            request_ids.append([seed * 10000 + t * 100 + i for i in range(rps)])

    elif pattern == "bursty":
        # 突发流量模式
        for t in range(time_steps):
            random.seed(seed + t)
            if t % 20 < 15:  # 15个时间步正常流量
                rps = int(25 * random.uniform(0.85, 1.15))
            else:  # 5个时间步高流量
                rps = int(60 * random.uniform(0.9, 1.1))
            requests_per_step.append(rps)
            request_ids.append([seed * 10000 + t * 100 + i for i in range(rps)])

    elif pattern == "ramp_up":
        # 逐渐增加流量，添加波动
        for t in range(time_steps):
            random.seed(seed + t)
            base_request = 5 + (60 * t / time_steps)
            rps = int(base_request * random.uniform(0.9, 1.1))
            requests_per_step.append(rps)
            request_ids.append([seed * 10000 + t * 100 + i for i in range(rps)])

    return requests_per_step, request_ids


def run_simulation(strategy, pattern, time_steps, num_replicas=10, seed=42):
    # 生成确定性的请求序列
    requests_per_step, request_ids = generate_request_sequence(pattern, time_steps, seed)

    lb = LoadBalancer(num_replicas, strategy)

    # 统计数据
    cpu_usage_history = []
    active_replicas_history = []
    p95_latency_history = []
    p99_latency_history = []
    avg_latency_history = []
    total_cpu_usage_history = []
    rps_to_latency = {}  # 记录每个RPS值对应的延迟

    # 运行模拟
    for t in range(time_steps):
        requests = requests_per_step[t]

        # 处理该时间步的所有请求
        for req_id in request_ids[t]:
            lb.route_request(req_id)

        # 收集统计数据
        cpu_stats = [r.cpu_usage for r in lb.replicas]
        total_cpu = lb.get_total_cpu_usage()
        cpu_usage_history.append(cpu_stats.copy())
        active_replicas_history.append(lb.get_active_replicas())
        p95_latency = lb.get_p95_latency()
        p99_latency = lb.get_p99_latency()
        avg_latency = lb.get_avg_latency()

        p95_latency_history.append(p95_latency)
        p99_latency_history.append(p99_latency)
        avg_latency_history.append(avg_latency)
        total_cpu_usage_history.append(total_cpu)

        # 记录RPS到延迟的映射
        rps = requests
        if rps not in rps_to_latency:
            rps_to_latency[rps] = []
        rps_to_latency[rps].append({
            'p95': p95_latency,
            'p99': p99_latency,
            'avg': avg_latency,
            'cpu': total_cpu
        })

        # # 每个时间步后冷却
        # lb.cool_down_all(t)

    # 计算每个RPS的平均指标
    rps_metrics = {}
    for rps, metrics_list in rps_to_latency.items():
        rps_metrics[rps] = {
            'p95': np.mean([m['p95'] for m in metrics_list]),
            'p99': np.mean([m['p99'] for m in metrics_list]),
            'avg': np.mean([m['avg'] for m in metrics_list]),
            'cpu': np.mean([m['cpu'] for m in metrics_list])
        }

    # 计算总体统计数据
    results = {
        "avg_active_replicas": np.mean(active_replicas_history),
        "cpu_hours": lb.get_cpu_hours(),
        "avg_latency": lb.get_avg_latency(),
        "p95_latency": lb.get_p95_latency(),
        "p99_latency": lb.get_p99_latency(),
        "route_changes": lb.route_changes,
        "cpu_usage_history": cpu_usage_history,
        "active_replicas_history": active_replicas_history,
        "p95_latency_history": p95_latency_history,
        "p99_latency_history": p99_latency_history,
        "avg_latency_history": avg_latency_history,
        "total_cpu_usage_history": total_cpu_usage_history,
        "request_distribution": lb.get_request_distribution(),
        "requests_per_step": requests_per_step,
        "rps_metrics": rps_metrics
    }

    return results


def save_simulation_data(results, pattern, results_dir):
    """将模拟数据保存到CSV文件"""
    for strategy, data in results.items():
        # 保存CPU利用率历史
        cpu_df = pd.DataFrame(data["cpu_usage_history"])
        cpu_df.columns = [f"Replica_{i}" for i in range(cpu_df.shape[1])]
        cpu_df.to_csv(f"{results_dir}/{pattern}_{strategy}_cpu_usage.csv", index=False)

        # 保存其他时间序列数据
        timeseries_data = {
            "Time": list(range(len(data["active_replicas_history"]))),
            "Active_Replicas": data["active_replicas_history"],
            "P95_Latency": data["p95_latency_history"],
            "P99_Latency": data["p99_latency_history"],
            "Avg_Latency": data["avg_latency_history"],
            "Total_CPU": data["total_cpu_usage_history"],
            "Requests": data["requests_per_step"]
        }
        timeseries_df = pd.DataFrame(timeseries_data)
        timeseries_df.to_csv(f"{results_dir}/{pattern}_{strategy}_timeseries.csv", index=False)

        # 保存请求分布
        dist_df = pd.DataFrame({
            "Replica": [f"Replica_{i}" for i in range(len(data["request_distribution"]))],
            "Percentage": data["request_distribution"]
        })
        dist_df.to_csv(f"{results_dir}/{pattern}_{strategy}_request_distribution.csv", index=False)

        # 保存RPS到延迟的映射
        rps_data = []
        for rps, metrics in data["rps_metrics"].items():
            rps_data.append({
                "RPS": rps,
                "P95_Latency": metrics["p95"],
                "P99_Latency": metrics["p99"],
                "Avg_Latency": metrics["avg"],
                "Total_CPU": metrics["cpu"]
            })
        rps_df = pd.DataFrame(rps_data)
        rps_df.to_csv(f"{results_dir}/{pattern}_{strategy}_rps_metrics.csv", index=False)

    # 保存聚合指标
    metrics = []
    for strategy, data in results.items():
        metrics.append({
            "Strategy": strategy,
            "Pattern": pattern,
            "Avg_Active_Replicas": data["avg_active_replicas"],
            "CPU_Hours": data["cpu_hours"],
            "Avg_Latency": data["avg_latency"],
            "P95_Latency": data["p95_latency"],
            "P99_Latency": data["p99_latency"],
            "Route_Changes": data["route_changes"]
        })
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(f"{results_dir}/{pattern}_summary_metrics.csv", index=False)


def plot_cpu_utilization(results, pattern, results_dir):
    """绘制CPU利用率图表"""
    strategies = list(results.keys())
    fig, axs = plt.subplots(len(strategies), 1, figsize=(12, 15))

    for i, strategy in enumerate(strategies):
        data = results[strategy]["cpu_usage_history"]
        time_steps = len(data)

        for j in range(len(data[0])):
            replica_data = [data[t][j] for t in range(time_steps)]
            axs[i].plot(replica_data, alpha=0.7, linewidth=1, label=f"Replica {j}")

        # 添加总请求量作为背景参考
        ax2 = axs[i].twinx()
        requests = results[strategy]["requests_per_step"]
        ax2.plot(requests, color='gray', linestyle='--', alpha=0.3, label="Requests")
        ax2.set_ylabel("Requests per step", color='gray')

        # 添加安全阈值线
        axs[i].axhline(y=60, color='r', linestyle='--', alpha=0.7, label="Safety Threshold (60%)")
        # 添加性能下降阈值线
        axs[i].axhline(y=75, color='orange', linestyle='--', alpha=0.7, label="Performance Degradation (75%)")

        axs[i].set_title(f"{strategy.upper()} - CPU Utilization")
        axs[i].set_ylabel("CPU Usage (%)")
        axs[i].set_ylim(0, 100)
        axs[i].legend(loc='upper left')

        if i == len(strategies) - 1:
            axs[i].set_xlabel("Time Steps")

    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_cpu_utilization.png", dpi=300)
    plt.close()


def plot_total_cpu_comparison(results, pattern, results_dir):
    """绘制总CPU使用率对比图"""
    plt.figure(figsize=(12, 6))

    for strategy in results.keys():
        data = results[strategy]["total_cpu_usage_history"]
        plt.plot(data, label=f"{strategy.upper()}", linewidth=2)

    # 添加请求量作为背景参考
    ax2 = plt.gca().twinx()
    # 所有策略的请求模式相同，取第一个
    requests = list(results.values())[0]["requests_per_step"]
    ax2.plot(requests, color='gray', linestyle='--', alpha=0.3, label="Requests")
    ax2.set_ylabel("Requests per step", color='gray')

    plt.title(f"Total CPU Usage - {pattern.capitalize()} Load")
    plt.ylabel("Total CPU Usage (%)")
    plt.xlabel("Time Steps")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_total_cpu_comparison.png", dpi=300)
    plt.close()


def plot_active_replicas(results, pattern, results_dir):
    """绘制活跃副本数量图表"""
    plt.figure(figsize=(12, 6))

    for strategy in results.keys():
        data = results[strategy]["active_replicas_history"]
        plt.plot(data, label=f"{strategy.upper()}", linewidth=2)

    # 添加请求量作为背景参考
    ax2 = plt.gca().twinx()
    requests = list(results.values())[0]["requests_per_step"]
    ax2.plot(requests, color='gray', linestyle='--', alpha=0.3, label="Requests")
    ax2.set_ylabel("Requests per step", color='gray')

    plt.title(f"Active Replicas - {pattern.capitalize()} Load")
    plt.ylabel("Number of Active Replicas")
    plt.xlabel("Time Steps")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_active_replicas.png", dpi=300)
    plt.close()


def plot_latency(results, pattern, results_dir):
    """绘制延迟图表"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # P95 延迟
    for strategy in results.keys():
        data = results[strategy]["p95_latency_history"]
        ax1.plot(data, label=f"{strategy.upper()}", linewidth=2)

    # 添加请求量作为背景参考
    ax1_twin = ax1.twinx()
    requests = list(results.values())[0]["requests_per_step"]
    ax1_twin.plot(requests, color='gray', linestyle='--', alpha=0.3, label="Requests")
    ax1_twin.set_ylabel("Requests per step", color='gray')

    ax1.set_title(f"P95 Latency - {pattern.capitalize()} Load")
    ax1.set_ylabel("Latency (ms)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # P99 延迟
    for strategy in results.keys():
        data = results[strategy]["p99_latency_history"]
        ax2.plot(data, label=f"{strategy.upper()}", linewidth=2)

    # 添加请求量作为背景参考
    ax2_twin = ax2.twinx()
    ax2_twin.plot(requests, color='gray', linestyle='--', alpha=0.3, label="Requests")
    ax2_twin.set_ylabel("Requests per step", color='gray')

    ax2.set_title(f"P99 Latency - {pattern.capitalize()} Load")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_xlabel("Time Steps")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_latency.png", dpi=300)
    plt.close()


def plot_request_distribution(results, pattern, results_dir):
    """绘制请求分布图表"""
    strategies = list(results.keys())
    fig, axs = plt.subplots(len(strategies), 1, figsize=(10, 10))

    for i, strategy in enumerate(strategies):
        data = results[strategy]["request_distribution"]
        axs[i].bar(range(len(data)), data)
        axs[i].set_title(f"{strategy.upper()} - Request Distribution")
        axs[i].set_ylabel("Percentage (%)")
        axs[i].set_xticks(range(len(data)))
        axs[i].set_xticklabels([f"Replica {j}" for j in range(len(data))])

        if i == len(strategies) - 1:
            axs[i].set_xlabel("Replicas")

    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_request_distribution.png", dpi=300)
    plt.close()


def plot_rps_metrics(results, pattern, results_dir):
    """绘制以RPS为横轴的性能指标图表"""
    strategies = list(results.keys())
    metric_types = ["p95", "p99", "avg", "cpu"]
    titles = ["P95 Latency vs RPS", "P99 Latency vs RPS", "Average Latency vs RPS", "Total CPU Usage vs RPS"]
    ylabels = ["P95 Latency (ms)", "P99 Latency (ms)", "Avg Latency (ms)", "Total CPU Usage (%)"]

    # 为每种指标创建一个图表
    for idx, metric in enumerate(metric_types):
        plt.figure(figsize=(10, 6))

        for strategy in strategies:
            rps_metrics = results[strategy]["rps_metrics"]
            rps_values = sorted(rps_metrics.keys())
            metric_values = [rps_metrics[rps][metric] for rps in rps_values]

            plt.plot(rps_values, metric_values, 'o-', label=strategy.upper(), linewidth=2)

        plt.title(f"{titles[idx]} - {pattern.capitalize()} Load")
        plt.xlabel("Requests Per Second (RPS)")
        plt.ylabel(ylabels[idx])
        plt.grid(True, alpha=0.3)
        plt.legend()

        plt.tight_layout()
        plt.savefig(f"{results_dir}/{pattern}_{metric}_vs_rps.png", dpi=300)
        plt.close()


def plot_summary_metrics(all_results, results_dir):
    """绘制汇总指标对比图表"""
    patterns = list(all_results.keys())
    strategies = list(all_results[patterns[0]].keys())
    metrics = ["avg_active_replicas", "cpu_hours", "p95_latency", "p99_latency", "route_changes"]
    metric_names = ["Avg Active Replicas", "CPU Hours", "P95 Latency (ms)", "P99 Latency (ms)", "Route Changes"]

    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 15))

    bar_width = 0.25
    index = np.arange(len(patterns))

    for i, metric in enumerate(metrics):
        for j, strategy in enumerate(strategies):
            values = [all_results[pattern][strategy][metric] for pattern in patterns]
            axs[i].bar(index + j*bar_width, values, bar_width, label=strategy.upper())

        axs[i].set_title(metric_names[i])
        axs[i].set_xticks(index + bar_width)
        axs[i].set_xticklabels([p.capitalize() for p in patterns])
        axs[i].legend()

    plt.tight_layout()
    plt.savefig(f"{results_dir}/summary_metrics.png", dpi=300)
    plt.close()


def plot_improvement_comparison(all_results, results_dir):
    """绘制CILB相对于RR和LC的改进百分比"""
    patterns = list(all_results.keys())
    metrics = ["avg_active_replicas", "cpu_hours", "p95_latency", "p99_latency"]
    metric_names = ["Avg Active Replicas", "CPU Hours", "P95 Latency", "P99 Latency"]

    # 计算改进百分比
    improvements = {}
    for pattern in patterns:
        improvements[pattern] = {
            "vs_rr": [],
            "vs_lc": []
        }

        for metric in metrics:
            rr_val = all_results[pattern]["rr"][metric]
            lc_val = all_results[pattern]["lc"][metric]
            cilb_val = all_results[pattern]["cilb"][metric]

            # 对于延迟指标，较低值更好；对于其他指标，较高值更好
            if metric in ["p95_latency", "p99_latency", "avg_latency", "route_changes", "cpu_hours", "avg_active_replicas"]:
                vs_rr = ((rr_val - cilb_val) / rr_val) * 100 if rr_val != 0 else 0
                vs_lc = ((lc_val - cilb_val) / lc_val) * 100 if lc_val != 0 else 0
            else:
                vs_rr = ((cilb_val - rr_val) / rr_val) * 100 if rr_val != 0 else 0
                vs_lc = ((cilb_val - lc_val) / lc_val) * 100 if lc_val != 0 else 0

            improvements[pattern]["vs_rr"].append(vs_rr)
            improvements[pattern]["vs_lc"].append(vs_lc)

    # 绘制改进百分比图表
    fig, axs = plt.subplots(len(patterns), 1, figsize=(12, 15))

    bar_width = 0.35
    index = np.arange(len(metrics))

    for i, pattern in enumerate(patterns):
        axs[i].bar(index, improvements[pattern]["vs_rr"], bar_width, label="CILB vs RR")
        axs[i].bar(index + bar_width, improvements[pattern]["vs_lc"], bar_width, label="CILB vs LC")

        axs[i].set_title(f"Improvement % - {pattern.capitalize()} Load")
        axs[i].set_ylabel("Improvement (%)")
        axs[i].set_xticks(index + bar_width / 2)
        axs[i].set_xticklabels(metric_names)

        # 添加数值标签
        for j, v in enumerate(improvements[pattern]["vs_rr"]):
            axs[i].text(j - 0.1, v + (5 if v >= 0 else -5), f"{v:.1f}%", ha='center')

        for j, v in enumerate(improvements[pattern]["vs_lc"]):
            axs[i].text(j + bar_width + 0.1, v + (5 if v >= 0 else -5), f"{v:.1f}%", ha='center')

        axs[i].legend()
        axs[i].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{results_dir}/improvement_comparison.png", dpi=300)
    plt.close()


def plot_cumulative_metrics(results, pattern, results_dir):
    """绘制CPU使用率和延迟随累计请求总数增加的变化趋势"""
    strategies = list(results.keys())

    # 创建一个2x1的子图布局
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    for strategy in strategies:
        # 计算每个时间步的累计请求数
        requests_per_step = results[strategy]["requests_per_step"]
        cumulative_requests = np.cumsum(requests_per_step)

        # CPU使用率随累计请求数的变化
        total_cpu = results[strategy]["total_cpu_usage_history"]
        ax1.plot(cumulative_requests, total_cpu, label=f"{strategy.upper()}", linewidth=2)

    ax1.set_title(f"Total CPU Usage vs Cumulative Requests - {pattern.capitalize()} Load")
    ax1.set_ylabel("Total CPU Usage (%)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 延迟随累计请求数的变化
    for strategy in strategies:
        requests_per_step = results[strategy]["requests_per_step"]
        cumulative_requests = np.cumsum(requests_per_step)

        # P95延迟
        p95_latency = results[strategy]["p95_latency_history"]
        ax2.plot(cumulative_requests, p95_latency, label=f"{strategy.upper()}", linewidth=2)

    ax2.set_title(f"P95 Latency vs Cumulative Requests - {pattern.capitalize()} Load")
    ax2.set_ylabel("P95 Latency (ms)")
    ax2.set_xlabel("Cumulative Requests")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_cumulative_metrics.png", dpi=300)
    plt.close()

    # 另外创建一个更详细的图，包含P99延迟和平均延迟
    fig, axs = plt.subplots(3, 1, figsize=(12, 15))

    # 各种延迟指标
    latency_types = ["avg_latency_history", "p95_latency_history", "p99_latency_history"]
    titles = ["Average Latency", "P95 Latency", "P99 Latency"]

    for i, latency_type in enumerate(latency_types):
        for strategy in strategies:
            requests_per_step = results[strategy]["requests_per_step"]
            cumulative_requests = np.cumsum(requests_per_step)

            latency = results[strategy][latency_type]
            axs[i].plot(cumulative_requests, latency, label=f"{strategy.upper()}", linewidth=2)

        axs[i].set_title(f"{titles[i]} vs Cumulative Requests - {pattern.capitalize()} Load")
        axs[i].set_ylabel(f"{titles[i]} (ms)")
        axs[i].grid(True, alpha=0.3)
        axs[i].legend()

    axs[2].set_xlabel("Cumulative Requests")

    plt.tight_layout()
    plt.savefig(f"{results_dir}/{pattern}_detailed_latency_vs_requests.png", dpi=300)
    plt.close()


def create_summary_report(all_results, results_dir):
    """创建摘要报告，保存为文本文件"""
    with open(f"{results_dir}/summary_report.txt", "w") as f:
        f.write("=========== LOAD BALANCING SIMULATION RESULTS ===========\n\n")

        for pattern in all_results.keys():
            f.write(f"=== {pattern.upper()} LOAD PATTERN ===\n\n")

            for strategy in all_results[pattern].keys():
                data = all_results[pattern][strategy]
                f.write(f"--- {strategy.upper()} Strategy ---\n")
                f.write(f"Average Active Replicas: {data['avg_active_replicas']:.2f}\n")
                f.write(f"CPU Hours: {data['cpu_hours']:.2f}\n")
                f.write(f"Average Latency: {data['avg_latency']:.2f} ms\n")
                f.write(f"P95 Latency: {data['p95_latency']:.2f} ms\n")
                f.write(f"P99 Latency: {data['p99_latency']:.2f} ms\n")
                f.write(f"Route Changes: {data['route_changes']}\n")
                f.write(f"Request Distribution: {[f'{x:.1f}%' for x in data['request_distribution']]}\n\n")

            # 计算改进百分比
            rr_data = all_results[pattern]["rr"]
            lc_data = all_results[pattern]["lc"]
            cilb_data = all_results[pattern]["cilb"]

            f.write("--- Improvement Analysis ---\n")

            # CILB vs RR
            replica_reduction_rr = ((rr_data["avg_active_replicas"] - cilb_data["avg_active_replicas"]) /
                                 rr_data["avg_active_replicas"]) * 100
            cpu_reduction_rr = ((rr_data["cpu_hours"] - cilb_data["cpu_hours"]) /
                             rr_data["cpu_hours"]) * 100
            latency_reduction_rr = ((rr_data["p95_latency"] - cilb_data["p95_latency"]) /
                                 rr_data["p95_latency"]) * 100

            f.write(f"CILB vs RR:\n")
            f.write(f"  Active Replica Reduction: {replica_reduction_rr:.2f}%\n")
            f.write(f"  CPU Hours Reduction: {cpu_reduction_rr:.2f}%\n")
            f.write(f"  P95 Latency Reduction: {latency_reduction_rr:.2f}%\n\n")

            # CILB vs LC
            replica_reduction_lc = ((lc_data["avg_active_replicas"] - cilb_data["avg_active_replicas"]) /
                                 lc_data["avg_active_replicas"]) * 100
            cpu_reduction_lc = ((lc_data["cpu_hours"] - cilb_data["cpu_hours"]) /
                             lc_data["cpu_hours"]) * 100
            latency_reduction_lc = ((lc_data["p95_latency"] - cilb_data["p95_latency"]) /
                                 lc_data["p95_latency"]) * 100
            route_reduction_lc = ((lc_data["route_changes"] - cilb_data["route_changes"]) /
                               lc_data["route_changes"]) * 100

            f.write(f"CILB vs LC:\n")
            f.write(f"  Active Replica Reduction: {replica_reduction_lc:.2f}%\n")
            f.write(f"  CPU Hours Reduction: {cpu_reduction_lc:.2f}%\n")
            f.write(f"  P95 Latency Reduction: {latency_reduction_lc:.2f}%\n")
            f.write(f"  Route Changes Reduction: {route_reduction_lc:.2f}%\n\n")

            f.write("\n")

        f.write("================== END OF REPORT ==================\n")


def compare_strategies():
    time_steps = 100
    patterns = ["stable", "bursty", "ramp_up"]
    strategies = ["rr", "lc", "cilb"]

    # 设置全局随机种子以保证可重现性
    seed = 42

    # 存储所有结果
    all_results = {}

    # 运行所有模拟
    for pattern in patterns:
        pattern_results = {}
        print(f"\n--- Pattern: {pattern} ---")

        for strategy in strategies:
            print(f"Running {strategy}...")
            results = run_simulation(strategy, pattern, time_steps, seed=seed)
            pattern_results[strategy] = results

            # 打印主要统计数据
            print(f"  Avg Active Replicas: {results['avg_active_replicas']:.2f}")
            print(f"  CPU Hours: {results['cpu_hours']:.2f}")
            print(f"  P95 Latency: {results['p95_latency']:.2f} ms")
            print(f"  P99 Latency: {results['p99_latency']:.2f} ms")
            print(f"  Route Changes: {results['route_changes']}")

        all_results[pattern] = pattern_results

        # 保存该模式的结果
        save_simulation_data(pattern_results, pattern, results_dir)

        # 绘制各种图表
        plot_cpu_utilization(pattern_results, pattern, results_dir)
        plot_total_cpu_comparison(pattern_results, pattern, results_dir)
        plot_active_replicas(pattern_results, pattern, results_dir)
        plot_latency(pattern_results, pattern, results_dir)
        plot_request_distribution(pattern_results, pattern, results_dir)
        plot_cumulative_metrics(pattern_results, pattern, results_dir)

    # 绘制汇总图表
    plot_summary_metrics(all_results, results_dir)
    plot_improvement_comparison(all_results, results_dir)

    # 创建摘要报告
    create_summary_report(all_results, results_dir)

    print(f"\nAll results saved to: {results_dir}")


# 运行比较
compare_strategies()