"""Add webhook queue scheduling columns

Revision ID: 0002_webhook_queue_fields
Revises: 0001_initial_schema
Create Date: 2026-02-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0002_webhook_queue_fields"
down_revision = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "webhook_deliveries",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute("UPDATE webhook_deliveries SET next_attempt_at = CURRENT_TIMESTAMP WHERE next_attempt_at IS NULL")
    op.alter_column("webhook_deliveries", "next_attempt_at", nullable=False)


def downgrade() -> None:
    op.drop_column("webhook_deliveries", "dead_lettered_at")
    op.drop_column("webhook_deliveries", "last_attempt_at")
    op.drop_column("webhook_deliveries", "next_attempt_at")
