# CARE-PACK Control Center

CARE-PACK plans items for an outing, uses a robot arm to move them into a bag, and verifies that loading physically succeeded. This repository currently contains the Korean control-center UI and a pre-hardware simulation.

> Robot, vision, and sensor states shown in the UI are simulated. The physical SO-ARM101, camera, ESP32, backend, and database are not connected yet.

## Development environment setup

The current web frontend runs on Node.js. The Python virtual environment isolates packages for the future FastAPI backend, OpenCV vision pipeline, and SO-ARM101 controller from the system Python installation.

### Requirements

- Node.js 22.13 or newer (`.nvmrc`: `22.13.0`)
- npm
- Python 3.12.2 (`.python-version`: `3.12.2`)

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
| `requirements.txt` | Runtime environment | FastAPI, pydantic-settings, SQLAlchemy, NumPy, OpenCV contrib, pyserial |
| `requirements-dev.txt` | Development and tests | All runtime packages plus pytest, pytest-asyncio, Ruff, and mypy |

Most developers only need to install `requirements-dev.txt`. A device or deployment environment that needs runtime packages only can use:

```bash
python -m pip install -r requirements.txt
```

OpenCV contrib is selected because it includes ArUco and AprilTag marker support. `pyserial` is the initial serial-transport dependency for SO-ARM101 or ESP32; add a robot-specific SDK only after the hardware interface is confirmed.

SQLAlchemy remains the database-neutral layer. No SQLite, PostgreSQL, or other database driver is installed until the actual database is selected; add that driver through a separate requirements file later.

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
python -c "import cv2, fastapi, numpy, serial, sqlalchemy; print('Python dependencies OK')"
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

All data resets on reload. No real devices or APIs are controlled.

## Repository structure

```text
app/          Application entry and layout
components/   Control-center shell and shared UI
views/        Feature views
store/        Global state and orchestration
services/     Domain service contracts and mock calls
mocks/        Initial data and simulation engine
scripts/      Unified setup and development commands for macOS/Linux and Windows
types/        Shared TypeScript models
docs/ko/      Korean technical documentation
docs/en/      English technical documentation
```

## Documentation

- [Project Overview](docs/en/00_PROJECT_OVERVIEW.md)
- [System Architecture](docs/en/01_SYSTEM_ARCHITECTURE.md)
- [Frontend Structure](docs/en/02_FRONTEND_STRUCTURE.md)
- [Backend API Specification](docs/en/03_BACKEND_API_SPEC.md)
- [State Machine](docs/en/04_STATE_MACHINE.md)
- [Vision System Design](docs/en/05_VISION_DESIGN.md)
- [SO-ARM101 Interface](docs/en/06_SO_ARM101_INTERFACE.md)
- [Database Schema](docs/en/07_DATABASE_SCHEMA.md)
- [Simulation Mode](docs/en/08_SIMULATION_MODE.md)
- [Event Log Specification](docs/en/09_EVENT_LOG_SPEC.md)
- [Failure Recovery](docs/en/10_FAILURE_RECOVERY.md)
- [Development Roadmap](docs/en/11_DEVELOPMENT_ROADMAP.md)
- [Team Interface Guide](docs/en/12_TEAM_INTERFACE.md)

For Korean, see [README.ko.md](README.ko.md).
