import { mockDetections } from '@/mocks/mockData';
import type { DetectionResult, Item } from '@/types';

export interface VisionService {
  getDetections(): Promise<DetectionResult[]>;
  simulateDetection(items: Item[]): Promise<DetectionResult>;
}

const grids = ['A1', 'A2', 'B1', 'B2', 'B3', 'C2'];
export const visionService: VisionService = {
  async getDetections() { return mockDetections.map((item) => ({ ...item })); },
  async simulateDetection(items) {
    const candidates = items.filter((item) => item.enabled);
    const item = candidates[Math.floor(Math.random() * candidates.length)] ?? items[0];
    const gridPosition = grids[Math.floor(Math.random() * grids.length)];
    return {
      id: `DET-${Date.now()}`, tagId: item.tagId, itemId: item.id, itemName: item.name, gridPosition,
      cameraX: Math.round(90 + Math.random() * 280), cameraY: Math.round(60 + Math.random() * 190),
      cameraZ: Math.round(390 + Math.random() * 30), detectedAt: new Date().toISOString(),
    };
  },
};
