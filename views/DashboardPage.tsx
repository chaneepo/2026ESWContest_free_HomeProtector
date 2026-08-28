'use client';

import { EventList, PageHeader, StateFlow, jobStatusLabel, stateLabel } from '@/components/ui';
import { useSystem } from '@/store/SystemProvider';

export function DashboardPage() {
  const { status, currentJob, events, setPage } = useSystem();
  const devices = [
    { name: 'SO-ARM101', detail: '로봇팔 제어기', status: status.armStatus, glyph: 'AR' },
    { name: '비전 카메라', detail: 'AprilTag 인식', status: status.visionStatus, glyph: 'VS' },
    { name: 'ESP32', detail: '센서 및 액추에이터', status: status.esp32Status, glyph: 'IO' },
    { name: 'Razbot', detail: '이동형 로봇', status: status.razbotStatus, glyph: 'RB' },
  ];
  return <>
    <PageHeader eyebrow="시스템 개요" title="CARE-PACK 대시보드" description="로봇 작업 상태와 연결된 장치를 한눈에 확인하세요." action={<button className="primary" onClick={() => setPage('automatic')}>자동 운전 시작 <span>→</span></button>} />
    <section className={`health-banner ${status.emergencyStop ? 'danger' : ''}`}><div><i className="health-icon">{status.emergencyStop ? '!' : '✓'}</i><span><b>{status.emergencyStop ? '비상 정지가 활성화되었습니다' : '시스템이 정상입니다'}</b><small>{status.emergencyStop ? '수동 해제 전까지 모든 동작이 차단됩니다.' : '현재 시뮬레이션 작업을 시작할 수 있습니다.'}</small></span></div><p>온라인 <strong>2</strong> <i /> 오프라인 <strong className="gray">2</strong></p></section>
    <section className="section-block"><div className="section-title"><div><p>장치 연결</p><span>실제로 연결되지 않은 장치는 오프라인으로 표시됩니다.</span></div><button>시뮬레이션 상태</button></div><div className="device-grid">{devices.map((device) => { const online = device.status === 'ONLINE' || device.status === 'BUSY'; return <article className="device-card" key={device.name}><div className={`device-glyph ${online ? 'online' : 'offline'}`}>{device.glyph}</div><div className="device-copy"><b>{device.name}</b><small>{device.detail}</small></div><span className={`status-pill ${online ? 'online' : 'offline'}`}><i /> {device.status === 'BUSY' ? '작업 중' : online ? '온라인' : '오프라인'}</span><footer><span>현재 상태 <b>{online ? stateLabel[status.currentState] : '-'}</b></span><span>최종 업데이트 <b>{online ? '방금 전' : '연결 없음'}</b></span></footer></article>; })}</div></section>
    <div className="dashboard-grid"><section className="panel current-job"><div className="panel-head"><div><p>현재 작업</p><span>실행 엔진 상태</span></div><span className={`idle-badge ${currentJob?.status === 'RUNNING' ? 'running' : ''}`}>{currentJob ? jobStatusLabel[currentJob.status] : '대기'}</span></div>{currentJob ? <div className="job-summary"><div className="job-id"><span>{currentJob.type === 'PACK' ? '가방 준비' : '귀가 분류'}</span><b>{currentJob.id}</b></div><dl><div><dt>현재 상태</dt><dd>{stateLabel[currentJob.currentState]}</dd></div><div><dt>현재 물품</dt><dd>{currentJob.currentItem ?? '-'}</dd></div><div><dt>진행률</dt><dd>{currentJob.completedItems} / {currentJob.totalItems}</dd></div><div><dt>재시도</dt><dd>{currentJob.retryCount}회</dd></div></dl><div className="progress-track"><span style={{ width: `${currentJob.totalItems ? (currentJob.completedItems / currentJob.totalItems) * 100 : 0}%` }} /></div><button className="text-link" onClick={() => setPage('automatic')}>작업 상세 보기 →</button></div> : <div className="empty-job"><div className="empty-orbit"><span>▷</span></div><b>진행 중인 작업이 없습니다</b><p>자동 운전에서 새 시뮬레이션 작업을 생성해 보세요.</p><button className="secondary" onClick={() => setPage('automatic')}>시뮬레이션 작업 만들기</button></div>}</section>
      <section className="panel events"><div className="panel-head"><div><p>최근 이벤트</p><span>시스템 활동 기록</span></div><button onClick={() => setPage('history')}>전체 보기</button></div><EventList events={events} limit={4} /></section></div>
    <section className="panel flow-panel"><div className="panel-head"><div><p>실행 상태 흐름</p><span>명령 완료와 실제 작업 성공을 구분하는 검증 기반 프로세스</span></div><code>계획 → 실행 → 검증 → 완료</code></div><StateFlow current={status.currentState} /></section>
  </>;
}
