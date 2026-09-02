# /api/device/raspbot/status

[프로젝트 홈](../../../../../README.md) · [상위 안내](../README.md)

현재 모드·연결·이동 잠금·명령 상태를 조회합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `GET /api/device/raspbot/status` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/api/status` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

요청 본문은 없습니다. 상태 조회만으로 이동 권한이 발급되거나 갱신되지 않습니다. `control_token`은 공개 상태 응답에 포함되지 않습니다.
