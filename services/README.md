# 웹 서비스 계약

[프로젝트 홈](../README.md) · [상위 안내](../README.md)

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

현재 팔 서비스의 `SUCCESS`는 지연 후 반환하는 시뮬레이션입니다. `armApiContract`의 경로 목록도 구현된 HTTP 라우트 목록이 아닙니다. 실기 라즈봇은 [장치 API](../app/api/device/raspbot/README.md)를 사용합니다.
