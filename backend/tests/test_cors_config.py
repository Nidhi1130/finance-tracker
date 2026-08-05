from __future__ import annotations

from app.main import _allowed_origins


def test_allowed_origins_falls_back_to_localhost_defaults(monkeypatch) -> None:
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    origins = _allowed_origins()
    assert "http://localhost:3000" in origins
    assert "http://localhost:3100" in origins


def test_allowed_origins_reads_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://example.vercel.app, https://foo.example.com",
    )
    assert _allowed_origins() == [
        "https://example.vercel.app",
        "https://foo.example.com",
    ]


def test_allowed_origins_falls_back_when_env_is_blank(monkeypatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "   ")
    origins = _allowed_origins()
    assert "http://localhost:3000" in origins
