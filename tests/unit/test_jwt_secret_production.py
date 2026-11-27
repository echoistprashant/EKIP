import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_refuses_to_start_when_jwt_secret_missing():
    """App must refuse to start in production if JWT_SECRET is missing."""
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", JWT_SECRET=None)
    assert "JWT_SECRET must be set in production environment" in str(exc.value)


def test_production_refuses_to_start_when_jwt_secret_is_weak():
    """App must refuse to start in production if JWT_SECRET is less than 32 characters."""
    with pytest.raises(ValidationError) as exc:
        Settings(APP_ENV="production", JWT_SECRET="short-key-under-32-chars")
    assert "JWT_SECRET is too weak" in str(exc.value)


def test_production_refuses_default_insecure_placeholder():
    """App must refuse default placeholder secret in production."""
    with pytest.raises(ValidationError) as exc:
        Settings(
            APP_ENV="production",
            JWT_SECRET="ekip-super-secure-jwt-secret-key-change-in-production-2026",
        )
    assert "cannot use default or insecure placeholder" in str(exc.value)


def test_production_accepts_strong_jwt_secret():
    """App successfully starts in production when a strong secret (>= 32 chars) is provided."""
    strong_secret = "a" * 32
    settings = Settings(APP_ENV="production", JWT_SECRET=strong_secret)
    assert strong_secret == settings.JWT_SECRET


def test_local_environment_provides_dev_fallback_when_omitted():
    """Local / non-production environment allows development without explicit secret."""
    settings = Settings(APP_ENV="local", JWT_SECRET=None)
    assert settings.JWT_SECRET is not None
    assert len(settings.JWT_SECRET) >= 32
