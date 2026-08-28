'use client';

import { EventList, PageHeader, stateLabel } from '@/components/ui';
import { armApiContract, type ArmCommand } from '@/services/armService';
import { useSystem } from '@/store/SystemProvider';

const commands: { command: ArmCommand; label: string; description: string; icon: string; danger?: boolean }[] = [
  { command: 'HOME', label: 'HOME 위치', description: '기본 대기 자세로 이동', icon: '⌂' },
  { command: 'SAFE', label: '안전 위치', description: '충돌 위험이 낮은 위치로 이동', icon: '◇' },
  { command: 'GRIPPER_OPEN', label: '그리퍼 열기', description: '파지 장치를 완전히 열기', icon: '〈 〉' },
  { command: 'GRIPPER_CLOSE', label: '그리퍼 닫기', description: '파지 장치를 안전하게 닫기', icon: '〉〈' },
  { command: 'STOP', label: '로봇팔 정지', description: '현재 동작을 즉시 중단', icon: '■', danger: true },
];

export function ManualPage() {
  const { arm, events, status, sendArmCommand } = useSystem();
  return <>
    <PageHeader eyebrow="SO-ARM101 명령 인터페이스" title="수동 제어" description="로봇팔 제어 명령을 안전하게 테스트합니다. 현재는 모든 명령이 시뮬레이션으로만 실행됩니다." />
    <section className="simulation-warning"><i>SIM</i><div><b>실물 하드웨어 제어 안 함</b><p>버튼은 서비스 계층의 가상 제어기로만 연결됩니다.</p></div><span>연결: 시뮬레이션 어댑터</span></section>
    <div className="manual-layout"><section className="panel arm-visual"><div className="panel-head"><div><p>SO-ARM101 상태</p><span>수동 제어기 실시간 상태</span></div><span className="status-pill online"><i /> 온라인</span></div><div className="arm-stage"><div className="robot-illustration"><div className="arm-base"/><div className="arm-joint one"/><div className="arm-link first"/><div className="arm-joint two"/><div className="arm-link second"/><div className="arm-gripper"/></div><span>시뮬레이션 표시</span></div><dl className="status-grid"><div><dt>연결</dt><dd className="success-text">온라인</dd></div><div><dt>현재 상태</dt><dd>{stateLabel[arm.state]}</dd></div><div><dt>현재 작업</dt><dd>{arm.currentTask}</dd></div><div><dt>마지막 명령</dt><dd>{arm.lastCommand}</dd></div><div><dt>마지막 결과</dt><dd className={arm.lastResult === 'SUCCESS' ? 'success-text' : ''}>{arm.lastResult === 'SUCCESS' ? '성공' : arm.lastResult}</dd></div></dl></section>
      <section className="panel command-panel"><div className="panel-head"><div><p>로봇팔 명령</p><span>원하는 제어 명령을 선택하세요.</span></div></div><div className="command-list">{commands.map((item) => <button className={item.danger ? 'danger-command' : ''} key={item.command} disabled={status.emergencyStop && item.command !== 'STOP'} onClick={() => sendArmCommand(item.command)}><i>{item.icon}</i><div><b>{item.label}</b><small>{item.description}</small><code>{armApiContract[item.command]}</code></div><span>실행 →</span></button>)}</div></section>
    </div><section className="panel command-events"><div className="panel-head"><div><p>수동 명령 기록</p><span>로봇팔 서비스에서 발생한 이벤트</span></div></div><EventList events={events.filter((event) => event.source === 'ARM')} limit={6} /></section>
  </>;
}
