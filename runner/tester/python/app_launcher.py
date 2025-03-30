import argparse
import subprocess

# 应用与 YAML 文件路径的映射表
APP_YAML_MAP = {
    "onlineBoutique": "./yaml/onlineBoutique/app",
    "whoami": "./yamls/whoami/app"
}

def deploy(app_name):
    yaml_path = APP_YAML_MAP.get(app_name)
    if not yaml_path:
        print(f"错误：未找到应用 '{app_name}' 的 YAML 文件路径。")
        return

    try:
        print(f"正在部署应用 '{app_name}'，YAML 文件：{yaml_path}")
        subprocess.run(["kubectl", "apply", "-f", yaml_path], check=True)
        print("部署完成。")
    except subprocess.CalledProcessError as e:
        print("部署失败：", e)

def main():
    parser = argparse.ArgumentParser(description="根据应用名称部署对应的 YAML 文件")
    parser.add_argument("app", help="应用程序名称")
    args = parser.parse_args()

    deploy(args.app)

if __name__ == "__main__":
    main()
