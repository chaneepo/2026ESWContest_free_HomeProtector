# CARE-PACK 제어센터

CARE-PACK은 외출 준비물을 계획하고, 로봇팔이 물품을 가방으로 옮기며, 센서로 실제 적재 여부를 확인하는 생활 보조 시스템이다. 이 저장소에는 현재 한국어 제어센터 UI와 장비 연동 전 시뮬레이션이 구현되어 있다.

> 라즈봇 수동 제어, 카메라 서버 연동과 작업·팔 UI 시뮬레이션을 제공한다. 자율 작업의 의사결정과 상태 전이는 독립 시뮬레이터로 검증한다. [기능 안내](../../README.md), [자율 작업 시뮬레이터](../../autonomy/README.md), [안전 점검](../../raspbot_runtime/SAFETY_REVIEW.md)을 참고한다.

이 문서는 `docs/setup/`에 있지만, 아래 명령은 별도 안내가 없으면 `package.json`이 있는 **프로젝트 루트**에서 실행합니다.

## 개발 환경 설정

현재 웹 프론트엔드는 Node.js로 실행한다. Python 가상환경은 앞으로 추가할 FastAPI 백엔드, OpenCV 비전, SO-ARM101 제어 모듈의 패키지를 시스템 Python과 분리하기 위해 사용한다.

### 필요 환경

- Node.js 22.13 이상 (`.nvmrc`: `22.13.0`)
- npm
- Python 3.12.2 (`.python-version`: `3.12.2`)
- Docker Desktop 또는 Docker Engine과 Docker Compose

`nvm` 또는 `pyenv`는 필수가 아니다. 설치되어 있다면 프로젝트의 버전 파일을 이용할 수 있다.

### 최초 1회 설치

저장소를 원하는 폴더에 복제하고 프로젝트 루트로 이동한다. 특정 사용자의 절대 경로는 필요하지 않다.

```bash
git clone https://github.com/chaneepo/2026_ESW_HomeProtector.git
cd 2026_ESW_HomeProtector
```

macOS/Linux에서는 다음 통합 설정 스크립트를 실행한다.

```bash
./scripts/setup.sh
```

이 스크립트는 Node.js 버전을 확인하고 `npm ci`, `.venv` 생성, pip 업그레이드, `requirements-dev.txt` 설치를 순서대로 수행한다. 이미 생성된 `.venv`는 재사용하므로 의존성을 갱신할 때 다시 실행해도 된다.

Windows PowerShell에서는 다음 명령을 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

명령의 의미는 다음과 같다.

- `powershell.exe`: Windows PowerShell 실행
- `-NoProfile`: 개인 PowerShell 설정을 불러오지 않고 동일한 조건에서 실행
- `-ExecutionPolicy Bypass`: 이 실행에서만 스크립트 실행을 허용하며 시스템 정책은 영구 변경하지 않음
- `-File .\scripts\setup.ps1`: 현재 프로젝트의 환경 설정 스크립트 실행

`setup.ps1`은 Node.js와 npm을 확인하고 프론트엔드 패키지를 설치한다. 이어서 Windows의 `py -3.12`, `python`, `python3` 순서로 Python을 찾아 `.venv\Scripts`에 가상환경을 만들고 `requirements-dev.txt`를 설치한다.

macOS/Linux에서 각 단계를 직접 실행하려면 다음 명령을 사용한다.

```bash
# Node.js 버전 선택: nvm 사용 시
nvm install
nvm use

# 프론트엔드 패키지 설치
npm install

# Python 가상환경 생성
python3 -m venv .venv

# macOS/Linux 가상환경 활성화
source .venv/bin/activate

# 가상환경 내부 도구와 전체 개발 의존성 설치
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Windows PowerShell에서 수동으로 가상환경을 활성화하려면 다음 명령을 사용한다.

```powershell
# 프론트엔드 패키지 설치
npm install

# Python 가상환경 생성 및 활성화
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 가상환경 내부 도구와 전체 개발 의존성 설치
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Node.js 패키지는 Python 가상환경에 넣지 않고 프로젝트의 `node_modules`에 설치된다. 두 환경 모두 프로젝트 폴더 안에 생성되며 `.gitignore`로 Git에서 제외된다.

### Python 설치 목록

| 파일 | 용도 | 주요 패키지 |
|---|---|---|
| `requirements.txt` | 실행 환경 | FastAPI, pydantic-settings, SQLAlchemy, psycopg, NumPy, OpenCV contrib, pyserial |
| `requirements-dev.txt` | 개발·테스트 환경 | 실행 환경 전체 + pytest, pytest-asyncio, Ruff, mypy |

