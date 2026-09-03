const DEFAULT_CAMERA_HOST = '192.168.0.73';

function normalizeBaseUrl(value: string | undefined) {
  const raw = value?.trim() || `http://${DEFAULT_CAMERA_HOST}:8000`;
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

export const cameraBaseUrl = normalizeBaseUrl(process.env.CAMERA_API_URL);

export function cameraUrl(path: string) {
  return `${cameraBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function fetchCameraStatus() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4_000);
  try {
    return await fetch(cameraUrl('/status'), {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

export function cameraError(error: unknown) {
  const detail = error instanceof Error ? error.message : '카메라 장치에 연결할 수 없습니다.';
  return Response.json({ ok: false, error: '라즈봇 카메라 연결 실패', detail }, { status: 503 });
}
