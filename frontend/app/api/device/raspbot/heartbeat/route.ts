import { proxyRaspbotPost } from '@/lib/raspbotProxy';

export function POST(request: Request) {
  return proxyRaspbotPost(request, '/api/raspbot/heartbeat');
}
