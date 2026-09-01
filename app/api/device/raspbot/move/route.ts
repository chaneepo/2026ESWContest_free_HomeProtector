import { postRaspbotMove, raspbotError } from '@/lib/raspbotProxy';

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const response = await postRaspbotMove({
      action: String(payload.action ?? ''),
      speed: Number(payload.speed ?? 40),
      duration: Number(payload.duration ?? 0.2),
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json; charset=utf-8' },
    });
  } catch (error) {
    return raspbotError(error);
  }
}
