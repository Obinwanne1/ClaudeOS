import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator


BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # Core
    CLAUDEOS_SECRET_KEY: str = "dev-secret-change-in-prod"
    CLAUDEOS_ENV: str = "development"
    CLAUDEOS_VERSION: str = "1.0.0"

    # Claude API
    ANTHROPIC_API_KEY: str = ""

    # Database
    SQLITE_PATH: str = "data/claudeos.db"
    CHROMADB_PATH: str = "data/chromadb"

    # Flask
    FLASK_PORT: int = 5000
    FLASK_DEBUG: bool = False

    # Streamlit
    STREAMLIT_PORT: int = 8501

    # Supabase (Phase 7)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Memory bridge
    CLAUDE_MEMORY_PATH: str = r"C:\Users\rigwe\.claude\memory"

    # RECI Transport
    RECI_DASHBOARD_DB: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "logs"

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("SQLITE_PATH", "CHROMADB_PATH", "LOG_PATH", mode="before")
    @classmethod
    def resolve_path(cls, v: str) -> str:
        p = Path(v)
        if not p.is_absolute():
            return str(BASE_DIR / v)
        return v

    @property
    def is_production(self) -> bool:
        return self.CLAUDEOS_ENV == "production"

    @property
    def sqlite_path(self) -> Path:
        return Path(self.SQLITE_PATH)

    @property
    def chromadb_path(self) -> Path:
        return Path(self.CHROMADB_PATH)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure data dirs exist
        _settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        _settings.chromadb_path.mkdir(parents=True, exist_ok=True)
        Path(_settings.LOG_PATH).mkdir(parents=True, exist_ok=True)
    return _settings
