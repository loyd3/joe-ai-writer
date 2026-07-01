@echo off
chcp 65001 >nul
setlocal

:: Joe AI Writer - Docker 镜像构建与发布
:: 双击运行或在项目根目录执行: deploy-docker.bat

cd /d "%~dp0"
title Joe AI Writer - Docker 发布

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\docker-push.ps1" -Interactive
if errorlevel 1 (
    echo.
    echo 发布失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
pause
