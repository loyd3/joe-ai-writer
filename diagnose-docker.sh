#!/bin/bash
# ============================================
# Docker 部署诊断脚本
# ============================================

echo "==========================================="
echo "  Docker 部署诊断"
echo "==========================================="
echo ""

# 检查容器状态
echo "1. 检查容器状态..."
docker-compose ps
echo ""

# 检查后端健康
echo "2. 检查后端服务..."
if curl -s http://localhost:9000/health > /dev/null; then
    echo "✓ 后端正常: http://localhost:9000"
else
    echo "✗ 后端无法访问"
fi
echo ""

# 检查前端
echo "3. 检查前端服务..."
if curl -s http://localhost:8080 > /dev/null; then
    echo "✓ 前端正常: http://localhost:8080"
else
    echo "✗ 前端无法访问"
fi
echo ""

# 检查日志
echo "4. 后端日志（最近10行）..."
docker-compose logs --tail=10 backend
echo ""

echo "5. 前端日志（最近10行）..."
docker-compose logs --tail=10 frontend
echo ""

echo "==========================================="
echo "  诊断完成"
echo "==========================================="
echo ""
echo "常见问题解决方案:"
echo ""
echo "1. 如果前端显示'无法连接到后端服务':"
echo "   重启前端容器: docker-compose restart frontend"
echo ""
echo "2. 如果后端启动失败:"
echo "   查看完整日志: docker-compose logs backend"
echo ""
echo "3. 重置所有服务:"
echo "   docker-compose down && docker-compose up -d"
echo ""
