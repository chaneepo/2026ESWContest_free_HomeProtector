const state = {
  speed: 40,
  duration: 0.2,
  turnAngle: 45,
  busy: false,
  movementEnabled: false,
  keyboardEnabled: true,
};

const labels = {
  forward: "전진",
  backward: "후진",
  turn_left: "좌회전",
  turn_right: "우회전",
  strafe_left: "왼쪽 평행이동",
  strafe_right: "오른쪽 평행이동",
  stop: "정지",
};

const keyMap = {
  ArrowUp: "forward",
  ArrowDown: "backward",
  ArrowLeft: "turn_left",
  ArrowRight: "turn_right",
  KeyW: "forward",
  KeyS: "backward",
  KeyA: "turn_left",
  KeyD: "turn_right",
  KeyQ: "strafe_left",
  KeyE: "strafe_right",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

function showToast(message, error = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", error);
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), 1800);
}

function setActivity(title, message) {
  $("#activity-title").textContent = title;
  $("#activity-message").textContent = message;
  $("#activity-time").textContent = new Date().toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderKeyboardSetting() {
  const toggle = $("#keyboard-toggle");
  toggle.setAttribute("aria-pressed", String(state.keyboardEnabled));
  toggle.classList.toggle("active", state.keyboardEnabled);
  $("#keyboard-state").textContent = state.keyboardEnabled ? "ON" : "OFF";
  $("#keyboard-toggle-label").textContent = state.keyboardEnabled
    ? "키보드 리모컨 켜짐"
    : "키보드 리모컨 꺼짐";
}

function renderStatus(status) {
  const online = $("#connection-pill");
  online.classList.add("online");
  state.movementEnabled = Boolean(status.movement_enabled);
  $("#connection-text").textContent = status.movement_enabled
    ? "Raspbot 실기 모드"
    : status.sensors_enabled
      ? "Raspbot 연결 · 이동 잠금"
      : "서버 연결 · 데모";
  const commandLabel = labels[status.last_action] || status.last_action;
  $("#last-command").textContent = status.last_angle == null
    ? commandLabel
    : `${commandLabel} ${Number(status.last_angle).toFixed(0)}° (예상)`;
  $("#command-count").textContent = `총 ${status.command_count}회`;

  if (status.hardware_enabled) {
    $("#safety-banner").classList.add("hardware");
    $("#mode-title").textContent = "실제 하드웨어 모드";
    $("#mode-description").textContent = "버튼을 누르면 Raspbot이 짧게 움직입니다. 주변을 비워주세요.";
  } else if (status.sensors_enabled) {
    $("#safety-banner").classList.remove("hardware");
    $("#mode-title").textContent = "센서 점검 모드 · 이동 잠금";
    $("#mode-description").textContent = "실제 센서를 읽고 있지만 모든 바퀴 이동 명령은 차단되어 있습니다.";
  }

  $$(".drive-button[data-action]").forEach((button) => {
    button.disabled = !state.movementEnabled;
  });
}

async function fetchStatus() {
  try {
    renderStatus(await request("/api/status"));
  } catch (error) {
    $("#connection-pill").classList.remove("online");
    $("#connection-text").textContent = "서버 연결 끊김";
    setActivity("연결 오류", error.message);
  }
}

async function fetchSensors() {
  try {
    const sensors = await request("/api/raspbot/sensors");
    $("#distance-value").textContent = Number(sensors.distance_cm).toFixed(1);
    $$("#sensor-array span").forEach((element, index) => {
      element.classList.toggle("on", Boolean(sensors.line[index]));
    });
  } catch (error) {
    showToast(`센서 오류: ${error.message}`, true);
    setActivity("센서 확인 실패", error.message);
  }
}

async function move(action, sourceButton = null) {
  if (!state.movementEnabled) {
    showToast("현재는 센서 점검 모드라 이동이 잠겨 있습니다.", true);
    return;
  }
  if (state.busy) return;
  state.busy = true;
  sourceButton?.classList.add("active");
  setActivity(`${labels[action]} 명령`, `속도 ${state.speed}, ${state.duration.toFixed(1)}초`);
  try {
    const result = await request("/api/raspbot/move", {
      method: "POST",
      body: JSON.stringify({ action, speed: state.speed, duration: state.duration }),
    });
    renderStatus(result);
    showToast(`${labels[action]} 완료 · 자동 정지`);
  } catch (error) {
    showToast(`이동 실패: ${error.message}`, true);
    setActivity("이동 명령 실패", error.message);
  } finally {
    sourceButton?.classList.remove("active");
    state.busy = false;
  }
}

async function turn(action, sourceButton = null) {
  if (!state.movementEnabled) {
    showToast("각도는 입력할 수 있지만 현재 이동은 잠겨 있습니다.", true);
    return;
  }
  const angleInput = $("#turn-angle");
  const angle = Number(angleInput.value);
  if (!Number.isFinite(angle) || angle < 1 || angle > 180) {
    showToast("회전각을 1~180° 사이로 입력하세요.", true);
    angleInput.focus();
    return;
  }
  if (state.busy) return;
  state.busy = true;
  sourceButton?.classList.add("active");
  const direction = action === "turn_left" ? "left" : "right";
  setActivity(`${labels[action]} ${angle}°`, "시간 기반 예상 회전 · 완료 후 자동 정지");
  try {
    const result = await request("/api/raspbot/turn", {
      method: "POST",
      body: JSON.stringify({ direction, angle, speed: state.speed }),
    });
    renderStatus(result);
    showToast(`${labels[action]} ${angle}° 완료 · 자동 정지`);
  } catch (error) {
    showToast(`회전 실패: ${error.message}`, true);
    setActivity("회전 명령 실패", error.message);
  } finally {
    sourceButton?.classList.remove("active");
    state.busy = false;
  }
}

async function stop() {
  try {
    const result = await request("/api/raspbot/stop", { method: "POST", body: "{}" });
    renderStatus(result);
    showToast("모든 모터 정지");
    setActivity("비상 정지", "모든 바퀴에 정지 명령을 전송했습니다.");
  } catch (error) {
    showToast(`정지 실패: ${error.message}`, true);
    setActivity("정지 명령 실패", error.message);
  }
}

function bindControls() {
  $$(".mode-tab").forEach((tabButton) => {
    tabButton.addEventListener("click", () => {
      const target = tabButton.dataset.viewTarget;
      $$(".mode-tab").forEach((item) => item.classList.toggle("active", item === tabButton));
      $$(".view-panel").forEach((panel) => {
        panel.hidden = panel.dataset.view !== target;
      });
    });
  });

  $$(".drive-button[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.dataset.action;
      if (action === "turn_left" || action === "turn_right") {
        turn(action, button);
      } else {
        move(action, button);
      }
    });
  });
  $("#stop-button").addEventListener("click", stop);
  $("#refresh-sensors").addEventListener("click", fetchSensors);
  $("#keyboard-toggle").addEventListener("click", () => {
    state.keyboardEnabled = !state.keyboardEnabled;
    renderKeyboardSetting();
    showToast(
      state.keyboardEnabled
        ? "키보드 리모컨을 켰습니다."
        : "키보드 리모컨을 껐습니다. 화면 버튼은 계속 사용할 수 있습니다.",
    );
  });

  const slider = $("#speed-slider");
  slider.addEventListener("input", () => {
    state.speed = Number(slider.value);
    $("#speed-value").textContent = state.speed;
  });

  const turnAngle = $("#turn-angle");
  turnAngle.addEventListener("input", () => {
    const value = Number(turnAngle.value);
    if (Number.isFinite(value)) state.turnAngle = value;
  });
  turnAngle.addEventListener("blur", () => {
    const value = Math.min(180, Math.max(1, Number(turnAngle.value) || 45));
    state.turnAngle = value;
    turnAngle.value = String(value);
  });

  $$("[data-duration]").forEach((button) => {
    button.addEventListener("click", () => {
      state.duration = Number(button.dataset.duration);
      $("#pulse-value").textContent = state.duration.toFixed(1);
      $$("[data-duration]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  window.addEventListener("keydown", (event) => {
    const isTyping = event.target.matches(
      'input, textarea, select, [contenteditable="true"]',
    );
    if (event.repeat || isTyping) return;
    if (event.code === "Space") {
      event.preventDefault();
      stop();
      return;
    }
    const action = keyMap[event.code];
    if (!action) return;
    event.preventDefault();
    if (!state.keyboardEnabled) {
      showToast("키보드 리모컨이 꺼져 있습니다.", true);
      return;
    }
    const button = $(`[data-action="${action}"]`);
    if (action === "turn_left" || action === "turn_right") {
      turn(action, button);
    } else {
      move(action, button);
    }
  });
}

bindControls();
renderKeyboardSetting();
fetchStatus();
fetchSensors();
setInterval(fetchStatus, 3000);
setInterval(fetchSensors, 5000);
