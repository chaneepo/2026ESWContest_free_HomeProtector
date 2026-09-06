import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { CELLS, COLS, DOCK, FLOOR, OBJECTS, ROOMS, coverage, explorationPath, findPath, initialMapping, inRoom, inside, key, mappingReducer, roomAt, same, scan, scanAppearance, traceContours, walkable, wall } from '../mocks/homeMapping.ts';

function finish(state) {
  for (let i = 0; i < 3000 && state.running; i++) state = mappingReducer(state, { type: 'tick', speed: 4, locked: false });
  assert.equal(state.running, false, 'bounded simulation must terminate');
  return state;
}
function validPath(path, restricted = false) {
  assert.ok(path && path.length > 0);
  path.forEach((p, i) => {
    assert.ok(walkable(p, restricted), `blocked cell ${JSON.stringify(p)}`);
    if (i) assert.equal(Math.abs(p.x - path[i - 1].x) + Math.abs(p.y - path[i - 1].y), 1);
  });
}
const completed = finish(mappingReducer(initialMapping(), { type: 'start' }));

test('initial state is an idle demo, never a completed physical map', () => {
  const state = initialMapping();
  assert.equal(state.phase, 'idle'); assert.equal(state.mapped, false); assert.equal(state.running, false);
  assert.deepEqual(state.position, DOCK);
  assert.equal(mappingReducer(state, { type: 'go', roomId: 'living' }), state);
  assert.equal(mappingReducer(state, { type: 'return' }), state);
});
test('all room targets and docking location are reachable', () => {
  for (const room of ROOMS) { const route = findPath(DOCK, room.target); validPath(route); assert.deepEqual(route.at(-1), room.target); }
});
test('exploration visits every free cell without jumping through walls or furniture', () => {
  const route = explorationPath(); validPath(route);
  const visited = new Set(route.map(key));
  for (const p of FLOOR) assert.ok(visited.has(key(p)));
});
test('obstacles, bounds, malformed coordinates, and prohibited destinations are rejected', () => {
  for (const p of [{ x: 0, y: 0 }, { x: -1, y: 3 }, { x: 2, y: 2 }, { x: 9, y: 2 }, { x: 1.5, y: 2 }, { x: NaN, y: 1 }]) assert.equal(findPath(DOCK, p), null);
  assert.equal(findPath(DOCK, ROOMS[4].target, true), null);
});
test('sensor stops at walls rather than revealing the room behind them', () => {
  const known = scan(new Set(), { x: 8, y: 2 });
  assert.ok(known.has(key({ x: 9, y: 2 })));
  assert.equal(known.has(key({ x: 10, y: 2 })), false);
});
test('exploration completes at genuine full simulated coverage', () => {
  assert.equal(completed.phase, 'ready'); assert.equal(completed.mapped, true); assert.equal(coverage(completed.known), 100);
  for (const obj of OBJECTS) assert.ok([...completed.known].some(k => inside({ x: k % COLS, y: Math.floor(k / COLS) }, obj)));
});
test('discovery is monotonic and does not mutate previous state sets', () => {
  let state = mappingReducer(initialMapping(), { type: 'start' });
  for (let i = 0; i < 30; i++) {
    const original = new Set(state.known);
    const next = mappingReducer(state, { type: 'tick', speed: 2, locked: false });
    assert.deepEqual(state.known, original);
    for (const k of state.known) assert.ok(next.known.has(k));
    state = next;
  }
});
test('pause freezes location and an explicit resume continues the route', () => {
  const started = mappingReducer(initialMapping(), { type: 'start' });
  const paused = mappingReducer(started, { type: 'pause' });
  assert.equal(mappingReducer(paused, { type: 'tick', speed: 4, locked: false }), paused);
  const resumed = mappingReducer(paused, { type: 'resume' });
  assert.ok(resumed.running); assert.deepEqual(resumed.position, paused.position);
  assert.notDeepEqual(mappingReducer(resumed, { type: 'tick', speed: 1, locked: false }).position, paused.position);
});
test('emergency/inactive tick pauses without motion and does not auto-resume on unlock', () => {
  const state = mappingReducer(initialMapping(), { type: 'start' });
  const stopped = mappingReducer(state, { type: 'tick', speed: 4, locked: true });
  assert.equal(stopped.running, false); assert.deepEqual(stopped.position, state.position);
  assert.equal(mappingReducer(stopped, { type: 'tick', speed: 4, locked: false }), stopped);
});
test('all selected rooms are reachable after mapping and return finishes at the dock', () => {
  for (const room of ROOMS) {
    const moving = mappingReducer(completed, { type: 'go', roomId: room.id });
    validPath(moving.route);
    const arrived = finish(moving); assert.ok(same(arrived.position, room.target));
    const docked = finish(mappingReducer(arrived, { type: 'return' })); assert.deepEqual(docked.position, DOCK);
  }
});
test('restricted study is avoided; trying to go there preserves robot position', () => {
  const docked = finish(mappingReducer(completed, { type: 'return' }));
  const restricted = mappingReducer(docked, { type: 'restrict' });
  assert.equal(restricted.restricted, true);
  const refused = mappingReducer(restricted, { type: 'go', roomId: 'study' });
  assert.equal(refused.running, false); assert.deepEqual(refused.position, DOCK); assert.match(refused.message, /경로가 없습니다/);
  validPath(mappingReducer(restricted, { type: 'go', roomId: 'kitchen' }).route, true);
});
test('restrictions cannot enclose the robot or change while a path is active', () => {
  const moving = mappingReducer(completed, { type: 'go', roomId: 'study' });
  assert.equal(mappingReducer(moving, { type: 'restrict' }), moving);
  const paused = mappingReducer(moving, { type: 'pause' });
  assert.equal(mappingReducer(paused, { type: 'restrict' }), paused);
  const arrived = finish(moving);
  assert.equal(mappingReducer(arrived, { type: 'restrict' }).restricted, false);
});
test('speed changes playback steps, not collision detection or scan results', () => {
  const started = mappingReducer(initialMapping(), { type: 'start' });
  let slow = started;
  for (let i = 0; i < 4; i++) slow = mappingReducer(slow, { type: 'tick', speed: 1, locked: false });
  const fast = mappingReducer(started, { type: 'tick', speed: 4, locked: false });
  assert.deepEqual(fast.position, slow.position); assert.deepEqual(fast.known, slow.known); assert.equal(fast.steps, slow.steps);
});
test('reset clears only simulation state and late ticks cannot restart it', () => {
  const reset = mappingReducer(completed, { type: 'reset' });
  assert.deepEqual(reset, initialMapping());
  assert.equal(mappingReducer(reset, { type: 'tick', speed: 4, locked: false }), reset);
});
test('mapping UI and engine have no hardware client or network commands', () => {
  for (const file of ['../mocks/homeMapping.ts', '../views/MappingPage.tsx']) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /\bfetch\s*\(|WebSocket|ControlClient|\/api\/device\//);
  }
  const shell = readFileSync(new URL('../components/ControlCenter.tsx', import.meta.url), 'utf8');
  assert.match(shell, /remote: <section[\s\S]*?<RaspbotRemote embedded emergencyLocked=\{status\.emergencyStop\}/);
  assert.equal((shell.match(/<RaspbotRemote/g) ?? []).length, 1, 'hardware remote belongs only to its own page');
  assert.match(shell, /\}\[page\]/, 'only the selected page is mounted');
  assert.match(shell, /\/api\/device\/raspbot\/stop/, 'existing global safety stop must remain');
});

