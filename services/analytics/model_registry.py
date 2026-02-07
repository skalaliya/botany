from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.models import ModelVersion


class ModelRegistryService:
    def register_model(
        self,
        db: Session,
        *,
        tenant_id: str,
        domain: str,
        model_name: str,
        model_version: str,
        metadata: dict[str, object],
    ) -> ModelVersion:
        active_stmt = select(ModelVersion).where(
            ModelVersion.tenant_id == tenant_id,
            ModelVersion.domain == domain,
            ModelVersion.model_name == model_name,
            ModelVersion.status == "active",
        )
        for existing in db.execute(active_stmt).scalars().all():
            existing.status = "inactive"

        record = ModelVersion(
            id=f"mdl_{uuid4().hex}",
            tenant_id=tenant_id,
            domain=domain,
            model_name=model_name,
            model_version=model_version,
            status="active",
            rollback_of_id=None,
            model_metadata=metadata,
            deployed_at=datetime.now(timezone.utc),
        )
        db.add(record)
        return record

    def list_models(
        self,
        db: Session,
        *,
        tenant_id: str,
        domain: str | None = None,
    ) -> list[ModelVersion]:
        stmt = select(ModelVersion).where(ModelVersion.tenant_id == tenant_id)
        if domain:
            stmt = stmt.where(ModelVersion.domain == domain)
        stmt = stmt.order_by(ModelVersion.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    def rollback_model(
        self,
        db: Session,
        *,
        tenant_id: str,
        model_id: str,
    ) -> ModelVersion:
        target_stmt = select(ModelVersion).where(
            ModelVersion.id == model_id,
            ModelVersion.tenant_id == tenant_id,
        )
        target = db.execute(target_stmt).scalar_one_or_none()
        if not target:
            raise ValueError("model version not found")

        active_stmt = select(ModelVersion).where(
            ModelVersion.tenant_id == tenant_id,
            ModelVersion.domain == target.domain,
            ModelVersion.model_name == target.model_name,
            ModelVersion.status == "active",
        )
        for existing in db.execute(active_stmt).scalars().all():
            existing.status = "inactive"

        rollback_record = ModelVersion(
            id=f"mdl_{uuid4().hex}",
            tenant_id=tenant_id,
            domain=target.domain,
            model_name=target.model_name,
            model_version=target.model_version,
            status="active",
            rollback_of_id=target.id,
            model_metadata={
                "rollback_source": target.id,
                "reason": "manual rollback",
                "copied_metadata": target.model_metadata,
            },
            deployed_at=datetime.now(timezone.utc),
        )
        db.add(rollback_record)
        return rollback_record
