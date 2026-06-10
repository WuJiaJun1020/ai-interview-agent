from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AI Interview Agent"
    app_env: str = "development"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'dev.db').as_posix()}"
    scoring_mode: str = "mock"
    openai_api_key: str = ""
    dashscope_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_enable_thinking: bool = False
    llm_timeout_seconds: float = 120
    interview_pass_score: int = 70

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    @property
    def llm_api_key(self) -> str:
        return self.openai_api_key or self.dashscope_api_key

    @field_validator("database_url")
    @classmethod
    def normalize_sqlite_url(cls, value: str) -> str:
        prefix = "sqlite:///"
        if not value.startswith(prefix) or value == "sqlite:///:memory:":
            return value

        db_path = Path(value.removeprefix(prefix))
        if db_path.is_absolute():
            return value

        absolute_path = (BACKEND_DIR.parent / db_path).resolve()
        return f"{prefix}{absolute_path.as_posix()}"


settings = Settings()
