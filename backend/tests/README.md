# DB 테스트

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

전용 PostgreSQL 테스트 DB에서 모델·서비스·제약조건과 마이그레이션을 검증합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [conftest.py](conftest.py) | 격리 DB 생성·정리 fixture |
| [test_database.py](test_database.py) | DB 모델·서비스 검증 |

## 사용 방법

격리된 개발 DB를 준비한 뒤 저장소 루트에서:

```bash
python -m pytest backend/tests -q
```

## 알아둘 점

**파괴적 테스트 주의:** `conftest.py`가 `_test`로 끝나는 대상 DB를 삭제·재생성하고 테이블을 비웁니다. `TEST_DATABASE_URL`에 보존해야 하는 DB를 지정하지 마세요. 테스트용 PostgreSQL 관리 권한이 필요합니다.
