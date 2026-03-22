# Joe AI Writer - Windows Docker Deploy Script (PowerShell)
# ============================================

$PROJECT_DIR = $PSScriptRoot
Set-Location $PROJECT_DIR

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "     Joe AI Writer - Docker Deploy" -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker installation
Write-Host "[1/7] Checking Docker environment..."
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw }
    Write-Host "[OK] $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not installed or not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop:"
    Write-Host "   https://www.docker.com/products/docker-desktop"
    Write-Host ""
    Write-Host "Make sure Docker Desktop is running after installation."
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify Docker daemon is reachable (CLI can exist while Desktop is stopped)
Write-Host "[2/7] Verifying Docker engine..."
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Cannot connect to Docker Engine!" -ForegroundColor Red
    Write-Host ""
    Write-Host "On Windows, start Docker Desktop and wait until it shows 'Engine running'."
    Write-Host "If you see 'open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified',"
    Write-Host "the Docker daemon is not running — open Docker Desktop from the Start menu."
    Write-Host ""
    Write-Host "After Docker is green, run this deploy script again."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Docker Engine is reachable" -ForegroundColor Green

# Check Docker Compose
Write-Host ""
Write-Host "[3/7] Checking Docker Compose..."
$COMPOSE_CMD = ""
try {
    docker compose version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $COMPOSE_CMD = "docker compose"
    } else {
        throw
    }
} catch {
    try {
        docker-compose --version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $COMPOSE_CMD = "docker-compose"
        } else {
            throw
        }
    } catch {
        Write-Host "[ERROR] Docker Compose is not installed!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host "[OK] Docker Compose is available: $COMPOSE_CMD" -ForegroundColor Green

# Check .env file
Write-Host ""
Write-Host "[4/7] Checking environment configuration..."
if (-not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found" -ForegroundColor Yellow
    
    if (Test-Path ".env.docker") {
        Write-Host "[INFO] Creating .env from .env.docker..."
        Copy-Item ".env.docker" ".env" -Force
        Write-Host "[OK] .env file created" -ForegroundColor Green
        Write-Host ""
        Write-Host "[WARN] Please edit .env file to configure your AI API Key!" -ForegroundColor Yellow
        Write-Host "   File location: $PROJECT_DIR\.env"
        Write-Host ""
        Write-Host "Default configuration:"
        Write-Host "   - MySQL root password: rootpassword"
        Write-Host "   - Database user: joewriter / joewriter123"
        Write-Host "   - AI Provider: DeepSeek"
        Write-Host ""
        $editNow = Read-Host "Edit .env file now? (Y/N)"
        if ($editNow -eq "Y" -or $editNow -eq "y") {
            notepad ".env"
        }
    } else {
        Write-Host "[ERROR] .env.docker template file not found!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[OK] Environment configuration exists" -ForegroundColor Green
}

# Check API Key configuration
Write-Host ""
Write-Host "[5/7] Verifying API Key configuration..."
$API_KEY_CONFIGURED = $false
$envContent = Get-Content ".env" -Raw

if ($envContent -match "DEEPSEEK_API_KEY=sk-") { $API_KEY_CONFIGURED = $true }
if ($envContent -match "OPENAI_API_KEY=sk-") { $API_KEY_CONFIGURED = $true }
if ($envContent -match "SILICONFLOW_API_KEY=sk-") { $API_KEY_CONFIGURED = $true }
if ($envContent -match "CUSTOM_API_KEY=sk-") { $API_KEY_CONFIGURED = $true }

if (-not $API_KEY_CONFIGURED) {
    Write-Host "[WARN] No valid AI API Key detected!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please edit .env file and configure at least one API Key:"
    Write-Host "   - DEEPSEEK_API_KEY (Recommended for Chinese writing)"
    Write-Host "   - OPENAI_API_KEY"
    Write-Host "   - SILICONFLOW_API_KEY"
    Write-Host "   - CUSTOM_API_KEY"
    Write-Host ""
    $continueDeploy = Read-Host "Continue deployment? AI features will not work (Y/N)"
    if ($continueDeploy -ne "Y" -and $continueDeploy -ne "y") {
        Write-Host "Deployment cancelled"
        Read-Host "Press Enter to exit"
        exit 0
    }
} else {
    Write-Host "[OK] API Key is configured" -ForegroundColor Green
}

# Stop old services if exist
Write-Host ""
Write-Host "[6/7] Cleaning up old containers..."
Invoke-Expression "$COMPOSE_CMD down --remove-orphans 2>`$null"
Write-Host "[OK] Cleanup completed" -ForegroundColor Green

# Build and start services
Write-Host ""
Write-Host "[7/7] Building and starting services..."
Write-Host "   This may take a few minutes, please wait..."
Write-Host ""

Invoke-Expression "$COMPOSE_CMD up --build -d"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Deployment failed! Please check error messages above." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Wait for services to start
Write-Host ""
Write-Host "Waiting for services to start..."
Start-Sleep -Seconds 5

# Check service status
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "      Deployment Successful!" -ForegroundColor Green
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Invoke-Expression "$COMPOSE_CMD ps"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:8080"
Write-Host "   Backend API: http://localhost:9000"
Write-Host ""
Write-Host "Common Commands:" -ForegroundColor Yellow
Write-Host "   View logs:  .\deploy.ps1 logs"
Write-Host "   Stop:       .\deploy.ps1 stop"
Write-Host "   Restart:    .\deploy.ps1 restart"
Write-Host "   Status:     .\deploy.ps1 status"
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "   $PROJECT_DIR\.env"
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Handle additional commands
paramHandler

function paramHandler {
    param([string]$action)
    
    switch ($action) {
        "logs" { showLogs }
        "stop" { stopServices }
        "down" { stopServices }
        "restart" { restartServices }
        "status" { showStatus }
        default { 
            $viewLogs = Read-Host "View real-time logs? (Y/N)"
            if ($viewLogs -eq "Y" -or $viewLogs -eq "y") {
                showLogs
            }
        }
    }
}

function showLogs {
    Write-Host ""
    Write-Host "Showing logs (Press Ctrl+C to exit)..."
    Invoke-Expression "$COMPOSE_CMD logs -f"
}

function stopServices {
    Write-Host ""
    Write-Host "Stopping services..."
    Invoke-Expression "$COMPOSE_CMD down"
    Write-Host "[OK] Services stopped" -ForegroundColor Green
}

function restartServices {
    Write-Host ""
    Write-Host "Restarting services..."
    Invoke-Expression "$COMPOSE_CMD restart"
    Write-Host "[OK] Services restarted" -ForegroundColor Green
}

function showStatus {
    Write-Host ""
    Invoke-Expression "$COMPOSE_CMD ps"
}

Read-Host "Press Enter to exit"
