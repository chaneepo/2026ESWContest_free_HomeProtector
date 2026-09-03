function normalizeBaseUrl(value: string | undefined) {
  const raw = value?.trim() || '';
  return raw.endsWith('/') ? raw.slice(0, -1) : raw;
}

export const raspbotBaseUrl = normalizeBaseUrl(process.env.RASPBOT_API_URL);

export function raspbotUrl(path: string) {
  if (!raspbotBaseUrl) throw new Error('RASPBOT_API_URL 설정이 필요합니다. 기기 주소를 먼저 확인하세요.');
  return `${raspbotBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

async function send(path: string, init?: RequestInit) {
  const controller = new AbortController();
  // Generous enough to cover a full-length turn() pulse (up to 4s) blocking
  // the upstream response before it replies.
  const timeout = setTimeout(() => controller.abort(), 6_000);
  try {
    const response = await fetch(raspbotUrl(path), {
      cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...init,
    });
    const body = await response.text(); // Keep the timeout active while reading the body.
    return new Response(body, { status: response.status, headers: {
      'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
    } });
  } finally {
    clearTimeout(timeout);
  }
}

export function fetchRaspbotStatus() {
  return send('/api/status');
}

export function raspbotError(error: unknown) {
  const detail = error instanceof Error ? error.message : '라즈봇 컨트롤러에 연결할 수 없습니다.';
  return Response.json({ ok: false, error: '라즈봇 연결 실패', detail }, { status: 503 });
}

// Forwards the caller's JSON body as-is (control_token included) so the proxy
// never has to know each endpoint's exact field list.
export async function proxyRaspbotPost(incoming: Request, upstreamPath: string): Promise<Response> {
  const origin = incoming.headers.get('origin');
  if (incoming.headers.get('sec-fetch-site') === 'cross-site' || (origin && origin !== new URL(incoming.url).origin)) {
    return Response.json({ ok: false, error: '외부 웹사이트의 제어 요청은 차단됩니다.' }, { status: 403 });
  }
  if (incoming.headers.get('content-type')?.split(';')[0].trim() !== 'application/json') {
    return Response.json({ ok: false, error: 'application/json 요청이 필요합니다.' }, { status: 415 });
  }
  try {
    let payload;
    try { payload = await incoming.json(); }
    catch { return Response.json({ ok: false, error: '잘못된 JSON입니다.' }, { status: 400 }); }
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return Response.json({ ok: false, error: 'JSON object required' }, { status: 400 });
    }
    const response = await send(upstreamPath, { method: 'POST', body: JSON.stringify(payload ?? {}) });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json; charset=utf-8', 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    return raspbotError(error);
  }
}
