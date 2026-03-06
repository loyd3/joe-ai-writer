#!/bin/bash
# ============================================
# Docker 镜像加速配置脚本
# ============================================

echo "配置 Docker 国内镜像源..."

# 创建 Docker 配置目录
mkdir -p ~/.docker

# 配置镜像加速
cat > ~/.docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://docker.m.daocloud.io"
  ],
  "exec-opts": ["native.cgroupdriver=cgroupfs"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  }
}
EOF

echo "✓ 镜像配置已写入 ~/.docker/daemon.json"
echo ""
echo "请执行以下命令重启 Docker:"
echo "  sudo systemctl restart docker     # Linux"
echo "  或"
echo "  打开 Docker Desktop -> Settings -> Docker Engine 粘贴配置"
echo ""
echo "配置内容:"
cat ~/.docker/daemon.json
