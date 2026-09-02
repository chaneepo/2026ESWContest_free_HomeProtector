# /api/device/raspbot/stop

[프로젝트 홈](../../../../../README.md) · [상위 안내](../README.md)

정지를 요청하고 운전 권한을 폐기합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `POST /api/device/raspbot/stop` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/api/stop` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

JSON `{}`를 전달합니다. 운전 토큰이 없어도 정지 요청은 가능하지만 같은 출처·JSON 검사는 적용됩니다. `stop_confirmed`는 명령 처리 확인이지 물리적인 바퀴 정지 피드백이 아닙니다.