일반 개발자는 `requirements-dev.txt` 하나만 설치하면 된다. 실행 패키지만 필요한 장치나 배포 환경에서는 다음처럼 설치한다.

```bash
python -m pip install -r requirements.txt
```

OpenCV contrib 패키지는 ArUco와 AprilTag marker 기능을 포함하기 위해 선택했다. `pyserial`은 SO-ARM101 또는 ESP32의 직렬 통신 기반선이며, 전용 로봇 SDK는 실제 연결 방식이 확정된 뒤 별도로 추가한다.

SQLAlchemy는 ORM 계층으로 사용하고 PostgreSQL 연결에는 psycopg 3을 사용한다. `requirements-dev.txt`가 `requirements.txt`를 포함하므로 일반 개발환경에서도 PostgreSQL 드라이버가 함께 설치된다.

### PostgreSQL Docker 설정

PostgreSQL 17은 `compose.yaml`의 `db` 서비스로 실행한다. 데이터는 `postgres_data` Docker 볼륨에 저장되므로 컨테이너를 다시 만들어도 유지된다. 호스트 포트는 외부 네트워크에 공개하지 않고 `127.0.0.1`에만 연결한다.

최초 1회 환경변수 예시를 로컬 `.env`로 복사한다. `.env`에는 개발자별 비밀번호가 있으므로 Git에 올라가지 않는다.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

복사한 `.env`에서 `POSTGRES_PASSWORD`와 `DATABASE_URL`의 비밀번호를 동일하게 변경한 뒤 DB를 실행한다.

```bash
docker compose up -d db
docker compose ps
```

DB 로그와 직접 접속 명령은 다음과 같다.

```bash
docker compose logs -f db
docker compose exec db psql -U care_pack -d care_pack
```

종료와 재실행:

```bash
docker compose stop db
docker compose start db
```

컨테이너만 제거할 때는 `docker compose down`을 사용한다. `docker compose down -v`는 `postgres_data` 볼륨과 모든 DB 데이터를 삭제하므로 완전 초기화가 필요한 경우에만 사용한다.

호스트의 FastAPI 백엔드는 `.env`의 `localhost:5432` 주소를 사용한다. 나중에 백엔드도 Compose 서비스로 옮기면 호스트 이름을 `localhost`에서 `db`로 변경한다.

### DB 마이그레이션과 시드

빈 DB에 현재 스키마를 생성하거나 기존 DB를 최신 버전으로 올린다.

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

현재 마이그레이션 확인과 모델 일치 검사:

```bash
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
```

개발/시뮬레이션용 위치 5개, 물품 5개, 루틴 2개와 루틴 구성을 명시적으로 넣는다. 여러 번 실행해도 중복되지 않으며 애플리케이션 시작 시 자동 실행되지 않는다.

```bash
python -m backend.app.seed
```

구현된 애플리케이션 테이블은 다음 일곱 개다.

```text
locations, items, routines, routine_items, jobs, job_items, job_events
```

### DB 테스트와 FastAPI 상태 확인

DB 테스트는 정상 개발 DB를 건드리지 않고 이름이 `_test`로 끝나는 별도 데이터베이스를 생성해 마이그레이션 왕복, 제약조건, 관계, 시드 멱등성과 실행 이력 보호를 확인한 뒤 삭제한다.

```bash
python -m pytest backend/tests -q
```

FastAPI 상태 확인 서버 실행:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

브라우저에서 `http://127.0.0.1:8000/health`를 열면 DB 연결 상태를 확인할 수 있다. 웹 화면은 메모리 mock으로 물품·루틴·작업 흐름을 제공하며, 업무 CRUD API를 통한 DB 연동은 확장 계획에 포함된다.

### DB 종료와 안전한 초기화

일상적인 종료는 데이터를 보존한다.

```bash
docker compose stop db
```

컨테이너만 다시 만들 때는 `docker compose down` 후 `docker compose up -d db`를 사용한다. 개발 DB를 완전히 초기화해야 할 때만 다음 명령을 사용한다. 이 명령은 Docker 볼륨과 모든 DB 데이터를 삭제한다.

```bash
docker compose down -v
docker compose up -d db
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
```

실제 `.env`와 PostgreSQL 볼륨은 Git에 올라가지 않는다. `.env.example`, 모델, 마이그레이션과 시드 코드만 추적한다.

### 환경 확인

macOS/Linux:

```bash
which python
python --version
python -m pip --version
node --version
npm --version
```

Windows PowerShell:

```powershell
(Get-Command python).Source
python --version
python -m pip --version
node --version
npm --version
```

