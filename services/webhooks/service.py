from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import httpx
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.models import WebhookDelivery, WebhookSubscription
from libs.common.secrets import resolve_secret

HttpPostFn = Callable[..., httpx.Response]


class WebhookService:
    def __init__(self, http_post: Optional[HttpPostFn] = None):
        self._http_post = http_post or httpx.post

    def create_subscription(
        self,
        db: Session,
        *,
        tenant_id: str,
        actor_id: str,
        target_url: str,
        event_filter: str,
    ) -> WebhookSubscription:
        subscription = WebhookSubscription(
            id=f"whs_{uuid4().hex}",
            tenant_id=tenant_id,
            target_url=target_url,
            secret_ref="secret-manager://webhook-signing-secret",
            event_filter=event_filter,
            active=True,
        )
        db.add(subscription)

        create_audit_event(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="webhook.subscription.created",
            entity_type="webhook_subscription",
            entity_id=subscription.id,
            payload={"target_url": target_url, "event_filter": event_filter},
        )
        return subscription

    def dispatch_event(
        self,
        db: Session,
        *,
        tenant_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> int:
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.tenant_id == tenant_id,
            WebhookSubscription.active.is_(True),
            WebhookSubscription.event_filter == event_type,
        )
        subscriptions = list(db.execute(stmt).scalars().all())
        enqueued = 0
        for subscription in subscriptions:
            idempotency_key = (
                f"{subscription.id}:{event_type}:"
                f"{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}"
            )
            existing_stmt = select(WebhookDelivery).where(
                WebhookDelivery.tenant_id == tenant_id,
                WebhookDelivery.idempotency_key == idempotency_key,
            )
            existing = db.execute(existing_stmt).scalar_one_or_none()
            if existing:
                continue

            delivery = WebhookDelivery(
                id=f"whd_{uuid4().hex}",
                tenant_id=tenant_id,
                subscription_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempt_count=0,
                idempotency_key=idempotency_key,
                next_attempt_at=datetime.now(timezone.utc),
                last_attempt_at=None,
                dead_lettered_at=None,
            )
            db.add(delivery)
            enqueued += 1

        return enqueued

    def process_delivery_queue(
        self,
        db: Session,
        *,
        tenant_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        filters = [
            WebhookDelivery.status.in_(["pending", "retry_scheduled"]),
            WebhookDelivery.next_attempt_at <= now,
        ]
        if tenant_id:
            filters.append(WebhookDelivery.tenant_id == tenant_id)

        stmt = (
            select(WebhookDelivery)
            .where(and_(*filters))
            .order_by(WebhookDelivery.next_attempt_at.asc())
            .limit(batch_size)
        )
        deliveries = list(db.execute(stmt).scalars().all())

        delivered = 0
        retried = 0
        dead_lettered = 0
        for delivery in deliveries:
            result = self._attempt_delivery(db, delivery)
            if result == "delivered":
                delivered += 1
            elif result == "retry_scheduled":
                retried += 1
            elif result == "dead_lettered":
                dead_lettered += 1

        return {
            "processed": len(deliveries),
            "delivered": delivered,
            "retried": retried,
            "dead_lettered": dead_lettered,
        }

    def replay_dead_lettered(
        self,
        db: Session,
        *,
        tenant_id: str,
        delivery_ids: Optional[list[str]] = None,
        limit: int = 100,
    ) -> int:
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.tenant_id == tenant_id,
            WebhookDelivery.status == "dead_lettered",
        )
        if delivery_ids:
            stmt = stmt.where(WebhookDelivery.id.in_(delivery_ids))
        stmt = stmt.order_by(WebhookDelivery.dead_lettered_at.desc()).limit(limit)

        deliveries = list(db.execute(stmt).scalars().all())
        now = datetime.now(timezone.utc)
        for delivery in deliveries:
            delivery.status = "pending"
            delivery.attempt_count = 0
            delivery.last_error = None
            delivery.next_attempt_at = now
            delivery.dead_lettered_at = None
        return len(deliveries)

    def _attempt_delivery(self, db: Session, delivery: WebhookDelivery) -> str:
        subscription_stmt = select(WebhookSubscription).where(
            WebhookSubscription.id == delivery.subscription_id,
            WebhookSubscription.tenant_id == delivery.tenant_id,
            WebhookSubscription.active.is_(True),
        )
        subscription = db.execute(subscription_stmt).scalar_one_or_none()
        if subscription is None:
            delivery.status = "dead_lettered"
            delivery.last_error = "subscription_missing_or_inactive"
            delivery.dead_lettered_at = datetime.now(timezone.utc)
            return "dead_lettered"

        settings = get_settings()
        body = json.dumps(delivery.payload).encode("utf-8")
        signing_secret = resolve_secret("WEBHOOK_SIGNING_SECRET", "webhook-signing-secret")
        signature = hmac.new(
            signing_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Nexus-Signature": f"sha256={signature}",
            "X-Nexus-Event": delivery.event_type,
            "X-Idempotency-Key": delivery.idempotency_key,
        }

        now = datetime.now(timezone.utc)
        delivery.last_attempt_at = now
        delivery.attempt_count += 1

        try:
            response = self._http_post(
                subscription.target_url,
                content=body,
                headers=headers,
                timeout=settings.integration_timeout_seconds,
            )
            response.raise_for_status()
            delivery.status = "delivered"
            delivery.delivered_at = now
            delivery.last_error = None
            return "delivered"
        except Exception as exc:  # noqa: BLE001
            delivery.last_error = str(exc)
            if delivery.attempt_count >= settings.webhook_max_retries:
                delivery.status = "dead_lettered"
                delivery.dead_lettered_at = now
                return "dead_lettered"

            backoff_seconds = min(2 ** (delivery.attempt_count - 1), 300)
            delivery.status = "retry_scheduled"
            delivery.next_attempt_at = now + timedelta(seconds=backoff_seconds)
            return "retry_scheduled"
