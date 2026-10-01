@echo off
chcp 65001 >nul
setlocal EnableExtensions

:: 墨心 AI 写作 - Docker 一键部署（MySQL + 后端 + 前端）
:: 持久化数据默认写到 F:\joe-ai-writer\docker-data，避免占 C 盘
:: 用法: deploy.bat [up|down|logs|restart|status|prune]

cd /d "%~dp0"
title 墨心 - Docker 部署

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=up"

:: 数据根目录（可用环境变量或 .env 覆盖）
if "%DOCKER_DATA_ROOT%"=="" set "DOCKER_DATA_ROOT=F:/joe-ai-writer/docker-data"

docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker，请先安装并启动 Docker Desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未运行，请启动 Docker Desktop
    pause
    exit /b 1
)

if not exist ".env" (
    echo [提示] 未找到 .env，从 .env.docker 复制...
    copy /Y ".env.docker" ".env" >nul
    echo [提示] 请编辑 .env 配置 DEEPSEEK_API_KEY 等 AI 密钥后重新运行
)

:: 确保 .env 里有 DOCKER_DATA_ROOT
findstr /B /C:"DOCKER_DATA_ROOT=" ".env" >nul 2>&1
if errorlevel 1 (
    echo.>> ".env"
    echo # Docker 持久化数据目录（F 盘，不占 C 盘）>> ".env"
    echo DOCKER_DATA_ROOT=F:/joe-ai-writer/docker-data>> ".env"
)

:: 在 F 盘创建数据目录
for %%D in (mysql search_index hf-cache backend-data) do (
    if not exist "F:\joe-ai-writer\docker-data\%%D" mkdir "F:\joe-ai-writer\docker-data\%%D" >nul 2>&1
)

:: 检查 Docker Desktop 数据盘是否在 F（junction）
if exist "%LOCALAPPDATA%\Docker\wsl\disk" (
    echo [信息] Docker Desktop 磁盘目录: %LOCALAPPDATA%\Docker\wsl\disk
    dir /AL "%LOCALAPPDATA%\Docker\wsl" 2>nul | findstr /I "disk" >nul
)

if /i "%ACTION%"=="up" goto :up
if /i "%ACTION%"=="down" goto :down
if /i "%ACTION%"=="logs" goto :logs
if /i "%ACTION%"=="restart" goto :restart
if /i "%ACTION%"=="status" goto :status
if /i "%ACTION%"=="prune" goto :prune
echo 未知命令: %ACTION%
echo 用法: deploy.bat [up^|down^|logs^|restart^|status^|prune]
exit /b 1

:up
echo.
echo ========================================
echo   启动 Docker 服务 (MySQL + 后端 + 前端)
echo   数据目录: %DOCKER_DATA_ROOT%
echo ========================================
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [错误] 启动失败，运行 deploy.bat logs 查看日志
    pause
    exit /b 1
)
echo.
echo ========================================
echo   部署成功
echo ========================================
echo   前端:     http://localhost:8080
echo   后端 API: http://localhost:9000
echo   API 文档: http://localhost:9000/docs
echo.
echo   MySQL 数据:  %DOCKER_DATA_ROOT%/mysql
echo   搜索索引:    %DOCKER_DATA_ROOT%/search_index
echo   模型缓存:    %DOCKER_DATA_ROOT%/hf-cache
echo.
docker compose ps
goto :end

:down
echo 停止所有服务（保留 F 盘数据）...
docker compose down
goto :end

:logs
docker compose logs -f
goto :end

:restart
docker compose restart
docker compose ps
goto :end

:status
docker compose ps
echo.
echo --- 磁盘占用 ---
docker system df
echo.
echo --- F 盘项目数据 ---
dir /s /-c "F:\joe-ai-writer\docker-data" 2>nul | findstr /I "个文件 个目录 File Dir"
goto :end

:prune
echo 清理未使用的镜像/构建缓存（不删 F 盘业务数据）...
docker builder prune -f
docker image prune -f
docker system df
goto :end

:end
echo.
pause
