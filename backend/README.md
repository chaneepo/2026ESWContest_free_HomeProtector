# 백엔드·데이터베이스

[프로젝트 홈](../README.md) · [상위 안내](../README.md)

FastAPI 상태 확인, SQLAlchemy 모델·서비스와 Alembic 마이그레이션을 관리합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [alembic/](alembic/README.md) | DB 마이그레이션 |
| [app/](app/README.md) | FastAPI·도메인 로직 |
| [tests/](tests/README.md) | DB 테스트 |
| [__init__.py](__init__.py) | Python 패키지 진입점 |
| [alembic.ini](alembic.ini) | Alembic 설정 |

## 사용 방법

저장소 루트에서 Python 가상환경에 `requirements/requirements-dev.txt`를 설치하고 `.env.example`을 참고해 `.env`를 준비합니다. DB를 준비한 뒤 실행합니다.

```bash
docker compose --project-directory . -f infra/compose.yaml up -d db
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.app.seed
python -m uvicorn backend.app.main:app --reload --port 8000
```

## 알아둘 점

공개 HTTP API인 `GET /health`로 DB 접속을 확인하고, 내부 서비스 함수로 작업 생성·이벤트 처리를 구성합니다. 업무 REST API와 웹 데이터 연동은 확장 계획에 포함됩니다. 카메라 서버도 8000을 사용하는 경우 포트를 분리하세요. DB 테스트는 전용 테스트 DB를 삭제·재생성합니다.
