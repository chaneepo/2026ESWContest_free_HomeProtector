# SO-ARM101 Interface

## 1. Current implementation

`services/armService.ts` simulates the following commands and always returns success after roughly 350 ms:

- `HOME`
- `SAFE`
- `GRIPPER_OPEN`
- `GRIPPER_CLOSE`
- `STOP`

No SO-ARM101 SDK, serial connection, motor status, or coordinate motion is connected. The `/api/arm/*` paths shown in the UI are proposed placeholders, not working routes.

## 2. Responsibility split

| Component | Responsibility |
|---|---|
| Execution Engine | Task sequence and retry policy |
| Arm Adapter | Translate semantic commands to the SO-ARM101 protocol |
| Robot Controller | Trajectory, joint limits, motor control, physical stop |
| Safety Layer | Workspace, speed, collision, and E-stop enforcement |

The upper layer should issue poses and semantic commands rather than motor IDs or raw pulse values.

## 3. Target commands

| Command | Purpose | Main parameters |
|---|---|---|
| `HOME` | Return to reference pose | speed |
| `SAFE` | Move to low-risk waiting pose | speed |
| `MOVE_TO_POSE` | Move to a target pose | x, y, z, roll, pitch, yaw, speed |
| `GRIPPER_OPEN` | Open gripper | width or preset |
| `GRIPPER_CLOSE` | Close gripper | force, width |
| `PICK` | Approach, grip, and lift | targetPose, graspProfile |
| `PLACE` | Approach, release, and retreat | targetPose, releaseProfile |
| `STOP` | Stop motion as quickly as supported | reason |
| `GET_STATUS` | Read pose, activity, and errors | none |

## 4. Command contract

```json
{
  "requestId":"req-004",
  "commandId":"cmd-001",
  "jobId":"job-001",
  "itemId":"item-medication",
  "command":"MOVE_TO_POSE",
  "parameters":{"frame":"robot_base","x":0.31,"y":0.10,"z":0.08,"unit":"m","speed":0.15},
  "timeoutMs":10000
}
```

Completion result:

```json
{
  "commandId":"cmd-001",
  "status":"SUCCESS",
  "startedAt":"2026-08-28T03:02:00Z",
  "completedAt":"2026-08-28T03:02:04Z",
  "finalPose":{"x":0.31,"y":0.10,"z":0.08,"unit":"m"},
  "error":null
}
```

Command acceptance and completion are separate. A successful HTTP response means `ACCEPTED`, not successful physical movement.

## 5. Status and errors

Recommended arm states are `OFFLINE`, `IDLE`, `MOVING`, `GRIPPING`, `STOPPING`, and `ERROR`.

| Error code | Meaning | Default response |
|---|---|---|
| `ARM_OFFLINE` | Communication unavailable | Block job start |
| `COMMAND_TIMEOUT` | No completion before deadline | Stop and inspect status |
| `OUT_OF_WORKSPACE` | Target is outside allowed workspace | Recompute; do not blindly retry |
| `JOINT_LIMIT` | Joint constraint violation | Change approach pose |
| `MOTION_BLOCKED` | Collision or obstruction | Stop and require inspection |
| `GRIP_NOT_DETECTED` | Pick could not be verified | Redetect and regrasp |
| `ESTOP_ACTIVE` | E-stop is active | Do not reset before physical release |

## 6. Basic pick-and-place sequence

`HOME → MOVE_TO_ITEM → GRIPPER_CLOSE → LIFT → MOVE_TO_TARGET → GRIPPER_OPEN → RETREAT → HOME`

Each step must confirm command completion, current pose, and error state. Where possible, verify PICK with at least two of gripper position, motor current, and vision. Verify PLACE with an independent signal such as bag weight.

## 7. Hardware integration checklist

- Connection and reconnection policy
- Fixed distance, angle, and speed units
- Joint and Cartesian workspace limits
- Ordering and request idempotency
- Worst-case STOP response time
- Safe behavior after communication loss
- Validated Home and Safe poses
- Recorded success rate over at least 100 repeated pick-and-place cycles

