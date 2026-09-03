export type SystemMode = 'SIMULATION' | 'REAL';
export type DeviceConnectionStatus = 'ONLINE' | 'OFFLINE' | 'BUSY' | 'ERROR';
export type JobStatus = 'WAITING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED';
export type ExecutionState = 'IDLE' | 'PLAN' | 'DETECT' | 'PICK' | 'MOVE' | 'PLACE' | 'VERIFY' | 'RECOVER' | 'COMPLETE' | 'ERROR';
export type EventLevel = 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
export type EventSource = 'SYSTEM' | 'VISION' | 'ARM' | 'ESP32' | 'RAZBOT';
export type PageKey = 'dashboard' | 'automatic' | 'manual' | 'vision' | 'items' | 'history';
export type FailureTarget = 'NONE' | 'PICK' | 'VERIFY';

export interface SystemStatus {
  mode: SystemMode;
  currentState: ExecutionState;
  emergencyStop: boolean;
  armStatus: DeviceConnectionStatus;
  visionStatus: DeviceConnectionStatus;
  esp32Status: DeviceConnectionStatus;
  razbotStatus: DeviceConnectionStatus;
}

export interface Item {
  id: number;
  tagId: string;
  name: string;
  category: string;
  destination: string;
  enabled: boolean;
}

export interface DetectionResult {
  id: string;
  tagId: string;
  itemId?: number;
  itemName?: string;
  gridPosition?: string;
  cameraX?: number;
  cameraY?: number;
  cameraZ?: number;
  robotX?: number;
  robotY?: number;
  robotZ?: number;
  robotYaw?: number;
  detectedAt: string;
}

export interface TaskItem {
  id: string;
  itemId: number;
  itemName: string;
  destination: string;
  status: 'WAITING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
}

export interface Job {
  id: string;
  type: 'PACK' | 'SORT' | 'DELIVERY' | 'EMERGENCY';
  status: JobStatus;
  currentState: ExecutionState;
  currentItem?: string;
  totalItems: number;
  completedItems: number;
  retryCount: number;
  startedAt?: string;
  completedAt?: string;
  durationSeconds?: number;
  failureReason?: string;
  tasks?: TaskItem[];
}

export interface EventLog {
  id: string;
  timestamp: string;
  level: EventLevel;
  source: EventSource;
  message: string;
  jobId?: string;
}

export interface ArmStatus {
  connection: DeviceConnectionStatus;
  state: ExecutionState;
  currentTask: string;
  lastCommand: string;
  lastResult: 'SUCCESS' | 'FAILED' | '-';
}

export interface SimulationStep {
  state: ExecutionState;
  level: EventLevel;
  source: EventSource;
  message: string;
}
