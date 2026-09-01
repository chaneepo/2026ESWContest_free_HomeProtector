# CHAN Raspbot 운영 가이드

Raspberry Pi 5와 Yahboom Raspbot V2를 처음 연결하고 웹 UI로 운행할 때 사용하는 절차입니다.

## 현재 구성

- Raspberry Pi: Raspberry Pi 5 Model B
- 운영체제: Ubuntu 24.04 LTS
- 프로젝트 경로: `/home/tracelab/chan`
- Python 가상환경: `/home/tracelab/raspbot_ws/venv`
- 웹 UI 기본 주소: `http://192.168.0.74:8090`
- Raspbot I2C 주소: `0x2B`

IP 주소는 네트워크 환경에 따라 변경될 수 있습니다.

## I2C 배선

Raspberry Pi 40핀 헤더의 물리 핀 번호를 기준으로 연결합니다.

| Raspbot 선 | 기능 | Raspberry Pi 물리 핀 | GPIO |
| --- | --- | ---: | ---: |
| 노란색 | SDA | 3번 | GPIO2 |
| 초록색 | SCL | 5번 | GPIO3 |
| 검은색 | GND | 6번 | GND |

전원이 켜진 상태에서는 배선을 꽂거나 빼지 않습니다.

연결 확인:

```bash
i2cdetect -y -a 1
```

표에 `2b`가 표시되면 Raspbot 제어 보드가 연결된 것입니다.

## Mac에서 접속

Mac과 Raspberry Pi를 같은 네트워크에 연결한 뒤 터미널에서 실행합니다.

```bash
ssh tracelab@192.168.0.74
```

## 센서 점검 모드

센서는 실제 값을 읽지만 모든 이동 명령을 차단합니다.

```bash
cd ~/chan
source ~/raspbot_ws/venv/bin/activate
python3 -u server.py --host 0.0.0.0 --port 8090 --sensors-only
```

Mac 브라우저에서 `http://192.168.0.74:8090`을 엽니다.

## 최초 모터 시험

다음 조건을 모두 만족한 상태에서만 실행합니다.

1. 바퀴 네 개를 모두 바닥에서 띄웁니다.
2. 손과 케이블을 바퀴에서 치웁니다.
3. 전원 스위치를 즉시 끌 수 있게 준비합니다.

```bash
cd ~/chan
source ~/raspbot_ws/venv/bin/activate
python3 drive_test.py forward --speed 40 --duration 0.1 --confirm-wheels-off-ground
```

네 바퀴가 전진 방향으로 짧게 회전하고 자동으로 정지하는지 확인합니다.

## 실제 운행 모드

최초 모터 시험을 통과한 후에만 실행합니다.

```bash
cd ~/chan
source ~/raspbot_ws/venv/bin/activate
python3 -u server.py --host 0.0.0.0 --port 8090 --hardware
```

UI의 이동 버튼과 `WASD`, `QE` 키가 실제 바퀴를 움직입니다. 처음에는 속도 `20`, 이동 시간 `0.1초`로 시험합니다. `STOP` 버튼 또는 스페이스바는 모든 모터에 정지 명령을 전송합니다.

좌우 회전각은 센서 피드백이 아닌 시간 기반 예상값입니다. 실제 바닥과 배터리 상태에 따라 오차가 생기므로 현장에서 보정해야 합니다.

## 배터리와 충전

Raspbot V2는 Yahboom 전용 `8.4V 2A DC4017` 충전기를 사용합니다. 일반 USB-A
케이블이나 Raspberry Pi USB-C 전원 어댑터는 Raspbot 배터리 충전기가 아닙니다.

정상 충전 순서:

1. UI에서 `STOP`을 누르고 서버에 동작 명령을 보내지 않습니다.
2. Raspbot 제어보드의 주 전원 스위치를 `OFF`로 둡니다.
3. 전용 충전기를 정상 콘센트에 연결합니다.
4. 충전기의 가느다란 원형 DC 플러그를 제어보드 충전 단자에 꽂습니다.
5. 충전기 본체의 상태 LED를 확인합니다.
6. 완충 후 충전기를 로봇과 콘센트에서 분리합니다.

충전 표시의 의미:

- 충전기 LED 빨간색: 충전 중
- 충전기 LED 초록색: 충전 완료
- 충전기만 콘센트에 연결했는데 LED가 꺼짐: 콘센트·충전기 문제 가능성
- 로봇 연결 후에도 계속 초록색이고 로봇이 켜지지 않음: 배터리 커넥터,
  충전 단자, 배터리 보호회로 또는 배터리 점검 필요

충전 중 제어보드의 전원 LED가 꺼져 있는 것은 이상이 아닐 수 있습니다. 충전
상태는 보드가 아니라 충전기 어댑터 본체의 LED로 확인합니다. 배터리를 바퀴
안쪽에서 분리해 직접 충전하거나 임의의 어댑터를 연결하지 않습니다.

배터리나 충전기가 부풀거나, 뜨겁거나, 냄새가 나면 즉시 분리하고 사용하지
않습니다.

## 종료

서버를 실행한 터미널에서 `Control + C`를 누릅니다. Raspberry Pi 전원을 끌 때는 다음 명령이 완료된 후 전원 케이블을 분리합니다.

```bash
sudo shutdown -h now
```

## 자주 발생하는 문제

### `python: command not found`

Ubuntu에서는 `python3`를 사용하거나 가상환경을 활성화합니다.

### `Address already in use`

8090 포트에서 서버가 이미 실행 중입니다. 기존 서버를 종료한 뒤 다시 실행합니다.

### UI에 `Failed to fetch` 표시

Mac과 Raspberry Pi의 네트워크 연결을 확인하고 페이지를 새로고침합니다. SSH 연결과 서버 실행 상태도 함께 확인합니다.

### `raspberrypi.local`을 찾을 수 없음

호스트 이름 대신 Raspberry Pi의 현재 IP 주소로 접속합니다.

### I2C 표에 `2b`가 없음

전원을 끈 뒤 SDA, SCL, GND 배선 위치를 다시 확인합니다.

### Raspberry Pi는 켜지지만 Raspbot 보드에 불이 없음

Raspberry Pi가 별도 USB-C 전원으로 켜진 상태일 수 있습니다. Raspbot 보드의
주 전원 스위치, 배터리 잔량, 배터리 커넥터와 충전기 상태를 순서대로
확인합니다. 이 상태에서는 웹 UI가 열리더라도 모터 운행이 가능한 것으로
판단하지 않습니다.
