# ============================================
# Joe AI Writer - Docker 生产环境部署 (Windows)
# ============================================
# 用法:
#   交互模式:  .\scripts\windows\deploy.ps1
#   本地镜像:  .\scripts\windows\deploy.ps1 -Source local
#   Docker Hub: .\scripts\windows\deploy.ps1 -Source hub -DockerUser loyd3
#   离线 tar:  .\scripts\windows\deploy.ps1 -Source tar
# ============================================

param(
    [ValidateSet("local", "hub", "tar", "")]
    [string]$Source = "",
    [string]$DockerUser = "",
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "> $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[X] $msg" -ForegroundColor Red }

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot
$ExportDir = Join-Path $ProjectRoot "docker-images"
$EnvFile = Join-Path $ProjectRoot ".env.prod"
$ComposeFile = "docker-compose.prod.yml"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Joe AI Writer - Docker 部署" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Info "[1/5] 检查 Docker 环境..."
docker --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker 未安装，请安装 Docker Desktop"
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker 未运行，请启动 Docker Desktop"
    exit 1
}
Write-Success "Docker 环境正常"
Write-Host ""

Write-Info "[2/5] 检查配置文件..."
$EnvExample = Join-Path $ProjectRoot ".env.prod.example"
if (-not (Test-Path $EnvFile)) {
    Write-Warn "未找到 .env.prod，从模板创建..."
    Copy-Item $EnvExample $EnvFile
    Write-Warn "请编辑 .env.prod 修改密码和 AI 配置后重新运行"
    notepad $EnvFile
    Read-Host "配置完成后按 Enter 继续"
} else {
    Write-Success ".env.prod 已存在"
}
Write-Host ""

if (-not $Source) {
    Write-Host "请选择镜像来源:" -ForegroundColor Yellow
    Write-Host "  1. 本地已构建的镜像 (先运行 deploy-docker.bat)"
    Write-Host "  2. 从 Docker Hub 拉取"
    Write-Host "  3. 从 tar 文件加载 (离线部署)"
    Write-Host ""
    $choice = Read-Host "请选择 (1-3)"
    switch ($choice) {
        "1" { $Source = "local" }
        "2" { $Source = "hub" }
        "3" { $Source = "tar" }
        default { Write-Err "无效选项"; exit 1 }
    }
}

if ($Source -eq "hub") {
    if (-not $DockerUser) {
        $DockerUser = Read-Host "输入 Docker Hub 用户名 (默认 loyd3)"
        if (-not $DockerUser) { $DockerUser = "loyd3" }
    }

    Write-Info "[3/5] 从 Docker Hub 拉取镜像..."
    docker pull "${DockerUser}/joe-ai-writer-backend:${Version}"
    docker pull "${DockerUser}/joe-ai-writer-frontend:${Version}"

    $envContent = Get-Content $EnvFile -Raw
    if ($envContent -match "DOCKER_REGISTRY=.*") {
        $envContent = $envContent -replace "DOCKER_REGISTRY=.*", "DOCKER_REGISTRY=$DockerUser"
    } else {
        $envContent += "`nDOCKER_REGISTRY=$DockerUser`n"
    }
    if ($envContent -match "VERSION=.*") {
        $envContent = $envContent -replace "VERSION=.*", "VERSION=$Version"
    }
    Set-Content -Path $EnvFile -Value $envContent -NoNewline
    Write-Success "镜像拉取完成，已更新 .env.prod 中的 DOCKER_REGISTRY"
} elseif ($Source -eq "tar") {
    Write-Info "[3/5] 从 tar 文件加载镜像..."

    $backendTar = Get-ChildItem -Path $ExportDir -Filter "joe-ai-writer-backend-*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $frontendTar = Get-ChildItem -Path $ExportDir -Filter "joe-ai-writer-frontend-*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if (-not $backendTar -or -not $frontendTar) {
        $backendTar = Get-ChildItem -Path $ProjectRoot -Filter "joe-ai-writer-backend-*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $frontendTar = Get-ChildItem -Path $ProjectRoot -Filter "joe-ai-writer-frontend-*.tar" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }

    if (-not $backendTar -or -not $frontendTar) {
        Write-Err "未找到 tar 镜像文件。请先运行 deploy-docker.bat 并选择导出，或放到 docker-images/ 目录"
        exit 1
    }

    docker load -i $backendTar.FullName
    docker load -i $frontendTar.FullName
    Write-Success "镜像加载完成"
} else {
    Write-Info "[3/5] 使用本地镜像 (跳过拉取/加载)..."
    Write-Warn "请确认 .env.prod 中 DOCKER_REGISTRY 与构建时用户名一致"
}

Write-Host ""
Write-Info "[4/5] 启动服务..."
docker compose -f $ComposeFile --env-file $EnvFile up -d
if ($LASTEXITCODE -ne 0) {
    Write-Err "启动失败，查看日志: docker compose -f $ComposeFile logs"
    exit 1
}

Write-Host ""
Write-Info "[5/5] 检查服务状态..."
Start-Sleep -Seconds 5
docker compose -f $ComposeFile ps

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  部署完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Yellow
Write-Host "  前端:   http://localhost:8080"
Write-Host "  后端:   http://localhost:9000"
Write-Host "  API 文档: http://localhost:9000/docs"
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Cyan
Write-Host "  查看日志: docker compose -f $ComposeFile logs -f"
Write-Host "  停止服务: docker compose -f $ComposeFile down"
Write-Host "  重启服务: docker compose -f $ComposeFile restart"
Write-Host ""
