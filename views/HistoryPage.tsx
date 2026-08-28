'use client';

import { useMemo, useState } from 'react';
import { EventList, Modal, PageHeader, StatusBadge, formatDateTime, formatTime, stateLabel } from '@/components/ui';
import { useSystem } from '@/store/SystemProvider';
import type { Job } from '@/types';

export function HistoryPage() {
  const { jobs, events } = useSystem();
  const [selected, setSelected] = useState<Job | null>(null);
  const summary = useMemo(() => {
    const finished = jobs.filter((job) => job.status !== 'RUNNING');
    const success = finished.filter((job) => job.status === 'SUCCESS').length;
    const durations = finished.map((job) => job.durationSeconds ?? 0).filter(Boolean);
    return { today: jobs.length, rate: finished.length ? Math.round((success / finished.length) * 100) : 0, average: durations.length ? Math.round(durations.reduce((a,b) => a + b, 0) / durations.length) : 0, retries: jobs.reduce((sum, job) => sum + job.retryCount, 0), failed: finished.filter((job) => job.status === 'FAILED' || job.status === 'CANCELLED').length };
  }, [jobs]);
  return <>
    <PageHeader eyebrow="성능 및 신뢰성 기록" title="작업 이력" description="인식·파지·배치·검증·재시도 결과를 작업별로 확인합니다." />
    <div className="summary-grid"><article><span>오늘의 작업</span><b>{summary.today}</b><small>건</small></article><article><span>성공률</span><b>{summary.rate}</b><small>%</small></article><article><span>평균 처리 시간</span><b>{summary.average}</b><small>초</small></article><article><span>총 재시도</span><b>{summary.retries}</b><small>회</small></article><article className="failed"><span>실패·취소</span><b>{summary.failed}</b><small>건</small></article></div>
    <section className="panel history-panel"><div className="panel-head"><div><p>전체 작업</p><span>최신 순으로 표시됩니다.</span></div><button>보고서 내보내기 · 준비 중</button></div><table><thead><tr><th>작업 ID</th><th>작업 유형</th><th>상태</th><th>물품</th><th>재시도</th><th>시작 시간</th><th>완료 시간</th><th>소요 시간</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id} onClick={() => setSelected(job)} className="clickable"><td><b>{job.id}</b></td><td>{job.type === 'PACK' ? '가방 준비' : job.type === 'SORT' ? '귀가 분류' : job.type === 'DELIVERY' ? '물품 배송' : '재난 우선'}</td><td><StatusBadge status={job.status} /></td><td>{job.completedItems} / {job.totalItems}</td><td>{job.retryCount}회</td><td>{formatDateTime(job.startedAt)}</td><td>{formatDateTime(job.completedAt)}</td><td>{job.durationSeconds ? `${job.durationSeconds}초` : '진행 중'}</td></tr>)}</tbody></table></section>
    <section className="panel all-events"><div className="panel-head"><div><p>시스템 이벤트 로그</p><span>모든 장치와 실행 엔진의 최근 활동</span></div></div><EventList events={events} limit={10} /></section>
    {selected && <Modal title="작업 상세" wide onClose={() => setSelected(null)}><div className="job-detail"><header><div><small>{selected.type === 'PACK' ? '가방 준비' : '귀가 분류'}</small><h3>{selected.id}</h3></div><StatusBadge status={selected.status} /></header><dl><div><dt>최종 상태</dt><dd>{stateLabel[selected.currentState]}</dd></div><div><dt>물품 처리</dt><dd>{selected.completedItems} / {selected.totalItems}</dd></div><div><dt>재시도</dt><dd>{selected.retryCount}회</dd></div><div><dt>소요 시간</dt><dd>{selected.durationSeconds ? `${selected.durationSeconds}초` : '-'}</dd></div></dl>{selected.failureReason && <p className="failure-reason"><b>실패 사유</b>{selected.failureReason}</p>}<h4>실행 타임라인</h4><div className="timeline">{['작업 시작','계획 생성','물품 탐지','파지 시작', selected.retryCount ? '회복 및 재시도' : '파지 성공','배치 완료','적재 검증', selected.status === 'SUCCESS' ? '작업 완료' : '작업 종료'].map((entry, index) => <div key={entry}><i className={index === 7 && selected.status !== 'SUCCESS' ? 'error' : ''}>{index === 7 && selected.status !== 'SUCCESS' ? '!' : '✓'}</i><time>{selected.startedAt ? formatTime(new Date(new Date(selected.startedAt).getTime() + index * 9000).toISOString()) : '-'}</time><span>{entry}</span></div>)}</div></div></Modal>}
  </>;
}
