@echo off
chcp 65001 >nul
setlocal

:: Joe AI Writer - Docker 生产环境一键部署
:: 双击运行或在项目根目录执行: install.bat

cd /d "%~dp0"
title Joe AI Writer - Docker 部署

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\deploy.ps1"
if errorlevel 1 (
    echo.
    echo 部署失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
pause
