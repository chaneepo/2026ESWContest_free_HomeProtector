# CHAN 통합 제어 구조

## 결론

소스코드의 원본은 맥북의 Git 작업공간에서 관리하고, Raspberry Pi는 배포된
코드를 실행하는 장치로 사용합니다.

```text
MacBook: /Users/jung-yechan/EmbeddedSW/chan
             │
             │ deploy_to_pi.sh
             ▼
Raspberry Pi: /home/tracelab/chan
             │
             ├── /api/raspbot/* ── I2C 0x2B ── Raspbot V2
             │
             └── /api/arm/* (예정) ── RobotUnified_v2 :8000 ── 로봇팔

MacBook/Phone Browser ── http://192.168.0.74:8090 ── 통합 UI
```

## 역할 분리

### 맥북 로컬

- Git 이력과 코드 원본 관리
- UI·API 개발
- 하드웨어 없는 단위 테스트
- Raspberry Pi로 배포

### Raspberry Pi

- `raspbot_ws/venv` Python 환경 사용
- Raspbot I2C 통신
- RobotUnified_v2 ROS2·Klipper·YOLO 실행
- 통합 UI 서버 제공

## 통합 계획

현재 UI의 API는 `/api/raspbot/status`, `/api/raspbot/move`,
`/api/raspbot/stop`, `/api/raspbot/sensors`로 구분했습니다.

로봇팔은 기존 `RobotUnified_v2`의 다음 API를 재사용할 수 있습니다.

- `GET /status`
- `GET /mjpeg`
- `GET /detections`
- `POST /robot/movej`
- `POST /move/axis`
- `POST /move/pose`

로봇팔 이동 UI를 활성화하기 전에는 반드시 별도의 정지 API, 관절 범위 제한,
속도 제한, 통신 끊김 시 정지 처리를 먼저 추가해야 합니다.

## 개발 원칙

1. VS Code의 로컬 `chan` 폴더를 기본 편집 위치로 사용합니다.
2. Raspberry Pi 원격 폴더는 실행·하드웨어 확인에 사용합니다.
3. 원격에서 긴급 수정했다면 반드시 로컬 원본에도 동일하게 반영합니다.
4. 실제 하드웨어 모드는 명시적인 실행 옵션으로만 활성화합니다.
