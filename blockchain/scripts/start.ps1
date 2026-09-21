# PowerShell script to start local Hyperledger Fabric Docker network
$NetworkDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\network"

Write-Host "[Fabric] Starting local permissioned Hyperledger Fabric network..." -ForegroundColor Cyan
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    Set-Location $NetworkDir
    docker-compose -f docker-compose-fabric.yml up -d
    Write-Host "[Fabric] Network containers started successfully." -ForegroundColor Green
} elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    Set-Location $NetworkDir
    docker compose -f docker-compose-fabric.yml up -d
    Write-Host "[Fabric] Network containers started successfully." -ForegroundColor Green
} else {
    Write-Host "[Fabric] Docker Desktop is not detected on PATH. Local in-process air-gapped ledger fallback is active." -ForegroundColor Yellow
}
