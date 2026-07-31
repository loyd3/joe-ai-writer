@echo off
chcp 65001 >nul
setlocal

:: 墨心 AI 写作 - Docker 一键部署（MySQL + 后端 + 前端）
:: 用法: deploy.bat [up|down|logs|restart|status]

cd /d "%~dp0"
title 墨心 - Docker 部署

set ACTION=%~1
if "%ACTION%"=="" set ACTION=up

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

if /i "%ACTION%"=="up" goto :up
if /i "%ACTION%"=="down" goto :down
if /i "%ACTION%"=="logs" goto :logs
if /i "%ACTION%"=="restart" goto :restart
if /i "%ACTION%"=="status" goto :status
echo 未知命令: %ACTION%
echo 用法: deploy.bat [up^|down^|logs^|restart^|status]
exit /b 1

:up
echo.
echo ========================================
echo   启动 Docker 服务 (MySQL + 后端 + 前端)
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
echo   数据库: Docker 内 MySQL (容器名 joe-writer-mysql)
echo   连接串: mysql://joewriter:***@mysql:3306/joe_writer
echo.
docker compose ps
goto :end

:down
echo 停止所有服务...
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
goto :end

:end
echo.
pause
