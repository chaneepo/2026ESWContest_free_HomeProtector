# CARE-PACK 한국어 문서

[프로젝트 홈](../../README.md) · [전체 문서](../README.md) · [English](../en/README.md)

이 폴더에는 구현 내용과 목표 설계가 함께 있습니다. 현재 완료 여부는 루트 README의 구현 현황을 우선하세요.

## 문서 목차

| 문서 | 관련 모듈·안내 |
|---|---|
| [프로젝트 개요](00_PROJECT_OVERVIEW.md) | [Project](../../README.md) |
| [시스템 아키텍처](01_SYSTEM_ARCHITECTURE.md) | [Project](../../README.md) |
| [프론트엔드 구조](02_FRONTEND_STRUCTURE.md) | [Web UI](../../views/README.md) |
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

## 실물·시뮬레이션 구분

- 라즈봇 수동 실기 제어와 웹 작업·팔 시뮬레이션은 서로 다른 경로입니다.
- 기존 motor 도구의 수동·고정 시퀀스 실행을 인식 기반 통합 자율 동작과 구분합니다.
- `autonomy/`는 현재 가상 관측값과 가상 명령 기록만 사용합니다.
- 백엔드 공개 API는 현재 `/health`이며, 설계상의 API 표 전체가 구현된 것은 아닙니다.
- 실기 사용 전 [안전 제약](../../chan/SAFETY_REVIEW.md)을 확인하세요.
