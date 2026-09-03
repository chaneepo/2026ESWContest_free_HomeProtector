# Simulation Mode

## 1. Purpose

Simulation mode validates UI behavior, state transitions, events, and recovery contracts without hardware. It does not demonstrate physical accuracy, timing, or safety.

## 2. Files

| Path | Role |
|---|---|
| `frontend/mocks/mockData.ts` | Initial device, item, detection, job, and event data |
| `frontend/mocks/simulationEngine.ts` | Steps, delays, cancellation, failure injection |
| `frontend/store/SystemProvider.tsx` | Per-item execution and state/event/history updates |
| `frontend/services/*.ts` | Asynchronous mock boundaries |

## 3. Current rules

- A job includes up to four enabled items.
- PACK targets `외출 가방` (outing bag).
- SORT uses each item's default destination.
- Each item runs `PLAN → DETECT → PICK → MOVE → PLACE → VERIFY`.
- DETECT, PICK, and MOVE wait about 1.1 seconds; other steps wait about 0.75 seconds.
- After all items succeed, job status is `SUCCESS` and system state is `COMPLETE`.
- A page reload resets current state and edited data.

## 4. Failure injection

The automatic view offers `NONE`, `PICK`, and `VERIFY`. The selected failure applies to the first item only, occurs once, enters `RECOVER`, and then succeeds on one retry.

Known limitations:

- No final `FAILED` path after retry exhaustion
- UI text says “up to two retries,” but the engine performs one retry
- No DETECT, MOVE, PLACE, or sensor-communication failure injection
- Delays and outcomes do not model physical device behavior

## 5. Cancellation and emergency stop

Stop sets an engine cancel flag. At the next cancellation check, the provider records job `CANCELLED` and execution `ERROR`. Emergency stop uses the same cancellation mechanism and additionally sets the arm/error and emergency-stop states. This validates UI flow only; it does not guarantee a physical stop.

## 6. Replacing it with real mode

`SystemMode` includes `REAL`, but there is no mode switch or real adapter. Migration should:

1. Preserve views and domain types.
2. Replace `frontend/services/*.ts` with REST/live clients.
3. Make the server Execution Engine authoritative.
4. Expose failure injection only in development.
5. Determine device state from real heartbeats.
6. Include `mode` in every execution event.

## 7. Recommended scenarios

- Normal PACK and SORT
- One PICK failure then success
- One VERIFY failure then success
- Stop and emergency stop from each state
- No enabled items
- Server state restoration after reload/reconnect
- Contract comparison between mock and physical adapters

