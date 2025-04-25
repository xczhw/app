# monitor_evictions.py
import subprocess
import json
import time
import csv
import os
import matplotlib.pyplot as plt
from datetime import datetime

# Record start time
start_time = time.time()
# Lists to store events and metrics
pod_events = []
memory_metrics = []
cpu_metrics = []
timestamps = []
base_dir = f'./data/{int(start_time)}/'
os.makedirs('./data', exist_ok=True)  # Create the data directory first
os.makedirs(base_dir, exist_ok=True)

# Create a CSV file to record all events
events_csv_path = base_dir + 'pod_events.csv'
with open(events_csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Elapsed Time (s)', 'Event Type', 'Pod Name', 'Message'])

try:
    print("Starting to monitor Pod memory events (OOMKilled/Eviction)...")
    print("Press Ctrl+C to stop monitoring")

    while True:
        # Get all Pod events
        result = subprocess.run(
            ["kubectl", "get", "events", "--field-selector=involvedObject.kind=Pod", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        events = json.loads(result.stdout)

        # Get all Pod statuses to check for OOMKilled
        pod_status_result = subprocess.run(
            ["kubectl", "get", "pods", "-o", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        pod_data = json.loads(pod_status_result.stdout)

        current_time = time.time()
        elapsed = current_time - start_time

        # Check for OOMKilled Pods
        for pod in pod_data['items']:
            if 'status' in pod and 'containerStatuses' in pod['status']:
                for container in pod['status']['containerStatuses']:
                    if 'state' in container and 'terminated' in container['state']:
                        terminated = container['state']['terminated']
                        if terminated.get('reason') == 'OOMKilled':
                            pod_name = pod['metadata']['name']
                            # Try to get termination time
                            if 'finishedAt' in terminated:
                                try:
                                    # Parse ISO 8601 datetime format
                                    finished_time = datetime.strptime(
                                        terminated['finishedAt'].split('.')[0],
                                        "%Y-%m-%dT%H:%M:%S"
                                    ).timestamp()
                                    event_elapsed = finished_time - start_time
                                except (ValueError, IndexError):
                                    # If time parsing fails, use current time
                                    event_elapsed = elapsed
                            else:
                                event_elapsed = elapsed

                            if event_elapsed > 0:  # Only record events after test start
                                message = f"Container {container['name']} was OOMKilled"

                                # Check if this event has already been recorded
                                event_key = (pod_name, message)
                                if not any(event_key == (e[1], e[2]) for e in pod_events):
                                    # Save event to list
                                    pod_events.append((event_elapsed, pod_name, message))

                                    # Write to CSV
                                    with open(events_csv_path, 'a', newline='') as f:
                                        writer = csv.writer(f)
                                        writer.writerow([
                                            datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S'),
                                            f"{event_elapsed:.2f}",
                                            "OOMKilled",
                                            pod_name,
                                            message
                                        ])

                                    print(f"Detected OOMKilled event ({event_elapsed:.2f}s): Pod {pod_name} - {message}")

        # Check for new eviction or kill events
        for event in events['items']:
            event_type = None
            if "Killing" in event["message"] and "memory" in event["message"].lower():
                event_type = "Eviction (Memory)"
            elif "OOM killed" in event["message"].lower() or "oomkilled" in event["message"].lower():
                event_type = "OOMKilled"
            elif "Killing" in event["message"]:
                event_type = "Pod Killed"

            if event_type:
                try:
                    event_time = datetime.strptime(
                        event["firstTimestamp"].split('.')[0],
                        "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
                except (ValueError, IndexError):
                    event_time = current_time

                event_elapsed = event_time - start_time
                if event_elapsed > 0:  # Only record events after test start
                    pod_name = event["involvedObject"]["name"]
                    message = event["message"]

                    # Check if this event has already been recorded
                    event_key = (pod_name, message)
                    if not any(event_key == (e[1], e[2]) for e in pod_events):
                        # Save event to list
                        pod_events.append((event_elapsed, pod_name, message))

                        # Write to CSV
                        with open(events_csv_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                datetime.fromtimestamp(event_time).strftime('%Y-%m-%d %H:%M:%S'),
                                f"{event_elapsed:.2f}",
                                event_type,
                                pod_name,
                                message
                            ])

                        print(f"Detected {event_type} event ({event_elapsed:.2f}s): Pod {pod_name} - {message}")

        # Get current resource usage
        try:
            memory_result = subprocess.run(
                ["kubectl", "top", "pods", "-l", "app=memory-service", "--no-headers"],
                capture_output=True,
                text=True,
                check=True
            )

            if memory_result.stdout.strip():
                # Parse output
                pod_metrics = memory_result.stdout.strip().split('\n')
                total_memory = 0
                total_cpu = 0
                pod_count = 0

                for line in pod_metrics:
                    parts = line.split()
                    if len(parts) >= 3:
                        pod_name = parts[0]
                        cpu = parts[1].rstrip('m')  # Remove 'm' suffix
                        memory = parts[2].rstrip('Mi')  # Remove 'Mi' suffix

                        try:
                            memory_value = float(memory)
                            cpu_value = float(cpu)
                            total_memory += memory_value
                            total_cpu += cpu_value
                            pod_count += 1
                        except ValueError:
                            pass

                if pod_count > 0:
                    avg_memory = total_memory / pod_count
                    avg_cpu = total_cpu / pod_count
                    memory_metrics.append((elapsed, avg_memory, pod_count))
                    cpu_metrics.append((elapsed, avg_cpu))
                    timestamps.append(elapsed)

                    print(f"Current status ({elapsed:.2f}s): {pod_count} Pods, Avg Memory: {avg_memory:.2f}Mi, Avg CPU: {avg_cpu:.2f}m")
        except subprocess.CalledProcessError as e:
            print(f"Error getting resource metrics: {e}")

        # Check every 5 seconds
        time.sleep(5)

except KeyboardInterrupt:
    print("\nMonitoring stopped. Generating report...")

    # Create visualization charts
    plt.figure(figsize=(16, 12))

    # Plot memory usage
    plt.subplot(3, 1, 1)
    memory_times = [x[0] for x in memory_metrics]
    memory_values = [x[1] for x in memory_metrics]
    pod_counts = [x[2] for x in memory_metrics]

    plt.plot(memory_times, memory_values, 'b-', label='Avg Memory (Mi)')
    plt.ylabel('Memory (Mi)')
    plt.title('Memory Usage and Pod Count')
    plt.grid(True)

    # Show pod count on the same plot
    ax2 = plt.twinx()
    ax2.plot(memory_times, pod_counts, 'g-', label='Pod Count')
    ax2.set_ylabel('Number of Pods')

    # Mark events
    for event in pod_events:
        plt.axvline(x=event[0], color='r', linestyle='--', alpha=0.5)
        plt.text(event[0], max(memory_values) if memory_values else 100,
                 'OOMKilled' if "OOM" in event[2] else 'Eviction',
                 rotation=90, verticalalignment='bottom')

    # Add legend
    lines1, labels1 = plt.gca().get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    # Plot CPU usage
    plt.subplot(3, 1, 2)
    cpu_times = [x[0] for x in cpu_metrics]
    cpu_values = [x[1] for x in cpu_metrics]

    plt.plot(cpu_times, cpu_values, 'orange', label='Avg CPU (m)')
    plt.ylabel('CPU (millicores)')
    plt.title('CPU Usage')
    plt.grid(True)
    plt.legend()

    # Mark events
    for event in pod_events:
        plt.axvline(x=event[0], color='r', linestyle='--', alpha=0.5)

    # Plot events timeline
    plt.subplot(3, 1, 3)
    event_times = [x[0] for x in pod_events]

    # Categorize events
    oom_events = [(time, pod, msg) for time, pod, msg in pod_events if "OOM" in msg]
    eviction_events = [(time, pod, msg) for time, pod, msg in pod_events if "OOM" not in msg]

    # Plot OOMKilled events
    if oom_events:
        oom_times = [x[0] for x in oom_events]
        oom_y = [1 for _ in oom_events]
        plt.scatter(oom_times, oom_y, color='red', s=100, marker='x', label='OOMKilled')
        for i, event in enumerate(oom_events):
            plt.text(event[0], 1.1, f"Pod: {event[1]}", rotation=45, verticalalignment='bottom')

    # Plot Eviction events
    if eviction_events:
        eviction_times = [x[0] for x in eviction_events]
        eviction_y = [0.5 for _ in eviction_events]
        plt.scatter(eviction_times, eviction_y, color='purple', s=100, marker='o', label='Eviction')
        for i, event in enumerate(eviction_events):
            plt.text(event[0], 0.6, f"Pod: {event[1]}", rotation=45, verticalalignment='bottom')

    plt.title('Pod Events Timeline')
    plt.xlabel('Elapsed Time (seconds)')
    plt.ylim(0, 1.5)
    plt.yticks([0.5, 1], ['Eviction', 'OOMKilled'])
    plt.grid(True, axis='x')
    plt.legend()

    plt.tight_layout()
    plt.savefig(base_dir + 'pod_events_results.png')
    print(f"Report generated: {base_dir}pod_events_results.png")
    print(f"Events CSV saved: {events_csv_path}")

except Exception as e:
    print(f"Error during monitoring: {e}")