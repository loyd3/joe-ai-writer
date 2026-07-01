@echo off
chcp 65001 >nul
setlocal

:: Joe AI Writer - Docker 环境诊断

cd /d "%~dp0"
title Joe AI Writer - 环境诊断

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\diagnose.ps1"
pause
