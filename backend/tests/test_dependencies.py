from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app import dependencies


def test_extract_subject_from_supabase_jwks_token(monkeypatch) -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    issuer = "https://example-project.supabase.co/auth/v1"
    subject = UUID("00000000-0000-0000-0000-000000000123")

    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        dependencies.jwt,
        "PyJWKClient",
        lambda jwks_url: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=public_key),
        ),
    )

    token = jwt.encode(
        {
            "sub": str(subject),
            "iss": issuer,
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )

    assert dependencies._extract_subject_from_jwt(token) == subject
