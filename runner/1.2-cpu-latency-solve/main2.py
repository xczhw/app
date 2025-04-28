import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import random
import os

# Simulation parameters
NUM_REPLICAS = 10
SIMULATION_DURATION = 60  # minutes
SAMPLING_INTERVAL = 1  # minute
CPU_THRESHOLD = 5  # % threshold for active replica counting

# Traffic patterns - requests per second
def generate_traffic(pattern="stable", duration=SIMULATION_DURATION):
    time_points = np.arange(0, duration, SAMPLING_INTERVAL)

    if pattern == "stable":
        base_traffic = 500
        return [base_traffic + random.randint(-50, 50) for _ in time_points]
    elif pattern == "bursty":
        base_traffic = 300
        traffic = []
        for t in time_points:
            if t % 10 < 2:  # Create bursts every 10 minutes
                traffic.append(base_traffic * 3 + random.randint(-100, 100))
            else:
                traffic.append(base_traffic + random.randint(-50, 50))
        return traffic
    elif pattern == "ramp-up":
        base_traffic = 100
        return [base_traffic + int(t * 15) + random.randint(-30, 30) for t in time_points]

    return [500 for _ in time_points]  # Default

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
            self.cpu_usage[i] = max(0, self.cpu_usage[i] * 0.7)

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
            if cpu < 50:
                latency = base_latency * (1 + cpu/100)
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
    def __init__(self, num_replicas, low_threshold=30, high_threshold=75, safe_cpu=85):
        super().__init__(num_replicas)
        self.name = "CILB"
        self.low_threshold = low_threshold    # Threshold to consider removing replicas
        self.high_threshold = high_threshold  # Threshold to consider adding replicas
        self.safe_cpu = safe_cpu              # Max safe CPU threshold for any replica
        self.active_replicas = [0]            # Start with 1 active replica
        self.hysteresis_counter = 0           # Prevents rapid oscillations

    def route_traffic(self, requests_per_second):
        distribution = [0] * self.num_replicas

        # Key CILB principle: Prefer loading existing replicas rather than spreading thinly
        # Sort active replicas by CPU (ascending)
        active_sorted = sorted(self.active_replicas, key=lambda i: self.cpu_usage[i])

        # Estimate how much traffic we can send to each replica
        # based on its current CPU and our safe threshold
        remaining_traffic = requests_per_second

        # First pass: estimate how much each replica can handle
        for i in active_sorted:
            current_cpu = self.cpu_usage[i]
            available_cpu = self.safe_cpu - current_cpu

            # Each unit of traffic adds approximately 0.2% CPU
            cpu_per_request = 0.2
            can_handle = available_cpu / cpu_per_request

            # Assign traffic to this replica
            traffic_to_assign = min(remaining_traffic, can_handle)
            distribution[i] = traffic_to_assign
            remaining_traffic -= traffic_to_assign

            # If we've assigned all traffic, we're done
            if remaining_traffic <= 0:
                break

        # If we still have traffic to assign, we need more replicas
        if remaining_traffic > 0:
            # Find inactive replicas to activate
            inactive = [i for i in range(self.num_replicas) if i not in self.active_replicas]

            # Activate another replica if available
            if inactive and self.hysteresis_counter >= 0:
                new_replica = inactive[0]
                self.active_replicas.append(new_replica)

                # Assign remaining traffic to the new replica
                distribution[new_replica] = remaining_traffic
                remaining_traffic = 0

                # Reset hysteresis counter
                self.hysteresis_counter = -2  # Wait 2 cycles before next scale event

        # Check if we can deactivate a replica (only if no scale-up just happened)
        elif len(self.active_replicas) > 1 and self.hysteresis_counter >= 0:
            # Calculate average CPU across active replicas
            avg_cpu = sum(self.cpu_usage[i] for i in self.active_replicas) / len(self.active_replicas)

            # If average CPU is below threshold, consider removing least used replica
            if avg_cpu < self.low_threshold:
                # Find least utilized replica
                least_used = min(self.active_replicas, key=lambda i: self.cpu_usage[i])

                # Check if removing it would keep average CPU below high threshold
                remaining_load = sum(distribution[i] for i in self.active_replicas)
                remaining_load -= distribution[least_used]
                remaining_replicas = len(self.active_replicas) - 1

                # Would removing this replica push others too high?
                if remaining_load / remaining_replicas * 0.2 < self.high_threshold:
                    # Safe to remove
                    redistribution = distribution[least_used] / remaining_replicas
                    distribution[least_used] = 0

                    # Redistribute its load
                    for i in self.active_replicas:
                        if i != least_used:
                            distribution[i] += redistribution

                    # Remove from active list
                    self.active_replicas.remove(least_used)

                    # Reset hysteresis counter
                    self.hysteresis_counter = -2  # Wait 2 cycles before next scale event

        # Update hysteresis counter
        self.hysteresis_counter += 1

        self.update_metrics(distribution)
        return distribution

