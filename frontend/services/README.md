# 웹 서비스 계약

[프로젝트 홈](../../README.md) · [상위 안내](../../README.md)

물품·작업·이벤트·팔·비전·시스템 조회의 인터페이스와 현재 목업 구현을 제공합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [armService.ts](armService.ts) | 가상 팔 명령·인터페이스 계약 |
| [eventService.ts](eventService.ts) | 가상 이벤트 생성·조회 |
| [itemService.ts](itemService.ts) | 메모리 기반 물품 서비스 |
| [jobService.ts](jobService.ts) | 가상 작업·물품 목록 생성 |
| [systemService.ts](systemService.ts) | 가상 시스템 상태 |
| [visionService.ts](visionService.ts) | 가상 인식 결과 |

## 사용 방법

[SystemProvider](../store/README.md)에서 호출합니다. 별도의 서버 실행 명령은 없습니다.

## 알아둘 점

팔 서비스는 지연 후 `SUCCESS`를 반환해 UI 작업 흐름을 시뮬레이션합니다. `armApiContract`는 향후 서버 연동에 사용할 경로 설계입니다. 실기 라즈봇은 [장치 API](../app/api/device/raspbot/README.md)를 사용합니다.
