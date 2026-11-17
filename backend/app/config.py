from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Admissions Follow-up System"
    source_directory: Path = Path(__file__).resolve().parents[2]
    ollama_base_url: str = "http://localhost:11434"
    database_url: str = "sqlite:///./admissions.db"
    extracted_directory: Path = Path(__file__).resolve().parents[2] / "data" / "extracted"
    vector_index_path: Path = Path(__file__).resolve().parents[2] / "data" / "embeddings" / "index.json"
    embedding_model: str = "all-minilm:latest"
    chunk_size: int = 1200
    chunk_overlap: int = 180
    jwt_secret: str = "change-this-local-secret"
    environment: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    access_token_ttl_seconds: int = 86_400
    rate_limit_window_seconds: int = 60
    rate_limit_requests: int = 60
    upload_directory: Path = Path(__file__).resolve().parents[2] / "data" / "uploads"
    max_upload_bytes: int = 25 * 1024 * 1024
    whisper_model: str = "small"
    piper_executable: str = "piper"
    piper_voice: Path | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADMISSIONS_")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("ollama_base_url must be an HTTP(S) URL")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> "Settings":
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("cors_origins must contain explicit origins; wildcard is not allowed")
        if self.rate_limit_requests < 1 or self.rate_limit_window_seconds < 1:
            raise ValueError("rate limiting values must be positive")
        if self.access_token_ttl_seconds < 300 or self.access_token_ttl_seconds > 86_400:
            raise ValueError("access token TTL must be between 5 minutes and 24 hours")
        if self.max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive")
        if self.environment.lower() in {"production", "prod"}:
            if self.jwt_secret == "change-this-local-secret" or len(self.jwt_secret) < 32:
                raise ValueError("ADMISSIONS_JWT_SECRET must be at least 32 characters in production")
            if any(origin.startswith(("http://localhost", "http://127.0.0.1")) for origin in self.cors_origins):
                raise ValueError("localhost CORS origins are not allowed in production")
        return self


settings = Settings()
