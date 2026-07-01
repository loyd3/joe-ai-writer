# ============================================
# Joe AI Writer - Docker 环境诊断 (Windows)
# ============================================

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Joe AI Writer - 环境诊断" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目目录: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

Write-Host "[1/5] 检查 Docker 状态..." -ForegroundColor Yellow
docker info *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Docker 运行正常" -ForegroundColor Green
} else {
    Write-Host "  [X] Docker 未运行或未安装" -ForegroundColor Red
}
Write-Host ""

Write-Host "[2/5] 检查容器状态 (生产环境)..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml ps 2>$null
Write-Host ""
Write-Host "轻量开发环境:" -ForegroundColor DarkGray
docker compose -f docker-compose-lite.yml ps 2>$null
Write-Host ""

Write-Host "[3/5] 检查端口占用..." -ForegroundColor Yellow
$ports = @(8080, 9000, 11434)
foreach ($port in $ports) {
    $connection = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
    if ($connection) {
        Write-Host "  [OK] 端口 $port 正在监听" -ForegroundColor Green
        if ($connection -match "0\.0\.0\.0:$port" -or $connection -match "\[::\]:$port") {
            Write-Host "       监听范围: 所有接口" -ForegroundColor Green
        } elseif ($connection -match "127\.0\.0\.1:$port") {
            Write-Host "       仅监听 127.0.0.1，Docker 容器可能无法访问" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [-] 端口 $port 未监听" -ForegroundColor DarkYellow
    }
}
Write-Host ""

Write-Host "[4/5] 检查 Ollama..." -ForegroundColor Yellow
$ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollamaProc) {
    Write-Host "  [OK] Ollama 正在运行 (PID: $($ollamaProc.Id))" -ForegroundColor Green
    $models = ollama list 2>$null
    if ($models) {
        Write-Host "  已安装模型:" -ForegroundColor Cyan
        $models | Select-Object -Skip 1 | ForEach-Object { Write-Host "    - $_" }
    }
} else {
    Write-Host "  [-] Ollama 未运行 (使用云端 API 时可忽略)" -ForegroundColor DarkYellow
}
Write-Host ""

Write-Host "[5/5] 检查后端日志..." -ForegroundColor Yellow
$prodLogs = docker compose -f docker-compose.prod.yml logs backend --tail 15 2>&1
if ($prodLogs -match "Error|Exception") {
    Write-Host "  [!] 生产环境后端可能有错误:" -ForegroundColor Yellow
    $prodLogs | Select-String "Error|Exception" | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
} else {
    Write-Host "  [OK] 生产环境后端无明显错误" -ForegroundColor Green
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  诊断完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址: http://localhost:8080 (前端) / http://localhost:9000 (后端)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ollama 仅监听本地时，以管理员运行:" -ForegroundColor Cyan
Write-Host '  [Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "Machine")' -ForegroundColor Gray
Write-Host ""
