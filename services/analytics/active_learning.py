from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.models import Correction


class ActiveLearningService:
    def curate_dataset(self, db: Session, *, tenant_id: str) -> tuple[int, str]:
        stmt = select(Correction).where(Correction.tenant_id == tenant_id)
        corrections = list(db.execute(stmt).scalars().all())

        output_dir = Path("/tmp/nexuscargo-active-learning")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{tenant_id}-corrections.jsonl"

        with output_file.open("w", encoding="utf-8") as stream:
            for correction in corrections:
                stream.write(
                    json.dumps(
                        {
                            "tenant_id": tenant_id,
                            "field_name": correction.field_name,
                            "old_value": correction.old_value,
                            "new_value": correction.new_value,
                            "reason_tag": correction.reason_tag,
                        }
                    )
                    + "\n"
                )

        return len(corrections), f"file://{output_file}"


# TODO(owner:ml-platform): publish curated dataset to BigQuery + Vertex AI Dataset and version model registry metadata.
