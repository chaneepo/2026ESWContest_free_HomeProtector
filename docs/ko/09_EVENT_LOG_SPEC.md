# 이벤트 로그 명세

## 1. 현재 구현

현재 `EventLog` 타입은 다음 필드를 가진다.

- `id`
- `timestamp`
- `level`: INFO, SUCCESS, WARNING, ERROR
- `source`: SYSTEM, VISION, ARM, ESP32, RAZBOT
- `message`
- 선택적 `jobId`

프론트엔드 이벤트는 `services/eventService.ts`와 `SystemProvider`가 메모리에 추가한다. 백엔드에는 별도로 `job_events` 영구 테이블과 `event_type`, `job_item_id`, `step`, `device`, `severity`, `metadata_json` 모델이 구현되어 있지만 프론트엔드 서비스와 아직 연결되지 않았다.

## 2. 목표 API 페이로드

```json
{
  "id": "evt-001",
  "occurredAt": "2026-08-28T03:02:04Z",
  "level": "SUCCESS",
  "source": "ARM",
  "eventCode": "ARM_COMMAND_COMPLETED",
  "message": "HOME 명령이 완료되었습니다.",
  "mode": "SIMULATION",
  "jobId": "job-001",
  "itemId": "item-medication",
  "commandId": "cmd-001",
  "metadata": {"durationMs": 4200}
}
```

`message`는 사람이 읽는 표시용이고 자동 처리와 통계에는 `eventCode`를 사용한다.

## 3. 이벤트 코드 규칙

형식은 `{SOURCE}_{SUBJECT}_{RESULT}`를 권장하며 한번 배포한 코드는 의미를 변경하지 않는다.

| 코드 | 레벨 | 의미 | 상태 |
|---|---|---|---|
| `SYSTEM_READY` | INFO | 시스템 준비 완료 | 계획 코드 |
| `JOB_CREATED` | INFO | 작업 생성 | 계획 코드 |
| `JOB_STARTED` | INFO | 작업 실행 시작 | 계획 코드 |
| `JOB_COMPLETED` | SUCCESS | 모든 필수 물품 검증 완료 | 계획 코드 |
| `JOB_CANCELLED` | WARNING | 사용자/안전 정책에 의한 취소 | 계획 코드 |
| `ITEM_DETECTED` | SUCCESS | 대상 물품 인식 | 계획 코드 |
| `ITEM_NOT_FOUND` | WARNING | 대상 물품 미검출 | 계획 코드 |
| `ARM_COMMAND_ACCEPTED` | INFO | 로봇 명령 접수 | 계획 코드 |
| `ARM_COMMAND_COMPLETED` | SUCCESS | 로봇 명령 완료 | 계획 코드 |
| `PICK_FAILED` | WARNING | 파지 검증 실패 | 계획 코드 |
| `PLACE_FAILED` | WARNING | 놓기 검증 실패 | 계획 코드 |
| `VERIFY_SUCCEEDED` | SUCCESS | 독립 센서 검증 성공 | 계획 코드 |
| `VERIFY_FAILED` | WARNING | 독립 센서 검증 실패 | 계획 코드 |
| `RECOVERY_STARTED` | WARNING | 복구 절차 시작 | 계획 코드 |
| `RETRY_EXHAUSTED` | ERROR | 재시도 예산 소진 | 계획 코드 |
| `EMERGENCY_STOP_ACTIVATED` | ERROR | 비상정지 활성화 | 계획 코드 |
| `DEVICE_OFFLINE` | ERROR | 장치 연결 끊김 | 계획 코드 |

현재 화면 이벤트는 자유 형식의 한국어 메시지로만 생성되므로 위 코드와 직접 대응하지 않는다.

## 4. 기록 시점

- 작업 생성·시작·완료·실패·취소
- 모든 상태 진입과 종료
- 로봇 명령 접수·시작·완료·오류
- 비전 검출 결과와 좌표 변환 실패
- 센서 측정과 검증 판정
- 재시도 결정과 복구 결과
- 장치 연결 상태 변경
- 설정 변경과 운영자 reset

고빈도 원시 센서 데이터는 이벤트 로그에 모두 넣지 않고 측정 저장소에 분리하고, 이벤트에는 판정에 사용한 요약과 참조 ID를 기록한다.

## 5. 추적성과 보안

- 하나의 작업은 동일한 `jobId`로 연결한다.
- 물품 단계는 `itemId`, 로봇 호출은 `commandId`를 포함한다.
- 장치와 서버의 시각 동기화 상태를 관리한다.
- 이벤트는 append-only로 저장하고 관리자 작업도 감사 이벤트로 남긴다.
- 로그에 비밀번호, 토큰, 불필요한 개인정보를 기록하지 않는다.
- 사용자 표시 문구와 개발 진단 metadata를 분리한다.

## 6. 조회와 보존

기본 필터는 시간, 레벨, source, eventCode, jobId, itemId다. PostgreSQL의 `job_events` 테이블은 작업·작업 물품·이벤트 코드·생성 시각 인덱스를 제공한다. CSV/JSON 내보내기와 보존 기간, 개인정보 삭제 정책은 운영 환경과 대회 시연 환경을 구분해 추가한다.
