import argparse
import subprocess
import yaml
import os

def get_services(namespace):
    try:
        output = subprocess.check_output(
            ["kubectl", "get", "svc", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"],
            text=True
        )
        services = output.strip().split()
        return [s for s in services if not s.startswith("kube-") and s != "kubernetes"]
    except subprocess.CalledProcessError as e:
        print(f"❌ 获取服务失败: {e}")
        return []

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
    output_dir = os.path.join("yaml", app, "algo")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{policy}-{app}.yaml")
    temp_file_paths = []

    with open(output_file, "w") as combined_file:
        for svc in services:
            dr = generate_destination_rule(svc, namespace, policy)

            # 临时文件路径（用于删除）
            temp_path = os.path.join(output_dir, f"{svc}-{policy}.tmp.yaml")
            temp_file_paths.append(temp_path)

            with open(temp_path, "w") as f:
                yaml.dump(dr, f, sort_keys=False)

            yaml.dump(dr, combined_file, sort_keys=False)
            combined_file.write("\n---\n")

            print(f"✅ 为服务生成策略 {policy}: {svc}")

    # 删除临时文件
    for path in temp_file_paths:
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ 删除临时文件: {path}")

    print(f"\n📦 合并输出: {output_file}\n")

def generate_yaml(algo_list, namespace, app):
    services = get_services(namespace)
    for algo in algo_list:
        generate_for_policy(algo, services, namespace, app)

def main():
    from constants import ALGO_LIST

    parser = argparse.ArgumentParser(description="生成 Istio DestinationRule YAML 文件")
    parser.add_argument("--namespace", default="default", help="Kubernetes 命名空间（默认: default）")
    parser.add_argument("--policy", default="LEAST_REQUEST", help="负载均衡策略（默认: LEAST_REQUEST）")
    parser.add_argument("--app", default="onlineBoutique", help="应用名（默认: onlineBoutique）")
    parser.add_argument("--all-algo", action="store_true", help="为所有策略生成 YAML（覆盖 --policy）")

    args = parser.parse_args()
    services = get_services(args.namespace)
    if not services:
        print("⚠️ 没找到服务，退出。")
        return

    if args.all_algo:
        for algo in ALGO_LIST:
            print(f"\n🚀 正在生成策略: {algo}")
            generate_for_policy(algo, services, args.namespace, args.app)
    else:
        generate_for_policy(args.policy, services, args.namespace, args.app)

if __name__ == "__main__":
    main()
