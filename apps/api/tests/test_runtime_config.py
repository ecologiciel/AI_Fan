import pytest

from app.core.config import INSECURE_DEFAULT_SECRET, Settings


def test_production_rejects_placeholder_secrets() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key=INSECURE_DEFAULT_SECRET,
        admin_password=INSECURE_DEFAULT_SECRET,
    )

    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        settings.validate_runtime_security()


def test_production_accepts_explicit_non_placeholder_secrets() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key="a" * 32,
        admin_password="a-long-unique-admin-password",
    )

    settings.validate_runtime_security()
