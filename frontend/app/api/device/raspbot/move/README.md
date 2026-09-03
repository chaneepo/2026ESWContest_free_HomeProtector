# /api/device/raspbot/move

[프로젝트 홈](../../../../../../README.md) · [상위 안내](../README.md)

짧은 방향 이동을 요청합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `POST /api/device/raspbot/move` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/api/move` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

본문에 `action`, `speed`, `duration`, `control_token`을 전달합니다. 실기모드·유효 권한이 필요하며 일반 이동은 최대 0.5초, 속도는 최대 80입니다. 각도 기반 `/turn`은 Pi 전용 UI가 직접 사용하는 경로로, 이 웹 프록시에 별도 구현되어 있지 않습니다.
