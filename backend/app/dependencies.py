from __future__ import annotations

import base64
import json
import os
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Header, HTTPException, status


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _decode_unverified_jwt(token: str) -> tuple[dict[str, object], dict[str, object]]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    header_raw = _decode_base64url(parts[0])
    payload_raw = _decode_base64url(parts[1])
    header = json.loads(header_raw.decode("utf-8"))
    payload = json.loads(payload_raw.decode("utf-8"))
    return header, payload


def _supabase_issuer() -> str | None:
    supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_url:
        return None
    return f"{supabase_url.rstrip('/')}/auth/v1"


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _verify_with_supabase_jwks(token: str, header: dict[str, object]) -> dict[str, object]:
    issuer = _supabase_issuer()
    if issuer is None:
        raise ValueError("Missing Supabase URL")

    algorithm = header.get("alg")
    if algorithm not in {"ES256", "RS256"}:
        raise ValueError("Unsupported JWT algorithm")

    jwks_url = f"{issuer}/.well-known/jwks.json"
    signing_key = _get_jwks_client(jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[str(algorithm)],
        issuer=issuer,
        options={"require": ["exp", "iss", "sub"], "verify_aud": False},
    )


def _verify_with_supabase_secret(token: str) -> dict[str, object]:
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise ValueError("Missing JWT secret")

    issuer = _supabase_issuer()
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=issuer,
        options={"require": ["exp", "sub"], "verify_aud": False},
    )


def _extract_subject_from_jwt(token: str) -> UUID:
    header, payload = _decode_unverified_jwt(token)

    issuer = _supabase_issuer()
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if issuer:
        try:
            payload = _verify_with_supabase_jwks(token, header)
        except Exception:
            if not secret:
                raise
            payload = _verify_with_supabase_secret(token)
    elif secret:
        payload = _verify_with_supabase_secret(token)

    subject = payload.get("sub")
    if not subject:
        raise ValueError("Missing JWT subject")
    return UUID(str(subject))


def get_current_user_id(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> UUID:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )

    try:
        return _extract_subject_from_jwt(token)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        ) from None
