#!/usr/bin/env bash
# 墨心 AI 写作 - Docker 一键部署（MySQL + 后端 + 前端）
# 用法: ./deploy.sh [up|down|logs|restart|status]

set -e
cd "$(dirname "$0")"
ACTION="${1:-up}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 Docker"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[错误] Docker 未运行"
  exit 1
fi

if [ ! -f .env ]; then
  echo "[提示] 未找到 .env，从 .env.docker 复制..."
  cp .env.docker .env
  echo "[提示] 请编辑 .env 配置 AI API Key 后重新运行"
fi

case "$ACTION" in
  up)
    echo "启动 Docker 服务 (MySQL + 后端 + 前端)..."
    docker compose up -d --build
    echo ""
    echo "前端:     http://localhost:8080"
    echo "后端 API: http://localhost:9000"
    echo "API 文档: http://localhost:9000/docs"
    docker compose ps
    ;;
  down) docker compose down ;;
  logs) docker compose logs -f ;;
  restart) docker compose restart; docker compose ps ;;
  status) docker compose ps ;;
  *)
    echo "用法: ./deploy.sh [up|down|logs|restart|status]"
    exit 1
    ;;
esac
