# CARE-PACK Control Center

CARE-PACK plans items for an outing, uses a robot arm to move them into a bag, and verifies that loading physically succeeded. This repository currently contains the Korean control-center UI and a pre-hardware simulation.

> The project provides manual Raspbot control, camera-server integration, and job/arm UI simulation. A standalone simulator validates autonomous task decisions and state transitions. See the [feature guide](../../README.md), [autonomy simulator](../../autonomy/README.md), and [safety review](../../raspbot_runtime/SAFETY_REVIEW.md).

Although this guide lives in `docs/setup/`, run the commands from the **project root** containing `package.json`, unless explicitly stated otherwise.

## Development environment setup

The current web frontend runs on Node.js. The Python virtual environment isolates packages for the future FastAPI backend, OpenCV vision pipeline, and SO-ARM101 controller from the system Python installation.

### Requirements

- Node.js 22.13 or newer (`.nvmrc`: `22.13.0`)
- npm
- Python 3.12.2 (`.python-version`: `3.12.2`)
- Docker Desktop or Docker Engine with Docker Compose

`nvm` and `pyenv` are optional. If installed, they can read the version files included in the project.

### First-time setup

Clone the repository into any directory and enter the project root. No user-specific absolute path is required.

```bash
git clone https://github.com/chaneepo/2026_ESW_HomeProtector.git
cd 2026_ESW_HomeProtector
```

On macOS/Linux, run:

```bash
./scripts/setup.sh
```

The script checks Node.js, runs `npm ci`, creates or reuses `.venv`, upgrades pip, and installs `requirements-dev.txt`. It is safe to run again when dependencies change.

On Windows PowerShell, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

The command components are:

- `powershell.exe`: starts Windows PowerShell
- `-NoProfile`: skips personal PowerShell profiles for a consistent setup
- `-ExecutionPolicy Bypass`: allows scripts for this process only and does not permanently change system policy
- `-File .\scripts\setup.ps1`: runs the setup script from the current project

`setup.ps1` verifies Node.js and npm and installs the frontend packages. It then looks for `py -3.12`, `python`, and `python3` in that order, creates `.venv\Scripts`, and installs `requirements-dev.txt`.

To perform each step manually on macOS/Linux:

```bash
# Select Node.js when using nvm
nvm install
nvm use

# Install frontend packages
npm install

# Create the Python environment
python3 -m venv .venv

# Activate on macOS/Linux
source .venv/bin/activate

# Install environment tooling and all development dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, perform the equivalent setup with:

```powershell
# Install frontend packages
npm install

# Create and activate the Python environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install environment tooling and all development dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Node.js packages are installed in the project's `node_modules`, not in the Python virtual environment. Both environments are local to the project and excluded from Git through `.gitignore`.

### Python dependency files

| File | Purpose | Main packages |
|---|---|---|
| `requirements.txt` | Runtime environment | FastAPI, pydantic-settings, SQLAlchemy, psycopg, NumPy, OpenCV contrib, pyserial |
| `requirements-dev.txt` | Development and tests | All runtime packages plus pytest, pytest-asyncio, Ruff, and mypy |

Most developers only need to install `requirements-dev.txt`. A device or deployment environment that needs runtime packages only can use:

```bash
python -m pip install -r requirements.txt
```

OpenCV contrib is selected because it includes ArUco and AprilTag marker support. `pyserial` is the initial serial-transport dependency for SO-ARM101 or ESP32; add a robot-specific SDK only after the hardware interface is confirmed.

SQLAlchemy provides the ORM layer and psycopg 3 connects it to PostgreSQL. Because `requirements-dev.txt` includes `requirements.txt`, normal development setup installs the PostgreSQL driver as well.

### PostgreSQL with Docker

PostgreSQL 17 runs as the `db` service in `compose.yaml`. Data is stored in the `postgres_data` Docker volume and survives container recreation. The host port binds only to `127.0.0.1` and is not exposed to the external network.

For the first setup, copy the environment template to a local `.env`. This file contains each developer's password and is excluded from Git.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Change the password in both `POSTGRES_PASSWORD` and `DATABASE_URL`, keeping the two values consistent, and then start the database.

```bash
docker compose up -d db
docker compose ps
```

View logs or open a database shell with:

```bash
docker compose logs -f db
docker compose exec db psql -U care_pack -d care_pack
```

Stop and restart it with:

```bash
docker compose stop db
docker compose start db
```

Use `docker compose down` to remove only the container. `docker compose down -v` also deletes the `postgres_data` volume and every database record, so use it only for an intentional full reset.

The FastAPI backend running on the host uses `localhost:5432` from `.env`. If the backend later becomes another Compose service, change the hostname from `localhost` to `db`.

### Database migrations and seed data

