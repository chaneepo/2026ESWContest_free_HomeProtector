import { ControlClient } from './control-client.mjs';

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { speed: 40, duration: 0.2, keyboardEnabled: true, status: {} };
const labels = { forward: '전진', backward: '후진', turn_left: '좌회전', turn_right: '우회전', strafe_left: '왼쪽 평행이동', strafe_right: '오른쪽 평행이동', stop: '정지' };
const keyMap = { ArrowUp: 'forward', ArrowDown: 'backward', ArrowLeft: 'turn_left', ArrowRight: 'turn_right', KeyW: 'forward', KeyS: 'backward', KeyA: 'turn_left', KeyD: 'turn_right', KeyQ: 'strafe_left', KeyE: 'strafe_right' };

function showToast(message) {
  $('#toast').textContent = message;
  $('#toast').classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => $('#toast').classList.remove('show'), 2500);
}
function renderModeControls() {
  const status = state.status;
  $('#safe-mode-button').disabled = false;
  $('#safe-mode-button').classList.toggle('active', !status.movement_enabled);
  $('#hardware-mode-button').classList.toggle('active', !!status.movement_enabled);
  $('#hardware-mode-button').disabled = !status.online || status.client_busy || status.movement_enabled || !$('#hardware-safety-check').checked;
  $$('.drive-button[data-action]').forEach((button) => { button.disabled = !status.movement_enabled || status.client_busy; });
}
const client = new ControlClient('/api/raspbot', (status) => {
  if (state.status.movement_enabled && !status.movement_enabled) $('#hardware-safety-check').checked = false;
  state.status = status;
  $('#connection-pill').classList.toggle('online', !!status.online);
  $('#connection-text').textContent = status.online ? '서버 연결됨' : '연결 미확인 · 이동 잠금';
  $('#last-command').textContent = labels[status.last_action] || '정지';
  $('#command-count').textContent = `총 ${status.command_count || 0}회`;
  $('#safety-banner').classList.toggle('hardware', !!status.movement_enabled);
  $('#mode-title').textContent = status.movement_enabled ? '실기모드 · 이 화면에서 운전 가능' : '이동 잠금';
  $('#mode-description').textContent = status.message;
  $('#activity-title').textContent = status.client_busy ? '명령 처리 중' : '제어 상태';
  $('#activity-message').textContent = status.message;
  $('#activity-time').textContent = new Date().toLocaleTimeString('ko-KR');
  renderModeControls();
});

async function fetchSensors() {
  if (state.status.client_busy || state.status.movement_enabled || !state.status.online) return;
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 2500);
  try {
    const response = await fetch('/api/raspbot/sensors', { cache: 'no-store', signal: abort.signal });
    const sensors = await response.json();
    if (!response.ok) throw new Error(sensors.error || '센서 응답 오류');
    $('#distance-value').textContent = Number(sensors.distance_cm).toFixed(1);
    $$('#sensor-array span').forEach((el, i) => el.classList.toggle('on', !!sensors.line[i]));
  } catch (error) {
    $('#distance-value').textContent = '—';
    $$('#sensor-array span').forEach((el) => el.classList.remove('on'));
    showToast(`센서 확인 실패: ${error.message}`);
  } finally { clearTimeout(timer); }
}
function drive(action) {
  if (action === 'turn_left' || action === 'turn_right') {
    const angle = Number($('#turn-angle').value);
    if (!Number.isFinite(angle) || angle < 1 || angle > 180) { showToast('회전각을 1~180°로 입력하세요.'); return; }
    void client.motion('turn', { direction: action === 'turn_left' ? 'left' : 'right', angle, speed: state.speed });
  } else void client.motion('move', { action, speed: state.speed, duration: state.duration });
}
function renderKeyboardSetting() {
  $('#keyboard-toggle').setAttribute('aria-pressed', String(state.keyboardEnabled));
  $('#keyboard-toggle').classList.toggle('active', state.keyboardEnabled);
  $('#keyboard-state').textContent = state.keyboardEnabled ? 'ON' : 'OFF';
  $('#keyboard-toggle-label').textContent = state.keyboardEnabled ? '키보드 리모컨 켜짐' : '키보드 리모컨 꺼짐';
}
$$('.mode-tab').forEach((button) => button.addEventListener('click', () => {
  client.suspend();
  $$('.mode-tab').forEach((el) => el.classList.toggle('active', el === button));
  $$('.view-panel').forEach((panel) => { panel.hidden = panel.dataset.view !== button.dataset.viewTarget; });
}));
$$('.drive-button[data-action]').forEach((button) => button.addEventListener('click', () => drive(button.dataset.action)));
$('#stop-button').addEventListener('click', () => { $('#hardware-safety-check').checked = false; void client.stop(); });
$('#safe-mode-button').addEventListener('click', () => { $('#hardware-safety-check').checked = false; void client.stop(); });
$('#hardware-mode-button').addEventListener('click', () => {
  void client.arm($('#hardware-safety-check').checked);
  $('#hardware-safety-check').checked = false;
});
$('#hardware-safety-check').addEventListener('change', renderModeControls);
$('#refresh-sensors').addEventListener('click', fetchSensors);
$('#keyboard-toggle').addEventListener('click', () => {
  state.keyboardEnabled = !state.keyboardEnabled;
  if (!state.keyboardEnabled) client.suspend();
  renderKeyboardSetting();
});
$('#speed-slider').addEventListener('input', (event) => {
  state.speed = Number(event.target.value);
  $('#speed-value').textContent = String(state.speed);
});
$$('[data-duration]').forEach((button) => button.addEventListener('click', () => {
  state.duration = Number(button.dataset.duration);
  $('#pulse-value').textContent = state.duration.toFixed(1);
  $$('[data-duration]').forEach((el) => el.classList.toggle('active', el === button));
}));
window.addEventListener('keydown', (event) => {
  if (event.repeat) return;
  if (event.code === 'Escape') { event.preventDefault(); void client.stop(); return; }
  if (event.target instanceof HTMLElement && event.target.closest('input,textarea,select,[contenteditable]')) return;
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  if (event.code === 'Space') { event.preventDefault(); void client.stop(); return; }
  if (state.keyboardEnabled && keyMap[event.code]) { event.preventDefault(); drive(keyMap[event.code]); }
});
window.addEventListener('blur', () => client.suspend());
window.addEventListener('pagehide', () => client.suspend());
document.addEventListener('visibilitychange', () => { if (document.hidden) client.suspend(); });
renderKeyboardSetting();
renderModeControls();
void client.refresh();
setInterval(() => { void client.tick(); }, 1000);
setInterval(fetchSensors, 5000);
