import { mockEvents } from '@/mocks/mockData';
import type { EventLog, EventLevel, EventSource } from '@/types';

export interface EventService {
  getEvents(): Promise<EventLog[]>;
  createEvent(level: EventLevel, source: EventSource, message: string, jobId?: string): EventLog;
}

export const eventService: EventService = {
  async getEvents() { return mockEvents.map((event) => ({ ...event })); },
  createEvent(level, source, message, jobId) {
    return { id: `EV-${Date.now()}-${Math.random().toString(16).slice(2)}`, timestamp: new Date().toISOString(), level, source, message, jobId };
  },
};
