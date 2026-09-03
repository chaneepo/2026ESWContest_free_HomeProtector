# /api/device/vision/mjpeg

[프로젝트 홈](../../../../../../README.md) · [상위 안내](../README.md)

카메라 MJPEG 응답 본문을 웹 화면으로 스트리밍합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [route.ts](route.ts) | HTTP 요청 처리 |

## 사용 방법

웹 서버와 함께 등록되는 `GET /api/device/vision/mjpeg` 엔드포인트입니다.

| 항목 | 값 |
|---|---|
| 구현 | [route.ts](route.ts) |
| 상위 장치 서버 경로 | `/mjpeg` |
| 실행 단위 | 저장소 루트의 웹 서버 |

## 알아둘 점

응답은 JSON이 아니라 `multipart/x-mixed-replace` 영상 스트림입니다. 프록시는 새로운 객체 인식·마스킹을 수행하지 않습니다.
