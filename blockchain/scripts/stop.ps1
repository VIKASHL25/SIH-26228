# PowerShell script to stop local Hyperledger Fabric Docker network
$NetworkDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\network"

Write-Host "[Fabric] Stopping local Hyperledger Fabric network..." -ForegroundColor Cyan
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    Set-Location $NetworkDir
    docker-compose -f docker-compose-fabric.yml down
    Write-Host "[Fabric] Network containers stopped." -ForegroundColor Green
} elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    Set-Location $NetworkDir
    docker compose -f docker-compose-fabric.yml down
    Write-Host "[Fabric] Network containers stopped." -ForegroundColor Green
} else {
    Write-Host "[Fabric] Local ledger stopped." -ForegroundColor Yellow
}
