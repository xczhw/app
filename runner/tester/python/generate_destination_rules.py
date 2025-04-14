import argparse
import subprocess
import yaml
import os
import yaml

def get_services_from_yaml(app: str) -> list:
    """
    从 yaml_files/{app}/app/ 目录下的所有 yaml 文件中提取出所有 Service 的名称。
    """
    svc_names = []
    app_dir = os.path.join("yaml_files", app, "app")

    for file in os.listdir(app_dir):
        if not file.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(app_dir, file)
        with open(path, "r") as f:
            docs = list(yaml.safe_load_all(f))
            for doc in docs:
                if isinstance(doc, dict) and doc.get("kind") == "Service":
                    name = doc.get("metadata", {}).get("name")
                    if name:
                        svc_names.append(name)

    return svc_names

def generate_destination_rule(service, namespace, policy):
    return {
        "apiVersion": "networking.istio.io/v1beta1",
        "kind": "DestinationRule",
        "metadata": {
            "name": f"{service}-lb",
            "namespace": namespace
        },
        "spec": {
            "host": f"{service}.{namespace}.svc.cluster.local",
            "trafficPolicy": {
                "loadBalancer": {
                    "simple": policy
                }
            }
        }
    }

def generate_for_policy(policy, services, namespace, app):
    output_dir = os.path.join("yaml_files", app, "algo")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{policy}-{app}.yaml")

    with open(output_file, "w") as combined_file:
        for svc in services:
            dr = generate_destination_rule(svc, namespace, policy)
            yaml.dump(dr, combined_file, sort_keys=False)
            combined_file.write("\n---\n")
            print(f"✅ 为服务生成策略 {policy}: {svc}")

    print(f"\n📦 合并输出: {output_file}\n")

def generate_yaml(algo_list, namespace, app):
    services = get_services_from_yaml(app)
    if not services:
        print("⚠️ 没找到服务，退出。")
        return
    for algo in algo_list:
        generate_for_policy(algo, services, namespace, app)

def main(algo_list, namespace, app):
    generate_yaml(algo_list, namespace, app)

if __name__ == "__main__":

    from constants import ALGO_LIST

    parser = argparse.ArgumentParser(description="生成 Istio DestinationRule YAML 文件")
    parser.add_argument("--namespace", default="default", help="Kubernetes 命名空间（默认: default）")
    parser.add_argument("--policy", default="LEAST_REQUEST", help="负载均衡策略（默认: LEAST_REQUEST）")
    parser.add_argument("--app", default="onlineBoutique", help="应用名（默认: onlineBoutique）")
    parser.add_argument("--all-algo", action="store_true", help="为所有策略生成 YAML（覆盖 --policy）")

    args = parser.parse_args()