function contourArea(contours) {
  return contours.reduce((sum, points) => sum + points.reduce((area, p, i) => {
    const q = points[(i + 1) % points.length];
    return area + p.x * q.y - q.x * p.y;
  }, 0) / 2, 0);
}
test('contours merge adjacent cells into one perimeter without internal grid edges', () => {
  const result = traceContours([{ x: 1, y: 1 }, { x: 2, y: 1 }, { x: 1, y: 2 }, { x: 2, y: 2 }]);
  assert.equal(result.length, 1); assert.equal(result[0].length, 4); assert.equal(contourArea(result), 4);
  assert.deepEqual(traceContours([]), []);
});
test('contours preserve holes and separate corner-touching spaces', () => {
  const ring = Array.from({ length: 9 }, (_, i) => ({ x: i % 3, y: Math.floor(i / 3) })).filter(p => p.x !== 1 || p.y !== 1);
  assert.equal(traceContours(ring).length, 2); assert.equal(contourArea(traceContours(ring)), 8);
  assert.equal(traceContours([{ x: 0, y: 0 }, { x: 1, y: 1 }]).length, 2);
});
test('vector floor representation preserves all walkable area', () => {
  assert.equal(contourArea(traceContours(FLOOR)), FLOOR.length);
  const source = readFileSync(new URL('../views/MappingPage.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /CELLS\.map/);
  assert.match(source, /vectorMap\.rooms\.map/);
});

test('reference layout has an open central living area, left kitchen/study, right bedrooms/baths, and lower entry', () => {
  for (const [p, id] of [[{ x: 14, y: 8 }, 'living'], [{ x: 3, y: 17 }, 'living'], [{ x: 6, y: 5 }, 'kitchen'], [{ x: 6, y: 12 }, 'study'], [{ x: 21, y: 6 }, 'bedroom'], [{ x: 21, y: 24 }, 'bedroom2'], [{ x: 21, y: 12 }, 'bathroom'], [{ x: 21, y: 17 }, 'bathroom2'], [DOCK, 'hall']]) assert.equal(roomAt(p)?.id, id);
  for (const room of ROOMS) {
    assert.ok(inRoom(room.target, room));
    assert.ok(FLOOR.some(p => inRoom(p, room)));
  }
  for (const p of FLOOR) assert.ok(ROOMS.filter(r => inRoom(p, r)).length <= 1, 'room regions must not overlap');
});

test('synthetic scan appearance is deterministic, empty-safe, and does not mutate cells', () => {
  assert.deepEqual(scanAppearance([]), { contours: [], path: '', flecks: [] });
  const cells = CELLS.filter(p => !wall(p));
  const before = structuredClone(cells);
  const first = scanAppearance(cells);
  assert.deepEqual(first, scanAppearance(cells));
  assert.deepEqual(cells, before);
  assert.ok(first.flecks.length > 0);
  assert.equal(new Set(first.flecks.map(f => f.id)).size, first.flecks.length);
  assert.doesNotMatch(first.path, /NaN|Infinity/);
  assert.ok(first.path.endsWith('Z'));
});

test('scan contours have bounded pixel-stepped edges, including holes and partial discovery', () => {
  const square = Array.from({ length: 16 }, (_, i) => ({ x: i % 4, y: Math.floor(i / 4) }));
  const result = scanAppearance(square);
  assert.equal(result.contours.length, 1);
  assert.ok(result.contours[0].length > 20, 'not just a four-corner rectangle');
  for (const p of result.contours[0]) {
    assert.ok(p.x >= -.334 && p.x <= 4.334 && p.y >= -.334 && p.y <= 4.334);
    assert.ok(Math.min(Math.abs(p.x), Math.abs(p.x - 4), Math.abs(p.y), Math.abs(p.y - 4)) <= .334);
  }
  const ring = square.filter(p => p.x !== 1 || p.y !== 1);
  const known = initialMapping().known;
  const partial = CELLS.filter(p => !wall(p) && known.has(key(p)));
  for (const cells of [square, ring, partial]) {
    const rough = scanAppearance(cells);
    assert.equal(rough.contours.length, traceContours(cells).length);
    for (const points of rough.contours) points.forEach((p, i) => {
      const q = points[(i + 1) % points.length];
      assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
      assert.ok(p.x === q.x || p.y === q.y, 'each boundary segment is horizontal or vertical');
    });
  }
});

test('display noise does not change navigation, sensor coverage, or collision geometry', () => {
  const path = findPath(DOCK, ROOMS[0].target);
  const known = scan(new Set(), DOCK);
  const beforeCoverage = coverage(known);
  scanAppearance(FLOOR);
  assert.deepEqual(findPath(DOCK, ROOMS[0].target), path);
  assert.deepEqual(scan(new Set(), DOCK), known);
  assert.equal(coverage(known), beforeCoverage);
  assert.equal(contourArea(traceContours(FLOOR)), FLOOR.length);
});
