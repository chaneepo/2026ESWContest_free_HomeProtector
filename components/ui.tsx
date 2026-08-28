'use client';

import type { EventLog, ExecutionState, JobStatus } from '@/types';

export const stateLabel: Record<ExecutionState, string> = {
  IDLE: '대기', PLAN: '계획', DETECT: '탐지', PICK: '파지', MOVE: '이동',
  PLACE: '배치', VERIFY: '검증', RECOVER: '회복', COMPLETE: '완료', ERROR: '오류',
};

export const jobStatusLabel: Record<JobStatus, string> = {
  WAITING: '대기', RUNNING: '실행 중', SUCCESS: '성공', FAILED: '실패', CANCELLED: '취소됨',
};

export const sourceLabel: Record<EventLog['source'], string> = {
  SYSTEM: '시스템', VISION: '비전', ARM: '로봇팔', ESP32: '센서', RAZBOT: '라즈봇',
};

export function formatTime(value?: string) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Seoul' }).format(new Date(value));
}

export function formatDateTime(value?: string) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul' }).format(new Date(value));
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

const normalStates: ExecutionState[] = ['IDLE', 'PLAN', 'DETECT', 'PICK', 'MOVE', 'PLACE', 'VERIFY', 'COMPLETE'];
export function StateFlow({ current }: { current: ExecutionState }) {
  const currentIndex = normalStates.indexOf(current);
  return <div className="state-flow">{normalStates.map((state, index) => <div className="state-piece" key={state}>{index > 0 && <span>→</span>}<div className={`state-node ${state === current ? 'active' : ''} ${currentIndex > index ? 'done' : ''} ${current === 'ERROR' ? 'error-state' : ''}`}><i>{currentIndex > index ? '✓' : index}</i><b>{stateLabel[state]}</b><small>{state}</small></div></div>)}</div>;
}

export function EventList({ events, limit = 8 }: { events: EventLog[]; limit?: number }) {
  return <div className="event-list">{events.slice(0, limit).map((event) => <div className={`event-row level-${event.level.toLowerCase()}`} key={event.id}><time>{formatTime(event.timestamp)}</time><span className={`source ${event.source.toLowerCase()}`}>{sourceLabel[event.source]}</span><p>{event.message}</p><i className="event-level">{event.level === 'SUCCESS' ? '성공' : event.level === 'WARNING' ? '주의' : event.level === 'ERROR' ? '오류' : '정보'}</i></div>)}</div>;
}

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`status-badge job-${status.toLowerCase()}`}>{jobStatusLabel[status]}</span>;
}

export function Modal({ title, children, onClose, wide = false }: { title: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><section className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}><header><h2>{title}</h2><button onClick={onClose} aria-label="닫기">×</button></header>{children}</section></div>;
}
