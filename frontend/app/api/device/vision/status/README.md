# /api/device/vision/status

[프로젝트 홈](../../../../../../README.md) · [상위 안내](../README.md)

카메라 서버 상태를 조회합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `GET /api/device/vision/status` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/status` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

`CAMERA_API_URL`의 실제 서버가 별도로 실행되어야 합니다. 이 경로는 추론 모델을 로드하거나 카메라 서버를 시작하지 않습니다.
