@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================
:: Joe AI Writer - Docker 发布脚本 (Windows)
:: 用法: 直接双击运行或在 PowerShell 中执行
:: ============================================

title Joe AI Writer - Docker 发布

:: 颜色定义
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RED=[91m"
set "NC=[0m"

echo %BLUE%=========================================%NC%
echo %BLUE%  Joe AI Writer - Docker 发布脚本%NC%
echo %BLUE%=========================================%NC%
echo.

:: 切换到项目目录
cd /d "D:\projects\joe-ai-writer"
if errorlevel 1 (
    echo %RED%错误: 无法切换到项目目录%NC%
    pause
    exit /b 1
)

:: 检查 Docker 是否运行
echo %BLUE%▶ 检查 Docker 状态...%NC%
docker info >nul 2>&1
if errorlevel 1 (
    echo %RED%✗ Docker 未运行，请先启动 Docker Desktop%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Docker 运行正常%NC%
echo.

:: 配置 - 使用 loyd3 作为默认用户名
set "DOCKER_USER=loyd3"
set "BACKEND_IMAGE=%DOCKER_USER%/joe-ai-writer-backend"
set "FRONTEND_IMAGE=%DOCKER_USER%/joe-ai-writer-frontend"

:: 获取版本号
set /p VERSION="输入版本号 (默认 latest): "
if "!VERSION!"=="" set "VERSION=latest"
echo %YELLOW%版本: %VERSION%%NC%
echo.

:: 步骤 1: 构建后端镜像
echo %BLUE%[1/4] 构建后端镜像...%NC%
docker build -t %BACKEND_IMAGE%:%VERSION% -t %BACKEND_IMAGE%:latest ./backend
if errorlevel 1 (
    echo %RED%✗ 后端镜像构建失败%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ 后端镜像构建完成%NC%
echo   - %BACKEND_IMAGE%:%VERSION%
echo   - %BACKEND_IMAGE%:latest
echo.

:: 步骤 2: 构建前端镜像
echo %BLUE%[2/4] 构建前端镜像...%NC%
docker build -t %FRONTEND_IMAGE%:%VERSION% -t %FRONTEND_IMAGE%:latest ./frontend
if errorlevel 1 (
    echo %RED%✗ 前端镜像构建失败%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ 前端镜像构建完成%NC%
echo   - %FRONTEND_IMAGE%:%VERSION%
echo   - %FRONTEND_IMAGE%:latest
echo.

:: 步骤 3: 显示镜像信息
echo %BLUE%[3/4] 镜像信息:%NC%
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | findstr "joe-ai-writer"
echo.

:: 步骤 4: 推送选项
echo %BLUE%[4/4] 推送选项:%NC%
echo.
echo 1. 推送到 Docker Hub (需要登录: docker login)
echo 2. 推送到阿里云容器镜像服务 (ACR)
echo 3. 仅保存为本地 tar 文件
echo 4. 跳过推送 (仅构建)
echo.
set /p PUSH_OPTION="请选择 (1-4): "

if "!PUSH_OPTION!"=="1" (
    echo.
    echo %BLUE%▶ 推送到 Docker Hub...%NC%
    
    :: 检查是否已登录
    docker info 2>nul | findstr "Username" >nul
    if errorlevel 1 (
        echo %YELLOW%未检测到 Docker Hub 登录，尝试登录...%NC%
        docker login
        if errorlevel 1 (
            echo %RED%✗ Docker 登录失败%NC%
            pause
            exit /b 1
        )
    )
    
    echo %BLUE%推送后端镜像...%NC%
    docker push %BACKEND_IMAGE%:%VERSION%
    docker push %BACKEND_IMAGE%:latest
    
    echo %BLUE%推送前端镜像...%NC%
    docker push %FRONTEND_IMAGE%:%VERSION%
    docker push %FRONTEND_IMAGE%:latest
    
    echo %GREEN%✓ 推送完成%NC%
)

if "!PUSH_OPTION!"=="2" (
    echo.
    set /p REGISTRY="输入阿里云仓库地址 (如: registry.cn-hangzhou.aliyuncs.com/your-namespace): "
    
    echo %BLUE%▶ 推送到阿里云...%NC%
    
    :: 登录阿里云
    echo %YELLOW%请先登录阿里云仓库...%NC%
    docker login !REGISTRY!
    if errorlevel 1 (
        echo %RED%✗ 登录失败%NC%
        pause
        exit /b 1
    )
    
    :: 重新标记镜像
    docker tag %BACKEND_IMAGE%:%VERSION% !REGISTRY!/joe-ai-writer-backend:%VERSION%
    docker tag %FRONTEND_IMAGE%:%VERSION% !REGISTRY!/joe-ai-writer-frontend:%VERSION%
    
    :: 推送
    docker push !REGISTRY!/joe-ai-writer-backend:%VERSION%
    docker push !REGISTRY!/joe-ai-writer-frontend:%VERSION%
    
    echo %GREEN%✓ 推送完成%NC%
)

if "!PUSH_OPTION!"=="3" (
    echo.
    echo %BLUE%▶ 保存镜像到本地文件...%NC%
    
    set "EXPORT_DIR=./docker-images"
    if not exist !EXPORT_DIR! mkdir !EXPORT_DIR!
    
    echo %BLUE%导出后端镜像...%NC%
    docker save -o !EXPORT_DIR!/joe-ai-writer-backend-%VERSION%.tar %BACKEND_IMAGE%:%VERSION%
    
    echo %BLUE%导出前端镜像...%NC%
    docker save -o !EXPORT_DIR!/joe-ai-writer-frontend-%VERSION%.tar %FRONTEND_IMAGE%:%VERSION%
    
    echo %GREEN%✓ 镜像已导出到 %EXPORT_DIR% 目录%NC%
    dir !EXPORT_DIR! /b
)

:: 完成
echo.
echo %GREEN%=========================================%NC%
echo %GREEN%  发布完成！%NC%
echo %GREEN%=========================================%NC%
echo.
echo %YELLOW%镜像信息:%NC%
echo   后端: %BACKEND_IMAGE%:%VERSION%
echo   前端: %FRONTEND_IMAGE%:%VERSION%
echo.
echo %BLUE%使用说明:%NC%
echo   1. 拉取镜像: docker pull %BACKEND_IMAGE%:%VERSION%
echo   2. 运行部署: docker-compose -f docker-compose.prod.yml up -d
echo.
echo %YELLOW%按任意键退出...%NC%
pause >nul
