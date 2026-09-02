# 라즈봇 안전 테스트

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

가짜 모터·loopback HTTP·가짜 fetch로 서버와 두 UI의 공통 제어 로직을 검증합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [control-client.test.mjs](control-client.test.mjs) | 통신 실패·늦은 응답·중복 요청 테스트 |
| [test_controller.py](test_controller.py) | 짧은 이동·정지·범위 검사 |
| [test_safety.py](test_safety.py) | 오류·STOP·운전권한·동시성·HTTP 검증 |
| [test_server.py](test_server.py) | 서버 모드·기본 동작 검증 |

## 사용 방법

저장소 루트에서:

```bash
(cd raspbot_runtime && python3 -B -m unittest discover -s tests -v)
node --test raspbot_runtime/tests/control-client.test.mjs
```

## 알아둘 점

HTTP 테스트는 로컬 임시 포트를 사용합니다. 실제 I2C를 연결하지 않으며, 통과 결과로 배선·배터리·바퀴 방향까지 검증되는 것은 아닙니다.
