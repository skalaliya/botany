from __future__ import annotations

from libs.common.logging import configure_logging, log_event


class NotificationService:
    def __init__(self) -> None:
        self._logger = configure_logging()

    def send_exception_notification(self, *, tenant_id: str, category: str, message: str) -> None:
        log_event(
            self._logger,
            "exception_notification",
            {
                "tenant_id": tenant_id,
                "category": category,
                "message": message,
            },
        )
