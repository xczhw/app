import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
import os

# Simulation parameters
NUM_REPLICAS = 10
SIMULATION_DURATION = 30  # minutes
SAMPLING_INTERVAL = 0.25  # minute
CPU_THRESHOLD = 5  # % threshold for active replica counting

# Traffic patterns - requests per second
def generate_traffic(pattern="ramp-up", duration=SIMULATION_DURATION):
    time_points = np.arange(0, duration, SAMPLING_INTERVAL)

    # Only keep ramp-up pattern
    base_traffic = 10
    return [base_traffic + int(t * 5) + random.randint(-10, 10) for t in time_points]

# Load balancing strategies
class LoadBalancer:
    def __init__(self, num_replicas):
        self.num_replicas = num_replicas
        self.cpu_usage = [0] * num_replicas
        self.name = "Base"

    def route_traffic(self, requests_per_second):
        # Base implementation
        pass

    def update_metrics(self, requests_distribution):
        # Update CPU usage based on traffic distribution
        # Simple model: 1 rps = 0.2% CPU on average with some randomness
        for i in range(self.num_replicas):
            # CPU usage decays by 30% each interval to simulate cooldown

            # Add new load
            if requests_distribution[i] > 0:
                cpu_per_request = 0.2 * (1 + random.uniform(-0.1, 0.1))
                self.cpu_usage[i] += requests_distribution[i] * cpu_per_request

    def get_active_replicas(self):
        return sum(1 for cpu in self.cpu_usage if cpu > CPU_THRESHOLD)

    def get_latency(self, requests_distribution):
        # Model latency based on CPU usage
        # Higher CPU usage = higher latency, with exponential increase above 80%
        latencies = []
        for i, rps in enumerate(requests_distribution):
            if rps == 0:
                continue

            base_latency = 20  # ms
            cpu = self.cpu_usage[i]

            # CPU impact on latency
            if cpu < 70:
                latency = base_latency
            elif cpu < 80:
                latency = base_latency * (1.5 + (cpu-50)/60)
            else:
                latency = base_latency * (2 + 3 * ((cpu-80)/20)**2)

            # Add some randomness
            latency *= random.uniform(0.9, 1.1)

            # Add latency entries for each request
            latencies.extend([latency] * int(rps))

        if not latencies:
            return 0, 0  # No requests

        return np.percentile(latencies, 95), np.percentile(latencies, 99)

class RoundRobinLB(LoadBalancer):
    def __init__(self, num_replicas):
        super().__init__(num_replicas)
        self.name = "Round-Robin"
        self.current_index = 0

    def route_traffic(self, requests_per_second):
        requests_per_replica = requests_per_second / self.num_replicas
        distribution = [requests_per_replica] * self.num_replicas
        self.update_metrics(distribution)
        return distribution

class LeastCpuLB(LoadBalancer):
    def __init__(self, num_replicas):
        super().__init__(num_replicas)
        self.name = "Least-CPU"

    def route_traffic(self, requests_per_second):
        # Direct all traffic to replicas with lowest CPU
        distribution = [0] * self.num_replicas
        cpu_with_index = [(cpu, i) for i, cpu in enumerate(self.cpu_usage)]
        cpu_with_index.sort()  # Sort by CPU usage

        # Distribute load proportionally to available capacity (100-cpu)
        total_available = sum(100 - cpu for cpu, _ in cpu_with_index)
        remaining_requests = requests_per_second

        if total_available <= 0:
            # Fallback to even distribution if all replicas are at capacity
            for i in range(self.num_replicas):
                distribution[i] = requests_per_second / self.num_replicas
        else:
            for cpu, idx in cpu_with_index:
                # Proportion of requests = proportion of available capacity
                allocation = remaining_requests * (100 - cpu) / total_available
                distribution[idx] = allocation
                remaining_requests -= allocation

        self.update_metrics(distribution)
        return distribution

