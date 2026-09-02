'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const directions = [
  { key: 'turn-left', action: 'turn_left', icon: '↶', label: '좌회전', area: 'remote-turn-left' },
  { key: 'forward', action: 'forward', icon: '↑', label: '전진', area: 'remote-forward' },
  { key: 'turn-right', action: 'turn_right', icon: '↷', label: '우회전', area: 'remote-turn-right' },
  { key: 'left', action: 'strafe_left', icon: '←', label: '좌 이동', area: 'remote-left' },
  { key: 'stop', action: 'stop', icon: '■', label: '정지', area: 'remote-stop' },
  { key: 'right', action: 'strafe_right', icon: '→', label: '우 이동', area: 'remote-right' },
  { key: 'backward', action: 'backward', icon: '↓', label: '후진', area: 'remote-backward' },
];

const keyToAction: Record<string, string> = {
  ArrowUp: 'forward',
  KeyW: 'forward',
  ArrowDown: 'backward',
  KeyS: 'backward',
  ArrowLeft: 'turn_left',
  KeyA: 'turn_left',
  ArrowRight: 'turn_right',
  KeyD: 'turn_right',
  KeyQ: 'strafe_left',
  KeyE: 'strafe_right',
};

type RaspbotStatus = {
  mode?: string;
  movement_enabled?: boolean;
  connected?: boolean;
  last_error?: string | null;
  error?: string;
};

export function RaspbotRemote() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<RaspbotStatus>({});
  const [connected, setConnected] = useState(false);
  const [safetyChecked, setSafetyChecked] = useState(false);
  const [modeBusy, setModeBusy] = useState(false);
  const [message, setMessage] = useState('실기 제어 연결 전');
  const movementEnabled = Boolean(status.movement_enabled);
  const movementEnabledRef = useRef(movementEnabled);
  movementEnabledRef.current = movementEnabled;

  const failureStreakRef = useRef(0);

  const fetchOnce = async () => {
    const response = await fetch('/api/device/raspbot/status', { cache: 'no-store' });
    const data = (await response.json()) as RaspbotStatus;
    if (!response.ok) throw new Error(data.error || '라즈봇 연결 실패');
    return data;
  };

  const refreshStatus = useCallback(async () => {
    try {
      let data: RaspbotStatus;
      try {
        data = await fetchOnce();
      } catch {
        // The dev fetch runtime occasionally drops a single request -- retry
        // once immediately before counting this poll as a real miss.
        await new Promise((resolve) => setTimeout(resolve, 300));
        data = await fetchOnce();
      }
      failureStreakRef.current = 0;
      setConnected(true);
      setStatus(data);
      setMessage(data.movement_enabled ? '실기모드 · 이동 가능' : `${data.mode ?? '센서'} 모드 · 이동 잠금`);
    } catch {
      // A single dropped poll is normal dev-server/network jitter, not a real
      // outage -- only flip to disconnected after a couple of misses in a row
      // so the badge doesn't flap on every transient hiccup.
      failureStreakRef.current += 1;
      if (failureStreakRef.current >= 2) {
        setConnected(false);
        setMessage('라즈봇 연결 실패');
      }
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    refreshStatus();
    const timer = window.setInterval(refreshStatus, 3_000);
    return () => window.clearInterval(timer);
  }, [open, refreshStatus]);

  const sendMove = useCallback(async (action: string) => {
    if (action === 'stop') {
      await fetch('/api/device/raspbot/stop', { method: 'POST' });
      setMessage('정지 명령 전송');
      return;
    }
    if (!movementEnabledRef.current) {
      setMessage('실기모드에서만 이동할 수 있습니다');
      return;
    }
    setMessage(`${action} 전송 중`);
    const response = await fetch('/api/device/raspbot/move', {
      method: 'POST',
      body: JSON.stringify({ action, speed: 40, duration: 0.2 }),
    });
    const data = (await response.json()) as RaspbotStatus;
    setMessage(response.ok ? `${action} 전송됨` : data.error || '이동 명령 실패');
  }, []);

  const switchMode = useCallback(async (mode: 'safe' | 'hardware') => {
    if (modeBusy) return;
    if (mode === 'hardware' && !safetyChecked) {
      setMessage('주변 안전 확인을 먼저 체크하세요');
      return;
    }
    setModeBusy(true);
    setMessage(mode === 'hardware' ? '실기모드 전환 중' : '안전모드 전환 중');
    try {
      const response = await fetch('/api/device/raspbot/mode', {
        method: 'POST',
        body: JSON.stringify({ mode, confirm_safe: mode === 'hardware' }),
      });
      const data = (await response.json()) as RaspbotStatus;
      if (response.ok) {
        setStatus(data);
        setConnected(true);
        if (mode === 'hardware') setSafetyChecked(false);
        setMessage(mode === 'hardware' ? '실기모드로 전환했습니다' : '안전모드로 전환하고 모터를 정지했습니다');
      } else {
        setMessage(data.error || '모드 전환 실패');
      }
    } catch {
      setMessage('모드 전환 실패');
    } finally {
      setModeBusy(false);
    }
  }, [modeBusy, safetyChecked]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      if (event.code === 'Space') {
        event.preventDefault();
        sendMove('stop');
        return;
      }
      const action = keyToAction[event.code];
      if (action) {
        event.preventDefault();
        sendMove(action);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, sendMove]);

  return <div className={`raspbot-remote ${open ? 'open' : ''}`}>
    {open && <aside className="remote-panel" aria-label="라즈봇 방향 리모컨">
      <header><div><small>RASPBOT V2</small><b>방향 리모컨</b></div><span><i className={connected ? 'dot green' : 'dot red'} />{message}</span></header>
      <div className="remote-mode-switch">
        <label><input type="checkbox" checked={safetyChecked} onChange={(event) => setSafetyChecked(event.target.checked)} /><span>주변에 사람·케이블 없음</span></label>
        <div>
          <button type="button" disabled={modeBusy} className={status.mode !== 'hardware' ? 'active' : ''} onClick={() => switchMode('safe')}>안전모드</button>
          <button type="button" disabled={modeBusy || !safetyChecked} className={status.mode === 'hardware' ? 'active' : ''} onClick={() => switchMode('hardware')}>실기모드</button>
        </div>
      </div>
      <div className="remote-pad">{directions.map((direction) => <button
        key={direction.key}
        className={direction.area}
        aria-label={direction.label}
        disabled={direction.action !== 'stop' && !movementEnabled}
        onClick={() => sendMove(direction.action)}
      ><strong>{direction.icon}</strong><small>{direction.label}</small></button>)}</div>
      <p>{movementEnabled ? '방향키/WASD로 이동, Q/E 평행이동, Space 정지' : '실기모드로 전환하면 방향키로 이동할 수 있습니다.'}</p>
    </aside>}
    <button className="remote-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span>{open ? '×' : '✥'}</span>{open ? '리모컨 닫기' : '라즈봇 리모컨'}
    </button>
  </div>;
}
