from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from libs.auth.security import decode_access_token
from libs.auth.types import AuthUser
from libs.common.config import get_settings


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user: AuthUser


def get_current_user(authorization: str = Header(default="", alias="Authorization")) -> AuthUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc


def get_tenant_context(
    user: AuthUser = Depends(get_current_user),
    tenant_id_header: str = Header(default="", alias="X-Tenant-Id"),
) -> TenantContext:
    settings = get_settings()
    tenant_id = tenant_id_header.strip()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"missing tenant header: {settings.tenant_header_name}",
        )
    if tenant_id not in user.tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant access denied")
    return TenantContext(tenant_id=tenant_id, user=user)


def require_roles(*allowed_roles: str) -> Callable[[AuthUser], AuthUser]:
    def _validator(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not set(user.roles).intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return _validator
