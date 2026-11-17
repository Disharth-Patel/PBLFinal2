import pytest
from pydantic import ValidationError

from app.config import Settings


def test_cors_environment_value_is_parsed() -> None:
    settings = Settings(
        cors_origins="https://admissions.example, https://www.example",
        jwt_secret="x" * 40,
        environment="production",
    )
    assert settings.cors_origins == ["https://admissions.example", "https://www.example"]


def test_production_rejects_default_secret_and_local_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            cors_origins="https://admissions.example",
        )
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="x" * 40,
            cors_origins="http://localhost:5173",
        )


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins="*")
