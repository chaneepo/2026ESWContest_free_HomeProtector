'use client';

import { useEffect, useRef, useState } from 'react';
import { ControlClient, type ControlStatus } from '../../raspbot_runtime/web/control-client.mjs';

const directions = [
  ['turn_left', '↶', '좌회전', 'remote-turn-left'],
  ['forward', '↑', '전진', 'remote-forward'],
  ['turn_right', '↷', '우회전', 'remote-turn-right'],
  ['strafe_left', '←', '좌 이동', 'remote-left'],
  ['stop', '■', '정지', 'remote-stop'],
  ['strafe_right', '→', '우 이동', 'remote-right'],
  ['backward', '↓', '후진', 'remote-backward'],
];
const keyToAction: Record<string, string> = {
  ArrowUp: 'forward', KeyW: 'forward', ArrowDown: 'backward', KeyS: 'backward',
  ArrowLeft: 'turn_left', KeyA: 'turn_left', ArrowRight: 'turn_right', KeyD: 'turn_right',
  KeyQ: 'strafe_left', KeyE: 'strafe_right',
};

export function RaspbotRemote({ emergencyLocked = false }: { emergencyLocked?: boolean }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<ControlStatus>({});
  const [safetyChecked, setSafetyChecked] = useState(false);
  const client = useRef<ControlClient | null>(null);
  const movementEnabled = !!status.movement_enabled && !status.client_busy && !emergencyLocked;

  useEffect(() => {
    if (emergencyLocked) client.current?.suspend();
  }, [emergencyLocked]);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    const control = new ControlClient('/api/device/raspbot', (next) => {
      if (mounted) setStatus(next);
    });
    client.current = control;
    void control.refresh();
    const timer = window.setInterval(() => { void control.tick(); }, 1000);
    const suspend = () => { control.suspend(); setSafetyChecked(false); };
    const visibility = () => { if (document.hidden) suspend(); };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      if (event.code === 'Escape') { event.preventDefault(); void control.stop(); return; }
      if (event.target instanceof HTMLElement && event.target.closest('input,textarea,select,[contenteditable]')) return;
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.code === 'Space') { event.preventDefault(); void control.stop(); return; }
      const action = keyToAction[event.code];
      if (action) {
        event.preventDefault();
        void control.motion('move', { action, speed: 40, duration: 0.2 });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('blur', suspend);
    window.addEventListener('chan-emergency-stop', suspend);
    window.addEventListener('pagehide', suspend);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('blur', suspend);
      window.removeEventListener('chan-emergency-stop', suspend);
      window.removeEventListener('pagehide', suspend);
      document.removeEventListener('visibilitychange', visibility);
      control.suspend();
      client.current = null;
    };
  }, [open]);

  return <div className={`raspbot-remote ${open ? 'open' : ''}`}>
    {open && <aside className="remote-panel" aria-label="라즈봇 방향 리모컨">
      <header><div><small>RASPBOT V2</small><b>방향 리모컨</b></div><span><i className={status.online ? 'dot green' : 'dot red'} />{status.message || '연결 확인 중 · 이동 잠금'}</span></header>
      <div className="remote-mode-switch">
        <label><input type="checkbox" checked={safetyChecked} onChange={(event) => setSafetyChecked(event.target.checked)} /><span>주변에 사람·케이블 없음</span></label>
        <div>
          <button type="button" className={!status.movement_enabled ? 'active' : ''} onClick={() => { setSafetyChecked(false); void client.current?.stop(); }}>안전모드</button>
          <button type="button" disabled={emergencyLocked || !status.online || status.client_busy || !!status.movement_enabled || !safetyChecked} className={status.movement_enabled ? 'active' : ''} onClick={() => { void client.current?.arm(safetyChecked); setSafetyChecked(false); }}>실기모드</button>
        </div>
      </div>
      <div className="remote-pad">{directions.map(([action, icon, label, area]) => <button
        key={action} className={area} aria-label={label}
        disabled={action !== 'stop' && !movementEnabled}
        onClick={() => { if (action === 'stop') { setSafetyChecked(false); void client.current?.stop(); } else void client.current?.motion('move', { action, speed: 40, duration: 0.2 }); }}
      ><strong>{icon}</strong><small>{label}</small></button>)}</div>
      <p>{status.movement_enabled ? '방향키/WASD 이동 · Q/E 평행이동 · Space/Esc 정지' : '안전 확인 후 실기모드로 전환하세요. 통신 끊김·창 전환·STOP 후에는 다시 잠깁니다.'}</p>
    </aside>}
    <button className="remote-toggle" aria-expanded={open} onClick={() => { if (open) client.current?.suspend(); setSafetyChecked(false); setOpen(!open); }}>
      <span>{open ? '×' : '✥'}</span>{open ? '리모컨 닫기' : '라즈봇 리모컨'}
    </button>
  </div>;
}
