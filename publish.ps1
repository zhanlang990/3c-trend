$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "[1/4] Running crawler..." -ForegroundColor Cyan
python crawler/run.py
if ($LASTEXITCODE -ne 0) { Write-Host "Crawler failed." -ForegroundColor Red; exit 1 }

# Pre-flight: verify git repo + remote exist (gentle hint for first-time users)
git rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not a git repo. Crawler output is updated; you can manually deploy data/news.json + static files." -ForegroundColor Yellow
    exit 0
}
$remote = git remote 2>$null
if (-not $remote) {
    Write-Host "No git remote configured. Skipping push step. Add a remote and re-run to publish." -ForegroundColor Yellow
    exit 0
}

Write-Host "[2/4] Staging data/news.json..." -ForegroundColor Cyan
git add data/news.json

Write-Host "[3/4] Committing..." -ForegroundColor Cyan
$ts = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "data: update news at $ts" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Nothing to commit." -ForegroundColor Yellow }

Write-Host "[4/4] Pushing to remote..." -ForegroundColor Cyan
git push origin main

Write-Host "Done." -ForegroundColor Green