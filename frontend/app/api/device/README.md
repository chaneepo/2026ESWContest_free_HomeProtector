# 장치 API 프록시

[프로젝트 홈](../../../../README.md) · [상위 안내](../README.md)

브라우저가 Pi 주소를 직접 다루지 않도록 웹 서버에서 라즈봇과 카메라 요청을 중계합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [raspbot/](raspbot/README.md) | 라즈봇 API |
| [vision/](vision/README.md) | 카메라 API |

## 사용 방법

웹 루트(`frontend/`)의 `.env.local`에 `RASPBOT_API_URL`, `CAMERA_API_URL`을 설정한 뒤 웹 서버를 재시작합니다.

## 알아둘 점

실제 기기 주소는 직접 확인합니다. 카메라와 라즈봇의 서버·포트는 서로 다를 수 있으며, 환경 파일은 Git에 올리지 않습니다.
