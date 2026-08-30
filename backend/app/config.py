from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    test_database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def resolved_test_database_url(self) -> str:
        if self.test_database_url:
            return self.test_database_url

        url = make_url(self.database_url)
        database = url.database or "care_pack"
        return url.set(database=f"{database}_test").render_as_string(
            hide_password=False
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
