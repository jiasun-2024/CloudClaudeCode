from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Cloud Claude Code API")
    api_prefix: str = Field(default="/api")
    workspaces_root: Path = Field(default=Path("backend/workspaces"))
    allowed_origins: list[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173"])


settings = Settings()
