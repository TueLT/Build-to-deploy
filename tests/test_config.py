import pytest
from pydantic import ValidationError

from src.config import Settings


def _production_settings(**overrides):
    values = {
        "app_env": "production",
        "secret_key": "x" * 32,
        "database_url": "postgresql://orbit:secret@db/orbit",
        "cors_origins": "https://app.example.com",
        "llm_provider": "google",
        "google_api_key": "test-api-key",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_valid_production_settings_are_accepted():
    settings = _production_settings()
    assert settings.app_env == "production"


def test_development_requires_postgres():
    with pytest.raises(ValidationError, match="Development and production require a PostgreSQL DATABASE_URL"):
        Settings(_env_file=None, app_env="development", database_url="sqlite:///./data/app.db")


def test_test_environment_accepts_sqlite():
    settings = Settings(_env_file=None, app_env="test", database_url="sqlite+aiosqlite:///:memory:")
    assert settings.database_url.startswith("sqlite")


def test_database_url_is_required():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="development")


@pytest.mark.parametrize(
    "override",
    [
        {"secret_key": "too-short"},
        {"database_url": "sqlite:///./data/app.db"},
        {"cors_origins": "*"},
        {"google_api_key": ""},
    ],
)
def test_unsafe_production_settings_are_rejected(override):
    with pytest.raises(ValidationError):
        _production_settings(**override)