Create the current schema in an empty database or upgrade an existing development database:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Inspect the current revision and verify model/migration consistency:

```bash
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
```

Insert the explicit development and simulation seed of five locations, five items, two routines, and their assignments. The command is idempotent and is never run automatically at application startup.

```bash
python -m backend.app.seed
```

The seven implemented application tables are:

```text
locations, items, routines, routine_items, jobs, job_items, job_events
```

### Database tests and FastAPI health check

Tests create a separate database whose name ends in `_test`, verify migration round trips, constraints, relationships, idempotent seeding, and execution-history protection, and then remove that test database. They never modify the normal development database.

```bash
python -m pytest backend/tests -q
```

Start the FastAPI health-check server with:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/health` to verify database connectivity. The web UI uses in-memory mocks for item, routine, and job workflows. Database integration through business CRUD APIs is part of the development roadmap.

### Stopping and safely resetting the database

The normal stop command preserves all data:

```bash
docker compose stop db
```

Use `docker compose down` followed by `docker compose up -d db` to recreate only the container. Use the following full reset only when all development data may be deleted:

```bash
docker compose down -v
docker compose up -d db
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
```

The real `.env` file and PostgreSQL volume are not tracked by Git. Only `.env.example`, models, migrations, and seed code are tracked.

### Verify the environment

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

On macOS/Linux, `which python` should point to `.venv/bin/python` inside the current project. On Windows, `(Get-Command python).Source` should point to `.venv\Scripts\python.exe`. An active shell usually also displays `(.venv)` in the prompt.

### Daily workflow

macOS/Linux:

```bash
./scripts/dev.sh
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Each `dev` script verifies the operating-system-specific `.venv` and `node_modules`, activates Python, and starts the frontend. Open the local address printed by the development server. When FastAPI is implemented, its process can be added to the same scripts.

### Manage Python packages

Install packages only in the activated environment and prefer the `python -m pip` form.

```bash
python -m pip install <package-name>
python -m pip list
```

Record only direct, validated team dependencies in the appropriate requirements file. Do not commit temporary experiment packages until they are accepted. `.venv` is listed in `.gitignore` and must never be committed.

Verify the installed core packages with:

```bash
python -c "import cv2, fastapi, numpy, psycopg, serial, sqlalchemy; print('Python dependencies OK')"
python -m pytest --version
python -m ruff --version
python -m mypy --version
```

### Deactivate or rebuild

Leave the environment with:

```bash
deactivate
```

If the environment is damaged or the Python version changes, rebuild it as follows. This clears every package currently installed inside `.venv`.

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

### Build and run

Development:

```bash
npm run dev
```

Production build verification:

```bash
npm run build
npm run start
```

Activating the Python environment does not change the current Node.js frontend build.

## Current capabilities

- Dashboard and device status display
- PACK/SORT job simulation
- One injected PICK or VERIFY failure followed by recovery
- Simulated SO-ARM101 manual commands
- Simulated vision detection and 3×3 storage grid
- In-memory item management and job history
- UI emergency stop and manual reset

UI mock data resets on reload, while the independently operated PostgreSQL database persists its data. Hardware Raspbot control uses the device API; job and arm screens run in simulation.

## Repository structure

```text
app/          Application entry and layout
components/   Control-center shell and shared UI
views/        Feature views
store/        Global state and orchestration
services/     Domain service contracts and mock calls
mocks/        Initial data and simulation engine
backend/      FastAPI, SQLAlchemy models, Alembic migrations, and DB tests
scripts/      Unified setup and development commands for macOS/Linux and Windows
compose.yaml  PostgreSQL 17 Docker Compose configuration
types/        Shared TypeScript models
docs/ko/      Korean technical documentation
docs/en/      English technical documentation
```

## Documentation

- [Project Overview](../en/00_PROJECT_OVERVIEW.md)
- [System Architecture](../en/01_SYSTEM_ARCHITECTURE.md)
- [Frontend Structure](../en/02_FRONTEND_STRUCTURE.md)
- [Backend API Specification](../en/03_BACKEND_API_SPEC.md)
- [State Machine](../en/04_STATE_MACHINE.md)
- [Vision System Design](../en/05_VISION_DESIGN.md)
- [SO-ARM101 Interface](../en/06_SO_ARM101_INTERFACE.md)
- [Database Schema](../en/07_DATABASE_SCHEMA.md)
- [Simulation Mode](../en/08_SIMULATION_MODE.md)
- [Event Log Specification](../en/09_EVENT_LOG_SPEC.md)
- [Failure Recovery](../en/10_FAILURE_RECOVERY.md)
- [Development Roadmap](../en/11_DEVELOPMENT_ROADMAP.md)
- [Team Interface Guide](../en/12_TEAM_INTERFACE.md)

For Korean, see [README.ko.md](README.ko.md).
