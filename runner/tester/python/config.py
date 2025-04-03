import argparse

parser = argparse.ArgumentParser(description="统一配置参数")
parser.add_argument("app", help="应用名称")
# parser.add_argument('--app', type=str, default=None, help='App name (optional)')
parser.add_argument("--namespace", default="default", help="Kubernetes 命名空间")
parser.add_argument("--run-seconds", type=int, default=300, help="每个策略运行时长（秒）")
parser.add_argument("--pause-seconds", type=int, default=15, help="策略切换之间的间隔（秒）")
parser.add_argument("--policy", default="LEAST_REQUEST", help="负载均衡策略（默认: LEAST_REQUEST）")
parser.add_argument("--all-algo", action="store_true", help="为所有策略生成 YAML （覆盖 --policy）")
parser.add_argument("--interval", type=int, default=1)
parser.add_argument('--num_experiments', type=int, default=1, help='Number of recent experiments to process')
parser.add_argument("--replicas", type=int, default=20, help="Number of replicas to set (default: 20).")

args = parser.parse_args()
