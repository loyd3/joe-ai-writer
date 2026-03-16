# ============================================
# Joe AI Writer - Docker Publish Script (PowerShell)
# Usage: .\docker-push.ps1 [version]
# Example: .\docker-push.ps1 1.0.0
# ============================================

param(
    [string]$Version = "latest",
    [string]$Registry = "",
    [switch]$SkipPush = $false,
    [switch]$ExportOnly = $false
)

# Color functions
function Write-Info($msg) { Write-Host "> $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[X] $msg" -ForegroundColor Red }

# Header
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Joe AI Writer - Docker Publish" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Config
$DockerUser = "loyd3"
$BackendImage = "$DockerUser/joe-ai-writer-backend"
$FrontendImage = "$DockerUser/joe-ai-writer-frontend"

# Check Docker
Write-Info "Checking Docker..."
$dockerCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker is not running. Please start Docker Desktop first."
    exit 1
}
Write-Success "Docker is running"
Write-Host ""

# Show config
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Docker User: $DockerUser"
Write-Host "  Version: $Version"
Write-Host "  Backend: $BackendImage"
Write-Host "  Frontend: $FrontendImage"
Write-Host ""

# Build backend
Write-Info "[1/4] Building backend image..."
docker build -t "${BackendImage}:${Version}" -t "${BackendImage}:latest" ./backend
if ($LASTEXITCODE -ne 0) {
    Write-Err "Backend build failed"
    exit 1
}
Write-Success "Backend image built"
Write-Host "  - ${BackendImage}:${Version}"
Write-Host "  - ${BackendImage}:latest"
Write-Host ""

# Build frontend
Write-Info "[2/4] Building frontend image..."
docker build -t "${FrontendImage}:${Version}" -t "${FrontendImage}:latest" ./frontend
if ($LASTEXITCODE -ne 0) {
    Write-Err "Frontend build failed"
    exit 1
}
Write-Success "Frontend image built"
Write-Host "  - ${FrontendImage}:${Version}"
Write-Host "  - ${FrontendImage}:latest"
Write-Host ""

# Show images
Write-Info "[3/4] Image info:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | findstr "joe-ai-writer"
Write-Host ""

# Export only mode
if ($ExportOnly) {
    Write-Info "Exporting images..."
    $ExportDir = "./docker-images"
    if (!(Test-Path $ExportDir)) {
        New-Item -ItemType Directory -Path $ExportDir | Out-Null
    }
    
    docker save -o "$ExportDir/joe-ai-writer-backend-${Version}.tar" "${BackendImage}:${Version}"
    docker save -o "$ExportDir/joe-ai-writer-frontend-${Version}.tar" "${FrontendImage}:${Version}"
    
    Write-Success "Images exported to $ExportDir"
    Get-ChildItem $ExportDir
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Export Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    exit 0
}

# Push images
if (!$SkipPush) {
    Write-Info "[4/4] Pushing images..."
    
    # Determine target registry
    if ($Registry) {
        $TargetBackend = "$Registry/joe-ai-writer-backend"
        $TargetFrontend = "$Registry/joe-ai-writer-frontend"
        
        Write-Info "Tagging for $Registry..."
        docker tag "${BackendImage}:${Version}" "${TargetBackend}:${Version}"
        docker tag "${FrontendImage}:${Version}" "${TargetFrontend}:${Version}"
        
        Write-Info "Logging in to $Registry..."
        docker login $Registry
    } else {
        $TargetBackend = $BackendImage
        $TargetFrontend = $FrontendImage
        
        # Check Docker Hub login
        $loginInfo = docker info 2>&1 | findstr "Username"
        if (!$loginInfo) {
            Write-Warn "Not logged in to Docker Hub"
            $doLogin = Read-Host "Login now? (y/n)"
            if ($doLogin -eq "y") {
                docker login
            }
        }
    }
    
    # Push backend
    Write-Info "Pushing backend..."
    docker push "${TargetBackend}:${Version}"
    docker push "${TargetBackend}:latest"
    
    # Push frontend
    Write-Info "Pushing frontend..."
    docker push "${TargetFrontend}:${Version}"
    docker push "${TargetFrontend}:latest"
    
    Write-Success "Push complete"
} else {
    Write-Warn "Skipping push (SkipPush flag set)"
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Publish Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Images:" -ForegroundColor Yellow
Write-Host "  Backend: ${BackendImage}:${Version}"
Write-Host "  Frontend: ${FrontendImage}:${Version}"
Write-Host ""
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  Pull: docker pull ${BackendImage}:${Version}"
Write-Host "  Run:  docker-compose -f docker-compose.prod.yml up -d"
Write-Host ""
