# SO-ARM101 인터페이스

## 1. 현재 구현

`services/armService.ts`는 다음 수동 명령을 약 350ms 지연 후 항상 성공으로 반환하는 시뮬레이션이다.

- `HOME`
- `SAFE`
- `GRIPPER_OPEN`
- `GRIPPER_CLOSE`
- `STOP`

실제 SO-ARM101 SDK, 시리얼 포트, 모터 상태, 좌표 이동은 연결되어 있지 않다. UI에 표시되는 `/api/arm/*` 경로도 구현된 서버 API가 아니라 향후 계약 초안이다.

## 2. 책임 분리

| 구성요소 | 책임 |
|---|---|
| Execution Engine | 수행할 작업과 순서 결정, 재시도 정책 |
| Arm Adapter | 상위 명령을 SO-ARM101 SDK/프로토콜로 변환 |
| Robot Controller | 궤적, 관절 제한, 모터 제어, 실제 정지 |
| Safety Layer | 작업 공간, 속도, 충돌, E-stop 강제 |

상위 시스템은 모터 번호나 펄스 값을 직접 다루지 않고 pose와 의미 기반 명령을 사용한다.

## 3. 목표 명령 집합

| 명령 | 목적 | 주요 파라미터 |
|---|---|---|
| `HOME` | 기준 자세로 복귀 | speed |
| `SAFE` | 충돌 위험이 낮은 대기 자세 | speed |
| `MOVE_TO_POSE` | 지정 pose로 이동 | x, y, z, roll, pitch, yaw, speed |
| `GRIPPER_OPEN` | 그리퍼 열기 | width 또는 preset |
| `GRIPPER_CLOSE` | 그리퍼 닫기 | force, width |
| `PICK` | 접근·파지·들어올리기 복합 동작 | targetPose, graspProfile |
| `PLACE` | 접근·놓기·후퇴 복합 동작 | targetPose, releaseProfile |
| `STOP` | 가능한 즉시 운동 정지 | reason |
| `GET_STATUS` | 위치·상태·오류 조회 | 없음 |

## 4. 명령 계약

```json
{
  "requestId": "req-004",
  "commandId": "cmd-001",
  "jobId": "job-001",
  "itemId": "item-medication",
  "command": "MOVE_TO_POSE",
  "parameters": {
    "frame": "robot_base",
    "x": 0.31,
    "y": 0.10,
    "z": 0.08,
    "unit": "m",
    "speed": 0.15
  },
  "timeoutMs": 10000
}
```

완료 결과:

```json
{
  "commandId": "cmd-001",
  "status": "SUCCESS",
  "startedAt": "2026-08-28T03:02:00Z",
  "completedAt": "2026-08-28T03:02:04Z",
  "finalPose": {"x":0.31,"y":0.10,"z":0.08,"unit":"m"},
  "error": null
}
```

명령 접수와 완료는 분리한다. HTTP 요청 성공은 `ACCEPTED`일 뿐 로봇 동작 성공이 아니다.

## 5. 상태 및 오류

권장 로봇 상태는 `OFFLINE`, `IDLE`, `MOVING`, `GRIPPING`, `STOPPING`, `ERROR`다.

| 오류 코드 | 의미 | 기본 대응 |
|---|---|---|
| `ARM_OFFLINE` | 통신 불가 | 작업 시작 차단 |
| `COMMAND_TIMEOUT` | 제한 시간 내 완료 안 됨 | 정지 후 상태 확인 |
| `OUT_OF_WORKSPACE` | 목표가 작업 범위 밖 | 좌표 재계산, 자동 재시도 금지 |
| `JOINT_LIMIT` | 관절 제한 위반 | 접근 자세 변경 |
| `MOTION_BLOCKED` | 충돌 또는 구동 방해 | 정지, 운영자 확인 |
| `GRIP_NOT_DETECTED` | 파지 결과 미확인 | 재인식 후 재파지 |
| `ESTOP_ACTIVE` | E-stop 작동 | 물리 해제 전 reset 금지 |

## 6. 기본 pick & place 순서

`HOME → MOVE_TO_ITEM → GRIPPER_CLOSE → LIFT → MOVE_TO_TARGET → GRIPPER_OPEN → RETREAT → HOME`

각 단계는 명령 완료, 현재 pose, 오류 상태를 확인한 후 다음 단계로 넘어간다. `PICK` 성공은 가능하면 그리퍼 위치·전류·비전 중 둘 이상의 신호로 검증하고, `PLACE` 성공은 가방 센서 등 독립 신호로 검증한다.

## 7. 실장비 연결 체크리스트

- 장치 연결과 재연결 정책
- 좌표·각도·속도 단위 고정
- 관절/작업 공간 제한
- 명령 순서 보장과 중복 request 처리
- STOP의 최악 응답 시간 측정
- 통신 단절 시 안전 동작
- Home과 Safe pose 현장 검증
- 최소 100회 반복 pick & place 성공률 기록

