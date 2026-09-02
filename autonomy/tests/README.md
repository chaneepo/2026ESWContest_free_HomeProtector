# 자율 시뮬레이션 테스트

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

상태 전이·라인 판단·장애물 정지·실패·취소를 가상 관측값으로 검증합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [test_mission.py](test_mission.py) | 가상 미션 상태 전이·실패·취소 테스트 |

## 사용 방법

저장소 루트에서:

```bash
python3 -B -m unittest discover -s autonomy/tests -v
```

## 알아둘 점

실제 SSH, GPIO, CAN, 모터를 사용하지 않습니다. 통과 결과는 실물 자율주행 성능 측정값이 아닙니다.
