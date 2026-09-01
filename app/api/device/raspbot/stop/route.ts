import { postRaspbotStop, raspbotError } from '@/lib/raspbotProxy';

export async function POST() {
  try {
    const response = await postRaspbotStop();
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json; charset=utf-8' },
    });
  } catch (error) {
    return raspbotError(error);
  }
}