macOS/Linux의 `which python` 결과는 현재 프로젝트의 `.venv/bin/python`이어야 한다. Windows의 `(Get-Command python).Source` 결과는 현재 프로젝트의 `.venv\Scripts\python.exe`여야 한다. 프롬프트 앞에 `(.venv)`가 표시되는 것으로도 활성화를 확인할 수 있다.

### 매일 작업 시작

macOS/Linux:

```bash
./scripts/dev.sh
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

각 `dev` 스크립트는 운영체제에 맞는 `.venv`와 `node_modules`를 확인하고 Python 가상환경을 활성화한 뒤 프론트엔드 서버를 시작한다. 개발 서버가 출력하는 로컬 주소를 브라우저에서 연다. 향후 FastAPI가 추가되면 같은 스크립트에 백엔드 실행을 연결한다.

### Python 패키지 관리

반드시 활성화된 환경에서 `python -m pip` 형식으로 설치한다.

```bash
python -m pip install <패키지명>
python -m pip list
```

팀에서 사용할 직접 의존성과 검증된 버전만 해당 requirements 파일에 기록한다. 임시 실험 패키지는 확정하기 전까지 커밋하지 않는다. `.venv` 디렉터리는 `.gitignore`에 포함되어 있으므로 Git에 올라가지 않는다.

설치된 핵심 패키지를 확인하는 명령은 다음과 같다.

```bash
python -c "import cv2, fastapi, numpy, psycopg, serial, sqlalchemy; print('Python dependencies OK')"
python -m pytest --version
python -m ruff --version
python -m mypy --version
```

### 종료와 재생성

작업을 끝내면 다음 명령으로 가상환경을 종료한다.

```bash
deactivate
```

가상환경이 손상되었거나 Python 버전이 달라졌다면 다음과 같이 다시 만든다. 이 명령은 `.venv` 안에 설치된 패키지를 모두 초기화한다.

macOS/Linux:

```bash
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv --clear .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 빌드와 실행

개발 실행:

```bash
npm run dev
```

배포 빌드 확인은 다음과 같다.

```bash
npm run build
npm run start
```

가상환경 활성화 여부는 현재 Node.js 프론트엔드 빌드 결과에 영향을 주지 않는다.

## 현재 가능한 기능

- 대시보드와 장치 상태 확인
- PACK/SORT 작업 시뮬레이션
- PICK 또는 VERIFY 실패 1회 주입과 복구 흐름
- 모의 SO-ARM101 수동 명령
- 모의 비전 인식과 3×3 보관함 표시
- 메모리 기반 물품 관리와 작업 이력
- UI 비상정지와 수동 초기화

웹 화면의 mock 데이터는 새로고침하면 초기화되고, 별도로 운영하는 PostgreSQL 데이터는 유지된다. 실기 라즈봇은 장치 API를 통해 제어하며, 작업·팔 화면은 시뮬레이션으로 실행한다.

## 코드 구조

```text
app/          앱 진입점과 레이아웃
components/   제어센터 셸과 공통 UI
views/        기능별 화면
store/        전역 상태와 실행 조정
services/     도메인 서비스 계약과 mock 호출
mocks/        초기 데이터와 시뮬레이션 엔진
backend/      FastAPI, SQLAlchemy 모델, Alembic 마이그레이션과 DB 테스트
scripts/      macOS/Linux·Windows 통합 환경 설정과 개발 실행
compose.yaml  PostgreSQL 17 Docker Compose 설정
types/        공통 TypeScript 모델
docs/ko/      한국어 기술 문서
docs/en/      영어 기술 문서
```

## 문서

- [프로젝트 개요](../ko/00_PROJECT_OVERVIEW.md)
- [시스템 아키텍처](../ko/01_SYSTEM_ARCHITECTURE.md)
- [프론트엔드 구조](../ko/02_FRONTEND_STRUCTURE.md)
- [백엔드 API 명세](../ko/03_BACKEND_API_SPEC.md)
- [상태기계](../ko/04_STATE_MACHINE.md)
- [비전 시스템 설계](../ko/05_VISION_DESIGN.md)
- [SO-ARM101 인터페이스](../ko/06_SO_ARM101_INTERFACE.md)
- [데이터베이스 스키마](../ko/07_DATABASE_SCHEMA.md)
- [시뮬레이션 모드](../ko/08_SIMULATION_MODE.md)
- [이벤트 로그 명세](../ko/09_EVENT_LOG_SPEC.md)
- [실패 복구](../ko/10_FAILURE_RECOVERY.md)
- [개발 로드맵](../ko/11_DEVELOPMENT_ROADMAP.md)
- [팀 인터페이스 가이드](../ko/12_TEAM_INTERFACE.md)

영문 안내는 [README.en.md](README.en.md)를 참고한다.
