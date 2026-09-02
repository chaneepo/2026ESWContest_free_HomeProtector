// Shared by the Pi page and the integrated React controller. No automatic arming.
export class ControlClient {
  constructor(base, notify = () => {}, transport = fetch) {
    this.base = base;
    this.notify = notify;
    this.transport = transport;
    this.token = null;
    this.epoch = 0;
    this.status = {};
    this.busy = false;
    this.arming = false;
    this.online = false;
    this.message = '연결 확인 전 · 이동 잠금';
    this.polling = false;
  }
  emit(message = this.message) {
    this.message = message;
    this.notify({ ...this.status, online: this.online,
      movement_enabled: !!(this.token && this.online && this.status.movement_enabled),
      client_busy: this.busy || this.arming, message });
  }
  lock(message) {
    this.epoch++;
    this.token = null;
    this.status = { ...this.status, movement_enabled: false };
    this.emit(message);
  }
  async raw(path, body, timeout = 3000, keepalive = false) {
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), timeout);
    try {
      const response = await this.transport(`${this.base}/${path}`, {
        method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: abort.signal, keepalive,
      });
      const data = await response.json();
      if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
      if (data.safety_protocol !== 2) throw new Error('서버와 UI 버전이 다릅니다. 서버 업데이트 필요');
      return data;
    } finally { clearTimeout(timer); }
  }
  accept(data, epoch) {
    if (epoch !== this.epoch) return false;
    if (this.status.instance_id && data.instance_id !== this.status.instance_id) {
      this.lock('서버 재시작 감지 · 다시 안전 확인 필요');
    } else if ((data.revision ?? 0) < (this.status.revision ?? 0)) return false;
    this.status = data;
    this.online = true;
    if (!data.movement_enabled) this.token = null;
    this.emit(data.last_error || (this.token ? '실기모드 · 이동 가능' : '연결됨 · 이 화면의 이동 잠금'));
    return true;
  }
  bestEffortStop() {
    void this.raw('stop', {}, 2000, true).catch(() => {});
  }
  fail(error) {
    const owned = this.token || this.arming;
    this.online = false;
    this.lock(`이동 잠금: ${error.message}. 정지 미확인 시 본체 전원을 끄세요.`);
    if (owned) this.bestEffortStop();
  }
  async refresh() {
    const epoch = this.epoch;
    try { this.accept(await this.raw('status'), epoch); }
    catch (error) { if (epoch === this.epoch) this.fail(error); }
  }
  async tick() {
    if (this.polling) return;
    this.polling = true;
    const epoch = this.epoch;
    try {
      const data = this.token
        ? await this.raw('heartbeat', { control_token: this.token }, 1500)
        : await this.raw('status');
      this.accept(data, epoch);
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
    finally { this.polling = false; }
  }
  async arm(confirmed) {
    if (!confirmed || this.arming || this.busy || this.token || !this.online || this.status.safety_protocol !== 2) return;
    const epoch = ++this.epoch;
    this.arming = true;
    this.emit('실기 연결 확인 중');
    try {
      const data = await this.raw('mode', { mode: 'hardware', confirm_safe: true });
      if (epoch !== this.epoch) { this.bestEffortStop(); return; }
      if (!data.control_token || !data.movement_enabled) throw new Error('운전 권한 발급 실패');
      // A mode response can legitimately advance the instance following a reconnect.
      this.status = data;
      this.token = data.control_token;
      this.online = true;
      this.emit('실기모드 · 이동 가능');
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
    finally { this.arming = false; this.emit(); }
  }
  async stop() {
    this.lock('정지 요청 중 · 이동 잠금');
    const epoch = this.epoch;
    try {
      const data = await this.raw('stop', {});
      if (this.accept(data, epoch)) this.emit(data.stop_confirmed
        ? '정지 명령 처리됨 · 이동 잠금 (실제 정지 상태도 확인하세요)'
        : '이동 잠금 · 하드웨어 정지는 확인되지 않았습니다');
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
  }
  async motion(path, body) {
    if (!this.token || !this.online || !this.status.movement_enabled || this.busy || this.arming) return;
    const epoch = this.epoch;
    this.busy = true;
    this.emit('이동 명령 처리 중');
    try {
      this.accept(await this.raw(path, { ...body, control_token: this.token }, 5500), epoch);
    } catch (error) { if (epoch === this.epoch) this.fail(error); }
    finally { this.busy = false; this.emit(); }
  }
  suspend() {
    const owned = this.token || this.arming;
    this.lock('화면 비활성화 · 다시 안전 확인 필요');
    if (owned) this.bestEffortStop();
  }
}