def run_simulation():
    # Initialize load balancers
    rr_lb = RoundRobinLB(NUM_REPLICAS)
    lc_lb = LeastCpuLB(NUM_REPLICAS)
    cilb_lb = CILBLB(NUM_REPLICAS)

    # Traffic patterns to simulate
    patterns = ["stable", "bursty", "ramp-up"]

    all_results = []

    for pattern in patterns:
        traffic = generate_traffic(pattern)

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

# Generate summary statistics for the paper
summary = results_df.groupby(['pattern', 'strategy'])[['active_replicas', 'p95_latency', 'p99_latency']].mean()
summary.to_csv('results/summary_stats.csv')

# Calculate improvements
improvements = pd.DataFrame()
for pattern in results_df['pattern'].unique():
    pattern_data = results_df[results_df['pattern'] == pattern]

    # Calculate average metrics by strategy
    avg_metrics = pattern_data.groupby('strategy')[['active_replicas', 'p95_latency', 'p99_latency']].mean()

    # Calculate improvement percentages
    cilb_metrics = avg_metrics.loc['CILB']
    rr_metrics = avg_metrics.loc['Round-Robin']
    lc_metrics = avg_metrics.loc['Least-CPU']

    # Improvement over Round-Robin
    rr_improvement = {
        'pattern': pattern,
        'comparison': 'CILB vs RR',
        'active_replicas_reduction': (rr_metrics['active_replicas'] - cilb_metrics['active_replicas']) / rr_metrics['active_replicas'] * 100,
        'p95_latency_change': (cilb_metrics['p95_latency'] - rr_metrics['p95_latency']) / rr_metrics['p95_latency'] * 100,
        'p99_latency_change': (cilb_metrics['p99_latency'] - rr_metrics['p99_latency']) / rr_metrics['p99_latency'] * 100
    }

    # Improvement over Least-CPU
    lc_improvement = {
        'pattern': pattern,
        'comparison': 'CILB vs LC',
        'active_replicas_reduction': (lc_metrics['active_replicas'] - cilb_metrics['active_replicas']) / lc_metrics['active_replicas'] * 100,
        'p95_latency_change': (cilb_metrics['p95_latency'] - lc_metrics['p95_latency']) / lc_metrics['p95_latency'] * 100,
        'p99_latency_change': (cilb_metrics['p99_latency'] - lc_metrics['p99_latency']) / lc_metrics['p99_latency'] * 100
    }

    improvements = pd.concat([improvements, pd.DataFrame([rr_improvement, lc_improvement])])

improvements.to_csv('results/improvement_percentages.csv', index=False)

# Create visualizations
plt.figure(figsize=(12, 8))

# Plot active replicas over time for each pattern and strategy
for idx, pattern in enumerate(['stable', 'bursty', 'ramp-up']):
    plt.subplot(3, 1, idx+1)
    pattern_data = results_df[results_df['pattern'] == pattern]

    for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
        strategy_data = pattern_data[pattern_data['strategy'] == strategy]
        plt.plot(strategy_data['time'], strategy_data['active_replicas'], label=strategy)

    plt.title(f'Active Replicas - {pattern.title()} Traffic')
    plt.xlabel('Time (minutes)')
    plt.ylabel('Active Replicas')
    plt.legend()

plt.tight_layout()
plt.savefig('results/active_replicas_comparison.png')

# Plot latency over time
plt.figure(figsize=(12, 8))
for idx, pattern in enumerate(['stable', 'bursty', 'ramp-up']):
    plt.subplot(3, 1, idx+1)
    pattern_data = results_df[results_df['pattern'] == pattern]

    for strategy in ['Round-Robin', 'Least-CPU', 'CILB']:
        strategy_data = pattern_data[pattern_data['strategy'] == strategy]
        plt.plot(strategy_data['time'], strategy_data['p95_latency'], label=f'{strategy} P95')

    plt.title(f'P95 Latency - {pattern.title()} Traffic')
    plt.xlabel('Time (minutes)')
    plt.ylabel('Latency (ms)')
    plt.legend()

plt.tight_layout()
plt.savefig('results/latency_comparison.png')

print("Simulation completed. Results saved to 'results' directory.")
print(f"Overall improvement in active replicas: CILB vs RR: {improvements[improvements['comparison'] == 'CILB vs RR']['active_replicas_reduction'].mean():.2f}%")
print(f"Overall improvement in active replicas: CILB vs LC: {improvements[improvements['comparison'] == 'CILB vs LC']['active_replicas_reduction'].mean():.2f}%")
print(f"Overall P95 latency change: CILB vs RR: {improvements[improvements['comparison'] == 'CILB vs RR']['p95_latency_change'].mean():.2f}%")
print(f"Overall P95 latency change: CILB vs LC: {improvements[improvements['comparison'] == 'CILB vs LC']['p95_latency_change'].mean():.2f}%")