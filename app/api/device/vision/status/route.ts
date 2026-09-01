import { cameraError, fetchCameraStatus } from '@/lib/deviceProxy';

export async function GET() {
  try {
    const response = await fetchCameraStatus();
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json; charset=utf-8' },
    });
  } catch (error) {
    return cameraError(error);
  }
}
