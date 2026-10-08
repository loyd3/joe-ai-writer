@echo off
setlocal EnableExtensions

:: Joe AI Writer - Docker deploy
:: Data root: F:\joe-ai-writer\docker-data
:: Usage: deploy.bat [up|down|logs|restart|status|prune]

cd /d "%~dp0"
title Joe AI Writer - Docker

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=up"

if "%DOCKER_DATA_ROOT%"=="" set "DOCKER_DATA_ROOT=F:/joe-ai-writer/docker-data"

docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Install and start Docker Desktop first.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Start Docker Desktop first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [INFO] .env missing, copying from .env.docker ...
    copy /Y ".env.docker" ".env" >nul
    echo [INFO] Edit .env and set DEEPSEEK_API_KEY, and re-run.
)

findstr /B /C:"DOCKER_DATA_ROOT=" ".env" >nul 2>&1
if errorlevel 1 (
    echo.>>".env"
    echo # Docker data root on F drive>>".env"
    echo DOCKER_DATA_ROOT=F:/joe-ai-writer/docker-data>>".env"
)

for %%D in (mysql search_index hf-cache backend-data) do (
    if not exist "F:\joe-ai-writer\docker-data\%%D" mkdir "F:\joe-ai-writer\docker-data\%%D" >nul 2>&1
)

if /i "%ACTION%"=="up" goto up
if /i "%ACTION%"=="down" goto down
if /i "%ACTION%"=="logs" goto logs
if /i "%ACTION%"=="restart" goto restart
if /i "%ACTION%"=="status" goto status
if /i "%ACTION%"=="prune" goto prune
echo Unknown command: %ACTION%
echo Usage: deploy.bat [up^|down^|logs^|restart^|status^|prune]
exit /b 1

:up
echo.
echo ========================================
echo   Starting Docker stack
echo   Data root: %DOCKER_DATA_ROOT%
echo ========================================
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [ERROR] Start failed. Run: deploy.bat logs
    pause
    exit /b 1
)
echo.
echo ========================================
echo   Deploy OK
echo ========================================
echo   Frontend:  http://localhost:8080
echo   Backend:   http://localhost:9000
echo   API docs:  http://localhost:9000/docs
echo.
echo   MySQL:     %DOCKER_DATA_ROOT%/mysql
echo   Search:    %DOCKER_DATA_ROOT%/search_index
echo   HF cache:  %DOCKER_DATA_ROOT%/hf-cache
echo.
docker compose ps
goto end

:down
echo Stopping services - keeps F drive data ...
docker compose down
goto end

:logs
docker compose logs -f
goto end

:restart
docker compose restart
docker compose ps
goto end

:status
docker compose ps
echo.
echo --- docker disk ---
docker system df
echo.
echo --- F drive project data ---
dir /s /-c "F:\joe-ai-writer\docker-data" 2>nul | findstr /I "File Dir"
goto end

:prune
echo Pruning unused images/build cache - keeps F drive app data ...
docker builder prune -f
docker image prune -f
docker system df
goto end

:end
echo.
pause
