# 라즈봇 API

[프로젝트 홈](../../../../README.md) · [상위 안내](../README.md)

상태 조회, 실기 권한 요청, 짧은 이동, 정지와 heartbeat를 Pi 제어 서버로 전달합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [heartbeat/](heartbeat/README.md) | /api/device/raspbot/heartbeat |
| [mode/](mode/README.md) | /api/device/raspbot/mode |
| [move/](move/README.md) | /api/device/raspbot/move |
| [status/](status/README.md) | /api/device/raspbot/status |
| [stop/](stop/README.md) | /api/device/raspbot/stop |

## 사용 방법

루트 `RASPBOT_API_URL`을 확인한 Pi 서버 또는 SSH 터널 주소로 설정합니다. [프록시 구현](../../../../lib/README.md), [Pi 서버](../../../../raspbot_runtime/README.md)와 함께 사용합니다.

## 알아둘 점

쓰기 요청은 JSON과 같은 출처 검사를 사용합니다. 실기 이동에는 화면별 `control_token`이 필요합니다. 이 제어권은 사용자 로그인 인증을 대신하지 않습니다.
