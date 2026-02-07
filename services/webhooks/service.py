from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from libs.common.audit import create_audit_event
from libs.common.config import get_settings
from libs.common.models import WebhookDelivery, WebhookSubscription


class WebhookService:
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
        for subscription in subscriptions:
            idempotency_key = f"{subscription.id}:{event_type}:{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}"
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
            )
            db.add(delivery)
            self._deliver(subscription.target_url, event_type, payload, delivery)

        return len(subscriptions)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(5), reraise=True
    )
    def _deliver(
        self,
        target_url: str,
        event_type: str,
        payload: dict[str, object],
        delivery: WebhookDelivery,
    ) -> None:
        settings = get_settings()
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            settings.webhook_signing_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Nexus-Signature": f"sha256={signature}",
            "X-Nexus-Event": event_type,
            "X-Idempotency-Key": delivery.idempotency_key,
        }
        delivery.attempt_count += 1
        try:
            response = httpx.post(target_url, content=body, headers=headers, timeout=10)
            response.raise_for_status()
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.last_error = None
        except Exception as exc:  # noqa: BLE001
            delivery.status = "failed"
            delivery.last_error = str(exc)
            raise
