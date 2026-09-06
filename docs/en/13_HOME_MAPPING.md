# Raspbot home mapping simulation

This Korean UI demonstrates robot-vacuum-style exploration, room analysis, destination navigation, and docking on a fixed example floor plan. It is not real SLAM, vision classification, LiDAR sensing, or hardware control.

## Workflow

Open **라즈봇 · 집 지도**, select **집 탐색 시작**, and use the 1×/2×/4× playback controls. Initially the complete floor plan is explicitly labeled as a preview. During exploration only sensed cells are revealed. After exploration, choose a room and start simulated navigation, return to the dock, or restrict study access. Restrictions cannot be changed during an active/paused route or enabled while the robot is inside the study.

Navigation pauses when switching app pages, losing window focus, hiding the document, or receiving a global emergency stop. Resuming requires user action. State is preserved across app-page navigation, but refresh/reset clears it. There is no database persistence.

## Model and metrics

- Fixed 28×30 grid at 0.4m/cell. The supplied reference plan informs the central living/dining area, left kitchen/study, right bedrooms/bathrooms, and lower entrance. This is a simplified layout, not a dimensionally accurate reproduction. Names, furniture, and categories remain predefined demo data.
- The UI draws continuous colored room regions and wall contours, not grid cells. Shared cell edges are removed and the remaining boundaries are traced into vector paths. The grid remains internal to navigation and sensing.
- Coordinate-seeded pixel steps and sparse scan flecks add synthetic texture to walls and furniture. Boundary displacement is capped at approximately 0.334 cells. This is a deterministic display effect, not measured sensor uncertainty; it never changes paths, collision checks, or coverage.
- Exploration uses a deterministic traversal of the known example map, not autonomous exploration of an unknown real environment.
- Simulated rays extend up to 4.5 cells and stop at the first wall/furniture cell. Contact with a furniture boundary exposes its predefined demo annotation.
- Coverage and room completion count discovered traversable cells; simulated usable area is traversable cells × 0.16m², not measured building area.
- Destination paths use four-neighbor shortest paths excluding walls, furniture, and restricted rooms. Real footprint, turning radius, stopping distance, localization uncertainty, and dynamic obstacles are not modeled.
- Simulated travel distance counts traversed cells × 0.4m, not hardware odometry.

## Safety separation

`frontend/views/MappingPage.tsx` and `frontend/mocks/homeMapping.ts` contain no hardware client or network calls. The hardware remote is available only on the sidebar’s **라즈봇 리모컨** page, never mounted on the map page. Opening it does not arm the robot; explicit safety confirmation and hardware-mode selection are required. Leaving the page retains the existing stop/lock cleanup. **모의 정지** pauses simulation only.

The existing top-bar **전체 비상정지** intentionally retains its real Raspbot stop request for safety. API acknowledgement does not prove physical wheel stop. Simulation tests do not call it.

## Verification

From the project root, with Node.js 22.13 or newer:

```sh
npm --prefix frontend run test:mapping
(cd frontend && npx tsc --noEmit --incremental false)
npm --prefix frontend run build
```

Tests cover path continuity, blocked cells, full exploration, occlusion, restrictions, pause/resume, emergency locking, docking, reset, hardware/network separation, reference layout, and deterministic bounded scan geometry isolated from navigation. No camera, motor, or database is used.

Real integration requires calibrated coordinate frames, actual localization/mapping, obstacle and clearance validation, versioned map persistence, and hardware feedback. Never treat simulated completion as a verified physical result.
