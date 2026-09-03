# CARE-PACK 한국어 문서

[프로젝트 홈](../../README.md) · [전체 문서](../README.md) · [English](../en/README.md)

시스템 구조와 모듈별 인터페이스·확장 설계를 정리합니다. 제공 기능과 실행 방식은 [루트 README](../../README.md#구현-현황)에서 확인할 수 있습니다.

## 문서 목차

| 문서 | 관련 모듈·안내 |
|---|---|
| [프로젝트 개요](00_PROJECT_OVERVIEW.md) | [Project](../../README.md) |
| [시스템 아키텍처](01_SYSTEM_ARCHITECTURE.md) | [Project](../../README.md) |
| [프론트엔드 구조](02_FRONTEND_STRUCTURE.md) | [Web UI](../../frontend/views/README.md) |
| [백엔드 API 설계](03_BACKEND_API_SPEC.md) | [Project](../../README.md) |
| [작업 상태기계](04_STATE_MACHINE.md) | [Project](../../README.md) |
| [비전 시스템 설계](05_VISION_DESIGN.md) | [Project](../../README.md) |
| [SO-ARM101 인터페이스](06_SO_ARM101_INTERFACE.md) | [Motor](../../motor/README.md) |
| [데이터베이스 스키마](07_DATABASE_SCHEMA.md) | [Backend](../../backend/README.md) |
| [웹 시뮬레이션](08_SIMULATION_MODE.md) | [Autonomy](../../autonomy/README.md) |
| [이벤트 로그](09_EVENT_LOG_SPEC.md) | [Project](../../README.md) |
| [실패 복구](10_FAILURE_RECOVERY.md) | [Project](../../README.md) |
| [개발 로드맵](11_DEVELOPMENT_ROADMAP.md) | [Project](../../README.md) |
| [팀 연동 규칙](12_TEAM_INTERFACE.md) | [Project](../../README.md) |

## 모듈별 실행 방식

- 라즈봇 수동 제어는 장치 API, 웹 작업·팔 화면은 시뮬레이션으로 실행합니다.
- `motor/`는 독립 도구에서 수동 제어·고정 자세 시퀀스·리더암 추종을 제공합니다.
- `autonomy/`는 가상 관측값과 명령 기록으로 자율 작업 흐름을 검증합니다.
- 백엔드는 `/health`로 DB 접속을 확인하며, 업무 API 명세는 연동 확장을 위한 설계입니다.
- 실기 사용 전 [안전 점검 안내](../../raspbot_runtime/SAFETY_REVIEW.md)를 확인하세요.
