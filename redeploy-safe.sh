#!/bin/bash
# ============================================
# Docker 重新部署脚本 - 安全版（保留数据）
# ============================================

echo "==========================================="
echo "  Joe AI Writer - 安全重新部署"
echo "==========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}步骤 1/4: 检查现有数据...${NC}"

# 检查 MySQL 数据卷是否存在
if docker volume ls | grep -q "joe-ai-writer_mysql_data"; then
    echo -e "${GREEN}✓ 发现数据卷: joe-ai-writer_mysql_data${NC}"
    
    # 尝试获取数据库大小
    docker run --rm -v joe-ai-writer_mysql_data:/data alpine du -sh /data 2>/dev/null || echo "  数据卷存在"
else
    echo "  未找到现有数据卷（可能是首次部署）"
fi

echo ""
echo -e "${YELLOW}步骤 2/4: 停止现有服务...${NC}"
docker-compose down
echo -e "${GREEN}✓ 服务已停止${NC}"

echo ""
echo -e "${YELLOW}步骤 3/4: 重新构建并启动...${NC}"
docker-compose up -d --build
echo -e "${GREEN}✓ 服务已启动${NC}"

echo ""
echo -e "${YELLOW}步骤 4/4: 验证数据...${NC}"
sleep 3  # 等待 MySQL 启动

# 检查数据库连接
if docker exec joe-writer-mysql mysql -ujoewriter -pjoewriter123 -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='joe_writer';" 2>/dev/null; then
    TABLE_COUNT=$(docker exec joe-writer-mysql mysql -ujoewriter -pjoewriter123 -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='joe_writer';" 2>/dev/null | tail -1)
    echo -e "${GREEN}✓ 数据库正常，表数量: $TABLE_COUNT${NC}"
else
    echo "  等待数据库初始化..."
fi

echo ""
echo "==========================================="
echo -e "${GREEN}  重新部署完成！${NC}"
echo "==========================================="
echo ""
echo "访问地址:"
echo "  - 前端: http://localhost:5173"
echo "  - 后端: http://localhost:8000"
echo ""
echo "服务状态:"
docker-compose ps
