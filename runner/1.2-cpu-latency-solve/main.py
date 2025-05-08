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
LATENCY_TIMEOUT = 2000  # ms - timeout threshold for latency

# set random seed for reproducibility
random.seed(42)

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

            base_latency = 250  # ms
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
        for i in range(requests_per_second % self.num_replicas):
            distribution[(self.current_index + i) % self.num_replicas] += 1
        self.current_index = (self.current_index + requests_per_second) % self.num_replicas
        self.update_metrics(distribution)
        return distribution

class LeastCpuLB(LoadBalancer):
    def __init__(self, num_replicas):
        super().__init__(num_replicas)
        self.name = "Least-CPU"

    def route_traffic(self, requests_per_second):
        # Initialize distribution with all zeros
        distribution = [0] * self.num_replicas
        remaining_requests = int(requests_per_second)

        # Distribute traffic one request at a time to the replica with the lowest CPU
        for _ in range(remaining_requests):
            # Find replica with lowest CPU usage
            min_cpu_idx = self.cpu_usage.index(min(self.cpu_usage))

            # Assign one request to it
            distribution[min_cpu_idx] += 1

        # Actual CPU update based on final distribution
        self.update_metrics(distribution)
        return distribution

class CILBLB(LoadBalancer):
    def __init__(self, num_replicas, cpu_threshold=50):
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
    for lb in [cilb_lb, rr_lb, lc_lb]:
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
            p90, p99 = lb.get_latency(distribution)

            results.append({
                'time': t * SAMPLING_INTERVAL,
                'pattern': pattern,
                'strategy': lb.name,
                'traffic': rps,
                'active_replicas': active_replicas,
                'p90_latency': p90,
                'p99_latency': p99,
                'cpu_usage': lb.cpu_usage.copy(),
                'cpu_usage_sum': sum(lb.cpu_usage)
            })

        all_results.extend(results)

    return pd.DataFrame(all_results)

# Run simulation and save results
results_df = run_simulation()

# Create output directory if it doesn't exist
if not os.path.exists('results'):
    os.makedirs('results')

# Save to CSV
results_df.to_csv('data/load_balancing_simulation_results.csv', index=False)

# Generate summary statistics
summary = results_df.groupby(['strategy'])[['active_replicas', 'p90_latency', 'p99_latency']].mean()
summary.to_csv('data/summary_stats.csv')

# Calculate improvements
improvements = pd.DataFrame()
pattern = "ramp-up"  # Only for ramp-up pattern

# Calculate average metrics by strategy
avg_metrics = results_df.groupby('strategy')[['active_replicas', 'p90_latency', 'p99_latency']].mean()

# Calculate improvement percentages
cilb_metrics = avg_metrics.loc['CILB']
rr_metrics = avg_metrics.loc['Round-Robin']
lc_metrics = avg_metrics.loc['Least-CPU']

# Improvement over Round-Robin
rr_improvement = {
    'comparison': 'CILB vs RR',
    'active_replicas_reduction': (rr_metrics['active_replicas'] - cilb_metrics['active_replicas']) / rr_metrics['active_replicas'] * 100,
    'p90_latency_change': (cilb_metrics['p90_latency'] - rr_metrics['p90_latency']) / rr_metrics['p90_latency'] * 100,
    'p99_latency_change': (cilb_metrics['p99_latency'] - rr_metrics['p99_latency']) / rr_metrics['p99_latency'] * 100
}

# Improvement over Least-CPU
lc_improvement = {
    'comparison': 'CILB vs LC',
    'active_replicas_reduction': (lc_metrics['active_replicas'] - cilb_metrics['active_replicas']) / lc_metrics['active_replicas'] * 100,
    'p90_latency_change': (cilb_metrics['p90_latency'] - lc_metrics['p90_latency']) / lc_metrics['p90_latency'] * 100,
    'p99_latency_change': (cilb_metrics['p99_latency'] - lc_metrics['p99_latency']) / lc_metrics['p99_latency'] * 100
}

improvements = pd.concat([improvements, pd.DataFrame([rr_improvement, lc_improvement])])
improvements.to_csv('data/improvement_percentages.csv', index=False)

# Create separate visualizations

# 1. Plot active replicas over time
plt.figure(figsize=(10, 6))
for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
    strategy_data = results_df[results_df['strategy'] == strategy]
    plt.plot(strategy_data['time'], strategy_data['active_replicas'], label=strategy)

plt.xlabel('Time (minutes)')
plt.ylabel('Active Replicas')

plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('results/active_replicas_over_time.pdf')
plt.close()

