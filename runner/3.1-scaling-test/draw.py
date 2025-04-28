import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

def plot_autoscaling_charts():
    # Create fig directory if it doesn't exist
    if not os.path.exists('fig'):
        os.makedirs('fig')

    # Set larger font size for all text
    plt.rcParams.update({
        'font.size': 14,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12
    })

    # Load data
    df = pd.read_csv('autoscaling_data.csv')

    # Load scaling points
    rr_scaling_df = pd.read_csv('rr_scaling_points.csv')
    ci_scaling_df = pd.read_csv('ci_scaling_points.csv')
    rr_scaling_points = rr_scaling_df['index'].tolist()
    ci_scaling_points = ci_scaling_df['index'].tolist()

    # Load selected timepoints
    selected_df = pd.read_csv('selected_timepoints.csv')
    selected_points = selected_df['time_idx'].tolist()
    selected_times = selected_df['time'].tolist()

    # Extract data
    time_points = df['time'].values
    traffic = df['traffic'].values
    rr_replicas = df['rr_replicas'].values
    ci_replicas = df['ci_replicas'].values

    # Plot 1: Instances over time
    plt.figure(figsize=(10, 6))
    plt.plot(time_points, traffic, label='Traffic Load', color='black', linestyle='--')
    plt.plot(time_points, rr_replicas, label='Round-Robin Instances', color='#4DBEEE', linewidth=2.5)
    plt.plot(time_points, ci_replicas, label='Controlled Imbalance Instances', color='#D95319', linewidth=2.5)

    # Add scale-out trigger points
    for p in rr_scaling_points:
        plt.plot(time_points[p], rr_replicas[p], 'o', color='#4DBEEE', markersize=10)

    for p in ci_scaling_points:
        plt.plot(time_points[p], ci_replicas[p], 'o', color='#D95319', markersize=10)

    plt.xlabel('Time (minutes)', fontsize=14)
    plt.ylabel('Instance Count / Traffic Load', fontsize=14)
    plt.title('Autoscaling Behavior Comparison', fontsize=18, pad=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper left', fontsize=12)
    plt.tight_layout()
    plt.savefig('fig/instances_over_time.png', dpi=300, bbox_inches='tight')

    # Plot 2: CPU utilization distribution
    box_data = []
    labels = []

    # Load instance data for selected timepoints
    for t in selected_times:
        rr_df = pd.read_csv(f'rr_t{t}_cpu.csv')
        ci_df = pd.read_csv(f'ci_t{t}_cpu.csv')

        box_data.extend([rr_df['cpu'].values, ci_df['cpu'].values])
        labels.extend([f'{t}m\nRR', f'{t}m\nCI'])

    plt.figure(figsize=(12, 6))
    bplot = plt.boxplot(box_data, positions=range(1, len(box_data)+1), patch_artist=True, widths=0.6)

    # Set colors
    colors = []
    for i in range(len(box_data)):
        if i % 2 == 0:  # Round-robin routing
            colors.append('#4DBEEE')
        else:  # Controlled imbalance routing
            colors.append('#D95319')

    for patch, color in zip(bplot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Add threshold lines
    plt.axhline(y=50, color='blue', linestyle='--', alpha=0.7, label='RR Scaling Threshold (50%)')
    plt.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='CI Scaling Threshold (70%)')

    plt.xticks(range(1, len(box_data)+1), labels)
    plt.ylabel('CPU Utilization (%)', fontsize=14)
    plt.title('CPU Utilization Distribution at Different Time Points', fontsize=18, pad=10)
    plt.grid(True, linestyle='--', alpha=0.7, axis='y')
    plt.ylim(0, 100)
    plt.legend(loc='upper left', fontsize=12)
    plt.tight_layout()
    plt.savefig('fig/cpu_distribution.png', dpi=300, bbox_inches='tight')

    # Plot 3: CPU utilization over time
    plt.figure(figsize=(12, 6))

    # Extract CPU min/max/mean values
    rr_min_cpu = df['rr_min_cpu'].values
    rr_max_cpu = df['rr_max_cpu'].values
    rr_mean_cpu = df['rr_mean_cpu'].values
    ci_min_cpu = df['ci_min_cpu'].values
    ci_max_cpu = df['ci_max_cpu'].values
    ci_mean_cpu = df['ci_mean_cpu'].values

    # Plot ranges with fill_between
    plt.fill_between(time_points, rr_min_cpu, rr_max_cpu, alpha=0.2, color='#4DBEEE')
    plt.fill_between(time_points, ci_min_cpu, ci_max_cpu, alpha=0.2, color='#D95319')

    # Plot mean lines
    plt.plot(time_points, rr_mean_cpu, color='#4DBEEE', linewidth=2, label='RR Mean CPU')
    plt.plot(time_points, ci_mean_cpu, color='#D95319', linewidth=2, label='CI Mean CPU')

    # Add threshold lines
    plt.axhline(y=50, color='blue', linestyle='--', alpha=0.7, label='RR Scaling Threshold (50%)')
    plt.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='CI Scaling Threshold (70%)')

    # Mark scaling points
    for p in rr_scaling_points:
        plt.plot(time_points[p], rr_mean_cpu[p], 'o', color='#4DBEEE', markersize=10)

    for p in ci_scaling_points:
        plt.plot(time_points[p], ci_mean_cpu[p], 'o', color='#D95319', markersize=10)

    plt.xlabel('Time (minutes)', fontsize=14)
    plt.ylabel('CPU Utilization (%)', fontsize=14)
    plt.title('CPU Utilization Range Over Time', fontsize=18)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper left', fontsize=12)
    plt.tight_layout()
    plt.savefig('fig/cpu_utilization_over_time.png', dpi=300, bbox_inches='tight')

    print("All charts saved to 'fig' directory.")

if __name__ == "__main__":
    plot_autoscaling_charts()
    print("Plotting complete. Charts saved to 'fig' directory.")