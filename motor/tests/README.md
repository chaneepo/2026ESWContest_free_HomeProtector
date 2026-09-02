# 기존 SO-ARM101 로직 테스트

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

업로드된 Profiled Studio의 범위·상대 추종·이동 계획 등 내부 로직을 fake bus로 검증하는 테스트를 보관합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [test_logic.py](test_logic.py) | 기존 SO-ARM101 로직의 fake-bus 테스트 |

## 사용 방법

기존 팔 개발 환경에서 저장소 루트 기준:

```bash
python -m unittest discover -s motor/tests -v
```

환경 조건은 [팔 모듈 안내](../README.md)를 참고하세요.

## 알아둘 점

이번 문서 작업에서는 기존 테스트와 팔 코드를 변경하거나 실행하지 않았습니다. 이 테스트 결과가 실제 관절·하중·충돌 안전성을 보장하지는 않습니다.
