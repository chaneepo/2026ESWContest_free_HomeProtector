[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvPython) -or -not (Test-Path "frontend/node_modules")) {
    throw "[CARE-PACK] 개발 환경이 준비되지 않았습니다. 먼저 powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 명령을 실행하세요."
}

# 향후 FastAPI/비전 프로세스도 같은 Python 환경을 사용한다.
& $ActivateScript

Write-Host "[CARE-PACK] Python: $(& python --version 2>&1)"
Write-Host "[CARE-PACK] Node.js: $(& node --version)"
Write-Host "[CARE-PACK] 프론트엔드 개발 서버를 시작합니다."

& npm --prefix frontend run dev
exit $LASTEXITCODE
