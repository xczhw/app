#!/bin/bash

# ========================================
# Kubernetes & Containerd Data Migration Script
# ========================================

# 节点列表：node0 到 node5
SERVERS=(
  "node0"
  "node1"
  "node2"
  "node3"
  "node4"
  "node5"
)

# 用户名
USER="xczhw"

# 执行远程命令的函数
run_remote_command() {
    SERVER=$1
    COMMAND=$2
    echo "������ 执行命令：$COMMAND 在服务器：$SERVER"
    ssh "${SERVER}" "${COMMAND}"
}

# 移动数据目录的函数
migrate_server() {
    SERVER=$1
    echo "������ 正在迁移服务器：$SERVER"

    # 停止服务
    run_remote_command $SERVER "sudo systemctl stop kubelet && sudo systemctl stop containerd"

    # 创建目录
    run_remote_command $SERVER "sudo mkdir -p /mydata/containerd && sudo mkdir -p /mydata/kubelet"

    # 修改 containerd 配置
    run_remote_command $SERVER "sudo sed -i 's|root = \"/var/lib/containerd\"|root = \"/mydata/containerd/root\"|' /etc/containerd/config.toml"
    run_remote_command $SERVER "sudo sed -i 's|state = \"/var/lib/containerd\"|state = \"/mydata/containerd/state\"|' /etc/containerd/config.toml"

    # 修改 kubelet 配置
    run_remote_command $SERVER "sudo sed -i 's|--root-dir=/var/lib/kubelet|--root-dir=/mydata/kubelet|' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf"

    # 移动旧数据
    run_remote_command $SERVER "sudo mv /var/lib/containerd/* /mydata/containerd/ || true"
    run_remote_command $SERVER "sudo mv /var/lib/kubelet/* /mydata/kubelet/ || true"

    # 更新权限与 SELinux
    run_remote_command $SERVER "sudo chown -R root:root /mydata/containerd /mydata/kubelet"
    run_remote_command $SERVER "sudo restorecon -R /mydata || true"

    # 重载 daemon 并重启服务
    run_remote_command $SERVER "sudo systemctl daemon-reload"
    run_remote_command $SERVER "sudo systemctl restart containerd && sudo systemctl restart kubelet"

    # 检查服务状态
    run_remote_command $SERVER "sudo systemctl status containerd"
    run_remote_command $SERVER "sudo systemctl status kubelet"

    echo "✅ 服务器 $SERVER 的迁移完成！"
}

# 循环遍历服务器列表并进行迁移
for SERVER in "${SERVERS[@]}"; do
    migrate_server $SERVER
done

echo "������ 所有服务器的迁移已完成！"