# 2. Plot latency over time with timeout threshold
plt.figure(figsize=(10, 6))
for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
    strategy_data = results_df[results_df['strategy'] == strategy]
    time_data = strategy_data['time'].values
    original_latency_data = strategy_data['p90_latency'].values

    # Cap latency values at the timeout threshold
    capped_latency_data = np.minimum(original_latency_data, LATENCY_TIMEOUT)

    # Plot the line with capped values
    line, = plt.plot(time_data, capped_latency_data, label=f'{strategy} p90')
    line_color = line.get_color()

    # Mark points that exceed the threshold with 'x'
    timeout_indices = original_latency_data > LATENCY_TIMEOUT
    if any(timeout_indices):
        plt.plot(time_data[timeout_indices],
                 [LATENCY_TIMEOUT] * sum(timeout_indices),
                 'x', color=line_color, markersize=8, markeredgewidth=2)

plt.xlabel('Time (minutes)')
plt.ylabel('Latency (ms)')

plt.axhline(y=LATENCY_TIMEOUT, color='r', linestyle='--', label=f'Timeout ({LATENCY_TIMEOUT} ms)')
plt.ylim(0, LATENCY_TIMEOUT * 1.1)  # Limit height with some padding
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('results/latency_over_time.pdf')
plt.close()

# 3. Plot traffic over time (separate)
plt.figure(figsize=(10, 6))
traffic_time = results_df[results_df['strategy'] == 'Round-Robin']['time'].values
traffic_data = results_df[results_df['strategy'] == 'Round-Robin']['traffic'].values  # Traffic is same for all strategies
plt.plot(traffic_time, traffic_data, color='black', linestyle='-', label='Traffic (RPS)')
plt.xlabel('Time (minutes)')
plt.ylabel('Requests per Second')

plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('results/traffic_over_time.pdf')
plt.close()

# 4. Bar chart comparing average active replicas
plt.figure(figsize=(10, 6))
avg_active = summary['active_replicas']
plt.bar(avg_active.index, avg_active.values)
plt.ylabel('Number of Replicas')

plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('results/avg_active_replicas.pdf')
plt.close()

# # 5. Resource efficiency visualization (latency vs replicas)
# plt.figure(figsize=(10, 6))
# for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
#     strategy_data = results_df[results_df['strategy'] == strategy]
#     original_avg_latency = strategy_data['p90_latency'].mean()
#     # Cap at timeout threshold
#     capped_avg_latency = min(original_avg_latency, LATENCY_TIMEOUT)
#     avg_replicas = strategy_data['active_replicas'].mean()

#     # Plot point
#     marker = 'o'
#     if original_avg_latency > LATENCY_TIMEOUT:
#         # Use regular marker but add an annotation
#         plt.scatter(avg_replicas, capped_avg_latency, s=100, marker=marker, label=f"{strategy} (capped)")
#         # Add small 'x' marker to indicate capping
#         plt.plot(avg_replicas, capped_avg_latency, 'x', color='black', markersize=6)
#     else:
#         plt.scatter(avg_replicas, capped_avg_latency, s=100, marker=marker, label=strategy)

# plt.xlabel('Average Active Replicas (Resource Usage)')
# plt.ylabel('Average p90 Latency (ms)')

# plt.ylim(0, LATENCY_TIMEOUT * 1.1)  # Limit height
# plt.axhline(y=LATENCY_TIMEOUT, color='r', linestyle='--', label=f'Timeout ({LATENCY_TIMEOUT} ms)')
# plt.grid(True, linestyle='--', alpha=0.7)
# plt.legend()

# # Add annotation showing percentage improvements
# x_min, x_max = plt.xlim()
# y_min, y_max = plt.ylim()
# plt.text(x_min + (x_max-x_min)*0.05, y_max - (y_max-y_min)*0.2,
#          f"CILB reduces active replicas by:\n{rr_improvement['active_replicas_reduction']:.1f}% vs RR\n{lc_improvement['active_replicas_reduction']:.1f}% vs LC",
#          bbox=dict(facecolor='white', alpha=0.7))

# plt.savefig('results/efficiency_vs_performance.pdf')
# plt.close()

print("Simulation completed. Results saved to 'results' directory.")
print(f"Active replicas reduction: CILB vs RR: {rr_improvement['active_replicas_reduction']:.2f}%")
print(f"Active replicas reduction: CILB vs LC: {lc_improvement['active_replicas_reduction']:.2f}%")
print(f"p90 latency change: CILB vs RR: {rr_improvement['p90_latency_change']:.2f}%")
print(f"p90 latency change: CILB vs LC: {lc_improvement['p90_latency_change']:.2f}%")