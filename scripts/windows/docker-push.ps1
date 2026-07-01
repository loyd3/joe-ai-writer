# ============================================
# Joe AI Writer - Docker 镜像构建与发布 (Windows)
# ============================================
# 用法:
#   交互模式:  .\scripts\windows\docker-push.ps1 -Interactive
#   命令行:    .\scripts\windows\docker-push.ps1 -Version 1.0.0
#   仅导出:    .\scripts\windows\docker-push.ps1 -ExportOnly
#   跳过推送:  .\scripts\windows\docker-push.ps1 -SkipPush
#   阿里云:    .\scripts\windows\docker-push.ps1 -Registry registry.cn-hangzhou.aliyuncs.com/namespace
# ============================================

param(
    [string]$Version = "",
    [string]$DockerUser = "",
    [string]$Registry = "",
    [switch]$SkipPush = $false,
    [switch]$ExportOnly = $false,
    [switch]$Interactive = $false,
    [ValidateSet("full", "lite")]
    [string]$BackendVariant = "full"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "> $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[X] $msg" -ForegroundColor Red }

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Joe AI Writer - Docker 发布" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "项目目录: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

if (-not $DockerUser) {
    $DockerUser = $env:DOCKER_USER
    if (-not $DockerUser) { $DockerUser = "loyd3" }
}

$BackendImage = "$DockerUser/joe-ai-writer-backend"
$FrontendImage = "$DockerUser/joe-ai-writer-frontend"
$ExportDir = Join-Path $ProjectRoot "docker-images"

Write-Info "检查 Docker..."
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker 未运行，请先启动 Docker Desktop"
    exit 1
}
Write-Success "Docker 运行正常"
Write-Host ""

if ($Interactive -or (-not $Version -and -not $ExportOnly -and -not $SkipPush -and -not $Registry)) {
    $Interactive = $true
    $inputVersion = Read-Host "输入版本号 (默认 latest)"
    if ($inputVersion) { $Version = $inputVersion } else { $Version = "latest" }

    $inputUser = Read-Host "Docker Hub 用户名 (默认 $DockerUser)"
    if ($inputUser) {
        $DockerUser = $inputUser
        $BackendImage = "$DockerUser/joe-ai-writer-backend"
        $FrontendImage = "$DockerUser/joe-ai-writer-frontend"
    }
} elseif (-not $Version) {
    $Version = "latest"
}

Write-Host "配置:" -ForegroundColor Yellow
Write-Host "  Docker 用户: $DockerUser"
Write-Host "  版本:        $Version"
Write-Host "  后端镜像:    $BackendImage"
Write-Host "  前端镜像:    $FrontendImage"
Write-Host "  后端变体:    $BackendVariant"
Write-Host ""

$backendDockerfile = if ($BackendVariant -eq "lite") { "Dockerfile.lite" } else { "Dockerfile" }

Write-Info "[1/4] 构建后端镜像 ($backendDockerfile)..."
docker build -f "backend/$backendDockerfile" -t "${BackendImage}:${Version}" -t "${BackendImage}:latest" ./backend
if ($LASTEXITCODE -ne 0) {
    Write-Err "后端镜像构建失败"
    exit 1
}
Write-Success "后端镜像构建完成"
Write-Host ""

Write-Info "[2/4] 构建前端镜像..."
docker build -t "${FrontendImage}:${Version}" -t "${FrontendImage}:latest" ./frontend
if ($LASTEXITCODE -ne 0) {
    Write-Err "前端镜像构建失败"
    exit 1
}
Write-Success "前端镜像构建完成"
Write-Host ""

Write-Info "[3/4] 镜像列表:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | Select-String "joe-ai-writer"
Write-Host ""

