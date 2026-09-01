import { postRaspbotMode, raspbotError } from '@/lib/raspbotProxy';

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as Record<string, unknown>;
    const response = await postRaspbotMode({
      mode: String(payload.mode ?? ''),
      confirm_safe: payload.confirm_safe === true,
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
