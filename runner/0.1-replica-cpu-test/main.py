import time
from app_launcher import deploy, remove
from constants import APP_YAML_MAP
from utils import wait_for_pods_ready

APP_NAME = "onlineBoutique"
REPLICA_COUNTS = [1, 2, 5, 10]
NAMESPACE = "default"  # 根据实际情况修改
OBSERVE_DURATION = 120  # 每轮稳定观测时间（秒）

def run_experiment():
    for replicas in REPLICA_COUNTS:
        print(f"\n==== 部署 {APP_NAME}，replicas = {replicas} ====")
        # remove(APP_NAME)
        time.sleep(10)

        deploy(APP_NAME, replicas=replicas)

        if not wait_for_pods_ready(NAMESPACE):
            print("⚠️ Pod 未全部就绪，跳过该轮副本数")
            continue

        print(f"✅ 副本数 {replicas} 部署成功，等待 {OBSERVE_DURATION} 秒供 Prometheus 采样...")
        time.sleep(OBSERVE_DURATION)

    print("\n🧪 实验结束，正在清理部署")
    # remove(APP_NAME)

if __name__ == "__main__":
    run_experiment()
