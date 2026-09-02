'use client';

import { useEffect, useState } from 'react';
import { AutomaticPage } from '@/views/AutomaticPage';
import { DashboardPage } from '@/views/DashboardPage';
import { HistoryPage } from '@/views/HistoryPage';
import { ItemsPage } from '@/views/ItemsPage';
import { ManualPage } from '@/views/ManualPage';
import { VisionPage } from '@/views/VisionPage';
import { SystemProvider, useSystem } from '@/store/SystemProvider';
import type { PageKey } from '@/types';
import { stateLabel } from './ui';
import { RaspbotRemote } from './RaspbotRemote';

const nav: { key: PageKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: '대시보드', icon: '◈' }, { key: 'automatic', label: '자동 운전', icon: '▷' },
  { key: 'manual', label: '수동 제어', icon: '⊕' }, { key: 'vision', label: '비전', icon: '◉' },
  { key: 'items', label: '물품 및 목적지', icon: '▦' }, { key: 'history', label: '작업 이력', icon: '≡' },
];

function AppContent() {
  const { page, setPage, status, emergencyStop, resetEmergency } = useSystem();
  const [time, setTime] = useState<Date | null>(null);
  const [robotStopMessage, setRobotStopMessage] = useState('');
  useEffect(() => {
    const timer = window.setInterval(() => setTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const stopAll = async () => {
    emergencyStop();
    window.dispatchEvent(new Event('chan-emergency-stop'));
    setRobotStopMessage('실제 라즈봇에도 정지 요청 중');
    const abort = new AbortController();
    const timer = window.setTimeout(() => abort.abort(), 3000);
    try {
      const response = await fetch('/api/device/raspbot/stop', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', signal: abort.signal,
      });
      const data = await response.json() as { stop_confirmed?: boolean };
      setRobotStopMessage(response.ok && data.stop_confirmed
        ? '라즈봇 정지 명령 처리됨 · 실제 바퀴 정지도 확인하세요'
        : '실제 라즈봇 정지 미확인 · 움직이면 본체 전원을 끄세요');
    } catch { setRobotStopMessage('실제 라즈봇 정지 요청 실패 · 움직이면 본체 전원을 끄세요'); }
    finally { window.clearTimeout(timer); }
  };
  const pageContent = { dashboard: <DashboardPage />, automatic: <AutomaticPage />, manual: <ManualPage />, vision: <VisionPage />, items: <ItemsPage />, history: <HistoryPage /> }[page];
  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><span /></div><div><strong>CARE-PACK</strong><small>로봇 제어 시스템</small></div></div><nav aria-label="주요 메뉴">{nav.map((item) => <button key={item.key} onClick={() => setPage(item.key)} className={`nav-item ${page === item.key ? 'active' : ''}`}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="nav-section"><p>추후 연동</p><span>사용자 관리 <em>준비 중</em></span><span>일정 관리 <em>준비 중</em></span><span>알림 <em>준비 중</em></span><span>장치 설정 <em>준비 중</em></span></div><div className="sim-note"><b>시뮬레이션 모드</b><span>작업·팔 화면은 가상 데이터입니다.<br />별도 라즈봇 리모컨은 실제 구동이 가능합니다.</span></div></aside>
    <section className="workspace"><header className="topbar"><div className="mode-cluster"><span className="mode-badge">작업 시뮬레이션</span><span><i className={`dot ${status.emergencyStop ? 'red' : 'green'}`} /> {status.emergencyStop ? '안전 정지' : '시스템 준비'}</span><span><i className="dot blue" /> {stateLabel[status.currentState]}</span></div><div className="top-actions"><time>{time ? new Intl.DateTimeFormat('ko-KR', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }).format(time) : '현재 시간 확인 중'}</time>{status.emergencyStop ? <button className="reset-stop" onClick={resetEmergency}>비상 정지 해제</button> : <button className="emergency" onClick={stopAll}><span>■</span> 비상 정지</button>}</div></header><div className="content">{pageContent}</div></section>
    {status.emergencyStop && <div className="emergency-strip"><b>비상 정지 활성</b><span>{robotStopMessage || '시뮬레이션과 라즈봇 리모컨 이동을 잠갔습니다. 실제 정지 상태도 확인하세요.'}</span></div>}
    <RaspbotRemote emergencyLocked={status.emergencyStop} />
  </main>;
}

export function ControlCenter() { return <SystemProvider><AppContent /></SystemProvider>; }