function Export-Images {
    Write-Info "导出镜像到 $ExportDir ..."
    if (-not (Test-Path $ExportDir)) {
        New-Item -ItemType Directory -Path $ExportDir | Out-Null
    }

    docker save -o "$ExportDir/joe-ai-writer-backend-${Version}.tar" "${BackendImage}:${Version}"
    if ($LASTEXITCODE -ne 0) { throw "后端镜像导出失败" }

    docker save -o "$ExportDir/joe-ai-writer-frontend-${Version}.tar" "${FrontendImage}:${Version}"
    if ($LASTEXITCODE -ne 0) { throw "前端镜像导出失败" }

    Write-Success "镜像已导出"
    Get-ChildItem $ExportDir -Filter "*${Version}.tar" | Format-Table Name, Length, LastWriteTime
}

function Push-ToDockerHub {
    $loginInfo = docker info 2>&1 | Select-String "Username"
    if (-not $loginInfo) {
        Write-Warn "未检测到 Docker Hub 登录"
        $doLogin = Read-Host "是否现在登录? (y/n)"
        if ($doLogin -eq "y") {
            docker login
            if ($LASTEXITCODE -ne 0) { throw "Docker Hub 登录失败" }
        } else {
            throw "请先运行 docker login"
        }
    }

    Write-Info "推送到 Docker Hub..."
    docker push "${BackendImage}:${Version}"
    docker push "${BackendImage}:latest"
    docker push "${FrontendImage}:${Version}"
    docker push "${FrontendImage}:latest"
}

function Push-ToRegistry([string]$TargetRegistry) {
    $targetBackend = "$TargetRegistry/joe-ai-writer-backend"
    $targetFrontend = "$TargetRegistry/joe-ai-writer-frontend"

    Write-Info "标记镜像: $TargetRegistry"
    docker tag "${BackendImage}:${Version}" "${targetBackend}:${Version}"
    docker tag "${FrontendImage}:${Version}" "${targetFrontend}:${Version}"

    Write-Info "登录 $TargetRegistry ..."
    docker login $TargetRegistry
    if ($LASTEXITCODE -ne 0) { throw "仓库登录失败" }

    Write-Info "推送镜像..."
    docker push "${targetBackend}:${Version}"
    docker push "${targetFrontend}:${Version}"
}

if ($ExportOnly) {
    Export-Images
} elseif ($Interactive) {
    Write-Info "[4/4] 发布选项:"
    Write-Host ""
    Write-Host "  1. 推送到 Docker Hub"
    Write-Host "  2. 推送到阿里云容器镜像服务 (ACR)"
    Write-Host "  3. 导出为本地 tar 文件"
    Write-Host "  4. 跳过推送 (仅构建)"
    Write-Host ""
    $choice = Read-Host "请选择 (1-4)"

    switch ($choice) {
        "1" { Push-ToDockerHub; Write-Success "推送完成" }
        "2" {
            $acr = Read-Host "输入阿里云仓库地址 (如 registry.cn-hangzhou.aliyuncs.com/your-namespace)"
            Push-ToRegistry $acr
            Write-Success "推送完成"
        }
        "3" { Export-Images }
        "4" { Write-Warn "已跳过推送" }
        default { Write-Warn "无效选项，已跳过推送" }
    }
} elseif (-not $SkipPush) {
    Write-Info "[4/4] 推送镜像..."
    if ($Registry) {
        Push-ToRegistry $Registry
    } else {
        Push-ToDockerHub
    }
    Write-Success "推送完成"
} else {
    Write-Warn "已跳过推送 (SkipPush)"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  发布完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "镜像:" -ForegroundColor Yellow
Write-Host "  后端: ${BackendImage}:${Version}"
Write-Host "  前端: ${FrontendImage}:${Version}"
Write-Host ""
Write-Host "部署:" -ForegroundColor Cyan
Write-Host "  1. 配置 .env.prod 中的 DOCKER_REGISTRY=$DockerUser"
Write-Host "  2. 运行 install.bat 或:"
Write-Host "     docker compose -f docker-compose.prod.yml --env-file .env.prod up -d"
Write-Host ""
