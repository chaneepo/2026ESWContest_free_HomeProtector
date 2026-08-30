from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def recreate_test_database(database_url: str) -> None:
    url = make_url(database_url)
    database_name = url.database or ""
    if not database_name.endswith("_test"):
        raise RuntimeError("테스트 DB 이름은 안전을 위해 '_test'로 끝나야 합니다.")

    admin_url = url.set(drivername="postgresql", database="postgres")
    with (
        psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(database_name)
            )
        )
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


@pytest.fixture(scope="session")
def test_database_url() -> Generator[str, None, None]:
    database_url = get_settings().resolved_test_database_url()
    recreate_test_database(database_url)

    alembic_config = Config(REPOSITORY_ROOT / "backend" / "alembic.ini")
    alembic_config.attributes["database_url"] = database_url
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    yield database_url

    url = make_url(database_url)
    admin_url = url.set(drivername="postgresql", database="postgres")
    with (
        psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(url.database or "care_pack_test")
            )
        )


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    table_names = (
        "job_events",
        "job_items",
        "jobs",
        "routine_items",
        "routines",
        "items",
        "locations",
    )
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(table_names)} CASCADE"))

    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with factory() as session:
        yield session
        session.rollback()
