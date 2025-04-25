#!/bin/bash

set -e  # 发生错误时终止脚本执行

CONTAINER_NAME="istio-proxy-builder"
if ! docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "启动 istio-proxy-builder 容器..."
    docker run --init --privileged --name $CONTAINER_NAME --hostname $CONTAINER_NAME \
        -v /var/run/docker.sock:/var/run/docker.sock:rw \
        -v /mydata/istio-testing/work:/work \
        -v /mydata/istio-testing/home/.cache:/home/.cache \
        -w /work \
        -d gcr.io/istio-testing/build-tools-proxy:release-1.22-latest-amd64 bash -c '/bin/sleep 300d'
else
    echo "容器 $CONTAINER_NAME 已经存在，跳过创建。"
fi

# 进入 istio-proxy-builder 容器并构建 envoy
echo "Building envoy inside istio-proxy-builder container..."
docker exec -it istio-proxy-builder bash -c "make build BAZEL_STARTUP_ARGS='' BAZEL_BUILD_ARGS='-s --override_repository=envoy=/work/envoy' BAZEL_TARGETS=':envoy'"

# 复制构建完成的 envoy 二进制文件到 /mydata/istio-testing
echo "Copying built envoy binary to /mydata/istio-testing..."
mkdir -p /mydata/istio/istio/out/
docker cp istio-proxy-builder:/work/bazel-bin/envoy /mydata/istio/istio/out/envoy

# 进入 Istio 目录并构建 Istio Docker 镜像
echo "Building Istio Docker image..."
cd /mydata/istio/istio
rm -f /mydata/istio/istio/out/istio_is_init
make docker.push TAGS=1.24-dev
mv /mydata/istio/istio/out/linux_amd64/istioctl /usr/local/bin/istioctl

# 安装 Istio
# echo "Installing Istio..."
istioctl install -f /mydata/app/runner/istio-operator.yaml -y
kubectl apply -f /mydata/app/runner/addons
# 启用链路追踪
kubectl apply -f /mydata/app/runner/telemetry.yaml

# 重新部署 whoami 服务
echo "Redeploying whoami service..."
kubectl delete -f /mydata/whoami || true  # 忽略不存在的错误
kubectl apply -f /mydata/whoami

echo "Deployment completed successfully!"
