# Team Interface Guide

## 1. Purpose

This guide keeps frontend, backend, vision, robot, and sensor teams aligned on state, IDs, units, and ownership. It is a practical contract guide for integration boundaries, not an organization chart.

## 2. Ownership

| Team | Owns | Must provide |
|---|---|---|
| Frontend | Operator UI, input, state display | API requests, error UI, explicit mode label |
| Backend/Core | API, state machine, persistence, orchestration | Versioned contracts, idempotency, events |
| Vision | Detection, pose, calibration | Frame, confidence, calibration version, time |
| Robot | SO-ARM101 adapter, motion, safety state | ACK/completion, final pose, errors |
| Sensor/ESP32 | Loading and docking measurements | Unit, quality, sample time, connection state |
| Mobile robot | Future Razbot delivery and docking | Location, task handoff, docking result |
| QA/Safety | Scenarios, KPIs, hazard review | Results and release blockers |

## 3. Shared rules

- Every request and result uses `requestId` or an equivalent trace ID.
- Correlate jobs with `jobId`, items with `itemId`, and robot calls with `commandId`.
- Fix length and angle units in the contract and include units in payloads.
- Send time as UTC ISO 8601.
- Send enums as strings and do not silently change their meaning.
- Unknown enums must become an explicit error state, not an unhandled crash.
- Separate API success, command acceptance, motion completion, and physical verification.

## 4. Integration matrix

| Provider → consumer | Contract | Checks |
|---|---|---|
| Frontend → Backend | Job/manual request | Duplicate click, validation, 409 handling |
| Backend → Frontend | State and events | Reconnect, ordering, stale-state rejection |
| Core → Vision | Detection request | Item, deadline, coordinate frame |
| Vision → Core | Detection result | Frame, pose, confidence, calibration |
| Core → Arm | Robot command | Command ID, timeout, workspace |
| Arm → Core | ACK/completion/error | Actual completion time, final pose |
| Core → Sensor | Verification request | Threshold, sample window, job/item linkage |
| Sensor → Core | Measurement/decision | Unit, quality, timestamp |

## 5. Change management

1. Update documentation and TypeScript/OpenAPI schemas together.
2. Prefer backward-compatible field additions.
3. Version the API for field removal or enum semantic changes.
4. Run the same contract tests against mock and physical adapters.
5. Require joint approval for coordinate-frame, unit, and timeout changes.
6. Track a named owner for mismatches such as retry UI text versus engine behavior.

## 6. Integration review checklist

- Is this build clearly SIMULATION or REAL?
- Are new endpoints, commands, and event codes documented?
- Are normal, timeout, offline, and cancel responses covered?
- Does request replay execute physical motion only once?
- Do vision and robot use the same calibration version?
- Are sensor thresholds and sampling windows agreed?
- Does every team stop sending motion commands after E-stop?
- Can a failure be traced end-to-end with one job ID?

## 7. Definition of done

A feature is not done merely because it appears to work in the UI. Contract tests, failure scenarios, event tracing, physical-device verification where applicable, and documentation updates must all be complete.

