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

# 应用与 YAML 文件路径的映射表
APP_YAML_MAP = {
    "onlineBoutique": "./yaml_files/onlineBoutique/app",
    "whoami": "./yaml_files/whoami/app"
}