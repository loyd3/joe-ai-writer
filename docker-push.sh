#!/bin/bash
# ============================================
# Joe AI Writer - 一键构建并推送 Docker 镜像
# 用法: ./docker-push.sh [版本号]
# 示例: ./docker-push.sh 1.0.1
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
DOCKER_USER="loyd3"
BACKEND_IMAGE="${DOCKER_USER}/joe-ai-writer-backend"
FRONTEND_IMAGE="${DOCKER_USER}/joe-ai-writer-frontend"

# 获取版本号
VERSION=${1:-latest}
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Joe AI Writer - Docker 推送脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "版本: ${YELLOW}${VERSION}${NC}"
echo ""

# 检查 docker 登录状态
echo -e "${BLUE}▶ 检查 Docker 登录状态...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker 未运行或未登录${NC}"
    echo "请先运行: docker login"
    exit 1
fi

# 检查是否登录到 Docker Hub
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo -e "${RED}✗ 未登录到 Docker Hub${NC}"
    echo "请先运行: docker login"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已登录${NC}"
echo ""

# 构建镜像
echo -e "${BLUE}▶ 构建后端镜像...${NC}"
docker build -t ${BACKEND_IMAGE}:${VERSION} -t ${BACKEND_IMAGE}:latest ./backend

echo ""
echo -e "${BLUE}▶ 构建前端镜像...${NC}"
docker build -t ${FRONTEND_IMAGE}:${VERSION} -t ${FRONTEND_IMAGE}:latest ./frontend

echo ""
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 推送镜像到 Docker Hub
echo -e "${BLUE}▶ 推送后端镜像到 Docker Hub...${NC}"
docker push ${BACKEND_IMAGE}:${VERSION}
docker push ${BACKEND_IMAGE}:latest

echo ""
echo -e "${BLUE}▶ 推送前端镜像到 Docker Hub...${NC}"
docker push ${FRONTEND_IMAGE}:${VERSION}
docker push ${FRONTEND_IMAGE}:latest

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ 推送完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "镜像地址:"
echo -e "  ${YELLOW}${BACKEND_IMAGE}:${VERSION}${NC}"
echo -e "  ${YELLOW}${FRONTEND_IMAGE}:${VERSION}${NC}"
echo ""
echo -e "拉取命令:"
echo -e "  ${BLUE}docker pull ${BACKEND_IMAGE}:${VERSION}${NC}"
echo -e "  ${BLUE}docker pull ${FRONTEND_IMAGE}:${VERSION}${NC}"
echo ""
