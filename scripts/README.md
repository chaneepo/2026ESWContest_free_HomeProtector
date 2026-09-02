# 개발환경 실행 스크립트

[프로젝트 홈](../README.md) · [상위 안내](../README.md)

macOS/Linux와 Windows에서 의존성·가상환경을 준비하고 웹 개발 서버를 실행합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [dev.ps1](dev.ps1) | Windows 웹 개발 서버 실행 |
| [dev.sh](dev.sh) | macOS/Linux 웹 개발 서버 실행 |
| [setup.ps1](setup.ps1) | Windows 개발환경 설치 |
| [setup.sh](setup.sh) | macOS/Linux 환경·의존성 설치 |

## 사용 방법

저장소 루트에서:

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

## 알아둘 점

설치 스크립트는 패키지를 다운로드하고 `.venv`를 생성합니다. 개발 실행은 웹 서버를 시작하며 DB·카메라·Pi 서버를 모두 자동 기동하지 않습니다. 팔의 `lerobot` 환경은 별도입니다.