class CILBLB(LoadBalancer):
    def __init__(self, num_replicas, cpu_threshold=85):
        super().__init__(num_replicas)
        self.name = "CILB"
        self.cpu_threshold = cpu_threshold  # CPU使用率阈值，超过此值不再分配流量
        self.active_replicas = []  # 跟踪活跃的副本

    def route_traffic(self, requests_per_second):
        distribution = [0] * self.num_replicas

        # 按CPU使用率从高到低排序所有副本
        cpu_with_index = [(self.cpu_usage[i], i) for i in range(self.num_replicas)]
        cpu_with_index.sort(reverse=True)  # 降序排序

        # 将每个请求分配给第一个未超过阈值的副本
        remaining_traffic = requests_per_second

        # 分配流量
        while remaining_traffic > 0:
            found_available_replica = False

            for cpu, idx in cpu_with_index:
                # 如果CPU使用率低于阈值，将一个请求分配给它
                if cpu < self.cpu_threshold:
                    # 假设每个请求增加0.2%的CPU
                    distribution[idx] += 1
                    self.cpu_usage[idx] += 0.2
                    remaining_traffic -= 1
                    found_available_replica = True
                    break

            # 如果没有找到可用副本或已分配所有流量，结束循环
            if not found_available_replica or remaining_traffic <= 0:
                break

        # 更新活跃副本列表（CPU使用率大于5%的副本）
        self.active_replicas = [i for i in range(self.num_replicas) if self.cpu_usage[i] > CPU_THRESHOLD]

        # 如果还有剩余流量但所有副本都超过阈值，按比例分配给所有副本
        if remaining_traffic > 0:
            for i in range(self.num_replicas):
                distribution[i] += remaining_traffic / self.num_replicas

        self.update_metrics(distribution)
        return distribution

def run_simulation():
    # Initialize load balancers
    rr_lb = RoundRobinLB(NUM_REPLICAS)
    lc_lb = LeastCpuLB(NUM_REPLICAS)
    cilb_lb = CILBLB(NUM_REPLICAS)

    # Only use ramp-up traffic pattern
    pattern = "ramp-up"
    traffic = generate_traffic(pattern)

    all_results = []

    # Run each load balancer with this traffic pattern
    for lb in [rr_lb, lc_lb, cilb_lb]:
        # Reset the load balancer
        lb.cpu_usage = [0] * NUM_REPLICAS
        if isinstance(lb, CILBLB):
            lb.active_replicas = [0]  # Start with one active replica
            lb.hysteresis_counter = 0

        results = []
        for t, rps in enumerate(traffic):
            # Route traffic according to strategy
            distribution = lb.route_traffic(rps)

            # Measure metrics
            active_replicas = lb.get_active_replicas()
            p95, p99 = lb.get_latency(distribution)

            results.append({
                'time': t,
                'pattern': pattern,
                'strategy': lb.name,
                'traffic': rps,
                'active_replicas': active_replicas,
                'p95_latency': p95,
                'p99_latency': p99,
                'cpu_usage': lb.cpu_usage.copy()
            })

        all_results.extend(results)

    return pd.DataFrame(all_results)

# Run simulation and save results
results_df = run_simulation()

# Create output directory if it doesn't exist
if not os.path.exists('results'):
    os.makedirs('results')

# Save to CSV
results_df.to_csv('results/load_balancing_simulation_results.csv', index=False)

# Generate summary statistics
summary = results_df.groupby(['strategy'])[['active_replicas', 'p95_latency', 'p99_latency']].mean()
summary.to_csv('results/summary_stats.csv')

# Calculate improvements
improvements = pd.DataFrame()
pattern = "ramp-up"  # Only for ramp-up pattern

# Calculate average metrics by strategy
avg_metrics = results_df.groupby('strategy')[['active_replicas', 'p95_latency', 'p99_latency']].mean()

# Calculate improvement percentages
cilb_metrics = avg_metrics.loc['CILB']
rr_metrics = avg_metrics.loc['Round-Robin']
lc_metrics = avg_metrics.loc['Least-CPU']

