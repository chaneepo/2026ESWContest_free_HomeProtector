# /api/device/raspbot/heartbeat

[프로젝트 홈](../../../../../README.md) · [상위 안내](../README.md)

운전 화면이 응답 중임을 알려 임시 운전 권한을 갱신합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `POST /api/device/raspbot/heartbeat` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/api/raspbot/heartbeat` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

본문에 해당 화면의 `control_token`이 필요합니다. 공통 클라이언트는 1초마다 확인하며 서버의 권한 만료 시간은 5초입니다. 이전·잘못된 토큰으로 이동 권한이 복구되지 않습니다.
