# PowerShell Live Demonstration Launcher for SIH-26228 Blockchain Evidence Layer
param(
    [string]$PythonPath = "C:\Users\Gaargi L\miniconda3\envs\sih26\python.exe"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$DemoScript = Join-Path $ScriptDir "demo.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Launching Trustworthy CV Integrity & Blockchain Demo CLI" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

if (Test-Path $PythonPath) {
    & $PythonPath $DemoScript
} else {
    Write-Host "Specified Python executable not found at $PythonPath. Using default python..." -ForegroundColor Yellow
    python $DemoScript
}
