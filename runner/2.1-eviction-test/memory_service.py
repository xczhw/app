# memory_service.py
from flask import Flask, request, jsonify
import time
import gc
import os
import psutil
import threading
import logging

app = Flask(__name__)
memory_store = []
lock = threading.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/metrics')
def metrics():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    cpu_percent = process.cpu_percent(interval=0.1)

    return jsonify({
        "memory_usage_mb": memory_info.rss / (1024 * 1024),
        "cpu_percent": cpu_percent,
        "items_in_memory": len(memory_store)
    })

@app.route('/allocate', methods=['POST'])
def allocate_memory():
    # 接收数据大小参数（MB）
    size_mb = int(request.json.get('size_mb', 10))
    hold_time = int(request.json.get('hold_time_sec', 60))

    # 分配指定大小的内存 (MB)
    new_data = bytearray(size_mb * 1024 * 1024)

    # 将数据添加到内存存储
    with lock:
        memory_store.append((new_data, time.time() + hold_time))

    # 执行一些CPU工作以保持固定的CPU使用率
    start_time = time.time()
    while time.time() - start_time < 0.1:
        _ = [i*i for i in range(10000)]

    # 清理过期数据
    cleanup_memory()

    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 * 1024)
    logger.info(f"Memory usage: {memory_mb:.2f} MB, Items: {len(memory_store)}")

    return jsonify({
        "status": "allocated",
        "size_mb": size_mb,
        "memory_usage_mb": memory_mb,
        "items": len(memory_store)
    })

@app.route('/process', methods=['POST'])
def process_data():
    # 接收数据大小参数
    data_size = int(request.json.get('size_kb', 100))
    hold_time = int(request.json.get('hold_time_sec', 60))

    # 分配指定大小的内存 (KB)
    new_data = bytearray(data_size * 1024)

    # 将数据添加到内存存储
    with lock:
        memory_store.append((new_data, time.time() + hold_time))

    # 执行一些CPU工作以保持固定的CPU使用率
    start_time = time.time()
    while time.time() - start_time < 0.1:
        _ = [i*i for i in range(10000)]

    # 清理过期数据
    cleanup_memory()

    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 * 1024)
    logger.info(f"Memory usage: {memory_mb:.2f} MB, Items: {len(memory_store)}")

    return jsonify({
        "status": "processed",
        "memory_mb": memory_mb,
        "items": len(memory_store)
    })

def cleanup_memory():
    """清理已过期的内存数据"""
    current_time = time.time()
    with lock:
        global memory_store
        memory_store = [(data, expire_time) for data, expire_time in memory_store if expire_time > current_time]

    # 强制垃圾回收
    gc.collect()

# 启动定时清理线程
def cleanup_thread():
    while True:
        cleanup_memory()
        time.sleep(5)

threading.Thread(target=cleanup_thread, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)