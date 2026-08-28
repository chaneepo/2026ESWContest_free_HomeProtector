import { mockJobs } from '@/mocks/mockData';
import type { Item, Job, TaskItem } from '@/types';

export interface JobService {
  getJobs(): Promise<Job[]>;
  createJob(type: 'PACK' | 'SORT', items: Item[]): Promise<Job>;
}

export const jobService: JobService = {
  async getJobs() { return mockJobs.map((job) => ({ ...job })); },
  async createJob(type, items) {
    const selected = items.filter((item) => item.enabled).slice(0, 4);
    const tasks: TaskItem[] = selected.map((item) => ({ id: `TASK-${item.id}`, itemId: item.id, itemName: item.name, destination: type === 'PACK' ? '외출 가방' : item.destination, status: 'WAITING' }));
    const sequence = Math.floor(1000 + Math.random() * 8999);
    return { id: `JOB-${sequence}`, type, status: 'RUNNING', currentState: 'PLAN', totalItems: tasks.length, completedItems: 0, retryCount: 0, startedAt: new Date().toISOString(), tasks };
  },
};
