// 하드웨어·통신과 완전히 분리된 고정 평면도 시뮬레이터. 실제 SLAM이 아니다.
export type Point = { x: number; y: number };
export type Rect = Point & { w: number; h: number };
export type Room = Rect & { id: string; name: string; color: string; target: Point; label: Point; purpose: string; regions?: Rect[] };
export const COLS = 28;
export const ROWS = 30;
export const CELL_METERS = 0.4;
export const DOCK: Point = { x: 16, y: 27 };
// 사용자 도면의 배치만 참고한 가상 모델. 도면의 치수·좌표를 실측한 데이터가 아니다.
export const ROOMS: Room[] = [
  { id: 'living', name: '거실 · 식사 공간', x: 1, y: 1, w: 18, h: 28, color: '#8dd5dc', target: { x: 13, y: 20 }, label: { x: 12, y: 17 }, purpose: '일상 물품 전달', regions: [{ x: 10, y: 1, w: 9, h: 25 }, { x: 1, y: 15, w: 9, h: 14 }, { x: 10, y: 26, w: 2, h: 3 }] },
  { id: 'kitchen', name: '주방', x: 1, y: 1, w: 8, h: 7, color: '#f3d880', target: { x: 6, y: 5 }, label: { x: 5.5, y: 6.8 }, purpose: '생활 물품 수령' },
  { id: 'bedroom', name: '침실 1', x: 20, y: 1, w: 7, h: 8, color: '#b5c5f0', target: { x: 21, y: 6 }, label: { x: 23.5, y: 8 }, purpose: '외출 준비물 수령' },
  { id: 'hall', name: '현관', x: 12, y: 26, w: 7, h: 3, color: '#b9dfc8', target: { x: 13, y: 27 }, label: { x: 13.7, y: 28.5 }, purpose: '가방 적재 · 충전소' },
  { id: 'study', name: '서재', x: 1, y: 9, w: 8, h: 5, color: '#e5b4d6', target: { x: 6, y: 12 }, label: { x: 5, y: 13.2 }, purpose: '개인 물품 수령' },
  { id: 'bedroom2', name: '침실 2', x: 20, y: 21, w: 7, h: 8, color: '#9ebff0', target: { x: 21, y: 24 }, label: { x: 23.5, y: 28.2 }, purpose: '생활 물품 전달' },
  { id: 'bathroom', name: '욕실 1', x: 20, y: 10, w: 7, h: 5, color: '#efc4b9', target: { x: 21, y: 12 }, label: { x: 23, y: 14.1 }, purpose: '예시 욕실 위치 확인' },
  { id: 'bathroom2', name: '욕실 2', x: 20, y: 16, w: 7, h: 4, color: '#f0cfb0', target: { x: 21, y: 17 }, label: { x: 23, y: 19.3 }, purpose: '예시 욕실 위치 확인' },
];
export const OBJECTS: (Rect & { name: string })[] = [
  { x: 1, y: 2, w: 2, h: 5, name: '조리대' }, { x: 4, y: 1, w: 3, h: 1, name: '싱크대' },
  { x: 12, y: 3, w: 4, h: 3, name: '식탁' }, { x: 2, y: 9, w: 3, h: 2, name: '책상' },
  { x: 23, y: 2, w: 3, h: 4, name: '침대 1' }, { x: 24, y: 10, w: 2, h: 2, name: '욕조' },
  { x: 24, y: 16, w: 2, h: 2, name: '세면대' }, { x: 23, y: 23, w: 3, h: 4, name: '침대 2' },
  { x: 7, y: 19, w: 3, h: 5, name: '소파' }, { x: 5, y: 24, w: 5, h: 2, name: '보조 소파' },
  { x: 4, y: 20, w: 2, h: 3, name: '테이블' }, { x: 1, y: 19, w: 1, h: 5, name: 'TV장' },
];
export const key = (p: Point) => p.y * COLS + p.x;
export const inside = (p: Point, r: Rect) => p.x >= r.x && p.x < r.x + r.w && p.y >= r.y && p.y < r.y + r.h;
export const same = (a: Point, b: Point) => a.x === b.x && a.y === b.y;
export const inRoom = (p: Point, r: Room) => (r.regions ?? [r]).some(region => inside(p, region));
export const roomAt = (p: Point) => ROOMS.find(r => inRoom(p, r));
// 격자 내부의 공유 변은 제거하고 외곽선만 연결한다. 화면에는 셀 경계를 그리지 않는다.
export function traceContours(cells: Point[]): Point[][] {
  const vertex = (p: Point) => `${p.x},${p.y}`;
  const edgeKey = (a: Point, b: Point) => `${vertex(a)}>${vertex(b)}`;
  const edges = new Map<string, { a: Point; b: Point }>();
  for (const p of cells) {
    const corners = [p, { x: p.x + 1, y: p.y }, { x: p.x + 1, y: p.y + 1 }, { x: p.x, y: p.y + 1 }];
    for (let i = 0; i < 4; i++) {
      const a = corners[i], b = corners[(i + 1) % 4];
      if (!edges.delete(edgeKey(b, a))) edges.set(edgeKey(a, b), { a, b });
    }
  }
  const outgoing = new Map<string, { a: Point; b: Point }[]>();
  for (const edge of edges.values()) outgoing.set(vertex(edge.a), [...(outgoing.get(vertex(edge.a)) ?? []), edge]);
  const contours: Point[][] = [];
  while (edges.size) {
    const first = edges.values().next().value!;
    let edge = first;
    const contour: Point[] = [first.a];
    for (;;) {
      edges.delete(edgeKey(edge.a, edge.b));
      if (same(edge.b, first.a)) break;
      contour.push(edge.b);
      const candidates = (outgoing.get(vertex(edge.b)) ?? []).filter(e => edges.has(edgeKey(e.a, e.b)));
      if (!candidates.length) throw new Error('Map boundary must be closed');
      // 대각선으로만 접한 영역은 우회전 우선으로 각각의 윤곽선을 유지한다.
      const rank = (e: { a: Point; b: Point }) => {
        const dx = edge.b.x - edge.a.x, dy = edge.b.y - edge.a.y;
        const nx = e.b.x - e.a.x, ny = e.b.y - e.a.y;
        const cross = dx * ny - dy * nx, dot = dx * nx + dy * ny;
        return cross > 0 ? 0 : dot > 0 ? 1 : cross < 0 ? 2 : 3;
      };
      edge = candidates.sort((a, b) => rank(a) - rank(b))[0];
    }
    contours.push(contour.filter((p, i) => {
      const a = contour[(i + contour.length - 1) % contour.length], b = contour[(i + 1) % contour.length];
      return (p.x - a.x) * (b.y - p.y) !== (p.y - a.y) * (b.x - p.x);
    }));
  }
  return contours;
}
export const contourPath = (cells: Point[]) => traceContours(cells).map(points => `M${points.map(p => `${p.x} ${p.y}`).join('L')}Z`).join(' ');
export type ScanFleck = Rect & { id: string; opacity: number; fill: string };
const scanHash = (x: number, y: number, salt: number) => {
  let n = Math.imul(x + 37, 374761393) ^ Math.imul(y + 91, 668265263) ^ Math.imul(salt, 1274126177);
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return (n ^ (n >>> 16)) >>> 0;
};
// 화면 전용 합성 스캔 질감. 원본 셀·경로·센서값은 변경하지 않는다.
// 좌표로 고정한 미세 계단을 사용하므로 재렌더링·부분 탐색 시 기존 벽선이 깜빡이지 않는다.
export function scanAppearance(cells: Point[]) {
  const flecks: ScanFleck[] = [];
  const contours = traceContours(cells).map(contour => {
    const points: Point[] = [];
    const push = (x: number, y: number) => {
      const point = { x: Number(x.toFixed(3)), y: Number(y.toFixed(3)) };
      if (!points.length || !same(points[points.length - 1], point)) points.push(point);
    };
    contour.forEach((a, i) => {
      const b = contour[(i + 1) % contour.length];
      const dx = Math.sign(b.x - a.x), dy = Math.sign(b.y - a.y);
      const horizontal = dx !== 0;
      const length = Math.abs(b.x - a.x) + Math.abs(b.y - a.y);
      for (let unit = 0; unit < length; unit++) {
        const start = { x: a.x + dx * unit, y: a.y + dy * unit };
        const low = { x: Math.min(start.x, start.x + dx), y: Math.min(start.y, start.y + dy) };
        const seed = scanHash(low.x, low.y, horizontal ? 1 : 2);
        push(start.x, start.y);
        for (let step = 0; step < 6; step++) {
          const canonicalStep = dx + dy > 0 ? step : 5 - step;
          const detail = scanHash(low.x * 6 + canonicalStep, low.y * 6, horizontal ? 3 : 4);
          const offset = step === 0 || step === 5 ? 0 : Math.max(-4, Math.min(4, seed % 7 - 3 + detail % 3 - 1)) / 12;
          const ox = horizontal ? 0 : offset, oy = horizontal ? offset : 0;
          push(start.x + dx * step / 6 + ox, start.y + dy * step / 6 + oy);
          push(start.x + dx * (step + 1) / 6 + ox, start.y + dy * (step + 1) / 6 + oy);
        }
        if (seed % 3 === 0) {
          const along = (seed % 5 + 1) / 6;
          const offset = (seed % 2 ? 1 : -1) * (0.25 + (seed % 4) / 12);
          flecks.push({ id: `${horizontal ? 'h' : 'v'}-${low.x}-${low.y}`, x: low.x + (horizontal ? along : offset), y: low.y + (horizontal ? offset : along), w: (seed % 3 + 1) / 12, h: ((seed >>> 3) % 3 + 1) / 12, opacity: 0.25 + (seed % 4) / 10, fill: seed % 5 === 0 ? '#ffffff' : '#768895' });
        }
      }
    });
    if (points.length && same(points[0], points[points.length - 1])) points.pop();
    return points.filter((p, i) => {
      const a = points[(i + points.length - 1) % points.length], b = points[(i + 1) % points.length];
      return Math.abs((p.x - a.x) * (b.y - p.y) - (p.y - a.y) * (b.x - p.x)) > 0.000001;
    });
  });
  return { contours, path: contours.map(points => `M${points.map(p => `${p.x} ${p.y}`).join('L')}Z`).join(' '), flecks };
}
export function wall(p: Point): boolean {
  return p.x <= 0 || p.x >= COLS - 1 || p.y <= 0 || p.y >= ROWS - 1
    || (p.x === 9 && p.y < 15 && ![4, 5, 11, 12].includes(p.y))
    || (p.y === 8 && p.x < 10)
    || (p.y === 14 && p.x < 10 && ![7, 8].includes(p.x))
    || (p.x === 19 && ![6, 7, 12, 17, 23, 24].includes(p.y))
    || ([9, 15, 20].includes(p.y) && p.x > 19);
}
export function walkable(p: Point, restricted = false): boolean {
  return Number.isInteger(p.x) && Number.isInteger(p.y) && !wall(p)
    && !OBJECTS.some(o => inside(p, o)) && !(restricted && inside(p, ROOMS[4]));
}
export const CELLS: Point[] = Array.from({ length: COLS * ROWS }, (_, i) => ({ x: i % COLS, y: Math.floor(i / COLS) }));
export const FLOOR = CELLS.filter(p => walkable(p));
// 4방향 최단 경로. 모의 평면도의 벽과 가구를 가로지르지 않는다.
export function findPath(start: Point, end: Point, restricted = false): Point[] | null {
  if (!walkable(start, restricted) || !walkable(end, restricted)) return null;
  const queue = [start];
  const previous = new Map<number, Point | null>([[key(start), null]]);
  for (let i = 0; i < queue.length; i++) {
    const p = queue[i];
    if (same(p, end)) {
      const result: Point[] = [];
      let cursor: Point | null = p;
      while (cursor) { result.unshift(cursor); cursor = previous.get(key(cursor)) ?? null; }
      return result;
    }
    for (const next of [{ x: p.x + 1, y: p.y }, { x: p.x, y: p.y + 1 }, { x: p.x - 1, y: p.y }, { x: p.x, y: p.y - 1 }]) {
      if (walkable(next, restricted) && !previous.has(key(next))) { previous.set(key(next), p); queue.push(next); }
    }
  }
  return null;
}
export function scan(known: Set<number>, p: Point): Set<number> {
  const next = new Set(known);
  next.add(key(p));
  // 가상 거리 센서 광선: 처음 만난 벽/가구에서 멈추며 벽 뒤를 투시하지 않는다.
  for (let angle = 0; angle < 360; angle += 4) {
    for (let d = 0.25; d <= 4.5; d += 0.25) {
      const q = { x: Math.round(p.x + Math.cos(angle * Math.PI / 180) * d), y: Math.round(p.y + Math.sin(angle * Math.PI / 180) * d) };
      if (q.x < 0 || q.x >= COLS || q.y < 0 || q.y >= ROWS) break;
      next.add(key(q));
      if (!walkable(q)) break;
    }
  }
  return next;
}
export function explorationPath(): Point[] {
  let path = [DOCK];
  const visited = new Set<number>([key(DOCK)]);
  for (let y = ROWS - 2; y > 0; y--) {
    const row = FLOOR.filter(p => p.y === y).sort((a, b) => y % 2 ? a.x - b.x : b.x - a.x);
    for (const target of row) {
      if (visited.has(key(target))) continue;
      const segment = findPath(path[path.length - 1], target);
      if (segment) { path = [...path, ...segment.slice(1)]; segment.forEach(p => visited.add(key(p))); }
    }
  }
  return path;
}
export type MappingState = {
  phase: 'idle' | 'scanning' | 'ready' | 'moving' | 'returning' | 'arrived';
  running: boolean; position: Point; route: Point[]; index: number;
  known: Set<number>; trail: Point[]; steps: number; mapped: boolean; restricted: boolean;
  message: string; events: string[];
};
export function initialMapping(): MappingState {
  return { phase: 'idle', running: false, position: DOCK, route: [], index: 0, known: scan(new Set(), DOCK),
    trail: [DOCK], steps: 0, mapped: false, restricted: false,
    message: '예시 평면도가 준비되었습니다. 탐색을 시작해 보세요.', events: ['가상 라즈봇이 현관 충전소에서 대기 중입니다.'] };
}
type Action = { type: 'start' | 'pause' | 'resume' | 'reset' | 'return' | 'restrict' }
  | { type: 'tick'; speed: number; locked: boolean } | { type: 'go'; roomId: string };
