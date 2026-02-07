from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.models import IdempotencyKey


class IdempotencyConflictError(ValueError):
    pass


def hash_request(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_idempotent_response(
    db: Session, *, tenant_id: str, key: str, request_hash: str
) -> dict[str, Any] | None:
    statement = select(IdempotencyKey).where(
        IdempotencyKey.tenant_id == tenant_id,
        IdempotencyKey.idempotency_key == key,
    )
    existing = db.execute(statement).scalar_one_or_none()
    if not existing:
        return None
    if existing.request_hash != request_hash:
        raise IdempotencyConflictError("idempotency key reused with different payload")
    return existing.response_payload


def save_idempotent_response(
    db: Session,
    *,
    tenant_id: str,
    key: str,
    request_hash: str,
    response_payload: dict[str, Any],
) -> None:
    record = IdempotencyKey(
        id=f"idmp_{uuid4().hex}",
        tenant_id=tenant_id,
        idempotency_key=key,
        request_hash=request_hash,
        response_payload=response_payload,
    )
    db.add(record)
