import type { ArmStatus, DetectionResult, EventLog, Item, Job, SystemStatus } from '@/types';

export const mockSystemStatus: SystemStatus = {
  mode: 'SIMULATION', currentState: 'IDLE', emergencyStop: false,
  armStatus: 'ONLINE', visionStatus: 'ONLINE', esp32Status: 'OFFLINE', razbotStatus: 'OFFLINE',
};

export const mockArmStatus: ArmStatus = {
  connection: 'ONLINE', state: 'IDLE', currentTask: '-', lastCommand: 'HOME', lastResult: 'SUCCESS',
};

export const mockItems: Item[] = [
  { id: 1, tagId: 'TAG-001', name: '약통', category: '의료용품', destination: '침실', enabled: true },
  { id: 2, tagId: 'TAG-002', name: '물병', category: '일상용품', destination: '주방', enabled: true },
  { id: 3, tagId: 'TAG-003', name: '차키', category: '개인용품', destination: '현관', enabled: true },
  { id: 4, tagId: 'TAG-004', name: '마스크', category: '위생용품', destination: '외출 가방', enabled: true },
  { id: 5, tagId: 'TAG-005', name: '핫팩', category: '일상용품', destination: '외출 가방', enabled: true },
];

const now = new Date('2026-08-28T14:32:00+09:00').getTime();
export const mockDetections: DetectionResult[] = [
  { id: 'DET-001', tagId: 'TAG-001', itemId: 1, itemName: '약통', gridPosition: 'A1', cameraX: 124, cameraY: 83, cameraZ: 412, robotX: 188, robotY: -72, robotZ: 34, robotYaw: 0, detectedAt: new Date(now - 120000).toISOString() },
  { id: 'DET-002', tagId: 'TAG-003', itemId: 3, itemName: '차키', gridPosition: 'B2', cameraX: 306, cameraY: 216, cameraZ: 408, detectedAt: new Date(now - 76000).toISOString() },
];

export const mockEvents: EventLog[] = [
  { id: 'EV-003', timestamp: new Date(now - 12000).toISOString(), level: 'SUCCESS', source: 'SYSTEM', message: '시뮬레이션 서비스가 준비되었습니다.' },
  { id: 'EV-002', timestamp: new Date(now - 24000).toISOString(), level: 'INFO', source: 'VISION', message: '비전 카메라 연결 상태를 확인했습니다.' },
  { id: 'EV-001', timestamp: new Date(now - 33000).toISOString(), level: 'INFO', source: 'ARM', message: 'SO-ARM101이 HOME 위치에 있습니다.' },
];

export const mockJobs: Job[] = [
  { id: 'JOB-0103', type: 'PACK', status: 'SUCCESS', currentState: 'COMPLETE', totalItems: 4, completedItems: 4, retryCount: 0, startedAt: new Date(now - 5400000).toISOString(), completedAt: new Date(now - 5326000).toISOString(), durationSeconds: 74 },
  { id: 'JOB-0102', type: 'SORT', status: 'SUCCESS', currentState: 'COMPLETE', totalItems: 3, completedItems: 3, retryCount: 1, startedAt: new Date(now - 10800000).toISOString(), completedAt: new Date(now - 10712000).toISOString(), durationSeconds: 88 },
  { id: 'JOB-0101', type: 'PACK', status: 'FAILED', currentState: 'ERROR', totalItems: 4, completedItems: 2, retryCount: 2, failureReason: '검증 센서 응답 시간 초과', startedAt: new Date(now - 86400000).toISOString(), completedAt: new Date(now - 86304000).toISOString(), durationSeconds: 96 },
];
