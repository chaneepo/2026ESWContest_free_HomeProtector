import { mockArmStatus } from '@/mocks/mockData';
import type { ArmStatus } from '@/types';

export type ArmCommand = 'HOME' | 'SAFE' | 'GRIPPER_OPEN' | 'GRIPPER_CLOSE' | 'STOP';

export interface ArmService {
  getStatus(): Promise<ArmStatus>;
  sendCommand(command: ArmCommand): Promise<{ command: ArmCommand; result: 'SUCCESS' }>;
}

export const armService: ArmService = {
  async getStatus() { return { ...mockArmStatus }; },
  async sendCommand(command) {
    await new Promise((resolve) => setTimeout(resolve, 350));
    return { command, result: 'SUCCESS' };
  },
};

export const armApiContract: Record<ArmCommand, string> = {
  HOME: '/api/arm/home', SAFE: '/api/arm/safe', GRIPPER_OPEN: '/api/arm/gripper/open',
  GRIPPER_CLOSE: '/api/arm/gripper/close', STOP: '/api/arm/stop',
};
