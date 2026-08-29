# Event Log Specification

## 1. Current implementation

The current `EventLog` type contains `id`, `timestamp`, `level`, `source`, `message`, and optional `jobId`. Levels are INFO, SUCCESS, WARNING, and ERROR; sources are SYSTEM, VISION, ARM, ESP32, and RAZBOT. Events live only in memory. There are no standardized event codes, item IDs, metadata, or persistence.

## 2. Target schema

```json
{
  "id":"evt-001",
  "occurredAt":"2026-08-28T03:02:04Z",
  "level":"SUCCESS",
  "source":"ARM",
  "eventCode":"ARM_COMMAND_COMPLETED",
  "message":"The HOME command completed.",
  "mode":"SIMULATION",
  "jobId":"job-001",
  "itemId":"item-medication",
  "commandId":"cmd-001",
  "metadata":{"durationMs":4200}
}
```

Use `message` for human display and `eventCode` for automation and analytics.

## 3. Event-code rules

Use stable `{SOURCE}_{SUBJECT}_{RESULT}`-style names and never change the meaning of a published code.

| Code | Level | Meaning | Status |
|---|---|---|---|
| `SYSTEM_READY` | INFO | System ready | Planned code |
| `JOB_CREATED` | INFO | Job created | Planned code |
| `JOB_STARTED` | INFO | Execution started | Planned code |
| `JOB_COMPLETED` | SUCCESS | All required items verified | Planned code |
| `JOB_CANCELLED` | WARNING | Cancelled by user or safety policy | Planned code |
| `ITEM_DETECTED` | SUCCESS | Target item detected | Planned code |
| `ITEM_NOT_FOUND` | WARNING | Target item not found | Planned code |
| `ARM_COMMAND_ACCEPTED` | INFO | Robot accepted command | Planned code |
| `ARM_COMMAND_COMPLETED` | SUCCESS | Robot command completed | Planned code |
| `PICK_FAILED` | WARNING | Pick verification failed | Planned code |
| `PLACE_FAILED` | WARNING | Placement verification failed | Planned code |
| `VERIFY_SUCCEEDED` | SUCCESS | Independent verification passed | Planned code |
| `VERIFY_FAILED` | WARNING | Independent verification failed | Planned code |
| `RECOVERY_STARTED` | WARNING | Recovery started | Planned code |
| `RETRY_EXHAUSTED` | ERROR | Retry budget exhausted | Planned code |
| `EMERGENCY_STOP_ACTIVATED` | ERROR | Emergency stop active | Planned code |
| `DEVICE_OFFLINE` | ERROR | Device disconnected | Planned code |

Current UI events are free-form Korean messages and do not directly implement these codes.

## 4. Required event points

- Job creation, start, completion, failure, cancellation
- State entry and exit
- Robot command acceptance, start, completion, error
- Vision result and coordinate-transform failure
- Sensor measurement and verification decision
- Retry decision and recovery result
- Device connection-state change
- Configuration change and operator reset

Keep high-frequency raw sensor samples in a measurement store; log the decision summary and reference ID in the event stream.

## 5. Traceability and security

- Correlate a job with `jobId`, item work with `itemId`, and robot calls with `commandId`.
- Maintain clock synchronization across server and devices.
- Store events append-only and audit administrative actions.
- Never record passwords, tokens, or unnecessary personal data.
- Separate user-facing text from diagnostic metadata.

## 6. Query and retention

Support filters for time, level, source, eventCode, jobId, and itemId. The SQLite MVP can index these fields and offer CSV/JSON export. Define separate retention rules for competition demos and operational deployments.

