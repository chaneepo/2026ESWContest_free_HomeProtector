# 자율 작업 초안 — 시뮬레이션 전용

[프로젝트 홈](../README.md)

## 폴더와 코드 안내

| 파일·폴더 | 내용 |
|---|---|
| [mission.py](mission.py) | 가상 미션·라인 판단·관측 모델 |
| [__main__.py](__main__.py) | 시나리오 선택 CLI |
| [tests/](tests/README.md) | 하드웨어 없는 테스트 |

이 모듈은 예선 단계에서 자율 동작의 의사결정·상태 전이·실패 처리를 검토하기 위한 코드입니다.
**실제 라즈봇 자율주행 및 실제 팔 자율 작업은 구현 완료되지 않았습니다.**

## 실행

저장소 루트에서 Python 3.10 이상으로 실행합니다. 추가 패키지나 로봇은 필요하지 않습니다.

```bash
python3 -m autonomy --scenario success
python3 -m autonomy --scenario obstacle
python3 -m autonomy --scenario line-lost
python3 -m autonomy --scenario pick-failure
python3 -m autonomy --scenario verify-failure
python3 -m autonomy --scenario timeout
python3 -m autonomy --scenario cancel
python3 -B -m unittest discover -s autonomy/tests -v
```

결과는 JSON으로 출력하며 항상 `SIMULATION_ONLY`, `hardware_executed: false`를 포함합니다.
실패 시나리오는 의도적으로 `FAULT` 또는 `CANCELLED`로 끝납니다. 출력 로그는 실물 측정 데이터가 아닙니다.

## 구현한 것

- `decide_line`: 네 개 라인 신호의 가중 평균에 따른 전진·좌우 회전 판단 함수.
- 장애물 20cm 이하, 오래된 센서(0.5초 초과), 잘못된 값, 라인 소실 시 정지 판단.
- `Mission`: 이동 → 도킹 → 인식 → 집기 → 놓기 → 적재 확인의 단계별 상태 전이.
- 도킹·물품 인식 신호가 없으면 팔 작업을 시작하지 않음.
- 파지 확인 실패 시 재인식 후 한 번만 재시도, 적재 확인 실패 시 오류 종료.
- 단계당 10초 제한, 취소, 두 가상 장치의 정지 기록.
- 가상 장치만 허용하며 하드웨어 어댑터는 제공하지 않음.

라인 센서의 `True` 의미, 좌우 배치, 회전 방향은 **설계상 가정**입니다. 본선에서 실물 센서의 극성과 바퀴 방향을 보정해야 합니다. 현재 명령은 목록에 기록될 뿐 실제 이동 시간·궤적·전류를 만들지 않습니다.

## 구현하지 않은 것

SLAM, 경로 탐색, 위치 추정, AprilTag 실제 도킹, 카메라-팔 좌표 보정, 역기구학,
관절 궤적·속도 제어, 충돌 회피, 파지/적재 센서의 실제 입력은 미구현입니다.
기존 웹 `mocks/simulationEngine.ts`와 이 독립 CLI는 아직 연결되어 있지 않습니다.

## 본선 연결 순서

1. 센서 실측값과 신뢰도·시간 정보를 `Observation`에 연결하고 극성을 보정합니다.
2. 차체 어댑터에 짧은 이동·독립 watchdog·STOP·오류 처리를 구현하고 받침대 시험을 합니다.
3. 도킹의 실제 확인 신호를 넣어 정지 후에만 팔이 동작하게 합니다.
4. 실제 팔 모델·좌표계·작업 공간을 확정한 뒤 궤적과 관절 한계를 검증합니다.
5. 파지·무게 센서를 연결해 명령 응답과 물리 성공을 분리합니다.
6. 사람이 감독하는 통합 시험으로 성공률·오차·시간을 **실제로 측정**해 문서에 추가합니다.

이 모듈을 실제 구동 코드로 단순 교체해 무인 실행하지 마세요. 원격 운전 권한과 수동·자율 간 제어권 전환, 하드웨어 비상정지 설계가 먼저 필요합니다.
