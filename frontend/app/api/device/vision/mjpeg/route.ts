import { cameraError, cameraUrl } from '@/lib/deviceProxy';

export async function GET() {
  try {
    const upstream = await fetch(cameraUrl('/mjpeg'), {
      cache: 'no-store',
      headers: { Accept: 'multipart/x-mixed-replace' },
    });
    if (!upstream.ok || !upstream.body) {
      return Response.json({ ok: false, error: `카메라 스트림 응답 오류 (${upstream.status})` }, { status: 502 });
    }
    return new Response(upstream.body, {
      headers: {
        'Content-Type': upstream.headers.get('content-type') || 'multipart/x-mixed-replace; boundary=frame',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        Pragma: 'no-cache',
      },
    });
  } catch (error) {
    return cameraError(error);
  }
}
