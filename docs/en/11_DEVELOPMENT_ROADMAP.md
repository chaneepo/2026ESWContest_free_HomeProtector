# Development Roadmap

## 1. Priority

The first proof required with the available equipment is:

> The camera finds an item → SO-ARM101 picks it → places it in the bag → the system verifies that it is really there.

This loop's repeatability and safety take priority over user apps, Razbot, and weather features.

## 2. Phases

| Phase | Deliverable | Current status | Completion criterion |
|---|---|---|---|
| 1. Control-center UI | Korean dashboard and feature views | Complete | Six primary views navigable |
| 2. Execution simulation | State flow, events, failure injection | Complete with limits | Normal and recovery demo works |
| 3. SO-ARM101 control | Home, pose, gripper, stop | Planned | Repeated real commands and errors observed |
| 4. Marker vision | Marker ID and camera pose | Planned | Target accuracy in fixed setup |
| 5. Transform and pick/place | Robot pose connected to motion | Planned | Repeated item transfer succeeds |
| 6. Sensor verification | Detect bag weight change | Planned | Distinguish PLACE from physical load success |
| 7. Execution Engine | Server state machine, recovery, persistence | Planned | Restore state and exhaust retries correctly |
| 8. Planning Engine | Rules from purpose, user, weather | Planned | Generate items with reasons/requirements |
| 9. Return-home sorting | Restore items to default storage | Partial UI simulation | Real SORT differs from PACK and is verified |
| 10. Razbot integration | Mobile-platform task handoff | Planned | Dock and handoff succeed |
| 11. Room delivery | Room-level delivery | Planned | Delivery and return verified |
| 12. Disaster Priority Mode | Prioritized emergency supplies | Planned | Safety and priority policies tested |
| 13. User/guardian apps | Schedules, alerts, remote status | Planned | Role-specific critical flows complete |
| 14. Integrated testing | Endurance, failure, and safety tests | Planned | Defined KPIs and safety gates pass |

## 3. Recommended next sprint

1. Confirm the SO-ARM101 SDK/transport and write a minimal adapter.
2. Execute real Home, Safe, gripper, and STOP commands; measure stop latency.
3. Detect three markers with a fixed camera.
4. Perform the first pick-and-place using manually measured fixed poses.
5. Record every command and verification as structured events.

User accounts, schedules, weather, and Razbot should remain out of this sprint.

## 4. Key metrics

- Detection rate and pose error
- Pick success, place success, verification accuracy
- Mean time per item
- Worst time from STOP request to physical stop
- Recovery success rate by failure class
- Communication loss and data loss during endurance runs

## 5. Release gates for real mode

- Physical E-stop and software STOP tested
- Safe workspace and speed limits enforced
- Calibration version is visible and verifiable
- Persistent events support root-cause tracing
- SIMULATION and REAL modes are unmistakably labeled
- Operators know the manual recovery procedure

