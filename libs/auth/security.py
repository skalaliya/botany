from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt

from libs.auth.types import AuthUser
from libs.common.config import get_settings
from libs.common.secrets import resolve_secret

ALGORITHM = "HS256"


def create_access_token(user: AuthUser) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_ttl_minutes)
    secret = resolve_secret("AUTH_JWT_SECRET", "auth-jwt-secret")
    claims = {
        "sub": user.user_id,
        "email": user.email,
        "tenant_ids": user.tenant_ids,
        "roles": user.roles,
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), expires_at


def create_refresh_token(user: AuthUser) -> tuple[str, str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    jti = f"rt_{uuid4().hex}"
    secret = resolve_secret("AUTH_REFRESH_SECRET", "auth-refresh-secret")
    claims = {
        "sub": user.user_id,
        "tenant_ids": user.tenant_ids,
        "roles": user.roles,
        "jti": jti,
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), jti, expires_at


def decode_access_token(token: str) -> AuthUser:
    settings = get_settings()
    secret = resolve_secret("AUTH_JWT_SECRET", "auth-jwt-secret")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
        )
    except JWTError as exc:
        raise ValueError("invalid access token") from exc

    return AuthUser(
        user_id=str(payload["sub"]),
        email=str(payload.get("email", "")),
        tenant_ids=[str(tenant) for tenant in payload.get("tenant_ids", [])],
        roles=[str(role) for role in payload.get("roles", [])],
    )


def decode_refresh_token(token: str) -> tuple[AuthUser, str]:
    settings = get_settings()
    secret = resolve_secret("AUTH_REFRESH_SECRET", "auth-refresh-secret")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
        )
    except JWTError as exc:
        raise ValueError("invalid refresh token") from exc

    user = AuthUser(
        user_id=str(payload["sub"]),
        email="",
        tenant_ids=[str(tenant) for tenant in payload.get("tenant_ids", [])],
        roles=[str(role) for role in payload.get("roles", [])],
    )
    return user, str(payload["jti"])
