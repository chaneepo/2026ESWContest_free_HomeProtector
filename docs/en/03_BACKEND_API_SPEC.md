# Backend API Specification

## 1. Status and scope

The repository now includes a FastAPI server foundation, PostgreSQL sessions, and `GET /health`. Every business endpoint below remains a **planned contract**, and current `services/*.ts` modules still call in-memory mocks. Implement business routes under the versioned `/api/v1` JSON API and restrict device commands to authenticated, authorized clients.

## 2. Common conventions

- Content-Type: `application/json`
- Time: ISO 8601 UTC strings
- IDs: server-generated unique strings
- Mutating requests include `requestId` for idempotency.
- Standard error body:

```json
{
  "error": {
    "code": "JOB_ALREADY_RUNNING",
    "message": "Another job is already running.",
    "requestId": "req-20260828-001"
  }
}
```

Primary error statuses are `400` invalid input, `404` not found, `409` state conflict, `422` domain validation, and `503` unavailable device.

## 3. Endpoint inventory

| Status | Method | Path | Purpose |
|---|---|---|---|
| Implemented | GET | `/health` | Verify FastAPI and PostgreSQL connectivity |
| Planned | GET | `/api/v1/system/status` | System, device, and execution status |
| Planned | POST | `/api/v1/system/emergency-stop` | Request emergency stop |
| Planned | POST | `/api/v1/system/reset` | Clear error after safety checks |
| Planned | GET | `/api/v1/jobs` | List jobs |
| Planned | POST | `/api/v1/jobs` | Create PACK/SORT job |
| Planned | GET | `/api/v1/jobs/{jobId}` | Read job detail |
| Planned | POST | `/api/v1/jobs/{jobId}/start` | Start waiting job |
| Planned | POST | `/api/v1/jobs/{jobId}/cancel` | Cancel or safely stop job |
| Planned | GET | `/api/v1/items` | List items |
| Planned | POST | `/api/v1/items` | Create item |
| Planned | PATCH | `/api/v1/items/{itemId}` | Update or enable item |
| Planned | DELETE | `/api/v1/items/{itemId}` | Delete item |
| Planned | POST | `/api/v1/vision/detect` | Request a detection |
| Planned | GET | `/api/v1/vision/detections` | Read recent detections |
| Planned | POST | `/api/v1/arm/commands` | Submit generic robot command |
| Planned | GET | `/api/v1/arm/status` | Read robot status |
| Planned | POST | `/api/v1/arm/home` | HOME convenience command |
| Planned | POST | `/api/v1/arm/safe` | SAFE convenience command |
| Planned | POST | `/api/v1/arm/gripper/open` | Open gripper |
| Planned | POST | `/api/v1/arm/gripper/close` | Close gripper |
| Planned | POST | `/api/v1/arm/stop` | Request immediate robot stop |
| Planned | GET | `/api/v1/events` | Filter event logs |

The `/api/arm/*` paths in `services/armService.ts` are display-only drafts, not working server routes. A backend must standardize them or document a compatibility layer.

## 4. System API

`GET /system/status` has no request body:

```json
{
  "mode":"SIMULATION",
  "executionState":"IDLE",
  "emergencyStop":false,
  "devices":{"arm":"ONLINE","vision":"ONLINE","esp32":"OFFLINE","razbot":"OFFLINE"},
  "updatedAt":"2026-08-28T03:00:00Z"
}
```

`POST /system/emergency-stop` and `/system/reset` accept:

```json
{"requestId":"req-001","reason":"operator_button"}
```

They return `202 Accepted` with the new state. Reset returns `409 SAFETY_CONDITION_NOT_MET` if safety conditions are not satisfied.

## 5. Job API

`POST /jobs` request:

```json
{
  "requestId":"req-002",
  "type":"PACK",
  "itemIds":["item-medication","item-key"],
  "destination":"outing-bag",
  "simulation":true
}
```

Response `201 Created`:

```json
{
  "id":"job-001",
  "type":"PACK",
  "status":"WAITING",
  "executionState":"IDLE",
  "progress":0,
  "items":[{"itemId":"item-medication","name":"Medication","status":"WAITING","retryCount":0}]
}
```

`start` and `cancel` accept `{ "requestId": "..." }` and return `202`. Conflicts include `409 JOB_ALREADY_RUNNING` and `409 INVALID_JOB_STATE`. `GET /jobs` should support `status`, `type`, `from`, `to`, and `cursor` filters.

## 6. Item API

Create request:

```json
{
  "name":"Medication",
  "category":"medicine",
  "markerId":"01",
  "storageLocation":"A1",
  "defaultDestination":"outing-bag",
  "enabled":true
}
```

Create returns `201`, PATCH returns `200`, and DELETE returns `204`. Conflicts include `409 DUPLICATE_MARKER_ID` and `409 ITEM_IN_USE`.

## 7. Vision API

`POST /vision/detect`:

```json
{"requestId":"req-003","itemId":"item-medication","coordinateFrame":"robot_base"}
```

Response:

```json
{
  "detectionId":"det-001",
  "itemId":"item-medication",
  "markerId":"01",
  "found":true,
  "confidence":0.98,
  "cameraPose":{"x":0.12,"y":-0.04,"z":0.58,"unit":"m"},
  "robotPose":{"x":0.31,"y":0.10,"z":0.08,"unit":"m"},
  "capturedAt":"2026-08-28T03:01:00Z"
}
```

A normal miss may return `found:false`. Device failures use `503 CAMERA_UNAVAILABLE`; missing calibration uses `422 CALIBRATION_REQUIRED`.

## 8. Robot API

Generic request:

```json
{
  "requestId":"req-004",
  "jobId":"job-001",
  "command":"MOVE_TO_POSE",
  "parameters":{"x":0.31,"y":0.10,"z":0.08,"unit":"m","speed":0.15},
  "timeoutMs":10000
}
```

Response `202 Accepted`:

```json
{"commandId":"cmd-001","status":"ACCEPTED","acceptedAt":"2026-08-28T03:02:00Z"}
```

Acceptance is not motion completion. Command and error details are defined in [SO-ARM101 Interface](06_SO_ARM101_INTERFACE.md).

## 9. Events and live updates

`GET /events?jobId=job-001&level=ERROR&source=ARM&cursor=...` returns events and a next cursor. A future `/ws/system` WebSocket or SSE channel may reuse the [Event Log Specification](09_EVENT_LOG_SPEC.md), but neither transport is currently implemented.
