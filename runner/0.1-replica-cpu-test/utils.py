import subprocess
import time
def wait_for_pods_ready(namespace, timeout=300):
    print("⏳ 正在等待所有 Pod 就绪...")
    start = time.time()
    while time.time() - start < timeout:
        output = subprocess.getoutput(f"kubectl get pods -n {namespace}")
        lines = output.splitlines()[1:]  # 跳过表头
        all_running = all("Running" in line for line in lines)
        if all_running:
            print("✅ 所有 Pod 已就绪")
            return True
        time.sleep(5)
    print("❌ 等待超时，部分 Pod 未就绪")
    return False