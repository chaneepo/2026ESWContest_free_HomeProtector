'use client';

import { useEffect, useId, useMemo, useReducer, useState } from 'react';
import { PageHeader } from '@/components/ui';
import { CELL_METERS, CELLS, COLS, DOCK, FLOOR, OBJECTS, ROOMS, ROWS, coverage, initialMapping, inRoom, inside, key, mappingReducer, roomAt, same, scanAppearance, walkable, wall } from '@/mocks/homeMapping';

const HOME_AREA = CELLS.filter(p => !wall(p));
const HOME_OUTLINE = scanAppearance(HOME_AREA).path;
const SCANNED_OBJECTS = OBJECTS.map(o => ({ ...o, ...scanAppearance(CELLS.filter(p => inside(p, o))) }));

export function MappingPage({ active, emergencyLocked }: { active: boolean; emergencyLocked: boolean }) {
  const [state, dispatch] = useReducer(mappingReducer, undefined, initialMapping);
  const [selected, setSelected] = useState('living');
  const [speed, setSpeed] = useState(2);
  const [showRoute, setShowRoute] = useState(true);
  const [showSensor, setShowSensor] = useState(false);
  const patternId = useId();
  const preview = state.phase === 'idle';
  const room = ROOMS.find(r => r.id === selected)!;
  const paused = !state.running && state.route.length > state.index + 1;
  const percent = preview ? 0 : coverage(state.known);
  const vectorMap = useMemo(() => {
    const discovered = HOME_AREA.filter(p => preview || state.known.has(key(p)));
    const scanned = scanAppearance(discovered);
    return { outline: scanned.path, flecks: scanned.flecks, rooms: ROOMS.map(r => ({ ...r, path: scanAppearance(discovered.filter(p => inRoom(p, r))).path })) };
  }, [preview, state.known]);
  const rooms = ROOMS.map(r => {
    const floor = FLOOR.filter(p => inRoom(p, r));
    const seen = preview ? 0 : floor.filter(p => state.known.has(key(p))).length;
    return { ...r, percent: Math.floor(seen / floor.length * 100), area: (floor.length * CELL_METERS ** 2).toFixed(1) };
  });
  const visibleObjects = SCANNED_OBJECTS.filter(o => preview || CELLS.some(p => inside(p, o) && state.known.has(key(p))));
  const label = emergencyLocked ? '전체 안전정지' : paused ? '일시정지' : ({ idle: '충전소 대기', scanning: '집 탐색 중', ready: '집 분석 완료', moving: '목적지 이동 중', returning: '충전소 복귀 중', arrived: '가상 이동 완료' }[state.phase]);
  const sensor = useMemo(() => Array.from({ length: 24 }, (_, i) => {
    const angle = i * Math.PI / 12;
    let distance = 0;
    for (let d = 0.2; d <= 4.5; d += 0.2) {
      distance = d;
      if (!walkable({ x: Math.round(state.position.x + Math.cos(angle) * d), y: Math.round(state.position.y + Math.sin(angle) * d) })) break;
    }
    return { x: state.position.x + 0.5 + Math.cos(angle) * distance, y: state.position.y + 0.5 + Math.sin(angle) * distance };
  }), [state.position]);

  useEffect(() => {
    if (!state.running) return;
    const timer = window.setInterval(() => dispatch({ type: 'tick', speed, locked: emergencyLocked || !active }), 120);
    return () => window.clearInterval(timer);
  }, [state.running, speed, emergencyLocked, active]);
  useEffect(() => {
    const pause = () => dispatch({ type: 'pause' });
    const visibility = () => { if (document.hidden) pause(); };
    window.addEventListener('chan-emergency-stop', pause);
    window.addEventListener('blur', pause);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      window.removeEventListener('chan-emergency-stop', pause);
      window.removeEventListener('blur', pause);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, []);

  const previous = state.trail.at(-2) ?? { x: state.position.x, y: state.position.y + 1 };
  const heading = Math.atan2(state.position.y - previous.y, state.position.x - previous.x) * 180 / Math.PI + 90;
  const points = (path: typeof state.trail) => path.map(p => `${p.x + 0.5},${p.y + 0.5}`).join(' ');
  return <div className="home-mapping">
    <PageHeader eyebrow="라즈봇 · 공간 인식 시뮬레이션" title="우리 집을 이해하는 라즈봇" description="집을 탐색하고, 공간을 구분하고, 필요한 곳으로 이동합니다." action={<span className="mapping-demo-badge"><i />가상 지도 · 시뮬레이션 전용</span>} />
    <div className="mapping-notice"><span>모의 실험</span><p>참고 도면의 배치를 단순화한 가상 지도입니다. 실제 집을 촬영하거나 라즈봇을 움직이지 않습니다.</p></div>
    <div className="mapping-steps" aria-label="집 분석 진행 단계">
      {['가상 집 불러오기', '탐색·지도 만들기', '방·장애물 분석', '목적지 이동'].map((title, i) => <div key={title} className={i === 0 || (i === 1 && !preview) || (i === 2 && state.mapped) || (i === 3 && ['moving', 'returning', 'arrived'].includes(state.phase)) ? 'reached' : ''}><span>{String(i + 1).padStart(2, '0')}</span>{title}</div>)}
    </div>
    <div className="mapping-layout">
      <section className="mapping-map-panel" aria-label="가상 주택 지도">
        <header className="mapping-map-head"><div><span className="mapping-kicker">집 지도 01</span><h2>우리 집 · 가상 스캔 맵</h2><p>참고 도면 기반 · 방별 영역 · {preview ? '탐색 전 예시 미리보기' : '가상 센서로 확인한 영역만 표시'}</p></div><span className={`mapping-state ${state.running && !emergencyLocked ? 'is-running' : ''}`}><i />{label}</span></header>
        <div className="mapping-map-toolbar"><div className="mapping-legend"><span><i className="known" />인식 공간</span><span><i className="unknown" />미탐색</span><span><i className="obstacle" />벽·가구</span></div><div><label><input type="checkbox" checked={showRoute} onChange={e => setShowRoute(e.target.checked)} />경로</label><label><input type="checkbox" checked={showSensor} onChange={e => setShowSensor(e.target.checked)} />가상 센서</label></div></div>
        <div className="mapping-map-canvas">
          <svg viewBox={`-0.8 -0.8 ${COLS + 1.6} ${ROWS + 1.6}`} role="img" aria-label={`참고 도면을 바탕으로 한 가상 스캔 지도. ${label}, 탐색률 ${percent}%. 목적지는 오른쪽 방 목록에서 선택하세요.`}>
            <defs><pattern id={patternId} width="0.6" height="0.6" patternUnits="userSpaceOnUse"><path d="M0 0L.6 .6" stroke="#d97081" strokeWidth=".06" /></pattern></defs>
            <path d={HOME_OUTLINE} fill="#e9edf2" stroke="#cbd5df" strokeWidth=".045" strokeLinejoin="miter" />
            <path d={vectorMap.outline} fill="#dce9ee" />
            {vectorMap.rooms.map(r => <path key={r.id} d={r.path} fill={r.color} />)}
            <path d={vectorMap.outline} fill="none" stroke="#6e8391" strokeWidth=".055" strokeLinejoin="miter" />
            {state.mapped && <path d={vectorMap.rooms.find(r => r.id === selected)?.path} fill="none" stroke="#1769e0" strokeWidth=".09" strokeLinejoin="miter" />}
            {state.restricted && <g><path d={vectorMap.rooms.find(r => r.id === 'study')?.path} fill={`url(#${patternId})`} opacity=".55" /><text x={ROOMS[4].label.x} y={ROOMS[4].label.y - 1} textAnchor="middle" fontSize=".55" fill="#a6314b" fontWeight="700">출입 제한</text></g>}
            {visibleObjects.map(o => <g key={o.name}><path d={o.path} fill="#bcc6cb" stroke="#8c9eac" strokeWidth=".05" />{o.flecks.map(f => <rect key={f.id} x={f.x} y={f.y} width={f.w} height={f.h} fill={f.fill} opacity={f.opacity} />)}<text x={o.x + o.w / 2} y={o.y + o.h / 2 + .17} textAnchor="middle" fontSize=".45" fill="#43566b">{o.name}</text></g>)}
            <g aria-hidden="true">{vectorMap.flecks.map(f => <rect key={f.id} x={f.x} y={f.y} width={f.w} height={f.h} fill={f.fill} opacity={f.opacity} />)}</g>
            {rooms.filter(r => preview || r.percent >= 60).map(r => <text key={r.id} x={r.label.x} y={r.label.y} textAnchor="middle" fontSize=".63" fontWeight="700" fill="#3c5366" paintOrder="stroke" stroke="#ffffffb0" strokeWidth=".13">{r.name}</text>)}
            {showRoute && !preview && <>
              {state.mapped && <polyline points={points(state.route.slice(state.index))} fill="none" stroke="#1c98a4" strokeWidth=".12" strokeDasharray=".25 .22" strokeLinecap="round" />}
              <polyline points={points(state.trail)} fill="none" stroke="#2474d6" opacity=".7" strokeWidth=".12" strokeLinecap="round" strokeLinejoin="round" />
            </>}
            <g transform={`translate(${DOCK.x + .5} ${DOCK.y + .5})`}><rect x="-.5" y="-.45" width="1" height=".9" rx=".18" fill="#234d70" /><path d="M.1 -.3L-.17 .05H.04L-.1 .3" stroke="white" strokeWidth=".09" fill="none" /><text x="0" y="1" textAnchor="middle" fontSize=".45" fill="#34556f">충전소</text></g>
            {state.mapped && !(state.restricted && selected === 'study') && <g transform={`translate(${room.target.x + .5} ${room.target.y + .5})`}><circle r=".44" stroke="#1769e0" strokeWidth=".1" fill="#fff" /><circle r=".15" fill="#1769e0" /></g>}
            {showSensor && !preview && <g stroke="#13a599" strokeWidth=".035" opacity=".3">{sensor.map((p, i) => <line key={i} x1={state.position.x + .5} y1={state.position.y + .5} x2={p.x} y2={p.y} />)}</g>}
            <g transform={`translate(${state.position.x + .5} ${state.position.y + .5})`}>
              <circle r=".9" fill="#1769e018" /><circle r=".48" fill="white" stroke="#1769e0" strokeWidth=".13" />
              <g transform={`rotate(${heading})`}><path d="M0 -.31L.2 .14L0 .05L-.2 .14Z" fill="#1769e0" /></g>
            </g>
            <g aria-hidden="true" stroke="#7b8fa1" strokeWidth=".06"><path d={`M1 ${ROWS + .1}V${ROWS + .35}H6V${ROWS + .1}`} fill="none" /><text x="6.3" y={ROWS + .5} fontSize=".4" fill="#7b8fa1" stroke="none">2m</text></g>
          </svg>
          {preview && <div className="mapping-preview-note">가상 스캔 미리보기 · 경계 질감은 합성 표현입니다</div>}
        </div>
        <div className="mapping-metrics"><div><span>탐색률</span><strong>{percent}<small>%</small></strong></div><div><span>분석한 공간</span><strong>{rooms.filter(r => r.percent === 100).length}<small>/ {ROOMS.length}</small></strong></div><div><span>인식한 가구</span><strong>{preview ? 0 : visibleObjects.length}<small>/ {OBJECTS.length}</small></strong></div><div><span>가상 이동 거리</span><strong>{(state.steps * CELL_METERS).toFixed(1)}<small>m</small></strong></div></div>
        <div className="mapping-progress" role="progressbar" aria-label="가상 지도 탐색률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}><span style={{ width: `${percent}%` }} /></div>
        <p className="mapping-message" role="status">{emergencyLocked ? '전체 안전정지가 활성화되었습니다. 해제 후에도 재개 버튼을 눌러야 움직입니다.' : state.message}</p>
      </section>
      <aside className="mapping-side">
        <section className="mapping-control">
          <div className="mapping-robot-head"><div className="mapping-location-icon" aria-hidden="true">⌖</div><div><span className="mapping-kicker">가상 라즈봇</span><h2>{roomAt(state.position)?.name ?? '연결 통로'}<span>에 있어요</span></h2></div></div>
          <div className="mapping-coordinates"><span>지도 기준 위치</span><b>{(state.position.x * CELL_METERS).toFixed(1)}m, {(state.position.y * CELL_METERS).toFixed(1)}m</b></div>
          <button type="button" className="mapping-primary" disabled={emergencyLocked || (!preview && !state.running && !paused)} onClick={() => dispatch({ type: state.running ? 'pause' : preview ? 'start' : 'resume' })}>{state.running ? 'Ⅱ  일시정지' : paused ? '▷  이어서 이동' : state.mapped ? '✓  집 분석 완료' : '▷  집 탐색 시작'}</button>
          <div className="mapping-small-actions"><button type="button" disabled={!state.mapped || state.running || emergencyLocked || same(state.position, DOCK)} onClick={() => dispatch({ type: 'return' })}>⌂ 충전소 복귀</button><button type="button" className="mapping-stop" disabled={!state.running} onClick={() => dispatch({ type: 'pause' })}>■ 모의 정지</button></div>
          <div className="mapping-speed"><span>시뮬레이션 속도</span><div role="group" aria-label="시뮬레이션 속도">{[1, 2, 4].map(value => <button type="button" key={value} aria-pressed={speed === value} onClick={() => setSpeed(value)}>{value}×</button>)}</div></div>
          <p className="mapping-hint">속도는 가상 화면 재생에만 적용됩니다.</p>
        </section>
        <section className="mapping-room-panel"><div className="mapping-section-head"><h2>공간 분석</h2><span>방 이름은 예시</span></div><p>탐색 후 이동할 공간을 선택하세요.</p>
          <div className="mapping-room-list" role="group" aria-label="가상 이동 목적지">{rooms.map(r => <button type="button" key={r.id} aria-pressed={selected === r.id} className={selected === r.id ? 'selected' : ''} onClick={() => setSelected(r.id)}><i style={{ background: r.color }} /><span><b>{r.name}</b><small>{r.id === 'study' && state.restricted ? '출입 제한' : r.percent === 100 ? `분석 완료 · 가상 가용면적 ${r.area}㎡` : r.percent > 0 ? `부분 탐색 · ${r.percent}% 확인` : '탐색 대기'}</small></span><em>{selected === r.id ? '●' : '○'}</em></button>)}</div>
          <div className="mapping-destination"><small>선택한 목적지</small><strong>{room.name}</strong><p>{room.purpose}</p><button type="button" disabled={!state.mapped || state.running || emergencyLocked || (selected === 'study' && state.restricted)} onClick={() => dispatch({ type: 'go', roomId: selected })}>{!state.mapped ? '집 분석 후 이동할 수 있어요' : selected === 'study' && state.restricted ? '출입 제한 중' : `${room.name} 가상 이동 →`}</button></div>
          <label className="mapping-restriction"><input type="checkbox" checked={state.restricted} disabled={!state.mapped || state.running || paused || emergencyLocked} onChange={() => dispatch({ type: 'restrict' })} /><span>서재 출입 제한<small>선택한 공간을 이동 경로에서 제외</small></span></label>
        </section>
      </aside>
    </div>
    <div className="mapping-bottom"><section className="mapping-log"><div className="mapping-section-head"><h2>가상 인식 기록</h2><span>최근 {state.events.length}개</span></div><ol>{state.events.slice(0, 5).map((event, i) => <li key={`${event}-${i}`}><span>{i === 0 ? '최근' : '이전'}</span>{event}</li>)}</ol></section><section className="mapping-next"><span className="mapping-kicker">실물 연동은 다음 단계</span><h2>가상 지도를 실제 인식으로</h2><p>현재 방 이름과 가구는 미리 정의된 데이터입니다. 향후 센서 측정, 위치 추정, 실제 지도 생성 및 장애물 검증을 연결할 예정입니다.</p><button type="button" onClick={() => dispatch({ type: 'reset' })}>↻ 가상 지도 초기화</button><small>가상 진행만 초기화합니다. 실제 파일·장치는 변경하지 않습니다.</small></section></div>
  </div>;
}
