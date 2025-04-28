import numpy as np
import pandas as pd
import os

def generate_autoscaling_data():
    # Create fig directory if it doesn't exist
    if not os.path.exists('fig'):
        os.makedirs('fig')

    # Generate simulation data with fixed seed for reproducibility
    np.random.seed(42)
    time_points = np.arange(0, 100, 5)  # 0 to 95 minutes, every 5 minutes
    traffic = np.minimum(100, 20 + time_points * 1.5 + np.random.rand(len(time_points)) * 5)

    # Round-robin routing: instances and CPU utilization
    rr_replicas = [3]
    for i in range(1, len(time_points)):
        prev_replicas = rr_replicas[-1]
        # Scale out if average CPU usage exceeds 50%
        if traffic[i] / prev_replicas > 50:
            new_replicas = int(np.ceil(traffic[i] / 45))  # target 45% utilization
            rr_replicas.append(new_replicas)
        else:
            rr_replicas.append(prev_replicas)

    rr_replicas = np.array(rr_replicas)

    # Controlled imbalance routing: instances
    ci_replicas = [3]
    for i in range(1, len(time_points)):
        prev_replicas = ci_replicas[-1]
        # Scale out if highest loaded instance exceeds 70%
        if traffic[i] / prev_replicas > 70:
            new_replicas = int(np.ceil(traffic[i] / 65))  # target 65% utilization
            ci_replicas.append(new_replicas)
        else:
            ci_replicas.append(prev_replicas)

    ci_replicas = np.array(ci_replicas)

    # Calculate average CPU utilization for each strategy
    rr_avg_cpu = traffic / rr_replicas
    ci_avg_cpu = traffic / ci_replicas

    # Generate per-instance CPU data for both strategies
    rr_instance_data = []
    ci_instance_data = []

    # Function to generate detailed CPU distribution
    def generate_cpu_distribution(time_idx, strategy):
        """Generate CPU distribution for instances at a specific time point"""
        if strategy == 'rr':
            n_replicas = rr_replicas[time_idx]
            avg_cpu = traffic[time_idx] / n_replicas
            # Round-robin: load relatively evenly distributed
            distribution = np.random.normal(avg_cpu, avg_cpu * 0.1, n_replicas)
        else:  # controlled imbalance
            n_replicas = ci_replicas[time_idx]
            avg_cpu = traffic[time_idx] / n_replicas
            # Controlled imbalance: some instances high load, some low load
            high_load_count = int(np.ceil(n_replicas * 0.7))
            low_load_count = n_replicas - high_load_count

            # Ensure the average is maintained
            if low_load_count > 0:
                low_load_avg = max(10, avg_cpu * 0.5)  # at least 10% CPU
                high_load_avg = (avg_cpu * n_replicas - low_load_avg * low_load_count) / high_load_count
                high_load_avg = min(85, high_load_avg)  # cap at 85% for safety

                high_load = np.random.normal(high_load_avg, high_load_avg * 0.1, high_load_count)
                low_load = np.random.normal(low_load_avg, low_load_avg * 0.1, low_load_count)
                distribution = np.concatenate([high_load, low_load])
            else:
                distribution = np.random.normal(avg_cpu, avg_cpu * 0.1, n_replicas)

        # Ensure values are within reasonable range
        distribution = np.clip(distribution, 10, 95)
        return distribution

    # Generate detailed CPU data for each time point
    for i in range(len(time_points)):
        rr_cpu_dist = generate_cpu_distribution(i, 'rr')
        ci_cpu_dist = generate_cpu_distribution(i, 'ci')

        # Add to instance data lists
        rr_instance_data.append(rr_cpu_dist)
        ci_instance_data.append(ci_cpu_dist)

    # Find scaling points (Don't add to data_dict directly since they're different lengths)
    rr_scaling_points = [i for i in range(1, len(rr_replicas)) if rr_replicas[i] > rr_replicas[i-1]]
    ci_scaling_points = [i for i in range(1, len(ci_replicas)) if ci_replicas[i] > ci_replicas[i-1]]

    # Save scaling points to separate files
    pd.DataFrame({'index': rr_scaling_points}).to_csv('rr_scaling_points.csv', index=False)
    pd.DataFrame({'index': ci_scaling_points}).to_csv('ci_scaling_points.csv', index=False)

    # Calculate min, max, and mean CPU for each strategy at each time point
    rr_min_cpu = [np.min(rr_instance_data[i]) for i in range(len(time_points))]
    rr_max_cpu = [np.max(rr_instance_data[i]) for i in range(len(time_points))]
    rr_mean_cpu = [np.mean(rr_instance_data[i]) for i in range(len(time_points))]

    ci_min_cpu = [np.min(ci_instance_data[i]) for i in range(len(time_points))]
    ci_max_cpu = [np.max(ci_instance_data[i]) for i in range(len(time_points))]
    ci_mean_cpu = [np.mean(ci_instance_data[i]) for i in range(len(time_points))]

    # Create the main dataframe (without scaling points)
    data_dict = {
        'time': time_points,
        'traffic': traffic,
        'rr_replicas': rr_replicas,
        'ci_replicas': ci_replicas,
        'rr_avg_cpu': rr_avg_cpu,
        'ci_avg_cpu': ci_avg_cpu,
        'rr_min_cpu': rr_min_cpu,
        'rr_max_cpu': rr_max_cpu,
        'rr_mean_cpu': rr_mean_cpu,
        'ci_min_cpu': ci_min_cpu,
        'ci_max_cpu': ci_max_cpu,
        'ci_mean_cpu': ci_mean_cpu
    }

    df = pd.DataFrame(data_dict)

    # Save the main dataframe
    df.to_csv('autoscaling_data.csv', index=False)

    # Save instance-level CPU data
    with open('rr_instance_cpu_data.csv', 'w') as f:
        f.write('time,instance,cpu\n')
        for t_idx, time in enumerate(time_points):
            for i_idx, cpu in enumerate(rr_instance_data[t_idx]):
                f.write(f'{time},{i_idx+1},{cpu:.2f}\n')

    with open('ci_instance_cpu_data.csv', 'w') as f:
        f.write('time,instance,cpu\n')
        for t_idx, time in enumerate(time_points):
            for i_idx, cpu in enumerate(ci_instance_data[t_idx]):
                f.write(f'{time},{i_idx+1},{cpu:.2f}\n')

    # Save instance distribution data for selected points
    selected_points = [3, 8, 13, 18]  # 15, 40, 65, 90 minutes

    selected_df = pd.DataFrame({
        'time_idx': selected_points,
        'time': [time_points[i] for i in selected_points]
    })
    selected_df.to_csv('selected_timepoints.csv', index=False)

    # Save instance data at selected timepoints
    for i, idx in enumerate(selected_points):
        # RR data
        rr_df = pd.DataFrame({
            'instance': range(1, len(rr_instance_data[idx])+1),
            'cpu': rr_instance_data[idx]
        })
        rr_df.to_csv(f'rr_t{time_points[idx]}_cpu.csv', index=False)

        # CI data
        ci_df = pd.DataFrame({
            'instance': range(1, len(ci_instance_data[idx])+1),
            'cpu': ci_instance_data[idx]
        })
        ci_df.to_csv(f'ci_t{time_points[idx]}_cpu.csv', index=False)

    print("All data generated and saved successfully.")

    return {
        'main_data': df,
        'rr_instance_data': rr_instance_data,
        'ci_instance_data': ci_instance_data,
        'selected_points': selected_points,
        'rr_scaling_points': rr_scaling_points,
        'ci_scaling_points': ci_scaling_points
    }

if __name__ == "__main__":
    generate_autoscaling_data()
    print("Data generation complete. Files saved.")