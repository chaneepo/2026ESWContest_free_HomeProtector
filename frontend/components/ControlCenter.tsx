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
import { PageHeader, stateLabel } from './ui';
import { RaspbotRemote } from './RaspbotRemote';
import { MappingPage } from '@/views/MappingPage';

const nav: { key: PageKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: '대시보드', icon: '◈' },
  { key: 'mapping', label: '라즈봇 · 집 지도', icon: '⌖' },
  { key: 'automatic', label: '자동 운전', icon: '▷' },
  { key: 'manual', label: '수동 제어', icon: '⊕' },
  { key: 'remote', label: '라즈봇 리모컨', icon: '✥' },
  { key: 'vision', label: '비전', icon: '◉' },
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
  const pageContent = { dashboard: <DashboardPage />, automatic: <AutomaticPage />, manual: <ManualPage />, vision: <VisionPage />, items: <ItemsPage />, history: <HistoryPage />, mapping: null,
    remote: <section className="raspbot-remote-page"><PageHeader eyebrow="라즈봇 · 실물 수동 제어" title="라즈봇 리모컨" description="전진·후진·좌우 회전과 평행이동을 직접 조작합니다." /><p className="remote-hardware-notice">집 지도와 달리 실제 라즈봇을 제어하는 화면입니다. 처음에는 이동이 잠겨 있으며, 주변 안전 확인 후 실기모드를 선택해야 움직입니다. 메뉴를 벗어나면 운전 권한을 잠그고 정지를 요청합니다. 실제 바퀴 정지는 직접 확인하세요.</p><RaspbotRemote embedded emergencyLocked={status.emergencyStop} /></section>,
  }[page];
  return <main className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><span /></div><div><strong>CARE-PACK</strong><small>로봇 제어 시스템</small></div></div><nav aria-label="주요 메뉴">{nav.map((item) => <button key={item.key} aria-current={page === item.key ? 'page' : undefined} onClick={() => setPage(item.key)} className={`nav-item ${page === item.key ? 'active' : ''}`}><span>{item.icon}</span>{item.label}</button>)}</nav><div className="nav-section"><p>추후 연동</p><span>사용자 관리 <em>준비 중</em></span><span>일정 관리 <em>준비 중</em></span><span>알림 <em>준비 중</em></span><span>장치 설정 <em>준비 중</em></span></div><div className="sim-note"><b>집 지도 시뮬레이션</b><span>탐색·지도 이동은 가상 동작입니다.<br />상단 전체 비상정지는 기존 실기 정지 요청도 유지합니다.</span></div></aside>
    <section className="workspace"><header className="topbar"><div className="mode-cluster"><span className="mode-badge">{page === 'remote' ? '실물 수동 제어' : page === 'mapping' ? '지도 시뮬레이션' : '작업 시뮬레이션'}</span><span><i className={`dot ${status.emergencyStop ? 'red' : 'green'}`} /> {status.emergencyStop ? '안전 정지' : '시스템 준비'}</span><span><i className="dot blue" /> {stateLabel[status.currentState]}</span></div><div className="top-actions"><time>{time ? new Intl.DateTimeFormat('ko-KR', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false }).format(time) : '현재 시간 확인 중'}</time>{status.emergencyStop ? <button className="reset-stop" onClick={resetEmergency}>비상 정지 해제</button> : <button className="emergency" title="가상 동작을 멈추고 기존 실제 라즈봇 정지 요청도 전송합니다" onClick={stopAll}><span>■</span> 전체 비상정지</button>}</div></header><div className="content">{pageContent}<div hidden={page !== 'mapping'}><MappingPage active={page === 'mapping'} emergencyLocked={status.emergencyStop} /></div></div></section>
    {status.emergencyStop && <div className="emergency-strip"><b>비상 정지 활성</b><span>{robotStopMessage || '가상 동작을 잠갔습니다. 실제 정지 상태도 확인하세요.'}</span></div>}
    {page !== 'mapping' && page !== 'remote' && <div className="raspbot-remote"><button type="button" className="remote-toggle" onClick={() => setPage('mapping')}><span>⌖</span>라즈봇 집 지도</button></div>}
  </main>;
}

export function ControlCenter() { return <SystemProvider><AppContent /></SystemProvider>; }
