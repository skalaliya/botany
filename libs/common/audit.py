from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from libs.common.models import AuditEvent


def create_audit_event(
    db: Session,
    *,
    tenant_id: str,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, object],
) -> AuditEvent:
    event = AuditEvent(
        id=f"audit_{uuid4().hex}",
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    db.add(event)
    return event
