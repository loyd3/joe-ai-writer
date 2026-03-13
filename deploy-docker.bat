@echo off
chcp 65001
echo =========================================
echo   墨心 AI 写作工具 - Docker 发布脚本
echo =========================================
echo.

REM 配置项（按需修改）
set IMAGE_PREFIX=your-dockerhub-username
echo 镜像前缀: %IMAGE_PREFIX%
echo.

REM 版本号
set /p VERSION="输入版本号 (默认 latest): "
if "%VERSION%"=="" set VERSION=latest
echo 版本: %VERSION%
echo.

echo [1/5] 停止现有容器...
cd /d D:\projects\joe-ai-writer
docker-compose -f docker-compose-lite.yml down
echo.

echo [2/5] 构建后端镜像...
docker build -f backend\Dockerfile.lite -t %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION% .
docker tag %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION% %IMAGE_PREFIX%/joe-ai-writer-backend:latest
echo ✅ 后端镜像构建完成
echo.

echo [3/5] 构建前端镜像...
docker build -f frontend\Dockerfile -t %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION% .
docker tag %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION% %IMAGE_PREFIX%/joe-ai-writer-frontend:latest
echo ✅ 前端镜像构建完成
echo.

echo [4/5] 导出镜像到本地文件（可选）...
echo 正在导出镜像...
docker save %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION% > joe-ai-writer-backend-%VERSION%.tar
docker save %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION% > joe-ai-writer-frontend-%VERSION%.tar
echo ✅ 镜像已导出到:
echo    - joe-ai-writer-backend-%VERSION%.tar
echo    - joe-ai-writer-frontend-%VERSION%.tar
echo.

echo [5/5] 发布选项:
echo.
echo 1. 推送到 Docker Hub
echo 2. 推送到阿里云容器仓库
echo 3. 保存为本地文件（已完成）
echo 4. 跳过推送
echo.
set /p PUSH_OPTION="请选择 (1-4): "

if "%PUSH_OPTION%"=="1" (
    echo.
    echo 推送到 Docker Hub...
    docker push %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION%
    docker push %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION%
    docker push %IMAGE_PREFIX%/joe-ai-writer-backend:latest
    docker push %IMAGE_PREFIX%/joe-ai-writer-frontend:latest
    echo ✅ 推送完成
)

if "%PUSH_OPTION%"=="2" (
    echo.
    set /p REGISTRY="输入阿里云仓库地址 (如: registry.cn-hangzhou.aliyuncs.com/your-namespace): "
    echo 推送到阿里云...
    docker tag %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION% %REGISTRY%/joe-ai-writer-backend:%VERSION%
    docker tag %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION% %REGISTRY%/joe-ai-writer-frontend:%VERSION%
    docker push %REGISTRY%/joe-ai-writer-backend:%VERSION%
    docker push %REGISTRY%/joe-ai-writer-frontend:%VERSION%
    echo ✅ 推送完成
)

echo.
echo =========================================
echo   发布完成！
echo =========================================
echo.
echo 镜像信息:
echo   后端: %IMAGE_PREFIX%/joe-ai-writer-backend:%VERSION%
echo   前端: %IMAGE_PREFIX%/joe-ai-writer-frontend:%VERSION%
echo.
echo 部署命令:
echo   docker-compose -f docker-compose.prod.yml up -d
echo.
pause
