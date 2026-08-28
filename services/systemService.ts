import { mockSystemStatus } from '@/mocks/mockData';
import type { SystemStatus } from '@/types';

export interface SystemService {
  getStatus(): Promise<SystemStatus>;
}

export const systemService: SystemService = {
  async getStatus() { return { ...mockSystemStatus }; },
};

// REAL 모드 전환 시 GET /api/system/status로 교체합니다.
