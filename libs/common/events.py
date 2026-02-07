from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from libs.common.config import Settings, get_settings


class EventBus(Protocol):
    def publish(
        self, topic: str, payload: dict[str, Any], attributes: dict[str, str] | None = None
    ) -> None: ...


@dataclass
class InMemoryEventBus:
    events: list[dict[str, Any]] = field(default_factory=list)

    def publish(
        self, topic: str, payload: dict[str, Any], attributes: dict[str, str] | None = None
    ) -> None:
        self.events.append(
            {
                "topic": topic,
                "payload": payload,
                "attributes": attributes or {},
            }
        )


class GCPPubSubEventBus:
    def __init__(self, settings: Settings):
        if not settings.gcp_project_id:
            raise RuntimeError("gcp_project_id is required for pubsub backend")
        pubsub_module = importlib.import_module("google.cloud.pubsub_v1")
        self._publisher = pubsub_module.PublisherClient()
        self._project_id = settings.gcp_project_id
        self._prefix = settings.gcp_pubsub_topic_prefix

    def publish(
        self, topic: str, payload: dict[str, Any], attributes: dict[str, str] | None = None
    ) -> None:
        topic_id = f"{self._prefix}-{topic}".replace(".", "-")
        topic_path = self._publisher.topic_path(self._project_id, topic_id)
        data = json.dumps(payload).encode("utf-8")
        future = self._publisher.publish(topic_path, data=data, **(attributes or {}))
        future.result(timeout=10)


def get_event_bus(settings: Settings | None = None) -> EventBus:
    runtime_settings = settings or get_settings()
    if runtime_settings.event_bus_backend == "pubsub":
        return GCPPubSubEventBus(runtime_settings)
    return InMemoryEventBus()
