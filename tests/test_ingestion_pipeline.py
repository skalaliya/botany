from __future__ import annotations

import base64

from fastapi.testclient import TestClient


def _issue_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "user_id": "user_1",
            "email": "ops@example.com",
            "tenant_ids": ["tenant_1"],
            "roles": ["admin", "operator", "reviewer"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    access_token = body["access_token"]
    assert isinstance(access_token, str)
    return access_token


def test_ingestion_to_review_flow(client: TestClient) -> None:
    token = _issue_token(client)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "tenant_1",
        "Idempotency-Key": "idem-ingest-1",
    }
    document_payload = {
        "file_name": "random-lowconf.pdf",
        "content_type": "application/pdf",
        "content_base64": base64.b64encode(b"hello world").decode("utf-8"),
    }

    ingest_response = client.post(
        "/api/v1/ingestion/documents", json=document_payload, headers=headers
    )
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()
    assert ingest_body["review_required"] is True

    # Idempotency guarantees same response for identical payload.
    ingest_retry = client.post(
        "/api/v1/ingestion/documents", json=document_payload, headers=headers
    )
    assert ingest_retry.status_code == 200
    assert ingest_retry.json()["document_id"] == ingest_body["document_id"]

    documents_response = client.get("/api/v1/documents", headers=headers)
    assert documents_response.status_code == 200
    assert documents_response.json()["total"] >= 1

    review_response = client.get("/api/v1/review/tasks", headers=headers)
    assert review_response.status_code == 200
    tasks = review_response.json()
    assert len(tasks) == 1

    complete_response = client.post(
        f"/api/v1/review/tasks/{tasks[0]['id']}/complete",
        json={
            "approved": True,
            "corrections": [
                {
                    "field_name": "awb_number",
                    "old_value": "123-INVALID",
                    "new_value": "123-12345678",
                    "reason_tag": "manual_fix",
                }
            ],
        },
        headers=headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "approved"
