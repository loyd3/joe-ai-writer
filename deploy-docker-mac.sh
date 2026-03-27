#!/bin/bash
# ============================================
# Joe AI Writer - macOS 本地 Docker 部署（Docker Desktop）
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ "$(uname -s)" != "Darwin" ]; then
  echo -e "${YELLOW}提示: 本脚本面向 macOS；当前系统为 $(uname -s)，仍可使用下方 compose 文件手动执行。${NC}"
fi

compose_bin() {
  if docker compose version &>/dev/null; then
    echo "docker compose"
  elif command -v docker-compose &>/dev/null; then
    echo "docker-compose"
  else
    echo ""
  fi
}

DC=$(compose_bin)
if [ -z "$DC" ]; then
  echo -e "${RED}错误: 未找到「docker compose」或 docker-compose${NC}"
  echo "请安装 Docker Desktop for Mac: https://docs.docker.com/desktop/install/mac-install/"
  exit 1
fi

FILE_FULL="docker-compose.mac.yml"
FILE_LOCAL_DB="docker-compose.mac.local-db.yml"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}  Joe AI Writer - macOS 本地 Docker${NC}"
echo -e "${BLUE}  使用: ${DC} -f ${FILE_FULL}${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

if ! command -v docker &>/dev/null; then
  echo -e "${RED}错误: 未安装 docker${NC}"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo -e "${RED}错误: Docker 守护进程未运行，请先启动 Docker Desktop${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Docker 可用${NC}"

if [ ! -f .env ]; then
  echo -e "${YELLOW}未找到 .env，从 .env.docker.mac 复制...${NC}"
  cp .env.docker.mac .env
  echo -e "${YELLOW}请编辑 .env（至少配置 DEEPSEEK_API_KEY 等）${NC}"
  echo ""
fi

echo -e "${BLUE}请选择:${NC}"
echo "  1) 完整部署（MySQL 容器 + 后端 + 前端）"
echo "  2) 后端 + 前端（使用 Mac 本机 MySQL，需配置 LOCAL_MYSQL_*）"
echo "  3) 停止完整栈（${FILE_FULL}）"
echo "  4) 停止本机 MySQL 栈（${FILE_LOCAL_DB}）"
echo "  5) 查看完整栈日志"
echo "  6) 重新构建并启动完整栈"
echo ""
read -p "请输入 (1-6): " choice

case $choice in
  1)
    echo -e "${BLUE}启动完整栈...${NC}"
    $DC -f "$FILE_FULL" up -d --build
    echo ""
    echo -e "${GREEN}前端 http://localhost:8080  |  API http://localhost:9000  |  文档 http://localhost:9000/docs${NC}"
    $DC -f "$FILE_FULL" ps
    ;;
  2)
    echo -e "${BLUE}启动（连接本机 MySQL）...${NC}"
    echo -e "${YELLOW}确认 .env 中 LOCAL_MYSQL_USER / LOCAL_MYSQL_PASSWORD / LOCAL_MYSQL_DATABASE 已正确${NC}"
    $DC -f "$FILE_LOCAL_DB" --env-file .env up -d --build
    echo -e "${GREEN}前端 http://localhost:8080  |  API http://localhost:9000${NC}"
    $DC -f "$FILE_LOCAL_DB" ps
    ;;
  3)
    $DC -f "$FILE_FULL" down
    echo -e "${GREEN}✓ 已停止${NC}"
    ;;
  4)
    $DC -f "$FILE_LOCAL_DB" down 2>/dev/null || true
    echo -e "${GREEN}✓ 已停止（若曾用该文件启动）${NC}"
    ;;
  5)
    $DC -f "$FILE_FULL" logs -f
    ;;
  6)
    $DC -f "$FILE_FULL" down
    $DC -f "$FILE_FULL" up -d --build
    echo -e "${GREEN}✓ 重建完成${NC}"
    ;;
  *)
    echo -e "${RED}无效选项${NC}"
    exit 1
    ;;
esac

echo ""
echo -e "${YELLOW}常用:${NC} ${DC} -f ${FILE_FULL} logs -f  |  ${DC} -f ${FILE_FULL} ps  |  ${DC} -f ${FILE_FULL} down"
echo ""
