import argparse
import subprocess
import yaml
import os
from constants import APP_YAML_MAP

def update_deployment_replicas(yaml_file_path: str, replicas: int, output_file_path: str = None):
    """
    修改 Kubernetes YAML 文件中所有 Deployment 的副本数（replicas）

    :param yaml_file_path: 输入的 YAML 文件路径
    :param replicas: 想要设置的副本数
    :param output_file_path: 输出文件路径（如果为 None，则覆盖原文件）
    """
    with open(yaml_file_path, 'r') as f:
        docs = list(yaml.safe_load_all(f))

    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "Deployment":
            doc.setdefault("spec", {})["replicas"] = replicas

    output_path = output_file_path if output_file_path else yaml_file_path
    with open(output_path, 'w') as f:
        yaml.dump_all(docs, f, sort_keys=False)

def deploy(app_name, replicas):
    yaml_path = APP_YAML_MAP.get(app_name)
    if not yaml_path:
        print(f"错误：未找到应用 '{app_name}' 的 YAML 文件路径。")
        return
    if replicas > 0 and os.path.isdir(yaml_path):
        for file in os.listdir(yaml_path):
            if file.endswith((".yaml", ".yml")):
                full_path = os.path.join(yaml_path, file)
                update_deployment_replicas(full_path, replicas, full_path)

    try:
        print(f"正在部署应用 '{app_name}'，YAML 文件：{yaml_path}")
        subprocess.run(["kubectl", "apply", "-f", yaml_path], check=True)
        print("部署完成。")
    except subprocess.CalledProcessError as e:
        print("部署失败：", e)

def remove(app_name):
    yaml_path = APP_YAML_MAP.get(app_name)
    if not yaml_path:
        print(f"错误：未找到应用 '{app_name}' 的 YAML 文件路径。")
        return
    try:
        print(f"正在删除应用 '{app_name}'，YAML 文件：{yaml_path}")
        subprocess.run(["kubectl", "delete", "-f", yaml_path], check=True)
        print("删除完成。")
    except subprocess.CalledProcessError as e:
        print("删除失败：", e)

def main():
    parser = argparse.ArgumentParser(description="根据应用名称部署对应的 YAML 文件")
    parser.add_argument("app", help="应用程序名称")
    args = parser.parse_args()

    deploy(args.app)

if __name__ == "__main__":
    main()
