# CARE-PACK 제어센터

CARE-PACK은 로봇을 이용해 외출 준비물을 가방에 적재하고 실제 적재 성공 여부를 검증하는 생활 보조 시스템입니다.

- [한국어 상세 안내와 실행 방법](README.ko.md)
- [English guide and setup](README.en.md)
- 배포된 데모: [care-pack-control.chaneepo500.chatgpt.site](https://care-pack-control.chaneepo500.chatgpt.site/)

> 현재 저장소에는 제어센터 프론트엔드, 실행 시뮬레이션, PostgreSQL 기반 백엔드 DB 토대가 있습니다. SO-ARM101, 카메라, 센서와 업무 API의 프론트엔드 연결은 아직 구현되지 않았습니다.

## 기술 문서

| 주제 | 한국어 | English |
|---|---|---|
| 프로젝트 개요 | [프로젝트 개요](docs/ko/00_PROJECT_OVERVIEW.md) | [Project Overview](docs/en/00_PROJECT_OVERVIEW.md) |
| 시스템 구조 | [시스템 아키텍처](docs/ko/01_SYSTEM_ARCHITECTURE.md) | [System Architecture](docs/en/01_SYSTEM_ARCHITECTURE.md) |
| 프론트엔드 | [프론트엔드 구조](docs/ko/02_FRONTEND_STRUCTURE.md) | [Frontend Structure](docs/en/02_FRONTEND_STRUCTURE.md) |
| 백엔드 API | [백엔드 API 명세](docs/ko/03_BACKEND_API_SPEC.md) | [Backend API Specification](docs/en/03_BACKEND_API_SPEC.md) |
| 상태기계 | [상태기계](docs/ko/04_STATE_MACHINE.md) | [State Machine](docs/en/04_STATE_MACHINE.md) |
| 비전 | [비전 시스템 설계](docs/ko/05_VISION_DESIGN.md) | [Vision System Design](docs/en/05_VISION_DESIGN.md) |
| SO-ARM101 | [SO-ARM101 인터페이스](docs/ko/06_SO_ARM101_INTERFACE.md) | [SO-ARM101 Interface](docs/en/06_SO_ARM101_INTERFACE.md) |
| 데이터베이스 | [데이터베이스 스키마](docs/ko/07_DATABASE_SCHEMA.md) | [Database Schema](docs/en/07_DATABASE_SCHEMA.md) |
| 시뮬레이션 | [시뮬레이션 모드](docs/ko/08_SIMULATION_MODE.md) | [Simulation Mode](docs/en/08_SIMULATION_MODE.md) |
| 이벤트 로그 | [이벤트 로그 명세](docs/ko/09_EVENT_LOG_SPEC.md) | [Event Log Specification](docs/en/09_EVENT_LOG_SPEC.md) |
| 실패 복구 | [실패 복구](docs/ko/10_FAILURE_RECOVERY.md) | [Failure Recovery](docs/en/10_FAILURE_RECOVERY.md) |
| 개발 계획 | [개발 로드맵](docs/ko/11_DEVELOPMENT_ROADMAP.md) | [Development Roadmap](docs/en/11_DEVELOPMENT_ROADMAP.md) |
| 팀 연동 규칙 | [팀 인터페이스 가이드](docs/ko/12_TEAM_INTERFACE.md) | [Team Interface Guide](docs/en/12_TEAM_INTERFACE.md) |

## 환경 설정과 실행

프론트엔드는 Node.js를 사용하고, 향후 백엔드·비전·로봇 제어 모듈은 Python 가상환경을 사용합니다. 저장소를 원하는 위치에 받은 뒤 운영체제에 맞는 스크립트를 실행합니다.

```bash
git clone https://github.com/chaneepo/2026_ESW_HomeProtector.git
cd 2026_ESW_HomeProtector
```

macOS/Linux:

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Windows PowerShell:

```powershell
# 최초 1회 환경 설치
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# 평소 개발 서버 실행
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

`-ExecutionPolicy Bypass`는 현재 실행에서만 PowerShell 스크립트를 허용하며 Windows의 설정을 영구 변경하지 않습니다. `-File` 뒤에는 실행할 스크립트 경로가 옵니다.

설치 목록:

- `requirements.txt`: 백엔드 실행 환경, PostgreSQL ORM·드라이버, 비전, 시리얼 통신 패키지
- `requirements-dev.txt`: 실행 패키지 전체와 테스트·정적 검사 도구

## PostgreSQL 실행

PostgreSQL 17은 Docker에서 실행하며 DB 데이터는 Docker 볼륨에 보존됩니다. 최초 1회 `.env.example`을 `.env`로 복사하고 개발용 비밀번호를 변경합니다.

macOS/Linux:

```bash
cp .env.example .env
docker compose up -d db
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d db
```

상태 확인은 `docker compose ps`, 종료는 `docker compose stop db`를 사용합니다. `docker compose down -v`는 DB 데이터까지 삭제하므로 초기화할 때만 실행합니다.

DB 마이그레이션과 개발 시드:

```bash
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
```

DB 테스트와 백엔드 상태 확인 서버:

```bash
python -m pytest backend/tests -q
python -m uvicorn backend.app.main:app --reload --port 8000
```

현재 구현 테이블은 `locations`, `items`, `routines`, `routine_items`, `jobs`, `job_items`, `job_events`입니다. FastAPI 업무 API와 프론트엔드 연동은 다음 단계입니다.

자세한 공용 설치 방법은 [한국어 개발 환경 설정](README.ko.md#개발-환경-설정)을 참고하세요.
