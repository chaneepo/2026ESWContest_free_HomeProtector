# /api/device/raspbot/mode

[프로젝트 홈](../../../../../../README.md) · [상위 안내](../README.md)

안전모드 또는 실기모드 전환을 요청합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `POST /api/device/raspbot/mode` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/api/raspbot/mode` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

실기 전환 본문은 `mode: hardware`, `confirm_safe: true`입니다. 사용자의 안전 확인과 실제 연결 확인을 거친 후 `control_token`을 받습니다.
