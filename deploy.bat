@echo off
chcp 65001 >nul
title Joe AI Writer - Docker Deploy
color 0A

:: ============================================
:: Joe AI Writer - Windows Docker Deploy Script
:: ============================================

setlocal EnableDelayedExpansion

:: Set project path
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ============================================
echo.
echo      Joe AI Writer - Docker Deploy
echo.
echo ============================================
echo.

:: Check Docker installation
echo [1/6] Checking Docker environment...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not running!
    echo.
    echo Please install Docker Desktop:
    echo    https://www.docker.com/products/docker-desktop
    echo.
    echo Make sure Docker Desktop is running after installation.
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('docker --version') do echo [OK] Docker version: %%a

:: Check Docker Compose
echo.
echo [2/6] Checking Docker Compose...
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker-compose --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Docker Compose is not installed!
        pause
        exit /b 1
    ) else (
        set "COMPOSE_CMD=docker-compose"
    )
) else (
    set "COMPOSE_CMD=docker compose"
)
echo [OK] Docker Compose is available

:: Check .env file
echo.
echo [3/6] Checking environment configuration...
if not exist ".env" (
    echo [WARN] .env file not found
    
    if exist ".env.docker" (
        echo [INFO] Creating .env from .env.docker...
        copy /Y ".env.docker" ".env" >nul
        echo [OK] .env file created
        echo.
        echo [WARN] Please edit .env file to configure your AI API Key!
        echo    File location: %PROJECT_DIR%.env
        echo.
        echo Default configuration:
        echo    - MySQL root password: rootpassword
        echo    - Database user: joewriter / joewriter123
        echo    - AI Provider: DeepSeek
        echo.
        choice /C YN /M "Edit .env file now"
        if !errorlevel! equ 1 (
            notepad ".env"
        )
    ) else (
        echo [ERROR] .env.docker template file not found!
        pause
        exit /b 1
    )
) else (
    echo [OK] Environment configuration exists
)

:: Check API Key configuration
echo.
echo [4/6] Verifying API Key configuration...
set "API_KEY_CONFIGURED=false"
for /f "tokens=*" %%a in (.env) do (
    echo %%a | findstr /C:"DEEPSEEK_API_KEY=sk-" >nul && set "API_KEY_CONFIGURED=true"
    echo %%a | findstr /C:"OPENAI_API_KEY=sk-" >nul && set "API_KEY_CONFIGURED=true"
    echo %%a | findstr /C:"SILICONFLOW_API_KEY=sk-" >nul && set "API_KEY_CONFIGURED=true"
)

if "%API_KEY_CONFIGURED%"=="false" (
    echo [WARN] No valid AI API Key detected!
    echo.
    echo Please edit .env file and configure at least one API Key:
    echo    - DEEPSEEK_API_KEY (Recommended for Chinese writing)
    echo    - OPENAI_API_KEY
    echo    - SILICONFLOW_API_KEY
    echo    - CUSTOM_API_KEY
    echo.
    choice /C YN /M "Continue deployment (AI features will not work)"
    if !errorlevel! equ 2 (
        echo Deployment cancelled
        pause
        exit /b 0
    )
) else (
    echo [OK] API Key is configured
)

:: Stop old services if exist
echo.
echo [5/6] Cleaning up old containers...
%COMPOSE_CMD% down --remove-orphans 2>nul
echo [OK] Cleanup completed

:: Build and start services
echo.
echo [6/6] Building and starting services...
echo    This may take a few minutes, please wait...
echo.

%COMPOSE_CMD% up --build -d

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Deployment failed! Please check error messages above.
    pause
    exit /b 1
)

:: Wait for services to start
echo.
echo Waiting for services to start...
timeout /t 5 /nobreak >nul

:: Check service status
echo.
echo ============================================
echo.
echo      Deployment Successful!
echo.
echo ============================================
echo.
%COMPOSE_CMD% ps

echo.
echo ============================================
echo.
echo Access URLs:
echo    Frontend: http://localhost:8080
echo    Backend API: http://localhost:9000
echo.
echo Common Commands:
echo    View logs:  deploy.bat logs
echo    Stop:       deploy.bat stop
echo    Restart:    deploy.bat restart
echo    Status:     deploy.bat status
echo.
echo Configuration:
echo    %PROJECT_DIR%.env
echo.
echo ============================================
echo.

:: Handle additional commands
if "%~1"=="logs" goto :logs
if "%~1"=="stop" goto :stop
if "%~1"=="restart" goto :restart
if "%~1"=="status" goto :status
if "%~1"=="down" goto :stop
if "%~1"=="up" goto :done

choice /C YN /M "View real-time logs"
if !errorlevel! equ 1 goto :logs
goto :done

:logs
echo.
echo Showing logs (Press Ctrl+C to exit)...
%COMPOSE_CMD% logs -f
goto :done

:stop
echo.
echo Stopping services...
%COMPOSE_CMD% down
echo [OK] Services stopped
goto :done

:restart
echo.
echo Restarting services...
%COMPOSE_CMD% restart
echo [OK] Services restarted
goto :done

:status
echo.
%COMPOSE_CMD% ps
goto :done

:done
echo.
pause
exit /b 0
