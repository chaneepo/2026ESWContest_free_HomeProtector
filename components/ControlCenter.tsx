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

const nav: { key: PageKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: '대시보드', icon: '◈' }, { key: 'automatic', label: '자동 운전', icon: '▷' },
  { key: 'manual', label: '수동 제어', icon: '⊕' }, { key: 'vision', label: '비전', icon: '◉' },
  { key: 'items', label: '물품 및 목적지', icon: '▦' }, { key: 'history', label: '작업 이력', icon: '≡' },
];

function AppContent() {
  const { page, setPage, status, emergencyStop, resetEmergency } = useSystem();
  const [time, setTime] = useState<Date>(() => new Date());
  useEffect(() => { const timer = window.setInterval(() => setTime(new Date()), 1000); return () => window.clearInterval(timer); }, []);
  const pageContent = { dashboard: <DashboardPage />, automatic: <AutomaticPage />, manual: <ManualPage />, vision: <VisionPage />, items: <ItemsPage />, history: <HistoryPage /> }[page];
  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><span /></div><div><strong>CARE-PACK</strong><small>로봇 제어 시스템</small></div></div><nav aria-label="주요 메뉴">{nav.map((item) => <button key={item.key} onClick={() => setPage(item.key)} className={`nav-item ${page === item.key ? 'active' : ''}`}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="nav-section"><p>추후 연동</p><span>사용자 관리 <em>준비 중</em></span><span>일정 관리 <em>준비 중</em></span><span>알림 <em>준비 중</em></span><span>장치 설정 <em>준비 중</em></span></div><div className="sim-note"><b>시뮬레이션 모드</b><span>가상 장치 데이터를 사용 중입니다.<br />실물 장치는 움직이지 않습니다.</span></div></aside>
    <section className="workspace"><header className="topbar"><div className="mode-cluster"><span className="mode-badge">시뮬레이션</span><span><i className={`dot ${status.emergencyStop ? 'red' : 'green'}`} /> {status.emergencyStop ? '안전 정지' : '시스템 준비'}</span><span><i className="dot blue" /> {stateLabel[status.currentState]}</span></div><div className="top-actions"><time>{time ? new Intl.DateTimeFormat('ko-KR', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }).format(time) : '현재 시간 확인 중'}</time>{status.emergencyStop ? <button className="reset-stop" onClick={resetEmergency}>비상 정지 해제</button> : <button className="emergency" onClick={emergencyStop}><span>■</span> 비상 정지</button>}</div></header><div className="content">{pageContent}</div></section>
    {status.emergencyStop && <div className="emergency-strip"><b>비상 정지 활성</b><span>모든 시뮬레이션 동작이 차단되었습니다. 상단의 &apos;비상 정지 해제&apos;를 사용하세요.</span></div>}
  </main>;
}

export function ControlCenter() { return <SystemProvider><AppContent /></SystemProvider>; }
