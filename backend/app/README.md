# FastAPI·도메인 로직

[프로젝트 홈](../../README.md) · [상위 안내](../README.md)

설정, DB 세션, 데이터 모델, 스키마, 작업·이벤트 관련 서비스 함수를 제공합니다.

## 파일과 하위 폴더

| 파일·폴더 | 내용 |
|---|---|
| [__init__.py](__init__.py) | Python 패키지 진입점 |
| [config.py](config.py) | 환경변수·DB 설정 |
| [database.py](database.py) | DB 엔진·세션 |
| [enums.py](enums.py) | DB·도메인 열거형 |
| [main.py](main.py) | FastAPI /health 진입점 |
| [models.py](models.py) | SQLAlchemy 테이블 모델 |
| [schemas.py](schemas.py) | 요청·응답 스키마 |
| [seed.py](seed.py) | 개발용 초기 데이터 |
| [services.py](services.py) | 작업 생성·이벤트 내부 함수 |

## 사용 방법

저장소 루트에서 `python -m uvicorn backend.app.main:app --reload --port 8000`으로 실행합니다. `.env`의 `DATABASE_URL`과 PostgreSQL이 필요합니다.

## 알아둘 점

`main.py`는 DB 상태 확인용 `/health`를 제공합니다. `services.py`의 도메인 함수는 Python 내부 호출용이며, 업무 REST API 확장의 기반으로 사용합니다.
