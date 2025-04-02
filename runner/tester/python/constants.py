# constants.py

# 支持的策略列表
ALGO_LIST = [
    "ROUND_ROBIN",
    "RANDOM",
    "LEAST_REQUEST",
    "LEAST_CONN"
]

APP_SERVICE_NAME_MAP = {
    "whoami": "caller",  # 'whoami' 应用对应的 Jaeger 服务名是 'caller'
    "onlineBoutique": "frontend",  # 'onlineBoutique' 应用对应的 Jaeger 服务名是 'frontend'
}