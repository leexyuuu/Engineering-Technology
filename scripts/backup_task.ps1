# -*- coding: utf-8 -*-
# 上线前动作 · 定时备份任务脚本（配合计划任务每日执行）
# 用法：powershell -File scripts\backup_task.ps1
# 注册：schtasks /Create /TN "JWC-Agent-DailyBackup" /TR "powershell -ExecutionPolicy Bypass -File <项目绝对路径>\scripts\backup_task.ps1" /SC DAILY /ST 02:00
# 内容：备份 app.db + faiss + docs + uploads → data\backups\daily-<时间戳>；自动清理仅保留最近 30 份
param(
    [int]$Keep = 30
)

$ErrorActionPreference = "Stop"
# 项目根 = 脚本所在目录的上一级
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $ProjectRoot "data"
$BackupRoot = Join-Path $DataDir "backups"

if (-not (Test-Path (Join-Path $DataDir "app.db"))) {
    Write-Output "[backup] 未找到数据库，跳过本次备份"
    exit 1
}

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dest = Join-Path $BackupRoot "daily-$ts"
New-Item -ItemType Directory -Path $dest -Force | Out-Null

# 备份数据库（SQLite 单文件）+ 向量索引 + 种子文档 + 上传原件
Copy-Item (Join-Path $DataDir "app.db") $dest -Force
foreach ($sub in @("faiss", "docs", "uploads")) {
    $src = Join-Path $DataDir $sub
    if (Test-Path $src) { Copy-Item $src $dest -Recurse -Force }
}

$count = (Get-ChildItem $dest -Recurse -File).Count
Write-Output "[backup] 完成 → $dest（$count 个文件）"

# 保留最近 $Keep 份 daily-*，更早的自动清理
$old = Get-ChildItem $BackupRoot -Directory -Filter "daily-*" |
    Sort-Object Name -Descending | Select-Object -Skip $Keep
foreach ($d in $old) {
    Remove-Item $d.FullName -Recurse -Force
    Write-Output "[backup] 清理过期备份：$($d.Name)"
}
