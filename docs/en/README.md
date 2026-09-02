# CARE-PACK documentation

[Project home](../../README.md) · [Documentation index](../README.md) · [한국어](../ko/README.md)

Design documents include planned interfaces, not just completed features. Consult the root README for current implementation status.

## Document index

| Document | Related folder / guide |
|---|---|
| [Project overview](00_PROJECT_OVERVIEW.md) | [Project](../../README.md) |
| [System architecture](01_SYSTEM_ARCHITECTURE.md) | [Project](../../README.md) |
| [Frontend structure](02_FRONTEND_STRUCTURE.md) | [Web UI](../../views/README.md) |
| [Backend API specification](03_BACKEND_API_SPEC.md) | [Project](../../README.md) |
| [State machine](04_STATE_MACHINE.md) | [Project](../../README.md) |
| [Vision design](05_VISION_DESIGN.md) | [Project](../../README.md) |
| [SO-ARM101 interface](06_SO_ARM101_INTERFACE.md) | [Motor](../../motor/README.md) |
| [Database schema](07_DATABASE_SCHEMA.md) | [Backend](../../backend/README.md) |
| [Simulation mode](08_SIMULATION_MODE.md) | [Autonomy](../../autonomy/README.md) |
| [Event log specification](09_EVENT_LOG_SPEC.md) | [Project](../../README.md) |
| [Failure recovery](10_FAILURE_RECOVERY.md) | [Project](../../README.md) |
| [Development roadmap](11_DEVELOPMENT_ROADMAP.md) | [Project](../../README.md) |
| [Team interface guide](12_TEAM_INTERFACE.md) | [Project](../../README.md) |

## Implementation boundaries

- Manual Raspbot control is separate from simulated job and arm UI behavior.
- The existing motor tools support manual/recorded operations; they are not integrated perception-driven autonomy.
- `autonomy/` currently runs simulated observations and records virtual actuator commands only.
- The backend currently exposes `/health`; design API tables are not a list of implemented routes.
- Review the [safety limitations](../../chan/SAFETY_REVIEW.md) before hardware use.
