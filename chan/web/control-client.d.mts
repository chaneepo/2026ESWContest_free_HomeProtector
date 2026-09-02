export type ControlStatus = {
  mode?: string; connected?: boolean; online?: boolean; client_busy?: boolean;
  movement_enabled?: boolean; hardware_enabled?: boolean; sensors_enabled?: boolean;
  last_error?: string | null; message?: string; safety_protocol?: number;
  last_action?: string; last_angle?: number | null; command_count?: number;
};
export class ControlClient {
  constructor(base: string, notify?: (status: ControlStatus) => void);
  refresh(): Promise<void>;
  tick(): Promise<void>;
  arm(confirmed: boolean): Promise<void>;
  stop(): Promise<void>;
  motion(path: string, body: Record<string, unknown>): Promise<void>;
  suspend(): void;
}
