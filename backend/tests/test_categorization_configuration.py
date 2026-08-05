from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def import_configured_provider(
    *,
    provider_mode: str | None,
    api_key: str | None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    environment.pop("SUPABASE_URL", None)
    environment.pop("SUPABASE_JWT_SECRET", None)
    if provider_mode is None:
        environment.pop("CATEGORIZATION_PROVIDER", None)
    else:
        environment["CATEGORIZATION_PROVIDER"] = provider_mode
    if api_key is None:
        environment.pop("OPENAI_API_KEY", None)
    else:
        environment["OPENAI_API_KEY"] = api_key

    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.services import categorization_provider; "
                "print('none' if categorization_provider is None "
                "else type(categorization_provider).__name__)"
            ),
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_rules_mode_is_default_and_ignores_an_ambient_openai_key() -> None:
    result = import_configured_provider(provider_mode=None, api_key="ambient-test-key")

    assert result.returncode == 0
    assert result.stdout.strip() == "none"


def test_explicit_openai_mode_builds_the_optional_provider() -> None:
    result = import_configured_provider(provider_mode="openai", api_key=None)

    assert result.returncode == 0
    assert result.stdout.strip() == "OpenAICategorizationProvider"


def test_invalid_provider_mode_fails_startup_clearly() -> None:
    result = import_configured_provider(provider_mode="unexpected", api_key="ambient-test-key")

    assert result.returncode != 0
    assert "CATEGORIZATION_PROVIDER" in result.stderr
