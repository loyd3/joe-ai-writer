# 设置 Ollama 监听所有网络接口
# 以管理员身份运行 PowerShell，然后执行：

# 停止 Ollama 服务
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 设置环境变量
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "Machine")
[Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "Machine")

# 启动 Ollama（需要指定环境变量）
$env:OLLAMA_HOST="0.0.0.0:11434"
$env:OLLAMA_ORIGINS="*"
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve"

Write-Host "Ollama 已启动，监听 0.0.0.0:11434"
Write-Host "请验证: netstat -ano | findstr 11434"
