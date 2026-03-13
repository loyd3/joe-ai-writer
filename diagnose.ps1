# 墨心 AI 写作工具 - 启动诊断脚本
# 运行此脚本检查常见问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  墨心 AI 写作工具 - 启动诊断" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Docker 状态
Write-Host "[1/5] 检查 Docker 状态..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Docker 运行正常" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Docker 未运行" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ Docker 未安装或未启动" -ForegroundColor Red
}
Write-Host ""

# 2. 检查容器状态
Write-Host "[2/5] 检查容器状态..." -ForegroundColor Yellow
cd D:\projects\joe-ai-writer
docker-compose -f docker-compose-lite.yml ps
Write-Host ""

# 3. 检查端口占用
Write-Host "[3/5] 检查端口占用..." -ForegroundColor Yellow
$ports = @(8080, 9000, 11434)
foreach ($port in $ports) {
    $connection = netstat -ano | findstr ":$port " | findstr "LISTENING"
    if ($connection) {
        Write-Host "  ✅ 端口 $port 正在监听" -ForegroundColor Green
        # 检查是否监听所有接口
        if ($connection -match "0\.0\.0\.0:$port" -or $connection -match "\[::\]:$port") {
            Write-Host "     监听范围: 所有接口 (0.0.0.0)" -ForegroundColor Green
        } elseif ($connection -match "127\.0\.0\.1:$port") {
            Write-Host "     ⚠️  仅监听本地 (127.0.0.1)，Docker 可能无法访问" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ❌ 端口 $port 未监听" -ForegroundColor Red
    }
}
Write-Host ""

# 4. 检查 Ollama
Write-Host "[4/5] 检查 Ollama..." -ForegroundColor Yellow
try {
    $ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
    if ($ollamaProc) {
        Write-Host "  ✅ Ollama 正在运行 (PID: $($ollamaProc.Id))" -ForegroundColor Green
        
        # 检查模型
        $models = ollama list 2>$null
        if ($models) {
            Write-Host "  📦 已安装模型:" -ForegroundColor Cyan
            $models | Select-Object -Skip 1 | ForEach-Object { Write-Host "     - $_" }
        }
    } else {
        Write-Host "  ❌ Ollama 未运行" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ Ollama 未安装" -ForegroundColor Red
}
Write-Host ""

# 5. 检查后端日志
Write-Host "[5/5] 检查后端错误日志..." -ForegroundColor Yellow
$logs = docker-compose -f docker-compose-lite.yml logs backend --tail 20 2>&1
if ($logs -match "Error|error|ERROR|Exception|exception") {
    Write-Host "  ⚠️  发现错误:" -ForegroundColor Yellow
    $logs | findstr "Error error ERROR Exception exception" | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
} else {
    Write-Host "  ✅ 后端运行正常" -ForegroundColor Green
}
Write-Host ""

# 总结
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  诊断完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Yellow
Write-Host "  前端: http://localhost:8080"
Write-Host "  后端: http://localhost:9000"
Write-Host ""
Write-Host "常见问题:" -ForegroundColor Yellow
Write-Host "  1. 如果 Ollama 显示 '仅监听本地'，需要配置环境变量:" -ForegroundColor Cyan
Write-Host "     [Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')" -ForegroundColor Gray
Write-Host "     然后重启 Ollama" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. 如果 Docker 容器无法启动，尝试重启:" -ForegroundColor Cyan
Write-Host "     docker-compose -f docker-compose-lite.yml restart" -ForegroundColor Gray