function announce(state: MappingState, message: string): MappingState {
  return { ...state, message, events: [message, ...state.events].slice(0, 8) };
}
export const coverage = (known: Set<number>) => Math.floor(FLOOR.filter(p => known.has(key(p))).length / FLOOR.length * 100);
export function mappingReducer(state: MappingState, action: Action): MappingState {
  if (action.type === 'reset') return initialMapping();
  if (action.type === 'pause') return state.running ? announce({ ...state, running: false }, '가상 라즈봇을 일시정지했습니다. 재개 버튼으로 다시 출발하세요.') : state;
  if (action.type === 'resume') return !state.running && state.index < state.route.length - 1 ? announce({ ...state, running: true }, '남은 경로를 이어서 이동합니다.') : state;
  if (action.type === 'start') {
    if (state.running || state.phase !== 'idle') return state;
    return announce({ ...initialMapping(), phase: 'scanning', running: true, route: explorationPath() }, '가상 탐색 시작 · 벽과 가구를 확인하며 집 지도를 구성합니다.');
  }
  if (action.type === 'restrict') {
    if (state.running || !state.mapped || state.index < state.route.length - 1) return state;
    if (!state.restricted && inside(state.position, ROOMS[4])) return announce(state, '서재 안에 있습니다. 먼저 다른 방으로 이동한 뒤 출입을 제한하세요.');
    return announce({ ...state, restricted: !state.restricted }, state.restricted ? '서재 출입 제한을 해제했습니다.' : '서재를 출입 제한 구역으로 지정했습니다. 경로 계획에서 제외합니다.');
  }
  if (action.type === 'go' || action.type === 'return') {
    if (state.running || !state.mapped) return state;
    const room = action.type === 'go' ? ROOMS.find(r => r.id === action.roomId) : undefined;
    if (action.type === 'go' && !room) return state;
    const target = room?.target ?? DOCK;
    const route = findPath(state.position, target, state.restricted);
    if (!route) return announce(state, '이동 가능한 경로가 없습니다. 출입 제한 구역을 확인하세요.');
    const moving = route.length > 1;
    return announce({ ...state, route, index: 0, trail: [state.position], running: moving,
      phase: moving ? action.type === 'return' ? 'returning' : 'moving' : 'arrived' },
      moving ? `${room?.name ?? '충전소'}까지 장애물을 피하는 가상 경로를 생성했습니다.` : `${room?.name ?? '충전소'}에 이미 도착해 있습니다.`);
  }
  if (action.type !== 'tick' || !state.running) return state;
  if (action.locked) return mappingReducer(state, { type: 'pause' });
  const index = Math.min(state.index + Math.max(1, Math.min(4, Math.floor(action.speed) || 1)), state.route.length - 1);
  const segment = state.route.slice(state.index + 1, index + 1);
  const position = state.route[index];
  const known = state.phase === 'scanning' ? segment.reduce(scan, state.known) : state.known;
  let next = { ...state, position, known, index, steps: state.steps + segment.length, trail: [...state.trail, ...segment] };
  const beforeRoom = roomAt(state.position), afterRoom = roomAt(position);
  if (beforeRoom?.id !== afterRoom?.id && afterRoom) next = announce(next, `${afterRoom.name} 영역 진입 · ${afterRoom.purpose}`);
  if (index === state.route.length - 1) {
    const explored = state.phase === 'scanning';
    next = announce({ ...next, running: false, mapped: state.mapped || explored, phase: explored ? 'ready' : 'arrived' },
      explored ? '가상 집 분석 완료 · 방을 선택해 목적지 이동을 시험해 보세요.'
        : state.phase === 'returning' ? '가상 충전소 복귀 완료 · 실제 충전 상태는 확인하지 않습니다.' : '가상 목적지에 도착했습니다.');
  }
  return next;
}
