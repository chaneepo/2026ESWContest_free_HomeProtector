# chan - CARE-PACK Raspbot V2 작업공간

이 폴더는 Raspberry Pi에 이미 설치된 `raspbot==0.1.2` 패키지를 이용해
CARE-PACK 이동 로봇을 개발하기 위한 별도 작업공간입니다.

기존 환경은 수정하지 않습니다.

- 기존 가상환경: `/home/tracelab/raspbot_ws/venv`
- Raspbot I2C 버스: `/dev/i2c-1`
- Raspbot 제어보드 주소: `0x2B`
- 기존 로봇팔 프로젝트: `/home/tracelab/RobotUnified_v2`

## 현재 확인된 상태 (2026-09-01)

- Raspberry Pi 5, Ubuntu 24.04 LTS SSH 접속 확인
- Raspbot V2 제어보드 I2C 주소 `0x2B` 응답 확인
- 라인 센서와 초음파 센서 실제 값 수신 확인
- 네 바퀴를 띄운 상태에서 0.1초 전진 및 자동 정지 시험 완료
- 센서 점검 모드와 실제 하드웨어 모드 분리
- 브라우저 UI 방향키·WASD 이동, 정지, 센서 표시와 좌우 예상 회전각 직접 입력 구현
- Mac 원본과 Raspberry Pi 실행본을 분리한 배포 구조 구성

배터리 충전 및 재가동 후에는 낮은 속도와 0.1초 설정으로 바퀴 방향을 다시
확인합니다. 세부 진행 기록은 [`PROGRESS.md`](./PROGRESS.md), 배선·충전·운영
절차는 [`OPERATIONS.md`](./OPERATIONS.md), 전체 구조는
[`ARCHITECTURE.md`](./ARCHITECTURE.md)를 참고합니다.

## 1. 접속 후 환경 활성화

```bash
ssh tracelab@192.168.0.74
source /home/tracelab/raspbot_ws/venv/bin/activate
cd /home/tracelab/chan
```

## 2. 설치 상태 확인

아래 명령은 모터를 움직이지 않습니다.

```bash
python3 check_setup.py
```

차체와 Raspberry Pi의 I2C 선까지 연결한 뒤 실제 제어보드 응답을 확인하려면:

```bash
python3 check_setup.py --probe
```

`0x2B 응답 정상`이 표시되면 프로그램과 제어보드가 통신 가능한 상태입니다.

## 3. 센서 확인

라인 센서만 5회 읽기:

```bash
python3 read_sensors.py --count 5
```

라인 센서와 초음파 거리 함께 읽기:

```bash
python3 read_sensors.py --count 5 --with-ultrasonic
```

## 4. 모터 안전 시험

1. 로봇을 받침대 위에 올려 네 바퀴를 모두 바닥에서 띄웁니다.
2. 주변 케이블이 바퀴에 닿지 않는지 확인합니다.
3. 처음에는 속도 40, 시간 0.1초만 사용합니다.

```bash
python3 drive_test.py forward \
  --speed 40 \
  --duration 0.1 \
  --confirm-wheels-off-ground
```

지원 동작:

- `forward`, `backward`
- `turn_left`, `turn_right`
- `strafe_left`, `strafe_right`
- `diagonal_forward_left`, `diagonal_forward_right`
- `diagonal_backward_left`, `diagonal_backward_right`
- `stop`

`--confirm-wheels-off-ground`가 없으면 이동 명령은 거부됩니다. 속도는 최대 80,
한 번의 시험 시간은 최대 1초로 제한했습니다. 프로그램 종료 또는 오류 시에도
`stop()`을 호출하도록 구성했습니다.

## 파일 구성

```text
chan/
├── README.md
├── OPERATIONS.md
├── PROGRESS.md
├── ARCHITECTURE.md
├── check_setup.py
├── drive_test.py
├── read_sensors.py
├── server.py
├── requirements.txt
├── web/
├── chan_control/
│   ├── __init__.py
│   └── controller.py
└── tests/
    ├── test_controller.py
    └── test_server.py
```

다음 단계에서는 이 안전 제어 계층 위에 라인 주행, 장애물 정지, AprilTag 정밀
도킹, 로봇팔 인계 API를 순서대로 추가합니다.

## 브라우저 컨트롤러 UI

기본 실행은 모터를 움직이지 않는 데모 모드입니다.

```bash
python3 server.py --host 0.0.0.0 --port 8090
```

맥북 또는 같은 네트워크의 휴대폰에서 다음 주소를 엽니다.

```text
http://192.168.0.74:8090
```

차체 연결과 `python3 check_setup.py --probe` 확인을 마친 후에만 실제 제어 모드를
실행합니다.

실제 센서만 확인하고 이동을 잠그려면:

```bash
python3 -u server.py --host 0.0.0.0 --port 8090 --sensors-only
```

최초 모터 시험까지 통과한 후 실제 제어 모드를 실행합니다.

```bash
python3 -u server.py --host 0.0.0.0 --port 8090 --hardware
```

UI 이동 명령은 한 번 누를 때 기본 0.2초만 동작합니다. 서버에서도 속도 80,
명령 시간 0.5초로 제한하며 모든 이동 명령이 끝날 때 모터 정지를 호출합니다.

키보드 운전:

- `↑` 또는 `W`: 전진
- `↓` 또는 `S`: 후진
- `←` 또는 `A`: 좌회전
- `→` 또는 `D`: 우회전
- `Q` / `E`: 좌우 평행이동
- `Space`: 모든 모터 정지

방향키를 길게 눌러도 키 반복 입력은 무시하며, 한 번 누를 때 선택한 시간만큼
움직인 뒤 자동으로 정지합니다. 화면 옆 `REMOTE SETTING` 버튼으로 키보드
리모컨만 켜거나 끌 수 있으며, 화면의 이동 버튼과 STOP은 계속 사용할 수
있습니다. 키보드 리모컨이 꺼져 있어도 스페이스바 정지는 항상 작동합니다.

좌·우회전은 UI의 숫자 입력칸에 `1~180°`를 직접 입력할 수 있습니다. 바퀴에는
절대각 센서가 없으므로 입력값은 시간으로 환산한 예상 각도이며, 기본 보정값은
속도 40에서 90°당 1초입니다. 실제 바닥과 배터리 상태에 맞춰 보정해야 합니다.

## 충전기

Raspbot V2는 Yahboom 전용 `8.4V 2A DC4017` 충전기를 사용합니다. USB-A나
Raspberry Pi USB-C 어댑터로 충전하지 않습니다. 본체 전원 스위치를 `OFF`로
둔 상태에서 제어보드의 원형 충전 단자에 연결합니다.

- 충전기 LED 빨간색: 충전 중
- 충전기 LED 초록색: 충전 완료
- 충전기만 콘센트에 꽂아도 LED가 꺼짐: 콘센트 또는 충전기 점검 필요

충전 상태는 제어보드 LED가 아니라 충전기 어댑터 본체의 LED로 확인합니다.
