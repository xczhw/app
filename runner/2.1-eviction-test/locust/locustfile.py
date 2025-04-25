from locust import HttpUser, task, between
import time
import random

class MemoryUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def allocate_small(self):
        """分配小块内存（5-10MB）"""
        size = random.randint(5, 10)
        # 正确的调用方式，指定name只是用于统计分类
        self.client.post("/allocate", json={"size_mb": size}, name="/allocate (small)")

    @task(1)
    def allocate_large(self):
        """分配大块内存（20-50MB）"""
        size = random.randint(20, 50)
        # 正确的调用方式，指定name只是用于统计分类
        self.client.post("/allocate", json={"size_mb": size}, name="/allocate (large)")

    @task(3)
    def get_metrics(self):
        """获取当前内存指标"""
        self.client.get("/metrics")