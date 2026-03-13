@echo off
chcp 65001
echo =========================================
echo   墨心 AI 写作工具 - 更新脚本
echo =========================================
echo.

cd /d D:\projects\joe-ai-writer

echo [1/4] 备份数据...
if not exist backups mkdir backups
set BACKUP_FILE=backups\backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.sql
docker exec joe-writer-mysql-prod mysqldump -u root -p${MYSQL_ROOT_PASSWORD} joe_writer > %BACKUP_FILE% 2> nul
echo ✅ 数据库备份完成: %BACKUP_FILE%
echo.

echo [2/4] 拉取新镜像...
docker-compose -f docker-compose.prod.yml pull
echo.

echo [3/4] 重新构建镜像（如果需要）...
echo 是否重新构建本地镜像?
echo 1. 是（重新构建）
echo 2. 否（使用已拉取的镜像）
set /p REBUILD="请选择 (1-2): "
if "%REBUILD%"=="1" (
    docker-compose -f docker-compose.prod.yml build --no-cache
)
echo.

echo [4/4] 重启服务...
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

echo.
echo =========================================
echo   更新完成！
echo =========================================
echo.
docker-compose -f docker-compose.prod.yml ps
pause
