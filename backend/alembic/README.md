# DB 마이그레이션

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

PostgreSQL 테이블의 생성과 스키마 변경 이력을 관리합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [versions/](versions/README.md) | DB 변경 이력 |
| [env.py](env.py) | Alembic 실행환경 |
| [script.py.mako](script.py.mako) | migration 파일 템플릿 |

## 사용 방법

저장소 루트에서:

```bash
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini upgrade head
```

## 알아둘 점

`upgrade`는 DB 구조를 변경합니다. 실제 운영 데이터가 있다면 먼저 백업하세요. 기존 배포 버전의 마이그레이션을 수정하지 말고 새 revision으로 변경을 추가합니다.
