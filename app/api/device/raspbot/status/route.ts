import { fetchRaspbotStatus, raspbotError } from '@/lib/raspbotProxy';

export async function GET() {
  try {
    const response = await fetchRaspbotStatus();
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json; charset=utf-8' },
    });
  } catch (error) {
    return raspbotError(error);
  }
}
