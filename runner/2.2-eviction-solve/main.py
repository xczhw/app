import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os

# 设置随机种子以确保结果可复现
np.random.seed(42)

# 模拟参数
num_replicas = 5  # 微服务副本数量
simulation_time = 500  # 模拟总时间步数
request_rate = 50  # 每时间步的平均请求数
memory_hard_limit = 95  # 内存硬限制(%)
cold_start_time = 20  # 冷启动时间(时间步)

# 微服务副本类
class Replica:
    def __init__(self, id):
        self.id = id
        self.cpu_usage = 30 + np.random.random() * 10  # 初始CPU使用率
        self.memory_usage = 20 + np.random.random() * 10  # 初始内存使用率
        self.restarting = False  # 是否在重启
        self.restart_timer = 0  # 重启计时器
        self.eviction_count = 0  # 被驱逐次数
    
    def process_request(self):
        if self.restarting:
            return False  # 重启中无法处理请求
        
        # CPU使用率几乎不变，只有小幅波动
        self.cpu_usage = min(95, self.cpu_usage + np.random.random() * 2 - 1)
        
        # 内存使用率增长有较大方差
        memory_increase = np.random.gamma(2, 2)  # 使用gamma分布产生右偏的方差大的内存增长
        
        self.memory_usage = min(100, self.memory_usage + memory_increase)
        
        # 检查是否需要驱逐
        if self.memory_usage > memory_hard_limit:
            self.evict()
            return False  # 请求失败
        
        return True  # 请求成功
    
    def update(self):
        # 自然资源减少（内存释放等）
        if not self.restarting:
            self.cpu_usage = max(20, self.cpu_usage - 0.2)
            self.memory_usage = max(10, self.memory_usage - 0.5)
        
        # 处理重启逻辑
        if self.restarting:
            self.restart_timer -= 1
            if self.restart_timer <= 0:
                self.restarting = False
                self.cpu_usage = 30 + np.random.random() * 10
                self.memory_usage = 20 + np.random.random() * 10
    
    def evict(self):
        self.restarting = True
        self.restart_timer = cold_start_time
        self.eviction_count += 1

# 路由策略类
class RoundRobinStrategy:
    def __init__(self, replicas):
        self.replicas = replicas
        self.index = 0
    
    def select_replica(self):
        active_replicas = [r for r in self.replicas if not r.restarting]
        if not active_replicas:
            return None
        
        # 简单的轮询选择
        selected = active_replicas[self.index % len(active_replicas)]
        self.index = (self.index + 1) % len(active_replicas)
        return selected

class LeastCPUStrategy:
    def __init__(self, replicas):
        self.replicas = replicas
    
    def select_replica(self):
        active_replicas = [r for r in self.replicas if not r.restarting]
        if not active_replicas:
            return None
        
        # 选择CPU使用率最低的副本
        return min(active_replicas, key=lambda r: r.cpu_usage)

class ResourceAwareStrategy:
    def __init__(self, replicas):
        self.replicas = replicas
    
    def select_replica(self):
        active_replicas = [r for r in self.replicas if not r.restarting]
        if not active_replicas:
            return None
        
        # 选择综合资源评分最好的副本，主要考虑内存使用率
        # 使用综合评分 = 0.2*CPU使用率 + 0.8*内存使用率
        return min(active_replicas, key=lambda r: 0.2*r.cpu_usage + 0.8*r.memory_usage)

