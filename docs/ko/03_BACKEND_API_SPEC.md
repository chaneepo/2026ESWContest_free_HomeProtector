# 백엔드 API 명세

## 1. 상태와 범위

현재 저장소에는 FastAPI 서버 기반, PostgreSQL 세션과 `GET /health`가 구현되어 있다. 아래 업무 API는 모두 **계획된 계약**이며 `services/*.ts`는 아직 메모리 mock을 사용한다. 실제 구현 시 `/api/v1` 버전 경로와 JSON을 사용하고 장치 호출은 인증된 내부 서비스만 허용한다.

## 2. 공통 규칙

- Content-Type: `application/json`
- 시간: ISO 8601 UTC 문자열
- ID: 서버가 생성하는 고유 문자열
- 상태 변경 요청은 중복 실행을 막기 위한 `requestId`를 포함
- 오류 본문 예시:

```json
{
  "error": {
    "code": "JOB_ALREADY_RUNNING",
    "message": "이미 실행 중인 작업이 있습니다.",
    "requestId": "req-20260828-001"
  }
}
```

주요 HTTP 상태는 `400` 입력 오류, `404` 미존재, `409` 상태 충돌, `422` 도메인 검증 실패, `503` 장치 사용 불가다.

## 3. 엔드포인트 목록

| 상태 | 메서드 | 경로 | 목적 |
|---|---|---|---|
| 구현 | GET | `/health` | FastAPI와 PostgreSQL 연결 상태 확인 |
| 계획 | GET | `/api/v1/system/status` | 시스템·장치·현재 상태 조회 |
| 계획 | POST | `/api/v1/system/emergency-stop` | 비상정지 요청 |
| 계획 | POST | `/api/v1/system/reset` | 안전 확인 후 오류 상태 해제 |
| 계획 | GET | `/api/v1/jobs` | 작업 목록 조회 |
| 계획 | POST | `/api/v1/jobs` | PACK/SORT 작업 생성 |
| 계획 | GET | `/api/v1/jobs/{jobId}` | 작업 상세 조회 |
| 계획 | POST | `/api/v1/jobs/{jobId}/start` | 대기 작업 시작 |
| 계획 | POST | `/api/v1/jobs/{jobId}/cancel` | 작업 취소 또는 안전 중지 |
| 계획 | GET | `/api/v1/items` | 물품 목록 조회 |
| 계획 | POST | `/api/v1/items` | 물품 등록 |
| 계획 | PATCH | `/api/v1/items/{itemId}` | 물품 수정·활성화 |
| 계획 | DELETE | `/api/v1/items/{itemId}` | 물품 삭제 |
| 계획 | POST | `/api/v1/vision/detect` | 단일 인식 요청 |
| 계획 | GET | `/api/v1/vision/detections` | 최근 인식 결과 조회 |
| 계획 | POST | `/api/v1/arm/commands` | 일반 로봇 명령 요청 |
| 계획 | GET | `/api/v1/arm/status` | 로봇 상태 조회 |
| 계획 | POST | `/api/v1/arm/home` | HOME 편의 명령 |
| 계획 | POST | `/api/v1/arm/safe` | SAFE 위치 편의 명령 |
| 계획 | POST | `/api/v1/arm/gripper/open` | 그리퍼 열기 |
| 계획 | POST | `/api/v1/arm/gripper/close` | 그리퍼 닫기 |
| 계획 | POST | `/api/v1/arm/stop` | 로봇 즉시 중지 요청 |
| 계획 | GET | `/api/v1/events` | 이벤트 필터 조회 |

`services/armService.ts`에 적힌 `/api/arm/*` 경로는 프론트엔드에 표시하기 위한 초안이며 실제 서버 라우트가 아니다. 서버 구현 시 위 버전 경로로 통일하거나 호환 정책을 명시해야 한다.

## 4. 시스템 API

### `GET /system/status`

요청 본문은 없다. 응답은 모드, 실행 상태, 장치 연결 상태, 비상정지 여부를 포함한다.

```json
{
  "mode": "SIMULATION",
  "executionState": "IDLE",
  "emergencyStop": false,
  "devices": {"arm": "ONLINE", "vision": "ONLINE", "esp32": "OFFLINE", "razbot": "OFFLINE"},
  "updatedAt": "2026-08-28T03:00:00Z"
}
```

### `POST /system/emergency-stop`, `POST /system/reset`

```json
{"requestId":"req-001","reason":"operator_button"}
```

성공 시 `202 Accepted`와 새 실행 상태를 반환한다. `reset`은 물리 안전 조건이 충족되지 않으면 `409 SAFETY_CONDITION_NOT_MET`를 반환한다.

## 5. 작업 API

### `POST /jobs`

```json
{
  "requestId": "req-002",
  "type": "PACK",
  "itemIds": ["item-medication", "item-key"],
  "destination": "외출 가방",
  "simulation": true
}
```

응답 `201 Created`:

```json
{
  "id": "job-001",
  "type": "PACK",
  "status": "WAITING",
  "executionState": "IDLE",
  "progress": 0,
  "items": [
    {"itemId":"item-medication","name":"약통","status":"WAITING","retryCount":0}
  ]
}
```

`start`와 `cancel`은 `{ "requestId": "..." }`를 받고 `202 Accepted`를 반환한다. 이미 실행 중이면 `409 JOB_ALREADY_RUNNING`, 종료된 작업을 시작하면 `409 INVALID_JOB_STATE`다. `GET /jobs`는 `status`, `type`, `from`, `to`, `cursor` 필터를 지원하도록 설계한다.

## 6. 물품 API

등록 요청:

```json
{
  "name":"약통",
  "category":"의약품",
  "markerId":"01",
  "storageLocation":"A1",
  "defaultDestination":"외출 가방",
  "enabled":true
}
```

등록은 `201`, 수정은 변경할 필드만 보내고 `200`, 삭제는 `204`를 반환한다. 중복 marker는 `409 DUPLICATE_MARKER_ID`, 실행 중 작업에서 참조하는 물품 삭제는 `409 ITEM_IN_USE`다.

## 7. 비전 API

`POST /vision/detect` 요청:

```json
{"requestId":"req-003","itemId":"item-medication","coordinateFrame":"robot_base"}
```

응답:

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

인식 실패는 정상 응답의 `found:false`로 표현할 수 있고, 카메라 자체 오류는 `503 CAMERA_UNAVAILABLE`, 보정 미완료는 `422 CALIBRATION_REQUIRED`다.

## 8. 로봇 API

일반 명령 요청:

```json
{
  "requestId":"req-004",
  "jobId":"job-001",
  "command":"MOVE_TO_POSE",
  "parameters":{"x":0.31,"y":0.10,"z":0.08,"unit":"m","speed":0.15},
  "timeoutMs":10000
}
```

응답 `202 Accepted`:

```json
{"commandId":"cmd-001","status":"ACCEPTED","acceptedAt":"2026-08-28T03:02:00Z"}
```

상세 명령·오류는 [SO-ARM101 인터페이스](06_SO_ARM101_INTERFACE.md)를 따른다. 편의 엔드포인트는 공통 요청 ID만 받고 동일한 명령 응답을 반환한다.

## 9. 이벤트 API와 실시간 갱신

`GET /events?jobId=job-001&level=ERROR&source=ARM&cursor=...`는 이벤트 배열과 다음 cursor를 반환한다. 실시간 전송은 향후 `/ws/system` WebSocket 또는 SSE로 설계할 수 있으나 현재 구현되지 않았다. 전송 페이로드는 [이벤트 로그 명세](09_EVENT_LOG_SPEC.md)의 표준 스키마를 재사용한다.
