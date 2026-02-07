from __future__ import annotations

from fastapi.testclient import TestClient


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/token",
        json={
            "user_id": "phase4_user",
            "email": "phase4@example.com",
            "tenant_ids": ["tenant_1"],
            "roles": ["admin", "operator", "analyst", "compliance", "finance", "reviewer"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": "tenant_1"}


def test_phase4_endpoints(client: TestClient) -> None:
    headers = _headers(client)

    discrepancy = client.post(
        "/api/v1/discrepancy/score",
        json={
            "declared_weight": 100,
            "actual_weight": 150,
            "declared_value": 1000,
            "actual_value": 600,
            "route_risk_factor": 0.8,
            "historical_score_bias": 0.5,
        },
        headers=headers,
    )
    assert discrepancy.status_code == 200
    discrepancy_body = discrepancy.json()
    assert discrepancy_body["risk_level"] in {"medium", "high"}
    assert len(discrepancy_body["explanations"]) >= 2

    dg_check = client.post(
        "/api/v1/dg/checks",
        json={
            "document_id": "doc_dg_1",
            "un_number": "INVALID",
            "packing_group": "IV",
        },
        headers=headers,
    )
    assert dg_check.status_code == 200
    dg_body = dg_check.json()
    assert dg_body["valid"] is False
    assert dg_body["review_task_id"] is not None

    station_kpis = client.post(
        "/api/v1/station-analytics/kpis",
        json={
            "throughput_per_hour": 20,
            "avg_dwell_minutes": 120,
            "delayed_shipments": 30,
            "total_shipments": 100,
        },
        headers=headers,
    )
    assert station_kpis.status_code == 200
    assert station_kpis.json()["risk_flag"] == "red"

    latest_kpi = client.get("/api/v1/analytics/station-kpi/latest", headers=headers)
    assert latest_kpi.status_code == 200
    assert "source" in latest_kpi.json()

    register_model = client.post(
        "/api/v1/active-learning/models/register",
        json={
            "domain": "awb",
            "model_name": "vertex-awb-extractor",
            "model_version": "v2026-02-08",
            "metadata": {"dataset_uri": "bq://project.ds.tbl"},
        },
        headers=headers,
    )
    assert register_model.status_code == 200
    model_id = register_model.json()["id"]

    listed_models = client.get("/api/v1/active-learning/models", headers=headers)
    assert listed_models.status_code == 200
    assert any(item["id"] == model_id for item in listed_models.json())

    rollback_model = client.post(
        f"/api/v1/active-learning/models/{model_id}/rollback",
        headers=headers,
    )
    assert rollback_model.status_code == 200
    assert rollback_model.json()["rollback_of_id"] == model_id
