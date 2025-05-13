import requests
import threading
import uuid
import time
import sys

# 服务地址
SERVICE_URL = "http://cpu-load-svc"
# 请求总数
TOTAL_REQUESTS = 100
# 结果跟踪
results = {"success": 0, "failed": 0}
# 锁，用于线程安全更新结果
results_lock = threading.Lock()

def send_request():
    request_id = str(uuid.uuid4())
    try:
        response = requests.get(
            SERVICE_URL,
            headers={"X-Request-ID": request_id},
            timeout=40
        )
        with results_lock:
            results["success"] += 1
        print(f"请求 {request_id} 成功")
    except Exception as e:
        with results_lock:
            results["failed"] += 1
        print(f"请求 {request_id} 失败: {str(e)}")

# 启动多个线程发送请求
threads = []
for i in range(TOTAL_REQUESTS):
    t = threading.Thread(target=send_request)
    threads.append(t)
    t.start()
    # 每0.1秒发送一个请求
    time.sleep(0.1)

# 触发缩容
print("所有请求已发送，准备触发缩容...")
# 此处可以通过手动方式，或通过kubectl scale命令减少副本数

# 等待所有请求完成
for t in threads:
    t.join()

# 打印结果
print(f"结果统计: 成功 {results['success']}, 失败 {results['failed']}")