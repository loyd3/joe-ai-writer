# 兼容入口：转发到 scripts/windows/docker-push.ps1
# 用法: .\docker-push.ps1 -Version 1.0.0 [-SkipPush] [-ExportOnly] [-Registry xxx]

param(
    [string]$Version = "latest",
    [string]$DockerUser = "",
    [string]$Registry = "",
    [switch]$SkipPush = $false,
    [switch]$ExportOnly = $false,
    [switch]$Interactive = $false,
    [ValidateSet("full", "lite")]
    [string]$BackendVariant = "full"
)

$scriptPath = Join-Path $PSScriptRoot "scripts\windows\docker-push.ps1"
& $scriptPath @PSBoundParameters
