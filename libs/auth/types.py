from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    email: str
    tenant_ids: list[str]
    roles: list[str]
