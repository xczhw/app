#!/bin/bash

set -e

# 设置安装目录
INSTALL_DIR="/opt/miniconda3"
ENV_PROFILE="/etc/profile.d/conda.sh"
CONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
INSTALLER="/tmp/Miniconda3-latest-Linux-x86_64.sh"

# 需要 root 权限
if [[ $EUID -ne 0 ]]; then
    echo "❌ 请以 root 身份运行这个脚本（sudo bash install_miniconda.sh）"
    exit 1
fi

echo "🚀 正在下载安装脚本..."
wget -O "$INSTALLER" "$CONDA_URL"

echo "📦 安装到 $INSTALL_DIR..."
bash "$INSTALLER" -b -p "$INSTALL_DIR"

echo "🔧 设置环境变量..."
echo "export PATH=\"$INSTALL_DIR/bin:\$PATH\"" > "$ENV_PROFILE"
chmod +x "$ENV_PROFILE"

# 激活 base 环境（可选）
source "$ENV_PROFILE"
$INSTALL_DIR/bin/conda init

echo "✅ Miniconda 安装完成！路径：$INSTALL_DIR"
echo "✅ 环境变量已写入：$ENV_PROFILE"

# 创建一个 Python 3.10 的共享环境（可选）
echo "创建系统级 Python 3.10 环境？ "

mkdir -p /opt/conda-envs
$INSTALL_DIR/bin/conda create -y -p /opt/conda-envs/py310 python=3.10
echo "✅ Python 3.10 环境创建成功！路径：/opt/conda-envs/py310"
conda activate /opt/conda-envs/py310


echo "📎 使用方法（重启终端或运行）："
echo "    source $ENV_PROFILE"
echo "    conda activate /opt/conda-envs/py310"
