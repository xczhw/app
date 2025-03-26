#!/bin/bash

# 要设置的 Git 用户信息
GIT_USER_NAME="xczhw"
GIT_USER_EMAIL="xczhw@outlook.com"

# 目标路径数组
DIRS=(
  "/mydata/app"
  "/mydata/app/whoami"
  "/mydata/app/social-network-lb"
  "/mydata/app/DeathStarBench"
  "/mydata/app/microservice-demo"
  "/mydata/istio/istio"
)

# 循环进入每个目录并设置 Git 配置
for dir in "${DIRS[@]}"; do
  if [ -d "$dir/.git" ]; then
    echo "Setting git config in $dir"
    git -C "$dir" config user.name "$GIT_USER_NAME"
    git -C "$dir" config user.email "$GIT_USER_EMAIL"
  else
    echo "Skipping $dir (not a git repo)"
  fi
done
