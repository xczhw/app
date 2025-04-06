#!/bin/bash

# ========================================
# Kubernetes & Containerd 迁移验证脚本
# ========================================

NODES=(node0 node1 node2 node3 node4 node5)

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # 无色

for NODE in "${NODES[@]}"; do
    echo -e "\n🔍 正在检查 ${NODE} ..."

    # 检查 kubelet 配置是否指向 /mydata
    KUBELET_ROOT=$(ssh "$NODE" "grep -- '--root-dir=' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf 2>/dev/null")

    # 检查 containerd 配置是否指向 /mydata
    CONTAINERD_ROOT=$(ssh "$NODE" "grep 'root =' /etc/containerd/config.toml | grep '/mydata' 2>/dev/null")
    CONTAINERD_STATE=$(ssh "$NODE" "grep 'state =' /etc/containerd/config.toml | grep '/mydata' 2>/dev/null")

    # 检查两个目录是否非空
    KUBELET_DIR=$(ssh "$NODE" "sudo du -sh /mydata/kubelet 2>/dev/null | cut -f1")
    CONTAINERD_DIR=$(ssh "$NODE" "sudo du -sh /mydata/containerd 2>/dev/null | cut -f1")

    # 检查服务状态
    KUBELET_STATUS=$(ssh "$NODE" "systemctl is-active kubelet 2>/dev/null")
    CONTAINERD_STATUS=$(ssh "$NODE" "systemctl is-active containerd 2>/dev/null")

    # 结果判断与输出
    if [[ $KUBELET_ROOT == *"/mydata/kubelet"* && $CONTAINERD_ROOT == *"/mydata/containerd/root"* && $CONTAINERD_STATE == *"/mydata/containerd/state"* && $KUBELET_STATUS == "active" && $CONTAINERD_STATUS == "active" ]]; then
        echo -e "${GREEN}✅ 配置正确，服务运行中${NC}"
        echo -e "📦 /mydata/kubelet 占用: ${KUBELET_DIR}"
        echo -e "📦 /mydata/containerd 占用: ${CONTAINERD_DIR}"
    else
        echo -e "${RED}❌ 检查失败："
        [[ ! $KUBELET_ROOT =~ /mydata ]] && echo -e "${RED}  - kubelet 配置未迁移${NC}"
        [[ ! $CONTAINERD_ROOT =~ /mydata ]] && echo -e "${RED}  - containerd root 配置未迁移${NC}"
        [[ ! $CONTAINERD_STATE =~ /mydata ]] && echo -e "${RED}  - containerd state 配置未迁移${NC}"
        [[ $KUBELET_STATUS != "active" ]] && echo -e "${RED}  - kubelet 未运行${NC}"
        [[ $CONTAINERD_STATUS != "active" ]] && echo -e "${RED}  - containerd 未运行${NC}"
    fi
done
