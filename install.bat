@echo off
chcp 65001
echo =========================================
echo   墨心 AI 写作工具 - 一键部署脚本
echo =========================================
echo.

REM 检查 Docker
echo [1/5] 检查 Docker 环境...
docker --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    echo    下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker 已安装
echo.

REM 检查 docker-compose
docker-compose --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装
    pause
    exit /b 1
)
echo ✅ Docker Compose 已安装
echo.

cd /d D:\projects\joe-ai-writer

REM 检查配置文件
if not exist .env.prod (
    echo [2/5] 创建环境配置文件...
    copy .env.prod.example .env.prod
    echo ⚠️  请编辑 .env.prod 文件，修改密码和配置
    notepad .env.prod
    echo.
    echo 配置完成后按任意键继续...
    pause > nul
) else (
    echo [2/5] 环境配置文件已存在
echo.
)

echo [3/5] 拉取/构建镜像...
echo.
echo 请选择部署方式:
echo 1. 使用本地构建的镜像（运行 deploy-docker.bat 后）
echo 2. 从 Docker Hub 拉取镜像
echo 3. 从 tar 文件加载镜像
echo.
set /p DEPLOY_TYPE="请选择 (1-3): "

if "%DEPLOY_TYPE%"=="2" (
    echo.
    set /p IMAGE_PREFIX="输入 Docker Hub 用户名: "
    docker pull %IMAGE_PREFIX%/joe-ai-writer-backend:latest
    docker pull %IMAGE_PREFIX%/joe-ai-writer-frontend:latest
    
    REM 更新 docker-compose.prod.yml 中的镜像地址
    powershell -Command "(Get-Content docker-compose.prod.yml) -replace 'your-dockerhub-username', '%IMAGE_PREFIX%' | Set-Content docker-compose.prod.yml"
)

if "%DEPLOY_TYPE%"=="3" (
    echo.
    if exist joe-ai-writer-backend-latest.tar (
        docker load -i joe-ai-writer-backend-latest.tar
        docker load -i joe-ai-writer-frontend-latest.tar
        echo ✅ 镜像加载完成
    ) else (
        echo ❌ 未找到镜像文件，请先运行 deploy-docker.bat 导出镜像
        pause
        exit /b 1
    )
)

echo.
echo [4/5] 启动服务...
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

if errorlevel 1 (
    echo.
    echo ❌ 启动失败，请检查日志:
    echo    docker-compose -f docker-compose.prod.yml logs
    pause
    exit /b 1
)

echo.
echo [5/5] 检查服务状态...
timeout /t 5 /nobreak > nul
docker-compose -f docker-compose.prod.yml ps

echo.
echo =========================================
echo   部署完成！
echo =========================================
echo.
echo 访问地址:
echo   前端: http://localhost:8080
echo   后端: http://localhost:9000
echo   API文档: http://localhost:9000/docs
echo.
echo 常用命令:
echo   查看日志: docker-compose -f docker-compose.prod.yml logs -f
echo   停止服务: docker-compose -f docker-compose.prod.yml down
echo   重启服务: docker-compose -f docker-compose.prod.yml restart
echo.
pause
