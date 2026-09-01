const DEFAULT_RASPBOT_HOST = '192.168.0.74';

function normalizeBaseUrl(value: string | undefined) {
  const raw = value?.trim() || `http://${DEFAULT_RASPBOT_HOST}:8090`;
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

export const raspbotBaseUrl = normalizeBaseUrl(process.env.RASPBOT_API_URL);

export function raspbotUrl(path: string) {
  return `${raspbotBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

async function request(path: string, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4_000);
  try {
    return await fetch(raspbotUrl(path), {
      cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...init,
    });
  } finally {
    clearTimeout(timeout);
  }
}

export function fetchRaspbotStatus() {
  return request('/api/status');
}

export function postRaspbotMove(body: { action: string; speed: number; duration: number }) {
  return request('/api/move', { method: 'POST', body: JSON.stringify(body) });
}

export function postRaspbotMode(body: { mode: string; confirm_safe: boolean }) {
  return request('/api/raspbot/mode', { method: 'POST', body: JSON.stringify(body) });
}

export function postRaspbotStop() {
  return request('/api/stop', { method: 'POST', body: '{}' });
}

export function raspbotError(error: unknown) {
  const detail = error instanceof Error ? error.message : '라즈봇 컨트롤러에 연결할 수 없습니다.';
  return Response.json({ ok: false, error: '라즈봇 연결 실패', detail }, { status: 503 });
}