# 模拟类
class Simulation:
    def __init__(self):
        # 为每个策略创建独立的副本集
        self.rr_replicas = [Replica(i) for i in range(num_replicas)]
        self.lc_replicas = [Replica(i) for i in range(num_replicas)]
        self.ra_replicas = [Replica(i) for i in range(num_replicas)]
        
        self.rr_strategy = RoundRobinStrategy(self.rr_replicas)
        self.lc_strategy = LeastCPUStrategy(self.lc_replicas)
        self.ra_strategy = ResourceAwareStrategy(self.ra_replicas)
        
        # 记录每个策略的指标
        self.metrics = {
            "RR": {
                "evictions": [],     # 每个时间步的总驱逐次数
                "memory_usage": [],  # 副本的平均内存使用率
                "cpu_usage": [],     # 副本的平均CPU使用率
                "active_replicas": [] # 活跃副本数量
            },
            "LC": {
                "evictions": [],
                "memory_usage": [],
                "cpu_usage": [],
                "active_replicas": []
            },
            "RA": {
                "evictions": [],
                "memory_usage": [],
                "cpu_usage": [],
                "active_replicas": []
            }
        }
    
    def run(self):
        for time_step in range(simulation_time):
            # 更新所有副本状态
            for replica in self.rr_replicas + self.lc_replicas + self.ra_replicas:
                replica.update()
            
            # 处理Round-Robin策略的请求
            self.process_strategy_requests("RR", self.rr_strategy, self.rr_replicas)
            
            # 处理Least-CPU策略的请求
            self.process_strategy_requests("LC", self.lc_strategy, self.lc_replicas)
            
            # 处理Resource-Aware策略的请求
            self.process_strategy_requests("RA", self.ra_strategy, self.ra_replicas)
            
            # 打印进度
            if time_step % 50 == 0:
                print(f"Simulation progress: {time_step}/{simulation_time}")
    
    def process_strategy_requests(self, strategy_name, strategy, replicas):
        # 生成这个时间步的请求数
        num_requests = np.random.poisson(request_rate)
        
        # 记录当前状态
        active_replicas = [r for r in replicas if not r.restarting]
        evictions_total = sum(r.eviction_count for r in replicas)
        
        active_count = len(active_replicas)
        if active_count > 0:
            avg_memory = sum(r.memory_usage for r in active_replicas) / active_count
            avg_cpu = sum(r.cpu_usage for r in active_replicas) / active_count
        else:
            avg_memory = 0
            avg_cpu = 0
        
        # 处理请求
        for _ in range(num_requests):
            replica = strategy.select_replica()
            if replica:
                replica.process_request()
        
        # 记录指标
        self.metrics[strategy_name]["evictions"].append(evictions_total)
        self.metrics[strategy_name]["memory_usage"].append(avg_memory)
        self.metrics[strategy_name]["cpu_usage"].append(avg_cpu)
        self.metrics[strategy_name]["active_replicas"].append(active_count)
    
    def plot_results(self):
        # 设置图表样式
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 1. 累积驱逐次数对比
        plt.figure(figsize=(10, 6))
        for strategy_name in ["RR", "LC", "RA"]:
            plt.plot(self.metrics[strategy_name]["evictions"], label=strategy_name)
        
        plt.title('Cumulative Eviction Count', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Number of Evictions', fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.savefig('eviction_comparison.png', dpi=300)
        
        # 2. 平均内存使用率对比
        plt.figure(figsize=(10, 6))
        window_size = 10  # 使用移动平均减少噪声
        for strategy_name in ["RR", "LC", "RA"]:
            memory_usage = self.metrics[strategy_name]["memory_usage"]
            moving_avg = pd.Series(memory_usage).rolling(window=window_size).mean()
            plt.plot(moving_avg, label=strategy_name)
        
        plt.title('Average Memory Usage', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Memory Usage (%)', fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.savefig('memory_usage_comparison.png', dpi=300)
        
        # 3. 平均CPU使用率对比
        plt.figure(figsize=(10, 6))
        for strategy_name in ["RR", "LC", "RA"]:
            cpu_usage = self.metrics[strategy_name]["cpu_usage"]
            moving_avg = pd.Series(cpu_usage).rolling(window=window_size).mean()
            plt.plot(moving_avg, label=strategy_name)
        
        plt.title('Average CPU Usage', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('CPU Usage (%)', fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.savefig('cpu_usage_comparison.png', dpi=300)
        
        # 4. 活跃副本数量对比
        plt.figure(figsize=(10, 6))
        for strategy_name in ["RR", "LC", "RA"]:
            active_replicas = self.metrics[strategy_name]["active_replicas"]
            moving_avg = pd.Series(active_replicas).rolling(window=window_size).mean()
            plt.plot(moving_avg, label=strategy_name)
        
        plt.title('Number of Active Replicas', fontsize=14)
        plt.xlabel('Time Step', fontsize=12)
        plt.ylabel('Active Replicas', fontsize=12)
        plt.legend()
        plt.tight_layout()
        plt.savefig('active_replicas_comparison.png', dpi=300)
        
        # 5. 最终状态汇总条形图
        final_metrics = {
            "RR": {
                "Total Evictions": self.metrics["RR"]["evictions"][-1],
                "Final Active Replicas": self.metrics["RR"]["active_replicas"][-1],
            },
            "LC": {
                "Total Evictions": self.metrics["LC"]["evictions"][-1],
                "Final Active Replicas": self.metrics["LC"]["active_replicas"][-1],
            },
            "RA": {
                "Total Evictions": self.metrics["RA"]["evictions"][-1],
                "Final Active Replicas": self.metrics["RA"]["active_replicas"][-1],
            }
        }
        
        df = pd.DataFrame(final_metrics).T
        
        plt.figure(figsize=(12, 6))
        ax1 = plt.subplot(1, 2, 1)
        sns.barplot(y=df.index, x="Total Evictions", data=df, ax=ax1)
        ax1.set_title('Total Evictions', fontsize=14)
        ax1.grid(True, alpha=0.3, axis='x')
        
        ax2 = plt.subplot(1, 2, 2)
        sns.barplot(y=df.index, x="Final Active Replicas", data=df, ax=ax2)
        ax2.set_title('Final Active Replicas', fontsize=14)
        ax2.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        plt.savefig('summary_comparison.png', dpi=300)
        
        # 打印改进百分比
        rr_evictions = self.metrics["RR"]["evictions"][-1]
        lc_evictions = self.metrics["LC"]["evictions"][-1]
        ra_evictions = self.metrics["RA"]["evictions"][-1]
        
        rr_improvement = (rr_evictions - ra_evictions) / rr_evictions * 100
        lc_improvement = (lc_evictions - ra_evictions) / lc_evictions * 100
        
        print("\nEviction Reduction Percentages:")
        print(f"vs Round-Robin: {rr_improvement:.2f}%")
        print(f"vs Least-CPU: {lc_improvement:.2f}%")
        
        # 保存最终数据到CSV
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 保存累积驱逐次数
        eviction_data = pd.DataFrame({
            'Time Step': range(simulation_time),
            'Round-Robin': self.metrics["RR"]["evictions"],
            'Least-CPU': self.metrics["LC"]["evictions"],
            'Resource-Aware': self.metrics["RA"]["evictions"]
        })
        eviction_data.to_csv('results/eviction_data.csv', index=False)
        
        # 保存摘要数据
        summary_data = pd.DataFrame({
            'Strategy': ["Round-Robin", "Least-CPU", "Resource-Aware"],
            'Total Evictions': [rr_evictions, lc_evictions, ra_evictions],
            'Eviction Reduction vs RR (%)': [0, (rr_evictions - lc_evictions) / rr_evictions * 100, rr_improvement],
            'Eviction Reduction vs LC (%)': [(lc_evictions - rr_evictions) / lc_evictions * 100, 0, lc_improvement]
        })
        summary_data.to_csv('results/summary_data.csv', index=False)

# 运行模拟
sim = Simulation()
sim.run()
sim.plot_results()