from locust import HttpUser, task, between, events
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义全局变量记录测试指标
class TestStats:
    def __init__(self):
        self.total_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.start_time = time.time()

    def log_request(self, request_type, name, response_time, response_length, exception):
        self.total_requests += 1
        if exception:
            self.failed_requests += 1
        self.response_times.append(response_time)

    def print_stats(self):
        duration = time.time() - self.start_time
        if not self.response_times:
            return

        avg_response_time = sum(self.response_times) / len(self.response_times)
        failure_rate = (self.failed_requests / self.total_requests) * 100 if self.total_requests > 0 else 0

        logger.info(f"测试运行时间: {duration:.2f}秒")
        logger.info(f"总请求数: {self.total_requests}")
        logger.info(f"失败请求数: {self.failed_requests}")
        logger.info(f"失败率: {failure_rate:.2f}%")
        logger.info(f"平均响应时间: {avg_response_time:.2f}毫秒")

# 创建统计实例
stats = TestStats()

# 注册事件钩子
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    stats.log_request(request_type, name, response_time, response_length, exception)

@events.test_stop.add_listener
def on_test_stop(**kwargs):
    stats.print_stats()

class CPULoadTestUser(HttpUser):
    # 等待时间，会影响RPS
    wait_time = between(1, 3)

    def on_start(self):
        # 在每个用户启动时记录测试开始时间（近似全局）
        self.start_time = time.time()

    @task
    def test_cpu_load(self):
        # 根据当前时间动态调整强度参数
        # 这是为了在测试不同阶段产生不同的CPU负载
        current_time = time.time() - self.start_time

        # 测试阶段划分（总时间30分钟）
        if current_time < 300:  # 0-5分钟
            intensity = 50000  # 低负载
        elif current_time < 600:  # 5-10分钟
            intensity = 100000  # 中低负载
        elif current_time < 900:  # 10-15分钟
            intensity = 150000  # 中负载
        elif current_time < 1200:  # 15-20分钟
            intensity = 200000  # 中高负载
        elif current_time < 1500:  # 20-25分钟
            intensity = 250000  # 高负载
        else:  # 25-30分钟
            intensity = 300000  # 极高负载（可能导致过载）

        # 发送请求到测试服务
        start_time = time.time()
        with self.client.get(
            f"/test?intensity={intensity}",
            catch_response=True,
            name=f"CPU测试-强度{intensity}"
        ) as response:
            if response.status_code != 200:
                response.failure(f"请求失败，状态码: {response.status_code}")
            elif time.time() - start_time > 2:  # 2秒超时
                response.failure("请求超时")
            else:
                response.success()

    @task(3)  # 更频繁执行这个任务，增加负载
    def test_cpu_load_higher(self):
        # 固定使用高强度参数
        intensity = 200000

        with self.client.get(
            f"/test?intensity={intensity}",
            catch_response=True,
            name=f"高强度CPU测试"
        ) as response:
            if response.status_code != 200:
                response.failure(f"请求失败，状态码: {response.status_code}")
            else:
                response.success()
