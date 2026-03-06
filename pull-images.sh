#!/bin/bash
# ============================================
# Docker 镜像拉取重试脚本
# ============================================

echo "==========================================="
echo "  Docker 镜像手动拉取"
echo "==========================================="
echo ""

# 使用国内镜像源拉取
pull_with_mirror() {
    local image=$1
    echo "正在拉取: $image"
    
    # 尝试多个镜像源
    docker pull $image || \
    docker pull docker.mirrors.ustc.edu.cn/$image || \
    docker pull hub-mirror.c.163.com/$image || \
    docker pull mirror.baidubce.com/$image
    
    if [ $? -eq 0 ]; then
        echo "✓ 拉取成功: $image"
    else
        echo "✗ 拉取失败: $image"
        return 1
    fi
}

echo "步骤 1: 拉取 Python 镜像"
pull_with_mirror "python:3.11-slim"

echo ""
echo "步骤 2: 拉取 Node 镜像"
pull_with_mirror "node:20-alpine"

echo ""
echo "步骤 3: 拉取 MySQL 镜像"
pull_with_mirror "mysql:8.0"

echo ""
echo "==========================================="
if [ $? -eq 0 ]; then
    echo "✓ 所有镜像拉取完成"
    echo "现在可以运行: docker-compose up -d"
else
    echo "✗ 部分镜像拉取失败，请检查网络"
fi
echo "==========================================="
