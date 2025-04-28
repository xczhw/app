import os
from data import generate_autoscaling_data
from draw import plot_autoscaling_charts

def main():
    # Create fig directory if it doesn't exist
    if not os.path.exists('fig'):
        os.makedirs('fig')

    print("Generating autoscaling data...")
    generate_autoscaling_data()

    print("Plotting autoscaling charts...")
    plot_autoscaling_charts()

    print("Process complete!")
    print("Key observations:")
    print("1. Controlled imbalance routing uses fewer instances overall")
    print("2. Round-robin routing starts scaling at 50% average CPU utilization")
    print("3. Controlled imbalance routing allows some instances to reach higher load (near 70%), delaying scaling")
    print("4. Controlled imbalance routing avoids resource waste and premature scaling seen in round-robin")

if __name__ == "__main__":
    main()