'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui';

const targetClasses = [
  { id: 0, name: 'lighter', label: '라이터' },
  { id: 1, name: 'car_key', label: '자동차 키' },
  { id: 2, name: 'lipstick', label: '립스틱' },
  { id: 3, name: 'lip_balm', label: '립밤' },
];

type CameraStatus = Record<string, unknown>;

export function VisionPage() {
  const [streaming, setStreaming] = useState(false);
  const [streamKey, setStreamKey] = useState(0);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<CameraStatus>({});
  const [message, setMessage] = useState('라즈봇 카메라 연결 확인 중');

  useEffect(() => {
    // The mjpeg stream holds its upstream connection open indefinitely, so polling
    // /status while streaming contends for the same origin's connection pool and
    // times out. The <img> onLoad/onError already reports connection health then.
    if (streaming) return;
    let cancelled = false;
    const checkStatus = async () => {
      try {
        const response = await fetch('/api/device/vision/status', { cache: 'no-store' });
        const data = await response.json();
        if (cancelled) return;
        setConnected(response.ok);
        setStatus(response.ok ? data : {});
        setMessage(response.ok ? '카메라 서버 연결됨' : (data.error || '카메라 서버 연결 실패'));
      } catch {
        if (!cancelled) { setConnected(false); setMessage('카메라 서버 연결 실패'); }
      }
    };
    checkStatus();
    const timer = window.setInterval(checkStatus, 5_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [streaming]);

  const toggleStream = () => {
    if (streaming) {
      setStreaming(false);
      setMessage(connected ? '카메라 서버 연결됨' : '카메라 서버 연결 실패');
      return;
    }
    setStreamKey(Date.now());
    setStreaming(true);
    setMessage('첫 번째 YOLO 프레임을 기다리는 중');
  };

  const modelName = String(status.model ?? status.model_name ?? 'yolo11n-seg.pt');
  const device = String(status.device ?? 'CPU');

  return <>
    <PageHeader eyebrow="RASPBOT U20CAM · YOLO11N" title="실시간 비전 인식" description="라즈봇 위 카메라 영상을 YOLO11n 마스킹 결과와 함께 확인합니다." action={<button className={streaming ? 'secondary outline' : 'primary'} onClick={toggleStream}>{streaming ? '영상 끄기' : '실시간 영상 켜기'}</button>} />
    <div className="vision-layout">
      <section className="panel camera-panel"><div className="panel-head"><div><p>YOLO 실시간 스트림</p><span>U20CAM · 라즈베리파이 /mjpeg</span></div><span className={`status-pill ${connected ? 'online' : 'offline'}`}><i /> {streaming && connected ? 'LIVE' : connected ? '연결됨' : '오프라인'}</span></div><div className={`camera-view live-camera ${streaming ? 'streaming' : ''}`}>
        {streaming ? <img key={streamKey} src={`/api/device/vision/mjpeg?session=${streamKey}`} alt="YOLO11n 실시간 객체 인식 영상" onLoad={() => { setConnected(true); setMessage('YOLO11n 실시간 인식 중'); }} onError={() => { setStreaming(false); setConnected(false); setMessage('영상 스트림을 열 수 없습니다.'); }} /> : <div className="camera-empty"><i>◉</i><b>카메라 대기 중</b><span>{message}</span><button onClick={toggleStream}>스트림 연결</button></div>}
        <div className="live-indicator"><i /> YOLO11N · SEG</div><footer><span>U20CAM 1280 × 720</span><span>입력 320 px</span><span>{device}</span></footer>
      </div></section>
      <aside className="vision-side"><section className="panel vision-runtime"><div className="panel-head"><div><p>추론 상태</p><span>현재 비전 서버 정보</span></div></div><dl className="pose-list"><div><dt>연결 상태</dt><dd className={connected ? 'success-text' : ''}>{message}</dd></div><div><dt>모델</dt><dd>{modelName}</dd></div><div><dt>카메라</dt><dd>/dev/video0</dd></div><div><dt>신뢰도 기준</dt><dd>0.35</dd></div><div><dt>추론 장치</dt><dd>{device}</dd></div></dl></section>
        <section className="panel target-classes"><div className="panel-head"><div><p>CARE-PACK 클래스</p><span>학습 데이터 클래스 번호</span></div></div>{targetClasses.map((item) => <div key={item.id}><i>{item.id}</i><span><b>{item.label}</b><small>{item.name}</small></span></div>)}<p>전용 <code>best.pt</code> 학습 전에는 기본 COCO 클래스만 검출됩니다.</p></section></aside>
    </div>
    <section className="panel vision-guide"><div><b>실시간 확인 순서</b><span>라즈베리파이에서 카메라·YOLO 서버를 켠 뒤 ‘실시간 영상 켜기’를 누르세요.</span></div><ol><li><i>1</i>U20CAM 연결</li><li><i>2</i>YOLO11n 모델 로드</li><li><i>3</i>마스크 오버레이</li><li><i>4</i>웹 스트리밍</li></ol></section>
  </>;
}
