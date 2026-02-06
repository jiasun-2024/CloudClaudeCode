from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cloud Claude Code Backend"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"])

    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    database_url: str | None = None
    data_dir: Path | None = None
    workspaces_root: Path | None = None

    anthropic_api_key: str | None = None
    claude_cli_path: str | None = None
    default_model: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context: object) -> None:
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.workspaces_root is None:
            self.workspaces_root = self.base_dir / "workspaces"
        if self.database_url is None:
            self.database_url = f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


settings = Settings()
