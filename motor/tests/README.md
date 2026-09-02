# SO-ARM101 로직 테스트

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

Profiled Studio의 범위·상대 추종·이동 계획 등 내부 로직을 fake bus로 검증합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [test_logic.py](test_logic.py) | SO-ARM101 로직의 fake-bus 테스트 |

## 사용 방법

기존 팔 개발 환경에서 저장소 루트 기준:

```bash
python -m unittest discover -s motor/tests -v
```

환경 조건은 [팔 모듈 안내](../README.md)를 참고하세요.

## 알아둘 점

fake-bus 테스트는 소프트웨어 로직을 검증합니다. 실제 관절·하중·충돌 안전성은 별도의 장치 시험으로 확인하세요.
