# PowerShell script to reset local Fabric ledger state
$DataDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\..\data"
$LedgerFile = Join-Path $DataDir "fabric_ledger.json"

Write-Host "[Fabric] Resetting local blockchain ledger state..." -ForegroundColor Cyan
if (Test-Path $LedgerFile) {
    Remove-Item -Path $LedgerFile -Force
    Write-Host "[Fabric] Removed $LedgerFile" -ForegroundColor Green
}
Write-Host "[Fabric] Reset completed." -ForegroundColor Green
