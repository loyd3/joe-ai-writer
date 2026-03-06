#!/bin/bash
# ============================================
# MySQL 数据备份脚本
# ============================================

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mysql_backup_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

echo "正在备份 MySQL 数据..."

# 从 Docker 容器导出数据
docker exec joe-writer-mysql mysqldump -ujoewriter -pjoewriter123 joe_writer > $BACKUP_FILE

if [ $? -eq 0 ]; then
    echo "✅ 备份成功: $BACKUP_FILE"
    # 保留最近 10 个备份
    ls -t $BACKUP_DIR/mysql_backup_*.sql | tail -n +11 | xargs rm -f 2>/dev/null
    echo "📦 当前备份文件:"
    ls -lh $BACKUP_DIR/
else
    echo "❌ 备份失败"
    exit 1
fi
