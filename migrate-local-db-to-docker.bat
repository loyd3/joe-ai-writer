@echo off
chcp 65001 >nul
setlocal EnableExtensions

:: 将本地 MySQL(aiwriter@3306) 迁移到 Docker MySQL(joe_writer@3307)
:: 数据落在 F:\joe-ai-writer\docker-data\mysql

cd /d "%~dp0"

set "MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 9.4\bin"
set "DUMP=F:\joe-ai-writer\docker-data\migration\aiwriter_dump.sql"
set "LOCAL_USER=root"
set "LOCAL_PWD=Lord2013"
set "LOCAL_DB=aiwriter"
set "DOCKER_ROOT_PWD=rootpassword"
set "DOCKER_DB=joe_writer"

if not exist "F:\joe-ai-writer\docker-data\migration" mkdir "F:\joe-ai-writer\docker-data\migration"

echo [1/4] 停止 backend / frontend ...
docker compose stop backend frontend

echo [2/4] 导出本地库 %LOCAL_DB% ...
set MYSQL_PWD=%LOCAL_PWD%
"%MYSQL_BIN%\mysqldump.exe" -u%LOCAL_USER% -hlocalhost -P3306 --protocol=TCP --single-transaction --routines --triggers --add-drop-table --default-character-set=utf8mb4 --set-gtid-purged=OFF --column-statistics=0 %LOCAL_DB% > "%DUMP%"
set MYSQL_PWD=

echo [3/4] 重建 Docker 库并导入 ...
docker exec joe-writer-mysql mysql -uroot -p%DOCKER_ROOT_PWD% -e "DROP DATABASE IF EXISTS %DOCKER_DB%; CREATE DATABASE %DOCKER_DB% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON %DOCKER_DB%.* TO 'joewriter'@'%%'; FLUSH PRIVILEGES;"
docker exec -i joe-writer-mysql mysql -uroot -p%DOCKER_ROOT_PWD% --default-character-set=utf8mb4 %DOCKER_DB% < "%DUMP%"
if errorlevel 1 (
  echo [错误] 导入失败
  pause
  exit /b 1
)

echo [4/4] 校验并重启服务 ...
docker exec joe-writer-mysql mysql -uroot -p%DOCKER_ROOT_PWD% -N %DOCKER_DB% -e "SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'projects', COUNT(*) FROM projects UNION ALL SELECT 'documents', COUNT(*) FROM documents;"
docker compose start backend frontend

echo.
echo 迁移完成。Dump: %DUMP%
echo Docker 前端 http://localhost:8080
pause
