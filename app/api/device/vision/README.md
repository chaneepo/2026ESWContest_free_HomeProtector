# 카메라 API

[프로젝트 홈](../../../../README.md) · [상위 안내](../README.md)

별도 카메라 서버의 상태와 MJPEG 스트림을 웹 비전 화면에 전달합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [mjpeg/](mjpeg/README.md) | /api/device/vision/mjpeg |
| [status/](status/README.md) | /api/device/vision/status |

## 사용 방법

루트 `.env.local`의 `CAMERA_API_URL`을 실제 카메라 서버 주소로 설정합니다. 카메라 서버는 별도로 실행해야 합니다.

## 알아둘 점

이 폴더는 YOLO 추론을 실행하지 않습니다. 인식·스트리밍 처리는 카메라 서버가 담당하며, 예시 IP를 현재 장치 주소로 가정하지 마세요.