# Improvement over Round-Robin
rr_improvement = {
    'comparison': 'CILB vs RR',
    'active_replicas_reduction': (rr_metrics['active_replicas'] - cilb_metrics['active_replicas']) / rr_metrics['active_replicas'] * 100,
    'p95_latency_change': (cilb_metrics['p95_latency'] - rr_metrics['p95_latency']) / rr_metrics['p95_latency'] * 100,
    'p99_latency_change': (cilb_metrics['p99_latency'] - rr_metrics['p99_latency']) / rr_metrics['p99_latency'] * 100
}

# Improvement over Least-CPU
lc_improvement = {
    'comparison': 'CILB vs LC',
    'active_replicas_reduction': (lc_metrics['active_replicas'] - cilb_metrics['active_replicas']) / lc_metrics['active_replicas'] * 100,
    'p95_latency_change': (cilb_metrics['p95_latency'] - lc_metrics['p95_latency']) / lc_metrics['p95_latency'] * 100,
    'p99_latency_change': (cilb_metrics['p99_latency'] - lc_metrics['p99_latency']) / lc_metrics['p99_latency'] * 100
}

improvements = pd.concat([improvements, pd.DataFrame([rr_improvement, lc_improvement])])
improvements.to_csv('results/improvement_percentages.csv', index=False)

# Create visualizations
plt.figure(figsize=(10, 6))

# Plot active replicas over time
plt.subplot(2, 1, 1)
for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
    strategy_data = results_df[results_df['strategy'] == strategy]
    plt.plot(strategy_data['time'], strategy_data['active_replicas'], label=strategy)


plt.xlabel('Time (minutes)')
plt.ylabel('Active Replicas')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

# Plot latency over time
plt.subplot(2, 1, 2)
for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
    strategy_data = results_df[results_df['strategy'] == strategy]
    plt.plot(strategy_data['time'], strategy_data['p95_latency'], label=f'{strategy} P95')


plt.xlabel('Time (minutes)')
plt.ylabel('Latency (ms)')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('results/rampup_performance.png')

# Add a plot for traffic vs active replicas
plt.figure(figsize=(12, 5))
traffic_data = results_df[results_df['strategy'] == 'Round-Robin']['traffic'].values  # Traffic is same for all strategies

# Plot traffic
plt.subplot(1, 2, 1)
plt.plot(traffic_data, color='black', linestyle='--', label='Traffic (RPS)')

plt.xlabel('Time (minutes)')
plt.ylabel('Requests per Second')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)

# Bar chart comparing average active replicas
plt.subplot(1, 2, 2)
avg_active = summary['active_replicas']
plt.bar(avg_active.index, avg_active.values)

plt.ylabel('Number of Replicas')
plt.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('results/traffic_and_replicas.png')

# Resource efficiency visualization
plt.figure(figsize=(10, 6))

# Create scatter plot of latency vs active replicas
for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
    strategy_data = results_df[results_df['strategy'] == strategy]
    avg_latency = strategy_data['p95_latency'].mean()
    avg_replicas = strategy_data['active_replicas'].mean()
    plt.scatter(avg_replicas, avg_latency, s=100, label=strategy)


plt.xlabel('Average Active Replicas (Resource Usage)')
plt.ylabel('Average P95 Latency (ms)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

# Add annotation showing percentage improvements
x_min, x_max = plt.xlim()
y_min, y_max = plt.ylim()
plt.text(x_min + (x_max-x_min)*0.05, y_max - (y_max-y_min)*0.1,
         f"CILB reduces active replicas by:\n{rr_improvement['active_replicas_reduction']:.1f}% vs RR\n{lc_improvement['active_replicas_reduction']:.1f}% vs LC",
         bbox=dict(facecolor='white', alpha=0.7))

plt.savefig('results/efficiency_vs_performance.png')

print("Simulation completed. Results saved to 'results' directory.")
print(f"Active replicas reduction: CILB vs RR: {rr_improvement['active_replicas_reduction']:.2f}%")
print(f"Active replicas reduction: CILB vs LC: {lc_improvement['active_replicas_reduction']:.2f}%")
print(f"P95 latency change: CILB vs RR: {rr_improvement['p95_latency_change']:.2f}%")
print(f"P95 latency change: CILB vs LC: {lc_improvement['p95_latency_change']:.2f}%")