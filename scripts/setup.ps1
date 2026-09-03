[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "[CARE-PACK] 필요한 명령을 찾을 수 없습니다: $Name"
    }
}

function Assert-LastExitCode {
    param([Parameter(Mandatory = $true)][string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "[CARE-PACK] $Step 단계가 실패했습니다. 종료 코드: $LASTEXITCODE"
    }
}

Assert-Command node
Assert-Command npm

$NodeVersion = (& node -p "process.versions.node").Trim()
Assert-LastExitCode "Node.js 버전 확인"
$NodeParts = $NodeVersion.Split(".")
if ([int]$NodeParts[0] -lt 22 -or ([int]$NodeParts[0] -eq 22 -and [int]$NodeParts[1] -lt 13)) {
    throw "[CARE-PACK] Node.js 22.13 이상이 필요합니다. 현재: v$NodeVersion"
}

$PythonCommand = $null
$PythonArguments = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
    $PythonArguments = @("-3.12")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCommand = "python3"
} else {
    throw "[CARE-PACK] Python 3.12를 찾을 수 없습니다. Python을 먼저 설치하세요."
}

Write-Host "[CARE-PACK] 1/3 Node.js 패키지를 설치합니다."
if (Test-Path "frontend/package-lock.json") {
    & npm --prefix frontend ci
} else {
    & npm --prefix frontend install
}
Assert-LastExitCode "Node.js 패키지 설치"

Write-Host "[CARE-PACK] 2/3 Python 가상환경을 준비합니다."
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $PythonCommand @PythonArguments -m venv .venv
    Assert-LastExitCode "Python 가상환경 생성"
}

Write-Host "[CARE-PACK] 3/3 Python 개발 패키지를 설치합니다."
& $VenvPython -m pip install --upgrade pip
Assert-LastExitCode "pip 업그레이드"
& $VenvPython -m pip install -r requirements/requirements-dev.txt
Assert-LastExitCode "Python 패키지 설치"

Write-Host ""
Write-Host "[CARE-PACK] 환경 설정이 완료되었습니다."
Write-Host "개발 실행: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1"
Write-Host "Python 활성화: .\.venv\Scripts\Activate.ps1"
