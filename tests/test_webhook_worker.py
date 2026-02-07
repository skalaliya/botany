from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from libs.common.config import get_settings
from libs.common.models import Base, Tenant, User, WebhookDelivery
from services.webhooks.service import WebhookService


def _make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    session.add(Tenant(id="tenant_1", name="Tenant 1", status="active"))
    session.add(User(id="user_1", email="user1@example.com", display_name="User 1"))
    session.commit()
    return session


def test_webhook_queue_worker_success_path() -> None:
    get_settings.cache_clear()
    db = _make_session()

    def success_post(*_args: object, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", "https://example.test/webhook")
        return httpx.Response(200, json={"ok": True}, request=request)

    service = WebhookService(http_post=success_post)
    subscription = service.create_subscription(
        db,
        tenant_id="tenant_1",
        actor_id="user_1",
        target_url="https://example.test/webhook",
        event_filter="document.received",
    )
    db.commit()

    enqueued = service.dispatch_event(
        db,
        tenant_id="tenant_1",
        event_type="document.received",
        payload={"document_id": "doc_1"},
    )
    db.commit()
    assert enqueued == 1

    pending = db.execute(
        select(WebhookDelivery).where(WebhookDelivery.subscription_id == subscription.id)
    ).scalar_one()
    assert pending.status == "pending"

    outcome = service.process_delivery_queue(db, tenant_id="tenant_1", batch_size=10)
    db.commit()

    assert outcome["processed"] == 1
    assert outcome["delivered"] == 1

    delivered = db.execute(
        select(WebhookDelivery).where(WebhookDelivery.subscription_id == subscription.id)
    ).scalar_one()
    assert delivered.status == "delivered"
    assert delivered.delivered_at is not None


def test_webhook_dlq_and_replay_path() -> None:
    get_settings.cache_clear()
    db = _make_session()

    def failing_post(*_args: object, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", "https://example.test/webhook")
        raise httpx.ConnectError("network down", request=request)

    service = WebhookService(http_post=failing_post)
    service.create_subscription(
        db,
        tenant_id="tenant_1",
        actor_id="user_1",
        target_url="https://example.test/webhook",
        event_filter="document.validated",
    )
    db.commit()

    service.dispatch_event(
        db,
        tenant_id="tenant_1",
        event_type="document.validated",
        payload={"document_id": "doc_2"},
    )
    db.commit()

    settings = get_settings()
    for _ in range(settings.webhook_max_retries + 1):
        service.process_delivery_queue(db, tenant_id="tenant_1", batch_size=10)
        db.commit()
        delivery = db.execute(select(WebhookDelivery)).scalar_one()
        if delivery.status == "dead_lettered":
            break
        delivery.next_attempt_at = datetime.now(timezone.utc)
        db.commit()

    dlq_delivery = db.execute(select(WebhookDelivery)).scalar_one()
    assert dlq_delivery.status == "dead_lettered"
    assert dlq_delivery.dead_lettered_at is not None

    requeued = service.replay_dead_lettered(db, tenant_id="tenant_1", limit=10)
    db.commit()
    assert requeued == 1

    replayed = db.execute(select(WebhookDelivery)).scalar_one()
    assert replayed.status == "pending"
    assert replayed.attempt_count == 0
