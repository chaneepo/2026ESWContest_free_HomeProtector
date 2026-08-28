'use client';

import { PageHeader, formatTime } from '@/components/ui';
import { useSystem } from '@/store/SystemProvider';

const grid = ['A1','A2','A3','B1','B2','B3','C1','C2','C3'];

export function VisionPage() {
  const { detections, simulateDetection } = useSystem();
  const latest = detections[0];
  return <>
    <PageHeader eyebrow="RGB 카메라 · APRILTAG" title="비전 인식" description="고정형 카메라의 3×3 작업 영역에서 물품 태그와 위치를 탐지합니다." action={<button className="primary" onClick={simulateDetection}>물품 탐지 시뮬레이션</button>} />
    <div className="vision-layout"><section className="panel camera-panel"><div className="panel-head"><div><p>카메라 작업 영역</p><span>가상 RGB 카메라 · 3×3 그리드</span></div><span className="status-pill online"><i /> 시뮬레이션 연결</span></div><div className="camera-view"><div className="scan-line"/><div className="camera-corners"/><div className="workspace-grid">{grid.map((cell) => { const found = detections.find((detection) => detection.gridPosition === cell); return <div className={found ? 'detected' : ''} key={cell}><span>{cell}</span>{found && <b><i>{found.tagId}</i>{found.itemName}</b>}</div>; })}</div><footer><span>해상도 1280 × 720</span><span>프레임 30 FPS</span><span>OpenCV 시뮬레이션</span></footer></div></section>
      <aside className="vision-side"><section className="panel latest-detection"><div className="panel-head"><div><p>최신 탐지</p><span>가장 최근에 인식된 물품</span></div></div>{latest ? <><div className="tag-title"><i>TAG</i><div><small>{latest.tagId}</small><b>{latest.itemName}</b></div><strong>{latest.gridPosition}</strong></div><dl className="pose-list"><div><dt>탐지 시간</dt><dd>{formatTime(latest.detectedAt)}</dd></div><div><dt>카메라 좌표</dt><dd>X {latest.cameraX ?? '-'} · Y {latest.cameraY ?? '-'} · Z {latest.cameraZ ?? '-'}</dd></div><div><dt>로봇 좌표</dt><dd>{latest.robotX ? `X ${latest.robotX} · Y ${latest.robotY} · Z ${latest.robotZ}` : '좌표 변환 대기'}</dd></div><div><dt>로봇 회전각</dt><dd>{latest.robotYaw !== undefined ? `${latest.robotYaw}°` : '-'}</dd></div></dl></> : <div className="empty-table">탐지 결과가 없습니다.</div>}</section><section className="panel pipeline"><div className="panel-head"><div><p>인식 데이터 흐름</p></div></div>{['카메라', 'AprilTag 탐지', '카메라 좌표', '좌표계 변환', '로봇 좌표', '파지 명령'].map((step, index) => <div key={step}><i>{index + 1}</i><span>{step}</span>{index < 5 && <b>↓</b>}</div>)}</section></aside></div>
    <section className="panel detection-table"><div className="panel-head"><div><p>탐지 이력</p><span>신뢰도 수치 대신 태그·물품·위치를 기록합니다.</span></div></div><table><thead><tr><th>태그 ID</th><th>물품</th><th>그리드</th><th>카메라 X/Y/Z</th><th>로봇 X/Y/Z</th><th>탐지 시간</th></tr></thead><tbody>{detections.map((item) => <tr key={item.id}><td><code>{item.tagId}</code></td><td><b>{item.itemName}</b></td><td><span className="grid-badge">{item.gridPosition}</span></td><td>{item.cameraX ?? '-'} / {item.cameraY ?? '-'} / {item.cameraZ ?? '-'}</td><td>{item.robotX ?? '-'} / {item.robotY ?? '-'} / {item.robotZ ?? '-'}</td><td>{formatTime(item.detectedAt)}</td></tr>)}</tbody></table></section>
  </>;
}
