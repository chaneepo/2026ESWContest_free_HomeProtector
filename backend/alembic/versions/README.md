# DB 변경 이력

[프로젝트 홈](../../../README.md) · [상위 안내](../README.md)

핵심 테이블 생성과 제약조건 정규화 migration을 보관합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [20260829_0001_core_database.py](20260829_0001_core_database.py) | 핵심 테이블 생성 |
| [20260829_0002_normalize_constraints.py](20260829_0002_normalize_constraints.py) | 제약조건 정규화 |

## 사용 방법

[상위 마이그레이션 안내](../README.md)에 따라 Alembic으로 실행합니다. 각 파일을 Python 스크립트처럼 직접 실행하지 않습니다.

## 알아둘 점

`downgrade`는 테이블·데이터에 영향을 줄 수 있습니다. 운영 DB에서 초기화 목적으로 실행하지 마세요.
