#!/bin/bash
# ============================================
# Joe AI Writer - Docker 本地部署脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}  Joe AI Writer - Docker 部署${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ 未找到 .env 文件${NC}"
    echo -e "${YELLOW}正在从 .env.docker 复制...${NC}"
    cp .env.docker .env
    echo -e "${YELLOW}请编辑 .env 文件配置你的 AI API Key${NC}"
    echo ""
fi

echo ""
echo -e "${BLUE}请选择部署方式:${NC}"
echo "  1) 完整部署 (MySQL + 后端 + 前端) - 推荐"
echo "  2) 仅部署后端和前端 (使用本地 MySQL)"
echo "  3) 停止所有服务"
echo "  4) 查看日志"
echo "  5) 重新构建并启动"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo -e "${BLUE}开始完整部署...${NC}"
        echo -e "${YELLOW}首次构建可能需要几分钟...${NC}"
        docker-compose up -d --build
        echo ""
        echo -e "${GREEN}===========================================${NC}"
        echo -e "${GREEN}  部署成功!${NC}"
        echo -e "${GREEN}===========================================${NC}"
        echo ""
        echo "Docker 访问地址:"
        echo "  - 前端: http://localhost:8080"
        echo "  - 后端 API: http://localhost:9000"
        echo "  - API 文档: http://localhost:9000/docs"
        echo ""
        echo "端口说明:"
        echo "  - Docker 前端使用 8080（本地开发用 5173）"
        echo "  - Docker 后端使用 9000（本地开发用 8000）"
        echo "  - 可同时运行两种环境，互不干扰"
        echo ""
        echo "服务状态:"
        docker-compose ps
        ;;
    2)
        echo -e "${BLUE}使用本地 MySQL 部署...${NC}"
        echo -e "${YELLOW}请确保本地 MySQL 已启动${NC}"
        docker-compose -f docker-compose.local-db.yml up -d --build
        echo ""
        echo -e "${GREEN}===========================================${NC}"
        echo -e "${GREEN}  部署成功!${NC}"
        echo -e "${GREEN}===========================================${NC}"
        echo ""
        echo "Docker 访问地址:"
        echo "  - 前端: http://localhost:8080"
        echo "  - 后端 API: http://localhost:9000"
        ;;
    3)
        echo -e "${BLUE}停止所有服务...${NC}"
        docker-compose down
        docker-compose -f docker-compose.local-db.yml down 2>/dev/null || true
        echo -e "${GREEN}✓ 服务已停止${NC}"
        ;;
    4)
        echo -e "${BLUE}查看日志 (按 Ctrl+C 退出)...${NC}"
        docker-compose logs -f
        ;;
    5)
        echo -e "${BLUE}重新构建并启动...${NC}"
        docker-compose down
        docker-compose up -d --build
        echo -e "${GREEN}✓ 重新构建完成${NC}"
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo "  - 端口说明: 详见 PORTS.md"
echo ""
